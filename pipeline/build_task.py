import argparse
import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.common import DERIVED, MAILDIR, REPO, iter_jsonl, write_json

HOUSTON = ZoneInfo("America/Chicago")
TEMPLATES = REPO / "templates"
TASKS = REPO / "tasks"
MAX_FILES = 3000
MAX_BYTES = 15 * 1024 * 1024


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_user_rows(user):
    return [r for r in iter_jsonl(DERIVED / "index.jsonl.gz") if r["user"] == user]


def select_snapshot(rows, t, window_days):
    start = t - timedelta(days=window_days)
    latest = {}
    for r in rows:
        if r["date_utc"]:
            d = datetime.fromisoformat(r["date_utc"])
            latest[r["cluster"]] = max(latest.get(r["cluster"], d), d)
    keep = []
    for r in rows:
        if not r["date_utc"]:
            continue
        d = datetime.fromisoformat(r["date_utc"])
        if start <= d <= t and latest[r["cluster"]] <= t:
            keep.append(r)
    return sorted(keep, key=lambda r: r["path"]), start


def instruction_text(episode, cut, t, window_days):
    local = t.astimezone(HOUSTON)
    lines = [
        f"# {episode['title']}",
        "",
        f"`/app/mailbox/` holds the email of {episode['person']} at Enron as it stood at "
        f"**{local:%A %d %B %Y, %H:%M} Houston time ({t:%Y-%m-%d %H:%M} UTC)**. "
        f"It covers the {window_days} days before that moment in the original folder layout, one RFC 822 message per file. "
        "Nothing written after that moment is included.",
        "",
        episode["question"],
        "",
        "Write your answer to `/app/answer.json`:",
        "",
        "```json",
        json.dumps({**{k: v["example"] for k, v in episode["fields"].items()}, "evidence_message_ids": ["<message-id>"]}, indent=2),
        "```",
        "",
    ]
    for name, spec in episode["fields"].items():
        lines.append(f"- `{name}`: {spec['doc']}")
    lines += [
        "- `evidence_message_ids`: 1 to 5 `Message-ID` header values, copied exactly including the angle brackets, of the emails that establish your answer.",
        "- Plans or terms that were proposed and later replaced do not count. Report what stands at the moment given above, according to the mailbox.",
        "",
    ]
    return "\n".join(lines)


def toml_text(episode, cut):
    meta = cut["metadata"]

    def q(s):
        return json.dumps(s, ensure_ascii=False)

    return "\n".join(
        [
            f"name = {q(cut['slug'])}",
            'artifacts = ["/app/answer.json"]',
            "",
            "[metadata]",
            'author_name = "Shailendrasinh Zala"',
            'category = "Enterprise data"',
            'subcategory = "Email archive reasoning"',
            f"tags = {json.dumps(['email-archive', 'time-split', 'superseded-information', episode['kind']])}",
            f"difficulty = {q(cut['difficulty'])}",
            f"difficulty_explanation = {q(meta['difficulty_explanation'])}",
            f"solution_explanation = {q(meta['solution_explanation'])}",
            f"verification_explanation = {q(meta['verification_explanation'])}",
            "",
            "[verifier]",
            "timeout_sec = 300",
            'environment_mode = "separate"',
            "",
            "[verifier.environment]",
            "allow_internet = false",
            "build_timeout_sec = 600",
            "cpus = 1",
            "memory_mb = 2048",
            "",
            "[agent]",
            "timeout_sec = 1800",
            "",
            "[environment]",
            "allow_internet = true",
            "build_timeout_sec = 900",
            "cpus = 2",
            "memory_mb = 4096",
            "storage_mb = 10240",
            "",
        ]
    )


def solve_text(user, cut, answer):
    rel = cut["decisive_paths"][0].split("/", 1)[1]
    quote = cut["evidence_quote"]
    if "'" in quote or "'" in rel:
        sys.exit("evidence quote and path must not contain single quotes")
    return "\n".join(
        [
            "#!/bin/bash",
            "set -euo pipefail",
            f"grep -qF -- '{quote}' '/app/mailbox/{rel}'",
            "cat > /app/answer.json <<'JSON'",
            json.dumps(answer, indent=2),
            "JSON",
            "",
        ]
    )


