from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Mapping

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import (
    ASTEROIDS,
    EPHEMERIS_MAX_DATE,
    EPHEMERIS_MIN_DATE,
    FAST_TRANSIT_BODIES,
    MAJOR_ASPECTS,
    MINOR_ASPECTS,
    NODES,
    OUTER_PLANETS,
    PERSONAL,
    POINTS,
    VERY_FAST_TRANSIT_BODIES,
)


@dataclass(frozen=True)
class HouseFrame:
    system: str
    cusps: tuple[float, ...]
    angles: dict[str, float]


@dataclass(frozen=True)
class BodyPosition:
    name: str
    lon_deg: float
    lat_deg: float | None = None
    speed: float | None = None
    sign: str | None = None
    house: int | None = None
    retro: bool | None = None
    layer: str | None = None


@dataclass(frozen=True)
class NormalizedChart:
    id: int | None
    chart_type: str | None
    subject_id: int | None
    jd_ut: float
    location: dict[str, float | str | None]
    houses: HouseFrame
    bodies: dict[str, BodyPosition]


@dataclass(frozen=True)
class AspectType:
    name: str
    angle_deg: float
    orb_deg: float
    weight: float = 1.0


@dataclass(frozen=True)
class AspectRuleSet:
    aspect_types: tuple[AspectType, ...]
    skip_same_body_name: bool = True
    context: str = "generic"
    orb_table: Callable[[BodyPosition, BodyPosition, AspectType, str], float] | None = None    
    pair_filter: Callable[[BodyPosition, BodyPosition, str], bool] | None = None

@dataclass(frozen=True)
class AspectHit:
    a: BodyPosition
    b: BodyPosition
    aspect: str
    exactness: float
    orb_deg: float
    applying_separating: str | None
    weight: float


@dataclass(frozen=True)
class TransitAspectWindowResult:
    start: datetime | None
    end: datetime | None
    start_truncated_to_scope: bool = False
    end_truncated_to_scope: bool = False
    out_of_scope: bool = False


class TransitAspectWindowCancelled(RuntimeError):
    """Raised when transit aspect window scanning is cancelled."""


@dataclass(frozen=True)
class CompositeChartView:
    base_chart: NormalizedChart
    overlays: tuple[dict[str, BodyPosition], ...]
    aspects: tuple[AspectHit, ...]
    style: str


DEFAULT_ASPECT_RULES = AspectRuleSet(
    aspect_types=(
        AspectType("conjunction", 0.0, 8.0, 1.0),
        AspectType("sextile", 60.0, 6.0, 0.7),
        AspectType("square", 90.0, 7.0, 0.85),
        AspectType("trine", 120.0, 8.0, 0.8),
        AspectType("opposition", 180.0, 8.0, 0.9),
    ),
    context="natal",
)

COMPOSITE_ASPECT_TYPES: tuple[AspectType, ...] = (
    # Major aspects
    AspectType("conjunction", 0.0, 7.0, 1.0),
    AspectType("sextile", 60.0, 7.0, 0.7),
    AspectType("square", 90.0, 7.0, 0.85),
    AspectType("trine", 120.0, 7.0, 0.8),
    AspectType("opposition", 180.0, 7.0, 0.9),
    # Minor aspects
    AspectType("quincunx", 150.0, 7.0, 0.55),
    AspectType("semisquare", 45.0, 7.0, 0.45),
    AspectType("sesquiquadrate", 135.0, 7.0, 0.5),
    AspectType("semisextile", 30.0, 7.0, 0.35),
    AspectType("quintile", 72.0, 7.0, 0.4),
    AspectType("biquintile", 144.0, 7.0, 0.4),
)

TRANSIT_ASPECT_RULES = AspectRuleSet(
    aspect_types=COMPOSITE_ASPECT_TYPES,
    skip_same_body_name=False,
    context="transit_to_natal",
    orb_table=lambda _a, _b, aspect, _ctx: min(aspect.orb_deg, PERSONAL_TRANSIT_MAX_ORB_DEG),
)

