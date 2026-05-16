"""DB-norm comparison helpers for Database View Similarities Analysis."""

from __future__ import annotations

import math

SIMILARITY_DELTA_SIGNIFICANCE_STANDARD_ERRORS = 2.0
SIMILARITY_DELTA_FALLBACK_SIGNIFICANCE_PERCENTAGE_POINTS = 10.0
SIMILARITY_DELTA_NEUTRAL_RGB = (150, 150, 150)
SIMILARITY_DELTA_POSITIVE_RGB = (127, 255, 0)
SIMILARITY_DELTA_NEGATIVE_RGB = (255, 45, 45)


def similarity_delta_points(
    selection_percent_value: int | float,
    db_percent_value: int | float,
) -> float:
    """Return signed percentage-point delta from the DB norm."""
    return float(selection_percent_value) - float(db_percent_value)


def similarity_deviation_z_score(
    selection_percent_value: int | float,
    db_percent_value: int | float,
    total_count: int,
) -> float | None:
    """Return signed standard-error units for selection prevalence vs. DB norm.

    Positive values are above the DB norm; negative values are below it. The
    denominator matches the standard-error guide lines drawn on the similarity
    bar for a sample with ``total_count`` known charts.
    """
    if total_count <= 0:
        return None
    probability = max(0.0, min(1.0, float(db_percent_value) / 100.0))
    standard_error_percent = (
        math.sqrt(probability * (1.0 - probability) / float(total_count)) * 100.0
    )
    if standard_error_percent <= 0.0 or not math.isfinite(standard_error_percent):
        return None
    z_score = (
        similarity_delta_points(selection_percent_value, db_percent_value)
        / standard_error_percent
    )
    return z_score if math.isfinite(z_score) else None


def similarity_delta_rgb(
    selection_percent_value: int | float,
    db_percent_value: int | float,
    total_count: int | None = None,
) -> tuple[int, int, int]:
    """Color a similarity row by signed, sample-aware distance from the DB norm.

    Over-represented factors move toward green; under-represented factors move
    toward red. Near-DB-norm factors remain neutral instead of being displayed
    as strongly negative solely because their absolute distance is small.
    """
    delta = similarity_delta_points(selection_percent_value, db_percent_value)
    if delta == 0.0:
        return SIMILARITY_DELTA_NEUTRAL_RGB
    target = (
        SIMILARITY_DELTA_POSITIVE_RGB if delta > 0.0 else SIMILARITY_DELTA_NEGATIVE_RGB
    )
    z_score = (
        similarity_deviation_z_score(
            selection_percent_value,
            db_percent_value,
            total_count,
        )
        if total_count is not None
        else None
    )
    if z_score is not None:
        ratio = (
            min(abs(z_score), SIMILARITY_DELTA_SIGNIFICANCE_STANDARD_ERRORS)
            / SIMILARITY_DELTA_SIGNIFICANCE_STANDARD_ERRORS
        )
    else:
        ratio = (
            min(abs(delta), SIMILARITY_DELTA_FALLBACK_SIGNIFICANCE_PERCENTAGE_POINTS)
            / SIMILARITY_DELTA_FALLBACK_SIGNIFICANCE_PERCENTAGE_POINTS
        )
    return tuple(
        int(
            round(
                SIMILARITY_DELTA_NEUTRAL_RGB[index]
                + (target[index] - SIMILARITY_DELTA_NEUTRAL_RGB[index]) * ratio
            )
        )
        for index in range(3)
    )
