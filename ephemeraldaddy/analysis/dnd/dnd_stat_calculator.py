from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from ephemeraldaddy.analysis.weighted_chart_predictor import (
    calculate_weighted_criteria_scores,
    normalize_weight_map_by_range,
)
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


def _shape_stat_profile(
    raw_scores: Mapping[str, float],
    dominant_sign_weights: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    values = {key: _clamp01(value) for key, value in raw_scores.items()}
    if dominant_sign_weights:
        for sign_name, sign_weight in dominant_sign_weights.items():
            sign_key = str(sign_name).strip().title()
            effect = _DND_SIGN_STAT_EFFECTS.get(sign_key)
            if effect is None:
                continue
            weight = max(0.0, float(sign_weight))
            values[effect["major"]] = _clamp01(values.get(effect["major"], 0.0) + (0.30 * weight))
            values[effect["minor"]] = _clamp01(values.get(effect["minor"], 0.0) + (0.14 * weight))
            # Temporarily disabling sign-based nerfs per product direction.

    mean = sum(values.values()) / max(1, len(values))
    variance = sum((value - mean) ** 2 for value in values.values()) / max(1, len(values))
    std_dev = variance ** 0.5
    contrast_factor = max(1.20, min(2.10, 1.52 + max(0.0, 0.20 - std_dev) * 3.2))
    shaped: Dict[str, float] = {}
    for key, value in values.items():
        shaped[key] = _clamp01(mean + ((value - mean) * contrast_factor))
    return shaped


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
    normalized_scores = normalize_weight_map_by_range(raw_weighted_scores)
    raw_scores = {
        key: _clamp01(float(normalized_scores.get(key, 0.0)))
        for key in _DND_STAT_COMPONENT_ORDER
    }
    raw_scores = _shape_stat_profile(raw_scores)
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