SYNASTRY_ASPECT_RULES = AspectRuleSet(
    aspect_types=COMPOSITE_ASPECT_TYPES,
    skip_same_body_name=False,
    context="synastry",
    orb_table=lambda _a, _b, aspect, _ctx: min(aspect.orb_deg, PERSONAL_TRANSIT_MAX_ORB_DEG),
)

PERSONAL_TRANSIT_MODE_LIFE_FORECAST = "life_forecast"
PERSONAL_TRANSIT_MODE_DAILY_VIBE = "daily_vibe"
PERSONAL_TRANSIT_MAX_ORB_DEG = 3.0

def _body_is_point(name: str) -> bool:
    return name in POINTS or name in {"Fortune"}


def _life_forecast_pair_filter(body_a: BodyPosition, body_b: BodyPosition, _context: str) -> bool:
    transit_name = body_a.name
    natal_name = body_b.name
    if transit_name in FAST_TRANSIT_BODIES or transit_name in VERY_FAST_TRANSIT_BODIES:
        return False
    if _body_is_point(transit_name) or _body_is_point(natal_name):
        return False
    if transit_name in OUTER_PLANETS:
        return natal_name in PERSONAL or natal_name in OUTER_PLANETS
    if transit_name in NODES:
        return natal_name in PERSONAL
    if transit_name in ASTEROIDS:
        return natal_name in PERSONAL
    return False


def _daily_vibe_pair_filter(body_a: BodyPosition, body_b: BodyPosition, _context: str) -> bool:
    transit_name = body_a.name
    natal_name = body_b.name
    if _body_is_point(transit_name) or _body_is_point(natal_name):
        return False
    return transit_name in PERSONAL and natal_name in PERSONAL

def personal_transit_orb_cap(mode: str, transit_body: str, natal_body: str, aspect_name: str) -> float:
    aspect_name = aspect_name.lower()
    angle_lookup = {asp.name: asp.angle_deg for asp in COMPOSITE_ASPECT_TYPES}
    angle = int(angle_lookup.get(aspect_name, -1))
    if mode == PERSONAL_TRANSIT_MODE_LIFE_FORECAST:
        if transit_body in OUTER_PLANETS:
            if natal_body in PERSONAL and angle in MAJOR_ASPECTS:
                return PERSONAL_TRANSIT_MAX_ORB_DEG
            if natal_body in OUTER_PLANETS and angle in MAJOR_ASPECTS:
                return PERSONAL_TRANSIT_MAX_ORB_DEG
            if natal_body in PERSONAL and angle in MINOR_ASPECTS:
                return PERSONAL_TRANSIT_MAX_ORB_DEG
            return 0.0
        if transit_body in NODES:
            if natal_body in PERSONAL and angle in {0, 180}:
                return PERSONAL_TRANSIT_MAX_ORB_DEG
            return 0.0
        if transit_body in ASTEROIDS:
            if natal_body in PERSONAL and angle in MAJOR_ASPECTS:
                return PERSONAL_TRANSIT_MAX_ORB_DEG
            return 0.0
        return 0.0

    if mode == PERSONAL_TRANSIT_MODE_DAILY_VIBE:
        if angle not in MAJOR_ASPECTS:
            return 0.0
        if natal_body not in PERSONAL:
            return 0.0
        if transit_body in {"AS", "MC", "DS", "IC"}:
            return PERSONAL_TRANSIT_MAX_ORB_DEG
        if transit_body == "Moon":
            return PERSONAL_TRANSIT_MAX_ORB_DEG
        if transit_body in {"Sun", "Mercury", "Venus"}:
            return PERSONAL_TRANSIT_MAX_ORB_DEG
        if transit_body == "Mars":
            return PERSONAL_TRANSIT_MAX_ORB_DEG
        return 0.0
    return 0.0

TRANSIT_BODY_DAILY_MOTION_DEG = {
    "Moon": 13.2,
    "Sun": 0.99,
    "Mercury": 1.2,
    "Venus": 1.2,
    "Mars": 0.52,
    "AS": 361.0,
    "DS": 361.0,
    "MC": 361.0,
    "IC": 361.0,
}


