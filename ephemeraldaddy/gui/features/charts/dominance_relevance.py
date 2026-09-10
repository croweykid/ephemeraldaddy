"""Reusable per-chart relevance labels derived from dominant-body weights."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from ephemeraldaddy.core.interpretations import normalize_body_name
from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_planet_weights


@dataclass(frozen=True, slots=True)
class ChartBodyRelevance:
    """Dominant-body weights plus an intentionally simple chart-relative cutoff."""

    weights: Mapping[str, float]
    median_weight: float
    above_median_bodies: frozenset[str]

    def weight_for(self, body: str) -> float | None:
        return self.weights.get(normalize_body_name(str(body)))

    def is_above_median(self, body: str) -> bool:
        return normalize_body_name(str(body)) in self.above_median_bodies


def calculate_chart_body_relevance(chart) -> ChartBodyRelevance:
    """Classify bodies whose dominance weight is strictly above this chart's median.

    This deliberately does not invent a new astrological scoring system. It reuses
    EphemeralDaddy's existing dominant-body calculation and adds only the relative
    cutoff needed by features such as Personal Timeline.
    """
    raw_weights = calculate_dominant_planet_weights(chart)
    normalized: dict[str, float] = {}
    for raw_body, raw_weight in (raw_weights or {}).items():
        body = normalize_body_name(str(raw_body))
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if not body or not math.isfinite(weight):
            continue
        normalized[body] = weight

    values = tuple(normalized.values())
    median_weight = float(statistics.median(values)) if values else 0.0
    above_median = frozenset(
        body for body, weight in normalized.items() if weight > median_weight
    )
    return ChartBodyRelevance(
        weights=MappingProxyType(dict(normalized)),
        median_weight=median_weight,
        above_median_bodies=above_median,
    )
