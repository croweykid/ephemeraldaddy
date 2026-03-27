from __future__ import annotations

"""
Foundational axes plus class-family gates and class scoring for assigning
D&D-style classes from an astrological chart or other symbolic profile.

Design rules:
1) Axes describe durable behavioral dimensions.
2) Family gates are soft priors, not absolute doors.
3) Class scores come from direct axis logic plus family affinity.
4) Avoid costume logic such as "smart = Wizard" or "pretty = Bard".
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import warnings

from ephemeraldaddy.core.interpretations import (
    ASPECT_ANGLE_DEGREES,
    ASPECT_ORB_ALLOWANCES,
    ASPECT_SCORE_WEIGHTS,
    MODES,
    NATAL_BODY_LOUDNESS,
    SIGN_ELEMENTS,
    ZODIAC_NAMES,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_element_weights,
    calculate_dominant_house_weights,
    calculate_dominant_planet_weights,
    calculate_mode_weights,
)
from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_CLASS_SUBCLASS_EXPLAINERS

class AxisCategory(str, Enum):
    """High-level grouping for class-assignment axes."""

    SOURCE = "source"
    ROLE = "role"
    STYLE = "style"
    SOCIAL = "social"


@dataclass(frozen=True)
class AxisDefinition:
    """Definition of one latent class-classification axis."""

    key: str
    display_name: str
    category: AxisCategory
    description: str
    classifier_question: str
    feature_hints: Tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


CLASS_AXES: Dict[str, AxisDefinition] = {
    "discipline": AxisDefinition(
        key="discipline",
        display_name="Discipline",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for deliberate training, structure, repetition, restraint, "
            "and controlled execution."
        ),
        classifier_question=(
            "Does this chart solve problems through method, regimen, and practiced control?"
        ),
        feature_hints=(
            "Saturn prominence",
            "Mars-Saturn contact",
            "Angular/6th/10th emphasis",
            "Cardinal or fixed stability",
        ),
        notes="Core driver for Fighter, Monk, Paladin, and some Artificer/Wizard lanes.",
    ),
    "instinct": AxisDefinition(
        key="instinct",
        display_name="Instinct",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for visceral response, bodily intelligence, impulse, survival timing, "
            "and acting before a formal theory arrives."
        ),
        classifier_question=(
            "Does this chart move by gut, appetite, reactivity, and embodied knowing?"
        ),
        feature_hints=(
            "Moon prominence",
            "Mars prominence",
            "Fire/Earth emphasis",
            "1st/4th/12th emphasis",
        ),
        notes="Core driver for Barbarian, primal Druid lanes, and some Ranger/Monk paths.",
    ),
    "study": AxisDefinition(
        key="study",
        display_name="Study",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for learning systems, accumulating technique, analyzing patterns, "
            "and mastering a craft through knowledge."
        ),
        classifier_question=(
            "Does this chart gain power through study, categorization, and system mastery?"
        ),
        feature_hints=(
            "Mercury prominence",
            "Mercury-Saturn contact",
            "3rd/6th/9th/10th emphasis",
            "Air/Earth blend",
        ),
        notes="Core driver for Wizard, Artificer, and technical Rogue/Fighter subclasses.",
    ),
    "faith": AxisDefinition(
        key="faith",
        display_name="Faith",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for devotion, moral alignment, higher-order meaning, sacred service, "
            "and trust in an orienting principle larger than the self."
        ),
        classifier_question=(
            "Does this chart operate through devotion, oath, doctrine, or consecrated purpose?"
        ),
        feature_hints=(
            "Jupiter prominence",
            "Neptune prominence",
            "Sun-Jupiter contact",
            "9th/12th emphasis",
        ),
        notes="Core driver for Cleric, Paladin, and some Druid paths.",
    ),
    "innate_power": AxisDefinition(
        key="innate_power",
        display_name="Innate Power",
        category=AxisCategory.SOURCE,
        description=(
            "Sense that power is native, internal, and already present rather than earned from "
            "study or borrowed from hierarchy."
        ),
        classifier_question=(
            "Does this chart treat power as a built-in condition rather than a learned tool?"
        ),
        feature_hints=(
            "Sun prominence",
            "Jupiter prominence",
            "Pluto or Neptune voltage",
            "1st/5th/8th emphasis",
        ),
        notes="Core driver for Sorcerer and some highly charismatic subclass lanes.",
    ),
    "patron_reliance": AxisDefinition(
        key="patron_reliance",
        display_name="Patron Reliance",
        category=AxisCategory.SOURCE,
        description=(
            "Orientation toward power mediated by pact, outside agency, taboo exchange, debt, "
            "initiation, or negotiated access."
        ),
        classifier_question=(
            "Does this chart reach power through compact, exchange, or entanglement with what lies outside the ordinary self?"
        ),
        feature_hints=(
            "Pluto prominence",
            "Neptune-Pluto contact",
            "Saturn-Pluto contact",
            "8th/12th emphasis",
        ),
        notes="Core driver for Warlock and certain occult subclass lanes.",
    ),
    "performance": AxisDefinition(
        key="performance",
        display_name="Performance",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for shaping reality through expression, presentation, rhetoric, style, "
            "timing, and emotional modulation."
        ),
        classifier_question=(
            "Does this chart alter outcomes through presentation, voice, style, or social staging?"
        ),
        feature_hints=(
            "Venus prominence",
            "Mercury prominence",
            "3rd/5th/7th/10th emphasis",
            "Libra/Leo/Pisces signatures",
        ),
        notes="Core driver for Bard and many socially expressive subclass lanes.",
    ),
    "nature_attunement": AxisDefinition(
        key="nature_attunement",
        display_name="Nature Attunement",
        category=AxisCategory.SOURCE,
        description=(
            "Sensitivity to cycles, land, weather, animals, seasons, ecological timing, and "
            "non-urban forms of intelligence."
        ),
        classifier_question=(
            "Does this chart align with the living world, its cycles, and non-civilized rhythms?"
        ),
        feature_hints=(
            "Moon prominence",
            "Venus/Jupiter support",
            "4th/6th/9th/12th emphasis",
            "Water/Earth blend",
        ),
        notes="Core driver for Druid and Ranger families.",
    ),
    "technical_inventiveness": AxisDefinition(
        key="technical_inventiveness",
        display_name="Technical Inventiveness",
        category=AxisCategory.SOURCE,
        description=(
            "Preference for tools, engineered solutions, modular systems, tinkering, elegant "
            "workarounds, and practical invention."
        ),
        classifier_question=(
            "Does this chart solve problems by building, modifying, or engineering solutions?"
        ),
        feature_hints=(
            "Mercury-Uranus contact",
            "Mercury-Saturn contact",
            "3rd/6th/10th/11th emphasis",
            "Air/Earth emphasis",
        ),
        notes="Core driver for Artificer and technical subclass branches elsewhere.",
    ),
    "stealth_indirection": AxisDefinition(
        key="stealth_indirection",
        display_name="Stealth / Indirection",
        category=AxisCategory.ROLE,
        description=(
            "Preference for flanking routes, concealment, timing, infiltration, feints, social or "
            "psychological maneuvering, and precision over spectacle."
        ),
        classifier_question=(
            "Does this chart win through angle, timing, concealment, or indirect leverage?"
        ),
        feature_hints=(
            "Mercury prominence",
            "Scorpio or mutable signatures",
            "8th/12th emphasis",
            "Mercury-Pluto or Mercury-Neptune contact",
        ),
        notes="Core role axis for Rogue, some Ranger, some Bard, and occult trickster lanes.",
    ),
    "frontline_courage": AxisDefinition(
        key="frontline_courage",
        display_name="Frontline Courage",
        category=AxisCategory.ROLE,
        description=(
            "Willingness to meet conflict directly, hold ground, absorb pressure, and remain visibly "
            "present when things become expensive."
        ),
        classifier_question=(
            "Does this chart meet danger head-on rather than triangulating around it?"
        ),
        feature_hints=(
            "Mars prominence",
            "Sun prominence",
            "1st/10th emphasis",
            "Cardinal or fixed fire/earth",
        ),
        notes="Core role axis for Fighter, Barbarian, Paladin, and battle-forward hybrids.",
    ),
    "control_planning": AxisDefinition(
        key="control_planning",
        display_name="Control / Planning",
        category=AxisCategory.ROLE,
        description=(
            "Preference for shaping the field in advance, limiting opponent options, arranging "
            "sequence, and treating conflict as architecture rather than collision."
        ),
        classifier_question=(
            "Does this chart prefer to govern the board, sequence events, and reduce uncertainty?"
        ),
        feature_hints=(
            "Saturn prominence",
            "Mercury prominence",
            "Uranus or Neptune support",
            "6th/8th/10th/11th emphasis",
        ),
        notes="Core role axis for Wizard, Artificer, Mastermind-style Rogue, and tactical subclasses.",
    ),
    "mercy_restoration": AxisDefinition(
        key="mercy_restoration",
        display_name="Mercy / Restoration",
        category=AxisCategory.ROLE,
        description=(
            "Orientation toward healing, repair, stabilization, care, and the conservation or "
            "restoration of life and function."
        ),
        classifier_question=(
            "Does this chart move toward healing, repair, and preservation under stress?"
        ),
        feature_hints=(
            "Moon-Venus-Jupiter support",
            "6th/12th emphasis",
            "Cancer/Pisces/Virgo signatures",
            "Benefic dominance",
        ),
        notes="Core role axis for Cleric, Druid, healing Bard lanes, and support-focused hybrids.",
    ),
    "risk_appetite": AxisDefinition(
        key="risk_appetite",
        display_name="Risk Appetite",
        category=AxisCategory.STYLE,
        description=(
            "Tolerance for volatility, improvisation, dramatic bets, unstable power sources, and "
            "high-upside uncertain plays."
        ),
        classifier_question=(
            "Does this chart willingly gamble on unstable force, speed, or dramatic payoff?"
        ),
        feature_hints=(
            "Mars-Uranus contact",
            "Jupiter-Uranus contact",
            "Fire or mutable emphasis",
            "5th/8th/11th emphasis",
        ),
        notes="Useful for distinguishing steady classes from volatile subclasses or multiclass shadows.",
    ),
    "social_leadership": AxisDefinition(
        key="social_leadership",
        display_name="Social Leadership",
        category=AxisCategory.SOCIAL,
        description=(
            "Capacity to gather, direct, inspire, persuade, or represent a group through presence, "
            "confidence, and social gravity."
        ),
        classifier_question=(
            "Does this chart naturally organize people around itself or speak for a collective?"
        ),
        feature_hints=(
            "Sun/Jupiter/Venus prominence",
            "7th/10th/11th emphasis",
            "Leo/Libra/Sagittarius signatures",
            "Strong angular charisma planets",
        ),
        notes="Important for Bard, Paladin, Cleric, some Fighter, and some Sorcerer lanes.",
    ),
}


AXIS_ORDER: Tuple[str, ...] = tuple(CLASS_AXES.keys())
SOURCE_AXES: Tuple[str, ...] = tuple(
    key for key, axis in CLASS_AXES.items() if axis.category == AxisCategory.SOURCE
)
ROLE_AXES: Tuple[str, ...] = tuple(
    key for key, axis in CLASS_AXES.items() if axis.category == AxisCategory.ROLE
)
STYLE_AXES: Tuple[str, ...] = tuple(
    key for key, axis in CLASS_AXES.items() if axis.category == AxisCategory.STYLE
)
SOCIAL_AXES: Tuple[str, ...] = tuple(
    key for key, axis in CLASS_AXES.items() if axis.category == AxisCategory.SOCIAL
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def empty_axis_scores() -> Dict[str, float]:
    return {key: 0.0 for key in AXIS_ORDER}


def validate_axis_scores(scores: Mapping[str, float]) -> None:
    missing = [key for key in AXIS_ORDER if key not in scores]
    unknown = [key for key in scores if key not in CLASS_AXES]
    if missing or unknown:
        bits: List[str] = []
        if missing:
            bits.append(f"missing={missing}")
        if unknown:
            bits.append(f"unknown={unknown}")
        raise ValueError("Invalid axis score mapping: " + "; ".join(bits))


def axis_subset(scores: Mapping[str, float], keys: Iterable[str]) -> Dict[str, float]:
    return {key: float(scores.get(key, 0.0)) for key in keys}


def axis_display_table() -> str:
    lines: List[str] = []
    for key in AXIS_ORDER:
        axis = CLASS_AXES[key]
        hints = ", ".join(axis.feature_hints)
        lines.append(f"[{axis.category.value}] {axis.display_name} ({axis.key})")
        lines.append(f"  {axis.description}")
        lines.append(f"  Q: {axis.classifier_question}")
        if hints:
            lines.append(f"  Hints: {hints}")
        if axis.notes:
            lines.append(f"  Notes: {axis.notes}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _weighted_average(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total_weight = sum(max(0.0, float(w)) for w in weights.values())
    if total_weight <= 0:
        return 0.0
    total = 0.0
    for key, weight in weights.items():
        total += float(values.get(key, 0.0)) * float(weight)
    return _clamp01(total / total_weight)


def _weighted_penalty(values: Mapping[str, float], penalties: Mapping[str, float]) -> float:
    total_weight = sum(max(0.0, float(w)) for w in penalties.values())
    if total_weight <= 0:
        return 0.0
    total = 0.0
    for key, weight in penalties.items():
        total += float(values.get(key, 0.0)) * float(weight)
    return _clamp01(total / total_weight)


def _synergy_average(values: Mapping[str, float], keys: Sequence[str]) -> float:
    if not keys:
        return 0.0
    return _clamp01(sum(float(values.get(key, 0.0)) for key in keys) / len(keys))


# ---------------------------------------------------------------------------
# Chart feature extraction + provisional axis scoring
# ---------------------------------------------------------------------------

ALL_SIGNS: Tuple[str, ...] = tuple(SIGN_ELEMENTS.keys())
SIGN_TO_MODE: Dict[str, str] = {
    sign: mode for mode, signs in MODES.items() for sign in signs
}
BODY_WEIGHT_SCALE = max(float(v) for v in NATAL_BODY_LOUDNESS.values()) if NATAL_BODY_LOUDNESS else 1.0
BODY_WEIGHTS: Dict[str, float] = {
    body: float(weight) / BODY_WEIGHT_SCALE for body, weight in NATAL_BODY_LOUDNESS.items()
}
ANGULAR_HOUSES = {1, 4, 7, 10}
EMPHASIS_HOUSE_GROUPS: Dict[str, Tuple[int, ...]] = {
    "self": (1, 5, 8),
    "discipline": (6, 10),
    "secrecy": (8, 12),
    "social": (7, 10, 11),
    "meaning": (9, 12),
    "craft": (3, 6, 10),
    "healing": (6, 12),
    "wild": (4, 9, 12),
}
DERIVED_ASPECTS: Sequence[Tuple[str, float, float]] = tuple(
    (name, float(ASPECT_ANGLE_DEGREES[name]), float(ASPECT_ORB_ALLOWANCES[name]))
    for name in ASPECT_SCORE_WEIGHTS
    if name in ASPECT_ANGLE_DEGREES and name in ASPECT_ORB_ALLOWANCES
)


@dataclass(frozen=True)
class AxisFeatureSet:
    planet_prominence: Mapping[str, float]
    element_balance: Mapping[str, float]
    mode_balance: Mapping[str, float]
    house_emphasis: Mapping[str, float]
    aspect_signals: Mapping[str, float]


@dataclass(frozen=True)
class DnDStatBlock:
    """Display-oriented D&D stat profile derived from axis/features."""

    raw_scores: Mapping[str, float]
    scores: Mapping[str, int]
    modifiers: Mapping[str, int]


class ClassAxisScorer:
    def __init__(self, *, default_orb_deg: float = 6.0) -> None:
        self.default_orb_deg = float(default_orb_deg)

    def score_chart(self, chart: Any) -> Dict[str, float]:
        return self.score_axes(self.extract_features(chart))

    def extract_features(self, chart: Any) -> AxisFeatureSet:
        positions = self._get_positions(chart)
        aspects = self._get_aspects(chart, positions)
        if not isinstance(chart, Mapping):
            dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
            is_placeholder = bool(getattr(chart, "is_placeholder", False))
            if not is_placeholder and not dominant_planet_weights:
                chart.dominant_planet_weights = calculate_dominant_planet_weights(chart)

        planet_prominence = self._planet_prominence(chart, positions)
        element_balance = self._element_balance(chart, positions)
        mode_balance = self._mode_balance(chart, positions)
        house_emphasis = self._house_emphasis(chart, positions)
        aspect_signals = self._aspect_signals(aspects)

        return AxisFeatureSet(
            planet_prominence=planet_prominence,
            element_balance=element_balance,
            mode_balance=mode_balance,
            house_emphasis=house_emphasis,
            aspect_signals=aspect_signals,
        )

    def score_axes(self, features: AxisFeatureSet) -> Dict[str, float]:
        scores = empty_axis_scores()
        p = features.planet_prominence
        e = features.element_balance
        m = features.mode_balance
        h = features.house_emphasis
        a = features.aspect_signals

        scores["discipline"] = (
            0.42 * p.get("Saturn", 0.0)
            + 0.24 * p.get("Mars", 0.0)
            + 0.22 * h.get("discipline", 0.0)
            + 0.12 * m.get("fixed", 0.0)
        )
        scores["instinct"] = (
            0.37 * p.get("Moon", 0.0)
            + 0.25 * p.get("Mars", 0.0)
            + 0.18 * (e.get("Fire", 0.0) + e.get("Earth", 0.0))
            + 0.20 * h.get("wild", 0.0)
        )
        scores["study"] = (
            0.45 * p.get("Mercury", 0.0)
            + 0.22 * p.get("Saturn", 0.0)
            + 0.18 * h.get("craft", 0.0)
            + 0.15 * (e.get("Air", 0.0) + e.get("Earth", 0.0))
        )
        scores["faith"] = (
            0.44 * p.get("Jupiter", 0.0)
            + 0.21 * p.get("Neptune", 0.0)
            + 0.23 * h.get("meaning", 0.0)
            + 0.12 * a.get("cohesion", 0.0)
        )
        scores["innate_power"] = (
            0.34 * p.get("Sun", 0.0)
            + 0.26 * p.get("Jupiter", 0.0)
            + 0.20 * p.get("Pluto", 0.0)
            + 0.20 * h.get("self", 0.0)
        )
        scores["patron_reliance"] = (
            0.40 * p.get("Pluto", 0.0)
            + 0.24 * p.get("Neptune", 0.0)
            + 0.22 * h.get("secrecy", 0.0)
            + 0.14 * a.get("tension", 0.0)
        )
        scores["performance"] = (
            0.34 * p.get("Venus", 0.0)
            + 0.24 * p.get("Mercury", 0.0)
            + 0.26 * h.get("social", 0.0)
            + 0.16 * (e.get("Air", 0.0) + e.get("Fire", 0.0))
        )
        scores["nature_attunement"] = (
            0.34 * p.get("Moon", 0.0)
            + 0.22 * p.get("Venus", 0.0)
            + 0.22 * p.get("Jupiter", 0.0)
            + 0.22 * h.get("wild", 0.0)
        )
        scores["technical_inventiveness"] = (
            0.42 * p.get("Mercury", 0.0)
            + 0.23 * p.get("Uranus", 0.0)
            + 0.20 * p.get("Saturn", 0.0)
            + 0.15 * h.get("craft", 0.0)
        )
        scores["stealth_indirection"] = (
            0.33 * p.get("Mercury", 0.0)
            + 0.27 * p.get("Pluto", 0.0)
            + 0.20 * p.get("Neptune", 0.0)
            + 0.20 * h.get("secrecy", 0.0)
        )
        scores["frontline_courage"] = (
            0.42 * p.get("Mars", 0.0)
            + 0.26 * p.get("Sun", 0.0)
            + 0.20 * h.get("self", 0.0)
            + 0.12 * e.get("Fire", 0.0)
        )
        scores["control_planning"] = (
            0.38 * p.get("Saturn", 0.0)
            + 0.28 * p.get("Mercury", 0.0)
            + 0.22 * h.get("craft", 0.0)
            + 0.12 * m.get("cardinal", 0.0)
        )
        scores["mercy_restoration"] = (
            0.33 * p.get("Moon", 0.0)
            + 0.29 * p.get("Venus", 0.0)
            + 0.22 * p.get("Jupiter", 0.0)
            + 0.16 * h.get("healing", 0.0)
        )
        scores["risk_appetite"] = (
            0.32 * p.get("Mars", 0.0)
            + 0.28 * p.get("Uranus", 0.0)
            + 0.20 * p.get("Jupiter", 0.0)
            + 0.20 * a.get("volatility", 0.0)
        )
        scores["social_leadership"] = (
            0.34 * p.get("Sun", 0.0)
            + 0.24 * p.get("Jupiter", 0.0)
            + 0.20 * p.get("Venus", 0.0)
            + 0.22 * h.get("social", 0.0)
        )

        return {key: _clamp01(value) for key, value in scores.items()}

    @staticmethod
    def _first_non_none(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _angular_distance(a: float, b: float) -> float:
        delta = abs((a - b) % 360.0)
        return min(delta, 360.0 - delta)

    def _normalize_aspect_name(self, name: str) -> str:
        return str(name).strip().lower().replace(" ", "").replace("-", "")

    def _sign_for_longitude(self, lon: float) -> str:
        index = int((lon % 360.0) // 30.0) % 12
        return ALL_SIGNS[index]

    def _house_for_longitude(self, houses: Any, lon: float) -> Optional[int]:
        if not houses:
            return None
        if isinstance(houses, Mapping):
            for house_key, value in houses.items():
                try:
                    cusp = float(value)
                except (TypeError, ValueError):
                    continue
                next_house = (int(house_key) % 12) + 1
                next_value = houses.get(next_house, houses.get(str(next_house)))
                if next_value is None:
                    continue
                try:
                    next_cusp = float(next_value)
                except (TypeError, ValueError):
                    continue
                start = cusp % 360.0
                end = next_cusp % 360.0
                if start <= end and start <= lon < end:
                    return int(house_key)
                if start > end and (lon >= start or lon < end):
                    return int(house_key)
        return None

    def _from_native_chart(self, chart: Any) -> Dict[str, Dict[str, Any]]:
        raw_positions = getattr(chart, "positions", {}) or {}
        houses = getattr(chart, "houses", None)
        out: Dict[str, Dict[str, Any]] = {}
        for body, raw in raw_positions.items():
            lon: Optional[float] = None
            sign: Optional[str] = None
            house: Optional[int] = None
            if isinstance(raw, Mapping):
                lon = self._first_non_none(raw.get("lon"), raw.get("longitude"), raw.get("ecl_lon"), raw.get("deg"))
                sign = raw.get("sign")
                house = raw.get("house")
            else:
                try:
                    lon = float(raw)
                except (TypeError, ValueError):
                    lon = None

            if lon is not None:
                lon = float(lon) % 360.0
                sign = str(sign) if sign else self._sign_for_longitude(lon)
                if house is None:
                    house = self._house_for_longitude(houses, lon)

            if lon is None and sign is None:
                continue
            out[str(body)] = {
                "lon": lon,
                "sign": str(sign) if sign else None,
                "house": int(house) if house is not None else None,
            }
        return out

    def _get_positions(self, chart: Any) -> Dict[str, Dict[str, Any]]:
        if hasattr(chart, "positions") and isinstance(getattr(chart, "positions"), Mapping):
            return self._from_native_chart(chart)

        raw_positions = chart.get("positions") or chart.get("planets") or {}
        if not isinstance(raw_positions, Mapping):
            raise TypeError("chart['positions'] (or chart['planets']) must be a mapping")

        out: Dict[str, Dict[str, Any]] = {}
        for body, raw in raw_positions.items():
            if not isinstance(raw, Mapping):
                continue
            lon = self._first_non_none(raw.get("lon"), raw.get("longitude"), raw.get("ecl_lon"), raw.get("deg"))
            sign = raw.get("sign")
            house = raw.get("house")
            lon_value: Optional[float] = None
            if lon is not None:
                lon_value = float(lon) % 360.0
            sign_value = str(sign) if sign else None
            if sign_value is None and lon_value is not None:
                sign_value = self._sign_for_longitude(lon_value)
            out[str(body)] = {
                "lon": lon_value,
                "sign": sign_value,
                "house": int(house) if house is not None else None,
            }
        return out

    def _derive_aspects(self, positions: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
        bodies = list(positions.keys())
        out: List[Dict[str, Any]] = []
        for i, p1 in enumerate(bodies):
            lon1 = positions[p1].get("lon")
            if lon1 is None:
                continue
            for p2 in bodies[i + 1 :]:
                lon2 = positions[p2].get("lon")
                if lon2 is None:
                    continue
                angle = self._angular_distance(float(lon1), float(lon2))
                best: Optional[Tuple[str, float]] = None
                for aspect_name, target_deg, orb_allowance in DERIVED_ASPECTS:
                    orb = abs(angle - target_deg)
                    allowance = orb_allowance if orb_allowance > 0 else self.default_orb_deg
                    if orb <= allowance:
                        if best is None or orb < best[1]:
                            best = (aspect_name, orb)
                if best:
                    out.append({"p1": p1, "p2": p2, "aspect": best[0], "orb": best[1]})
        return out

    def _get_aspects(
        self,
        chart: Any,
        positions: Mapping[str, Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        raw = chart.get("aspects") if isinstance(chart, Mapping) else getattr(chart, "aspects", None)
        if isinstance(raw, list) and raw:
            out: List[Dict[str, Any]] = []
            for item in raw:
                if not isinstance(item, Mapping):
                    continue
                p1 = str(item.get("p1") or item.get("planet1") or item.get("from") or "")
                p2 = str(item.get("p2") or item.get("planet2") or item.get("to") or "")
                if not p1 or not p2:
                    continue
                aspect = self._normalize_aspect_name(str(item.get("aspect") or item.get("type") or ""))
                if not aspect:
                    continue
                orb_raw = self._first_non_none(item.get("orb"), item.get("delta"))
                out.append(
                    {
                        "p1": p1,
                        "p2": p2,
                        "aspect": aspect,
                        "orb": abs(float(orb_raw)) if orb_raw is not None else None,
                    }
                )
            if out:
                return out
        return self._derive_aspects(positions)

    def _planet_prominence(
        self,
        chart: Any,
        positions: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, float]:
        out: Dict[str, float] = {body: 0.0 for body in BODY_WEIGHTS}

        def _fallback_dominance_from_positions() -> Dict[str, float]:
            fallback: Dict[str, float] = {}
            for body in BODY_WEIGHTS:
                if body not in positions:
                    continue
                val = float(BODY_WEIGHTS.get(body, 0.0))
                house = positions[body].get("house")
                if house in ANGULAR_HOUSES:
                    val += 0.15
                fallback[body] = max(0.0, val)
            return fallback

        is_placeholder = bool(
            chart.get("is_placeholder", False)
            if isinstance(chart, Mapping)
            else getattr(chart, "is_placeholder", False)
        )
        if is_placeholder:
            return out

        raw_dominance: Any = None
        if isinstance(chart, Mapping):
            raw_dominance = chart.get("dominant_planet_weights")
        else:
            raw_dominance = getattr(chart, "dominant_planet_weights", None)

        if not isinstance(raw_dominance, Mapping):
            raw_dominance = _fallback_dominance_from_positions()
            warnings.warn(
                "dominant_planet_weights missing for non-placeholder chart; "
                "falling back to inferred baseline dominance.",
                RuntimeWarning,
                stacklevel=2,
            )
            if not isinstance(chart, Mapping):
                try:
                    setattr(chart, "dominant_planet_weights", raw_dominance)
                except Exception:
                    pass

        normalized_dominance: Dict[str, float] = {}
        for body in BODY_WEIGHTS:
            raw_value = raw_dominance.get(body, raw_dominance.get(body.lower(), 0.0))
            try:
                normalized_dominance[body] = max(0.0, float(raw_value))
            except (TypeError, ValueError):
                normalized_dominance[body] = 0.0

        total = sum(normalized_dominance.values())
        if total <= 0:
            raw_dominance = _fallback_dominance_from_positions()
            for body in BODY_WEIGHTS:
                normalized_dominance[body] = max(0.0, float(raw_dominance.get(body, 0.0)))
            total = sum(normalized_dominance.values())
            if total <= 0:
                return out

        for body in out:
            if body not in positions:
                continue
            val = normalized_dominance.get(body, 0.0) / total
            house = positions[body].get("house")
            if house in ANGULAR_HOUSES:
                val += 0.15
            out[body] = _clamp01(val)
        return out

    @staticmethod
    def _normalize_numeric_map(values: Mapping[Any, Any]) -> Optional[Dict[Any, float]]:
        normalized: Dict[Any, float] = {}
        total = 0.0
        for key, raw in values.items():
            try:
                value = max(0.0, float(raw))
            except (TypeError, ValueError):
                value = 0.0
            normalized[key] = value
            total += value
        if total <= 0.0:
            return None
        return {key: value / total for key, value in normalized.items()}

    @staticmethod
    def _get_chart_map(chart: Any, attribute: str) -> Optional[Mapping[Any, Any]]:
        raw: Any = None
        if isinstance(chart, Mapping):
            raw = chart.get(attribute)
        else:
            raw = getattr(chart, attribute, None)
        if isinstance(raw, Mapping):
            return raw
        return None

    def _element_balance(self, chart: Any, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
        dominant_sign_weights = self._normalize_numeric_map(
            self._get_chart_map(chart, "dominant_sign_weights") or {}
        )
        if dominant_sign_weights:
            element_totals = {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0}
            for sign in ZODIAC_NAMES:
                element = SIGN_ELEMENTS.get(sign)
                if element in element_totals:
                    element_totals[element] += float(dominant_sign_weights.get(sign, 0.0))
            return element_totals

        totals = {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0}
        grand_total = 0.0
        for body, weight in BODY_WEIGHTS.items():
            pos = positions.get(body)
            if not pos:
                continue
            sign = pos.get("sign")
            if not sign:
                continue
            element = SIGN_ELEMENTS.get(str(sign))
            if element not in totals:
                continue
            totals[element] += weight
            grand_total += weight
        if grand_total <= 0:
            return totals
        return {element: value / grand_total for element, value in totals.items()}

    def _mode_balance(self, chart: Any, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
        dominant_sign_weights = self._normalize_numeric_map(
            self._get_chart_map(chart, "dominant_sign_weights") or {}
        )
        if dominant_sign_weights:
            mode_totals = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
            for sign in ZODIAC_NAMES:
                sign_weight = float(dominant_sign_weights.get(sign, 0.0))
                for mode, signs in MODES.items():
                    if sign in signs and mode in mode_totals:
                        mode_totals[mode] += sign_weight
                        break
            return mode_totals

        totals = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
        grand_total = 0.0
        for body, weight in BODY_WEIGHTS.items():
            pos = positions.get(body)
            if not pos:
                continue
            sign = pos.get("sign")
            if not sign:
                continue
            mode = SIGN_TO_MODE.get(str(sign))
            if mode not in totals:
                continue
            totals[mode] += weight
            grand_total += weight
        if grand_total <= 0:
            return totals
        return {mode: value / grand_total for mode, value in totals.items()}

    def _house_emphasis(self, chart: Any, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
        dominant_house_weights = self._normalize_numeric_map(
            self._get_chart_map(chart, "dominant_house_weights") or {}
        )
        if dominant_house_weights:
            return {
                key: float(
                    sum(
                        dominant_house_weights.get(house, dominant_house_weights.get(str(house), 0.0))
                        for house in houses
                    )
                )
                for key, houses in EMPHASIS_HOUSE_GROUPS.items()
            }

        counts = {key: 0.0 for key in EMPHASIS_HOUSE_GROUPS}
        total_weight = 0.0
        for body, weight in BODY_WEIGHTS.items():
            pos = positions.get(body)
            if not pos:
                continue
            house = pos.get("house")
            if not isinstance(house, int):
                continue
            for key, houses in EMPHASIS_HOUSE_GROUPS.items():
                if house in houses:
                    counts[key] += weight
            total_weight += weight
        if total_weight <= 0:
            return counts
        return {key: value / total_weight for key, value in counts.items()}

    def _aspect_signals(self, aspects: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
        totals = {"tension": 0.0, "cohesion": 0.0, "volatility": 0.0}
        for asp in aspects:
            aspect = self._normalize_aspect_name(str(asp.get("aspect") or ""))
            if not aspect:
                continue
            base = float(ASPECT_SCORE_WEIGHTS.get(aspect, 0.0))
            if base <= 0:
                continue
            orb = asp.get("orb")
            orb_allowance = float(ASPECT_ORB_ALLOWANCES.get(aspect, self.default_orb_deg))
            orb_decay = 1.0
            if orb is not None and orb_allowance > 0:
                orb_decay = _clamp01(1.0 - (float(orb) / orb_allowance))
            weight = base * orb_decay
            if aspect in {"square", "opposition", "semisquare", "sesquiquadrate"}:
                totals["tension"] += weight
            if aspect in {"trine", "sextile", "conjunction"}:
                totals["cohesion"] += weight
            if aspect in {"conjunction", "square", "opposition", "quincunx"}:
                totals["volatility"] += weight

        norm = max(1.0, totals["tension"] + totals["cohesion"] + totals["volatility"])
        return {key: value / norm for key, value in totals.items()}


# ---------------------------------------------------------------------------
# Class-family gates and class scoring
# ---------------------------------------------------------------------------

class ClassFamilyCategory(str, Enum):
    SOURCE = "source"
    HYBRID = "hybrid"
    SPECIALIST = "specialist"


@dataclass(frozen=True)
class ClassFamilyDefinition:
    key: str
    display_name: str
    category: ClassFamilyCategory
    description: str
    gate_weights: Mapping[str, float]
    notes: str = ""


@dataclass(frozen=True)
class ClassDefinition:
    key: str
    display_name: str
    family_affinity: Mapping[str, float]
    axis_weights: Mapping[str, float]
    synergy_groups: Tuple[Tuple[str, ...], ...] = field(default_factory=tuple)
    anti_axes: Mapping[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class ScoredClassFamily:
    key: str
    score: float


@dataclass(frozen=True)
class ScoredClass:
    key: str
    score: float
    direct_score: float
    family_score: float
    synergy_score: float
    penalty_score: float


@dataclass(frozen=True)
class ClassAssignment:
    primary_class: str
    primary_score: float
    class_family: str
    family_score: float
    secondary_class: Optional[str]
    secondary_score: float
    confidence_gap: float
    axis_scores: Mapping[str, float]
    family_scores: Mapping[str, float]
    class_scores: Mapping[str, float]


CLASS_FAMILIES: Dict[str, ClassFamilyDefinition] = {
    "martial_discipline": ClassFamilyDefinition(
        key="martial_discipline",
        display_name="Martial Discipline",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through trained force, regimen, and repeatable skill.",
        gate_weights={
            "discipline": 0.36,
            "frontline_courage": 0.30,
            "control_planning": 0.18,
            "social_leadership": 0.08,
            "risk_appetite": 0.08,
        },
        notes="Core lane for Fighter, Monk, and the martial half of Paladin.",
    ),
    "primal_embodiment": ClassFamilyDefinition(
        key="primal_embodiment",
        display_name="Primal Embodiment",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through body, appetite, survival timing, and raw contact with the living world.",
        gate_weights={
            "instinct": 0.30,
            "frontline_courage": 0.22,
            "nature_attunement": 0.20,
            "risk_appetite": 0.08,
            "mercy_restoration": 0.08,
            "discipline": 0.12,
        },
        notes="Core lane for Barbarian and the primal edge of Druid and Ranger.",
    ),
    "devotional_sacred": ClassFamilyDefinition(
        key="devotional_sacred",
        display_name="Devotional Sacred",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through oath, doctrine, service, and alignment to a higher order.",
        gate_weights={
            "faith": 0.32,
            "mercy_restoration": 0.22,
            "social_leadership": 0.16,
            "frontline_courage": 0.15,
            "control_planning": 0.07,
            "discipline": 0.08,
        },
        notes="Core lane for Cleric and Paladin, with some Druid overlap.",
    ),
    "arcane_scholar": ClassFamilyDefinition(
        key="arcane_scholar",
        display_name="Arcane Scholar",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through formal study, system knowledge, and controlled arcane method.",
        gate_weights={
            "study": 0.40,
            "control_planning": 0.24,
            "technical_inventiveness": 0.18,
            "discipline": 0.10,
            "risk_appetite": 0.08,
        },
        notes="Core lane for Wizard and part of the Artificer profile.",
    ),
    "innate_arcane": ClassFamilyDefinition(
        key="innate_arcane",
        display_name="Innate Arcane",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed as internal voltage, native gift, and volatile selfhood.",
        gate_weights={
            "innate_power": 0.42,
            "risk_appetite": 0.18,
            "social_leadership": 0.14,
            "performance": 0.14,
            "frontline_courage": 0.12,
        },
        notes="Core lane for Sorcerer and some highly expressive hybrids.",
    ),
    "pact_occult": ClassFamilyDefinition(
        key="pact_occult",
        display_name="Pact Occult",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through bargain, taboo access, outside agency, and selective entanglement.",
        gate_weights={
            "patron_reliance": 0.44,
            "stealth_indirection": 0.18,
            "control_planning": 0.16,
            "risk_appetite": 0.12,
            "innate_power": 0.10,
        },
        notes="Core lane for Warlock.",
    ),
    "expressive_social": ClassFamilyDefinition(
        key="expressive_social",
        display_name="Expressive Social",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through language, image, timing, and social orchestration.",
        gate_weights={
            "performance": 0.40,
            "social_leadership": 0.26,
            "study": 0.14,
            "stealth_indirection": 0.10,
            "risk_appetite": 0.10,
        },
        notes="Core lane for Bard.",
    ),
    "wild_warden": ClassFamilyDefinition(
        key="wild_warden",
        display_name="Wild Warden",
        category=ClassFamilyCategory.HYBRID,
        description="Power expressed through ecological fluency, field competence, and contact with uncivilized spaces.",
        gate_weights={
            "nature_attunement": 0.30,
            "instinct": 0.16,
            "stealth_indirection": 0.14,
            "frontline_courage": 0.20,
            "mercy_restoration": 0.08,
            "discipline": 0.12,
        },
        notes="Core lane for Druid and Ranger.",
    ),
    "shadow_precision": ClassFamilyDefinition(
        key="shadow_precision",
        display_name="Shadow Precision",
        category=ClassFamilyCategory.SPECIALIST,
        description="Power expressed through angle, infiltration, leverage, and technical timing.",
        gate_weights={
            "stealth_indirection": 0.40,
            "study": 0.18,
            "control_planning": 0.18,
            "risk_appetite": 0.12,
            "technical_inventiveness": 0.12,
        },
        notes="Core lane for Rogue, with spillover into Ranger and Bard trickster lanes.",
    ),
    "engineered_technical": ClassFamilyDefinition(
        key="engineered_technical",
        display_name="Engineered Technical",
        category=ClassFamilyCategory.SPECIALIST,
        description="Power expressed through devices, systems, applied craft, and precision utility.",
        gate_weights={
            "technical_inventiveness": 0.40,
            "study": 0.26,
            "control_planning": 0.18,
            "discipline": 0.10,
            "risk_appetite": 0.06,
        },
        notes="Core lane for Artificer.",
    ),
}


CLASS_FAMILY_ORDER: Tuple[str, ...] = tuple(CLASS_FAMILIES.keys())


DND_CLASSES: Dict[str, ClassDefinition] = {
    "Barbarian": ClassDefinition(
        key="Barbarian",
        display_name="Barbarian",
        family_affinity={"primal_embodiment": 0.78, "martial_discipline": 0.22},
        axis_weights={
            "instinct": 0.31,
            "frontline_courage": 0.24,
            "risk_appetite": 0.14,
            "nature_attunement": 0.16,
            "discipline": 0.09,
            "social_leadership": 0.06,
        },
        synergy_groups=(("instinct", "frontline_courage"), ("instinct", "risk_appetite")),
        anti_axes={"study": 0.22, "control_planning": 0.16},
        notes="Body-first action, low need for system mediation, high willingness to commit.",
    ),
    "Bard": ClassDefinition(
        key="Bard",
        display_name="Bard",
        family_affinity={"expressive_social": 0.76, "shadow_precision": 0.12, "innate_arcane": 0.12},
        axis_weights={
            "performance": 0.30,
            "social_leadership": 0.22,
            "study": 0.16,
            "stealth_indirection": 0.12,
            "risk_appetite": 0.08,
            "mercy_restoration": 0.04,
            "control_planning": 0.08,
        },
        synergy_groups=(("performance", "social_leadership"), ("performance", "study")),
        anti_axes={"patron_reliance": 0.12},
        notes="Social and expressive spellwork rather than purely decorative charm.",
    ),
    "Cleric": ClassDefinition(
        key="Cleric",
        display_name="Cleric",
        family_affinity={"devotional_sacred": 0.54, "wild_warden": 0.16, "martial_discipline": 0.30},
        axis_weights={
            "faith": 0.16,
            "mercy_restoration": 0.20,
            "social_leadership": 0.24,
            "control_planning": 0.16,
            "frontline_courage": 0.14,
            "discipline": 0.10,
        },
        synergy_groups=(("social_leadership", "mercy_restoration"), ("faith", "discipline")),
        anti_axes={},
        notes="Consecrated service with room for doctrine, healing, and judgment.",
    ),
    "Druid": ClassDefinition(
        key="Druid",
        display_name="Druid",
        family_affinity={"wild_warden": 0.70, "primal_embodiment": 0.15, "devotional_sacred": 0.15},
        axis_weights={
            "nature_attunement": 0.34,
            "instinct": 0.16,
            "mercy_restoration": 0.18,
            "faith": 0.14,
            "control_planning": 0.08,
            "risk_appetite": 0.10,
        },
        synergy_groups=(("nature_attunement", "instinct"), ("nature_attunement", "mercy_restoration")),
        anti_axes={"technical_inventiveness": 0.10},
        notes="Cycle-aware, ecological, and adaptive rather than merely pastoral.",
    ),
    "Fighter": ClassDefinition(
        key="Fighter",
        display_name="Fighter",
        family_affinity={"martial_discipline": 0.84, "shadow_precision": 0.08, "engineered_technical": 0.08},
        axis_weights={
            "discipline": 0.34,
            "frontline_courage": 0.28,
            "control_planning": 0.18,
            "social_leadership": 0.10,
            "risk_appetite": 0.10,
        },
        synergy_groups=(("discipline", "frontline_courage"), ("discipline", "control_planning")),
        anti_axes={"patron_reliance": 0.08},
        notes="Repeatable competence, tactical reliability, and durable visible action.",
    ),
    "Monk": ClassDefinition(
        key="Monk",
        display_name="Monk",
        family_affinity={"martial_discipline": 0.58, "primal_embodiment": 0.22, "devotional_sacred": 0.20},
        axis_weights={
            "discipline": 0.30,
            "instinct": 0.18,
            "control_planning": 0.18,
            "frontline_courage": 0.18,
            "faith": 0.08,
            "mercy_restoration": 0.08,
        },
        synergy_groups=(("discipline", "instinct"), ("discipline", "control_planning")),
        anti_axes={"performance": 0.08, "patron_reliance": 0.10},
        notes="Embodied restraint and internalized technique rather than brute force.",
    ),
    "Paladin": ClassDefinition(
        key="Paladin",
        display_name="Paladin",
        family_affinity={"devotional_sacred": 0.34, "martial_discipline": 0.66},
        axis_weights={
            "faith": 0.14,
            "frontline_courage": 0.30,
            "discipline": 0.28,
            "social_leadership": 0.16,
            "mercy_restoration": 0.08,
            "risk_appetite": 0.04,
        },
        synergy_groups=(("frontline_courage", "discipline"), ("faith", "social_leadership")),
        anti_axes={},
        notes="Oath plus visible force. Neither soft Cleric nor mere armored Fighter.",
    ),
    "Ranger": ClassDefinition(
        key="Ranger",
        display_name="Ranger",
        family_affinity={"wild_warden": 0.34, "shadow_precision": 0.26, "martial_discipline": 0.40},
        axis_weights={
            "nature_attunement": 0.08,
            "stealth_indirection": 0.18,
            "frontline_courage": 0.26,
            "discipline": 0.24,
            "instinct": 0.10,
            "control_planning": 0.14,
        },
        synergy_groups=(("frontline_courage", "discipline"), ("stealth_indirection", "control_planning")),
        anti_axes={"performance": 0.0},
        notes="Field competence, terrain fluency, and directed practical violence.",
    ),
    "Rogue": ClassDefinition(
        key="Rogue",
        display_name="Rogue",
        family_affinity={"shadow_precision": 0.72, "engineered_technical": 0.14, "expressive_social": 0.14},
        axis_weights={
            "stealth_indirection": 0.34,
            "study": 0.20,
            "control_planning": 0.18,
            "risk_appetite": 0.14,
            "technical_inventiveness": 0.14,
        },
        synergy_groups=(("stealth_indirection", "study"), ("stealth_indirection", "control_planning")),
        anti_axes={"faith": 0.06},
        notes="Precision leverage, timing, and low-spectacle problem solving.",
    ),
    "Sorcerer": ClassDefinition(
        key="Sorcerer",
        display_name="Sorcerer",
        family_affinity={"innate_arcane": 0.78, "expressive_social": 0.12, "pact_occult": 0.10},
        axis_weights={
            "innate_power": 0.34,
            "risk_appetite": 0.18,
            "social_leadership": 0.16,
            "performance": 0.14,
            "frontline_courage": 0.10,
            "control_planning": 0.08,
        },
        synergy_groups=(("innate_power", "risk_appetite"), ("innate_power", "social_leadership")),
        anti_axes={"study": 0.14},
        notes="Internal voltage first; formal schooling is optional at best.",
    ),
    "Warlock": ClassDefinition(
        key="Warlock",
        display_name="Warlock",
        family_affinity={"pact_occult": 0.84, "innate_arcane": 0.08, "shadow_precision": 0.08},
        axis_weights={
            "patron_reliance": 0.36,
            "stealth_indirection": 0.16,
            "control_planning": 0.16,
            "innate_power": 0.12,
            "risk_appetite": 0.10,
            "social_leadership": 0.10,
        },
        synergy_groups=(("patron_reliance", "stealth_indirection"), ("patron_reliance", "control_planning")),
        anti_axes={"mercy_restoration": 0.08},
        notes="Negotiated access to force with a clear appetite for asymmetry.",
    ),
    "Wizard": ClassDefinition(
        key="Wizard",
        display_name="Wizard",
        family_affinity={"arcane_scholar": 0.82, "engineered_technical": 0.10, "shadow_precision": 0.08},
        axis_weights={
            "study": 0.30,
            "control_planning": 0.20,
            "discipline": 0.14,
            "technical_inventiveness": 0.14,
            "risk_appetite": 0.08,
            "social_leadership": 0.06,
            "faith": 0.08,
        },
        synergy_groups=(("study", "control_planning"), ("study", "discipline")),
        anti_axes={"instinct": 0.14},
        notes="Codified arcana, learned method, and board-shaping intelligence.",
    ),
    "Artificer": ClassDefinition(
        key="Artificer",
        display_name="Artificer",
        family_affinity={"engineered_technical": 0.70, "arcane_scholar": 0.30},
        axis_weights={
            "technical_inventiveness": 0.34,
            "study": 0.22,
            "control_planning": 0.18,
            "discipline": 0.14,
            "risk_appetite": 0.06,
            "mercy_restoration": 0.06,
        },
        synergy_groups=(("technical_inventiveness", "study"), ("technical_inventiveness", "control_planning")),
        anti_axes={"instinct": 0.08},
        notes="Applied craft and engineered utility rather than purely abstract spellwork.",
    ),
}


CLASS_ORDER: Tuple[str, ...] = tuple(DND_CLASSES.keys())


class DnDClassScorer:
    """Scores class families and base classes from axis values."""

    def score_families(self, axis_scores: Mapping[str, float]) -> Dict[str, float]:
        validate_axis_scores(axis_scores)
        return {
            key: _weighted_average(axis_scores, definition.gate_weights)
            for key, definition in CLASS_FAMILIES.items()
        }

    def score_classes(
        self,
        axis_scores: Mapping[str, float],
        family_scores: Optional[Mapping[str, float]] = None,
    ) -> Dict[str, ScoredClass]:
        validate_axis_scores(axis_scores)
        families = dict(family_scores or self.score_families(axis_scores))
        out: Dict[str, ScoredClass] = {}

        for class_key, definition in DND_CLASSES.items():
            direct_score = _weighted_average(axis_scores, definition.axis_weights)
            family_score = self._class_family_score(definition, families)
            synergy_score = self._class_synergy_score(definition, axis_scores)
            penalty_score = _weighted_penalty(axis_scores, definition.anti_axes)
            final_score = self._compose_class_score(
                direct_score=direct_score,
                family_score=family_score,
                synergy_score=synergy_score,
                penalty_score=penalty_score,
            )
            out[class_key] = ScoredClass(
                key=class_key,
                score=final_score,
                direct_score=direct_score,
                family_score=family_score,
                synergy_score=synergy_score,
                penalty_score=penalty_score,
            )
        return out

    def assign_from_axis_scores(self, axis_scores: Mapping[str, float]) -> ClassAssignment:
        family_scores = self.score_families(axis_scores)
        class_detail = self.score_classes(axis_scores, family_scores)
        ranked_classes = sorted(class_detail.values(), key=lambda item: item.score, reverse=True)
        ranked_families = sorted(family_scores.items(), key=lambda kv: kv[1], reverse=True)

        primary = ranked_classes[0]
        secondary = ranked_classes[1] if len(ranked_classes) > 1 else None
        best_family_key, best_family_score = ranked_families[0]

        return ClassAssignment(
            primary_class=primary.key,
            primary_score=primary.score,
            class_family=best_family_key,
            family_score=float(best_family_score),
            secondary_class=secondary.key if secondary else None,
            secondary_score=secondary.score if secondary else 0.0,
            confidence_gap=max(0.0, primary.score - (secondary.score if secondary else 0.0)),
            axis_scores={key: float(axis_scores.get(key, 0.0)) for key in AXIS_ORDER},
            family_scores={key: float(value) for key, value in family_scores.items()},
            class_scores={key: value.score for key, value in class_detail.items()},
        )

    def assign_from_chart(self, chart: Any) -> ClassAssignment:
        axis_scores = score_class_axes(chart)
        return self.assign_from_axis_scores(axis_scores)

    @staticmethod
    def _class_family_score(
        definition: ClassDefinition,
        family_scores: Mapping[str, float],
    ) -> float:
        total_weight = sum(max(0.0, float(weight)) for weight in definition.family_affinity.values())
        if total_weight <= 0:
            return 0.0
        total = 0.0
        for family_key, weight in definition.family_affinity.items():
            total += float(family_scores.get(family_key, 0.0)) * float(weight)
        return _clamp01(total / total_weight)

    @staticmethod
    def _class_synergy_score(
        definition: ClassDefinition,
        axis_scores: Mapping[str, float],
    ) -> float:
        if not definition.synergy_groups:
            return 0.0
        group_scores = [_synergy_average(axis_scores, group) for group in definition.synergy_groups]
        return _clamp01(sum(group_scores) / len(group_scores))

    @staticmethod
    def _compose_class_score(
        *,
        direct_score: float,
        family_score: float,
        synergy_score: float,
        penalty_score: float,
    ) -> float:
        raw = (
            0.56 * direct_score
            + 0.24 * family_score
            + 0.20 * synergy_score
            - 0.12 * penalty_score
        )
        return _clamp01(raw)


def extract_class_axis_features(chart: Any) -> AxisFeatureSet:
    return ClassAxisScorer().extract_features(chart)


def score_class_axes(chart: Any) -> Dict[str, float]:
    return ClassAxisScorer().score_chart(chart)


def score_class_families(axis_scores: Mapping[str, float]) -> Dict[str, float]:
    return DnDClassScorer().score_families(axis_scores)


_DND_STAT_DISPLAY_ORDER: Tuple[str, ...] = ("CHA", "INT", "STR", "CON", "WIS", "DEX")
_DND_STAT_COMPONENT_ORDER: Tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
_DND_STAT_LABELS: Dict[str, str] = {
    "STR": "Strength",
    "DEX": "Dexterity",
    "CON": "Constitution",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}


def _to_dnd_stat(raw_score: float, floor: int = 5, ceiling: int = 20) -> int:
    raw_score = _clamp01(raw_score)
    return int(round(floor + raw_score * (ceiling - floor)))


def _compress_stat_profile(raw_scores: Mapping[str, float]) -> Dict[str, float]:
    values = {key: _clamp01(value) for key, value in raw_scores.items()}
    mean = sum(values.values()) / max(1, len(values))
    compressed: Dict[str, float] = {}
    for key, value in values.items():
        compressed[key] = _clamp01(0.70 * value + 0.30 * mean)
    return compressed


def score_dnd_statblock_from_features(
    axis_scores: Mapping[str, float],
    features: AxisFeatureSet,
    *,
    stat_floor: int = 5,
    stat_ceiling: int = 20,
) -> DnDStatBlock:
    validate_axis_scores(axis_scores)
    p = features.planet_prominence
    e = features.element_balance
    m = features.mode_balance
    h = features.house_emphasis
    raw_scores: Dict[str, float] = {
        "STR": _clamp01(
            0.40 * axis_scores["frontline_courage"]
            + 0.22 * axis_scores["instinct"]
            + 0.14 * axis_scores["discipline"]
            + 0.08 * p.get("Mars", 0.0)
            + 0.06 * p.get("Sun", 0.0)
            + 0.05 * h.get("self", 0.0)
            + 0.05 * ((e.get("Fire", 0.0) + e.get("Earth", 0.0)) / 2.0)
        ),
        "DEX": _clamp01(
            0.32 * axis_scores["stealth_indirection"]
            + 0.20 * axis_scores["control_planning"]
            + 0.16 * axis_scores["risk_appetite"]
            + 0.10 * p.get("Mercury", 0.0)
            + 0.08 * p.get("Uranus", 0.0)
            + 0.07 * e.get("Air", 0.0)
            + 0.07 * m.get("mutable", 0.0)
        ),
        "CON": _clamp01(
            0.28 * axis_scores["discipline"]
            + 0.20 * axis_scores["instinct"]
            + 0.16 * axis_scores["mercy_restoration"]
            + 0.12 * p.get("Saturn", 0.0)
            + 0.08 * p.get("Moon", 0.0)
            + 0.08 * e.get("Earth", 0.0)
            + 0.08 * m.get("fixed", 0.0)
        ),
        "INT": _clamp01(
            0.36 * axis_scores["study"]
            + 0.20 * axis_scores["technical_inventiveness"]
            + 0.16 * axis_scores["control_planning"]
            + 0.12 * p.get("Mercury", 0.0)
            + 0.08 * p.get("Saturn", 0.0)
            + 0.08 * h.get("craft", 0.0)
        ),
        "WIS": _clamp01(
            0.28 * axis_scores["faith"]
            + 0.24 * axis_scores["nature_attunement"]
            + 0.18 * axis_scores["instinct"]
            + 0.12 * axis_scores["mercy_restoration"]
            + 0.08 * p.get("Moon", 0.0)
            + 0.05 * p.get("Jupiter", 0.0)
            + 0.05 * ((h.get("wild", 0.0) + h.get("meaning", 0.0)) / 2.0)
        ),
        "CHA": _clamp01(
            0.32 * axis_scores["social_leadership"]
            + 0.24 * axis_scores["performance"]
            + 0.18 * axis_scores["innate_power"]
            + 0.10 * p.get("Sun", 0.0)
            + 0.08 * p.get("Venus", 0.0)
            + 0.08 * h.get("social", 0.0)
        ),
    }

    raw_scores = _compress_stat_profile(raw_scores)
    scores = {
        key: _to_dnd_stat(raw_scores[key], floor=stat_floor, ceiling=stat_ceiling)
        for key in _DND_STAT_COMPONENT_ORDER
    }
    modifiers = {key: int((value - 10) // 2) for key, value in scores.items()}
    return DnDStatBlock(raw_scores=raw_scores, scores=scores, modifiers=modifiers)


def score_dnd_statblock(
    chart: Any,
    *,
    stat_floor: int = 5,
    stat_ceiling: int = 20,
) -> DnDStatBlock:
    scorer = ClassAxisScorer()
    features = scorer.extract_features(chart)
    axis_scores = scorer.score_axes(features)
    return score_dnd_statblock_from_features(
        axis_scores,
        features,
        stat_floor=stat_floor,
        stat_ceiling=stat_ceiling,
    )


def build_dnd_statblock_profile_lines(
    statblock: DnDStatBlock,
    *,
    bar_width: int = 18,
    floor: int = 5,
    ceiling: int = 20,
) -> list[str]:
    span = max(1, ceiling - floor)
    lines: list[str] = []
    for stat_key in _DND_STAT_DISPLAY_ORDER:
        stat_value = int(statblock.scores.get(stat_key, floor))
        normalized_percent = max(0.0, min(100.0, ((stat_value - floor) / span) * 100.0))
        bar = _build_axis_score_bar(normalized_percent, 0.0, width=bar_width)
        modifier = int(statblock.modifiers.get(stat_key, 0))
        lines.append(
            f"‣ {stat_key} ({_DND_STAT_LABELS[stat_key]}): {stat_value:>2d} [{bar}] mod {modifier:+d}"
        )
    return lines


def score_dnd_classes(
    axis_scores: Mapping[str, float],
    family_scores: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    detail = DnDClassScorer().score_classes(axis_scores, family_scores)
    return {key: scored.score for key, scored in detail.items()}


def assign_dnd_class(chart_or_axis_scores: Any) -> ClassAssignment:
    scorer = DnDClassScorer()
    if isinstance(chart_or_axis_scores, Mapping) and all(
        key in chart_or_axis_scores for key in AXIS_ORDER
    ):
        return scorer.assign_from_axis_scores(chart_or_axis_scores)
    return scorer.assign_from_chart(chart_or_axis_scores)


def class_family_display_table() -> str:
    lines: List[str] = []
    for key in CLASS_FAMILY_ORDER:
        family = CLASS_FAMILIES[key]
        gate_text = ", ".join(f"{axis}={weight:.2f}" for axis, weight in family.gate_weights.items())
        lines.append(f"[{family.category.value}] {family.display_name} ({family.key})")
        lines.append(f"  {family.description}")
        lines.append(f"  Gate: {gate_text}")
        if family.notes:
            lines.append(f"  Notes: {family.notes}")
        lines.append("")
    return "\n".join(lines).rstrip()


def class_display_table() -> str:
    lines: List[str] = []
    for key in CLASS_ORDER:
        cls = DND_CLASSES[key]
        fam = ", ".join(f"{name}={weight:.2f}" for name, weight in cls.family_affinity.items())
        axis = ", ".join(f"{name}={weight:.2f}" for name, weight in cls.axis_weights.items())
        lines.append(f"{cls.display_name} ({cls.key})")
        lines.append(f"  Families: {fam}")
        lines.append(f"  Axes: {axis}")
        if cls.synergy_groups:
            lines.append(
                "  Synergy: "
                + ", ".join(" + ".join(group) for group in cls.synergy_groups)
            )
        if cls.anti_axes:
            lines.append(
                "  Anti: " + ", ".join(f"{name}={weight:.2f}" for name, weight in cls.anti_axes.items())
            )
        if cls.notes:
            lines.append(f"  Notes: {cls.notes}")
        lines.append("")
    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    print(axis_display_table())
    print()
    print(class_family_display_table())
    print()
    print(class_display_table())


_CLASS_AXIS_LABEL_OVERRIDES: Dict[str, str] = {
    "control_planning": "control & planning",
    "stealth_indirection": "stealth",
    "mercy_restoration": "mercy & restoration",
}

_CLASS_AXIS_BAR_FULL = "█"
_CLASS_AXIS_BAR_EMPTY = "░"
_CLASS_AXIS_THRESHOLD_MARK = "│"
DND_CLASS_THRESHOLD_COLOR = "#cc4444"
DND_CLASS_AXIS_EARTHTONE_COLORS: Dict[str, str] = {
    "discipline": "#8b6f47",
    "instinct": "#8f5d3b",
    "study": "#a0855b",
    "faith": "#94714d",
    "innate_power": "#7a5a3a",
    "patron_reliance": "#73563c",
    "performance": "#9b6f4e",
    "nature_attunement": "#6d7f4d",
    "technical_inventiveness": "#7f725e",
    "stealth_indirection": "#6e5c4a",
    "frontline_courage": "#8a4f3d",
    "control_planning": "#6a604f",
    "mercy_restoration": "#7a6d58",
    "risk_appetite": "#925440",
    "social_leadership": "#8d634a",
}


def format_class_axis_label(axis_name: str) -> str:
    return _CLASS_AXIS_LABEL_OVERRIDES.get(axis_name, axis_name.replace("_", " "))


def resolve_class_key(class_name: str) -> str | None:
    if class_name in DND_CLASSES:
        return class_name
    for class_key, definition in DND_CLASSES.items():
        if definition.display_name == class_name:
            return class_key
    return None


def _build_axis_score_bar(score_percent: float, threshold_percent: float, width: int = 18) -> str:
    clamped_score = max(0.0, min(100.0, float(score_percent)))
    clamped_threshold = max(0.0, min(100.0, float(threshold_percent)))
    filled_count = int(round((clamped_score / 100.0) * width))
    threshold_index = int(round((clamped_threshold / 100.0) * (width - 1)))
    cells = [
        _CLASS_AXIS_BAR_FULL if index < filled_count else _CLASS_AXIS_BAR_EMPTY
        for index in range(width)
    ]
    if 0 <= threshold_index < width:
        cells[threshold_index] = _CLASS_AXIS_THRESHOLD_MARK
    return "".join(cells)


def build_class_axis_profile_lines(
    class_name: str,
    axis_scores: Mapping[str, float],
    *,
    bar_width: int = 18,
) -> list[str]:
    class_key = resolve_class_key(class_name)
    if class_key is None:
        return []
    definition = DND_CLASSES.get(class_key)
    if definition is None:
        return []
    lines: list[str] = []
    axis_rows: list[tuple[float, str, float, float]] = []
    for axis_name, threshold_weight in definition.axis_weights.items():
        chart_axis_percent = max(0.0, min(1.0, float(axis_scores.get(axis_name, 0.0)))) * 100.0
        threshold_percent = max(0.0, min(1.0, float(threshold_weight))) * 100.0
        margin_percent = chart_axis_percent - threshold_percent
        axis_rows.append((margin_percent, axis_name, chart_axis_percent, threshold_percent))
    axis_rows.sort(key=lambda row: row[0], reverse=True)
    for margin_percent, axis_name, chart_axis_percent, threshold_percent in axis_rows:
        bar = _build_axis_score_bar(chart_axis_percent, threshold_percent, width=bar_width)
        status = f"{margin_percent:+.0f}%"
        lines.append(
            f"‣ {format_class_axis_label(axis_name)}: {chart_axis_percent:.0f}% [{bar}] threshold {threshold_percent:.0f}% ({status})"
        )
    return lines
