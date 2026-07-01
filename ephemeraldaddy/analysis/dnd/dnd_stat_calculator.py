from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ephemeraldaddy.analysis.weighted_chart_predictor import (
    calculate_weighted_criteria_scores,
    weighted_channel_entries,
    weighted_gate_entries,
    weighted_position_entries,
)
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
    ("channels", "antichannels", 6.0),
)
_MATCH_ONCE_PREDICTOR_CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("hdtypes", "antihdtypes"),
    ("centers", "anticenters"),
    ("profiles", "antiprofiles"),
    ("authorities", "antiauthorities"),
    ("bazisigns", "antibazisigns"),
)
# Keep criteria-volume normalization from flattening real evidence. A full
# criteria budget is useful for comparing sparse vs. broad stat predictors, but
# using that budget as the direct tanh divisor compresses normal matched
# evidence into the 10-12 band. This scale preserves budget balancing while
# letting clear positive/negative evidence produce visibly distinct stats.
_EVIDENCE_DENOMINATOR_SCALE = 0.4

_DND_AVERAGE_STAT_ANCHOR = 11.0


def _to_dnd_stat_from_db_norm(
    chart_value: float,
    db_average: float,
    *,
    floor: int = 5,
    ceiling: int = 20,
) -> int:
    """Map a chart stat to D&D terms by direct ratio to the DB average.

    The database norm is the anchor: whatever average value the database has for
    a stat is treated as D&D 11. The chart value then moves up or down by the
    exact same percentage deviation from that norm. No per-chart min/max, tanh,
    or criteria-budget normalization is applied to this DB-relative path.
    """
    try:
        norm = float(db_average)
        value = float(chart_value)
    except (TypeError, ValueError):
        return int(round(_DND_AVERAGE_STAT_ANCHOR))
    if not math.isfinite(norm) or abs(norm) <= 1e-9 or not math.isfinite(value):
        return int(round(_DND_AVERAGE_STAT_ANCHOR))
    stat_value = _DND_AVERAGE_STAT_ANCHOR * (value / norm)
    return int(math.floor(max(floor, min(ceiling, stat_value)) + 0.5))


def _calculate_db_norm_stat_averages(norm_charts: Iterable[Any] | None) -> Dict[str, float]:
    totals = {key: 0.0 for key in _DND_STAT_COMPONENT_ORDER}
    count = 0
    for norm_chart in norm_charts or ():
        raw_weighted_scores = calculate_weighted_criteria_scores(
            norm_chart,
            predictors=DND_STAT_PREDICTORS,
        )
        for key in _DND_STAT_COMPONENT_ORDER:
            totals[key] += float(raw_weighted_scores.get(key, 0.0))
        count += 1
    if count <= 0:
        return {}
    return {key: totals[key] / float(count) for key in _DND_STAT_COMPONENT_ORDER}


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


def _criterion_weights_for_category(category: str, values: Any) -> list[float]:
    if category in {"positions", "antipositions"}:
        return [abs(float(weight)) for weight in weighted_position_entries(values).values()]
    if category in {"gates", "antigates"}:
        return [abs(float(weight)) for weight in weighted_gate_entries(values).values()]
    if category in {"channels", "antichannels"}:
        return [abs(float(weight)) for weight in weighted_channel_entries(values).values()]
    return _criterion_weights(values)


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
            positive_weights = _criterion_weights_for_category(positive_key, factors.get(positive_key, ()))
            negative_weights = _criterion_weights_for_category(negative_key, factors.get(negative_key, ()))
            criteria_count = len(positive_weights) + len(negative_weights)
            if criteria_count <= 0:
                continue
            positive_budget = sum(positive_weights) * multiplier
            negative_budget = sum(negative_weights) * multiplier
            budget += max(positive_budget, negative_budget) / criteria_count
        for positive_key, negative_key in _MATCH_ONCE_PREDICTOR_CATEGORIES:
            weights = [
                *_criterion_weights_for_category(positive_key, factors.get(positive_key, ())),
                *_criterion_weights_for_category(negative_key, factors.get(negative_key, ())),
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
    first divided by a scaled criteria budget so stats with dozens of criteria
    are comparable to stats with sparse criteria without compressing real
    evidence into an overly flat 10-12 profile.
    """
    normalized: Dict[str, float] = {}
    for key, value in raw_scores.items():
        raw_value = float(value)
        if evidence_denominators is None:
            calibrated_evidence = raw_value / 24.0
        else:
            denominator = max(1e-9, float(evidence_denominators.get(key, 1.0)))
            calibrated_evidence = raw_value / (denominator * _EVIDENCE_DENOMINATOR_SCALE)
        normalized[key] = _clamp01(0.5 + (0.5 * math.tanh(calibrated_evidence)))
    return normalized


def score_dnd_statblock(
    chart: Any,
    *,
    stat_floor: int = 5,
    stat_ceiling: int = 20,
    norm_charts: Iterable[Any] | None = None,
) -> DnDStatBlock:
    """Score D&D stats using direct DB-relative stat ratios when norms exist."""
    raw_weighted_scores = calculate_weighted_criteria_scores(
        chart,
        predictors=DND_STAT_PREDICTORS,
    )
    chart_raw_scores = {key: float(raw_weighted_scores.get(key, 0.0)) for key in _DND_STAT_COMPONENT_ORDER}
    db_norm_averages = _calculate_db_norm_stat_averages(norm_charts)
    if db_norm_averages:
        raw_scores = chart_raw_scores
        scores = {
            key: _to_dnd_stat_from_db_norm(
                chart_raw_scores[key],
                db_norm_averages.get(key, 0.0),
                floor=stat_floor,
                ceiling=stat_ceiling,
            )
            for key in _DND_STAT_COMPONENT_ORDER
        }
    else:
        raw_scores = _normalize_weighted_stat_scores(
            chart_raw_scores,
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
