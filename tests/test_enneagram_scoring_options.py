from pathlib import Path

from ephemeraldaddy.analysis.weighted_chart_predictor import (
    TYPE_SIGNATURE_SCALE_SQRT,
    WeightedPredictorScoringOptions,
    calculate_weighted_criteria_scores,
)

SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text()


def test_enneagram_defaults_use_sqrt_type_opportunity_scaling_source():
    assert "TYPE_SIGNATURE_SCALE_SQRT" in SOURCE
    assert "type_signature_scale_mode=TYPE_SIGNATURE_SCALE_SQRT" in SOURCE
    assert '"type_signature_scale_mode": str(options.type_signature_scale_mode or TYPE_SIGNATURE_SCALE_SQRT)' in SOURCE


def test_sqrt_type_opportunity_scaling_divides_by_available_signature_weight_root():
    chart = type("Chart", (), {"dominant_sign_weights": {"Aries": 1}})()

    scores = calculate_weighted_criteria_scores(
        chart,
        predictors={
            "small": {"signs": {"Aries": 9}},
            "wide": {"signs": {"Aries": 9, "Taurus": 9, "Gemini": 9, "Cancer": 9}},
        },
        calculate_body_weights=lambda _chart: {},
        calculate_house_weights=lambda _chart: {},
        calculate_nakshatra_weights=lambda _chart: {},
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            average_scores_by_criterion_count=False,
            type_signature_scale_mode=TYPE_SIGNATURE_SCALE_SQRT,
            dominance_normalization_mode="share",
        ),
    )

    assert scores == {"small": 3.0, "wide": 1.5}


def test_sqrt_type_opportunity_scaling_ignores_unavailable_house_signature_weight():
    chart = type("Chart", (), {"dominant_sign_weights": {"Aries": 1}})()

    scores = calculate_weighted_criteria_scores(
        chart,
        predictors={
            "sign_only": {"signs": {"Aries": 9}},
            "sign_with_unavailable_houses": {
                "signs": {"Aries": 9},
                "houses": {1: 9, 2: 9, 3: 9},
                "antihouses": {4: 9},
                "positions": {"Moon in H8": 9, "Cancer in H4": 9},
                "antipositions": {"Mars in H12": 9},
            },
        },
        calculate_body_weights=lambda _chart: {},
        calculate_house_weights=lambda _chart: {1: 1, 2: 1, 3: 1, 4: 1},
        calculate_nakshatra_weights=lambda _chart: {},
        uses_houses=lambda _chart: False,
        scoring_options=WeightedPredictorScoringOptions(
            average_scores_by_criterion_count=False,
            type_signature_scale_mode=TYPE_SIGNATURE_SCALE_SQRT,
            dominance_normalization_mode="share",
        ),
    )

    assert scores == {"sign_only": 3.0, "sign_with_unavailable_houses": 3.0}
