from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

from ephemeraldaddy.gui.features.charts.dominance_relevance import (
    ChartBodyRelevance,
    calculate_chart_body_relevance,
)
from ephemeraldaddy.gui.features.transits.personal_timeline_filters import (
    ASPECT_FAMILY_MAJOR,
    ASPECT_FAMILY_MINOR,
    BODY_FAMILY_ASTEROIDS,
    BODY_FAMILY_OUTER,
    CYCLE_SCOPE_COHORT,
    CYCLE_SCOPE_INDIVIDUALIZED,
    PRESET_COHORT,
    PRESET_MAJOR_ASPECTS,
    PRESET_RELEVANT,
    aspect_family_for,
    body_family_for,
    filter_timeline_windows,
    metadata_for_window,
    preset_filter_state,
)


@dataclass
class _Transit:
    transiting_body: str
    natal_body: str
    aspect_name: str
    aspect_angle: float


@dataclass
class _Window:
    transit: _Transit


def _relevance(*above_median: str) -> ChartBodyRelevance:
    return ChartBodyRelevance(
        weights={body: 10.0 for body in above_median},
        median_weight=5.0,
        above_median_bodies=frozenset(above_median),
    )


def test_chart_body_relevance_reuses_existing_dominance_weights() -> None:
    with patch(
        "ephemeraldaddy.gui.features.charts.dominance_relevance.calculate_dominant_planet_weights",
        return_value={"Sun": 10.0, "Moon": 5.0, "Pluto": 20.0, "Vesta": 1.0},
    ):
        relevance = calculate_chart_body_relevance(object())

    assert relevance.median_weight == 7.5
    assert relevance.above_median_bodies == frozenset({"Sun", "Pluto"})
    assert relevance.is_above_median("Pluto")
    assert not relevance.is_above_median("Vesta")


def test_outer_to_outer_is_labeled_cohort_but_can_still_be_relevant() -> None:
    window = _Window(_Transit("Pluto", "Neptune", "square", 90.0))
    metadata = metadata_for_window(window, _relevance("Pluto"))

    assert metadata.body_family == BODY_FAMILY_OUTER
    assert metadata.aspect_family == ASPECT_FAMILY_MAJOR
    assert metadata.cycle_scope == CYCLE_SCOPE_COHORT
    assert metadata.unusually_relevant
    assert metadata.relevant_bodies == ("Pluto",)
    assert metadata.relevance_prefix == "🌟 "


def test_asteroid_and_minor_aspect_remain_descriptive_candidates() -> None:
    window = _Window(_Transit("Vesta", "Moon", "quincunx", 150.0))
    metadata = metadata_for_window(window)

    assert body_family_for("Vesta") == BODY_FAMILY_ASTEROIDS
    assert aspect_family_for(150.0) == ASPECT_FAMILY_MINOR
    assert metadata.cycle_scope == CYCLE_SCOPE_INDIVIDUALIZED


def test_major_preset_filters_only_by_aspect_family() -> None:
    major = _Window(_Transit("Saturn", "Sun", "square", 90.0))
    minor = _Window(_Transit("Vesta", "Moon", "quincunx", 150.0))

    filtered = filter_timeline_windows(
        [major, minor],
        preset_filter_state(PRESET_MAJOR_ASPECTS),
    )

    assert filtered == [major]


def test_cohort_preset_keeps_generational_cycles_instead_of_discarding_them() -> None:
    cohort = _Window(_Transit("Uranus", "Pluto", "trine", 120.0))
    individual = _Window(_Transit("Uranus", "Moon", "trine", 120.0))

    filtered = filter_timeline_windows(
        [cohort, individual],
        preset_filter_state(PRESET_COHORT),
    )

    assert filtered == [cohort]


def test_relevant_preset_can_select_chart_specific_candidates() -> None:
    starred = _Window(_Transit("Pluto", "Moon", "square", 90.0))
    ordinary = _Window(_Transit("Saturn", "Venus", "square", 90.0))

    filtered = filter_timeline_windows(
        [starred, ordinary],
        preset_filter_state(PRESET_RELEVANT),
        _relevance("Pluto"),
    )

    assert filtered == [starred]
