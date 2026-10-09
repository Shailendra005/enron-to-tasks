import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from audit.extract import values_for
from pipeline.common import DERIVED, iter_jsonl
from pipeline.strip_quotes import strip_quoted

spec = importlib.util.spec_from_file_location("grader", REPO / "templates" / "grader.py")
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)


def load_thread(paths):
    wanted = set(paths)
    msgs = []
    for rec in iter_jsonl(DERIVED / "messages.jsonl.gz"):
        if rec["path"] in wanted:
            text, _ = strip_quoted(rec["body"])
            msgs.append({"path": rec["path"], "id": rec["message_id"], "date": rec["date_utc"], "text": rec["subject"] + "\n" + text})
    return sorted(msgs, key=lambda m: m["date"])


def per_field(msgs, fields):
    found = {name: [] for name in fields}
    for m in msgs:
        for name, spec_ in fields.items():
            for v in values_for(spec_["type"], name, m["text"], m["date"]):
                found[name].append((v, m["id"]))
    return found


def answer_from(choice, fields):
    ans = {}
    ids = []
    for name in fields:
        if choice.get(name):
            value, mid = choice[name]
            ans[name] = value
            ids.append(mid)
    ans["evidence_message_ids"] = list(dict.fromkeys(ids))[:5] or ["<none>"]
    return ans


def strategies(visible, full, fields):
    vis = per_field(visible, fields)
    allv = per_field(full, fields)
    out = {}
    out["first_mention"] = {n: v[0] for n, v in vis.items() if v}
    out["latest_mention_before_t"] = {n: v[-1] for n, v in vis.items() if v}
    mode = {}
    for n, v in vis.items():
        if v:
            top = Counter(x for x, _ in v).most_common(1)[0][0]
            mode[n] = next(item for item in reversed(v) if item[0] == top)
    out["most_frequent"] = mode
    out["latest_in_uncut_archive"] = {n: v[-1] for n, v in allv.items() if v}
    confirm = [m for m in visible if "confirm" in m["text"].lower()]
    out["latest_confirm_message"] = {n: v[-1] for n, v in per_field(confirm[-1:], fields).items() if v} if confirm else {}
    return out


def main():
    episodes = sorted((REPO / "episodes").glob("*.json"))
    lines = ["| Task | Baseline | Reward | Fields right | Citation ok |", "|---|---|---|---|---|"]
    for ep_path in episodes:
        ep = json.loads(ep_path.read_text())
        if "cuts" not in ep:
            continue
        full = load_thread(ep["thread_paths"])
        for cut in ep["cuts"]:
            t = datetime.fromisoformat(cut["t_utc"]).astimezone(timezone.utc)
            visible = [m for m in full if datetime.fromisoformat(m["date"]) <= t]
            task = REPO / "tasks" / cut["slug"] / "tests"
            expected = json.loads((task / "expected.json").read_text())
            clusters = json.loads((task / "clusters.json").read_text())
            for name, choice in strategies(visible, full, expected["fields"]).items():
                res = grader.grade(answer_from(choice, expected["fields"]), expected, clusters)
                right = sum(res[f] for f in expected["fields"])
                lines.append(f"| {cut['slug']} | {name} | {res['reward']} | {right}/{len(expected['fields'])} | {'yes' if res['citations'] else 'no'} |")
    out = REPO / "results" / "baselines.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
