"""Human Design calculation pipeline (UTC, activations, channels, centers, type)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

from ephemeraldaddy.core.ephemeris import planetary_longitude

if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart

HD_BODIES: tuple[str, ...] = (
    "Sun",
    "Earth",
    "Moon",
    "Rahu",
    "Ketu",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)

# Fixed Rave Mandala gate order (64 equal 5.625° segments).
# Mapping is computed from a fixed boundary at 28°15' Pisces (358.25° tropical).
MANDALA_START_DEGREE = 358.25
MANDALA_GATE_ORDER: tuple[int, ...] = (
    25, 17, 21, 51, 42, 3, 27, 24, 2, 23, 8, 20, 16, 35, 45,
    12, 15, 52, 39, 53, 62, 56, 31, 33, 7, 4, 29, 59, 40, 64, 47,
    6, 46, 18, 48, 57, 32, 50, 28, 44, 1, 43, 14, 34, 9, 5, 26,
    11, 10, 58, 38, 54, 61, 60, 41, 19, 13, 49, 30, 55, 37, 63, 22, 36,
)

CHANNELS: tuple[tuple[int, int, str, str], ...] = (
    (64, 47, "Head", "Ajna"), (61, 24, "Head", "Ajna"), (63, 4, "Head", "Ajna"),
    (17, 62, "Ajna", "Throat"), (43, 23, "Ajna", "Throat"), (11, 56, "Ajna", "Throat"),
    (31, 7, "Throat", "G"), (8, 1, "Throat", "G"), (33, 13, "Throat", "G"),
    (10, 20, "G", "Throat"), (20, 34, "Throat", "Sacral"), (57, 20, "Spleen", "Throat"),
    (12, 22, "Throat", "Solar Plexus"), (35, 36, "Throat", "Solar Plexus"), (45, 21, "Throat", "Ego"),
    (10, 57, "G", "Spleen"), (10, 34, "G", "Sacral"), (57, 34, "Spleen", "Sacral"),
    (1, 8, "G", "Throat"), (25, 51, "G", "Ego"), (2, 14, "G", "Sacral"),
    (15, 5, "G", "Sacral"), (46, 29, "G", "Sacral"), (7, 31, "G", "Throat"),
    (13, 33, "G", "Throat"), (37, 40, "Solar Plexus", "Ego"), (22, 12, "Solar Plexus", "Throat"),
    (6, 59, "Solar Plexus", "Sacral"), (30, 41, "Solar Plexus", "Root"), (49, 19, "Solar Plexus", "Root"),
    (39, 55, "Root", "Solar Plexus"), (21, 45, "Ego", "Throat"), (26, 44, "Ego", "Spleen"),
    (51, 25, "Ego", "G"), (27, 50, "Sacral", "Spleen"), (34, 10, "Sacral", "G"),
    (34, 57, "Sacral", "Spleen"), (9, 52, "Sacral", "Root"), (3, 60, "Sacral", "Root"),
    (42, 53, "Sacral", "Root"), (32, 54, "Spleen", "Root"), (28, 38, "Spleen", "Root"),
    (18, 58, "Spleen", "Root"),
)

MOTOR_CENTERS = {"Ego", "Solar Plexus", "Root", "Sacral"}


@dataclass(frozen=True)
class HDActivation:
    body: str
    side: Literal["personality", "design"]
    longitude: float
    gate: int
    line: int
    color: int
    tone: int
    base: int
    style: Literal["black", "red", "combined"]


@dataclass(frozen=True)
class HumanDesignResult:
    birth_utc: datetime
    design_utc: datetime
    personality_activations: tuple[HDActivation, ...]
    design_activations: tuple[HDActivation, ...]
    active_gates: frozenset[int]
    defined_channels: tuple[tuple[int, int, str, str], ...]
    defined_centers: frozenset[str]
    hd_type: str
    authority: str
    profile: str
    strategy: str
    split_definition: str
    incarnation_cross: str


def _norm360(value: float) -> float:
    return value % 360.0


def _angular_diff(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _mandala_components(longitude: float) -> tuple[int, int, int, int, int]:
    lon = _norm360(float(longitude))
    gate_width = 360.0 / 64.0
    adjusted = _norm360(lon - MANDALA_START_DEGREE)
    segment_index = int(adjusted // gate_width)
    gate = MANDALA_GATE_ORDER[segment_index]
    offset_in_gate = adjusted - (segment_index * gate_width)
    line_width = gate_width / 6.0
    color_width = line_width / 6.0
    tone_width = color_width / 6.0
    base_width = tone_width / 5.0
    line = min(6, int(offset_in_gate // line_width) + 1)
    in_line = offset_in_gate - ((line - 1) * line_width)
    color = min(6, int(in_line // color_width) + 1)
    in_color = in_line - ((color - 1) * color_width)
    tone = min(6, int(in_color // tone_width) + 1)
    in_tone = in_color - ((tone - 1) * tone_width)
    base = min(5, int(in_tone // base_width) + 1)
    return gate, line, color, tone, base


def _body_longitudes(at_utc: datetime) -> dict[str, float]:
    sun = planetary_longitude(at_utc, "Sun")
    moon = planetary_longitude(at_utc, "Moon")
    north_node = planetary_longitude(at_utc, "Rahu")
    mercury = planetary_longitude(at_utc, "Mercury")
    venus = planetary_longitude(at_utc, "Venus")
    mars = planetary_longitude(at_utc, "Mars")
    jupiter = planetary_longitude(at_utc, "Jupiter")
    saturn = planetary_longitude(at_utc, "Saturn")
    uranus = planetary_longitude(at_utc, "Uranus")
    neptune = planetary_longitude(at_utc, "Neptune")
    pluto = planetary_longitude(at_utc, "Pluto")
    if sun is None or moon is None or north_node is None:
        raise ValueError("Missing required Swiss Ephemeris values for Human Design.")
    return {
        "Sun": _norm360(sun),
        "Earth": _norm360(sun + 180.0),
        "Moon": _norm360(moon),
        "Rahu": _norm360(north_node),
        "Ketu": _norm360(north_node + 180.0),
        "Mercury": _norm360(float(mercury or 0.0)),
        "Venus": _norm360(float(venus or 0.0)),
        "Mars": _norm360(float(mars or 0.0)),
        "Jupiter": _norm360(float(jupiter or 0.0)),
        "Saturn": _norm360(float(saturn or 0.0)),
        "Uranus": _norm360(float(uranus or 0.0)),
        "Neptune": _norm360(float(neptune or 0.0)),
        "Pluto": _norm360(float(pluto or 0.0)),
    }


def _solve_design_utc(birth_utc: datetime, personality_sun: float) -> datetime:
    target = _norm360(personality_sun - 88.0)
    start = birth_utc - timedelta(days=100)
    end = birth_utc - timedelta(days=80)
    step = timedelta(hours=6)
    probe = start
    prev_t = start
    prev_f = _angular_diff(float(planetary_longitude(start, "Sun") or 0.0), target)
    bracket: tuple[datetime, datetime] | None = None
    while probe <= end:
        f = _angular_diff(float(planetary_longitude(probe, "Sun") or 0.0), target)
        if prev_f == 0 or (prev_f < 0 <= f) or (prev_f > 0 >= f):
            bracket = (prev_t, probe)
            break
        prev_t, prev_f = probe, f
        probe += step
    if bracket is None:
        return birth_utc - timedelta(days=88)
    lo, hi = bracket
    flo = _angular_diff(float(planetary_longitude(lo, "Sun") or 0.0), target)
    for _ in range(50):
        mid = lo + (hi - lo) / 2
        fmid = _angular_diff(float(planetary_longitude(mid, "Sun") or 0.0), target)
        if abs(fmid) < 1e-6 or (hi - lo).total_seconds() <= 1:
            return mid
        if (flo < 0 <= fmid) or (flo > 0 >= fmid):
            hi = mid
        else:
            lo = mid
            flo = fmid
    return lo + (hi - lo) / 2


def _resolve_type(defined_centers: set[str], defined_channels: tuple[tuple[int, int, str, str], ...]) -> str:
    if not defined_centers:
        return "Reflector"
    sacral_defined = "Sacral" in defined_centers
    if sacral_defined:
        return "Manifesting Generator" if _has_motor_to_throat_path(defined_centers, defined_channels) else "Generator"
    return "Manifestor" if _has_motor_to_throat_path(defined_centers, defined_channels) else "Projector"


def _has_motor_to_throat_path(
    defined_centers: set[str],
    defined_channels: tuple[tuple[int, int, str, str], ...],
) -> bool:
    if "Throat" not in defined_centers:
        return False
    graph: dict[str, set[str]] = {}
    for _ga, _gb, c1, c2 in defined_channels:
        graph.setdefault(c1, set()).add(c2)
        graph.setdefault(c2, set()).add(c1)
    frontier = {"Throat"}
    seen = set(frontier)
    while frontier:
        next_frontier: set[str] = set()
        for center in frontier:
            for neighbor in graph.get(center, set()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier
    return any(center in seen for center in MOTOR_CENTERS if center in defined_centers)


def _centers_connected(
    center_a: str,
    center_b: str,
    defined_channels: tuple[tuple[int, int, str, str], ...],
) -> bool:
    if center_a == center_b:
        return True
    graph: dict[str, set[str]] = {}
    for _gate_a, _gate_b, c1, c2 in defined_channels:
        graph.setdefault(c1, set()).add(c2)
        graph.setdefault(c2, set()).add(c1)
    frontier = {center_a}
    seen: set[str] = set()
    while frontier:
        next_frontier: set[str] = set()
        for center in frontier:
            if center in seen:
                continue
            if center == center_b:
                return True
            seen.add(center)
            next_frontier.update(graph.get(center, set()) - seen)
        frontier = next_frontier
    return False


def _resolve_authority(
    hd_type: str,
    defined_centers: set[str],
    defined_channels: tuple[tuple[int, int, str, str], ...],
) -> str:
    if hd_type == "Reflector":
        return "Lunar"
    if "Solar Plexus" in defined_centers:
        return "Emotional"
    if "Sacral" in defined_centers:
        return "Sacral"
    if "Spleen" in defined_centers:
        return "Splenic"
    if hd_type == "Manifestor" and _centers_connected("Ego", "Throat", defined_channels):
        return "Ego Manifested"
    if hd_type == "Projector" and _centers_connected("Ego", "G", defined_channels):
        return "Ego Projected"
    if hd_type == "Projector" and _centers_connected("G", "Throat", defined_channels):
        return "Self-Projected"
    if hd_type == "Projector" and _centers_connected("Ajna", "Throat", defined_channels):
        return "Mental (Environmental / Sounding Board)"
    return "No Inner Authority"


def _resolve_strategy(hd_type: str) -> str:
    if hd_type in {"Generator", "Manifesting Generator"}:
        return "To Respond"
    if hd_type == "Manifestor":
        return "To Inform"
    if hd_type == "Projector":
        return "Wait for the Invitation"
    return "Wait a Lunar Cycle"


def _split_definition(defined_channels: tuple[tuple[int, int, str, str], ...]) -> str:
    graph: dict[str, set[str]] = {}
    for _gate_a, _gate_b, center_a, center_b in defined_channels:
        graph.setdefault(center_a, set()).add(center_b)
        graph.setdefault(center_b, set()).add(center_a)
    if not graph:
        return "No Definition"
    components = 0
    seen: set[str] = set()
    for center in graph:
        if center in seen:
            continue
        components += 1
        frontier = {center}
        while frontier:
            next_frontier: set[str] = set()
            for node in frontier:
                if node in seen:
                    continue
                seen.add(node)
                next_frontier.update(graph.get(node, set()) - seen)
            frontier = next_frontier
    if components == 1:
        return "Single Definition"
    if components == 2:
        return "Split Definition"
    if components == 3:
        return "Triple Split Definition"
    return "Quadruple Split Definition"


INCARNATION_CROSS_LOOKUP: dict[tuple[int, int, int, int], str] = {}


def _incarnation_cross_angle(line: int) -> str:
    if line in (1, 2, 3):
        return "Right Angle"
    if line == 4:
        return "Juxtaposition"
    return "Left Angle"


def _resolve_incarnation_cross(
    personality_sun: HDActivation,
    personality_earth: HDActivation,
    design_sun: HDActivation,
    design_earth: HDActivation,
) -> str:
    key = (personality_sun.gate, personality_earth.gate, design_sun.gate, design_earth.gate)
    named = INCARNATION_CROSS_LOOKUP.get(key)
    if named:
        return named
    angle = _incarnation_cross_angle(personality_sun.line)
    return (
        f"{angle} Incarnation (gates {personality_sun.gate}/{personality_earth.gate}"
        f" • {design_sun.gate}/{design_earth.gate})"
    )


def calculate_human_design(chart: "Chart") -> HumanDesignResult:
    birth_utc = chart.dt.astimezone(timezone.utc)
    personality = _body_longitudes(birth_utc)
    design_utc = _solve_design_utc(birth_utc, personality["Sun"])
    design = _body_longitudes(design_utc)

    p_components = {name: _mandala_components(lon) for name, lon in personality.items()}
    d_components = {name: _mandala_components(lon) for name, lon in design.items()}
    p_gate_set = {components[0] for components in p_components.values()}
    d_gate_set = {components[0] for components in d_components.values()}
    active_gates = p_gate_set | d_gate_set

    def style_for_gate(gate: int, side: str) -> Literal["black", "red", "combined"]:
        if gate in p_gate_set and gate in d_gate_set:
            return "combined"
        return "black" if side == "personality" else "red"

    personality_activations = tuple(
        HDActivation(
            body=body,
            side="personality",
            longitude=personality[body],
            gate=gate,
            line=line,
            color=color,
            tone=tone,
            base=base,
            style=style_for_gate(gate, "personality"),
        )
        for body, (gate, line, color, tone, base) in ((name, p_components[name]) for name in HD_BODIES)
    )
    design_activations = tuple(
        HDActivation(
            body=body,
            side="design",
            longitude=design[body],
            gate=gate,
            line=line,
            color=color,
            tone=tone,
            base=base,
            style=style_for_gate(gate, "design"),
        )
        for body, (gate, line, color, tone, base) in ((name, d_components[name]) for name in HD_BODIES)
    )

    unique_channels: dict[tuple[int, int], tuple[int, int, str, str]] = {}
    for channel in CHANNELS:
        gate_a, gate_b, _center_a, _center_b = channel
        if gate_a not in active_gates or gate_b not in active_gates:
            continue
        channel_key = tuple(sorted((gate_a, gate_b)))
        unique_channels.setdefault(channel_key, channel)
    defined_channels = tuple(unique_channels.values())
    defined_centers = frozenset({c for _g1, _g2, c1, c2 in defined_channels for c in (c1, c2)})
    hd_type = _resolve_type(set(defined_centers), defined_channels)
    authority = _resolve_authority(hd_type, set(defined_centers), defined_channels)
    strategy = _resolve_strategy(hd_type)
    split_definition = _split_definition(defined_channels)
    personality_sun_line = p_components["Sun"][1]
    design_sun_line = d_components["Sun"][1]
    profile = f"{personality_sun_line}/{design_sun_line}"
    p_sun = next(item for item in personality_activations if item.body == "Sun")
    p_earth = next(item for item in personality_activations if item.body == "Earth")
    d_sun = next(item for item in design_activations if item.body == "Sun")
    d_earth = next(item for item in design_activations if item.body == "Earth")
    incarnation_cross = _resolve_incarnation_cross(p_sun, p_earth, d_sun, d_earth)

    return HumanDesignResult(
        birth_utc=birth_utc,
        design_utc=design_utc,
        personality_activations=personality_activations,
        design_activations=design_activations,
        active_gates=frozenset(active_gates),
        defined_channels=defined_channels,
        defined_centers=defined_centers,
        hd_type=hd_type,
        authority=authority,
        profile=profile,
        strategy=strategy,
        split_definition=split_definition,
        incarnation_cross=incarnation_cross,
    )
