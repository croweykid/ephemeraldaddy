"""Pure, non-Qt generation model for the Personal Timeline workflow."""

from __future__ import annotations

import calendar
import datetime
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ephemeraldaddy.core.aspect_display import axis_aspect_redundancy_key
from ephemeraldaddy.core.composite import (
    BodyPosition,
    COMPOSITE_ASPECT_TYPES,
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    PERSONAL_TRANSIT_MAX_ORB_DEG,
    angular_distance,
    compute_chart,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.core.ephemeris import planetary_longitude
from ephemeraldaddy.core.interpretations import (
    ANGLES, ASTEROIDS, BLACK_MOON_LILITH, EPHEMERIS_MAX_DATE, EPHEMERIS_MIN_DATE,
    FAST_TRANSIT_BODIES, NODES, OUTER_PLANETS, VERY_FAST_TRANSIT_BODIES,
)

DEFAULT_TIMELINE_YEARS = 120
DEFAULT_SCAN_STEP_DAYS = 2
_BOUNDARY_REFINEMENT_STEPS = 14

# Personal Timeline intentionally starts broad. These are slow/life-scale
# transiting bodies; the view filters the resulting candidates after generation.
_TIMELINE_TRANSITING_BODIES = frozenset(
    set(OUTER_PLANETS)
    | set(NODES)
    | set(ASTEROIDS)
    | set(BLACK_MOON_LILITH)
    | {"Jupiter", "Saturn", "Chiron"}
)

_BODY_DISPLAY_ORDER = (
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Rahu",
    "Ketu",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Lilith",
)

_ASPECT_LABELS = {
    "conjunction": "conjunct",
    "semisextile": "semisextile",
    "semisquare": "semisquare",
    "sextile": "sextile",
    "quintile": "quintile",
    "square": "square",
    "trine": "trine",
    "sesquiquadrate": "sesquiquadrate",
    "biquintile": "biquintile",
    "quincunx": "quincunx",
    "opposition": "opposite",
}


@dataclass(frozen=True, slots=True)
class TimelineTransitDefinition:
    transiting_body: str
    natal_body: str
    natal_longitude: float
    aspect_name: str
    aspect_angle: float
    orb_deg: float

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.transiting_body, self.natal_body, self.aspect_name)

    @property
    def label(self) -> str:
        aspect = _ASPECT_LABELS.get(self.aspect_name, self.aspect_name)
        return f"{self.transiting_body} {aspect} natal {self.natal_body}"


@dataclass(frozen=True, slots=True)
class PersonalTimelineWindow:
    chart_uid: str
    transit: TimelineTransitDefinition
    start: datetime.datetime
    end: datetime.datetime
    start_truncated: bool = False
    end_truncated: bool = False

    @property
    def midpoint(self) -> datetime.datetime:
        return self.start + ((self.end - self.start) / 2)

    @property
    def duration_days(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds() / 86400.0)


def _timeline_transiting_bodies() -> tuple[str, ...]:
    ordered = [body for body in _BODY_DISPLAY_ORDER if body in _TIMELINE_TRANSITING_BODIES]
    ordered.extend(sorted(_TIMELINE_TRANSITING_BODIES.difference(ordered)))
    return tuple(ordered)


def _build_transit_definitions(chart: Any) -> tuple[TimelineTransitDefinition, ...]:
    """Build the broad research candidate set before any display filters apply.

    Every configured aspect type is considered for every slow/life-scale transit
    body against every natal position available on the chart. Orbs are clamped to
    the existing Personal Transit maximum so broad coverage does not imply broad
    orbs. Importance is evaluated later through filters and outcome analysis.
    """
    positions = dict(getattr(chart, "positions", {}) or {})
    if not positions:
        return ()

    definitions: dict[tuple[str, str, str], TimelineTransitDefinition] = {}
    for transit_name in _timeline_transiting_bodies():
        for natal_name_raw, natal_longitude_raw in positions.items():
            if natal_longitude_raw is None:
                continue
            try:
                natal_longitude = float(natal_longitude_raw) % 360.0
            except (TypeError, ValueError):
                continue

            natal_name = str(natal_name_raw)
            for aspect in COMPOSITE_ASPECT_TYPES:
                allowed_orb = min(
                    float(aspect.orb_deg),
                    float(PERSONAL_TRANSIT_MAX_ORB_DEG),
                )
                if allowed_orb <= 0:
                    continue
                definition = TimelineTransitDefinition(
                    transiting_body=transit_name,
                    natal_body=natal_name,
                    natal_longitude=natal_longitude,
                    aspect_name=aspect.name,
                    aspect_angle=float(aspect.angle_deg),
                    orb_deg=allowed_orb,
                )
                definitions[definition.key] = definition

    return tuple(definitions.values())


