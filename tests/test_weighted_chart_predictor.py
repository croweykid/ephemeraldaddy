from types import SimpleNamespace

from ephemeraldaddy.analysis.weighted_chart_predictor import (
    WeightedPredictorScoringOptions,
    calculate_weighted_criteria_scores,
    coerce_scoring_options,
)


def _empty_weights(_chart):
    return {}


def _score(predictors, chart):
    return calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=_empty_weights,
        calculate_body_weights=_empty_weights,
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
    )


def test_scores_human_design_and_bazi_metadata_categories():
    chart = SimpleNamespace(
        human_design_type="Manifesting Generator",
        human_design_defined_centers=["Solar Plexus", "Sacral"],
        human_design_profile="1/3",
        human_design_authority="Emotional",
        bazi_sign_weights={"Horse": 2, "Dog": 1, "Rabbit": 1},
    )
    predictors = {
        "match": {
            "hdtypes": {"MF Generator": 6},
            "antihdtypes": {"Projector": 7},
            "centers": {"Emotional": 2, "Sacral": 3},
            "anticenters": {"Root": 5, "Sacral": 1},
            "profiles": {"1/3": 7},
            "antiprofiles": {"3/5": 4},
            "authorities": {"Emotional": 5},
            "antiauthorities": {"Sacral": 2},
            "bazisigns": {"Horse": 4, "Rabbit": 1},
            "antibazisigns": {"Dog": 3},
        },
        "miss": {
            "hdtypes": {"Projector": 6},
            "centers": {"Root": 3},
            "profiles": {"3/5": 7},
            "authorities": {"Splenic": 5},
            "bazisigns": {"Snake": 4},
        },
    }

    scores = _score(predictors, chart)

    assert scores["match"] == 28.0
    assert scores["miss"] == 0.0


def test_scoring_options_include_human_design_activation_weight():
    options = WeightedPredictorScoringOptions(human_design_activation_weight=2.5)

    assert options.human_design_activation_weight == 2.5


def test_coerce_scoring_options_preserves_human_design_activation_weight():
    options = coerce_scoring_options({"human_design_activation_weight": "0.25"})

    assert options.human_design_activation_weight == 0.25


def test_scores_weighted_human_design_channels():
    chart = SimpleNamespace(human_design_channels=["34-20", "6-59"])
    predictors = {
        "weighted_channel": {
            "channels": {(20, 34): 2},
        },
        "unweighted_channel": {
            "channels": [[20, 34]],
        },
        "anti_channel": {
            "antichannels": {(59, 6): 2},
        },
    }

    scores = _score(predictors, chart)

    assert scores["weighted_channel"] == 2.0
    assert scores["unweighted_channel"] == 1.0
    assert scores["anti_channel"] == -2.0


def test_scores_bazi_signs_from_stored_pillars():
    chart = SimpleNamespace(
        bazi_year_pillar="甲午",
        bazi_month_pillar="丙午",
        bazi_day_pillar="甲戌",
        bazi_hour_pillar="乙卯",
    )
    predictors = {
        "bazi": {
            "bazisigns": {"Horse": 2, "Rabbit": 3},
            "antibazisigns": {"Dog": 4},
        }
    }

    scores = _score(predictors, chart)

    assert scores["bazi"] == 3.0


def test_position_dominance_weighting_can_be_disabled():
    chart = SimpleNamespace(positions={"Sun": 330.0})
    predictors = {"target": {"positions": {"Sun in Pisces": 8}}}

    weighted = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=lambda _chart: {"Pisces": 3, "Aries": 1},
        calculate_body_weights=lambda _chart: {"Sun": 2, "Moon": 0},
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            use_position_dominance_weighting=True,
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
        ),
    )
    binary = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=lambda _chart: {"Pisces": 3, "Aries": 1},
        calculate_body_weights=lambda _chart: {"Sun": 2, "Moon": 0},
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            use_position_dominance_weighting=False,
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
        ),
    )

    assert weighted["target"] == 16.0
    assert binary["target"] == 8.0


