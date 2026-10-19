import json
import math
import random
import sys
from pathlib import Path

from pipeline.common import DERIVED, REPO, RESULTS, iter_jsonl, write_json

SEED = 20261010
SAMPLE_SIZE = 20
LABELS = REPO / "episodes" / "yield_labels.json"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def sample():
    cands = list(iter_jsonl(DERIVED / "candidates.jsonl.gz"))
    rng = random.Random(SEED)
    picks = sorted(rng.sample(range(len(cands)), min(SAMPLE_SIZE, len(cands))))
    write_json(DERIVED / "yield_sample.json", [{"candidate_index": i, "user": cands[i]["user"], "subject": cands[i]["subject"], "kind": cands[i]["kind"]} for i in picks])
    print(" ".join(str(i) for i in picks))


def estimate():
    labels = json.loads(LABELS.read_text())["labels"]
    n = len(labels)
    k = sum(1 for x in labels if x["accept"])
    k_strict = sum(1 for x in labels if x.get("strict_accept"))
    lo, hi = wilson(k, n)
    slo, shi = wilson(k_strict, n)
    summary = json.loads((RESULTS / "candidates_summary.json").read_text())
    tokens = json.loads((RESULTS / "tokens.json").read_text())
    new_tokens = tokens["levels"]["4_new_text"]["o200k_base"]
    cands = summary["candidates"]
    users = json.loads((RESULTS / "profile.json").read_text())["users"]
    per_m = 1e6 / new_tokens
    report = {
        "sample_size": n,
        "accepted": k,
        "acceptance_rate": round(k / n, 3) if n else None,
        "acceptance_rate_95ci_wilson": [round(lo, 3), round(hi, 3)],
        "candidates_total": cands,
        "estimated_verifiable_episodes_total": [round(cands * lo), round(cands * k / n), round(cands * hi)],
        "estimated_per_mailbox_mean": [round(cands * lo / users, 1), round(cands * k / n / users, 1), round(cands * hi / users, 1)],
        "estimated_per_million_new_text_tokens": [round(cands * lo * per_m, 2), round(cands * k / n * per_m, 2), round(cands * hi * per_m, 2)],
        "strict_accepted": k_strict,
        "strict_acceptance_rate_95ci_wilson": [round(slo, 3), round(shi, 3)],
        "strict_estimated_verifiable_episodes_total": [round(cands * slo), round(cands * k_strict / n), round(cands * shi)],
        "note": "Episodes are thread-level task seeds (one thread can yield more than one cut). Estimates are [low, point, high] from the 95% Wilson interval of a random sample labelled by a separate Claude session; candidates are counted per mailbox, so a thread copied into several mailboxes counts more than once; the miner's recall (good threads it misses) is not measured.",
    }
    write_json(RESULTS / "yield.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    {"sample": sample, "estimate": estimate}[sys.argv[1]]()