def _build_personal_transit_range_definitions(
    chart: Any,
) -> tuple[TimelineTransitDefinition, ...]:
    """Build exactly the candidates accepted by the two Personal Transit modes."""
    positions = dict(getattr(chart, "positions", {}) or {})
    transit_bodies = list(_timeline_transiting_bodies())
    transit_bodies.extend(
        sorted(
            (FAST_TRANSIT_BODIES | VERY_FAST_TRANSIT_BODIES | ANGLES).difference(
                transit_bodies
            )
        )
    )
    definitions: dict[tuple[str, str, str], TimelineTransitDefinition] = {}
    seen_axis_events: set[tuple[object, ...]] = set()

    for mode in (
        PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
        PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    ):
        rules = personal_transit_rules_for_mode(mode)
        for transit_name in transit_bodies:
            transit_position = BodyPosition(name=transit_name, lon_deg=0.0)
            for natal_name_raw, natal_longitude_raw in positions.items():
                if natal_longitude_raw is None:
                    continue
                try:
                    natal_longitude = float(natal_longitude_raw) % 360.0
                except (TypeError, ValueError):
                    continue
                natal_name = str(natal_name_raw)
                natal_position = BodyPosition(name=natal_name, lon_deg=natal_longitude)
                if rules.pair_filter and not rules.pair_filter(
                    transit_position, natal_position, rules.context
                ):
                    continue
                for aspect in rules.aspect_types:
                    allowed_orb = (
                        rules.orb_table(
                            transit_position, natal_position, aspect, rules.context
                        )
                        if rules.orb_table
                        else aspect.orb_deg
                    )
                    if allowed_orb <= 0:
                        continue
                    axis_key = axis_aspect_redundancy_key(
                        transit_name,
                        natal_name,
                        aspect.name,
                        directed=True,
                        layer1="TRANSIT",
                        layer2="NATAL",
                    )
                    if axis_key is not None:
                        if axis_key in seen_axis_events:
                            continue
                        seen_axis_events.add(axis_key)
                    definition = TimelineTransitDefinition(
                        transiting_body=transit_name,
                        natal_body=natal_name,
                        natal_longitude=natal_longitude,
                        aspect_name=aspect.name,
                        aspect_angle=float(aspect.angle_deg),
                        orb_deg=float(allowed_orb),
                    )
                    definitions[definition.key] = definition
    return tuple(definitions.values())


def _aspect_orb(
    transit_longitude: float,
    definition: TimelineTransitDefinition,
) -> float:
    separation = angular_distance(transit_longitude, definition.natal_longitude)
    return abs(float(separation) - definition.aspect_angle)


def _definition_is_active(
    when: datetime.datetime,
    definition: TimelineTransitDefinition,
    longitude_at: Callable[[datetime.datetime, str], float | None] | None = None,
) -> bool:
    resolver = longitude_at or planetary_longitude
    longitude = resolver(when, definition.transiting_body)
    return bool(
        longitude is not None
        and _aspect_orb(float(longitude), definition) <= definition.orb_deg
    )


def _refine_boundary(
    outside: datetime.datetime,
    inside: datetime.datetime,
    definition: TimelineTransitDefinition,
    longitude_at: Callable[[datetime.datetime, str], float | None] | None = None,
) -> datetime.datetime:
    """Refine an outside/inside transition to approximately minute precision."""
    left = outside
    right = inside
    left_active = _definition_is_active(left, definition, longitude_at)
    right_active = _definition_is_active(right, definition, longitude_at)
    if left_active == right_active:
        return inside

    for _ in range(_BOUNDARY_REFINEMENT_STEPS):
        middle = left + ((right - left) / 2)
        middle_active = _definition_is_active(middle, definition, longitude_at)
        if middle_active == left_active:
            left = middle
        else:
            right = middle
    return right if right_active else left


def _add_years_clamped(value: datetime.datetime, years: int) -> datetime.datetime:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _ephemeris_boundary(
    date_value: datetime.date,
    tzinfo: datetime.tzinfo,
    *,
    end_of_day: bool,
) -> datetime.datetime:
    time_value = datetime.time(23, 59, 59, 999999) if end_of_day else datetime.time.min
    return datetime.datetime.combine(date_value, time_value, tzinfo=tzinfo)


