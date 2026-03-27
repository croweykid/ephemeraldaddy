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

from ephemeraldaddy.core.interpretations import (
    ASPECT_ANGLE_DEGREES,
    ASPECT_ORB_ALLOWANCES,
    ASPECT_SCORE_WEIGHTS,
    MODES,
    NATAL_BODY_LOUDNESS,
    SIGN_ELEMENTS,
)


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


class ClassAxisScorer:
    def __init__(self, *, default_orb_deg: float = 6.0) -> None:
        self.default_orb_deg = float(default_orb_deg)

    def score_chart(self, chart: Any) -> Dict[str, float]:
        return self.score_axes(self.extract_features(chart))

    def extract_features(self, chart: Any) -> AxisFeatureSet:
        positions = self._get_positions(chart)
        aspects = self._get_aspects(chart, positions)

        planet_prominence = self._planet_prominence(positions)
        element_balance = self._element_balance(positions)
        mode_balance = self._mode_balance(positions)
        house_emphasis = self._house_emphasis(positions)
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

    def _planet_prominence(self, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
        out: Dict[str, float] = {body: 0.0 for body in BODY_WEIGHTS}
        for body in out:
            if body not in positions:
                continue
            val = BODY_WEIGHTS.get(body, 0.0)
            house = positions[body].get("house")
            if house in ANGULAR_HOUSES:
                val += 0.15
            out[body] = _clamp01(val)
        return out

    def _element_balance(self, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
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

    def _mode_balance(self, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
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

    def _house_emphasis(self, positions: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
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
            "instinct": 0.36,
            "frontline_courage": 0.24,
            "nature_attunement": 0.20,
            "risk_appetite": 0.12,
            "mercy_restoration": 0.08,
        },
        notes="Core lane for Barbarian and the primal edge of Druid and Ranger.",
    ),
    "devotional_sacred": ClassFamilyDefinition(
        key="devotional_sacred",
        display_name="Devotional Sacred",
        category=ClassFamilyCategory.SOURCE,
        description="Power expressed through oath, doctrine, service, and alignment to a higher order.",
        gate_weights={
            "faith": 0.42,
            "mercy_restoration": 0.20,
            "social_leadership": 0.16,
            "frontline_courage": 0.12,
            "control_planning": 0.10,
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
            "nature_attunement": 0.34,
            "instinct": 0.18,
            "stealth_indirection": 0.16,
            "frontline_courage": 0.16,
            "mercy_restoration": 0.16,
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
            "instinct": 0.34,
            "frontline_courage": 0.28,
            "risk_appetite": 0.20,
            "nature_attunement": 0.10,
            "social_leadership": 0.08,
        },
        synergy_groups=(("instinct", "frontline_courage"), ("instinct", "risk_appetite")),
        anti_axes={"study": 0.18, "control_planning": 0.12},
        notes="Body-first action, low need for system mediation, high willingness to commit.",
    ),
    "Bard": ClassDefinition(
        key="Bard",
        display_name="Bard",
        family_affinity={"expressive_social": 0.76, "shadow_precision": 0.12, "innate_arcane": 0.12},
        axis_weights={
            "performance": 0.34,
            "social_leadership": 0.22,
            "study": 0.16,
            "stealth_indirection": 0.12,
            "risk_appetite": 0.08,
            "mercy_restoration": 0.08,
        },
        synergy_groups=(("performance", "social_leadership"), ("performance", "study")),
        anti_axes={"patron_reliance": 0.08},
        notes="Social and expressive spellwork rather than purely decorative charm.",
    ),
    "Cleric": ClassDefinition(
        key="Cleric",
        display_name="Cleric",
        family_affinity={"devotional_sacred": 0.82, "wild_warden": 0.10, "martial_discipline": 0.08},
        axis_weights={
            "faith": 0.34,
            "mercy_restoration": 0.24,
            "social_leadership": 0.16,
            "control_planning": 0.14,
            "frontline_courage": 0.12,
        },
        synergy_groups=(("faith", "mercy_restoration"), ("faith", "social_leadership")),
        anti_axes={"risk_appetite": 0.10},
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
        family_affinity={"devotional_sacred": 0.52, "martial_discipline": 0.48},
        axis_weights={
            "faith": 0.28,
            "frontline_courage": 0.24,
            "discipline": 0.18,
            "social_leadership": 0.16,
            "mercy_restoration": 0.14,
        },
        synergy_groups=(("faith", "frontline_courage"), ("faith", "discipline")),
        anti_axes={"stealth_indirection": 0.08},
        notes="Oath plus visible force. Neither soft Cleric nor mere armored Fighter.",
    ),
    "Ranger": ClassDefinition(
        key="Ranger",
        display_name="Ranger",
        family_affinity={"wild_warden": 0.48, "shadow_precision": 0.28, "martial_discipline": 0.24},
        axis_weights={
            "nature_attunement": 0.26,
            "stealth_indirection": 0.20,
            "frontline_courage": 0.18,
            "discipline": 0.14,
            "instinct": 0.12,
            "control_planning": 0.10,
        },
        synergy_groups=(("nature_attunement", "stealth_indirection"), ("nature_attunement", "frontline_courage")),
        anti_axes={"performance": 0.08},
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
            "study": 0.34,
            "control_planning": 0.24,
            "discipline": 0.14,
            "technical_inventiveness": 0.14,
            "risk_appetite": 0.08,
            "social_leadership": 0.06,
        },
        synergy_groups=(("study", "control_planning"), ("study", "discipline")),
        anti_axes={"instinct": 0.10},
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


DND_5E_CLASSES: Dict[str, Tuple[str, ...]] = {'Artificer': ('Alchemist', 'Armorer', 'Artillerist', 'Battle Smith', 'Cartographer'),
 'Barbarian': ('Ancestral Guardian',
               'Beast',
               'Berserker',
               'Giant',
               'Totem Warrior',
               'Wild Magic',
               'World Tree',
               'Zealot'),
 'Bard': ('Creation', 'Dance', 'Eloquence', 'Glamour', 'Lore', 'Swords', 'Valor', 'Whispers'),
 'Cleric': ('Arcana',
            'Death',
            'Forge',
            'Grave',
            'Knowledge',
            'Life',
            'Light',
            'Nature',
            'Order',
            'Peace',
            'Tempest',
            'Trickery',
            'Twilight',
            'War'),
 'Druid': ('Dreams', 'Land', 'Moon', 'Sea', 'Shepherd', 'Spores', 'Stars', 'Wildfire'),
 'Fighter': ('Battle Master',
             'Cavalier',
             'Champion',
             'Echo Knight',
             'Eldritch Knight',
             'Psi Warrior',
             'Rune Knight',
             'Samurai'),
 'Monk': ('Astral Self', 'Long Death', 'Mercy', 'Open Hand', 'Shadow', 'Warrior of the Elements'),
 'Paladin': ('Ancients', 'Conquest', 'Devotion', 'Redemption', 'Vengeance', 'Watchers'),
 'Ranger': ('Beast Master', 'Drakewarden', 'Fey Wanderer', 'Gloom Stalker', 'Horizon Walker', 'Hunter', 'Swarmkeeper'),
 'Rogue': ('Arcane Trickster', 'Phantom', 'Soulknife', 'Swashbuckler', 'Thief'),
 'Sorcerer': ('Aberrant Mind', 'Clockwork Soul', 'Divine Soul', 'Draconic Bloodline', 'Shadow Magic', 'Wild Magic'),
 'Warlock': ('Archfey', 'Celestial', 'Fathomless', 'Fiend', 'Genie', 'Great Old One', 'Hexblade', 'Undead'),
 'Wizard': ('Abjuration',
            'Bladesinger',
            'Conjuration',
            'Divination',
            'Enchantment',
            'Evocation',
            'Illusion',
            'Necromancy',
            'Order of Scribes',
            'Transmutation')}

 DND_CLASS_SUBCLASS_EXPLAINERS: Dict[str, str] = {
    "Artificer": "The sort of person who sees a crisis and immediately reaches for tools, notes, and a deeply suspect little device.",
    "Artificer::Alchemist": "A bottle-wielding laboratory menace who smells faintly of herbs, copper, and decisions made at 2 a.m.",
    "Artificer::Armorer": "Someone who looked at ordinary clothing and thought, 'What this needs is far more metal and better opinions.'",
    "Artificer::Artillerist": "A patient engineer with a fondness for controlled blasts and the calm tone of someone adjusting a very rude machine.",
    "Artificer::Battle Smith": "The practical romantic who wants both a weapon and a loyal metal companion, preferably tuned to the same frequency.",
    "Artificer::Cartographer": "A map-obsessed gadgeteer who treats distance, direction, and terrain like a personal challenge from the universe.",

    "Barbarian": "A person whose main philosophy is that feelings are real, volume is useful, and furniture is often optional.",
    "Barbarian::Ancestral Guardian": "A furious traditionalist backed by family approval from beyond the grave, which sounds supportive until you meet the family.",
    "Barbarian::Beast": "Someone who gets angry and becomes more tooth, claw, and bad news than usual.",
    "Barbarian::Berserker": "A classic all-gas-no-brakes engine with the bedside manner of a kicked-in tavern door.",
    "Barbarian::Giant": "A large-person enthusiast who thinks every problem improves when scaled up several sizes.",
    "Barbarian::Totem Warrior": "A wilderness mystic whose rage comes with animal branding and a suspicious amount of spiritual confidence.",
    "Barbarian::Wild Magic": "A person who gets mad and the laws of reality begin slipping on loose gravel.",
    "Barbarian::World Tree": "A bruiser with roots, reach, and the energy of an ancient oak finally losing patience.",
    "Barbarian::Zealot": "Someone who treats righteous conviction as a cardio program.",

    "Bard": "A socially weaponized performer who can solve a problem with charm, nerve, and a frankly unreasonable amount of eye contact.",
    "Bard::Creation": "The arts-and-crafts deity's favorite intern, forever turning imagination into visible clutter.",
    "Bard::Dance": "A kinetic peacock who treats footwork as theology and floor space as destiny.",
    "Bard::Eloquence": "A silver-tongued operator who could sell sunlight to a lizard on a rock.",
    "Bard::Glamour": "A dazzling court creature who enters like perfume and leaves like a questionable life choice.",
    "Bard::Lore": "A walking library card with excellent timing and several deeply embarrassing anecdotes about kings.",
    "Bard::Swords": "A stage-swashbuckler who thinks grace, steel, and applause belong in one coordinated package.",
    "Bard::Valor": "A marching-song extrovert who would like courage to be louder and better lit.",
    "Bard::Whispers": "A velvet-voiced rumor merchant who can make a compliment sound like blackmail.",

    "Cleric": "A person with divine backing, a professional tone, and strong feelings about what the cosmos ought to be doing.",
    "Cleric::Arcana": "A temple scholar who smells of incense, ink, and the smugness of being licensed in two departments at once.",
    "Cleric::Death": "A solemn specialist in endings, funerary dignity, and making mortality feel oddly administrative.",
    "Cleric::Forge": "A holy blacksmith type who thinks steel, sweat, and practical devotion are all part of the same prayer.",
    "Cleric::Grave": "A keeper of proper endings with cemetery manners and a firm dislike of unfinished departures.",
    "Cleric::Knowledge": "An archivist of sacred trivia who can make research sound judgmental.",
    "Cleric::Life": "A radiant medic with warm hands, clear eyes, and the quiet authority of fresh sheets.",
    "Cleric::Light": "A bright, scorching enthusiast who arrives like noon through a window nobody asked to open.",
    "Cleric::Nature": "A mossy minister who thinks roots, rain, and divine order are all on speaking terms.",
    "Cleric::Order": "A cosmic administrator who would like the universe alphabetized and everyone standing in the correct line.",
    "Cleric::Peace": "A soft-spoken diplomat whose calm has the tensile strength of steel wire.",
    "Cleric::Tempest": "A storm-priest with sea air in their lungs and weather in their posture.",
    "Cleric::Trickery": "A holy mischief broker who regards honesty as one available option among several.",
    "Cleric::Twilight": "A dusk-colored guardian who smells of cool air, lamp oil, and the hour when the town finally lowers its voice.",
    "Cleric::War": "A battle chaplain who treats discipline as sacred and hesitation as a design flaw.",

    "Druid": "A person who trusts mud, moonlight, and migrating birds more than most civic institutions.",
    "Druid::Dreams": "A soft lantern of a person who seems to have stepped out of a midsummer nap under very old trees.",
    "Druid::Land": "A regional specialist whose soul has local weather and strong opinions about soil.",
    "Druid::Moon": "A shape-changing naturalist who regards having one body as an unnecessary limitation.",
    "Druid::Sea": "A tide-minded mystic with salt in their hair and a patient respect for undertow.",
    "Druid::Shepherd": "A gentle organizer of beasts and spirits, essentially a field manager for the nonhuman world.",
    "Druid::Spores": "A damp little philosopher of rot, mushrooms, and the useful side of decay.",
    "Druid::Stars": "A celestial swamp-witch astronomer who reads the night sky like a favorite cookbook.",
    "Druid::Wildfire": "A controlled-burn visionary who thinks destruction and renewal should really stop pretending to be strangers.",

    "Fighter": "A professional in the oldest trade on earth: being alarmingly competent when things get physical.",
    "Fighter::Battle Master": "A tactician with the dry stare of someone who has already measured the room and found it lacking.",
    "Fighter::Cavalier": "A formal bruiser built for loyalty, posture, and occupying space with aristocratic certainty.",
    "Fighter::Champion": "A clean, classic athlete of violence who has never met a straightforward solution they did not respect.",
    "Fighter::Echo Knight": "A person followed by their own extra self, which is convenient and also mildly unsettling.",
    "Fighter::Eldritch Knight": "A practical soldier who added just enough magic to become intolerable at dinner.",
    "Fighter::Psi Warrior": "A disciplined combatant powered partly by concentration and partly by the conviction that physics is flexible.",
    "Fighter::Rune Knight": "A heavily upgraded giant-lore enthusiast who treats armor like a public monument.",
    "Fighter::Samurai": "A composed, ceremonial menace with the emotional restraint of polished wood and a blade that disagrees.",

    "Monk": "A person who took the body seriously, then took the mind seriously, then made both everyone else's problem.",
    "Monk::Astral Self": "A disciplined eccentric whose inner being has become visible and, annoyingly, looks excellent.",
    "Monk::Long Death": "A still, unsettling contemplative who studies mortality with the calm interest of a botanist.",
    "Monk::Mercy": "A masked healer-punisher hybrid who brings medicine, discipline, and very mixed feelings.",
    "Monk::Open Hand": "A minimalist perfectionist who can make basic technique feel like a personal insult.",
    "Monk::Shadow": "A quiet operator built from dusk, patience, and the useful fact that most people do not look up.",
    "Monk::Warrior of the Elements": "A martial ascetic who decided punches were good but weather would really complete the set.",

    "Paladin": "A walking oath in polished boots, powered by conviction and the inability to leave a principle alone.",
    "Paladin::Ancients": "A green-gold knight of old groves, old joy, and the last decent patch of sunlight.",
    "Paladin::Conquest": "A steel-spined authoritarian who believes fear is simply efficiency wearing a cape.",
    "Paladin::Devotion": "A painfully sincere exemplar with clean lines, bright armor, and no ironic distance whatsoever.",
    "Paladin::Redemption": "A patient idealist trying very hard to solve things before the swords come out.",
    "Paladin::Vengeance": "A grim promise with boots on, moving steadily toward the part where someone regrets everything.",
    "Paladin::Watchers": "A vigilant border-guard for reality itself, forever scanning the horizon for nonsense.",

    "Ranger": "A field specialist who knows where the tracks go, what made them, and whether you should already be worried.",
    "Ranger::Beast Master": "A competent wilderness professional with an animal partner and better priorities than most governments.",
    "Ranger::Drakewarden": "Someone who thought a dragon would improve their logistics and, irritatingly, was right.",
    "Ranger::Fey Wanderer": "A traveler touched by beautiful strangeness, like a forest path that suddenly starts giving side-eye.",
    "Ranger::Gloom Stalker": "A low-light specialist built for cellars, tunnels, and the hour when the street finally empties.",
    "Ranger::Horizon Walker": "A planar customs officer with boots dusty from places maps cannot agree on.",
    "Ranger::Hunter": "A classic practical predator, all sharpened senses, clean decisions, and no decorative nonsense.",
    "Ranger::Swarmkeeper": "A patient oddity attended by bees, moths, birds, or similar tiny assistants with excellent union spirit.",

    "Rogue": "A nimble opportunist who notices the latch, the purse, the blind angle, and your bad assumptions.",
    "Rogue::Arcane Trickster": "A thief who added spellcraft to an already disrespectful skill set.",
    "Rogue::Phantom": "A cool, grave-scented operator with one foot in memory and the other in your locked cabinet.",
    "Rogue::Soulknife": "A sleek psychic troublemaker whose weapons arrive looking far too convenient.",
    "Rogue::Swashbuckler": "A polished peacock with a blade, a grin, and absolutely no indoor voice.",
    "Rogue::Thief": "A classic second-story artisan who treats windows, locks, and unattended valuables as open invitations.",

    "Sorcerer": "A person who did not study power so much as wake up already inconveniently full of it.",
    "Sorcerer::Aberrant Mind": "A silk-voiced oddity with a beautifully arranged exterior and some deeply unlocal weather behind the eyes.",
    "Sorcerer::Clockwork Soul": "A strangely precise spellcaster who seems one brass hinge away from solving the cosmos by filing it.",
    "Sorcerer::Divine Soul": "A naturally radiant prodigy whose magic arrives wearing very expensive lighting.",
    "Sorcerer::Draconic Bloodline": "A proud, gleaming heir to reptilian grandeur, with excellent posture and at least one unnecessary flourish.",
    "Sorcerer::Shadow Magic": "A low-lit voltage source who seems built from moonless alleys and withheld information.",
    "Sorcerer::Wild Magic": "An ambulatory coincidence factory that should come with warning labels and a cheerful little bell.",

    "Warlock": "A person who saw power, signed something, and now has the posture of someone with very interesting mail.",
    "Warlock::Archfey": "A charmed and dangerous court stray with flower-sweet manners and deeply unreliable intentions.",
    "Warlock::Celestial": "A pact-bearer with bright edges, warm hands, and the energy of a stained-glass window that makes threats.",
    "Warlock::Fathomless": "A sea-dark contract holder who smells faintly of brine, rope, and things seen far below the pier.",
    "Warlock::Fiend": "A polished disaster with embers in the grin and contractual confidence in the eyes.",
    "Warlock::Genie": "A luxe, wish-adjacent operative who carries the air of silk cushions and dangerous convenience.",
    "Warlock::Great Old One": "A composed little antenna pointed toward truths that really ought to remain off the menu.",
    "Warlock::Hexblade": "A stylish pessimist who looked at a cursed weapon and thought, 'Finally, a colleague.'",
    "Warlock::Undead": "A cool, sepulchral customer whose vibe is formalwear, old coins, and the unreasonable persistence of important people.",

    "Wizard": "A trained arcane specialist who believes every mystery can be indexed, annotated, and eventually bullied into clarity.",
    "Wizard::Abjuration": "A magical risk manager who would like the world padded, warded, and less theatrical.",
    "Wizard::Bladesinger": "An elegant scholar-athlete who made swordplay look academically peer-reviewed.",
    "Wizard::Conjuration": "A spatial opportunist who solves shortages by simply producing the required item with a smug little gesture.",
    "Wizard::Divination": "A tea-stained foresight addict forever peering around corners time has not technically reached yet.",
    "Wizard::Enchantment": "A specialist in persuasion so refined it begins to feel architectural.",
    "Wizard::Evocation": "A fireworks intellectual with a suspicious fondness for clean lines and scorched air.",
    "Wizard::Illusion": "A curated liar with excellent taste, perfect timing, and a strong respect for plausible nonsense.",
    "Wizard::Necromancy": "A grave-minded academic who saw mortality and decided it needed more research.",
    "Wizard::Order of Scribes": "A book-besotted scriptomancer whose pen, paper, and filing habits have become frankly overqualified.",
    "Wizard::Transmutation": "A material-world tinkerer forever convinced that one more adjustment will finally perfect the furniture.",
}



# ---------------------------------------------------------------------------
# Subclass scoring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubclassDefinition:
    key: str
    display_name: str
    parent_class: str
    axis_weights: Mapping[str, float]
    synergy_groups: Tuple[Tuple[str, ...], ...] = field(default_factory=tuple)
    anti_axes: Mapping[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class ScoredSubclass:
    key: str
    parent_class: str
    score: float
    direct_score: float
    class_score: float
    synergy_score: float
    penalty_score: float


@dataclass(frozen=True)
class SubclassAssignment:
    parent_class: str
    primary_subclass: str
    primary_score: float
    secondary_subclass: Optional[str]
    secondary_score: float
    confidence_gap: float
    subclass_scores: Mapping[str, float]


@dataclass(frozen=True)
class DnDBuildAssignment:
    class_assignment: ClassAssignment
    subclass_assignment: SubclassAssignment


DND_SUBCLASSES: Dict[str, Dict[str, SubclassDefinition]] = {
    "Artificer": {
        "Alchemist": SubclassDefinition(
            key="Alchemist",
            display_name="Alchemist",
            parent_class="Artificer",
            axis_weights={'technical_inventiveness': 0.28,
 'study': 0.2,
 'mercy_restoration': 0.22,
 'control_planning': 0.16,
 'risk_appetite': 0.14},
            synergy_groups=(('technical_inventiveness', 'mercy_restoration'), ('study', 'control_planning')),
            anti_axes={'instinct': 0.08},
            notes="Experimental support-through-craft with volatile utility.",
        ),
        "Armorer": SubclassDefinition(
            key="Armorer",
            display_name="Armorer",
            parent_class="Artificer",
            axis_weights={'technical_inventiveness': 0.28, 'discipline': 0.22, 'frontline_courage': 0.22, 'control_planning': 0.18, 'study': 0.1},
            synergy_groups=(('technical_inventiveness', 'frontline_courage'), ('discipline', 'control_planning')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Engineered protection and armored field presence.",
        ),
        "Artillerist": SubclassDefinition(
            key="Artillerist",
            display_name="Artillerist",
            parent_class="Artificer",
            axis_weights={'technical_inventiveness': 0.3,
 'control_planning': 0.24,
 'risk_appetite': 0.2,
 'study': 0.16,
 'frontline_courage': 0.1},
            synergy_groups=(('technical_inventiveness', 'control_planning'), ('technical_inventiveness', 'risk_appetite')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Distance, devices, and elegant overkill.",
        ),
        "Battle Smith": SubclassDefinition(
            key="Battle Smith",
            display_name="Battle Smith",
            parent_class="Artificer",
            axis_weights={'technical_inventiveness': 0.26,
 'frontline_courage': 0.22,
 'discipline': 0.18,
 'mercy_restoration': 0.18,
 'control_planning': 0.16},
            synergy_groups=(('technical_inventiveness', 'frontline_courage'), ('technical_inventiveness', 'mercy_restoration')),
            anti_axes={'performance': 0.04},
            notes="Practical engineering pressed into loyal combat service.",
        ),
        "Cartographer": SubclassDefinition(
            key="Cartographer",
            display_name="Cartographer",
            parent_class="Artificer",
            axis_weights={'technical_inventiveness': 0.26,
 'study': 0.24,
 'control_planning': 0.22,
 'nature_attunement': 0.16,
 'stealth_indirection': 0.12},
            synergy_groups=(('technical_inventiveness', 'study'), ('study', 'control_planning')),
            anti_axes={'frontline_courage': 0.04},
            notes="Applied navigation, surveying, and world-modeling.",
        ),
    },
    "Barbarian": {
        "Ancestral Guardian": SubclassDefinition(
            key="Ancestral Guardian",
            display_name="Ancestral Guardian",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.28, 'frontline_courage': 0.22, 'faith': 0.16, 'social_leadership': 0.18, 'mercy_restoration': 0.16},
            synergy_groups=(('instinct', 'frontline_courage'), ('faith', 'social_leadership')),
            anti_axes={'study': 0.08},
            notes="Protective ferocity guided by lineage and duty.",
        ),
        "Beast": SubclassDefinition(
            key="Beast",
            display_name="Beast",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.34,
 'frontline_courage': 0.22,
 'nature_attunement': 0.18,
 'risk_appetite': 0.18,
 'stealth_indirection': 0.08},
            synergy_groups=(('instinct', 'nature_attunement'), ('instinct', 'risk_appetite')),
            anti_axes={'study': 0.1},
            notes="Animal embodiment and adaptive bodily aggression.",
        ),
        "Berserker": SubclassDefinition(
            key="Berserker",
            display_name="Berserker",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.34, 'frontline_courage': 0.3, 'risk_appetite': 0.24, 'social_leadership': 0.12},
            synergy_groups=(('instinct', 'frontline_courage'), ('frontline_courage', 'risk_appetite')),
            anti_axes={'control_planning': 0.1, 'study': 0.1},
            notes="Direct rage with minimal mediation.",
        ),
        "Giant": SubclassDefinition(
            key="Giant",
            display_name="Giant",
            parent_class="Barbarian",
            axis_weights={'frontline_courage': 0.28, 'instinct': 0.24, 'risk_appetite': 0.18, 'innate_power': 0.18, 'social_leadership': 0.12},
            synergy_groups=(('frontline_courage', 'innate_power'), ('instinct', 'risk_appetite')),
            anti_axes={'stealth_indirection': 0.1},
            notes="Enlarged force and mythic physical presence.",
        ),
        "Totem Warrior": SubclassDefinition(
            key="Totem Warrior",
            display_name="Totem Warrior",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.26, 'nature_attunement': 0.24, 'frontline_courage': 0.18, 'faith': 0.16, 'mercy_restoration': 0.16},
            synergy_groups=(('instinct', 'nature_attunement'), ('nature_attunement', 'faith')),
            anti_axes={'technical_inventiveness': 0.08},
            notes="Primal identity braided with spiritual animal alignment.",
        ),
        "Wild Magic": SubclassDefinition(
            key="Wild Magic",
            display_name="Wild Magic",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.24, 'risk_appetite': 0.26, 'innate_power': 0.24, 'frontline_courage': 0.16, 'performance': 0.1},
            synergy_groups=(('instinct', 'risk_appetite'), ('innate_power', 'risk_appetite')),
            anti_axes={'control_planning': 0.1},
            notes="Body-first chaos with magical backfire potential.",
        ),
        "World Tree": SubclassDefinition(
            key="World Tree",
            display_name="World Tree",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.22,
 'nature_attunement': 0.24,
 'mercy_restoration': 0.2,
 'control_planning': 0.18,
 'frontline_courage': 0.16},
            synergy_groups=(('nature_attunement', 'mercy_restoration'), ('instinct', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Rooted durability and connective protective reach.",
        ),
        "Zealot": SubclassDefinition(
            key="Zealot",
            display_name="Zealot",
            parent_class="Barbarian",
            axis_weights={'instinct': 0.24, 'frontline_courage': 0.24, 'faith': 0.24, 'risk_appetite': 0.18, 'social_leadership': 0.1},
            synergy_groups=(('faith', 'frontline_courage'), ('instinct', 'faith')),
            anti_axes={'stealth_indirection': 0.08},
            notes="Holy fury with no patience for half-belief.",
        ),
    },
    "Bard": {
        "Creation": SubclassDefinition(
            key="Creation",
            display_name="Creation",
            parent_class="Bard",
            axis_weights={'performance': 0.28, 'study': 0.2, 'innate_power': 0.18, 'control_planning': 0.18, 'social_leadership': 0.16},
            synergy_groups=(('performance', 'study'), ('performance', 'innate_power')),
            anti_axes={'patron_reliance': 0.04},
            notes="Expressive world-making and aesthetic manifestation.",
        ),
        "Dance": SubclassDefinition(
            key="Dance",
            display_name="Dance",
            parent_class="Bard",
            axis_weights={'performance': 0.3, 'frontline_courage': 0.2, 'risk_appetite': 0.18, 'discipline': 0.18, 'social_leadership': 0.14},
            synergy_groups=(('performance', 'discipline'), ('performance', 'frontline_courage')),
            anti_axes={'control_planning': 0.04},
            notes="Embodied rhythm as offense, defense, and persuasion.",
        ),
        "Eloquence": SubclassDefinition(
            key="Eloquence",
            display_name="Eloquence",
            parent_class="Bard",
            axis_weights={'performance': 0.3, 'social_leadership': 0.26, 'study': 0.18, 'control_planning': 0.14, 'mercy_restoration': 0.12},
            synergy_groups=(('performance', 'social_leadership'), ('study', 'performance')),
            anti_axes={'frontline_courage': 0.04},
            notes="Language treated as a precision weapon.",
        ),
        "Glamour": SubclassDefinition(
            key="Glamour",
            display_name="Glamour",
            parent_class="Bard",
            axis_weights={'performance': 0.28,
 'social_leadership': 0.22,
 'innate_power': 0.2,
 'mercy_restoration': 0.14,
 'stealth_indirection': 0.16},
            synergy_groups=(('performance', 'innate_power'), ('performance', 'social_leadership')),
            anti_axes={'discipline': 0.04},
            notes="Beauty, allure, and enthralling social force.",
        ),
        "Lore": SubclassDefinition(
            key="Lore",
            display_name="Lore",
            parent_class="Bard",
            axis_weights={'study': 0.28,
 'performance': 0.24,
 'control_planning': 0.18,
 'social_leadership': 0.16,
 'technical_inventiveness': 0.14},
            synergy_groups=(('study', 'performance'), ('study', 'control_planning')),
            anti_axes={'frontline_courage': 0.04},
            notes="Scholarship made conversational and weaponizable.",
        ),
        "Swords": SubclassDefinition(
            key="Swords",
            display_name="Swords",
            parent_class="Bard",
            axis_weights={'performance': 0.24, 'frontline_courage': 0.22, 'discipline': 0.2, 'risk_appetite': 0.16, 'social_leadership': 0.18},
            synergy_groups=(('performance', 'frontline_courage'), ('discipline', 'performance')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Showmanship fused to blade timing.",
        ),
        "Valor": SubclassDefinition(
            key="Valor",
            display_name="Valor",
            parent_class="Bard",
            axis_weights={'performance': 0.2,
 'frontline_courage': 0.24,
 'social_leadership': 0.22,
 'discipline': 0.18,
 'mercy_restoration': 0.16},
            synergy_groups=(('social_leadership', 'frontline_courage'), ('performance', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.04},
            notes="The rallying, public-facing martial bard lane.",
        ),
        "Whispers": SubclassDefinition(
            key="Whispers",
            display_name="Whispers",
            parent_class="Bard",
            axis_weights={'stealth_indirection': 0.28,
 'performance': 0.22,
 'control_planning': 0.18,
 'patron_reliance': 0.16,
 'social_leadership': 0.16},
            synergy_groups=(('stealth_indirection', 'performance'), ('stealth_indirection', 'control_planning')),
            anti_axes={'mercy_restoration': 0.06},
            notes="Rumor, dread, and private psychic leverage.",
        ),
    },
    "Cleric": {
        "Arcana": SubclassDefinition(
            key="Arcana",
            display_name="Arcana",
            parent_class="Cleric",
            axis_weights={'faith': 0.24, 'study': 0.24, 'control_planning': 0.18, 'innate_power': 0.18, 'mercy_restoration': 0.16},
            synergy_groups=(('faith', 'study'), ('faith', 'control_planning')),
            anti_axes={'risk_appetite': 0.04},
            notes="Sacred doctrine plus codified spellcraft.",
        ),
        "Death": SubclassDefinition(
            key="Death",
            display_name="Death",
            parent_class="Cleric",
            axis_weights={'faith': 0.24,
 'patron_reliance': 0.22,
 'control_planning': 0.18,
 'frontline_courage': 0.18,
 'stealth_indirection': 0.18},
            synergy_groups=(('faith', 'patron_reliance'), ('faith', 'control_planning')),
            anti_axes={'mercy_restoration': 0.1},
            notes="Sanctioned mortality, not cheerful necrophilia.",
        ),
        "Forge": SubclassDefinition(
            key="Forge",
            display_name="Forge",
            parent_class="Cleric",
            axis_weights={'faith': 0.24,
 'technical_inventiveness': 0.24,
 'discipline': 0.22,
 'frontline_courage': 0.18,
 'control_planning': 0.12},
            synergy_groups=(('faith', 'technical_inventiveness'), ('discipline', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Craft, durability, and consecrated making.",
        ),
        "Grave": SubclassDefinition(
            key="Grave",
            display_name="Grave",
            parent_class="Cleric",
            axis_weights={'faith': 0.24, 'mercy_restoration': 0.2, 'control_planning': 0.2, 'stealth_indirection': 0.18, 'patron_reliance': 0.18},
            synergy_groups=(('faith', 'mercy_restoration'), ('faith', 'control_planning')),
            anti_axes={'risk_appetite': 0.08},
            notes="Threshold-keeping, balance, and measured dealings with death.",
        ),
        "Knowledge": SubclassDefinition(
            key="Knowledge",
            display_name="Knowledge",
            parent_class="Cleric",
            axis_weights={'faith': 0.22, 'study': 0.3, 'control_planning': 0.22, 'social_leadership': 0.12, 'mercy_restoration': 0.14},
            synergy_groups=(('faith', 'study'), ('study', 'control_planning')),
            anti_axes={'frontline_courage': 0.04},
            notes="Doctrine as library, inquiry, and memory.",
        ),
        "Life": SubclassDefinition(
            key="Life",
            display_name="Life",
            parent_class="Cleric",
            axis_weights={'faith': 0.28,
 'mercy_restoration': 0.3,
 'social_leadership': 0.18,
 'control_planning': 0.12,
 'frontline_courage': 0.12},
            synergy_groups=(('faith', 'mercy_restoration'), ('mercy_restoration', 'social_leadership')),
            anti_axes={'risk_appetite': 0.08},
            notes="Healing, preservation, and clear benefic commitment.",
        ),
        "Light": SubclassDefinition(
            key="Light",
            display_name="Light",
            parent_class="Cleric",
            axis_weights={'faith': 0.26, 'innate_power': 0.22, 'frontline_courage': 0.18, 'social_leadership': 0.18, 'risk_appetite': 0.16},
            synergy_groups=(('faith', 'innate_power'), ('faith', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.08},
            notes="Radiant certainty with very little interest in subtle corners.",
        ),
        "Nature": SubclassDefinition(
            key="Nature",
            display_name="Nature",
            parent_class="Cleric",
            axis_weights={'faith': 0.22,
 'nature_attunement': 0.28,
 'mercy_restoration': 0.18,
 'frontline_courage': 0.14,
 'control_planning': 0.18},
            synergy_groups=(('faith', 'nature_attunement'), ('nature_attunement', 'mercy_restoration')),
            anti_axes={'technical_inventiveness': 0.06},
            notes="Sanctified ecology and stewardship.",
        ),
        "Order": SubclassDefinition(
            key="Order",
            display_name="Order",
            parent_class="Cleric",
            axis_weights={'faith': 0.26, 'control_planning': 0.28, 'social_leadership': 0.2, 'discipline': 0.16, 'mercy_restoration': 0.1},
            synergy_groups=(('faith', 'control_planning'), ('faith', 'social_leadership')),
            anti_axes={'risk_appetite': 0.08},
            notes="Authority, sequence, and doctrinal structure.",
        ),
        "Peace": SubclassDefinition(
            key="Peace",
            display_name="Peace",
            parent_class="Cleric",
            axis_weights={'faith': 0.26,
 'mercy_restoration': 0.26,
 'social_leadership': 0.22,
 'control_planning': 0.14,
 'stealth_indirection': 0.12},
            synergy_groups=(('faith', 'mercy_restoration'), ('mercy_restoration', 'social_leadership')),
            anti_axes={'frontline_courage': 0.04},
            notes="Protective harmony, not passivity.",
        ),
        "Tempest": SubclassDefinition(
            key="Tempest",
            display_name="Tempest",
            parent_class="Cleric",
            axis_weights={'faith': 0.22, 'frontline_courage': 0.24, 'risk_appetite': 0.22, 'innate_power': 0.18, 'social_leadership': 0.14},
            synergy_groups=(('faith', 'frontline_courage'), ('risk_appetite', 'innate_power')),
            anti_axes={'stealth_indirection': 0.06},
            notes="Weather as judgment and force projection.",
        ),
        "Trickery": SubclassDefinition(
            key="Trickery",
            display_name="Trickery",
            parent_class="Cleric",
            axis_weights={'faith': 0.2, 'stealth_indirection': 0.3, 'performance': 0.18, 'control_planning': 0.18, 'social_leadership': 0.14},
            synergy_groups=(('faith', 'stealth_indirection'), ('stealth_indirection', 'performance')),
            anti_axes={'frontline_courage': 0.06},
            notes="Sacred misdirection and sanctioned angle-play.",
        ),
        "Twilight": SubclassDefinition(
            key="Twilight",
            display_name="Twilight",
            parent_class="Cleric",
            axis_weights={'faith': 0.24,
 'stealth_indirection': 0.18,
 'mercy_restoration': 0.22,
 'control_planning': 0.2,
 'social_leadership': 0.16},
            synergy_groups=(('faith', 'mercy_restoration'), ('faith', 'stealth_indirection')),
            anti_axes={'risk_appetite': 0.04},
            notes="Liminal protection, dusk vigilance, and shelter.",
        ),
        "War": SubclassDefinition(
            key="War",
            display_name="War",
            parent_class="Cleric",
            axis_weights={'faith': 0.22, 'frontline_courage': 0.28, 'discipline': 0.22, 'social_leadership': 0.14, 'control_planning': 0.14},
            synergy_groups=(('faith', 'frontline_courage'), ('discipline', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.06},
            notes="The marching-order branch of sacred force.",
        ),
    },
    "Druid": {
        "Dreams": SubclassDefinition(
            key="Dreams",
            display_name="Dreams",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.26, 'mercy_restoration': 0.24, 'innate_power': 0.18, 'faith': 0.16, 'stealth_indirection': 0.16},
            synergy_groups=(('nature_attunement', 'mercy_restoration'), ('nature_attunement', 'innate_power')),
            anti_axes={'technical_inventiveness': 0.06},
            notes="Restorative, liminal, and quietly otherworldly.",
        ),
        "Land": SubclassDefinition(
            key="Land",
            display_name="Land",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.28, 'study': 0.2, 'control_planning': 0.22, 'faith': 0.14, 'mercy_restoration': 0.16},
            synergy_groups=(('nature_attunement', 'study'), ('nature_attunement', 'control_planning')),
            anti_axes={'risk_appetite': 0.04},
            notes="Biome literacy, memory, and place-specific method.",
        ),
        "Moon": SubclassDefinition(
            key="Moon",
            display_name="Moon",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.26,
 'instinct': 0.26,
 'frontline_courage': 0.2,
 'risk_appetite': 0.16,
 'mercy_restoration': 0.12},
            synergy_groups=(('nature_attunement', 'instinct'), ('instinct', 'frontline_courage')),
            anti_axes={'study': 0.06},
            notes="Embodied transformation and beast-form immediacy.",
        ),
        "Sea": SubclassDefinition(
            key="Sea",
            display_name="Sea",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.28,
 'control_planning': 0.18,
 'mercy_restoration': 0.18,
 'risk_appetite': 0.18,
 'innate_power': 0.18},
            synergy_groups=(('nature_attunement', 'control_planning'), ('nature_attunement', 'risk_appetite')),
            anti_axes={'discipline': 0.04},
            notes="Tidal force, adaptation, and wet inevitability.",
        ),
        "Shepherd": SubclassDefinition(
            key="Shepherd",
            display_name="Shepherd",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.3,
 'mercy_restoration': 0.24,
 'social_leadership': 0.18,
 'faith': 0.14,
 'control_planning': 0.14},
            synergy_groups=(('nature_attunement', 'mercy_restoration'), ('nature_attunement', 'social_leadership')),
            anti_axes={'frontline_courage': 0.04},
            notes="Guardian of creatures, circles, and living networks.",
        ),
        "Spores": SubclassDefinition(
            key="Spores",
            display_name="Spores",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.24,
 'patron_reliance': 0.18,
 'control_planning': 0.22,
 'stealth_indirection': 0.18,
 'frontline_courage': 0.18},
            synergy_groups=(('nature_attunement', 'control_planning'), ('nature_attunement', 'patron_reliance')),
            anti_axes={'social_leadership': 0.04},
            notes="Decay, proliferation, and ecological morbidity.",
        ),
        "Stars": SubclassDefinition(
            key="Stars",
            display_name="Stars",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.24, 'study': 0.22, 'innate_power': 0.2, 'faith': 0.18, 'control_planning': 0.16},
            synergy_groups=(('nature_attunement', 'study'), ('innate_power', 'faith')),
            anti_axes={'frontline_courage': 0.04},
            notes="Celestial pattern-reading rather than rustic simplicity.",
        ),
        "Wildfire": SubclassDefinition(
            key="Wildfire",
            display_name="Wildfire",
            parent_class="Druid",
            axis_weights={'nature_attunement': 0.22,
 'risk_appetite': 0.22,
 'innate_power': 0.2,
 'frontline_courage': 0.18,
 'mercy_restoration': 0.18},
            synergy_groups=(('nature_attunement', 'risk_appetite'), ('innate_power', 'mercy_restoration')),
            anti_axes={'control_planning': 0.04},
            notes="Destruction and renewal in the same breath.",
        ),
    },
    "Fighter": {
        "Battle Master": SubclassDefinition(
            key="Battle Master",
            display_name="Battle Master",
            parent_class="Fighter",
            axis_weights={'discipline': 0.3, 'control_planning': 0.26, 'frontline_courage': 0.22, 'study': 0.12, 'social_leadership': 0.1},
            synergy_groups=(('discipline', 'control_planning'), ('discipline', 'frontline_courage')),
            anti_axes={'patron_reliance': 0.04},
            notes="Tactical literacy and trained martial sequencing.",
        ),
        "Cavalier": SubclassDefinition(
            key="Cavalier",
            display_name="Cavalier",
            parent_class="Fighter",
            axis_weights={'discipline': 0.24,
 'frontline_courage': 0.26,
 'social_leadership': 0.22,
 'control_planning': 0.16,
 'mercy_restoration': 0.12},
            synergy_groups=(('frontline_courage', 'social_leadership'), ('discipline', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.06},
            notes="Protective prominence and mounted-guardian energy.",
        ),
        "Champion": SubclassDefinition(
            key="Champion",
            display_name="Champion",
            parent_class="Fighter",
            axis_weights={'frontline_courage': 0.3, 'discipline': 0.24, 'instinct': 0.18, 'social_leadership': 0.18, 'risk_appetite': 0.1},
            synergy_groups=(('frontline_courage', 'discipline'), ('frontline_courage', 'instinct')),
            anti_axes={'study': 0.04},
            notes="Pure athletic martial competence.",
        ),
        "Echo Knight": SubclassDefinition(
            key="Echo Knight",
            display_name="Echo Knight",
            parent_class="Fighter",
            axis_weights={'frontline_courage': 0.2,
 'control_planning': 0.24,
 'innate_power': 0.2,
 'stealth_indirection': 0.18,
 'discipline': 0.18},
            synergy_groups=(('control_planning', 'innate_power'), ('frontline_courage', 'control_planning')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Spatial weirdness grafted onto a Fighter chassis.",
        ),
        "Eldritch Knight": SubclassDefinition(
            key="Eldritch Knight",
            display_name="Eldritch Knight",
            parent_class="Fighter",
            axis_weights={'discipline': 0.22,
 'study': 0.24,
 'control_planning': 0.22,
 'frontline_courage': 0.18,
 'technical_inventiveness': 0.14},
            synergy_groups=(('discipline', 'study'), ('study', 'control_planning')),
            anti_axes={'instinct': 0.04},
            notes="Martial method plus learned arcana.",
        ),
        "Psi Warrior": SubclassDefinition(
            key="Psi Warrior",
            display_name="Psi Warrior",
            parent_class="Fighter",
            axis_weights={'discipline': 0.22, 'control_planning': 0.22, 'innate_power': 0.22, 'frontline_courage': 0.18, 'study': 0.16},
            synergy_groups=(('discipline', 'innate_power'), ('control_planning', 'innate_power')),
            anti_axes={'performance': 0.04},
            notes="Internal force projected through martial control.",
        ),
        "Rune Knight": SubclassDefinition(
            key="Rune Knight",
            display_name="Rune Knight",
            parent_class="Fighter",
            axis_weights={'discipline': 0.22,
 'technical_inventiveness': 0.22,
 'frontline_courage': 0.22,
 'innate_power': 0.18,
 'control_planning': 0.16},
            synergy_groups=(('technical_inventiveness', 'frontline_courage'), ('discipline', 'technical_inventiveness')),
            anti_axes={'stealth_indirection': 0.06},
            notes="Inscribed might, enlargement, and crafted power.",
        ),
        "Samurai": SubclassDefinition(
            key="Samurai",
            display_name="Samurai",
            parent_class="Fighter",
            axis_weights={'discipline': 0.26, 'frontline_courage': 0.24, 'social_leadership': 0.2, 'control_planning': 0.16, 'faith': 0.14},
            synergy_groups=(('discipline', 'frontline_courage'), ('discipline', 'social_leadership')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Formal courage, poise, and visible resolve.",
        ),
    },
    "Monk": {
        "Astral Self": SubclassDefinition(
            key="Astral Self",
            display_name="Astral Self",
            parent_class="Monk",
            axis_weights={'discipline': 0.24, 'faith': 0.2, 'innate_power': 0.22, 'control_planning': 0.18, 'frontline_courage': 0.16},
            synergy_groups=(('discipline', 'innate_power'), ('faith', 'control_planning')),
            anti_axes={'performance': 0.04},
            notes="Expanded spiritual body and self-projection.",
        ),
        "Long Death": SubclassDefinition(
            key="Long Death",
            display_name="Long Death",
            parent_class="Monk",
            axis_weights={'discipline': 0.22,
 'frontline_courage': 0.2,
 'control_planning': 0.18,
 'patron_reliance': 0.2,
 'stealth_indirection': 0.2},
            synergy_groups=(('discipline', 'control_planning'), ('frontline_courage', 'patron_reliance')),
            anti_axes={'mercy_restoration': 0.08},
            notes="Mortality fixation with disciplined menace.",
        ),
        "Mercy": SubclassDefinition(
            key="Mercy",
            display_name="Mercy",
            parent_class="Monk",
            axis_weights={'discipline': 0.24, 'mercy_restoration': 0.28, 'faith': 0.18, 'frontline_courage': 0.16, 'control_planning': 0.14},
            synergy_groups=(('discipline', 'mercy_restoration'), ('faith', 'mercy_restoration')),
            anti_axes={'risk_appetite': 0.04},
            notes="Precise healing and equally precise harm.",
        ),
        "Open Hand": SubclassDefinition(
            key="Open Hand",
            display_name="Open Hand",
            parent_class="Monk",
            axis_weights={'discipline': 0.28, 'instinct': 0.2, 'frontline_courage': 0.22, 'control_planning': 0.18, 'mercy_restoration': 0.12},
            synergy_groups=(('discipline', 'instinct'), ('discipline', 'frontline_courage')),
            anti_axes={'patron_reliance': 0.04},
            notes="The plainspoken core monk: technique over ornament.",
        ),
        "Shadow": SubclassDefinition(
            key="Shadow",
            display_name="Shadow",
            parent_class="Monk",
            axis_weights={'discipline': 0.22, 'stealth_indirection': 0.3, 'control_planning': 0.2, 'frontline_courage': 0.14, 'study': 0.14},
            synergy_groups=(('discipline', 'stealth_indirection'), ('stealth_indirection', 'control_planning')),
            anti_axes={'social_leadership': 0.06},
            notes="Concealment, repositioning, and austere infiltration.",
        ),
        "Warrior of the Elements": SubclassDefinition(
            key="Warrior of the Elements",
            display_name="Warrior of the Elements",
            parent_class="Monk",
            axis_weights={'discipline': 0.22, 'innate_power': 0.24, 'risk_appetite': 0.18, 'frontline_courage': 0.18, 'nature_attunement': 0.18},
            synergy_groups=(('discipline', 'innate_power'), ('innate_power', 'risk_appetite')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Elemental expression channeled through trained bodywork.",
        ),
    },
    "Paladin": {
        "Ancients": SubclassDefinition(
            key="Ancients",
            display_name="Ancients",
            parent_class="Paladin",
            axis_weights={'faith': 0.26,
 'nature_attunement': 0.22,
 'mercy_restoration': 0.2,
 'frontline_courage': 0.16,
 'social_leadership': 0.16},
            synergy_groups=(('faith', 'nature_attunement'), ('faith', 'mercy_restoration')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Life-affirming oathwork with green old-magic overtones.",
        ),
        "Conquest": SubclassDefinition(
            key="Conquest",
            display_name="Conquest",
            parent_class="Paladin",
            axis_weights={'faith': 0.22, 'frontline_courage': 0.26, 'control_planning': 0.22, 'social_leadership': 0.16, 'risk_appetite': 0.14},
            synergy_groups=(('faith', 'frontline_courage'), ('control_planning', 'social_leadership')),
            anti_axes={'mercy_restoration': 0.1},
            notes="Order through fear, dominance, and force.",
        ),
        "Devotion": SubclassDefinition(
            key="Devotion",
            display_name="Devotion",
            parent_class="Paladin",
            axis_weights={'faith': 0.28, 'social_leadership': 0.22, 'frontline_courage': 0.2, 'discipline': 0.18, 'mercy_restoration': 0.12},
            synergy_groups=(('faith', 'social_leadership'), ('faith', 'frontline_courage')),
            anti_axes={'stealth_indirection': 0.06},
            notes="The classic shining-oath lane.",
        ),
        "Redemption": SubclassDefinition(
            key="Redemption",
            display_name="Redemption",
            parent_class="Paladin",
            axis_weights={'faith': 0.24,
 'mercy_restoration': 0.28,
 'control_planning': 0.18,
 'social_leadership': 0.18,
 'frontline_courage': 0.12},
            synergy_groups=(('faith', 'mercy_restoration'), ('mercy_restoration', 'control_planning')),
            anti_axes={'risk_appetite': 0.08},
            notes="Protective restraint with stubborn moral optimism.",
        ),
        "Vengeance": SubclassDefinition(
            key="Vengeance",
            display_name="Vengeance",
            parent_class="Paladin",
            axis_weights={'faith': 0.22, 'frontline_courage': 0.24, 'stealth_indirection': 0.16, 'risk_appetite': 0.18, 'control_planning': 0.2},
            synergy_groups=(('faith', 'frontline_courage'), ('stealth_indirection', 'control_planning')),
            anti_axes={'mercy_restoration': 0.08},
            notes="Focused pursuit and oath-shaped retribution.",
        ),
        "Watchers": SubclassDefinition(
            key="Watchers",
            display_name="Watchers",
            parent_class="Paladin",
            axis_weights={'faith': 0.24, 'control_planning': 0.24, 'study': 0.18, 'social_leadership': 0.18, 'frontline_courage': 0.16},
            synergy_groups=(('faith', 'control_planning'), ('study', 'control_planning')),
            anti_axes={'instinct': 0.04},
            notes="Vigilant anti-incursion discipline.",
        ),
    },
    "Ranger": {
        "Beast Master": SubclassDefinition(
            key="Beast Master",
            display_name="Beast Master",
            parent_class="Ranger",
            axis_weights={'nature_attunement': 0.3,
 'social_leadership': 0.18,
 'mercy_restoration': 0.18,
 'frontline_courage': 0.16,
 'stealth_indirection': 0.18},
            synergy_groups=(('nature_attunement', 'social_leadership'), ('nature_attunement', 'mercy_restoration')),
            anti_axes={'performance': 0.04},
            notes="Bonded animal partnership and field care.",
        ),
        "Drakewarden": SubclassDefinition(
            key="Drakewarden",
            display_name="Drakewarden",
            parent_class="Ranger",
            axis_weights={'nature_attunement': 0.24,
 'frontline_courage': 0.22,
 'innate_power': 0.2,
 'social_leadership': 0.18,
 'risk_appetite': 0.16},
            synergy_groups=(('nature_attunement', 'innate_power'), ('frontline_courage', 'social_leadership')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Scaled companion energy with elevated mythic charge.",
        ),
        "Fey Wanderer": SubclassDefinition(
            key="Fey Wanderer",
            display_name="Fey Wanderer",
            parent_class="Ranger",
            axis_weights={'nature_attunement': 0.24,
 'performance': 0.18,
 'social_leadership': 0.18,
 'stealth_indirection': 0.2,
 'innate_power': 0.2},
            synergy_groups=(('nature_attunement', 'performance'), ('nature_attunement', 'stealth_indirection')),
            anti_axes={'discipline': 0.04},
            notes="The unsettlingly charming ranger lane.",
        ),
        "Gloom Stalker": SubclassDefinition(
            key="Gloom Stalker",
            display_name="Gloom Stalker",
            parent_class="Ranger",
            axis_weights={'stealth_indirection': 0.3,
 'frontline_courage': 0.18,
 'control_planning': 0.22,
 'nature_attunement': 0.18,
 'risk_appetite': 0.12},
            synergy_groups=(('stealth_indirection', 'control_planning'), ('nature_attunement', 'stealth_indirection')),
            anti_axes={'social_leadership': 0.04},
            notes="Dark-zone ambush competence.",
        ),
        "Horizon Walker": SubclassDefinition(
            key="Horizon Walker",
            display_name="Horizon Walker",
            parent_class="Ranger",
            axis_weights={'nature_attunement': 0.22,
 'risk_appetite': 0.2,
 'innate_power': 0.2,
 'control_planning': 0.2,
 'frontline_courage': 0.18},
            synergy_groups=(('innate_power', 'control_planning'), ('nature_attunement', 'risk_appetite')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Boundary-crossing, planar, and mobile.",
        ),
        "Hunter": SubclassDefinition(
            key="Hunter",
            display_name="Hunter",
            parent_class="Ranger",
            axis_weights={'frontline_courage': 0.24,
 'discipline': 0.22,
 'control_planning': 0.2,
 'nature_attunement': 0.18,
 'stealth_indirection': 0.16},
            synergy_groups=(('discipline', 'frontline_courage'), ('control_planning', 'nature_attunement')),
            anti_axes={'performance': 0.04},
            notes="The plain but effective predator-professional lane.",
        ),
        "Swarmkeeper": SubclassDefinition(
            key="Swarmkeeper",
            display_name="Swarmkeeper",
            parent_class="Ranger",
            axis_weights={'nature_attunement': 0.26,
 'control_planning': 0.2,
 'stealth_indirection': 0.18,
 'innate_power': 0.18,
 'mercy_restoration': 0.18},
            synergy_groups=(('nature_attunement', 'control_planning'), ('nature_attunement', 'innate_power')),
            anti_axes={'social_leadership': 0.04},
            notes="Distributed agency, many small motions, and ecological weirdness.",
        ),
    },
    "Rogue": {
        "Arcane Trickster": SubclassDefinition(
            key="Arcane Trickster",
            display_name="Arcane Trickster",
            parent_class="Rogue",
            axis_weights={'stealth_indirection': 0.28,
 'study': 0.22,
 'control_planning': 0.2,
 'technical_inventiveness': 0.16,
 'performance': 0.14},
            synergy_groups=(('stealth_indirection', 'study'), ('study', 'control_planning')),
            anti_axes={'faith': 0.04},
            notes="Cleverness, magic, and low-visibility mischief.",
        ),
        "Phantom": SubclassDefinition(
            key="Phantom",
            display_name="Phantom",
            parent_class="Rogue",
            axis_weights={'stealth_indirection': 0.26, 'patron_reliance': 0.22, 'control_planning': 0.2, 'risk_appetite': 0.14, 'study': 0.18},
            synergy_groups=(('stealth_indirection', 'patron_reliance'), ('stealth_indirection', 'control_planning')),
            anti_axes={'mercy_restoration': 0.06},
            notes="Death-haunted infiltration and borrowed echoes.",
        ),
        "Soulknife": SubclassDefinition(
            key="Soulknife",
            display_name="Soulknife",
            parent_class="Rogue",
            axis_weights={'stealth_indirection': 0.28, 'innate_power': 0.22, 'control_planning': 0.2, 'study': 0.14, 'risk_appetite': 0.16},
            synergy_groups=(('stealth_indirection', 'innate_power'), ('control_planning', 'innate_power')),
            anti_axes={'faith': 0.04},
            notes="Internalized weaponry and psychic precision.",
        ),
        "Swashbuckler": SubclassDefinition(
            key="Swashbuckler",
            display_name="Swashbuckler",
            parent_class="Rogue",
            axis_weights={'stealth_indirection': 0.22,
 'performance': 0.22,
 'frontline_courage': 0.22,
 'social_leadership': 0.2,
 'risk_appetite': 0.14},
            synergy_groups=(('performance', 'frontline_courage'), ('social_leadership', 'stealth_indirection')),
            anti_axes={'control_planning': 0.04},
            notes="Charm plus knife timing, in that order if possible.",
        ),
        "Thief": SubclassDefinition(
            key="Thief",
            display_name="Thief",
            parent_class="Rogue",
            axis_weights={'stealth_indirection': 0.3,
 'study': 0.2,
 'technical_inventiveness': 0.18,
 'risk_appetite': 0.18,
 'control_planning': 0.14},
            synergy_groups=(('stealth_indirection', 'technical_inventiveness'), ('stealth_indirection', 'risk_appetite')),
            anti_axes={'faith': 0.04},
            notes="Utility, access, and practical criminal competence.",
        ),
    },
    "Sorcerer": {
        "Aberrant Mind": SubclassDefinition(
            key="Aberrant Mind",
            display_name="Aberrant Mind",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.26, 'patron_reliance': 0.2, 'control_planning': 0.2, 'study': 0.14, 'stealth_indirection': 0.2},
            synergy_groups=(('innate_power', 'patron_reliance'), ('innate_power', 'control_planning')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Alien interiority with an unexpectedly strategic brain.",
        ),
        "Clockwork Soul": SubclassDefinition(
            key="Clockwork Soul",
            display_name="Clockwork Soul",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.22, 'control_planning': 0.28, 'discipline': 0.22, 'study': 0.16, 'mercy_restoration': 0.12},
            synergy_groups=(('innate_power', 'control_planning'), ('discipline', 'control_planning')),
            anti_axes={'risk_appetite': 0.08},
            notes="Built-in magic that prefers order to improvisation.",
        ),
        "Divine Soul": SubclassDefinition(
            key="Divine Soul",
            display_name="Divine Soul",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.24, 'faith': 0.24, 'mercy_restoration': 0.2, 'social_leadership': 0.16, 'frontline_courage': 0.16},
            synergy_groups=(('innate_power', 'faith'), ('faith', 'mercy_restoration')),
            anti_axes={'patron_reliance': 0.04},
            notes="Native radiance with sacred overtones.",
        ),
        "Draconic Bloodline": SubclassDefinition(
            key="Draconic Bloodline",
            display_name="Draconic Bloodline",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.3,
 'frontline_courage': 0.2,
 'social_leadership': 0.18,
 'risk_appetite': 0.16,
 'control_planning': 0.16},
            synergy_groups=(('innate_power', 'frontline_courage'), ('innate_power', 'social_leadership')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Inherited force, pride, and durable magical posture.",
        ),
        "Shadow Magic": SubclassDefinition(
            key="Shadow Magic",
            display_name="Shadow Magic",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.24,
 'stealth_indirection': 0.24,
 'patron_reliance': 0.18,
 'control_planning': 0.18,
 'risk_appetite': 0.16},
            synergy_groups=(('innate_power', 'stealth_indirection'), ('stealth_indirection', 'control_planning')),
            anti_axes={'social_leadership': 0.04},
            notes="Native power tuned to dark edges and concealment.",
        ),
        "Wild Magic": SubclassDefinition(
            key="Wild Magic",
            display_name="Wild Magic",
            parent_class="Sorcerer",
            axis_weights={'innate_power': 0.28, 'risk_appetite': 0.3, 'performance': 0.16, 'social_leadership': 0.14, 'frontline_courage': 0.12},
            synergy_groups=(('innate_power', 'risk_appetite'), ('performance', 'risk_appetite')),
            anti_axes={'control_planning': 0.1},
            notes="Internal voltage with dubious quality control.",
        ),
    },
    "Warlock": {
        "Archfey": SubclassDefinition(
            key="Archfey",
            display_name="Archfey",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.28,
 'performance': 0.18,
 'stealth_indirection': 0.22,
 'social_leadership': 0.16,
 'innate_power': 0.16},
            synergy_groups=(('patron_reliance', 'performance'), ('patron_reliance', 'stealth_indirection')),
            anti_axes={'discipline': 0.04},
            notes="Charm, glamour, and weaponized whim.",
        ),
        "Celestial": SubclassDefinition(
            key="Celestial",
            display_name="Celestial",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.24, 'faith': 0.22, 'mercy_restoration': 0.22, 'social_leadership': 0.18, 'innate_power': 0.14},
            synergy_groups=(('patron_reliance', 'faith'), ('faith', 'mercy_restoration')),
            anti_axes={'stealth_indirection': 0.04},
            notes="Borrowed grace without actually becoming a Cleric.",
        ),
        "Fathomless": SubclassDefinition(
            key="Fathomless",
            display_name="Fathomless",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.28,
 'nature_attunement': 0.18,
 'control_planning': 0.2,
 'stealth_indirection': 0.16,
 'innate_power': 0.18},
            synergy_groups=(('patron_reliance', 'nature_attunement'), ('patron_reliance', 'control_planning')),
            anti_axes={'social_leadership': 0.04},
            notes="Deep-water contract energy and pressure dynamics.",
        ),
        "Fiend": SubclassDefinition(
            key="Fiend",
            display_name="Fiend",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.28,
 'frontline_courage': 0.18,
 'risk_appetite': 0.22,
 'innate_power': 0.18,
 'social_leadership': 0.14},
            synergy_groups=(('patron_reliance', 'risk_appetite'), ('patron_reliance', 'frontline_courage')),
            anti_axes={'mercy_restoration': 0.1},
            notes="Power through appetitive infernal escalation.",
        ),
        "Genie": SubclassDefinition(
            key="Genie",
            display_name="Genie",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.24, 'performance': 0.18, 'innate_power': 0.2, 'risk_appetite': 0.18, 'social_leadership': 0.2},
            synergy_groups=(('patron_reliance', 'innate_power'), ('performance', 'social_leadership')),
            anti_axes={'discipline': 0.04},
            notes="Patronage with elegance, vanity, and elemental flourish.",
        ),
        "Great Old One": SubclassDefinition(
            key="Great Old One",
            display_name="Great Old One",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.3, 'control_planning': 0.22, 'study': 0.16, 'stealth_indirection': 0.18, 'innate_power': 0.14},
            synergy_groups=(('patron_reliance', 'control_planning'), ('study', 'patron_reliance')),
            anti_axes={'social_leadership': 0.04},
            notes="Asymmetric insight from something deeply inconvenient.",
        ),
        "Hexblade": SubclassDefinition(
            key="Hexblade",
            display_name="Hexblade",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.26,
 'frontline_courage': 0.22,
 'discipline': 0.18,
 'control_planning': 0.18,
 'stealth_indirection': 0.16},
            synergy_groups=(('patron_reliance', 'frontline_courage'), ('discipline', 'control_planning')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Weapon-bonded pact aggression with cleaner lines than Fiend.",
        ),
        "Undead": SubclassDefinition(
            key="Undead",
            display_name="Undead",
            parent_class="Warlock",
            axis_weights={'patron_reliance': 0.28,
 'stealth_indirection': 0.2,
 'control_planning': 0.18,
 'frontline_courage': 0.16,
 'social_leadership': 0.18},
            synergy_groups=(('patron_reliance', 'stealth_indirection'), ('patron_reliance', 'social_leadership')),
            anti_axes={'mercy_restoration': 0.08},
            notes="Fear, endurance, and refusal to behave like a finite creature.",
        ),
    },
    "Wizard": {
        "Abjuration": SubclassDefinition(
            key="Abjuration",
            display_name="Abjuration",
            parent_class="Wizard",
            axis_weights={'study': 0.28, 'control_planning': 0.26, 'discipline': 0.2, 'mercy_restoration': 0.14, 'frontline_courage': 0.12},
            synergy_groups=(('study', 'control_planning'), ('discipline', 'control_planning')),
            anti_axes={'risk_appetite': 0.06},
            notes="Protection through formalized magical architecture.",
        ),
        "Bladesinger": SubclassDefinition(
            key="Bladesinger",
            display_name="Bladesinger",
            parent_class="Wizard",
            axis_weights={'study': 0.22, 'discipline': 0.22, 'frontline_courage': 0.2, 'performance': 0.18, 'control_planning': 0.18},
            synergy_groups=(('study', 'discipline'), ('frontline_courage', 'performance')),
            anti_axes={'mercy_restoration': 0.04},
            notes="Fastidious wizardry that insisted on footwork.",
        ),
        "Conjuration": SubclassDefinition(
            key="Conjuration",
            display_name="Conjuration",
            parent_class="Wizard",
            axis_weights={'study': 0.28, 'control_planning': 0.24, 'risk_appetite': 0.18, 'technical_inventiveness': 0.14, 'innate_power': 0.16},
            synergy_groups=(('study', 'control_planning'), ('study', 'risk_appetite')),
            anti_axes={'frontline_courage': 0.04},
            notes="Spatial logistics, summoned assets, and flexible provisioning.",
        ),
        "Divination": SubclassDefinition(
            key="Divination",
            display_name="Divination",
            parent_class="Wizard",
            axis_weights={'study': 0.26, 'control_planning': 0.28, 'faith': 0.16, 'stealth_indirection': 0.14, 'innate_power': 0.16},
            synergy_groups=(('study', 'control_planning'), ('faith', 'control_planning')),
            anti_axes={'frontline_courage': 0.04},
            notes="Prediction, foresight, and a rude amount of informational leverage.",
        ),
        "Enchantment": SubclassDefinition(
            key="Enchantment",
            display_name="Enchantment",
            parent_class="Wizard",
            axis_weights={'study': 0.24, 'performance': 0.22, 'social_leadership': 0.2, 'control_planning': 0.18, 'stealth_indirection': 0.16},
            synergy_groups=(('study', 'performance'), ('performance', 'social_leadership')),
            anti_axes={'frontline_courage': 0.04},
            notes="Wizardry that edits motives rather than walls.",
        ),
        "Evocation": SubclassDefinition(
            key="Evocation",
            display_name="Evocation",
            parent_class="Wizard",
            axis_weights={'study': 0.24, 'frontline_courage': 0.2, 'risk_appetite': 0.2, 'innate_power': 0.18, 'control_planning': 0.18},
            synergy_groups=(('study', 'risk_appetite'), ('frontline_courage', 'innate_power')),
            anti_axes={'mercy_restoration': 0.06},
            notes="Direct magical force without the Bard's need to be liked.",
        ),
        "Illusion": SubclassDefinition(
            key="Illusion",
            display_name="Illusion",
            parent_class="Wizard",
            axis_weights={'study': 0.24, 'stealth_indirection': 0.28, 'performance': 0.18, 'control_planning': 0.18, 'innate_power': 0.12},
            synergy_groups=(('study', 'stealth_indirection'), ('performance', 'stealth_indirection')),
            anti_axes={'frontline_courage': 0.06},
            notes="Perception editing and elegant dishonesty.",
        ),
        "Necromancy": SubclassDefinition(
            key="Necromancy",
            display_name="Necromancy",
            parent_class="Wizard",
            axis_weights={'study': 0.24,
 'patron_reliance': 0.22,
 'control_planning': 0.22,
 'frontline_courage': 0.14,
 'stealth_indirection': 0.18},
            synergy_groups=(('study', 'control_planning'), ('study', 'patron_reliance')),
            anti_axes={'mercy_restoration': 0.1},
            notes="Administrative control over death and labor.",
        ),
        "Order of Scribes": SubclassDefinition(
            key="Order of Scribes",
            display_name="Order of Scribes",
            parent_class="Wizard",
            axis_weights={'study': 0.32, 'control_planning': 0.24, 'technical_inventiveness': 0.18, 'discipline': 0.16, 'innate_power': 0.1},
            synergy_groups=(('study', 'control_planning'), ('study', 'technical_inventiveness')),
            anti_axes={'frontline_courage': 0.04},
            notes="Wizardry as textual systems engineering.",
        ),
        "Transmutation": SubclassDefinition(
            key="Transmutation",
            display_name="Transmutation",
            parent_class="Wizard",
            axis_weights={'study': 0.26, 'technical_inventiveness': 0.22, 'control_planning': 0.2, 'risk_appetite': 0.16, 'innate_power': 0.16},
            synergy_groups=(('study', 'technical_inventiveness'), ('study', 'risk_appetite')),
            anti_axes={'social_leadership': 0.04},
            notes="Material change, adaptive method, and practical mutation.",
        ),
    },
}