def personal_transit_expected_duration_days(mode: str, transit_body: str, natal_body: str, aspect_name: str) -> float:
    orb_cap = personal_transit_orb_cap(mode, transit_body, natal_body, aspect_name)
    if orb_cap <= 0:
        return float("inf")
    motion = TRANSIT_BODY_DAILY_MOTION_DEG.get(transit_body)
    if motion is None or motion <= 0:
        return float("inf")
    return (2.0 * orb_cap) / motion


def split_daily_vibe_hits_by_expected_duration(
    daily_hits: Iterable[AspectHit],
    *,
    max_daily_days: float = 3.0,
) -> tuple[list[AspectHit], list[AspectHit]]:
    short_lived: list[AspectHit] = []
    longer_lived: list[AspectHit] = []
    for hit in daily_hits:
        duration_days = personal_transit_expected_duration_days(
            PERSONAL_TRANSIT_MODE_DAILY_VIBE,
            hit.a.name,
            hit.b.name,
            hit.aspect,
        )
        if duration_days <= max_daily_days:
            short_lived.append(hit)
        else:
            longer_lived.append(hit)
    return short_lived, longer_lived

def personal_transit_rules_for_mode(mode: str) -> AspectRuleSet:
    if mode == PERSONAL_TRANSIT_MODE_DAILY_VIBE:
        major_aspect_types = tuple(asp for asp in COMPOSITE_ASPECT_TYPES if int(asp.angle_deg) in MAJOR_ASPECTS)
        return AspectRuleSet(
            aspect_types=major_aspect_types,
            skip_same_body_name=False,
            context="transit_to_natal",
            pair_filter=_daily_vibe_pair_filter,
            orb_table=lambda a, b, aspect, _ctx: personal_transit_orb_cap(mode, a.name, b.name, aspect.name),
        )

    life_aspect_types = tuple(
        asp for asp in COMPOSITE_ASPECT_TYPES if int(asp.angle_deg) in MAJOR_ASPECTS or int(asp.angle_deg) in MINOR_ASPECTS
    )
    return AspectRuleSet(
        aspect_types=life_aspect_types,
        skip_same_body_name=False,
        context="transit_to_natal",
        pair_filter=_life_forecast_pair_filter,
        orb_table=lambda a, b, aspect, _ctx: personal_transit_orb_cap(mode, a.name, b.name, aspect.name),
    )

def compute_chart(
    dt_aware_or_local: datetime,
    location: tuple[float, float] | None,
    house_system: str = "placidus",
    *,
    name: str = "Computed chart",
) -> Chart:
    """
    Compute a chart with existing `Chart` primitives.

    Transit charts may pass `location=None`; in that case we use 0,0 and only
    treat planet longitudes as authoritative.
    """
    if house_system.lower() != "placidus":
        raise ValueError("Only placidus is currently supported by compute_chart.")
    lat, lon = (location if location is not None else (0.0, 0.0))
    return Chart(name=name, dt_local=dt_aware_or_local, lat=lat, lon=lon, tz=dt_aware_or_local.tzinfo)


def normalize_chart(
    chart: Chart,
    *,
    chart_id: int | None = None,
    chart_type: str | None = None,
    subject_id: int | None = None,
    house_system: str = "placidus",
) -> NormalizedChart:
    dt_utc = chart.dt.astimezone(timezone.utc)
    jd_ut = dt_utc.timestamp()
    house_cusps = tuple(float(value) % 360.0 for value in chart.houses[:12])

    angles: dict[str, float] = {}
    for name in ("AS", "MC", "DS", "IC"):
        value = chart.positions.get(name)
        if value is not None:
            angles[name] = float(value) % 360.0

    house_frame = HouseFrame(system=house_system, cusps=house_cusps, angles=angles)

    body_map: dict[str, BodyPosition] = {}
    retrogrades = dict(getattr(chart, "retrogrades", {}) or {})
    for name, lon in chart.positions.items():
        if lon is None:
            continue
        body_map[name] = BodyPosition(
            name=name,
            lon_deg=float(lon) % 360.0,
            sign=_sign_from_longitude(float(lon)),
            house=_house_for_longitude(float(lon), house_cusps),
            retro=retrogrades.get(name),
        )

    return NormalizedChart(
        id=chart_id,
        chart_type=chart_type,
        subject_id=subject_id,
        jd_ut=jd_ut,
        location={"lat": chart.lat, "lon": chart.lon, "tz": str(chart.dt.tzinfo) if chart.dt.tzinfo else None},
        houses=house_frame,
        bodies=body_map,
    )


