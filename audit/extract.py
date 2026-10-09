import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HOUSTON = ZoneInfo("America/Chicago")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

TIME_RE = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?\s*m\b\.?", re.IGNORECASE)
NOON_RE = re.compile(r"\bnoon\b", re.IGNORECASE)
MONTH_DAY_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE)
SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
WEEKDAY_RE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow)\b", re.IGNORECASE)
VOLUME_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d{3,6})\s*(?:mmbtu|mmbtus|dth|/d\b|/day|per day|a day)", re.IGNORECASE)
PRICE_RE = re.compile(r"\$\s?(\d{1,2}\.\d{2,4})\b")


def local_day(sent_utc):
    return datetime.fromisoformat(sent_utc).astimezone(HOUSTON).date()


def times(text):
    out = []
    for m in TIME_RE.finditer(text):
        hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
        out.append((m.start(), f"{hour:02d}:{m.group(2) or '00'}"))
    for m in NOON_RE.finditer(text):
        out.append((m.start(), "12:00"))
    return [v for _, v in sorted(out)]


def dates(text, sent_utc):
    base = local_day(sent_utc)
    out = []
    for m in MONTH_DAY_RE.finditer(text):
        try:
            out.append((m.start(), date(base.year, MONTHS[m.group(1).lower()[:3]], int(m.group(2)))))
        except ValueError:
            pass
    for m in SLASH_RE.finditer(text):
        month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
        y = base.year if not year else (int(year) + 2000 if len(year) == 2 else int(year))
        try:
            out.append((m.start(), date(y, month, day)))
        except ValueError:
            pass
    for m in WEEKDAY_RE.finditer(text):
        word = m.group(1).lower()
        if word == "tomorrow":
            out.append((m.start(), base + timedelta(days=1)))
        else:
            ahead = (WEEKDAYS.index(word) - base.weekday()) % 7
            out.append((m.start(), base + timedelta(days=ahead)))
    return [d.isoformat() for _, d in sorted(out)]


def volumes(text):
    return [int(m.group(1).replace(",", "")) for m in VOLUME_RE.finditer(text)]


def prices(text):
    return [float(m.group(1)) for m in PRICE_RE.finditer(text)]


def values_for(field_type, field_name, text, sent_utc):
    if field_type == "time":
        return times(text)
    if field_type == "date":
        return dates(text, sent_utc)
    if field_type == "int":
        return volumes(text)
    if field_type == "number":
        return prices(text)
    return []
