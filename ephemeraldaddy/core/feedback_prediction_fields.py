"""Authoritative provenance boundary between feedback and predictions.

``USER_FEEDBACK`` is a user's present assessment of reality and may be edited.
``APP_PREDICTIONS`` is output produced by an algorithm and is historical once
recorded.  A prediction may be re-evaluated against newer feedback, but newer
feedback must never rewrite the prediction or the settings that produced it.

The registries start with Astro Twin observations and are intended to be
extended as other app features persist comparable feedback/prediction pairs.
Identity and audit fields are deliberately classified as ``OBSERVATION_CONTEXT``
rather than being forced into either semantic category.
"""

from __future__ import annotations

from typing import Any, Mapping


USER_FEEDBACK = frozenset({"user_reported_accuracy", "not_applicable"})

APP_PREDICTIONS = frozenset(
    {
        "algorithm_mode",
        "ranking_algorithm",  # Legacy name for algorithm_mode.
        "predicted_percent",
        "ranking_position",
        "algorithm_snapshot",
    }
)

OBSERVATION_CONTEXT = frozenset(
    {
        "timestamp_utc",
        "chart_uids",
        "chart_1_compared_with_chart_2",  # Legacy chart-pair identity.
    }
)

SIMILARITY_ACCURACY_OBSERVATION_FIELDS = (
    USER_FEEDBACK | APP_PREDICTIONS | OBSERVATION_CONTEXT
)

if USER_FEEDBACK & APP_PREDICTIONS:
    raise RuntimeError("Fields cannot be both USER_FEEDBACK and APP_PREDICTIONS")


def require_classified_similarity_accuracy_observation(payload: Mapping[str, Any]) -> None:
    """Reject new observation fields without an explicit provenance class."""
    unclassified = set(payload) - SIMILARITY_ACCURACY_OBSERVATION_FIELDS
    if unclassified:
        names = ", ".join(sorted(str(field) for field in unclassified))
        raise ValueError(
            "Similarity accuracy observation contains unclassified fields: "
            f"{names}. Classify them as USER_FEEDBACK, APP_PREDICTIONS, or "
            "OBSERVATION_CONTEXT in feedback_prediction_fields.py."
        )
