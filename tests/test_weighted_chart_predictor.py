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
