import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.common import DERIVED, iter_jsonl
from pipeline.strip_quotes import strip_quoted

HOUSTON = ZoneInfo("America/Chicago")


def render(msgs, limit):
    out = []
    for i, m in enumerate(msgs, 1):
        d = datetime.fromisoformat(m["date_utc"])
        text, _ = strip_quoted(m["body"])
        text = text.strip()
        if limit and len(text) > limit:
            text = text[:limit] + " [...]"
        out.append(
            f"--- [{i}] {d:%Y-%m-%d %H:%M} UTC | {d.astimezone(HOUSTON):%a %Y-%m-%d %H:%M} Houston\n"
            f"path: {m['path']}\nmessage-id: {m['message_id']}\nfrom: {m['x_from'] or m['from']}\nto: {(m['x_to'] or m['to'])[:200]}\n"
            f"subject: {m['subject']}\n\n{text}\n"
        )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="*")
    ap.add_argument("--candidate", type=int, help="index into derived/candidates.jsonl.gz")
    ap.add_argument("--limit", type=int, default=1500)
    args = ap.parse_args()
    paths = set(args.paths or [])
    if args.candidate is not None:
        for i, c in enumerate(iter_jsonl(DERIVED / "candidates.jsonl.gz")):
            if i == args.candidate:
                paths = set(c["paths"])
                print(json.dumps({k: c[k] for k in c if k != "paths"}))
                break
    msgs = [r for r in iter_jsonl(DERIVED / "messages.jsonl.gz") if r["path"] in paths]
    msgs.sort(key=lambda r: r["date_utc"] or "")
    seen = set()
    unique = []
    for m in msgs:
        key = (m["date_utc"], m["subject"], m["body"][:200])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    print(render(unique, args.limit))


if __name__ == "__main__":
    main()
