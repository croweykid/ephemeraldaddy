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
