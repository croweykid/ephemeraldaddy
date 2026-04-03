from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.db import parse_relationship_types, parse_sentiments
from ephemeraldaddy.gui.features.charts.provenance import (
    SOURCE_PERSONAL,
    normalize_gui_source,
)
from ephemeraldaddy.io.geocode import geocode_location

from .parsing import parse_datetime_value, trim_import_row


def build_import_chart(
    row: list[str],
    geocode_cache: dict[str, tuple[float, float, str]] | None = None,
) -> tuple[Chart, str | None, bool]:
    """Build a Chart from a generic import row.

    Returns (chart, birth_place, used_utc_fallback).
    """
    force_utc_fallback = False

    lower_row = [cell.lower() for cell in row]
    if "datetime_iso" in lower_row and "latitude" in lower_row:
        raise ValueError("header row")

    row = trim_import_row(row)
    name = ""
    if row:
        if row[0].isdigit():
            if len(row) > 1:
                name = row[1].strip()
        else:
            name = row[0].strip()

    birth_place = None
    lat = lon = None
    tz_override = None
    dt_value = None
    time_missing = True

    sentiments: list[str] = []
    relationship_types: list[str] = []
    comments = ""
    if row and row[0].isdigit():
        if len(row) > 2:
            birth_place = row[2] or None
        dt_value, time_missing = parse_datetime_value(row[3] if len(row) > 3 else "")
        tz_name = row[4].strip() if len(row) > 4 else ""
        if tz_name:
            try:
                tz_override = ZoneInfo(tz_name)
            except Exception:
                tz_override = None
        try:
            lat = float(row[5]) if len(row) > 5 else None
            lon = float(row[6]) if len(row) > 6 else None
        except Exception:
            lat, lon = None, None
        if len(row) > 7 and row[7].strip():
            try:
                if bool(int(row[7])):
                    force_utc_fallback = True
            except Exception:
                pass
            sentiments = parse_sentiments(row[8]) if len(row) > 8 else []
            relationship_types = (
                parse_relationship_types(row[9]) if len(row) > 9 else []
            )
            chart_type_value = row[15].strip() if len(row) > 15 else ""
            legacy_source_value = row[16].strip() if len(row) > 16 else ""
            source = normalize_gui_source(
                chart_type_value or legacy_source_value or SOURCE_PERSONAL
            )
            comments = row[10] if len(row) > 10 else ""
    else:
        if len(row) >= 3:
            dt_value, time_missing = parse_datetime_value(row[1])
            birth_place = row[2].strip() or None
        else:
            dt_value, time_missing = parse_datetime_value(row[1] if len(row) > 1 else "")
            birth_place = None

        if birth_place:
            cached = None
            if geocode_cache is not None:
                cached = geocode_cache.get(birth_place)
            if cached:
                lat, lon, _label = cached
            else:
                try:
                    lat, lon, _label = geocode_location(birth_place)
                    if geocode_cache is not None:
                        geocode_cache[birth_place] = (lat, lon, _label)
                except Exception:
                    lat, lon = None, None
        else:
            lat, lon = None, None

    if dt_value is None:
        force_utc_fallback = True
        dt_value = datetime.datetime(1990, 1, 1, 12, 0)

    if lat is None or lon is None:
        force_utc_fallback = True
        lat, lon = 0.0, 0.0

    if force_utc_fallback:
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
    elif time_missing and dt_value is not None:
        # Keep the resolved timezone path for date-only imports so lunar motion
        # is not shifted by forcing an arbitrary UTC conversion.
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            dt_value = dt_value.astimezone(dt_value.tzinfo).replace(
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            )

    source = SOURCE_PERSONAL if "source" not in locals() else source
    chart = Chart(name, dt_value, lat, lon, tz=tz_override)
    chart.birth_place = birth_place
    chart.sentiments = sentiments
    chart.relationship_types = relationship_types
    chart.source = source
    chart.comments = comments
    chart.used_utc_fallback = force_utc_fallback or getattr(chart, "used_utc_fallback", False)
    chart.birthtime_unknown = bool(time_missing)
    return chart, birth_place, chart.used_utc_fallback