SUBCLASS_ORDER_BY_CLASS: Dict[str, Tuple[str, ...]] = {
    class_key: tuple(subclasses.keys())
    for class_key, subclasses in DND_SUBCLASSES.items()
}


class DnDSubclassScorer:
    """Scores subclasses inside a selected base class."""

    def score_subclasses(
        self,
        axis_scores: Mapping[str, float],
        parent_class: str,
        class_scores: Optional[Mapping[str, float]] = None,
    ) -> Dict[str, ScoredSubclass]:
        validate_axis_scores(axis_scores)
        if parent_class not in DND_SUBCLASSES:
            raise KeyError(f"Unknown class for subclass scoring: {parent_class}")

        if class_scores is None:
            class_scores = score_dnd_classes(axis_scores)
        parent_class_score = float(class_scores.get(parent_class, 0.0))

        out: Dict[str, ScoredSubclass] = {}
        for subclass_key, definition in DND_SUBCLASSES[parent_class].items():
            direct_score = _weighted_average(axis_scores, definition.axis_weights)
            synergy_score = self._subclass_synergy_score(definition, axis_scores)
            penalty_score = _weighted_penalty(axis_scores, definition.anti_axes)
            final_score = self._compose_subclass_score(
                direct_score=direct_score,
                class_score=parent_class_score,
                synergy_score=synergy_score,
                penalty_score=penalty_score,
            )
            out[subclass_key] = ScoredSubclass(
                key=subclass_key,
                parent_class=parent_class,
                score=final_score,
                direct_score=direct_score,
                class_score=parent_class_score,
                synergy_score=synergy_score,
                penalty_score=penalty_score,
            )
        return out

    def assign_from_axis_scores(
        self,
        axis_scores: Mapping[str, float],
        parent_class: Optional[str] = None,
        class_scores: Optional[Mapping[str, float]] = None,
    ) -> SubclassAssignment:
        validate_axis_scores(axis_scores)
        if class_scores is None:
            class_scores = score_dnd_classes(axis_scores)

        chosen_class = parent_class
        if chosen_class is None:
            class_assignment = DnDClassScorer().assign_from_axis_scores(axis_scores)
            chosen_class = class_assignment.primary_class

        subclass_detail = self.score_subclasses(
            axis_scores=axis_scores,
            parent_class=chosen_class,
            class_scores=class_scores,
        )
        ranked = sorted(subclass_detail.values(), key=lambda item: item.score, reverse=True)
        primary = ranked[0]
        secondary = ranked[1] if len(ranked) > 1 else None

        return SubclassAssignment(
            parent_class=chosen_class,
            primary_subclass=primary.key,
            primary_score=primary.score,
            secondary_subclass=secondary.key if secondary else None,
            secondary_score=secondary.score if secondary else 0.0,
            confidence_gap=max(0.0, primary.score - (secondary.score if secondary else 0.0)),
            subclass_scores={key: value.score for key, value in subclass_detail.items()},
        )

    def assign_from_chart(
        self,
        chart: Any,
        parent_class: Optional[str] = None,
    ) -> SubclassAssignment:
        axis_scores = score_class_axes(chart)
        return self.assign_from_axis_scores(axis_scores, parent_class=parent_class)

    @staticmethod
    def _subclass_synergy_score(
        definition: SubclassDefinition,
        axis_scores: Mapping[str, float],
    ) -> float:
        if not definition.synergy_groups:
            return 0.0
        group_scores = [_synergy_average(axis_scores, group) for group in definition.synergy_groups]
        return _clamp01(sum(group_scores) / len(group_scores))

    @staticmethod
    def _compose_subclass_score(
        *,
        direct_score: float,
        class_score: float,
        synergy_score: float,
        penalty_score: float,
    ) -> float:
        raw = (
            0.50 * direct_score
            + 0.32 * class_score
            + 0.18 * synergy_score
            - 0.10 * penalty_score
        )
        return _clamp01(raw)


