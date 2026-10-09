import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.common import DERIVED, iter_jsonl
from pipeline.strip_quotes import strip_quoted

SEED = 7
N = 20


def main():
    reps = {r["path"] for r in iter_jsonl(DERIVED / "index.jsonl.gz") if r["rep"]}
    rng = random.Random(SEED)
    pool = []
    for rec in iter_jsonl(DERIVED / "messages.jsonl.gz"):
        if rec["path"] in reps and len(rec["body"]) > 200:
            pool.append(rec)
    for i, rec in enumerate(rng.sample(pool, N), 1):
        kept, rule = strip_quoted(rec["body"])
        cut = len(kept)
        body = rec["body"]
        print(f"=== {i} {rec['path']} rule={rule} kept={len(kept)} of {len(body)}")
        print("KEPT_TAIL:", repr(kept.strip()[-160:]))
        rest = body[len(body) if rule is None else body.find(kept[-40:]) + 40 if kept.strip() else 0:]
        print("CUT_HEAD:", repr(rest.strip()[:200]) if rule else "(nothing cut)")


if __name__ == "__main__":
    main()
