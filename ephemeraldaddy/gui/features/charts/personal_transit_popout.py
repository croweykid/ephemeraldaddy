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
from ephemeraldaddy.gui.features.transits.diagnostics import (
    log_natal_derived_cache_diagnostic,
)
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location
from ephemeraldaddy.gui.style import format_chart_header

OUT_OF_SIGN_WARNING = "⚠️"
OUT_OF_SIGN_TOOLTIP = "Out of sign limits, but within orbital limits."
_SIGN_DISTANCE_BY_ASPECT = {
    "conjunction": 0,
    "semisextile": 1,
    "sextile": 2,
    "square": 3,
    "trine": 4,
    "quincunx": 5,
    "opposition": 6,
}


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


def _zodiac_sign_index(longitude: Any) -> int | None:
    try:
        return int((float(longitude) % 360.0) // 30.0) % 12
    except (TypeError, ValueError):
        return None


def is_out_of_sign_personal_transit_aspect(hit: Any) -> bool:
    """Return True when exact orb math yields an aspect across non-matching signs.

    Only aspects with an ordinary sign-distance counterpart are classified.
    Harmonics such as quintile/biquintile and 45°/135° aspects have no single
    canonical sign separation, so they are never labeled out-of-sign here.
    """
    aspect_key = str(getattr(hit, "aspect", "")).strip().replace(" ", "_").lower()
    expected_distance = _SIGN_DISTANCE_BY_ASPECT.get(aspect_key)
    if expected_distance is None:
        return False

    left_index = _zodiac_sign_index(getattr(getattr(hit, "a", None), "lon_deg", None))
    right_index = _zodiac_sign_index(getattr(getattr(hit, "b", None), "lon_deg", None))
    if left_index is None or right_index is None:
        return False

    raw_distance = abs(left_index - right_index)
    sign_distance = min(raw_distance, 12 - raw_distance)
    return sign_distance != expected_distance


def append_out_of_sign_warning(
    line: str,
    hit: Any,
) -> tuple[str, dict[str, object] | None]:
    """Append the Personal Transit warning and return its hover-span metadata."""
    if not is_out_of_sign_personal_transit_aspect(hit):
        return line, None
    base_line = line.rstrip()
    decorated = f"{base_line} {OUT_OF_SIGN_WARNING}"
    warning_start = len(decorated) - len(OUT_OF_SIGN_WARNING)
    return decorated, {
        "span_start": warning_start,
        "span_end": warning_start + len(OUT_OF_SIGN_WARNING),
        "tooltip": OUT_OF_SIGN_TOOLTIP,
    }


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
        "",
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
    # The popout can be recalculated long after it first opened. Revalidate the
    # natal derived state at the calculation boundary instead of assuming the
    # object still reflects canonical birth data.
    log_natal_derived_cache_diagnostic(natal_chart)

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
