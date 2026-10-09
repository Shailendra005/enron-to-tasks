import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def answer_from_solve(task):
    text = (task / "solution" / "solve.sh").read_text()
    body = text.split("<<'JSON'\n", 1)[1].split("\nJSON", 1)[0]
    return json.loads(body)


def run_case(tag, workdir):
    logs = workdir / "logs"
    logs.mkdir()
    subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "-v", f"{workdir / 'app'}:/app", "-v", f"{logs}:/logs", tag, "/tests/test.sh"],
        capture_output=True,
        text=True,
    )
    reward = logs / "verifier" / "reward.txt"
    return reward.read_text().strip() if reward.exists() else "missing"


def cases(task, ep_cut):
    true = answer_from_solve(task)
    clusters = json.loads((task / "tests" / "clusters.json").read_text())
    expected = json.loads((task / "tests" / "expected.json").read_text())
    decisive = set(expected["decisive_clusters"])
    copies = [mid for mid, c in clusters.items() if c in decisive and mid not in true["evidence_message_ids"]]
    others = [mid for mid, c in clusters.items() if c not in decisive]
    out = [("true answer", "1", json.dumps(true))]
    superseded = ep_cut.get("superseded")
    if superseded:
        out.append(("superseded answer", "0", json.dumps({**true, **superseded})))
    out.append(("right values, invented message id", "0", json.dumps({**true, "evidence_message_ids": ["<123.JavaMail.invented@thyme>"]})))
    out.append(("right values, only non-decisive ids", "0", json.dumps({**true, "evidence_message_ids": others[:3]})))
    if copies:
        out.append(("right values, id of a duplicate copy", "1", json.dumps({**true, "evidence_message_ids": copies[:1]})))
    out.append(("right values, 30 citations", "0", json.dumps({**true, "evidence_message_ids": (true["evidence_message_ids"] + others)[:30]})))
    out.append(("malformed json", "0", "{not json"))
    out.append(("oversized file", "0", json.dumps({**true, "pad": "x" * 70000})))
    out.append(("missing file", "0", None))
    out.append(("symlinked answer", "0", "SYMLINK"))
    first_field = sorted(expected["fields"])[0]
    out.append((f"wrong type for {first_field}", "0", json.dumps({**true, first_field: [true[first_field]]})))
    return out


def main():
    episodes = {}
    for ep_path in sorted((REPO / "episodes").glob("*.json")):
        ep = json.loads(ep_path.read_text())
        for cut in ep.get("cuts", []):
            episodes[cut["slug"]] = cut
    targets = sys.argv[1:] or sorted(episodes)
    lines = ["| Task | Case | Expected | Got | OK |", "|---|---|---|---|---|"]
    all_ok = True
    for slug in targets:
        task = REPO / "tasks" / slug
        tag = f"enron-grade-{slug}".lower()
        build = subprocess.run(["docker", "build", "-q", "-t", tag, str(task / "tests")], capture_output=True, text=True)
        if build.returncode != 0:
            print(build.stderr)
            sys.exit(f"tests image build failed for {slug}")
        for name, want, content in cases(task, episodes[slug]):
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                app = work / "app"
                app.mkdir()
                if content == "SYMLINK":
                    (app / "real.json").write_text(json.dumps(answer_from_solve(task)))
                    os.symlink("real.json", app / "answer.json")
                elif content is not None:
                    (app / "answer.json").write_text(content)
                got = run_case(tag, work)
            ok = got == want
            all_ok = all_ok and ok
            lines.append(f"| {slug} | {name} | {want} | {got} | {'yes' if ok else 'NO'} |")
    (REPO / "results" / "grader_selftest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
