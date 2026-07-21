"""Shared constants and helper values for Database View search controls."""

from __future__ import annotations

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import DND_CLASSES
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import FAMILY_SUBTYPES, SPECIES_FAMILIES
from ephemeraldaddy.analysis.human_design_reference import HD_CHANNELS
from ephemeraldaddy.core.aspects import ASPECT_DEFS
from ephemeraldaddy.core.interpretations import (
    GENDER_OPTIONS,
    GENERATIONAL_COHORTS,
    NAKSHATRA_RANGES,
    RELATION_TYPE,
    RODDEN_RATING,
    SENTIMENT_OPTIONS,
    ZODIAC_NAMES,
)
from ephemeraldaddy.gui.features.charts.provenance import SOURCE_OPTIONS

GENERATION_UNKNOWN_OPTION = "unknown"
GENERATION_FILTER_OPTIONS: tuple[str, ...] = tuple(
    [
        cohort["name"]
        for cohort in GENERATIONAL_COHORTS
        if isinstance(cohort.get("name"), str)
    ]
    + [GENERATION_UNKNOWN_OPTION]
)

SEARCH_SENTIMENT_OPTIONS = ["none", *SENTIMENT_OPTIONS]
SEARCH_RELATIONSHIP_TYPE_OPTIONS = ["none", *RELATION_TYPE]
SEARCH_GENDER_OPTIONS = ["none", *GENDER_OPTIONS]
SEARCH_GENDER_GUESSED_OPTIONS = [
    ("Any", ""),
    ("Masculine", "masculine"),
    ("Androgynous", "androgynous"),
    ("Feminine", "feminine"),
]
