import os
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor

import tiktoken

from pipeline.common import DATA, DERIVED, MAILDIR, RESULTS, iter_jsonl, write_json

os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(DATA / "tiktoken"))
ENCODINGS = ("o200k_base", "cl100k_base")
_enc = {}


def _init():
    for name in ENCODINGS:
        _enc[name] = tiktoken.get_encoding(name)


def _count_texts(texts):
    out = []
    for text in texts:
        out.append(tuple(len(_enc[name].encode_ordinary(text)) for name in ENCODINGS) + (len(text),))
    return out


def _count_files(paths):
    texts = []
    for rel in paths:
        with open(MAILDIR / rel, "rb") as fh:
            texts.append(fh.read().decode("latin-1"))
    return _count_texts(texts)


def _batches(items, size=2000):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _bounded_map(pool, fn, batches, in_flight=16):
    pending = deque()
    for batch in batches:
        pending.append(pool.submit(fn, batch))
        if len(pending) >= in_flight:
            yield pending.popleft().result()
    while pending:
        yield pending.popleft().result()


def _total(pool, fn, batches):
    totals = [0] * (len(ENCODINGS) + 1)
    per_item = []
    for result in _bounded_map(pool, fn, batches):
        for counts in result:
            per_item.append(counts)
            for i, value in enumerate(counts):
                totals[i] += value
    level = {name: totals[i] for i, name in enumerate(ENCODINGS)}
    level["chars"] = totals[-1]
    return level, per_item


def main():
    _init()
    index = list(iter_jsonl(DERIVED / "index.jsonl.gz"))
    with ProcessPoolExecutor(initializer=_init) as pool:
        raw_files, _ = _total(pool, _count_files, _batches(r["path"] for r in index))
        raw_bodies, body_counts = _total(pool, _count_texts, _batches(r["body"] for r in iter_jsonl(DERIVED / "messages.jsonl.gz")))
        unique = {name: 0 for name in ENCODINGS}
        unique["chars"] = 0
        for row, counts in zip(index, body_counts):
            if row["rep"]:
                for i, name in enumerate(ENCODINGS):
                    unique[name] += counts[i]
                unique["chars"] += counts[-1]
        new_rows = list(iter_jsonl(DERIVED / "newtext.jsonl.gz"))
        new_text, new_counts = _total(pool, _count_texts, _batches(r["new_text"] for r in new_rows))
    cluster_tokens = {row["cluster"]: counts[0] for row, counts in zip(new_rows, new_counts)}
    per_user = defaultdict(lambda: {"files": 0, "raw_body_tokens": 0, "clusters": set()})
    for row, counts in zip(index, body_counts):
        u = per_user[row["user"]]
        u["files"] += 1
        u["raw_body_tokens"] += counts[0]
        u["clusters"].add(row["cluster"])
    users = {}
    for name, u in sorted(per_user.items()):
        users[name] = {
            "files": u["files"],
            "raw_body_tokens_o200k": u["raw_body_tokens"],
            "unique_messages": len(u["clusters"]),
            "new_text_tokens_o200k": sum(cluster_tokens.get(c, 0) for c in u["clusters"]),
        }
    write_json(DERIVED / "cluster_tokens.json", cluster_tokens)
    report = {
        "tokenizer_note": "Estimated with OpenAI tiktoken encodings; other tokenizers (including Claude's) give different absolute numbers. The ratios between levels are the finding.",
        "levels": {
            "1_raw_files_with_headers": raw_files,
            "2_raw_bodies": raw_bodies,
            "3_unique_bodies": unique,
            "4_new_text": new_text,
        },
        "ratios_o200k": {
            "unique_over_raw_bodies": round(unique["o200k_base"] / raw_bodies["o200k_base"], 4),
            "new_text_over_raw_bodies": round(new_text["o200k_base"] / raw_bodies["o200k_base"], 4),
            "new_text_over_raw_files": round(new_text["o200k_base"] / raw_files["o200k_base"], 4),
        },
    }
    write_json(RESULTS / "tokens.json", report)
    write_json(RESULTS / "tokens_per_mailbox.json", users)
    for key, value in report["levels"].items():
        print(key, value)
    print(report["ratios_o200k"])


if __name__ == "__main__":
    main()
