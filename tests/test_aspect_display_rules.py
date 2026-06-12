from types import SimpleNamespace

from ephemeraldaddy.analysis.get_astro_twin import _aspect_map
from ephemeraldaddy.core.aspect_display import (
    STRUCTURAL_ASPECT_TAUTOLOGIES,
    aspect_is_displayable,
    display_aspect_key,
    is_structural_aspect_tautology,
)


def test_structural_tautologies_are_single_source_display_exclusions():
    assert STRUCTURAL_ASPECT_TAUTOLOGIES == {
        "opposition": frozenset(
            {
                frozenset({"AS", "DS"}),
                frozenset({"MC", "IC"}),
                frozenset({"Rahu", "Ketu"}),
            }
        ),
        "square": frozenset(
            {
                frozenset({"AS", "MC"}),
                frozenset({"AS", "IC"}),
                frozenset({"MC", "DS"}),
                frozenset({"DS", "IC"}),
            }
        ),
    }
    assert is_structural_aspect_tautology({"p1": "AS", "p2": "DS", "type": "opposition"})
    assert is_structural_aspect_tautology({"p1": "Rahu", "p2": "Ketu", "type": "opposition"})
    assert not is_structural_aspect_tautology({"p1": "AS", "p2": "MC", "type": "trine"})


def test_displayable_aspects_hide_angles_only_when_houses_unavailable():
    aspect = {"p1": "Sun", "p2": "AS", "type": "trine"}

    assert aspect_is_displayable(aspect, use_houses=True)
    assert not aspect_is_displayable(aspect, use_houses=False)


def test_similarity_aspect_map_uses_display_rules_not_broad_angle_angle_exclusion():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        retcon_time_used=False,
        aspects=[
            {"p1": "AS", "p2": "MC", "type": "trine", "delta": 0.5},
            {"p1": "AS", "p2": "DS", "type": "opposition", "delta": 0.0},
            {"p1": "Sun", "p2": "Moon", "type": "sextile", "delta": 1.0},
        ],
    )

    assert _aspect_map(chart) == {
        (("AS", "MC"), "trine"): [0.5],
        (("Moon", "Sun"), "sextile"): [1.0],
    }


def test_display_key_hides_missing_position_endpoints_when_requested():
    aspect = {"p1": "Sun", "p2": "Moon", "type": "sextile"}

    assert display_aspect_key(aspect, use_houses=True, known_positions={"Sun"}) is None
    assert display_aspect_key(aspect, use_houses=True, known_positions={"Sun", "Moon"}) == (
        ("Moon", "Sun"),
        "sextile",
    )
