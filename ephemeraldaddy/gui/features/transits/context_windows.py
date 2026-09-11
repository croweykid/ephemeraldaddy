"""Bounded context scanning for Personal Transit popouts.

The Personal Transit popout needs more context than aspects active at one instant:
users should also be able to see structural transits that recently ended and
those that are about to begin.  This module discovers Life Forecast events in a
small date neighborhood, then delegates exact ingress/egress resolution to the
same core window scanner used by the existing transit UI.

This deliberately follows ``personal_transit_rules_for_mode`` instead of
inventing a second definition of a "major" transit.  In particular, outer
planet minor aspects remain eligible when the Life Forecast policy allows them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from ephemeraldaddy.core.aspect_display import axis_aspect_redundancy_key
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_CHIRON_BODIES,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    PERSONAL_TRANSIT_SOCIAL_PLANETS,
    AspectHit,
    BodyPosition,
    assign_houses,
    compute_aspects,
    compute_chart,
    find_transit_aspect_window_result,
    normalize_chart,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.core.ephemeris import planetary_longitude
from ephemeraldaddy.core.interpretations import (
    ASTEROIDS,
    BLACK_MOON_LILITH,
    NODES,
    OUTER_PLANETS,
)


STATUS_RECENT = "recent"
STATUS_ACTIVE = "active"
STATUS_UPCOMING = "upcoming"
STATUS_ORDER = (STATUS_RECENT, STATUS_ACTIVE, STATUS_UPCOMING)

DEFAULT_CONTEXT_DAYS = 30
DEFAULT_DISCOVERY_STEP_HOURS = 24.0

# Stable order keeps repeated scans deterministic and puts the most structural
# bodies first when two events have identical dates.
_LIFE_FORECAST_TRANSITING_BODIES = (
    "Pluto",
    "Neptune",
    "Uranus",
    "Saturn",
    "Jupiter",
    "Rahu",
    "Ketu",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Mean Lilith",
    "Osculating Lilith",
    "Natural Lilith",
)
_ELIGIBLE_LIFE_FORECAST_BODIES = frozenset(
    OUTER_PLANETS
    | PERSONAL_TRANSIT_SOCIAL_PLANETS
    | PERSONAL_TRANSIT_CHIRON_BODIES
    | NODES
    | ASTEROIDS
    | BLACK_MOON_LILITH
)


@dataclass(frozen=True, slots=True)
class TransitContextWindow:
    """One Life Forecast event relevant to the selected date neighborhood."""

    status: str
    transiting_body: str
    natal_body: str
    aspect_name: str
    start: datetime | None
    end: datetime | None
    representative_hit: AspectHit
    start_truncated_to_scope: bool = False
    end_truncated_to_scope: bool = False

    @property
    def event_key(self) -> tuple[object, ...]:
        return _event_key(self.representative_hit)



def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)



def _event_key(hit: AspectHit) -> tuple[object, ...]:
    """Return the same conceptual key across complementary axis endpoints."""
    axis_key = axis_aspect_redundancy_key(
        hit.a.name,
        hit.b.name,
        hit.aspect,
        directed=True,
        layer1=hit.a.layer,
        layer2=hit.b.layer,
    )
    if axis_key is not None:
        return ("axis", *axis_key)
    return ("aspect", hit.a.name, hit.aspect, hit.b.name)



def _natal_targets(natal_chart: object) -> tuple[BodyPosition, ...]:
    normalized = normalize_chart(natal_chart, chart_type="natal")
    assigned = assign_houses(normalized.bodies, normalized.houses, layer="NATAL")
    return tuple(assigned.values())



def _transiting_positions_at(
    when_utc: datetime,
    transit_location: tuple[float, float],
) -> tuple[BodyPosition, ...]:
    """Resolve only bodies eligible for Life Forecast discovery.

    ``planetary_longitude`` is normally sufficient.  A lazily-created Chart is
    retained as a fallback for any supported body not exposed by that helper.
    """
    fallback_chart = None
    rows: list[BodyPosition] = []
    for body_name in _LIFE_FORECAST_TRANSITING_BODIES:
        if body_name not in _ELIGIBLE_LIFE_FORECAST_BODIES:
            continue
        longitude = planetary_longitude(when_utc, body_name)
        if longitude is None:
            if fallback_chart is None:
                fallback_chart = compute_chart(
                    when_utc,
                    transit_location,
                    name="Personal Transit context discovery",
                )
            longitude = fallback_chart.positions.get(body_name)
        if longitude is None:
            continue
        rows.append(
            BodyPosition(
                name=body_name,
                lon_deg=float(longitude) % 360.0,
                layer="TRANSIT",
            )
        )
    return tuple(rows)



def _probe_times(
    center: datetime,
    *,
    context_days: int,
    step_hours: float,
) -> tuple[datetime, ...]:
    radius = timedelta(days=max(0, int(context_days)))
    start = center - radius
    end = center + radius
    step = timedelta(hours=max(1.0, float(step_hours)))

    probes: list[datetime] = [center]
    cursor = start
    while cursor <= end:
        probes.append(cursor)
        cursor += step
    if probes[-1] != end:
        probes.append(end)
    return tuple(sorted(set(probes)))



def _status_for_window(
    *,
    event_key: tuple[object, ...],
    active_event_keys: set[tuple[object, ...]],
    start: datetime | None,
    end: datetime | None,
    center: datetime,
    context_days: int,
) -> str | None:
    radius = timedelta(days=max(0, int(context_days)))
    if event_key in active_event_keys:
        return STATUS_ACTIVE
    if end is not None and center - radius <= end < center:
        return STATUS_RECENT
    if start is not None and center < start <= center + radius:
        return STATUS_UPCOMING
    return None



def _sort_key(window: TransitContextWindow) -> tuple[object, ...]:
    body_rank = {
        body: index for index, body in enumerate(_LIFE_FORECAST_TRANSITING_BODIES)
    }
    if window.status == STATUS_RECENT:
        # Most recently completed first.
        date_key = -(
            window.end.timestamp() if window.end is not None else float("-inf")
        )
    elif window.status == STATUS_ACTIVE:
        # Most exact active events first, then structural-body order.
        date_key = -float(window.representative_hit.exactness)
    else:
        date_key = window.start.timestamp() if window.start is not None else float("inf")
    return (
        STATUS_ORDER.index(window.status),
        date_key,
        body_rank.get(window.transiting_body, len(body_rank)),
        window.natal_body,
        window.aspect_name,
    )



def scan_personal_transit_context(
    natal_chart: object,
    selected_datetime_utc: datetime,
    transit_location: tuple[float, float],
    *,
    context_days: int = DEFAULT_CONTEXT_DAYS,
    discovery_step_hours: float = DEFAULT_DISCOVERY_STEP_HOURS,
    precision_minutes: float = 15.0,
    should_cancel: Callable[[], bool] | None = None,
) -> list[TransitContextWindow]:
    """Return recent, active, and approaching Life Forecast windows.

    Discovery is bounded to ``selected_datetime_utc +/- context_days``.  Once an
    event is discovered, its real start/end are resolved by the core adaptive
    scanner, so a Pluto transit that spans years still receives its true dates.
    """
    center = _ensure_utc(selected_datetime_utc)
    rules = personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
    natal_targets = _natal_targets(natal_chart)

    discovered: dict[tuple[object, ...], tuple[datetime, AspectHit]] = {}
    active_event_keys: set[tuple[object, ...]] = set()

    for probe in _probe_times(
        center,
        context_days=context_days,
        step_hours=discovery_step_hours,
    ):
        if should_cancel is not None and should_cancel():
            return []
        transit_positions = _transiting_positions_at(probe, transit_location)
        hits = compute_aspects(transit_positions, natal_targets, rules)
        for hit in hits:
            key = _event_key(hit)
            if probe == center:
                active_event_keys.add(key)
            previous = discovered.get(key)
            # Keep the hit sampled nearest the selected moment.  This provides
            # the most useful exactness value for active rows and a stable
            # representative for theme grouping.
            if previous is None or abs((probe - center).total_seconds()) < abs(
                (previous[0] - center).total_seconds()
            ):
                discovered[key] = (probe, hit)

    results: list[TransitContextWindow] = []
    for key, (probe, hit) in discovered.items():
        if should_cancel is not None and should_cancel():
            return []
        resolved = find_transit_aspect_window_result(
            natal_chart,
            probe,
            transit_location,
            hit,
            rules,
            search_days=max(float(context_days), 30.0),
            precision_minutes=precision_minutes,
            should_cancel=should_cancel,
        )
        status = _status_for_window(
            event_key=key,
            active_event_keys=active_event_keys,
            start=resolved.start,
            end=resolved.end,
            center=center,
            context_days=context_days,
        )
        if status is None:
            continue
        results.append(
            TransitContextWindow(
                status=status,
                transiting_body=hit.a.name,
                natal_body=hit.b.name,
                aspect_name=hit.aspect,
                start=resolved.start,
                end=resolved.end,
                representative_hit=hit,
                start_truncated_to_scope=resolved.start_truncated_to_scope,
                end_truncated_to_scope=resolved.end_truncated_to_scope,
            )
        )

    results.sort(key=_sort_key)
    return results



def partition_context_windows(
    windows: Iterable[TransitContextWindow],
) -> dict[str, list[TransitContextWindow]]:
    """Return stable Recent / Active / Upcoming buckets for presenters."""
    buckets = {status: [] for status in STATUS_ORDER}
    for window in windows:
        if window.status in buckets:
            buckets[window.status].append(window)
    return buckets
