import json
import math
import re
from pathlib import Path

MAX_ANSWER_BYTES = 65536
MAX_CITATIONS = 5
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TIME_RE = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def load_answer(path):
    path = Path(path)
    if not path.exists() or path.is_symlink() or not path.is_file():
        return None
    if path.stat().st_size > MAX_ANSWER_BYTES:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def schema_ok(answer, expected):
    if answer is None:
        return False
    required = set(expected["fields"]) | {"evidence_message_ids"}
    return required.issubset(answer)


def field_ok(answer, expected, name):
    if answer is None:
        return False
    spec = expected["fields"][name]
    value = answer.get(name)
    kind = spec["type"]
    if kind == "date":
        return isinstance(value, str) and DATE_RE.fullmatch(value) is not None and value == spec["value"]
    if kind == "time":
        return isinstance(value, str) and TIME_RE.fullmatch(value) is not None and value == spec["value"]
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool) and value == spec["value"]
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
        return abs(value - spec["value"]) <= spec.get("tolerance", 0.0)
    return False


def citations_ok(answer, expected, clusters):
    if answer is None:
        return False
    ids = answer.get("evidence_message_ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_CITATIONS:
        return False
    if not all(isinstance(i, str) and i.strip() in clusters for i in ids):
        return False
    decisive = set(expected["decisive_clusters"])
    return any(clusters[i.strip()] in decisive for i in ids)


def grade(answer, expected, clusters):
    results = {"schema": schema_ok(answer, expected)}
    for name in sorted(expected["fields"]):
        results[name] = field_ok(answer, expected, name)
    results["citations"] = citations_ok(answer, expected, clusters)
    results["reward"] = int(all(results.values()))
    return results
