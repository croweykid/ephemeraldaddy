from __future__ import annotations

import pytest

from ephemeraldaddy.gui.features.transits.intensity import (
    TransitAspectInput,
    calculate_transit_intensities,
)


def _aspect(source: str, target: str, *, aspect: str = "conjunction", orb: float = 0.0) -> TransitAspectInput:
    return TransitAspectInput(
        source=source,
        aspect=aspect,
        target=target,
        orb=orb,
        orb_cap=8.0,
    )


def test_isolated_exact_major_aspect_has_no_cluster_bonus() -> None:
    result = calculate_transit_intensities(
        [_aspect("Saturn", "Sun")],
        {"Saturn": 100.0, "Sun": 100.0},
    )
    score = result.score_for("Saturn", "conjunction", "Sun")

    assert score is not None
    assert score.base_potential == pytest.approx(1.0)
    assert score.source_reinforcement == pytest.approx(0.0)
    assert score.target_reinforcement == pytest.approx(0.0)
    assert score.intensity == pytest.approx(score.base_potential)
    assert score.display_score == pytest.approx(100.0)


def test_duplicate_physical_aspect_does_not_inflate_convergence() -> None:
    result = calculate_transit_intensities(
        [
            _aspect("Saturn", "Sun"),
            _aspect("Saturn", "Sun"),
        ],
        {"Saturn": 100.0, "Sun": 100.0},
    )

    saturn = result.body_activations["Saturn"]
    score = result.score_for("Saturn", "conjunction", "Sun")
    assert score is not None
    assert saturn.source_count == 1
    assert saturn.source_reinforcement == pytest.approx(0.0)
    assert score.source_reinforcement == pytest.approx(0.0)


def test_multiple_saturn_contacts_can_overcome_below_average_natal_prominence() -> None:
    weights = {
        "Saturn": 170.0,
        "Sun": 200.0,
        "Moon": 200.0,
        "Mercury": 200.0,
        "Venus": 200.0,
        "Mars": 200.0,
        "Jupiter": 200.0,
    }
    aspects = [
        _aspect("Saturn", "Sun"),
        _aspect("Saturn", "Moon"),
        _aspect("Saturn", "Mercury"),
        _aspect("Saturn", "Venus"),
        _aspect("Saturn", "Mars"),
    ]

    result = calculate_transit_intensities(aspects, weights)
    saturn = result.body_activations["Saturn"]
    representative = result.score_for("Saturn", "conjunction", "Sun")

    assert representative is not None
    assert saturn.baseline_dominance < 1.0
    assert saturn.source_count == 5
    assert saturn.current_activation > 1.0
    assert representative.source_reinforcement > 0.0
    assert representative.intensity > representative.base_potential


def test_convergence_bonus_has_diminishing_returns() -> None:
    weights = {
        "Saturn": 100.0,
        "Sun": 100.0,
        "Moon": 100.0,
        "Mercury": 100.0,
        "Venus": 100.0,
        "Mars": 100.0,
        "Jupiter": 100.0,
    }
    targets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter"]

    bonuses = []
    for count in (1, 2, 5, 6):
        result = calculate_transit_intensities(
            [_aspect("Saturn", target) for target in targets[:count]],
            weights,
        )
        bonuses.append(result.body_activations["Saturn"].source_reinforcement)

    one, two, five, six = bonuses
    assert one == pytest.approx(0.0)
    assert one < two < five < six
    assert (six - five) < (two - one)
    assert six < 0.75


def test_target_natal_prominence_matters_more_than_source_prominence() -> None:
    weights = {
        "Saturn": 100.0,
        "Sun": 400.0,
        "Moon": 100.0,
        "Venus": 100.0,
    }
    result = calculate_transit_intensities(
        [
            _aspect("Saturn", "Sun"),
            _aspect("Sun", "Saturn"),
        ],
        weights,
    )
    high_target = result.score_for("Saturn", "conjunction", "Sun")
    high_source = result.score_for("Sun", "conjunction", "Saturn")

    assert high_target is not None
    assert high_source is not None
    assert high_target.base_potential > high_source.base_potential


def test_minor_aspect_has_lower_base_strength_than_major_aspect() -> None:
    result = calculate_transit_intensities(
        [
            _aspect("Saturn", "Sun", aspect="square"),
            _aspect("Jupiter", "Moon", aspect="semisextile"),
        ],
        {
            "Saturn": 100.0,
            "Sun": 100.0,
            "Jupiter": 100.0,
            "Moon": 100.0,
        },
    )
    major = result.score_for("Saturn", "square", "Sun")
    minor = result.score_for("Jupiter", "semisextile", "Moon")

    assert major is not None
    assert minor is not None
    assert major.base_aspect_strength == pytest.approx(1.0)
    assert minor.base_aspect_strength == pytest.approx(2.0 / 9.0)
    assert major.base_potential > minor.base_potential
