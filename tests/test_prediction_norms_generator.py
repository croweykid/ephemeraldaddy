import pytest

from ephemeraldaddy.analysis import prediction_norms_generator as generator


class _Chart:
    def __init__(self, *, houses_available: bool):
        self.houses_available = houses_available


TRAIT = {
    "uid": "trait-1",
    "name": "Example",
    "profile": {"houses": {1: 2}, "signs": {"Aries": 1}},
}


def test_trait_likelihood_for_norm_mode_forces_weighted_predictor_house_policy(monkeypatch):
    seen = []

    def fake_scores(chart, *, predictors, uses_houses, **_kwargs):
        seen.append(uses_houses(chart))
        return {"Example": 1.0 if uses_houses(chart) else -1.0}

    monkeypatch.setattr(generator, "calculate_weighted_criteria_scores", fake_scores)
    monkeypatch.setattr(generator, "trait_possible_score", lambda _profile, *, include_houses: 2.0)

    chart = _Chart(houses_available=True)
    assert generator.trait_likelihood_for_norm_mode(chart, TRAIT, include_houses=True) == 75.0
    assert generator.trait_likelihood_for_norm_mode(chart, TRAIT, include_houses=False) == 25.0
    assert seen == [True, False]


def test_no_house_population_rescores_every_chart_while_house_population_is_filtered(monkeypatch):
    charts = [_Chart(houses_available=True), _Chart(houses_available=False), _Chart(houses_available=True)]

    monkeypatch.setattr(generator, "chart_uses_houses", lambda chart: chart.houses_available)
    monkeypatch.setattr(
        generator,
        "trait_likelihood_for_norm_mode",
        lambda chart, _trait, *, include_houses: 70.0 if include_houses else 40.0,
    )

    with_houses, without_houses = generator.trait_population_scores(charts, TRAIT)
    assert with_houses == [70.0, 70.0]
    assert without_houses == [40.0, 40.0, 40.0]


def test_build_trait_norm_row_from_charts_records_population_sizes(monkeypatch):
    charts = [_Chart(houses_available=True), _Chart(houses_available=False)]
    monkeypatch.setattr(generator, "chart_uses_houses", lambda chart: chart.houses_available)
    monkeypatch.setattr(
        generator,
        "trait_likelihood_for_norm_mode",
        lambda chart, _trait, *, include_houses: 60.0 if include_houses else 45.0,
    )

    row = generator.build_trait_norm_row_from_charts(
        TRAIT,
        charts,
        source="official",
        profile_hash="profile-hash",
    )

    assert row["key"] == "uid:trait-1"
    assert row["sample_sizes"] == {
        "reference_population": 2,
        "with_houses": 1,
        "without_houses": 2,
    }
    assert row["distributions"]["with_houses"]["mean"] == 60.0
    assert row["distributions"]["without_houses"]["mean"] == 45.0
