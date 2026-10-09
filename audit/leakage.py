import email
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.common import DERIVED, iter_jsonl, norm_subject, parse_date

HOUSTON = ZoneInfo("America/Chicago")
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
SENT_RE = re.compile(r"Sent:\s*\w+,\s*(\w+)\s+(\d{1,2}),\s*(\d{4})", re.IGNORECASE)
SLASH_TS_RE = re.compile(r"^[ \t]*(\d{1,2})/(\d{1,2})/(\d{4})\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)[ \t]*$", re.MULTILINE | re.IGNORECASE)
ON_DATE_RE = re.compile(r"\bon\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)", re.IGNORECASE)


def quoted_dates(text):
    out = []
    for m in SENT_RE.finditer(text):
        month = MONTHS.get(m.group(1).lower())
        if month:
            try:
                out.append(date(int(m.group(3)), month, int(m.group(2))))
            except ValueError:
                pass
    for rx in (SLASH_TS_RE, ON_DATE_RE):
        for m in rx.finditer(text):
            try:
                out.append(date(int(m.group(3)), int(m.group(1)), int(m.group(2))))
            except ValueError:
                pass
    return out


def value_forms(spec):
    v = spec["value"]
    if spec["type"] == "date":
        d = date.fromisoformat(v)
        return {v, f"{d.month}/{d.day}/{d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}", d.strftime("%B ") + str(d.day), d.strftime("%b ") + str(d.day)}
    if spec["type"] == "time":
        h, mnt = map(int, v.split(":"))
        h12 = h % 12 or 12
        ampm = "pm" if h >= 12 else "am"
        forms = {v, f"{h12}:{mnt:02d} {ampm}", f"{h12}:{mnt:02d}{ampm}"}
        if mnt == 0:
            forms |= {f"{h12} {ampm}", f"{h12}{ampm}"}
        return forms
    if spec["type"] == "int":
        return {str(v), f"{v:,}"}
    if spec["type"] == "number":
        return {f"{v:.2f}", f"{v:.3f}", f"{v:.4f}"}
    return {str(v)}


def mailbox_files(task):
    box = task / "environment" / "mailbox"
    return [p for p in sorted(box.rglob("*")) if p.is_file()]


def check_cut(ep, cut, user_rows):
    task = REPO / "tasks" / cut["slug"]
    t = datetime.fromisoformat(cut["t_utc"]).astimezone(timezone.utc)
    t_local_day = t.astimezone(HOUSTON).date()
    files = mailbox_files(task)
    expected = json.loads((task / "tests" / "expected.json").read_text())
    instruction = (task / "instruction.md").read_text()
    result = {"task": cut["slug"], "files": len(files)}

    late = []
    bodies = {}
    for p in files:
        msg = email.message_from_bytes(p.read_bytes())
        d = parse_date(msg.get("Date"))
        if d is None or d > t:
            late.append(str(p.relative_to(task)))
        bodies[p] = p.read_text(encoding="latin-1")
    result["L1_files_after_t_or_undated"] = late

    snap_clusters = {r["cluster"] for r in user_rows if r["path"].split("/", 1)[1] in {str(p.relative_to(task / "environment" / "mailbox")) for p in files}}
    straddle = sorted({r["cluster"] for r in user_rows if r["cluster"] in snap_clusters and r["date_utc"] and datetime.fromisoformat(r["date_utc"]) > t})
    result["L2_clusters_straddling_t"] = straddle

    future_quotes = []
    for p, text in bodies.items():
        if any(d > t_local_day for d in quoted_dates(text)):
            future_quotes.append(str(p.relative_to(task)))
    result["L3_quoted_dates_after_t"] = future_quotes

    hits = []
    for value in cut.get("post_t_values", []):
        for p, text in bodies.items():
            if value in text:
                hits.append(f"{value} :: {p.relative_to(task)}")
    result["L4_post_t_value_hits_for_review"] = hits

    result["L5_canary_in_agent_image"] = canary_hits(task, expected["canary"])

    leaked = []
    lower = instruction.lower()
    for name, spec in expected["fields"].items():
        for form in value_forms(spec):
            if form.lower() in lower:
                leaked.append(f"{name}={form}")
    by_path = {r["path"]: r for r in user_rows}
    for p in cut["decisive_paths"]:
        subj = by_path[p]["subject"]
        if len(subj) >= 8 and subj in norm_subject(instruction):
            leaked.append(f"decisive subject: {subj}")
    result["L6_instruction_leaks"] = leaked

    verbatim = {}
    for name, spec in expected["fields"].items():
        forms = value_forms(spec)
        verbatim[name] = sum(1 for text in bodies.values() if any(f in text for f in forms))
    result["L7_files_containing_answer_value"] = verbatim
    return result


def canary_hits(task, canary):
    tag = f"enron-audit-{task.name}".lower()
    build = subprocess.run(["docker", "build", "-q", "-t", tag, str(task / "environment")], capture_output=True, text=True)
    if build.returncode != 0:
        return ["docker build failed: " + build.stderr.strip()[-200:]]
    run = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", tag, "grep", "-rIl", canary, "/", "--exclude-dir=proc", "--exclude-dir=sys", "--exclude-dir=dev"],
        capture_output=True,
        text=True,
    )
    return [line for line in run.stdout.splitlines() if line]


def main():
    rows_by_user = {}
    lines = ["# Leakage audit", ""]
    failed = False
    for ep_path in sorted((REPO / "episodes").glob("*.json")):
        ep = json.loads(ep_path.read_text())
        if "cuts" not in ep:
            continue
        if ep["user"] not in rows_by_user:
            rows_by_user[ep["user"]] = [r for r in iter_jsonl(DERIVED / "index.jsonl.gz") if r["user"] == ep["user"]]
        for cut in ep["cuts"]:
            res = check_cut(ep, cut, rows_by_user[ep["user"]])
            hard = ["L1_files_after_t_or_undated", "L2_clusters_straddling_t", "L3_quoted_dates_after_t", "L5_canary_in_agent_image", "L6_instruction_leaks"]
            bad = [k for k in hard if res[k]]
            failed = failed or bool(bad)
            lines.append(f"## {res['task']}  ({res['files']} files)  {'FAIL: ' + ', '.join(bad) if bad else 'PASS'}")
            lines.append("")
            for k in hard:
                lines.append(f"- {k}: {len(res[k])}" + (f" -> {res[k][:5]}" if res[k] else ""))
            lines.append(f"- L4_post_t_value_hits_for_review: {len(res['L4_post_t_value_hits_for_review'])}")
            for h in res["L4_post_t_value_hits_for_review"][:10]:
                lines.append(f"  - {h}")
            note = cut.get("l4_review")
            if note:
                lines.append(f"  - review: {note}")
            lines.append(f"- L7_files_containing_answer_value: {res['L7_files_containing_answer_value']}")
            lines.append("")
    (REPO / "results" / "audit.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