def build_cut(episode, cut, rows):
    t = datetime.fromisoformat(cut["t_utc"]).astimezone(timezone.utc)
    window = episode.get("window_days", 90)
    snap, start = select_snapshot(rows, t, window)
    total = sum((MAILDIR / r["path"]).stat().st_size for r in snap)
    if len(snap) > MAX_FILES or total > MAX_BYTES:
        sys.exit(f"{cut['slug']}: snapshot too large ({len(snap)} files, {total} bytes); shrink window_days")
    paths = {r["path"] for r in snap}
    by_path = {r["path"]: r for r in rows}
    for p in cut["decisive_paths"]:
        if p not in paths:
            sys.exit(f"{cut['slug']}: decisive file {p} not in snapshot")
    decisive = sorted({by_path[p]["cluster"] for p in cut["decisive_paths"]})
    clusters = {}
    for r in snap:
        mid = r["message_id"]
        if not mid:
            continue
        if mid in clusters and clusters[mid] != r["cluster"]:
            sys.exit(f"{cut['slug']}: message id {mid} maps to two clusters")
        clusters[mid] = r["cluster"]
    task = TASKS / cut["slug"]
    if task.exists():
        shutil.rmtree(task)
    (task / "environment" / "mailbox").mkdir(parents=True)
    (task / "solution").mkdir()
    (task / "tests").mkdir()
    manifest = {}
    for r in snap:
        rel = r["path"].split("/", 1)[1]
        dst = task / "environment" / "mailbox" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(MAILDIR / r["path"], dst)
        manifest[rel] = sha256_file(dst)
    write_json(
        task / "snapshot_manifest.json",
        {
            "source": "CMU Enron email corpus, enron_mail_20150507",
            "user": episode["user"],
            "t_utc": t.isoformat(),
            "window_start_utc": start.isoformat(),
            "files": manifest,
        },
    )
    fields = {}
    for name, spec in episode["fields"].items():
        entry = {"type": spec["type"], "value": cut["expected"][name]}
        if "tolerance" in spec:
            entry["tolerance"] = spec["tolerance"]
        fields[name] = entry
    canary = str(uuid.uuid5(uuid.NAMESPACE_URL, f"enron-to-tasks/{cut['slug']}"))
    write_json(task / "tests" / "expected.json", {"fields": fields, "decisive_clusters": decisive, "canary": canary})
    write_json(task / "tests" / "clusters.json", clusters)
    decisive_id = by_path[cut["decisive_paths"][0]]["message_id"]
    answer = {**cut["expected"], "evidence_message_ids": [decisive_id]}
    (task / "solution" / "solve.sh").write_text(solve_text(episode["user"], cut, answer))
    (task / "solution" / "solve.sh").chmod(0o755)
    (task / "instruction.md").write_text(instruction_text(episode, cut, t, window))
    (task / "task.toml").write_text(toml_text(episode, cut))
    shutil.copyfile(TEMPLATES / "env.Dockerfile", task / "environment" / "Dockerfile")
    shutil.copyfile(TEMPLATES / "env.dockerignore", task / "environment" / ".dockerignore")
    shutil.copyfile(TEMPLATES / "tests.Dockerfile", task / "tests" / "Dockerfile")
    shutil.copyfile(TEMPLATES / "tests.dockerignore", task / "tests" / ".dockerignore")
    for name in ("test.sh", "test_outputs.py", "grader.py", "requirements.lock"):
        shutil.copyfile(TEMPLATES / name, task / "tests" / name)
    (task / "tests" / "test.sh").chmod(0o755)
    print(f"{cut['slug']}: {len(snap)} files, {total / 1e6:.1f} MB, decisive clusters {len(decisive)}")


def rebuild(task_dir):
    task_dir = Path(task_dir)
    manifest = json.loads((task_dir / "snapshot_manifest.json").read_text())
    box = task_dir / "environment" / "mailbox"
    if box.exists():
        shutil.rmtree(box)
    for rel, digest in manifest["files"].items():
        src = MAILDIR / manifest["user"] / rel
        if sha256_file(src) != digest:
            sys.exit(f"hash mismatch for {rel}")
        dst = box / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    print(f"{task_dir.name}: rebuilt {len(manifest['files'])} files, hashes match")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--rebuild", nargs="*")
    args = ap.parse_args()
    if args.rebuild is not None:
        targets = args.rebuild or sorted(str(p) for p in TASKS.iterdir() if p.is_dir())
        for target in targets:
            rebuild(target)
        return
    episode = json.loads(Path(args.episode).read_text())
    rows = load_user_rows(episode["user"])
    for cut in episode["cuts"]:
        build_cut(episode, cut, rows)


if __name__ == "__main__":
    main()
