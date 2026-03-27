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
from typing import Dict, Iterable, List, Mapping, Tuple


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


if __name__ == "__main__":
    print(axis_display_table())
