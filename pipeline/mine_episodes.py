import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

from pipeline.common import DERIVED, RESULTS, iter_jsonl, write_json

TIME_RE = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?\s*m\b\.?", re.IGNORECASE)
DAY_RE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow)\b", re.IGNORECASE)
VOLUME_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d{3,6})\s*(?:mmbtu|mmbtus|dth|/d\b|/day|per day|a day)", re.IGNORECASE)
PRICE_RE = re.compile(r"\$\s?(\d{1,2}\.\d{2,4})\b")
MEETING_WORDS = re.compile(r"\b(meet(?:ing)?|call|lunch|dinner|interview|presentation|conference)\b", re.IGNORECASE)
CHANGE_WORDS = re.compile(
    r"\b(reschedul\w*|postpone\w*|move(?:d)? (?:it |the \w+ )?to|push(?:ed)? (?:it )?back|instead of|change(?:d)? (?:the )?(?:time|date|volume|price)|revis\w+|correct(?:ed|ion)|now be|cancel\w*)\b",
    re.IGNORECASE,
)
DEAL_WORDS = re.compile(r"\b(deal|ticket|nomination|nom|volume|mmbtu|dth|price|nymex|index|counterparty|confirm\w*)\b", re.IGNORECASE)

MIN_MESSAGES = 3
MAX_SPAN_DAYS = 45


def norm_time(m):
    hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
    return f"{hour:02d}:{m.group(2) or '00'}"


def main():
    new_text = {row["cluster"]: row["new_text"] for row in iter_jsonl(DERIVED / "newtext.jsonl.gz")}
    threads = defaultdict(dict)
    for row in iter_jsonl(DERIVED / "index.jsonl.gz"):
        if not row["date_utc"] or not row["subject"] or len(row["subject"]) < 4:
            continue
        key = (row["user"], row["subject"])
        if row["cluster"] not in threads[key]:
            threads[key][row["cluster"]] = row
    candidates = []
    per_user = Counter()
    for (user, subject), msgs in threads.items():
        if len(msgs) < MIN_MESSAGES:
            continue
        rows = sorted(msgs.values(), key=lambda r: r["date_utc"])
        first = datetime.fromisoformat(rows[0]["date_utc"])
        last = datetime.fromisoformat(rows[-1]["date_utc"])
        if (last - first).days > MAX_SPAN_DAYS:
            continue
        senders = {r["from"] for r in rows}
        if len(senders) < 2:
            continue
        texts = [new_text.get(r["cluster"], "") for r in rows]
        joined = "\n".join(texts) + "\n" + subject
        times = {norm_time(m) for t in texts for m in TIME_RE.finditer(t)}
        volumes = {m.group(1).replace(",", "") for t in texts for m in VOLUME_RE.finditer(t)}
        prices = {m.group(1) for t in texts for m in PRICE_RE.finditer(t)}
        change = len(CHANGE_WORDS.findall(joined))
        kind = None
        if MEETING_WORDS.search(joined) and len(times) >= 2 and DAY_RE.search(joined) and change:
            kind = "meeting"
        elif DEAL_WORDS.search(joined) and (len(volumes) >= 2 or len(prices) >= 2) and change:
            kind = "deal"
        if not kind:
            continue
        score = change + len(times if kind == "meeting" else volumes | prices) + min(len(rows), 8)
        per_user[user] += 1
        candidates.append(
            {
                "user": user,
                "subject": subject,
                "kind": kind,
                "score": score,
                "messages": len(rows),
                "senders": len(senders),
                "first_utc": rows[0]["date_utc"],
                "last_utc": rows[-1]["date_utc"],
                "distinct_times": sorted(times),
                "distinct_volumes": sorted(volumes),
                "distinct_prices": sorted(prices),
                "paths": [r["path"] for r in rows],
            }
        )
    candidates.sort(key=lambda c: (-c["score"], c["user"], c["subject"]))
    with gzip.open(DERIVED / "candidates.jsonl.gz", "wt", encoding="utf-8") as fh:
        for c in candidates:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    kinds = Counter(c["kind"] for c in candidates)
    summary = {
        "threads_considered": len(threads),
        "candidates": len(candidates),
        "by_kind": dict(kinds),
        "mailboxes_with_candidates": len(per_user),
        "rules": {"min_unique_messages": MIN_MESSAGES, "max_span_days": MAX_SPAN_DAYS, "min_senders": 2},
    }
    write_json(RESULTS / "candidates_summary.json", summary)
    write_json(DERIVED / "candidates_per_mailbox.json", dict(per_user))
    print(summary)


if __name__ == "__main__":
    main()
