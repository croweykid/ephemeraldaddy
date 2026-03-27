from __future__ import annotations

"""
Foundational axes for assigning D&D-style classes and subclasses from an
astrological chart or other symbolic profile.

This module does not score classes yet. It defines the semantic skeleton the
future classifier should use so that classes are assigned by method, role, and
power-source rather than by costume or surface vibe.
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


# ---------------------------------------------------------------------------
# Axis definitions
# ---------------------------------------------------------------------------
# Design rule: each axis should describe one durable behavioral dimension.
# Avoid making the same concept appear under several different names.

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
    """Return a zeroed-out axis score dictionary."""
    return {key: 0.0 for key in AXIS_ORDER}



def validate_axis_scores(scores: Mapping[str, float]) -> None:
    """Raise on missing or unknown axis keys."""
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
    """Return a subset of axis scores in deterministic order."""
    return {key: float(scores.get(key, 0.0)) for key in keys}



def axis_display_table() -> str:
    """Pretty-print axis definitions for debugging or design review."""
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

ASPECT_ALIAS_MAP: Dict[str, str] = {
    "conj": "conjunction",
    "opp": "opposition",
    "opposition": "opposition",
    "trine": "trine",
    "trin": "trine",
    "square": "square",
    "sq": "square",
    "sextile": "sextile",
    "sex": "sextile",
    "quincunx": "quincunx",
    "inconjunct": "quincunx",
}


@dataclass(frozen=True)
class AxisFeatureSet:
    """Stable chart features consumed by D&D class-axis scoring."""

    planet_prominence: Mapping[str, float]
    element_balance: Mapping[str, float]
    mode_balance: Mapping[str, float]
    house_emphasis: Mapping[str, float]
    aspect_signals: Mapping[str, float]


class ClassAxisScorer:
    """
    Feature extraction + provisional axis scoring.

    This class intentionally separates:
    1) chart normalization/extraction and
    2) axis weighting logic.

    Next iteration can tune weights without changing ingestion.
    """

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

        return {key: self._clamp01(value) for key, value in scores.items()}

    @staticmethod
    def _first_non_none(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _angular_distance(a: float, b: float) -> float:
        delta = abs((a - b) % 360.0)
        return min(delta, 360.0 - delta)

    def _normalize_aspect_name(self, name: str) -> str:
        lowered = str(name).strip().lower()
        return ASPECT_ALIAS_MAP.get(lowered, lowered)

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
            out[body] = self._clamp01(val)
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
                orb_decay = self._clamp01(1.0 - (float(orb) / orb_allowance))
            weight = base * orb_decay
            if aspect in {"square", "opposition", "semisquare", "sesquiquadrate"}:
                totals["tension"] += weight
            if aspect in {"trine", "sextile", "conjunction"}:
                totals["cohesion"] += weight
            if aspect in {"conjunction", "square", "opposition", "quincunx"}:
                totals["volatility"] += weight

        norm = max(1.0, totals["tension"] + totals["cohesion"] + totals["volatility"])
        return {key: value / norm for key, value in totals.items()}


def extract_class_axis_features(chart: Any) -> AxisFeatureSet:
    """Public convenience wrapper for chart -> feature extraction."""
    return ClassAxisScorer().extract_features(chart)


def score_class_axes(chart: Any) -> Dict[str, float]:
    """Public convenience wrapper for chart -> axis scores."""
    return ClassAxisScorer().score_chart(chart)


if __name__ == "__main__":
    print(axis_display_table())
