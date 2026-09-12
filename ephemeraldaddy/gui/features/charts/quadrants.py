"""House-based quadrant analytics for Chart View."""

from __future__ import annotations

from collections.abc import Mapping

from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_house_prevalence_counts,
)

QUADRANT_DEFINITIONS: tuple[tuple[str, str, tuple[int, int, int]], ...] = (
    ("I", "Personal Identity", (1, 2, 3)),
    ("II", "Personal Expression", (4, 5, 6)),
    ("III", "Social Identity", (7, 8, 9)),
    ("IV", "Social Expression", (10, 11, 12)),
)


def quadrant_for_house(house: object) -> str | None:
    """Return the Roman-numeral quadrant for a 1-based house number."""
    try:
        house_number = int(house)
    except (TypeError, ValueError):
        return None
    if house_number < 1 or house_number > 12:
        return None
    return QUADRANT_DEFINITIONS[(house_number - 1) // 3][0]


def aggregate_house_values_by_quadrant(
    house_values: Mapping[object, object] | None,
) -> dict[str, float]:
    """Aggregate house-indexed values into the four standard house quadrants."""
    totals = {quadrant: 0.0 for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS}
    for raw_house, raw_value in (house_values or {}).items():
        quadrant = quadrant_for_house(raw_house)
        if quadrant is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        totals[quadrant] += value
    return totals


def calculate_quadrant_prevalence_counts(chart: object) -> dict[str, float]:
    """Return unweighted object counts grouped into quadrants."""
    return aggregate_house_values_by_quadrant(calculate_house_prevalence_counts(chart))


def calculate_dominant_quadrant_weights(chart: object) -> dict[str, float]:
    """Return existing house-dominance weights grouped into quadrants."""
    return aggregate_house_values_by_quadrant(calculate_dominant_house_weights(chart))


def quadrant_percentages(values: Mapping[str, object] | None) -> dict[str, float]:
    """Normalize quadrant values to percentages without dividing by zero."""
    normalized: dict[str, float] = {}
    for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS:
        try:
            normalized[quadrant] = max(0.0, float((values or {}).get(quadrant, 0.0)))
        except (TypeError, ValueError):
            normalized[quadrant] = 0.0
    total = sum(normalized.values())
    if total <= 0:
        return {quadrant: 0.0 for quadrant in normalized}
    return {quadrant: (value / total) * 100.0 for quadrant, value in normalized.items()}
