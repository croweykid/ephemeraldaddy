"""Type 1 CSV import formats, validation, placeholder records and retry reports.

No Qt dependencies: parsing and retry-file behavior can be tested without a GUI.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from types import SimpleNamespace

from .parsing import normalize_csv_row, parse_datetime_value


@dataclass(frozen=True)
class Type1Record:
    name: str
    date_text: str
    birth_place: str
    notes: str
    alias: str
    builder_row: list[str]
    latitude: str = ""
    longitude: str = ""


def is_header(row: list[str]) -> bool:
    """Recognize plain, exported, and previous failed-import headers."""
    fields = {field.strip().casefold() for field in row}
    first = row[0].strip().casefold() if row else ""
    return (
        first == "column_1"
        or ("name" in fields and bool(fields & {
            "datetime_iso", "birth_date", "birth_datetime",
            "birth place", "birth_place", "date", "birthdate", "notes",
        }))
        or (first == "id" and "name" in fields)
    )


def parse_record(row: list[str], header: list[str] | None = None) -> Type1Record:
    """Accept name/date/place[/notes/alias] or legacy ID-first exports."""
    values = normalize_csv_row(row)
    keys = [key.strip().casefold() for key in header] if header else []
    known = bool(keys) and not keys[0].startswith("column_")

    def field(*names: str) -> str:
        for name in names:
            if name in keys:
                i = keys.index(name)
                return values[i] if i < len(values) else ""
        return ""

    if known:
        name = field("name", "full name")
        date_text = field("datetime_iso", "birth_datetime", "birth_date", "birthdate", "date")
        place = field("birth_place", "birth place", "place", "birthplace")
        notes = field("notes", "comments", "subjective_notes", "subjective notes")
        alias = field("alias")
        lat = field("latitude", "lat")
        lon = field("longitude", "lon")
        if "id" in keys or lat or lon or field("tz_name"):
            builder = [
                "0", name, place, date_text, field("tz_name"), lat, lon,
                field("used_utc_fallback"), field("sentiments"),
                field("relationship_types"), notes, "", "", "", "",
                field("chart_type"), field("source"),
            ]
        else:
            builder = [name, date_text, place]
    elif values and values[0].isdigit():
        name = values[1] if len(values) > 1 else ""
        place = values[2] if len(values) > 2 else ""
        date_text = values[3] if len(values) > 3 else ""
        lat = values[5] if len(values) > 5 else ""
        lon = values[6] if len(values) > 6 else ""
        # Legacy positions 10-14 are numeric metrics/weights, not comments.
        notes = ""
        alias = ""
        builder = values[:17]
    else:
        name = values[0] if values else ""
        date_text = values[1] if len(values) > 1 else ""
        place = values[2] if len(values) > 2 else ""
        notes = values[3] if len(values) > 3 and (not keys or len(keys) > 3 and keys[3] == "column_4") else ""
        alias = values[4] if len(values) > 4 and (not keys or len(keys) > 4 and keys[4] == "column_5") else ""
        lat = lon = ""
        builder = [name, date_text, place]
    return Type1Record(name.strip(), date_text.strip(), place.strip(),
                       notes.strip(), alias.strip(), builder, lat.strip(), lon.strip())


def validate_calculable_record(record: Type1Record, min_year: int, max_year: int) -> None:
    if not record.name:
        raise ValueError("Missing chart name.")
    parsed, _ = parse_datetime_value(record.date_text)
    if parsed is None:
        raise ValueError("Missing or unrecognized birth date; use YYYY-MM-DD or YYYY-MM-DD HH:MM.")
    if not min_year <= parsed.year <= max_year:
        raise ValueError(f"Birth year {parsed.year} is outside {min_year}–{max_year}.")
    if not record.birth_place and not (record.latitude and record.longitude):
        raise ValueError("Birthplace or both latitude and longitude are required.")
    if bool(record.latitude) != bool(record.longitude):
        raise ValueError("Both latitude and longitude must be present together.")
    if record.latitude:
        try:
            lat, lon = float(record.latitude), float(record.longitude)
        except ValueError as exc:
            raise ValueError("Invalid geographic coordinates.") from exc
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Latitude/longitude are outside geographic bounds.")


def partial_birth_date(text: str) -> tuple[int | None, int | None, int | None]:
    """Keep any recognizable partial dates, without requiring a valid natal chart."""
    parsed, _ = parse_datetime_value(text)
    if parsed:
        return parsed.month, parsed.day, parsed.year
    raw = text.strip()
    match = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", raw)
    if match:
        year = int(match.group(1))
        month = int(match.group(2)) if match.group(2) else None
        day = int(match.group(3)) if match.group(3) else None
        return (month if month is not None and 1 <= month <= 12 else None,
                day if day is not None and 1 <= day <= 31 else None, year)
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if match:
        month, day, year = (int(value) for value in match.groups())
        return (month if 1 <= month <= 12 else None,
                day if 1 <= day <= 31 else None, year)
    return None, None, None


def build_placeholder(record: Type1Record, chart_type: str) -> SimpleNamespace:
    """Store metadata without running Chart/ephemeris/geocoding."""
    if not record.name:
        raise ValueError("Missing chart name.")
    month, day, year = partial_birth_date(record.date_text)
    comments = record.notes
    if record.date_text:
        comments = (comments + "\n" if comments else "") + "Imported birth date (unverified): " + record.date_text
    return SimpleNamespace(
        name=record.name,
        alias=record.alias or None,
        birth_place=record.birth_place,
        dt=datetime(1990, 1, 1, 12, tzinfo=timezone.utc),
        lat=0.0, lon=0.0,
        birthtime_unknown=True,
        used_utc_fallback=False,
        is_placeholder=True,
        chart_type=chart_type,
        source=chart_type,
        birth_month=month, birth_day=day, birth_year=year,
        comments=comments,
        positions={}, retrogrades={}, houses=[], aspects=[],
        dominant_sign_weights={}, dominant_planet_weights={},
        dominant_nakshatra_weights={}, modal_distribution={},
        sentiments=[], relationship_types=[],
    )


def failure_report_path(source_path: str | Path) -> Path:
    source = Path(source_path)
    return source.with_name(f"{source.stem}_import_failures.csv")


def write_failures(
    source_path: str | Path,
    failures: list[tuple[int, list[str], str]],
    header: list[str] | None,
) -> Path | None:
    """Preserve source fields in source order; metadata columns can be stripped on retry."""
    if not failures:
        return None
    path = failure_report_path(source_path)
    # Avoid overwritten retry exports or overwriting the source CSV itself.
    if path == Path(source_path):
        raise ValueError("Failure report path conflicts with source CSV.")
    width = max(len(header or []), *(len(row) for _, row, _ in failures))
    original_header = header or [f"column_{i + 1}" for i in range(width)]
    # Existing retry diagnostics are replaced, not endlessly appended.
    original_header = [key for key in original_header if key not in {"import_error", "source_row"}]
    width = len(original_header)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(original_header + ["import_error", "source_row"])
        for line, row, reason in failures:
            writer.writerow(row[:width] + [""] * max(0, width - len(row)) + [reason, line])
    return path
