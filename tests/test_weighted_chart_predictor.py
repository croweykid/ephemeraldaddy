from types import SimpleNamespace

from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores


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
    from ephemeraldaddy.analysis import weighted_chart_predictor as predictor

    captured = {}

    def fake_chart_uses_houses(_chart):
        return True

    def fake_build_bazi_chart_data(dt_local, *, include_hour=True):
        captured["dt_local"] = dt_local
        captured["include_hour"] = include_hour
        return SimpleNamespace(earthly_branches={"year": "午", "month": "戌", "day": "卯", "hour": "午"})

    monkeypatch.setattr(predictor, "default_chart_uses_houses", fake_chart_uses_houses)
    monkeypatch.setattr(bazi_getter, "build_bazi_chart_data", fake_build_bazi_chart_data)
    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 34),
        retcon_time_used=True,
        retcon_hour=22,
        retcon_minute=15,
    )

    weights = predictor.active_bazi_sign_weights(chart)

    assert captured["dt_local"].hour == 22
    assert captured["dt_local"].minute == 15
    assert captured["include_hour"] is True
    assert weights == {"Horse": 2.0, "Dog": 1.0, "Rabbit": 1.0}