def _known_death_datetime(
    chart: Any,
    tzinfo: datetime.tzinfo,
) -> datetime.datetime | None:
    if not bool(getattr(chart, "is_deceased", False)):
        return None

    try:
        year = int(getattr(chart, "death_year", None) or 0)
    except (TypeError, ValueError):
        return None
    if year <= 0:
        return None

    try:
        month = int(getattr(chart, "death_month", None) or 0)
    except (TypeError, ValueError):
        month = 0
    try:
        day = int(getattr(chart, "death_day", None) or 0)
    except (TypeError, ValueError):
        day = 0

    if not 1 <= month <= 12:
        month = 12
        day = 31
    elif not 1 <= day <= calendar.monthrange(year, month)[1]:
        day = calendar.monthrange(year, month)[1]

    try:
        return datetime.datetime(year, month, day, 23, 59, 59, tzinfo=tzinfo)
    except ValueError:
        return None


def _timeline_bounds(
    chart: Any,
    birth: datetime.datetime,
    years: int,
) -> tuple[datetime.datetime, datetime.datetime]:
    ephemeris_start = _ephemeris_boundary(
        EPHEMERIS_MIN_DATE,
        birth.tzinfo,
        end_of_day=False,
    )
    ephemeris_end = _ephemeris_boundary(
        EPHEMERIS_MAX_DATE,
        birth.tzinfo,
        end_of_day=True,
    )
    start = max(birth, ephemeris_start)
    end = min(_add_years_clamped(birth, years), ephemeris_end)
    death = _known_death_datetime(chart, birth.tzinfo)
    if death is not None and death > start:
        end = min(end, death)
    return start, end