def assign_houses(
    bodies: Mapping[str, BodyPosition],
    houses: HouseFrame,
    *,
    layer: str | None = None,
) -> dict[str, BodyPosition]:
    assigned: dict[str, BodyPosition] = {}
    for name, body in bodies.items():
        assigned[name] = BodyPosition(
            name=body.name,
            lon_deg=body.lon_deg,
            lat_deg=body.lat_deg,
            speed=body.speed,
            sign=body.sign or _sign_from_longitude(body.lon_deg),
            house=_house_for_longitude(body.lon_deg, houses.cusps),
            retro=body.retro if body.retro is not None else (body.speed < 0 if body.speed is not None else None),
            layer=layer or body.layer,
        )
    return assigned


def compute_aspects(
    set_a: Iterable[BodyPosition],
    set_b: Iterable[BodyPosition],
    rules: AspectRuleSet = DEFAULT_ASPECT_RULES,
) -> list[AspectHit]:
    aspects: list[AspectHit] = []
    list_a = list(set_a)
    list_b = list(set_b)

    for body_a in list_a:
        for body_b in list_b:
            if rules.skip_same_body_name and body_a.name == body_b.name:
                continue
            if rules.pair_filter and not rules.pair_filter(body_a, body_b, rules.context):
                continue

            delta = angular_distance(body_a.lon_deg, body_b.lon_deg)
            for aspect in rules.aspect_types:
                orb = abs(delta - aspect.angle_deg)
                allowed_orb = (
                    rules.orb_table(body_a, body_b, aspect, rules.context)
                    if rules.orb_table
                    else aspect.orb_deg
                )
                if orb <= allowed_orb:
                    exactness = 1.0 if allowed_orb == 0 else max(0.0, 1.0 - (orb / allowed_orb))
                    aspects.append(
                        AspectHit(
                            a=body_a,
                            b=body_b,
                            aspect=aspect.name,
                            exactness=exactness,
                            orb_deg=orb,
                            applying_separating=_applying_or_separating(body_a, body_b),
                            weight=aspect.weight,
                        )
                    )
                    break

    aspects.sort(key=lambda hit: (hit.exactness, hit.weight), reverse=True)
    return aspects


