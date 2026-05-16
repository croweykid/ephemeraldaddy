import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace


@dataclass
class _StubDnDStatBlock:
    raw_scores: dict
    scores: dict
    modifiers: dict


def _stub_clamp01(value):
    return max(0.0, min(1.0, float(value)))


stub_axes = ModuleType("ephemeraldaddy.analysis.dnd.dnd_class_axes_v2")
stub_axes.DND_CLASSES = {}
stub_axes.DnDClassScorer = object
stub_axes.DnDStatBlock = _StubDnDStatBlock
stub_axes.build_dnd_statblock_profile_lines = lambda *_args, **_kwargs: []
stub_axes.score_class_axes = lambda *_args, **_kwargs: {}
stub_axes.score_dnd_statblock = lambda *_args, **_kwargs: _StubDnDStatBlock({}, {}, {})
stub_axes._build_axis_score_bar = lambda *_args, **_kwargs: ""
stub_axes._build_right_justified_label = lambda label, _width: label
stub_axes._clamp01 = _stub_clamp01
sys.modules["ephemeraldaddy.analysis.dnd.dnd_class_axes_v2"] = stub_axes

from ephemeraldaddy.analysis.dnd import dnd_stat_calculator as stat_calculator
from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_STAT_PREDICTORS
from ephemeraldaddy.analysis.dnd.dnd_stat_calculator import (
    _calculate_predictor_criteria_budgets,
    _calculate_stat_evidence_denominators,
    _normalize_weighted_stat_scores,
    _to_dnd_stat,
)


def test_dnd_stat_normalization_anchors_average_band():
    assert _to_dnd_stat(0.0) == 5
    assert _to_dnd_stat(0.5) == 11
    assert _to_dnd_stat(1.0) == 20


def test_dnd_stat_normalization_keeps_clear_low_and_high_bands():
    assert _to_dnd_stat(0.33) < 10
    assert 10 <= _to_dnd_stat(0.5) <= 12
    assert _to_dnd_stat(0.62) > 12


def test_weighted_stat_scores_use_absolute_evidence_not_per_chart_minmax():
    raw_scores = {
        "STR": 1.0,
        "DEX": 0.15,
        "CON": 0.0,
        "INT": -0.1,
        "WIS": -0.2,
        "CHA": -0.3,
    }

    normalized = _normalize_weighted_stat_scores(raw_scores)
    dnd_scores = {key: _to_dnd_stat(value) for key, value in normalized.items()}

    assert all(10 <= dnd_scores[key] <= 12 for key in ("STR", "DEX", "CON", "INT", "WIS", "CHA"))
    assert min(dnd_scores.values()) > 5
    assert max(dnd_scores.values()) < 20


def test_score_dnd_statblock_does_not_force_min_and_max_for_ordinary_spreads(monkeypatch):
    monkeypatch.setattr(
        stat_calculator,
        "calculate_weighted_criteria_scores",
        lambda _chart, *, predictors: {
            "STR": 1.0,
            "DEX": 0.15,
            "CON": 0.0,
            "INT": -0.1,
            "WIS": -0.2,
            "CHA": -0.3,
        },
    )

    statblock = stat_calculator.score_dnd_statblock(SimpleNamespace(name="Ordinary spread"))

    assert statblock.scores == {
        "STR": 11,
        "DEX": 11,
        "CON": 11,
        "INT": 11,
        "WIS": 11,
        "CHA": 11,
    }


def test_dnd_stat_evidence_denominators_account_for_criteria_coverage():
    budgets = _calculate_predictor_criteria_budgets(DND_STAT_PREDICTORS)
    denominators = _calculate_stat_evidence_denominators(DND_STAT_PREDICTORS)

    assert budgets["DEX"] > budgets["WIS"]
    assert budgets["STR"] > budgets["INT"]
    assert denominators["DEX"] == budgets["DEX"]
    assert denominators["INT"] > budgets["INT"]


def test_score_dnd_statblock_normalizes_criteria_budget_before_mapping(monkeypatch):
    monkeypatch.setattr(
        stat_calculator,
        "calculate_weighted_criteria_scores",
        lambda _chart, *, predictors: {
            "STR": 24.0,
            "DEX": 18.0,
            "CON": 16.0,
            "INT": 14.0,
            "WIS": 0.0,
            "CHA": -18.0,
        },
    )

    statblock = stat_calculator.score_dnd_statblock(SimpleNamespace(name="Uneven criteria spread"))

    assert statblock.scores == {
        "STR": 13,
        "DEX": 12,
        "CON": 13,
        "INT": 13,
        "WIS": 11,
        "CHA": 10,
    }
    assert 20 not in statblock.scores.values()
    assert 5 not in statblock.scores.values()


def test_score_dnd_statblock_uses_dnd_stat_predictors(monkeypatch):
    captured = {}

    def fake_weighted_scores(_chart, *, predictors):
        captured["predictors"] = predictors
        return {key: 0.0 for key in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}

    monkeypatch.setattr(
        stat_calculator,
        "calculate_weighted_criteria_scores",
        fake_weighted_scores,
    )

    stat_calculator.score_dnd_statblock(SimpleNamespace(name="Predictor-only"))

    assert captured["predictors"] is DND_STAT_PREDICTORS


def test_old_feature_based_stat_scorer_is_removed():
    assert not hasattr(stat_calculator, "score_dnd_statblock_from_features")
    assert not hasattr(stat_calculator, "_shape_stat_profile")


def test_weighted_stat_scores_reserve_bounds_for_exceptional_evidence():
    raw_scores = {
        "STR": 24.0,
        "DEX": 18.0,
        "CON": 16.0,
        "INT": 14.0,
        "WIS": 0.0,
        "CHA": -18.0,
    }

    normalized = _normalize_weighted_stat_scores(raw_scores)
    dnd_scores = {key: _to_dnd_stat(value) for key, value in normalized.items()}

    assert dnd_scores == {
        "STR": 18,
        "DEX": 17,
        "CON": 16,
        "INT": 16,
        "WIS": 11,
        "CHA": 7,
    }
    assert 20 not in dnd_scores.values()
    assert 5 not in dnd_scores.values()
