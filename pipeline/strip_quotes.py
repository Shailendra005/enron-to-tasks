import gzip
import json
import re
import sys
from collections import Counter

from pipeline.common import DERIVED, RESULTS, collapse, iter_jsonl, sha1, write_json

RULES = [
    ("original_message", re.compile(r"^[ \t>]*-{2,}\s*Original Message\s*-{2,}", re.IGNORECASE | re.MULTILINE)),
    ("original_appointment", re.compile(r"^[ \t>]*-{2,}\s*Original Appointment\s*-{2,}", re.IGNORECASE | re.MULTILINE)),
    ("forwarded_by", re.compile(r"^[ \t>]*-{5,}\s*Forwarded by .* on", re.IGNORECASE | re.MULTILINE)),
    ("outlook_header", re.compile(r"^[ \t>]*From:.*\n(?:.*\n){0,2}?[ \t>]*Sent:", re.MULTILINE)),
    (
        "notes_header",
        re.compile(
            r"^.*\b\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM).*\n(?:.*\n){0,2}?[ \t]*To:",
            re.MULTILINE,
        ),
    ),
]

BOILERPLATE_MIN = 50
_PARA_SPLIT = re.compile(r"\n\s*\n")


def strip_quoted(body):
    cut = len(body)
    fired = None
    for name, pattern in RULES:
        m = pattern.search(body)
        if m and m.start() < cut:
            cut = m.start()
            fired = name
    kept = [line for line in body[:cut].splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(kept), fired


def paragraphs(text):
    return [p for p in (collapse(x) for x in _PARA_SPLIT.split(text)) if p]


def main():
    reps = []
    para_counts = Counter()
    rule_counts = Counter()
    index = iter_jsonl(DERIVED / "index.jsonl.gz")
    for rec, row in zip(iter_jsonl(DERIVED / "messages.jsonl.gz"), index):
        if row["path"] != rec["path"]:
            sys.exit("index and messages out of order")
        if not row["rep"]:
            continue
        text, fired = strip_quoted(rec["body"])
        rule_counts[fired or "none"] += 1
        for p in set(paragraphs(text)):
            para_counts[sha1(p)] += 1
        reps.append((row["path"], row["cluster"], text, fired))
    boiler = {h for h, n in para_counts.items() if n >= BOILERPLATE_MIN}
    removed = 0
    out_path = DERIVED / "newtext.jsonl.gz"
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        for path, cluster, text, fired in reps:
            kept = []
            for p in _PARA_SPLIT.split(text):
                if collapse(p) and sha1(collapse(p)) in boiler:
                    removed += 1
                    continue
                kept.append(p)
            new_text = "\n\n".join(kept).strip()
            fh.write(json.dumps({"path": path, "cluster": cluster, "rule": fired, "new_text": new_text}, ensure_ascii=False) + "\n")
    stats = {
        "unique_messages": len(reps),
        "quote_rule_fired": dict(rule_counts.most_common()),
        "boilerplate_paragraph_patterns": len(boiler),
        "boilerplate_paragraphs_removed": removed,
        "boilerplate_min_repeats": BOILERPLATE_MIN,
    }
    write_json(RESULTS / "strip.json", stats)
    for key, value in stats.items():
        print(key, value)


if __name__ == "__main__":
    main()
