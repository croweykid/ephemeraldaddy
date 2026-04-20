"""Personal-transit popout helpers to keep app.py lightweight."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    assign_houses,
    compute_aspects,
    normalize_chart,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location
from ephemeraldaddy.gui.style import format_chart_header


class PersonalTransitLocationError(ValueError):
    """Raised when a personal-transit location cannot be resolved."""


@dataclass(frozen=True)
class PersonalTransitRecalculationResult:
    transit_chart: Chart
    transit_positions_in_natal_houses: dict[str, Any]
    aspect_hits_by_mode: dict[str, list[Any]]
    location_label: str
    raw_location: str
    include_time: bool


def resolve_personal_transit_location(
    raw_value: str,
    *,
    fallback_lat: float,
    fallback_lon: float,
    fallback_location_label: str,
) -> tuple[float, float, str]:
    value = raw_value.strip()
    if not value:
        return float(fallback_lat), float(fallback_lon), str(fallback_location_label)

    if "," in value:
        maybe_lat, maybe_lon = value.split(",", 1)
        try:
            parsed_lat = float(maybe_lat.strip())
            parsed_lon = float(maybe_lon.strip())
            if -90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0:
                return parsed_lat, parsed_lon, f"{parsed_lat:.4f}, {parsed_lon:.4f}"
        except ValueError:
            pass

    try:
        lat, lon, resolved_label = geocode_location(value)
    except LocationLookupError as error:
        raise PersonalTransitLocationError(str(error)) from error
    return float(lat), float(lon), resolved_label


def build_personal_transit_header_lines(
    *,
    natal_chart_name: str,
    transit_chart: Chart,
    location_label: str,
    include_time: bool,
    local_tz: datetime.tzinfo,
) -> list[str]:
    local_dt = transit_chart.dt.astimezone(local_tz)
    date_label = local_dt.strftime("%m.%d.%Y")
    time_label = local_dt.strftime("%H:%M") if include_time else "omitted"
    timezone_label = local_dt.strftime("%Z") or str(local_tz)
    return [
        "Personal Transit (Transit → Natal)",
        "---------------------------------",
        f"Name:      {natal_chart_name}",
        format_chart_header(
            "when_where",
            date=date_label,
            time=time_label,
            timezone=timezone_label,
            location=location_label,
            lat=transit_chart.lat,
            lon=transit_chart.lon,
        ),
        "",
    ]


def recalculate_personal_transit(
    *,
    natal_chart: Chart,
    selected_local_datetime: datetime.datetime,
    location: tuple[float, float, str],
    raw_location: str,
) -> PersonalTransitRecalculationResult:
    lat, lon, location_label = location
    selected_utc = selected_local_datetime.astimezone(datetime.timezone.utc)
    include_time = True
    timestamp_label = selected_utc.strftime("%Y-%m-%d %H:%M UTC")
    personal_transit_name = (
        f"Personal Transit Chart for {natal_chart.name} on {timestamp_label} @ {location_label}"
    )
    transit_chart = Chart(
        personal_transit_name,
        selected_utc,
        lat,
        lon,
        tz=datetime.timezone.utc,
    )
    transit_chart.birth_place = location_label
    transit_chart.birthtime_unknown = not include_time
    transit_chart.retcon_time_used = False

    transit_normalized = normalize_chart(transit_chart, chart_type="transit")
    natal_normalized = normalize_chart(natal_chart, chart_type="natal")
    transit_in_natal = assign_houses(
        transit_normalized.bodies,
        natal_normalized.houses,
        layer="TRANSIT",
    )
    natal_targets = assign_houses(
        natal_normalized.bodies,
        natal_normalized.houses,
        layer="NATAL",
    )
    aspect_hits_by_mode = {
        PERSONAL_TRANSIT_MODE_LIFE_FORECAST: compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
        ),
        PERSONAL_TRANSIT_MODE_DAILY_VIBE: compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        ),
    }

    return PersonalTransitRecalculationResult(
        transit_chart=transit_chart,
        transit_positions_in_natal_houses=transit_in_natal,
        aspect_hits_by_mode=aspect_hits_by_mode,
        location_label=location_label,
        raw_location=raw_location.strip() or location_label,
        include_time=include_time,
    )