def find_transit_aspect_window_result(
    natal_chart: Chart,
    transit_datetime_utc: datetime,
    transit_location: tuple[float, float],
    hit: AspectHit,
    rules: AspectRuleSet,
    *,
    search_days: float = 30.0,
    step_hours: float = 12.0,
    precision_minutes: float = 15.0,
    should_cancel: Callable[[], bool] | None = None,
    diagnostics: dict[str, int | float] | None = None,
) -> TransitAspectWindowResult:
    """
    Estimate ingress/egress datetimes for an active transit aspect.

    Returns UTC datetimes for aspect start/end. If a boundary cannot be found
    inside ``search_days`` around ``transit_datetime_utc`` then ``None`` is returned
    for that side.
    """
    transit_name = hit.a.name
    natal_name = hit.b.name
    natal_lon = natal_chart.positions.get(natal_name)
    if natal_lon is None:
        return TransitAspectWindowResult(None, None)

    aspect_type = next((asp for asp in rules.aspect_types if asp.name == hit.aspect), None)
    if aspect_type is None:
        return TransitAspectWindowResult(None, None)

    center = _ensure_utc(transit_datetime_utc)
    min_scope = datetime.combine(EPHEMERIS_MIN_DATE, datetime.min.time(), tzinfo=timezone.utc)
    max_scope = datetime.combine(EPHEMERIS_MAX_DATE, datetime.max.time(), tzinfo=timezone.utc)
    if center < min_scope or center > max_scope:
        return TransitAspectWindowResult(None, None, out_of_scope=True)

    effective_orb_deg = (
        rules.orb_table(hit.a, hit.b, aspect_type, rules.context)
        if rules.orb_table
        else aspect_type.orb_deg
    )
    if effective_orb_deg <= 0:
        return TransitAspectWindowResult(None, None)

    base_search_days = max(0.25, float(search_days))
    max_span_days = base_search_days
    coarse_step_hours = max(0.25, float(step_hours))

    estimated_motion = _estimate_transit_daily_motion(
        transit_name,
        center,
        transit_location,
    )
    if estimated_motion is not None and estimated_motion > 0:
        # Slow movers (especially Uranus/Neptune/Pluto near stations) can keep
        # an aspect active for many months. A fixed 30-day search window leaves
        # the ingress/egress unresolved, so adapt the scan horizon from motion.
        estimated_half_window_days = (effective_orb_deg / estimated_motion) * 1.5
        # Use a much larger ceiling than 10 years; slow/stationing outer-planet
        # transits can legitimately remain in-orb for far longer and otherwise
        # show up as unresolved "… → …" windows in the UI.
        max_span_days = max(base_search_days, min(36500.0, estimated_half_window_days))

        # Keep scans tractable for ultra-slow movers by widening the coarse
        # stepping interval as apparent daily motion approaches zero.
        if estimated_motion < 0.02:
            coarse_step_hours = max(coarse_step_hours, 72.0)
        if estimated_motion < 0.005:
            coarse_step_hours = max(coarse_step_hours, 24.0 * 7.0)

    max_span = timedelta(days=max_span_days)
    max_scan_span = timedelta(days=36500.0)
    coarse_step = timedelta(hours=coarse_step_hours)
    precision = timedelta(minutes=max(1.0, float(precision_minutes)))

    if diagnostics is not None:
        diagnostics.setdefault("orb_gap_calls", 0)
        diagnostics.setdefault("coarse_scan_steps", 0)
        diagnostics.setdefault("binary_search_steps", 0)

    def _cancel_if_requested() -> None:
        if should_cancel is not None and should_cancel():
            raise TransitAspectWindowCancelled()

    def _orb_gap(at_time: datetime) -> float | None:
        _cancel_if_requested()
        if diagnostics is not None:
            diagnostics["orb_gap_calls"] = int(diagnostics.get("orb_gap_calls", 0)) + 1
        chart = compute_chart(at_time, transit_location, name="Transit aspect scan")
        transit_lon = chart.positions.get(transit_name)
        if transit_lon is None:
            return None
        delta = angular_distance(float(transit_lon), float(natal_lon))
        return abs(delta - aspect_type.angle_deg)

    def _is_active(at_time: datetime) -> bool:
        orb = _orb_gap(at_time)
        return orb is not None and orb <= effective_orb_deg

    if not _is_active(center):
        return TransitAspectWindowResult(None, None)

    def _scan_boundary(direction: int) -> datetime | None:
        active_time = center
        inactive_time: datetime | None = None
        traveled = timedelta(0)
        probe = center
        scope_boundary = min_scope if direction < 0 else max_scope

        while traveled < max_span:
            _cancel_if_requested()
            if diagnostics is not None:
                diagnostics["coarse_scan_steps"] = int(diagnostics.get("coarse_scan_steps", 0)) + 1
            candidate = probe + (coarse_step * direction)
            if direction < 0 and candidate <= min_scope:
                candidate = min_scope
            elif direction > 0 and candidate >= max_scope:
                candidate = max_scope
            probe = candidate
            traveled += coarse_step

            if not _is_active(probe):
                inactive_time = probe
                break
            active_time = probe

            if probe == scope_boundary:
                return scope_boundary

        if inactive_time is None:
            # If we exhausted the initial span while the aspect stayed active,
            # progressively extend the coarse scan out to the hard ceiling.
            while traveled < max_scan_span and probe != scope_boundary:
                _cancel_if_requested()
                if diagnostics is not None:
                    diagnostics["coarse_scan_steps"] = int(diagnostics.get("coarse_scan_steps", 0)) + 1
                candidate = probe + (coarse_step * direction)
                if direction < 0 and candidate <= min_scope:
                    candidate = min_scope
                elif direction > 0 and candidate >= max_scope:
                    candidate = max_scope
                probe = candidate
                traveled += coarse_step

                if not _is_active(probe):
                    inactive_time = probe
                    break
                active_time = probe

                if probe == scope_boundary:
                    return scope_boundary

        if inactive_time is None:
            return None

        # Binary search between active and inactive timestamps.
        if direction < 0:
            low = inactive_time
            high = active_time
        else:
            low = active_time
            high = inactive_time

        while (high - low) > precision:
            _cancel_if_requested()
            if diagnostics is not None:
                diagnostics["binary_search_steps"] = int(diagnostics.get("binary_search_steps", 0)) + 1
            mid = low + (high - low) / 2
            if _is_active(mid):
                if direction < 0:
                    high = mid
                else:
                    low = mid
            else:
                if direction < 0:
                    low = mid
                else:
                    high = mid

        return high if direction < 0 else low

    start_dt = _scan_boundary(-1)
    end_dt = _scan_boundary(1)
    return TransitAspectWindowResult(
        start=start_dt,
        end=end_dt,
        start_truncated_to_scope=bool(start_dt is not None and start_dt == min_scope),
        end_truncated_to_scope=bool(end_dt is not None and end_dt == max_scope),
    )