def score_dnd_subclasses(
    axis_scores: Mapping[str, float],
    parent_class: str,
    class_scores: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    detail = DnDSubclassScorer().score_subclasses(axis_scores, parent_class, class_scores)
    return {key: scored.score for key, scored in detail.items()}


def assign_dnd_subclass(
    chart_or_axis_scores: Any,
    parent_class: Optional[str] = None,
) -> SubclassAssignment:
    scorer = DnDSubclassScorer()
    if isinstance(chart_or_axis_scores, Mapping) and all(
        key in chart_or_axis_scores for key in AXIS_ORDER
    ):
        return scorer.assign_from_axis_scores(chart_or_axis_scores, parent_class=parent_class)
    return scorer.assign_from_chart(chart_or_axis_scores, parent_class=parent_class)


def assign_dnd_build(chart_or_axis_scores: Any) -> DnDBuildAssignment:
    class_assignment = assign_dnd_class(chart_or_axis_scores)
    subclass_assignment = assign_dnd_subclass(
        chart_or_axis_scores,
        parent_class=class_assignment.primary_class,
    )
    return DnDBuildAssignment(
        class_assignment=class_assignment,
        subclass_assignment=subclass_assignment,
    )


def subclass_display_table(parent_class: Optional[str] = None) -> str:
    lines: List[str] = []
    class_keys: Sequence[str]
    if parent_class is None:
        class_keys = CLASS_ORDER
    else:
        if parent_class not in DND_SUBCLASSES:
            raise KeyError(f"Unknown class for subclass display: {parent_class}")
        class_keys = (parent_class,)

    for class_key in class_keys:
        subclasses = DND_SUBCLASSES.get(class_key, {})
        if not subclasses:
            continue
        lines.append(f"{class_key} subclasses")
        for subclass_key in SUBCLASS_ORDER_BY_CLASS.get(class_key, ()):
            subclass = subclasses[subclass_key]
            axis = ", ".join(f"{name}={weight:.2f}" for name, weight in subclass.axis_weights.items())
            lines.append(f"  {subclass.display_name} ({subclass.key})")
            lines.append(f"    Axes: {axis}")
            if subclass.synergy_groups:
                lines.append(
                    "    Synergy: "
                    + ", ".join(" + ".join(group) for group in subclass.synergy_groups)
                )
            if subclass.anti_axes:
                lines.append(
                    "    Anti: "
                    + ", ".join(
                        f"{name}={weight:.2f}" for name, weight in subclass.anti_axes.items()
                    )
                )
            if subclass.notes:
                lines.append(f"    Notes: {subclass.notes}")
        lines.append("")
    return "\n".join(lines).rstrip()



def extract_class_axis_features(chart: Any) -> AxisFeatureSet:
    return ClassAxisScorer().extract_features(chart)


def score_class_axes(chart: Any) -> Dict[str, float]:
    return ClassAxisScorer().score_chart(chart)


def score_class_families(axis_scores: Mapping[str, float]) -> Dict[str, float]:
    return DnDClassScorer().score_families(axis_scores)


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
    print()
    print(subclass_display_table())
