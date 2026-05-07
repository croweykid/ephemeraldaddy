from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Tuple

from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores
from .dnd_definitions import DND_STAT_PREDICTORS

from .dnd_class_axes_v2 import (
    DnDStatBlock,
    _build_axis_score_bar,
    _build_right_justified_label,
    _clamp01,
)

_DND_STAT_DISPLAY_ORDER: Tuple[str, ...] = ("CHA", "INT", "STR", "CON", "WIS", "DEX")
_DND_STAT_COMPONENT_ORDER: Tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
_DND_STAT_LABELS: Dict[str, str] = {
    "STR": "Strength",
    "DEX": "Dexterity",
    "CON": "Constitution",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}
_DND_STAT_DISPLAY_LABELS: Dict[str, str] = {
    stat_key: f"{stat_key} ({_DND_STAT_LABELS[stat_key]})"
    for stat_key in _DND_STAT_DISPLAY_ORDER
}

_WEIGHT_NORMALIZED_PREDICTOR_CATEGORIES: Tuple[Tuple[str, str, float], ...] = (
    ("signs", "antisigns", 1.0),
    ("houses", "antihouses", 1.0),
    ("bodies", "antibodies", 1.0),
    ("nakshatras", "antinakshatras", 1.0),
    ("positions", "antipositions", 1.0),
    ("aspects", "antiaspects", 1.0),
    ("gates", "antigates", 6.0),
)
_MATCH_ONCE_PREDICTOR_CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("hdtypes", "antihdtypes"),
    ("centers", "anticenters"),
    ("profiles", "antiprofiles"),
    ("authorities", "antiauthorities"),
    ("bazisigns", "antibazisigns"),
)


def _to_dnd_stat(raw_score: float, floor: int = 5, ceiling: int = 20) -> int:
    """Map a normalized predictor score onto the D&D 5-20 ability range.

    The midpoint is intentionally anchored at 11 so ordinary predictions land in
    the requested "Average" band of 10-12. Scores below the midpoint spend the
    smaller 5-11 span, while scores above it spend the larger 11-20 span. That
    keeps below-average stats visibly below 10, lets strong outliers reach 20,
    and avoids inflating middling raw scores into heroic 14-16 results.
    """
    raw_score = _clamp01(raw_score)
    midpoint = 0.5
    average_anchor = floor + round((ceiling - floor) * 0.40)
    if raw_score <= midpoint:
        lower_ratio = raw_score / midpoint
        stat_value = floor + lower_ratio * (average_anchor - floor)
    else:
        upper_ratio = (raw_score - midpoint) / midpoint
        stat_value = average_anchor + upper_ratio * (ceiling - average_anchor)
    return int(round(max(floor, min(ceiling, stat_value))))


def _criterion_weights(values: Any) -> list[float]:
    if isinstance(values, Mapping):
        raw_entries = values.values()
    else:
        raw_entries = (1.0 for _value in (values or ()))
    weights: list[float] = []
    for raw_weight in raw_entries:
        try:
            weights.append(abs(float(raw_weight)))
        except (TypeError, ValueError):
            weights.append(1.0)
    return weights


def _median(values: list[float]) -> float:
    if not values:
        return 1.0
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0


def _calculate_predictor_criteria_budgets(
    predictors: Mapping[str, Mapping[str, Any]],
) -> Dict[str, float]:
    """Estimate each stat's potential evidence volume from its criteria.

    The weighted predictor scorer already averages within many categories, but
    D&D stats have wildly different category coverage: WIS currently has only a
    few sign criteria while STR/DEX/CHA have signs, houses, positions, aspects,
    gates, profiles, and more. This budget lets the stat calculator compare raw
    signed evidence against the amount of evidence a stat could reasonably have
    produced instead of treating every raw point as equally meaningful.
    """
    budgets: Dict[str, float] = {}
    for stat_key, raw_factors in predictors.items():
        factors = raw_factors if isinstance(raw_factors, Mapping) else {}
        budget = 0.0
        for positive_key, negative_key, multiplier in _WEIGHT_NORMALIZED_PREDICTOR_CATEGORIES:
            positive_weights = _criterion_weights(factors.get(positive_key, ()))
            negative_weights = _criterion_weights(factors.get(negative_key, ()))
            criteria_count = len(positive_weights) + len(negative_weights)
            if criteria_count <= 0:
                continue
            positive_budget = sum(positive_weights) * multiplier
            negative_budget = sum(negative_weights) * multiplier
            budget += max(positive_budget, negative_budget) / criteria_count
        for positive_key, negative_key in _MATCH_ONCE_PREDICTOR_CATEGORIES:
            weights = [
                *_criterion_weights(factors.get(positive_key, ())),
                *_criterion_weights(factors.get(negative_key, ())),
            ]
            if weights:
                budget += max(weights)
        budgets[str(stat_key)] = max(0.0, budget)
    return budgets


