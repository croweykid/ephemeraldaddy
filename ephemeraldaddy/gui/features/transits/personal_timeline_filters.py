"""Classification and filter state for exploratory Personal Timeline research.

The generator should retain a broad candidate set.  This module describes those
candidates independently from the view so filters can be tightened repeatedly
without re-running ephemerides or throwing away the full dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from ephemeraldaddy.core.interpretations import (
    ASTEROIDS,
    BLACK_MOON_LILITH,
    MAJOR_ASPECTS,
    NODES,
    OUTER_PLANETS,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.dominance_relevance import ChartBodyRelevance


BODY_FAMILY_OUTER = "Outer planets"
BODY_FAMILY_SOCIAL = "Jupiter / Saturn"
BODY_FAMILY_CHIRON = "Chiron"
BODY_FAMILY_NODES = "Nodes"
BODY_FAMILY_ASTEROIDS = "Asteroids"
BODY_FAMILY_LILITH = "Lilith"
BODY_FAMILY_OTHER = "Other"

BODY_FAMILY_ORDER = (
    BODY_FAMILY_OUTER,
    BODY_FAMILY_SOCIAL,
    BODY_FAMILY_CHIRON,
    BODY_FAMILY_NODES,
    BODY_FAMILY_ASTEROIDS,
    BODY_FAMILY_LILITH,
    BODY_FAMILY_OTHER,
)
ALL_BODY_FAMILIES = frozenset(BODY_FAMILY_ORDER)

ASPECT_FAMILY_MAJOR = "Major aspects"
ASPECT_FAMILY_MINOR = "Minor aspects"
ALL_ASPECT_FAMILIES = frozenset({ASPECT_FAMILY_MAJOR, ASPECT_FAMILY_MINOR})

CYCLE_SCOPE_INDIVIDUALIZED = "individualized"
CYCLE_SCOPE_COHORT = "cohort/generational cycle"

PRESET_ALL = "all"
PRESET_MAJOR_ASPECTS = "major_aspects"
PRESET_MINOR_ASPECTS = "minor_aspects"
PRESET_INDIVIDUALIZED = "individualized"
PRESET_COHORT = "cohort"
PRESET_ASTEROIDS_LILITH = "asteroids_lilith"
PRESET_RELEVANT = "relevant"

FILTER_PRESETS: tuple[tuple[str, str], ...] = (
    ("All candidates", PRESET_ALL),
    ("Major aspects only", PRESET_MAJOR_ASPECTS),
    ("Minor aspects only", PRESET_MINOR_ASPECTS),
    ("Individualized only", PRESET_INDIVIDUALIZED),
    ("Cohort/generational cycles only", PRESET_COHORT),
    ("Asteroids + Lilith", PRESET_ASTEROIDS_LILITH),
    ("🌟 Above-median chart relevance", PRESET_RELEVANT),
)


@dataclass(frozen=True, slots=True)
class TransitWindowMetadata:
    transiting_body: str
    natal_body: str
    aspect_name: str
    aspect_family: str
    body_family: str
    cycle_scope: str
    relevant_bodies: tuple[str, ...] = ()

    @property
    def unusually_relevant(self) -> bool:
        return bool(self.relevant_bodies)

    @property
    def relevance_prefix(self) -> str:
        return "🌟 " if self.unusually_relevant else ""


@dataclass(frozen=True, slots=True)
class PersonalTimelineFilterState:
    """All filter dimensions applied to an already-generated candidate set."""

    body_families: frozenset[str] = ALL_BODY_FAMILIES
    aspect_families: frozenset[str] = ALL_ASPECT_FAMILIES
    aspect_names: frozenset[str] | None = None
    transiting_bodies: frozenset[str] | None = None
    natal_bodies: frozenset[str] | None = None
    include_cohort_cycles: bool = True
    cohort_only: bool = False
    relevant_only: bool = False

    def matches(self, metadata: TransitWindowMetadata) -> bool:
        if metadata.body_family not in self.body_families:
            return False
        if metadata.aspect_family not in self.aspect_families:
            return False
        if self.aspect_names is not None and metadata.aspect_name not in self.aspect_names:
            return False
        if (
            self.transiting_bodies is not None
            and metadata.transiting_body not in self.transiting_bodies
        ):
            return False
        if self.natal_bodies is not None and metadata.natal_body not in self.natal_bodies:
            return False
        if not self.include_cohort_cycles and metadata.cycle_scope == CYCLE_SCOPE_COHORT:
            return False
        if self.cohort_only and metadata.cycle_scope != CYCLE_SCOPE_COHORT:
            return False
        if self.relevant_only and not metadata.unusually_relevant:
            return False
        return True


def body_family_for(body: str) -> str:
    normalized = normalize_body_name(str(body))
    if normalized in OUTER_PLANETS:
        return BODY_FAMILY_OUTER
    if normalized in {"Jupiter", "Saturn"}:
        return BODY_FAMILY_SOCIAL
    if normalized == "Chiron":
        return BODY_FAMILY_CHIRON
    if normalized in NODES:
        return BODY_FAMILY_NODES
    if normalized in ASTEROIDS:
        return BODY_FAMILY_ASTEROIDS
    if normalized in BLACK_MOON_LILITH:
        return BODY_FAMILY_LILITH
    return BODY_FAMILY_OTHER


def aspect_family_for(angle_degrees: float) -> str:
    angle = int(round(float(angle_degrees)))
    return ASPECT_FAMILY_MAJOR if angle in MAJOR_ASPECTS else ASPECT_FAMILY_MINOR


def cycle_scope_for(transiting_body: str, natal_body: str) -> str:
    """Label broad slow-planet cohort cycles without discarding them.

    Outer-to-outer contacts are the clearest generational case. The label is
    descriptive only: per-chart relevance can still mark such a contact with a
    star when either outer body is unusually dominant in this natal chart.
    """
    transiting = normalize_body_name(str(transiting_body))
    natal = normalize_body_name(str(natal_body))
    if transiting in OUTER_PLANETS and natal in OUTER_PLANETS:
        return CYCLE_SCOPE_COHORT
    return CYCLE_SCOPE_INDIVIDUALIZED


def metadata_for_window(
    window: Any,
    relevance: ChartBodyRelevance | None = None,
) -> TransitWindowMetadata:
    transit = window.transit
    transiting_body = normalize_body_name(str(transit.transiting_body))
    natal_body = normalize_body_name(str(transit.natal_body))
    relevant_bodies: list[str] = []
    if relevance is not None:
        for body in (transiting_body, natal_body):
            if relevance.is_above_median(body) and body not in relevant_bodies:
                relevant_bodies.append(body)
    return TransitWindowMetadata(
        transiting_body=transiting_body,
        natal_body=natal_body,
        aspect_name=str(transit.aspect_name),
        aspect_family=aspect_family_for(float(transit.aspect_angle)),
        body_family=body_family_for(transiting_body),
        cycle_scope=cycle_scope_for(transiting_body, natal_body),
        relevant_bodies=tuple(relevant_bodies),
    )


def preset_filter_state(preset: str) -> PersonalTimelineFilterState:
    state = PersonalTimelineFilterState()
    if preset == PRESET_ALL:
        return state
    if preset == PRESET_MAJOR_ASPECTS:
        return replace(state, aspect_families=frozenset({ASPECT_FAMILY_MAJOR}))
    if preset == PRESET_MINOR_ASPECTS:
        return replace(state, aspect_families=frozenset({ASPECT_FAMILY_MINOR}))
    if preset == PRESET_INDIVIDUALIZED:
        return replace(state, include_cohort_cycles=False)
    if preset == PRESET_COHORT:
        return replace(state, cohort_only=True)
    if preset == PRESET_ASTEROIDS_LILITH:
        return replace(
            state,
            body_families=frozenset({BODY_FAMILY_ASTEROIDS, BODY_FAMILY_LILITH}),
        )
    if preset == PRESET_RELEVANT:
        return replace(state, relevant_only=True)
    raise ValueError(f"Unknown Personal Timeline filter preset: {preset}")


def filter_timeline_windows(
    windows: Iterable[Any],
    state: PersonalTimelineFilterState,
    relevance: ChartBodyRelevance | None = None,
) -> list[Any]:
    return [
        window
        for window in windows
        if state.matches(metadata_for_window(window, relevance))
    ]
