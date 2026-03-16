from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.io.geocode import geocode_location

from .parsing import parse_datetime_value


def timezone_to_birth_place(tz_value: str) -> str | None:
    """Best-effort conversion of IANA timezone labels to a town-like value."""
    normalized = (tz_value or "").strip()
    if not normalized:
        return None
    first_entry = normalized.split(",", 1)[0].strip()
    if not first_entry:
        return None
    segments = [segment for segment in first_entry.split("/") if segment]
    if not segments:
        return None
    town_segment = segments[-1]
    return town_segment.replace("_", " ").strip() or None


def build_pattern_import_chart(
    row: list[str],
    *,
    column_index_map: dict[str, int],
    geocode_cache: dict[str, tuple[float, float, str]] | None = None,
) -> tuple[Chart, str | None, bool]:
    """Build a Chart from "Import CSV from The Pattern" rows."""

    def _value(column: str) -> str:
        idx = column_index_map.get(column, -1)
        if idx < 0 or idx >= len(row):
            return ""
        return row[idx].strip()

    name = _value("full name")
    date_text = _value("birthday")
    time_text = _value("birth time")
    gender_text = _value("gender")
    timezone_text = _value("birthtimezone")

    used_fallback = False
    birth_place = timezone_to_birth_place(timezone_text)
    dt_text = date_text if not time_text else f"{date_text} {time_text}"
    dt_value, time_missing = parse_datetime_value(dt_text)

    if time_text.casefold() == "unknown":
        dt_value, time_missing = parse_datetime_value(date_text)
        time_missing = True

    tz_override = None
    if timezone_text:
        try:
            tz_override = ZoneInfo(timezone_text)
        except Exception:
            used_fallback = True

    lat = lon = None
    if birth_place:
        cached = geocode_cache.get(birth_place) if geocode_cache is not None else None
        if cached:
            lat, lon, _label = cached
        else:
            try:
                lat, lon, _label = geocode_location(birth_place)
                if geocode_cache is not None:
                    geocode_cache[birth_place] = (lat, lon, _label)
            except Exception:
                used_fallback = True
    else:
        used_fallback = True

    if dt_value is None:
        used_fallback = True
        dt_value = datetime.datetime(1990, 1, 1, 12, 0)

    if lat is None or lon is None:
        used_fallback = True
        lat, lon = 0.0, 0.0

    if time_missing:
        used_fallback = True

    if used_fallback:
        base_date = dt_value.date() if dt_value else datetime.date.today()
        dt_value = datetime.datetime(
            base_date.year,
            base_date.month,
            base_date.day,
            12,
            0,
            tzinfo=ZoneInfo("UTC"),
        )
        tz_override = ZoneInfo("UTC")

    chart = Chart(name, dt_value, lat, lon, tz=tz_override)
    chart.birth_place = birth_place
    normalized_gender = gender_text.strip().casefold()
    if normalized_gender == "unknown" or not normalized_gender:
        chart.gender = None
    elif normalized_gender == "f":
        chart.gender = "F"
    elif normalized_gender == "m":
        chart.gender = "M"
    else:
        chart.gender = gender_text.strip()
    chart.used_utc_fallback = used_fallback or getattr(chart, "used_utc_fallback", False)
    chart.birthtime_unknown = bool(time_missing)
    return chart, birth_place, chart.used_utc_fallback