def find_transit_aspect_window(
    natal_chart: Chart,
    transit_datetime_utc: datetime,
    transit_location: tuple[float, float],
    hit: AspectHit,
    rules: AspectRuleSet,
    *,
    search_days: float = 30.0,
    step_hours: float = 12.0,
    precision_minutes: float = 15.0,
    should_cancel: Callable[[], bool] | None = None,
    diagnostics: dict[str, int | float] | None = None,
) -> tuple[datetime | None, datetime | None]:
    result = find_transit_aspect_window_result(
        natal_chart,
        transit_datetime_utc,
        transit_location,
        hit,
        rules,
        search_days=search_days,
        step_hours=step_hours,
        precision_minutes=precision_minutes,
        should_cancel=should_cancel,
        diagnostics=diagnostics,
    )
    return result.start, result.end


def render_chart_overlay(
    base_chart: NormalizedChart,
    overlays: Iterable[dict[str, BodyPosition]],
    aspects: Iterable[AspectHit],
    style: str,
) -> CompositeChartView:
    """
    Shared composition payload for UI/rendering callers.

    Existing plotting layers can map this object into wheel glyph layers + aspect
    chords without recomputing astro math.
    """
    return CompositeChartView(
        base_chart=base_chart,
        overlays=tuple(overlays),
        aspects=tuple(aspects),
        style=style,
    )


def build_transit_for_person(
    person_chart_id: int,
    transit_datetime_utc: datetime,
    *,
    natal_loader: Callable[[int], Chart],
    include_transit_houses: bool = False,
    transit_location: tuple[float, float] | None = None,
    aspect_rules: AspectRuleSet = TRANSIT_ASPECT_RULES,
) -> CompositeChartView:
    natal_chart = natal_loader(person_chart_id)
    natal = normalize_chart(natal_chart, chart_id=person_chart_id, chart_type="natal", subject_id=person_chart_id)

    if include_transit_houses and transit_location is not None:
        transit_loc = transit_location
    elif include_transit_houses:
        transit_loc = (natal_chart.lat, natal_chart.lon)
    else:
        transit_loc = None

    transit_chart = compute_chart(
        transit_datetime_utc,
        location=transit_loc,
        house_system=natal.houses.system,
        name=f"Transit for {natal_chart.name}",
    )
    transit = normalize_chart(transit_chart, chart_type="transit")

    transit_in_natal = assign_houses(transit.bodies, natal.houses, layer="TRANSIT")

    natal_targets = list(assign_houses(natal.bodies, natal.houses, layer="NATAL").values())
    aspects = compute_aspects(transit_in_natal.values(), natal_targets, aspect_rules)

    return render_chart_overlay(
        base_chart=natal,
        overlays=[transit_in_natal],
        aspects=aspects,
        style="transit_to_natal",
    )


