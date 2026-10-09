import email
import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from pathlib import Path

DATA = Path(os.environ.get("ENRON_DATA", "~/enron-data")).expanduser()
MAILDIR = DATA / "raw" / "maildir"
DERIVED = DATA / "derived"
REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"

DATE_MIN = datetime(1998, 1, 1, tzinfo=timezone.utc)
DATE_MAX = datetime(2002, 12, 31, tzinfo=timezone.utc)

_SUBJECT_PREFIX = re.compile(r"^\s*((re|fw|fwd)\s*(\[\d+\])?\s*:\s*)+", re.IGNORECASE)
_WS = re.compile(r"\s+")


def parse_date(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None or dt.tzinfo is None:
        return None
    dt = dt.astimezone(timezone.utc)
    if dt < DATE_MIN or dt > DATE_MAX:
        return None
    return dt


def tz_offset(raw):
    m = re.search(r"([+-]\d{4})", raw or "")
    return m.group(1) if m else None


def norm_subject(subject):
    s = _SUBJECT_PREFIX.sub("", subject or "")
    return _WS.sub(" ", s).strip().lower()


def norm_addr(value):
    return parseaddr(value or "")[1].strip().lower()


def collapse(text):
    return _WS.sub(" ", text or "").strip()


def sha1(text):
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()


def body_text(msg):
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_maintype() == "text":
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode("latin-1"))
        return "\n".join(parts)
    payload = msg.get_payload(decode=True)
    if payload is None:
        payload = (msg.get_payload() or "").encode("latin-1", "replace")
    return payload.decode("latin-1")


def read_message(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    msg = email.message_from_bytes(raw)

    def h(name):
        value = msg.get(name)
        return "" if value is None else str(value)

    rel = Path(path).relative_to(MAILDIR)
    date_raw = h("Date")
    dt = parse_date(date_raw)
    return {
        "path": str(rel),
        "user": rel.parts[0],
        "folder": "/".join(rel.parts[1:-1]),
        "message_id": h("Message-ID").strip(),
        "date_raw": date_raw,
        "date_utc": dt.isoformat() if dt else None,
        "tz": tz_offset(date_raw),
        "from": h("From"),
        "to": h("To"),
        "cc": h("Cc"),
        "subject": h("Subject"),
        "x_from": h("X-From"),
        "x_to": h("X-To"),
        "raw_chars": len(raw),
        "body": body_text(msg),
    }


def cluster_key(rec, with_date=True):
    minute = (rec["date_utc"] or "")[:16] if with_date else ""
    parts = [norm_addr(rec["from"]), norm_subject(rec["subject"]), minute, sha1(collapse(rec["body"]))]
    return sha1("|".join(parts))


def iter_jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
