from __future__ import annotations

import datetime
import re


def normalize_csv_row(row: list[str]) -> list[str]:
    """Normalize a raw CSV row from comma/tab sources into stripped cells."""
    if len(row) == 1 and "\t" in row[0]:
        row = row[0].split("\t")
    return [cell.strip() for cell in row]


def trim_import_row(row: list[str]) -> list[str]:
    """Trim row shape for legacy exports with optional numeric id column."""
    if row and row[0].isdigit():
        return row[:15]
    return row[:3]


def parse_sentiment_metric_value(value: str) -> int | None:
    """Parse numeric sentiment values from import rows."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith("{") or value.startswith("["):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if 1 <= parsed <= 10:
        return parsed
    return None


def parse_datetime_value(value: str) -> tuple[datetime.datetime | None, bool]:
    """Parse a datetime string. Returns (datetime_or_none, time_missing)."""
    if not value:
        return None, True

    try:
        dt = datetime.datetime.fromisoformat(value)
        if dt.tzinfo is None and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            if "T" not in value and ":" not in value:
                return dt, True
        return dt, False
    except ValueError:
        pass

    normalized = re.sub(r"\s+", " ", value.strip())
    formats = [
        "%A %B %d %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%B %d %Y",
        "%b %d %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(normalized, fmt)
            time_missing = "%H" not in fmt and "%I" not in fmt
            return dt, time_missing
        except ValueError:
            continue
    return None, True


def format_chart_row_datetime(
    dt_value: str | None,
    *,
    birthtime_unknown: bool = False,
) -> tuple[str, str]:
    """Display-safe chart row datetime formatter."""
    if not dt_value:
        return "??.??.????", "??:??"

    parsed_dt, time_missing = parse_datetime_value(dt_value)
    if parsed_dt is None:
        return "??.??.????", "??:??"

    date_label = parsed_dt.strftime("%m.%d.%Y")
    if birthtime_unknown:
        time_label = "unknown"
    else:
        time_label = "??:??" if time_missing else parsed_dt.strftime("%H:%M")
    return date_label, time_label