def generate_personal_timeline(
    chart_uid: str,
    chart: Any,
    *,
    years: int = DEFAULT_TIMELINE_YEARS,
    step_days: int = DEFAULT_SCAN_STEP_DAYS,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[PersonalTimelineWindow]:
    """Generate a broad set of continuous life-scale transit date ranges."""
    normalized_uid = str(chart_uid or "").strip().upper()
    if not normalized_uid:
        raise ValueError("Personal Timeline requires a Chart UID.")

    birth = getattr(chart, "dt", None)
    if not isinstance(birth, datetime.datetime) or birth.tzinfo is None:
        raise ValueError(
            "The selected chart does not have a timezone-aware birth datetime."
        )
    if years <= 0 or step_days <= 0:
        raise ValueError("Timeline years and scan step must be greater than zero.")

    definitions = _build_transit_definitions(chart)
    if not definitions:
        return []

    start, end = _timeline_bounds(chart, birth, years)
    if end <= start:
        return []

    definition_lookup = {definition.key: definition for definition in definitions}
    definitions_by_body: dict[str, list[TimelineTransitDefinition]] = {}
    for definition in definitions:
        definitions_by_body.setdefault(definition.transiting_body, []).append(definition)

    step = datetime.timedelta(days=step_days)
    total_steps = max(1, int((end - start) / step) + 1)
    active_starts: dict[tuple[str, str, str], tuple[datetime.datetime, bool]] = {}
    previous_active: set[tuple[str, str, str]] = set()
    results: list[PersonalTimelineWindow] = []

    previous_dt = start
    current_dt = start
    step_index = 0

    while current_dt <= end:
        if cancelled is not None and cancelled():
            return []

        current_active: set[tuple[str, str, str]] = set()
        for transit_body, body_definitions in definitions_by_body.items():
            longitude = planetary_longitude(current_dt, transit_body)
            if longitude is None:
                continue
            longitude_value = float(longitude)
            for definition in body_definitions:
                if _aspect_orb(longitude_value, definition) <= definition.orb_deg:
                    current_active.add(definition.key)

        for key in current_active.difference(previous_active):
            definition = definition_lookup[key]
            if current_dt == start:
                active_starts[key] = (start, True)
            else:
                active_starts[key] = (
                    _refine_boundary(previous_dt, current_dt, definition),
                    False,
                )

        for key in previous_active.difference(current_active):
            start_info = active_starts.pop(key, None)
            if start_info is None:
                continue
            definition = definition_lookup[key]
            boundary = _refine_boundary(current_dt, previous_dt, definition)
            window_start, start_truncated = start_info
            if boundary >= window_start:
                results.append(
                    PersonalTimelineWindow(
                        chart_uid=normalized_uid,
                        transit=definition,
                        start=window_start,
                        end=boundary,
                        start_truncated=start_truncated,
                    )
                )

        previous_active = current_active
        previous_dt = current_dt
        if current_dt >= end:
            break

        current_dt = min(end, current_dt + step)
        step_index += 1
        if progress is not None and (step_index % 64 == 0 or current_dt >= end):
            progress(min(step_index, total_steps), total_steps)

    for key, (window_start, start_truncated) in active_starts.items():
        results.append(
            PersonalTimelineWindow(
                chart_uid=normalized_uid,
                transit=definition_lookup[key],
                start=window_start,
                end=end,
                start_truncated=start_truncated,
                end_truncated=True,
            )
        )

    results.sort(key=lambda item: (item.start, item.end, item.transit.label))
    return results


def generate_personal_transit_range(
    chart_uid: str,
    chart: Any,
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    step_hours: float = 6.0,
    cancelled: Callable[[], bool] | None = None,
    transit_location: tuple[float, float] | None = None,
) -> list[PersonalTimelineWindow]:
    """Generate major transit windows inside an explicit, short date range."""
    normalized_uid = str(chart_uid or "").strip().upper()
    if not normalized_uid:
        raise ValueError("Personal Transit range generation requires a Chart UID.")
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Transit range bounds must be timezone-aware.")
    if end <= start or step_hours <= 0:
        raise ValueError(
            "Transit range end must be after start and scan step hours must be positive."
        )

    definitions = _build_personal_transit_range_definitions(chart)
    definition_lookup = {definition.key: definition for definition in definitions}
    definitions_by_body: dict[str, list[TimelineTransitDefinition]] = {}
    for definition in definitions:
        definitions_by_body.setdefault(definition.transiting_body, []).append(definition)

    longitude_cache: dict[tuple[datetime.datetime, str], float | None] = {}
    chart_positions_cache: dict[datetime.datetime, dict[str, float]] = {}

    def longitude_at(when: datetime.datetime, body: str) -> float | None:
        key = (when, body)
        if key not in longitude_cache:
            if transit_location is not None:
                positions = chart_positions_cache.get(when)
                if positions is None:
                    positions = dict(
                        compute_chart(
                            when,
                            transit_location,
                            name="Personal Transit range probe",
                        ).positions
                    )
                    chart_positions_cache[when] = positions
                value = positions.get(body)
                longitude_cache[key] = float(value) if value is not None else None
            else:
                longitude_cache[key] = planetary_longitude(when, body)
        return longitude_cache[key]

    step = datetime.timedelta(hours=step_hours)
    active_starts: dict[tuple[str, str, str], tuple[datetime.datetime, bool]] = {}
    previous_active: set[tuple[str, str, str]] = set()
    previous_dt = start
    current_dt = start
    results: list[PersonalTimelineWindow] = []
    while current_dt <= end:
        if cancelled is not None and cancelled():
            return []
        current_active: set[tuple[str, str, str]] = set()
        for transit_body, body_definitions in definitions_by_body.items():
            longitude = longitude_at(current_dt, transit_body)
            if longitude is None:
                continue
            for definition in body_definitions:
                if _aspect_orb(float(longitude), definition) <= definition.orb_deg:
                    current_active.add(definition.key)
        for key in current_active.difference(previous_active):
            active_starts[key] = (
                (
                    start
                    if current_dt == start
                    else _refine_boundary(
                        previous_dt,
                        current_dt,
                        definition_lookup[key],
                        longitude_at,
                    )
                ),
                current_dt == start,
            )
        for key in previous_active.difference(current_active):
            window_start, start_truncated = active_starts.pop(key)
            boundary = _refine_boundary(
                current_dt,
                previous_dt,
                definition_lookup[key],
                longitude_at,
            )
            if boundary >= window_start:
                results.append(PersonalTimelineWindow(normalized_uid, definition_lookup[key], window_start, boundary, start_truncated))
        previous_active = current_active
        previous_dt = current_dt
        if current_dt >= end:
            break
        current_dt = min(end, current_dt + step)
    for key, (window_start, start_truncated) in active_starts.items():
        results.append(PersonalTimelineWindow(normalized_uid, definition_lookup[key], window_start, end, start_truncated, True))
    results.sort(key=lambda item: (item.start, item.end, item.transit.label))
    return results
