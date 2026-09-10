from __future__ import annotations

import pytest

from ephemeraldaddy.analysis import theme_norms
from ephemeraldaddy.analysis import theme_prominence as prominence


def _context(*, houses_available: bool, house_activation: float = 0.0):
    return {
        "signs": {"Aries": 1.0},
        "bodies": {},
        "houses": {1: house_activation} if houses_available else {},
        "houses_available": houses_available,
        "elements": {},
        "modes": {},
        "nakshatras": {},
        "bazisigns": {},
        "bazi_available": False,
        "hd": {
            "gates": set(),
            "channels": set(),
            "centers": set(),
            "profile": "",
            "authority": "",
            "cross": "",
            "available": False,
        },
    }


def _install_minimal_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prominence,
        "THEMES",
        {
            "sample": {
                "family": "family",
                "signs": ["Aries"],
                "houses": [1],
            }
        },
    )
    monkeypatch.setattr(
        prominence,
        "THEME_FAMILIES",
        {"family": {"label": "Family"}},
    )
    monkeypatch.setattr(prominence, "WEIGHTED_THEME_PROPERTIES", ("signs", "houses"))
    monkeypatch.setattr(prominence, "theme_item_weight", lambda *_args: 1.0)
    monkeypatch.setattr(prominence, "themes_in_family", lambda _family_key: ["sample"])


def test_database_theme_norms_separate_incompatible_score_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_minimal_reference(monkeypatch)
    contexts = {
        "timed": _context(houses_available=True, house_activation=0.0),
        "unknown-time": _context(houses_available=False),
    }
    monkeypatch.setattr(prominence, "_activation_context", lambda chart: contexts[chart])

    _legacy_overall, by_availability, chart_counts = (
        theme_norms.calculate_database_theme_family_baselines(
            ["timed", "unknown-time"]
        )
    )

    timed_key = "houses:1|hd:0|bazi:0"
    unknown_key = "houses:0|hd:0|bazi:0"
    # Same Aries activation, but the timed chart has an available/inactive house
    # category while the unknown-time chart legitimately omits that category.
    assert by_availability[timed_key]["family"] == pytest.approx(50.0)
    assert by_availability[unknown_key]["family"] == pytest.approx(100.0)
    assert chart_counts == {timed_key: 1, unknown_key: 1}


def test_snapshot_lookup_selects_only_matching_availability_stratum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        prominence,
        "THEME_FAMILIES",
        {"family": {"label": "Family"}},
    )
    monkeypatch.setattr(prominence, "theme_definition_signature", lambda: "current")
    snapshot = {
        "theme_family_definition_signature": "current",
        theme_norms.THEME_NORMS_AVAILABILITY_SCHEMA_FIELD: (
            theme_norms.THEME_NORMS_AVAILABILITY_SCHEMA_VERSION
        ),
        theme_norms.THEME_FAMILY_AVAILABILITY_ROWS_FIELD: {
            "houses:1|hd:1|bazi:1": {"family": 40.0},
            "houses:0|hd:0|bazi:1": {"family": 70.0},
        },
    }

    assert theme_norms.theme_family_snapshot_averages_for_availability(
        snapshot,
        "houses:1|hd:1|bazi:1",
    ) == {"family": 40.0}
    assert theme_norms.theme_family_snapshot_averages_for_availability(
        snapshot,
        "houses:0|hd:0|bazi:1",
    ) == {"family": 70.0}
    assert theme_norms.theme_family_snapshot_averages_for_availability(
        snapshot,
        "houses:1|hd:0|bazi:0",
    ) == {}


def test_old_mixed_theme_snapshot_requires_recalculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prominence, "theme_definition_signature", lambda: "current")
    reason = theme_norms.theme_snapshot_unavailability_reason_for_availability(
        {
            "theme_family_definition_signature": "current",
            "theme_family_raw_averages": {"family": 55.0},
        },
        "houses:0|hd:0|bazi:1",
    )

    assert "predates availability-stratified Theme baselines" in reason


def test_snapshot_enrichment_records_strata_and_population_counts() -> None:
    enriched = theme_norms.enrich_theme_snapshot_with_availability_baselines(
        {"snapshot_id": "test"},
        {
            "houses:0|hd:0|bazi:1": {"family": 70.0},
            "houses:1|hd:1|bazi:1": {"family": 40.0},
        },
        {
            "houses:0|hd:0|bazi:1": 12,
            "houses:1|hd:1|bazi:1": 88,
        },
    )

    assert enriched[theme_norms.THEME_NORMS_AVAILABILITY_SCHEMA_FIELD] == 1
    assert enriched[theme_norms.THEME_FAMILY_AVAILABILITY_ROWS_FIELD][
        "houses:1|hd:1|bazi:1"
    ]["family"] == 40.0
    assert enriched[theme_norms.THEME_FAMILY_AVAILABILITY_COUNTS_FIELD][
        "houses:0|hd:0|bazi:1"
    ] == 12
