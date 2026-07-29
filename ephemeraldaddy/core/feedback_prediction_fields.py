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


USER_FEEDBACK = frozenset(
    {
        "perceived_similarity_score",
        "perceived_similarity_not_applicable",
        "trait_accuracy_score",
    }
)

# Read-only compatibility names from before feedback types were distinguished.
# ``not_applicable`` meant that the user could not meaningfully assess the
# chart pair; it was feedback state, not an algorithm result. New records use
# the domain-specific name above so it cannot be confused with future feedback.
LEGACY_USER_FEEDBACK_FIELDS = frozenset(
    {"user_reported_accuracy", "user_perceived_similarity_score", "not_applicable"}
)

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
    USER_FEEDBACK | LEGACY_USER_FEEDBACK_FIELDS | APP_PREDICTIONS | OBSERVATION_CONTEXT
)

if (USER_FEEDBACK | LEGACY_USER_FEEDBACK_FIELDS) & APP_PREDICTIONS:
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


def perceived_similarity_feedback(payload: Mapping[str, Any]) -> tuple[Any, bool]:
    """Return canonical perceived-similarity feedback from any log generation."""
    score = payload.get("perceived_similarity_score")
    if score is None:
        score = payload.get("user_perceived_similarity_score")
    if score is None:
        score = payload.get("user_reported_accuracy")
    unavailable = bool(
        payload.get(
            "perceived_similarity_not_applicable",
            payload.get("not_applicable", False),
        )
    )
    return score, unavailable
