import pytest

from ephemeraldaddy.core.feedback_prediction_fields import (
    APP_PREDICTIONS,
    LEGACY_USER_FEEDBACK_FIELDS,
    OBSERVATION_CONTEXT,
    SIMILARITY_ACCURACY_OBSERVATION_FIELDS,
    USER_FEEDBACK,
    require_classified_similarity_accuracy_observation,
)


def test_feedback_and_prediction_provenance_is_disjoint_and_explicit():
    assert not USER_FEEDBACK.intersection(APP_PREDICTIONS)
    assert {
        "perceived_similarity_score",
        "perceived_similarity_not_applicable",
        "trait_accuracy_score",
    } <= USER_FEEDBACK
    assert {"user_reported_accuracy", "not_applicable"} <= LEGACY_USER_FEEDBACK_FIELDS
    assert {"predicted_percent", "algorithm_snapshot", "algorithm_mode"} <= APP_PREDICTIONS
    assert {"chart_uids", "timestamp_utc"} <= OBSERVATION_CONTEXT
    assert SIMILARITY_ACCURACY_OBSERVATION_FIELDS == (
        USER_FEEDBACK | LEGACY_USER_FEEDBACK_FIELDS | APP_PREDICTIONS | OBSERVATION_CONTEXT
    )


def test_similarity_observation_rejects_unclassified_provenance():
    require_classified_similarity_accuracy_observation(
        {
            "chart_uids": ["A", "B"],
            "user_reported_accuracy": 65,
            "predicted_percent": 80.0,
            "algorithm_mode": "custom",
        }
    )
    with pytest.raises(ValueError, match="Classify them as USER_FEEDBACK"):
        require_classified_similarity_accuracy_observation({"mystery_score": 12})