def test_aspect_dominance_weighting_can_use_orb_quality_instead():
    chart = SimpleNamespace(
        aspects=[{"p1": "Sun", "p2": "Moon", "type": "conjunction", "delta": 2.0}]
    )
    predictors = {"target": {"aspects": {"Sun conjunction Moon": 8}}}

    weighted = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=_empty_weights,
        calculate_body_weights=lambda _chart: {"Sun": 2, "Moon": 0},
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            use_aspect_dominance_weighting=True,
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
        ),
    )
    orb_quality = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=_empty_weights,
        calculate_body_weights=lambda _chart: {"Sun": 2, "Moon": 0},
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            use_aspect_dominance_weighting=False,
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
        ),
    )

    assert weighted["target"] == 80.0
    assert orb_quality["target"] == 6.0


def test_simplified_anti_handling_directly_subtracts_anti_weights_without_category_weights():
    chart = SimpleNamespace(dominant_sign_weights={"Aries": 3, "Libra": 1})
    predictors = {"target": {"signs": {"Aries": 10}, "antisigns": {"Aries": 4}}}

    scores = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        category_weights={"signs": 0.0},
        calculate_sign_weights=lambda _chart: {"Aries": 3, "Libra": 1},
        calculate_body_weights=_empty_weights,
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
        ),
    )

    assert scores["target"] == 6.0


def test_skips_hd_gate_and_bazi_resolution_when_predictors_do_not_use_those_categories(monkeypatch):
    from ephemeraldaddy.analysis import weighted_chart_predictor as predictor

    def fail_resolution(*_args, **_kwargs):
        raise AssertionError("unneeded metadata resolution should not run")

    monkeypatch.setattr(predictor, "active_human_design_gates", fail_resolution)
    monkeypatch.setattr(predictor, "active_human_design_properties", fail_resolution)
    monkeypatch.setattr(predictor, "active_bazi_sign_weights", fail_resolution)

    chart = SimpleNamespace(dominant_sign_weights={"Aries": 1})
    scores = _score({"target": {"signs": {"Aries": 2}}}, chart)

    assert scores["target"] == 0.0


def test_bazi_fallback_uses_rectified_time_when_hour_is_available(monkeypatch):
    from datetime import datetime

    from ephemeraldaddy.analysis import bazi_getter

    captured = {}

    def fake_chart_uses_houses(_chart):
        return True

    def fake_build_bazi_chart_data(dt_local, *, include_hour=True):
        captured["dt_local"] = dt_local
        captured["include_hour"] = include_hour
        return SimpleNamespace(earthly_branches={"year": "午", "month": "戌", "day": "卯", "hour": "午"})

    monkeypatch.setattr(bazi_getter, "bazi_include_hour_for_chart", fake_chart_uses_houses)
    monkeypatch.setattr(bazi_getter, "build_bazi_chart_data", fake_build_bazi_chart_data)
    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 34),
        retcon_time_used=True,
        retcon_hour=22,
        retcon_minute=15,
    )

    weights = bazi_getter.bazi_sign_weights_from_chart(chart)

    assert captured["dt_local"].hour == 22
    assert captured["dt_local"].minute == 15
    assert captured["include_hour"] is True
    assert weights == {"Horse": 2.0, "Dog": 1.0, "Rabbit": 1.0}


def test_bazi_signs_from_stored_pillars_exclude_hour_without_house_time(monkeypatch):
    from ephemeraldaddy.analysis import bazi_getter

    monkeypatch.setattr(bazi_getter, "bazi_include_hour_for_chart", lambda _chart: False)
    chart = SimpleNamespace(
        bazi_year_pillar="甲午",
        bazi_month_pillar="丙午",
        bazi_day_pillar="甲戌",
        bazi_hour_pillar="乙卯",
    )

    weights = bazi_getter.bazi_sign_weights_from_chart(chart)

    assert weights == {"Horse": 2.0, "Dog": 1.0}


def test_direct_dominance_can_use_share_of_total_activation():
    chart = SimpleNamespace(dominant_sign_weights={"Aquarius": 42, "Libra": 58})
    predictors = {"e4": {"signs": {"Aquarius": 19}}}

    scores = calculate_weighted_criteria_scores(
        chart,
        predictors=predictors,
        calculate_sign_weights=lambda _chart: {"Aquarius": 42, "Libra": 58},
        calculate_body_weights=_empty_weights,
        calculate_house_weights=_empty_weights,
        calculate_nakshatra_weights=_empty_weights,
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            simplify_anti_factor_handling=True,
            average_scores_by_criterion_count=False,
            dominance_normalization_mode="share",
        ),
    )

    assert round(scores["e4"], 2) == 7.98
