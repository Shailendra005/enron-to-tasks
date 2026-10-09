import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
FIELDS = ["task", "agent", "model", "trial", "reward", "failed_tests", "exception", "duration_s", "input_tokens", "output_tokens", "cost_usd"]


def failed_tests(trial):
    ctrf = trial / "verifier" / "ctrf.json"
    if not ctrf.exists():
        return ""
    try:
        tests = json.loads(ctrf.read_text())["results"]["tests"]
    except (KeyError, json.JSONDecodeError):
        return "unreadable"
    return ";".join(t["name"].split("::")[-1] for t in tests if t.get("status") != "passed")


def trial_row(trial):
    data = json.loads((trial / "result.json").read_text())
    info = data.get("agent_info") or {}
    model = (info.get("model_info") or {}).get("name") or ""
    vr = data.get("verifier_result") or {}
    reward = (vr.get("rewards") or {}).get("reward")
    ar = data.get("agent_result") or {}
    exc = data.get("exception_info")
    duration = ""
    if data.get("started_at") and data.get("finished_at"):
        a = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(data["finished_at"].replace("Z", "+00:00"))
        duration = round((b - a).total_seconds())
    return {
        "task": data.get("task_name", ""),
        "agent": info.get("name", ""),
        "model": model,
        "trial": data.get("trial_name", ""),
        "reward": "" if reward is None else reward,
        "failed_tests": failed_tests(trial),
        "exception": (exc or {}).get("exception_type", "") if isinstance(exc, dict) else ("error" if exc else ""),
        "duration_s": duration,
        "input_tokens": ar.get("n_input_tokens", ""),
        "output_tokens": ar.get("n_output_tokens", ""),
        "cost_usd": round(ar["cost_usd"], 4) if isinstance(ar.get("cost_usd"), (int, float)) else "",
    }


def main():
    roots = [Path(p).expanduser() for p in sys.argv[1:]]
    rows = []
    for root in roots:
        for result in sorted(root.glob("*/*/result.json")):
            rows.append(trial_row(result.parent))
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "trials.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["agent"], r["model"], r["task"])].append(r)
    lines = ["| Agent | Model | Task | Passed | Valid trials | Infra errors | Failed checks |", "|---|---|---|---|---|---|---|"]
    for (agent, model, task), items in sorted(groups.items()):
        valid = [r for r in items if not r["exception"] and r["reward"] != ""]
        errors = len(items) - len(valid)
        passed = sum(1 for r in valid if float(r["reward"]) >= 1.0)
        fails = defaultdict(int)
        for r in valid:
            for name in filter(None, r["failed_tests"].split(";")):
                fails[name] += 1
        fail_text = ", ".join(f"{k} x{v}" for k, v in sorted(fails.items())) or "-"
        lines.append(f"| {agent} | {model or '-'} | {task} | {passed}/{len(valid)} | {len(valid)} | {errors} | {fail_text} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
