from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Tuple

from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores
from .dnd_definitions import DND_STAT_PREDICTORS

from .dnd_class_axes_v2 import (
    AxisFeatureSet,
    ClassAxisScorer,
    DnDStatBlock,
    _build_axis_score_bar,
    _build_right_justified_label,
    _clamp01,
    validate_axis_scores,
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
_DND_SIGN_STAT_EFFECTS: Dict[str, Dict[str, str]] = {
    "Aries": {"major": "DEX", "minor": "INT", "nerf": "WIS"},
    "Taurus": {"major": "CON", "minor": "CHA", "nerf": "DEX"},
    "Gemini": {"major": "INT", "minor": "CHA", "nerf": "CON"},
    "Cancer": {"major": "CON", "minor": "WIS", "nerf": "DEX"},
    "Leo": {"major": "CHA", "minor": "STR", "nerf": "WIS"},
    "Virgo": {"major": "DEX", "minor": "STR", "nerf": "CHA"},
    "Libra": {"major": "CHA", "minor": "DEX", "nerf": "STR"},
    "Scorpio": {"major": "WIS", "minor": "CON", "nerf": "CHA"},
    "Sagittarius": {"major": "STR", "minor": "DEX", "nerf": "INT"},
    "Capricorn": {"major": "STR", "minor": "CON", "nerf": "INT"},
    "Aquarius": {"major": "INT", "minor": "WIS", "nerf": "STR"},
    "Pisces": {"major": "WIS", "minor": "INT", "nerf": "CON"},
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


def _shape_stat_profile(
    raw_scores: Mapping[str, float],
    dominant_sign_weights: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Apply sign flavor bonuses without amplifying the whole stat spread."""
    values = {key: _clamp01(value) for key, value in raw_scores.items()}
    if dominant_sign_weights:
        for sign_name, sign_weight in dominant_sign_weights.items():
            sign_key = str(sign_name).strip().title()
            effect = _DND_SIGN_STAT_EFFECTS.get(sign_key)
            if effect is None:
                continue
            weight = max(0.0, float(sign_weight))
            major_key = effect["major"]
            minor_key = effect["minor"]
            major_value = values.get(major_key, 0.0)
            minor_value = values.get(minor_key, 0.0)
            values[major_key] = _clamp01(major_value + ((1.0 - major_value) * 0.10 * weight))
            values[minor_key] = _clamp01(minor_value + ((1.0 - minor_value) * 0.05 * weight))
            # Temporarily disabling sign-based nerfs per product direction.
    return values


def score_dnd_statblock_from_features(
    axis_scores: Mapping[str, float],
    features: AxisFeatureSet,
    *,
    stat_floor: int = 5,
    stat_ceiling: int = 20,
    dominant_sign_weights: Optional[Mapping[str, float]] = None,
) -> DnDStatBlock:
    validate_axis_scores(axis_scores)
    p = features.planet_prominence
    e = features.element_balance
    m = features.mode_balance
    h = features.house_emphasis
    raw_scores: Dict[str, float] = {
        "STR": _clamp01(
            0.40 * axis_scores["frontline_courage"]
            + 0.22 * axis_scores["instinct"]
            #+ 0.14 * axis_scores["discipline"] #strength isn't discipline
            + 0.08 * p.get("Mars", 0.0)
            + 0.06 * p.get("Sun", 0.0)
            + 0.05 * h.get("self", 0.0)
            + 0.05 * ((e.get("Fire", 0.0) + e.get("Earth", 0.0)) / 2.0)
        ),
        "DEX": _clamp01(
            0.32 * axis_scores["stealth_indirection"]
            + 0.20 * axis_scores["control_planning"]
            #+ 0.16 * axis_scores["risk_appetite"] #being dextrous isn't cowardice
            + 0.10 * p.get("Mercury", 0.0)
            + 0.08 * p.get("Uranus", 0.0)
            + 0.07 * e.get("Air", 0.0)
            + 0.07 * m.get("mutable", 0.0)
        ),
        "CON": _clamp01(
            0.28 * axis_scores["discipline"]
            + 0.20 * axis_scores["instinct"]
            + 0.16 * axis_scores["mercy_restoration"] #how well you bounce back
            #+ 0.12 * p.get("Saturn", 0.0) #depends how saturn is aspected!! could be antithetical!
            #+ 0.08 * p.get("Moon", 0.0) #depends how moon is aspected & in what sign & house!
            + 0.08 * e.get("Earth", 0.0)
            + 0.08 * m.get("fixed", 0.0)
        ),
        "INT": _clamp01(
            0.36 * axis_scores["study"]
            + 0.20 * axis_scores["technical_inventiveness"]
            + 0.16 * axis_scores["control_planning"]
            + 0.12 * p.get("Mercury", 0.0)
            + 0.08 * p.get("Saturn", 0.0) 
            #many genius scientists are taurus, followed by aries, pisces & aquarius
            + 0.08 * h.get("craft", 0.0)
        ),
        "WIS": _clamp01(
            0.24 * axis_scores["nature_attunement"]
            #+ 0.28 * axis_scores["faith"] #don't mistake faith for wisdom...
            + 0.18 * axis_scores["instinct"]
            + 0.12 * axis_scores["mercy_restoration"]
            + 0.08 * p.get("Moon", 0.0) #depends how it's aspected
            + 0.05 * p.get("Jupiter", 0.0) #depends how it's aspected
            + 0.05 * ((h.get("wild", 0.0) + h.get("meaning", 0.0)) / 2.0)
        ),
        "CHA": _clamp01(
            0.32 * axis_scores["social_leadership"]
            + 0.24 * axis_scores["performance"]
            + 0.18 * axis_scores["innate_power"]
            + 0.10 * p.get("Sun", 0.0)
            + 0.08 * p.get("Venus", 0.0) #depends on aspects
            + 0.08 * h.get("social", 0.0)
            #subtract Saturn weight if negatively aspected
        ),
    }

    normalized_sign_weights = ClassAxisScorer._normalize_numeric_map(dominant_sign_weights or {})
    raw_scores = _shape_stat_profile(raw_scores, dominant_sign_weights=normalized_sign_weights)
    scores = {
        key: _to_dnd_stat(raw_scores[key], floor=stat_floor, ceiling=stat_ceiling)
        for key in _DND_STAT_COMPONENT_ORDER
    }
    modifiers = {key: int((value - 10) // 2) for key, value in scores.items()}
    return DnDStatBlock(raw_scores=raw_scores, scores=scores, modifiers=modifiers)


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
