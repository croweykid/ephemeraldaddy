from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from ephemeraldaddy.analysis import prediction_context as context_module
from ephemeraldaddy.analysis import weighted_chart_predictor as predictor
from ephemeraldaddy.gui.features.predictions.trait_factor_explanations import (
    build_trait_factor_evidence,
)


def _range_chart() -> SimpleNamespace:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        dt=dt,
        dt_local=dt,
        lat=0.0,
        lon=0.0,
        birthtime_unknown=True,
        retcon_time_used=False,
        retcon_hour=None,
        retcon_minute=None,
        rectification_range_used=True,
        rectification_range_start_minute=900,
        rectification_range_end_minute=1020,
        use_birth_time_data=False,
        positions={"Moon": 45.0},  # Taurus in the unresolved source payload.
        aspects=[],
        houses=[],
        housesPo=[],
        retrogrades={},
        dominant_sign_weights={"Taurus": 99.0, "Gemini": 0.0},
        dominant_planet_weights={"Moon": 99.0},
        dominant_nakshatra_weights={"Rohini": 99.0},
        dominant_element_weights={"Earth": 99.0},
        human_design_gates=[1],
        human_design_lines=["1.1"],
        human_design_channels=[(1, 8)],
        human_design_type="Generator",
        human_design_defined_centers=["Sacral"],
        human_design_profile="1/3",
        human_design_authority="Sacral",
    )


def _resolved_context(monkeypatch):
    chart = _range_chart()

    def fake_policy(effective):
        # Stand in for core.chart's rectification-range midpoint application.
        effective.dt = effective.dt.replace(hour=16, minute=0)
        effective.positions = {"Moon": 65.0}  # Gemini at the rectified midpoint.
        effective.houses = []
        effective.housesPo = []
        effective.aspects = []

    monkeypatch.setattr(context_module, "apply_time_specific_metadata_policy", fake_policy)
    monkeypatch.setattr(context_module, "find_aspects", lambda _positions: [])

    context = context_module.build_effective_prediction_context(
        chart,
        calculate_sign_weights=lambda effective: {
            "Taurus": 0.0,
            "Gemini": 10.0 if effective.positions.get("Moon") == 65.0 else 0.0,
        },
        calculate_body_weights=lambda _effective: {"Moon": 10.0},
        calculate_house_weights=lambda _effective: {},
        calculate_nakshatra_weights=lambda _effective: {"Mrigashira": 5.0},
        uses_houses=lambda _effective: False,
        force_rebuild=True,
    )
    return chart, context


def test_injected_calculators_do_not_load_gui_metric_defaults(monkeypatch):
    def unexpected_default():
        pytest.fail("GUI metric default should not load when its calculator is injected")

    monkeypatch.setattr(context_module, "_default_sign_weight_calculator", unexpected_default)
    monkeypatch.setattr(context_module, "_default_body_weight_calculator", unexpected_default)
    monkeypatch.setattr(context_module, "_default_house_weight_calculator", unexpected_default)
    monkeypatch.setattr(context_module, "_default_nakshatra_weight_calculator", unexpected_default)

    _chart, context = _resolved_context(monkeypatch)

    assert context.sign_weights == {"Taurus": 0.0, "Gemini": 10.0}
    assert context.body_weights == {"Moon": 10.0}
    assert context.house_weights == {}
    assert context.nakshatra_weights == {"Mrigashira": 5.0}


def test_context_overrides_bypass_chart_level_cache(monkeypatch):
    chart = _range_chart()
    monkeypatch.setattr(context_module, "apply_time_specific_metadata_policy", lambda _chart: None)
    monkeypatch.setattr(context_module, "find_aspects", lambda _positions: [])

    first = context_module.build_effective_prediction_context(
        chart,
        calculate_sign_weights=lambda _chart: {"Taurus": 10.0},
        calculate_body_weights=lambda _chart: {"Moon": 10.0},
        calculate_house_weights=lambda _chart: {1: 7.0},
        calculate_nakshatra_weights=lambda _chart: {"Rohini": 5.0},
        uses_houses=lambda _chart: False,
    )
    second = context_module.build_effective_prediction_context(
        chart,
        calculate_sign_weights=lambda _chart: {"Gemini": 12.0},
        calculate_body_weights=lambda _chart: {"Moon": 11.0},
        calculate_house_weights=lambda _chart: {1: 7.0},
        calculate_nakshatra_weights=lambda _chart: {"Mrigashira": 6.0},
        uses_houses=lambda _chart: True,
    )

    assert first is not second
    assert first.use_houses is False
    assert first.house_weights == {}
    assert first.sign_weights == {"Taurus": 10.0}
    assert second.use_houses is True
    assert second.house_weights == {1: 7.0}
    assert second.sign_weights == {"Gemini": 12.0}
    assert not hasattr(chart, "_effective_prediction_context_cache")


def test_rectified_range_context_uses_resolved_midpoint_not_persisted_dominance(monkeypatch):
    chart, context = _resolved_context(monkeypatch)

    assert context.birth_time_policy == "rectified_range"
    assert context.rectification_range == (900, 1020)
    assert context.chart.positions["Moon"] == 65.0
    assert context.sign_weights == {"Taurus": 0.0, "Gemini": 10.0}
    assert context.chart.dominant_sign_weights == context.sign_weights

    # Building a prediction context must not rewrite the live chart or bless its
    # stale persistence payload as a valid scoring input.
    assert chart.positions["Moon"] == 45.0
    assert chart.dominant_sign_weights["Taurus"] == 99.0


def test_weighted_score_and_factor_evidence_share_rectified_context(monkeypatch):
    chart, context = _resolved_context(monkeypatch)
    matches = {}
    profile = {
        "signs": {"Taurus": 10.0, "Gemini": 10.0},
    }
    predictors = {"range-sensitive trait": profile}

    scores = context_module.calculate_weighted_criteria_scores_with_context(
        chart,
        predictors=predictors,
        prediction_context=context,
        matched_criteria_out=matches,
        _original_calculate=predictor.calculate_weighted_criteria_scores,
    )

    trait_matches = matches["range-sensitive trait"]
    evidence = build_trait_factor_evidence(
        context.chart,
        profile,
        matches=trait_matches,
    )

    assert scores["range-sensitive trait"] > 0.0
    assert trait_matches["positive"] == ["Gemini"]
    assert "Taurus" not in trait_matches["positive"]
    assert "Gemini" in evidence.supporting
    assert "Taurus not above baseline in chart" in evidence.missing
    assert context.matched_criteria_by_profile
