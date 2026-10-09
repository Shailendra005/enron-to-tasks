import gzip
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

from pipeline.common import DERIVED, MAILDIR, read_message


def list_files():
    out = []
    for root, _dirs, files in os.walk(MAILDIR):
        for name in files:
            out.append(os.path.join(root, name))
    out.sort()
    return out


def _safe_read(path):
    try:
        return read_message(path)
    except Exception as exc:
        return {"path": path, "error": repr(exc)}


def main():
    files = list_files()
    DERIVED.mkdir(parents=True, exist_ok=True)
    out_path = DERIVED / "messages.jsonl.gz"
    errors = 0
    with gzip.open(out_path, "wt", encoding="utf-8") as fh, ProcessPoolExecutor() as pool:
        for rec in pool.map(_safe_read, files, chunksize=500):
            if "error" in rec:
                errors += 1
                continue
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"files={len(files)} parsed={len(files) - errors} errors={errors} -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