def _calculate_stat_evidence_denominators(
    predictors: Mapping[str, Mapping[str, Any]],
) -> Dict[str, float]:
    """Calculate per-stat denominators that normalize uneven criteria coverage."""
    budgets = _calculate_predictor_criteria_budgets(predictors)
    typical_budget = max(1.0, _median([budget for budget in budgets.values() if budget > 0.0]))
    denominators: Dict[str, float] = {}
    for stat_key, budget in budgets.items():
        if budget <= 0.0:
            denominators[stat_key] = typical_budget
        elif budget < typical_budget:
            denominators[stat_key] = (budget * typical_budget) ** 0.5
        else:
            denominators[stat_key] = budget
    return denominators


def _normalize_weighted_stat_scores(
    raw_scores: Mapping[str, float],
    evidence_denominators: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Convert weighted predictor evidence to stable 0..1 stat scores.

    D&D stat predictors already return signed evidence: positive values mean a
    chart matched more pro-stat criteria, negative values mean it matched more
    anti-stat criteria, and zero means neutral/ordinary evidence. The old path
    normalized each chart's six stats by that chart's min and max, which forced
    every chart to have at least one floor stat and one ceiling stat even when
    the evidence gap was small.

    This absolute tanh calibration keeps neutral evidence at the average anchor
    (0.5), reserves the 5/20 bounds for exceptional evidence, and avoids
    manufacturing CHA 5 / WIS 11 / several-20 profiles from ordinary weighted
    predictor matches. When per-stat denominators are supplied, raw evidence is
    first divided by the stat's criteria budget so stats with dozens of criteria
    are comparable to stats with sparse criteria.
    """
    normalized: Dict[str, float] = {}
    for key, value in raw_scores.items():
        raw_value = float(value)
        if evidence_denominators is None:
            calibrated_evidence = raw_value / 24.0
        else:
            denominator = max(1e-9, float(evidence_denominators.get(key, 1.0)))
            calibrated_evidence = raw_value / denominator
        normalized[key] = _clamp01(0.5 + (0.5 * math.tanh(calibrated_evidence)))
    return normalized


def score_dnd_statblock(
    chart: Any,
    *,
    stat_floor: int = 5,
    stat_ceiling: int = 20,
) -> DnDStatBlock:
    """Score D&D stats using the shared multi-criterion chart predictor model."""
    raw_weighted_scores = calculate_weighted_criteria_scores(
        chart,
        predictors=DND_STAT_PREDICTORS,
    )
    raw_scores = _normalize_weighted_stat_scores(
        {key: float(raw_weighted_scores.get(key, 0.0)) for key in _DND_STAT_COMPONENT_ORDER},
        evidence_denominators=_calculate_stat_evidence_denominators(DND_STAT_PREDICTORS),
    )
    scores = {
        key: _to_dnd_stat(raw_scores[key], floor=stat_floor, ceiling=stat_ceiling)
        for key in _DND_STAT_COMPONENT_ORDER
    }
    modifiers = {key: int((value - 10) // 2) for key, value in scores.items()}
    return DnDStatBlock(raw_scores=raw_scores, scores=scores, modifiers=modifiers)


def build_dnd_statblock_profile_lines(
    statblock: DnDStatBlock,
    *,
    bar_width: int = 18,
    floor: int = 5,
    ceiling: int = 20,
) -> list[str]:
    span = max(1, ceiling - floor)
    lines: list[str] = []
    stat_label_width = max(len(label) for label in _DND_STAT_DISPLAY_LABELS.values())
    for stat_key in _DND_STAT_DISPLAY_ORDER:
        stat_value = int(statblock.scores.get(stat_key, floor))
        normalized_percent = max(0.0, min(100.0, ((stat_value - floor) / span) * 100.0))
        bar = _build_axis_score_bar(normalized_percent, 0.0, width=bar_width)
        modifier = int(statblock.modifiers.get(stat_key, 0))
        stat_label = _build_right_justified_label(_DND_STAT_DISPLAY_LABELS[stat_key], stat_label_width)
        lines.append(
            f"‣ {stat_label}: {stat_value:>2d} [{bar}] mod {modifier:+d}"
        )
    return lines