def build_synastry(
    person_a_chart_id: int,
    person_b_chart_id: int,
    *,
    natal_loader: Callable[[int], Chart],
    base_person: str = "A",
    include_two_way_aspects: bool = False,
    aspect_rules: AspectRuleSet = SYNASTRY_ASPECT_RULES,
) -> CompositeChartView:
    a_chart = normalize_chart(natal_loader(person_a_chart_id), chart_id=person_a_chart_id, chart_type="natal", subject_id=person_a_chart_id)
    b_chart = normalize_chart(natal_loader(person_b_chart_id), chart_id=person_b_chart_id, chart_type="natal", subject_id=person_b_chart_id)

    base, overlay = (a_chart, b_chart) if base_person.upper() == "A" else (b_chart, a_chart)
    overlay_tag = "B" if base is a_chart else "A"
    base_tag = "A" if base is a_chart else "B"

    overlay_in_base = assign_houses(overlay.bodies, base.houses, layer=overlay_tag)
    base_targets = assign_houses(base.bodies, base.houses, layer=base_tag)

    aspects = compute_aspects(overlay_in_base.values(), base_targets.values(), aspect_rules)
    if include_two_way_aspects:
        reverse_aspects = compute_aspects(base_targets.values(), overlay_in_base.values(), aspect_rules)
        aspects = sorted([*aspects, *reverse_aspects], key=lambda hit: (hit.exactness, hit.weight), reverse=True)

    return render_chart_overlay(
        base_chart=base,
        overlays=[overlay_in_base],
        aspects=aspects,
        style="synastry",
    )


def angular_distance(a_lon_deg: float, b_lon_deg: float) -> float:
    diff = abs((a_lon_deg % 360.0) - (b_lon_deg % 360.0)) % 360.0
    return min(diff, 360.0 - diff)


def _signed_angular_delta(a_lon_deg: float, b_lon_deg: float) -> float:
    """Return wrapped signed angular delta (a - b) in degrees, in [-180, 180)."""
    return ((a_lon_deg - b_lon_deg + 180.0) % 360.0) - 180.0


def _estimate_transit_daily_motion(
    transit_name: str,
    center_utc: datetime,
    transit_location: tuple[float, float],
) -> float | None:
    """
    Estimate absolute daily motion (deg/day) for the transit body near `center_utc`.

    Uses a centered finite difference to smooth numerical noise and avoid relying
    on retrograde metadata.
    """
    one_day = timedelta(days=1)
    chart_prev = compute_chart(center_utc - one_day, transit_location, name="Transit motion scan")
    chart_next = compute_chart(center_utc + one_day, transit_location, name="Transit motion scan")
    lon_prev = chart_prev.positions.get(transit_name)
    lon_next = chart_next.positions.get(transit_name)
    if lon_prev is None or lon_next is None:
        return None
    two_day_delta = _signed_angular_delta(float(lon_next), float(lon_prev))
    return abs(two_day_delta) / 2.0


def _house_for_longitude(lon_deg: float, cusps: tuple[float, ...] | list[float]) -> int | None:
    if len(cusps) < 12:
        return None
    lon = lon_deg % 360.0
    for i in range(12):
        start = float(cusps[i]) % 360.0
        end = float(cusps[(i + 1) % 12]) % 360.0
        if end <= start:
            end += 360.0
        compare_lon = lon + 360.0 if lon < start else lon
        if start <= compare_lon < end:
            return i + 1
    return None


def _sign_from_longitude(lon_deg: float) -> str:
    signs = (
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    )
    return signs[int((lon_deg % 360.0) // 30)]


def _applying_or_separating(a: BodyPosition, b: BodyPosition) -> str | None:
    if a.speed is None or b.speed is None:
        return None
    relative_speed = a.speed - b.speed
    return "applying" if relative_speed > 0 else "separating"


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
