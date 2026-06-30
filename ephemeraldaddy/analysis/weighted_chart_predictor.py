"""Reusable multi-criterion weighted chart prediction helpers.

This module generalizes the Enneagram prediction scoring model so other
prediction systems can score chart targets from the same weighted criteria
shape (signs/antisigns, bodies/antibodies, positions/antipositions, etc.).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ephemeraldaddy.analysis.bazi_getter import (
    bazi_sign_weights_from_chart,
    normalize_bazi_sign_value,
)
from ephemeraldaddy.core.aspects import ASPECT_DEFS
from ephemeraldaddy.core.chart import chart_uses_houses as default_chart_uses_houses
from ephemeraldaddy.core.interpretations import (
    ASPECT_SCORE_WEIGHTS,
    OPPOSITE_SIGNS,
    PLANET_ORDER,
    ZODIAC_NAMES,
    normalize_body_name,
)

BODY_ALIASES = {
    "fortune": "Part of Fortune",
    "part of fortune": "Part of Fortune",
    "true lilith": "Lilith",
    "lilith": "Lilith",
}

HD_TYPE_ALIASES = {
    "manifestinggenerator": "manifesting_generator",
    "manifesting_generator": "manifesting_generator",
    "mfgenerator": "manifesting_generator",
    "mf_generator": "manifesting_generator",
    "mg": "manifesting_generator",
    "generator": "generator",
    "manifestor": "manifestor",
    "projector": "projector",
    "reflector": "reflector",
}
HD_CENTER_ALIASES = {
    "head": "Head",
    "ajna": "Ajna",
    "throat": "Throat",
    "g": "G",
    "gcenter": "G",
    "identity": "G",
    "identitycenter": "G",
    "ego": "Ego",
    "heart": "Ego",
    "heartcenter": "Ego",
    "will": "Ego",
    "willcenter": "Ego",
    "spleen": "Spleen",
    "splenic": "Spleen",
    "sacral": "Sacral",
    "root": "Root",
    "solarplexus": "Solar Plexus",
    "emotional": "Solar Plexus",
    "emotionalcenter": "Solar Plexus",
}
HD_AUTHORITY_ALIASES = {
    "no_inner_authority": "lunar",
    "mental_environmental_sounding_board": "mental",
    "environmental_sounding_board": "mental",
    "sounding_board": "mental",
}
CANONICAL_FACTOR_NAMES = tuple(dict.fromkeys([*PLANET_ORDER, *ZODIAC_NAMES, "AS", "DS", "IC", "MC"]))
CANONICAL_FACTOR_LOOKUP = {name.casefold(): name for name in CANONICAL_FACTOR_NAMES}


def sign_for_longitude(lon: float) -> str:
    sign_index = int((lon % 360.0) // 30) % 12
    return ZODIAC_NAMES[sign_index]


def house_for_longitude(cusps: list[float] | None, lon: float) -> int | None:
    if not cusps or len(cusps) < 12:
        return None
    lon = lon % 360.0
    for index in range(12):
        start = cusps[index] % 360.0
        end = cusps[(index + 1) % 12] % 360.0
        if end <= start:
            end += 360.0
        check_lon = lon
        if check_lon < start:
            check_lon += 360.0
        if start <= check_lon < end:
            return index + 1
    return None


def calculate_dominant_sign_weights(chart: Any) -> Mapping[str, float]:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_sign_weights as _calculate

    return _calculate(chart)


def calculate_dominant_planet_weights(chart: Any) -> Mapping[str, float]:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_planet_weights as _calculate

    return _calculate(chart)


def calculate_dominant_house_weights(chart: Any) -> Mapping[int, float]:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_house_weights as _calculate

    return _calculate(chart)


def calculate_dominant_nakshatra_weights(chart: Any) -> Mapping[str, float]:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_nakshatra_weights as _calculate

    return _calculate(chart)



TYPE_SIGNATURE_SCALE_NONE = "none"
TYPE_SIGNATURE_SCALE_LOG = "log"
TYPE_SIGNATURE_SCALE_SQRT = "sqrt"
TYPE_SIGNATURE_SCALE_FULL = "full"
TYPE_SIGNATURE_SCALE_MODES = {
    TYPE_SIGNATURE_SCALE_NONE,
    TYPE_SIGNATURE_SCALE_LOG,
    TYPE_SIGNATURE_SCALE_SQRT,
    TYPE_SIGNATURE_SCALE_FULL,
}
DOMINANCE_NORMALIZATION_RANGE = "range"
DOMINANCE_NORMALIZATION_SHARE = "share"
DOMINANCE_NORMALIZATION_MODES = {
    DOMINANCE_NORMALIZATION_RANGE,
    DOMINANCE_NORMALIZATION_SHARE,
}
PREDICTION_SCORE_MODE_RAW = "raw"
PREDICTION_SCORE_MODE_OPPORTUNITY = "opportunity"
PREDICTION_SCORE_MODE_BACKGROUND_Z = "background_z"
PREDICTION_SCORE_MODE_CATEGORY_Z = "category_z"
PREDICTION_SCORE_MODES = {
    PREDICTION_SCORE_MODE_RAW,
    PREDICTION_SCORE_MODE_OPPORTUNITY,
    PREDICTION_SCORE_MODE_BACKGROUND_Z,
    PREDICTION_SCORE_MODE_CATEGORY_Z,
}


@dataclass(frozen=True)
class WeightedPredictorScoringOptions:
    """Runtime switches for experimental weighted predictor scoring behavior."""

    use_direct_dominance_activation: bool = True
    use_position_dominance_weighting: bool = True
    use_aspect_dominance_weighting: bool = True
    simplify_anti_factor_handling: bool = True
    average_scores_by_criterion_count: bool = True
    type_signature_scale_mode: str = TYPE_SIGNATURE_SCALE_NONE
    score_mode: str = PREDICTION_SCORE_MODE_OPPORTUNITY
    dominance_normalization_mode: str = DOMINANCE_NORMALIZATION_RANGE
    use_mutual_exclusive_bucket_scoring: bool = True
    human_design_activation_weight: float = 1.0

    def normalized_type_signature_scale_mode(self) -> str:
        mode = str(self.type_signature_scale_mode or TYPE_SIGNATURE_SCALE_NONE).strip().lower()
        return mode if mode in TYPE_SIGNATURE_SCALE_MODES else TYPE_SIGNATURE_SCALE_NONE

    def normalized_score_mode(self) -> str:
        mode = str(self.score_mode or PREDICTION_SCORE_MODE_OPPORTUNITY).strip().lower()
        return mode if mode in PREDICTION_SCORE_MODES else PREDICTION_SCORE_MODE_OPPORTUNITY

    def normalized_dominance_normalization_mode(self) -> str:
        mode = str(self.dominance_normalization_mode or DOMINANCE_NORMALIZATION_RANGE).strip().lower()
        return mode if mode in DOMINANCE_NORMALIZATION_MODES else DOMINANCE_NORMALIZATION_RANGE


BASELINE_DEFAULT_SCORING_OPTIONS = WeightedPredictorScoringOptions(simplify_anti_factor_handling=False)
DEFAULT_SCORING_OPTIONS = BASELINE_DEFAULT_SCORING_OPTIONS


def set_default_scoring_options(overrides: WeightedPredictorScoringOptions | Mapping[str, Any] | None) -> None:
    """Set process-wide scoring options for shared Predictions scorers."""
    global DEFAULT_SCORING_OPTIONS
    if overrides is None:
        DEFAULT_SCORING_OPTIONS = BASELINE_DEFAULT_SCORING_OPTIONS
        return
    DEFAULT_SCORING_OPTIONS = coerce_scoring_options(overrides)


def coerce_scoring_options(value: WeightedPredictorScoringOptions | Mapping[str, Any] | None) -> WeightedPredictorScoringOptions:
    if isinstance(value, WeightedPredictorScoringOptions):
        return value
    if not isinstance(value, Mapping):
        return DEFAULT_SCORING_OPTIONS

    def _bool(key: str, fallback: bool) -> bool:
        raw = value.get(key, fallback)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        if isinstance(raw, (int, float)):
            return bool(raw)
        return fallback

    def _float(key: str, fallback: float) -> float:
        raw = value.get(key, fallback)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return fallback

    return WeightedPredictorScoringOptions(
        use_direct_dominance_activation=_bool("use_direct_dominance_activation", True),
        use_position_dominance_weighting=_bool("use_position_dominance_weighting", True),
        use_aspect_dominance_weighting=_bool("use_aspect_dominance_weighting", True),
        simplify_anti_factor_handling=_bool("simplify_anti_factor_handling", True),
        average_scores_by_criterion_count=_bool("average_scores_by_criterion_count", True),
        type_signature_scale_mode=str(value.get("type_signature_scale_mode", TYPE_SIGNATURE_SCALE_NONE) or TYPE_SIGNATURE_SCALE_NONE),
        score_mode=str(value.get("score_mode", PREDICTION_SCORE_MODE_OPPORTUNITY) or PREDICTION_SCORE_MODE_OPPORTUNITY),
        dominance_normalization_mode=str(value.get("dominance_normalization_mode", DOMINANCE_NORMALIZATION_RANGE) or DOMINANCE_NORMALIZATION_RANGE),
        use_mutual_exclusive_bucket_scoring=_bool("use_mutual_exclusive_bucket_scoring", True),
        human_design_activation_weight=_float("human_design_activation_weight", 1.0),
    )


def _z_score(value: float, stats: Mapping[str, Any] | None) -> float:
    if not isinstance(stats, Mapping):
        return value
    try:
        mean = float(stats.get("mean", 0.0))
        stddev = float(stats.get("stddev", stats.get("stdev", 0.0)))
    except (TypeError, ValueError):
        return value
    return (value - mean) / stddev if stddev > 0 else value


def _apply_type_signature_scale(score: float, total_abs_weight: float, mode: str) -> float:
    if total_abs_weight <= 0:
        return score
    if mode == TYPE_SIGNATURE_SCALE_LOG:
        denominator = math.log1p(total_abs_weight)
    elif mode == TYPE_SIGNATURE_SCALE_SQRT:
        denominator = math.sqrt(total_abs_weight)
    elif mode == TYPE_SIGNATURE_SCALE_FULL:
        denominator = total_abs_weight
    else:
        return score
    return score / denominator if denominator > 0 else score

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "signs": 1.0,
    "bodies": 1.0,
    "nakshatras": 1.0,
    "houses": 1.0,
    "gates": 1.0,
    "channels": 1.0,
    "hdtypes": 1.0,
    "centers": 1.0,
    "profiles": 1.0,
    "authorities": 1.0,
    "bazisigns": 1.0,
    "positions": 1.0,
    "aspects": 1.0,
}
DEFAULT_CRITERION_MULTIPLIER = 1.0
DEFAULT_ANTI_FACTOR = 1.0


def normalize_weight_map_by_range(raw_weights: Mapping[Any, float] | None) -> dict[Any, float]:
    """Normalize arbitrary numeric weights to the 0..1 range."""
    if not raw_weights:
        return {}
    cleaned: dict[Any, float] = {}
    for key, raw_value in raw_weights.items():
        try:
            cleaned[key] = float(raw_value)
        except (TypeError, ValueError):
            cleaned[key] = 0.0
    values = list(cleaned.values())
    max_value = max(values)
    min_value = min(values)
    range_value = max_value - min_value
    if range_value <= 0:
        return {key: 0.0 for key in cleaned}
    return {key: (value - min_value) / range_value for key, value in cleaned.items()}


def normalize_weight_map_by_share(raw_weights: Mapping[Any, float] | None) -> dict[Any, float]:
    """Normalize arbitrary numeric weights as non-negative shares of total weight."""
    if not raw_weights:
        return {}
    cleaned: dict[Any, float] = {}
    for key, raw_value in raw_weights.items():
        try:
            cleaned[key] = max(0.0, float(raw_value))
        except (TypeError, ValueError):
            cleaned[key] = 0.0
    total = sum(cleaned.values())
    if total <= 0.0:
        return {key: 0.0 for key in cleaned}
    return {key: value / total for key, value in cleaned.items()}


def normalize_weight_map_for_dominance_activation(
    raw_weights: Mapping[Any, float] | None,
    mode: str,
) -> dict[Any, float]:
    """Normalize dominance activations according to weighted predictor settings."""
    if str(mode or DOMINANCE_NORMALIZATION_RANGE).strip().lower() == DOMINANCE_NORMALIZATION_SHARE:
        return normalize_weight_map_by_share(raw_weights)
    return normalize_weight_map_by_range(raw_weights)


def normalize_factor_value(value: str) -> str:
    """Normalize body/sign/axis aliases used by weighted criteria definitions."""
    token = str(value or "").strip()
    canonical_alias = BODY_ALIASES.get(token.lower())
    if canonical_alias:
        return canonical_alias
    canonical_from_lookup = CANONICAL_FACTOR_LOOKUP.get(token.casefold())
    if canonical_from_lookup:
        return canonical_from_lookup
    normalized = normalize_body_name(token)
    if normalized:
        normalized_lookup = CANONICAL_FACTOR_LOOKUP.get(str(normalized).casefold())
        if normalized_lookup:
            return normalized_lookup
        return str(normalized)
    return token


def normalize_string_set(values: Any) -> set[str]:
    return {
        normalize_factor_value(str(value).strip())
        for value in values or set()
        if str(value).strip()
    }


def normalize_house_set(values: Any) -> set[int]:
    return {
        int(house_num)
        for house_num in values or set()
        if str(house_num).strip().isdigit() and 1 <= int(house_num) <= 12
    }


def normalize_gate_set(values: Any) -> set[int]:
    return {
        int(gate_num)
        for gate_num in values or set()
        if str(gate_num).strip().isdigit() and 1 <= int(gate_num) <= 64
    }


def coerce_weighted_entries(values: Any) -> dict[Any, float]:
    """Accept either {criterion: weight} mappings or iterables of criteria."""
    weighted: dict[Any, float] = {}
    source = values.items() if isinstance(values, Mapping) else ((value, 1.0) for value in (values or []))
    for key, raw_weight in source:
        if key is None:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 1.0
        weighted[key] = weight
    return weighted


def weighted_string_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_factor_value(str(raw_value).strip())
        if token:
            entries[token] = weight
    return entries


def weighted_house_entries(values: Any) -> dict[int, float]:
    entries: dict[int, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = str(raw_value).strip()
        if token.isdigit() and 1 <= int(token) <= 12:
            entries[int(token)] = weight
    return entries


def weighted_gate_entries(values: Any) -> dict[int, float]:
    entries: dict[int, float] = {}
    if isinstance(values, Mapping):
        source = values.items()
    else:
        source = ((value, 1.0) for value in (values or []))
    for raw_value, raw_weight in source:
        try:
            gate_num = int(str(raw_value).strip())
        except (TypeError, ValueError):
            continue
        if not 1 <= abs(gate_num) <= 64:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 1.0
        if gate_num < 0 and not isinstance(values, Mapping):
            weight *= -1.0
        entries[abs(gate_num)] = weight
    return entries


def normalize_channel_value(value: Any) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        raw_gate_a, raw_gate_b = value
    else:
        match = re.fullmatch(r"\s*(\d{1,2})\s*[-/,]\s*(\d{1,2})\s*", str(value))
        if not match:
            return None
        raw_gate_a, raw_gate_b = match.groups()
    try:
        gate_a = int(raw_gate_a)
        gate_b = int(raw_gate_b)
    except (TypeError, ValueError):
        return None
    if not (1 <= gate_a <= 64 and 1 <= gate_b <= 64 and gate_a != gate_b):
        return None
    return (min(gate_a, gate_b), max(gate_a, gate_b))


def weighted_channel_entries(values: Any) -> dict[tuple[int, int], float]:
    entries: dict[tuple[int, int], float] = {}
    if isinstance(values, Mapping):
        source = values.items()
    else:
        source = ((value, 1.0) for value in (values or []))
    for raw_value, raw_weight in source:
        channel = normalize_channel_value(raw_value)
        if channel is None:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 1.0
        entries[channel] = weight
    return entries


def parse_house_token(token: str) -> int | None:
    match = re.fullmatch(r"H\s*(\d{1,2})", token.strip(), re.IGNORECASE)
    if not match:
        return None
    house_num = int(match.group(1))
    return house_num if 1 <= house_num <= 12 else None


def parse_position_spec(raw_spec: str) -> tuple[str, str | int, str] | None:
    parts = [part.strip() for part in str(raw_spec).split(" in ")]
    if len(parts) != 2:
        return None
    left, right = parts
    if not left or not right:
        return None
    right_house = parse_house_token(right)
    if right_house is not None:
        if left in ZODIAC_NAMES:
            return ("sign_in_house", right_house, left)
        return ("body_in_house", right_house, normalize_factor_value(left))
    if right in ZODIAC_NAMES:
        return ("body_in_sign", right, normalize_factor_value(left))
    return None


def parse_aspect_spec(raw_spec: str) -> tuple[str, str, str] | None:
    text = str(raw_spec).strip()
    if not text:
        return None
    aspect_pattern = "|".join(sorted(ASPECT_SCORE_WEIGHTS.keys(), key=len, reverse=True))
    match = re.fullmatch(rf"(.+?)\s+({aspect_pattern})\s+(.+)", text, re.IGNORECASE)
    if not match:
        return None
    left = normalize_factor_value(match.group(1).strip())
    aspect_type = match.group(2).strip().lower()
    right = normalize_factor_value(match.group(3).strip())
    if not left or not right:
        return None
    return (left, aspect_type, right)


def normalize_category_delta(
    positive_delta: float,
    negative_delta: float,
    *,
    criteria_count: int,
    anti_factor: float = DEFAULT_ANTI_FACTOR,
) -> float:
    if criteria_count <= 0:
        return 0.0
    return (positive_delta - (anti_factor * negative_delta)) / float(criteria_count)


def criterion_multiplier_for_target(target_factors: Mapping[str, Any], category: str) -> float:
    multipliers = target_factors.get("criterion_multipliers", {})
    if not isinstance(multipliers, Mapping):
        return DEFAULT_CRITERION_MULTIPLIER
    raw_value = multipliers.get(category, DEFAULT_CRITERION_MULTIPLIER)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_CRITERION_MULTIPLIER


def active_human_design_gates(chart: Any) -> set[int]:
    cached = {
        int(gate)
        for gate in (getattr(chart, "human_design_gates", None) or [])
        if str(gate).strip().isdigit() and 1 <= int(gate) <= 64
    }
    if cached:
        return cached
    try:
        from ephemeraldaddy.analysis.human_design import derive_human_design_profile

        gates, _lines, _channels, _hd_type = derive_human_design_profile(chart)
    except Exception:
        return set()
    return {int(gate) for gate in gates if 1 <= int(gate) <= 64}


def active_human_design_channels(chart: Any) -> set[tuple[int, int]]:
    cached = {
        channel
        for raw_channel in (getattr(chart, "human_design_channels", None) or [])
        if (channel := normalize_channel_value(raw_channel)) is not None
    }
    if cached:
        return cached
    try:
        from ephemeraldaddy.analysis.human_design import derive_human_design_profile

        _gates, _lines, channels, _hd_type = derive_human_design_profile(chart)
    except Exception:
        return set()
    return {
        channel
        for raw_channel in channels
        if (channel := normalize_channel_value(raw_channel)) is not None
    }


def _normalized_token_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def normalize_hd_type_value(value: Any) -> str:
    key = _normalized_token_key(value)
    compact_key = key.replace("_", "")
    return HD_TYPE_ALIASES.get(key) or HD_TYPE_ALIASES.get(compact_key, key)


def normalize_hd_center_value(value: Any) -> str:
    key = _normalized_token_key(value)
    compact_key = key.replace("_", "")
    return HD_CENTER_ALIASES.get(key) or HD_CENTER_ALIASES.get(compact_key, str(value).strip().title())


def normalize_hd_authority_value(value: Any) -> str:
    key = _normalized_token_key(value)
    normalized = HD_AUTHORITY_ALIASES.get(key, key)
    return normalized.replace("_", " ").title() if normalized else ""


def normalize_hd_profile_value(value: Any) -> str:
    text = str(value).strip().replace(" ", "")
    return text


def weighted_hd_type_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_hd_type_value(raw_value)
        if token:
            entries[token] = weight
    return entries


def weighted_hd_center_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_hd_center_value(raw_value)
        if token:
            entries[token] = weight
    return entries


def weighted_hd_profile_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_hd_profile_value(raw_value)
        if token:
            entries[token] = weight
    return entries


def weighted_hd_authority_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_hd_authority_value(raw_value)
        if token:
            entries[token] = weight
    return entries


def weighted_bazi_sign_entries(values: Any) -> dict[str, float]:
    entries: dict[str, float] = {}
    for raw_value, weight in coerce_weighted_entries(values).items():
        token = normalize_bazi_sign_value(raw_value)
        if token:
            entries[token] = weight
    return entries


def active_human_design_properties(chart: Any) -> tuple[str, set[str], str, str]:
    hd_type = normalize_hd_type_value(getattr(chart, "human_design_type", ""))
    centers = {
        normalize_hd_center_value(center)
        for center in (getattr(chart, "human_design_defined_centers", None) or [])
        if str(center).strip()
    }
    profile = normalize_hd_profile_value(getattr(chart, "human_design_profile", ""))
    authority = normalize_hd_authority_value(getattr(chart, "human_design_authority", ""))
    if hd_type and centers and profile and authority:
        return hd_type, centers, profile, authority

    from ephemeraldaddy.analysis.human_design import build_human_design_result

    try:
        hd_result = build_human_design_result(chart)
    except Exception:
        return hd_type, centers, profile, authority

    resolved_type = normalize_hd_type_value(getattr(hd_result, "hd_type", ""))
    resolved_centers = {
        normalize_hd_center_value(center)
        for center in getattr(hd_result, "defined_centers", [])
        if str(center).strip()
    }
    resolved_profile = normalize_hd_profile_value(getattr(hd_result, "profile", ""))
    resolved_authority = normalize_hd_authority_value(getattr(hd_result, "authority", ""))
    hd_type = resolved_type or hd_type
    centers = resolved_centers or centers
    profile = resolved_profile or profile
    authority = resolved_authority or authority
    return hd_type, centers, profile, authority


def active_bazi_sign_weights(chart: Any) -> dict[str, float]:
    try:
        return bazi_sign_weights_from_chart(chart)
    except Exception:
        return {}


def _weighted_text_entries(values: Any) -> dict[str, float]:
    return {
        str(value).strip(): float(weight)
        for value, weight in coerce_weighted_entries(values).items()
        if str(value).strip()
    }


def _is_numeric_weight(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _format_house_position_token(value: Any) -> str | None:
    token = str(value).strip()
    if not token:
        return None
    house_num = parse_house_token(token)
    if house_num is None and token.isdigit():
        house_num = int(token)
    if house_num is None or not 1 <= house_num <= 12:
        return None
    return f"H{house_num}"


def _position_destination_from_key(raw_key: Any, bucket: str | None = None) -> str | None:
    token = str(raw_key).strip()
    if not token:
        return None
    normalized_bucket = str(bucket or "").strip().casefold()
    if normalized_bucket in {"house", "houses", "h"}:
        return _format_house_position_token(token)
    if normalized_bucket in {"sign", "signs", "zodiac", "zodiacs"}:
        return token if token in ZODIAC_NAMES else None
    house_token = _format_house_position_token(token)
    if house_token is not None:
        return house_token
    return token if token in ZODIAC_NAMES else None


def _add_position_entry(entries: dict[str, float], subject: Any, destination: Any, raw_weight: Any, bucket: str | None = None) -> None:
    subject_text = normalize_factor_value(str(subject).strip())
    if not subject_text:
        return
    destination_text = _position_destination_from_key(destination, bucket)
    if destination_text is None:
        return
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError):
        weight = 1.0
    _set_position_entry_once(entries, f"{subject_text} in {destination_text}", weight)


def _opposite_sign(sign: str) -> str | None:
    if sign in OPPOSITE_SIGNS:
        return OPPOSITE_SIGNS[sign]
    for left, right in OPPOSITE_SIGNS.items():
        if right == sign:
            return left
    return None


def _opposite_house(house_num: int) -> int:
    return ((house_num + 5) % 12) + 1


def _canonical_position_equivalence_key(raw_spec: str) -> tuple[str, str | int, str] | None:
    """Return a canonical key for structural duplicate position predictors.

    Some predictor constants include both sides of the same chart axis, e.g.
    ``AS in Cancer`` and ``DS in Capricorn``. These are not independent
    opportunities to match a chart, so weighted position entries collapse them
    to one scoreable criterion while preserving the strongest supplied weight.
    """
    parsed = parse_position_spec(raw_spec)
    if parsed is None:
        return None
    category, container, subject = parsed

    if category == "body_in_sign" and isinstance(container, str):
        if subject == "AS":
            return ("sign_in_house", 1, container)
        if subject == "DS":
            return ("sign_in_house", 7, container)
        if subject == "MC":
            return ("sign_in_house", 10, container)
        if subject == "IC":
            return ("sign_in_house", 4, container)
        if subject == "Ketu":
            opposite = _opposite_sign(container)
            return ("body_in_sign", opposite, "Rahu") if opposite else parsed
        return parsed

    if category == "body_in_house" and isinstance(container, int):
        if subject == "DS":
            return ("body_in_house", _opposite_house(container), "AS")
        if subject == "IC":
            return ("body_in_house", _opposite_house(container), "MC")
        if subject == "Ketu":
            return ("body_in_house", _opposite_house(container), "Rahu")
        return parsed

    if category == "sign_in_house" and isinstance(container, int):
        # Prefer house-cusp positions as the canonical representation for
        # angle/sign structural duplicates. This keeps scoring/export criteria
        # in the user-facing house-position form (e.g. ``Aries in H10``) while
        # still collapsing equivalent angle labels such as ``MC in Aries``.
        if container in {1, 4, 7, 10}:
            return parsed
    return parsed


def canonical_position_equivalence_spec(raw_spec: str) -> str | None:
    """Return the preferred display/scoring spec for equivalent positions."""
    key = _canonical_position_equivalence_key(raw_spec)
    if key is None:
        return None
    return _canonical_position_spec_from_key(key, raw_spec)


def _canonical_position_spec_from_key(key: tuple[str, str | int, str], fallback: str) -> str:
    category, container, subject = key
    if category == "body_in_sign" and isinstance(container, str):
        return f"{subject} in {container}"
    if category == "body_in_house" and isinstance(container, int):
        return f"{subject} in H{container}"
    if category == "sign_in_house" and isinstance(container, int):
        return f"{subject} in H{container}"
    return fallback


def _set_position_entry_once(entries: dict[str, float], raw_spec: str, weight: float) -> None:
    key = _canonical_position_equivalence_key(raw_spec)
    canonical_spec = _canonical_position_spec_from_key(key, raw_spec) if key is not None else raw_spec
    previous = entries.get(canonical_spec)
    if previous is None or abs(float(weight)) > abs(float(previous)):
        entries[canonical_spec] = weight


def weighted_position_entries(values: Any) -> dict[str, float]:
    """Accept flat and nested position predictor criteria as equivalent.

    Supported shapes include:
    - {"Sun in Scorpio": 4, "Sun in H4": 6}
    - {"Sun": {"Scorpio": 4, "Aquarius": 3, "H4": 6}}
    - {"Sun": {"signs": {"Scorpio": 4}, "houses": {"H4": 6}}}
    - iterables such as {"Sun in Scorpio", "Moon in H8"}
    """
    entries: dict[str, float] = {}
    if isinstance(values, Mapping):
        for raw_subject, raw_value in values.items():
            subject_text = str(raw_subject).strip()
            if not subject_text:
                continue
            if _is_numeric_weight(raw_value):
                if parse_position_spec(subject_text) is not None:
                    _set_position_entry_once(entries, subject_text, float(raw_value))
                continue
            if not isinstance(raw_value, Mapping):
                continue
            for raw_destination, nested_value in raw_value.items():
                bucket_name = str(raw_destination).strip()
                if isinstance(nested_value, Mapping) and bucket_name.casefold() in {"sign", "signs", "house", "houses", "h"}:
                    for bucket_destination, bucket_weight in nested_value.items():
                        _add_position_entry(entries, subject_text, bucket_destination, bucket_weight, bucket_name)
                elif _is_numeric_weight(nested_value):
                    _add_position_entry(entries, subject_text, raw_destination, nested_value)
        return entries

    for raw_value, weight in coerce_weighted_entries(values).items():
        token = str(raw_value).strip()
        if token and parse_position_spec(token) is not None:
            _set_position_entry_once(entries, token, weight)
    return entries



def _bucketed_criteria_count_and_abs_weight(
    positive_entries: Mapping[Any, float],
    negative_entries: Mapping[Any, float],
    *,
    bucket_for_key: Callable[[Any], Any | None],
) -> tuple[int, float]:
    buckets: dict[Any, float] = {}
    for key, weight in [*positive_entries.items(), *negative_entries.items()]:
        bucket = bucket_for_key(key)
        if bucket is None:
            bucket = ("criterion", key)
        try:
            abs_weight = abs(float(weight))
        except (TypeError, ValueError):
            abs_weight = 1.0
        buckets[bucket] = max(buckets.get(bucket, 0.0), abs_weight)
    return len(buckets), sum(buckets.values())


def _singleton_position_bucket(raw_position: Any) -> tuple[str, Any] | None:
    parsed = parse_position_spec(str(raw_position))
    if parsed is None:
        return None
    category, container, subject = parsed
    if category == "body_in_sign":
        return ("body_sign", subject)
    if category == "body_in_house":
        return ("body_house", subject)
    if category == "sign_in_house":
        return ("house_sign", container)
    return None


def _one_bucket(_key: Any) -> tuple[str, str]:
    return ("singleton", "value")


def _has_any_predictor_criteria(predictors: Mapping[Any, Mapping[str, Any]], category_keys: set[str]) -> bool:
    for raw_factors in predictors.values():
        if not isinstance(raw_factors, Mapping):
            continue
        for key in category_keys:
            value = raw_factors.get(key)
            if isinstance(value, str):
                if value.strip():
                    return True
            elif value:
                return True
    return False


def _merged_category_weights(overrides: Mapping[str, float] | None) -> dict[str, float]:
    merged = dict(DEFAULT_CATEGORY_WEIGHTS)
    if not isinstance(overrides, Mapping):
        return merged
    for key, value in overrides.items():
        if key not in merged:
            continue
        try:
            merged[key] = float(value)
        except (TypeError, ValueError):
            continue
    return merged


def calculate_weighted_criteria_scores(
    chart: Any,
    *,
    predictors: Mapping[Any, Mapping[str, Any]],
    category_weights: Mapping[str, float] | None = None,
    anti_factor: float = DEFAULT_ANTI_FACTOR,
    calculate_sign_weights: Callable[[Any], Mapping[str, float]] = calculate_dominant_sign_weights,
    calculate_body_weights: Callable[[Any], Mapping[str, float]] = calculate_dominant_planet_weights,
    calculate_house_weights: Callable[[Any], Mapping[int, float]] = calculate_dominant_house_weights,
    calculate_nakshatra_weights: Callable[[Any], Mapping[str, float]] = calculate_dominant_nakshatra_weights,
    uses_houses: Callable[[Any], bool] = default_chart_uses_houses,
    scoring_options: WeightedPredictorScoringOptions | Mapping[str, Any] | None = None,
    background_score_stats: Mapping[Any, Mapping[str, Any]] | None = None,
    category_background_stats: Mapping[Any, Mapping[str, Mapping[str, Any]]] | None = None,
    debug: Callable[[str], None] | None = None,
    debug_prefix: str = "[Weighted Predictor Debug]",
    parse_error_prefix: str = "[Weighted Predictor Parse Error]",
    format_debug_target: Callable[[Any], str] | None = None,
) -> dict[Any, float]:
    """Score predictor targets from chart criteria and per-category weights.

    Predictor definitions may use weighted dicts or unweighted iterables for each
    positive/negative category: signs/antisigns, bodies/antibodies,
    nakshatras/antinakshatras, houses/antihouses, gates/antigates,
    channels/antichannels, hdtypes/antihdtypes, centers/anticenters, profiles/antiprofiles,
    authorities/antiauthorities, bazisigns/antibazisigns, positions/antipositions,
    and aspects/antiaspects.
    """
    scores = {target: 0.0 for target in predictors}
    options = coerce_scoring_options(scoring_options)
    score_mode = options.normalized_score_mode()
    use_legacy_category_delta = not options.simplify_anti_factor_handling
    weights_by_category = _merged_category_weights(category_weights) if use_legacy_category_delta else dict(DEFAULT_CATEGORY_WEIGHTS)
    target_label = format_debug_target or (lambda target: str(target))

    sign_weights_raw = getattr(chart, "dominant_sign_weights", None) or calculate_sign_weights(chart)
    body_weights_raw = getattr(chart, "dominant_planet_weights", None) or calculate_body_weights(chart)
    use_houses = uses_houses(chart)
    house_weights_raw = calculate_house_weights(chart) if use_houses else {}
    nakshatra_weights_raw = getattr(chart, "dominant_nakshatra_weights", None) or calculate_nakshatra_weights(chart)

    dominance_normalization_mode = options.normalized_dominance_normalization_mode()
    sign_weights = normalize_weight_map_for_dominance_activation(sign_weights_raw, dominance_normalization_mode)
    body_weights = normalize_weight_map_for_dominance_activation(body_weights_raw, dominance_normalization_mode)
    house_weights = normalize_weight_map_for_dominance_activation(house_weights_raw, dominance_normalization_mode) if use_houses else {}
    nakshatra_weights = normalize_weight_map_for_dominance_activation(nakshatra_weights_raw, dominance_normalization_mode)
    chart_name = str(getattr(chart, "name", "Unnamed Chart"))

    body_house_lookup: dict[str, int] = {}
    if use_houses:
        for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
            body = normalize_factor_value(str(raw_body))
            try:
                house_num = house_for_longitude(getattr(chart, "houses", None), float(lon))
            except (TypeError, ValueError):
                continue
            if house_num is not None:
                body_house_lookup[body] = house_num

    active_gates = (
        active_human_design_gates(chart)
        if _has_any_predictor_criteria(predictors, {"gates", "antigates"})
        else set()
    )
    active_channels = (
        active_human_design_channels(chart)
        if _has_any_predictor_criteria(predictors, {"channels", "antichannels"})
        else set()
    )
    if _has_any_predictor_criteria(
        predictors,
        {
            "hdtypes",
            "antihdtypes",
            "centers",
            "anticenters",
            "profiles",
            "antiprofiles",
            "authorities",
            "antiauthorities",
        },
    ):
        active_hd_type, active_centers, active_profile, active_authority = active_human_design_properties(chart)
    else:
        active_hd_type, active_centers, active_profile, active_authority = "", set(), "", ""
    bazi_sign_weights = (
        active_bazi_sign_weights(chart)
        if _has_any_predictor_criteria(predictors, {"bazisigns", "antibazisigns"})
        else {}
    )

    for target, raw_factors in predictors.items():
        factors = raw_factors if isinstance(raw_factors, Mapping) else {}
        signs = weighted_string_entries(factors.get("signs", set()))
        antisigns = weighted_string_entries(factors.get("antisigns", set()))
        bodies = weighted_string_entries(factors.get("bodies", set()))
        antibodies = weighted_string_entries(factors.get("antibodies", set()))
        nakshatras = weighted_string_entries(factors.get("nakshatras", set()))
        antinakshatras = weighted_string_entries(factors.get("antinakshatras", set()))
        houses = weighted_house_entries(factors.get("houses", set()))
        antihouses = weighted_house_entries(factors.get("antihouses", set()))
        gates = weighted_gate_entries(factors.get("gates", set()))
        antigates = weighted_gate_entries(factors.get("antigates", set()))
        channels = weighted_channel_entries(factors.get("channels", set()))
        antichannels = weighted_channel_entries(factors.get("antichannels", set()))
        hdtypes = weighted_hd_type_entries(factors.get("hdtypes", set()))
        antihdtypes = weighted_hd_type_entries(factors.get("antihdtypes", set()))
        centers = weighted_hd_center_entries(factors.get("centers", set()))
        anticenters = weighted_hd_center_entries(factors.get("anticenters", set()))
        profiles = weighted_hd_profile_entries(factors.get("profiles", set()))
        antiprofiles = weighted_hd_profile_entries(factors.get("antiprofiles", set()))
        authorities = weighted_hd_authority_entries(factors.get("authorities", set()))
        antiauthorities = weighted_hd_authority_entries(factors.get("antiauthorities", set()))
        bazisigns = weighted_bazi_sign_entries(factors.get("bazisigns", set()))
        antibazisigns = weighted_bazi_sign_entries(factors.get("antibazisigns", set()))
        positions = weighted_position_entries(factors.get("positions", set()))
        antipositions = weighted_position_entries(factors.get("antipositions", set()))
        aspects = _weighted_text_entries(factors.get("aspects", set()))
        antiaspects = _weighted_text_entries(factors.get("antiaspects", set()))

        if options.use_direct_dominance_activation:
            sign_positive = sum(float(sign_weights.get(sign, 0.0)) * weight for sign, weight in signs.items())
            sign_negative = sum(float(sign_weights.get(sign, 0.0)) * weight for sign, weight in antisigns.items())
            body_positive = sum(float(body_weights.get(body, 0.0)) * weight for body, weight in bodies.items())
            body_negative = sum(float(body_weights.get(body, 0.0)) * weight for body, weight in antibodies.items())
            nakshatra_positive = sum(float(nakshatra_weights.get(nakshatra, 0.0)) * weight for nakshatra, weight in nakshatras.items())
            nakshatra_negative = sum(float(nakshatra_weights.get(nakshatra, 0.0)) * weight for nakshatra, weight in antinakshatras.items())
        else:
            sign_positive = sum(weight for sign, weight in signs.items() if float(sign_weights.get(sign, 0.0)) > 0)
            sign_negative = sum(weight for sign, weight in antisigns.items() if float(sign_weights.get(sign, 0.0)) > 0)
            body_positive = sum(weight for body, weight in bodies.items() if float(body_weights.get(body, 0.0)) > 0)
            body_negative = sum(weight for body, weight in antibodies.items() if float(body_weights.get(body, 0.0)) > 0)
            nakshatra_positive = sum(weight for nakshatra, weight in nakshatras.items() if float(nakshatra_weights.get(nakshatra, 0.0)) > 0)
            nakshatra_negative = sum(weight for nakshatra, weight in antinakshatras.items() if float(nakshatra_weights.get(nakshatra, 0.0)) > 0)

        house_positive = 0.0
        house_negative = 0.0
        if use_houses:
            if options.use_direct_dominance_activation:
                house_positive = sum(float(house_weights.get(house_num, 0.0)) * weight for house_num, weight in houses.items())
                house_negative = sum(float(house_weights.get(house_num, 0.0)) * weight for house_num, weight in antihouses.items())
            else:
                house_positive = sum(weight for house_num, weight in houses.items() if float(house_weights.get(house_num, 0.0)) > 0)
                house_negative = sum(weight for house_num, weight in antihouses.items() if float(house_weights.get(house_num, 0.0)) > 0)

        hd_activation_weight = float(options.human_design_activation_weight)
        gates_positive = sum(hd_activation_weight * weight for gate, weight in gates.items() if gate in active_gates)
        gates_negative = sum(hd_activation_weight * weight for gate, weight in antigates.items() if gate in active_gates)
        channels_positive = sum(hd_activation_weight * weight for channel, weight in channels.items() if channel in active_channels)
        channels_negative = sum(hd_activation_weight * weight for channel, weight in antichannels.items() if channel in active_channels)
        
        hdtype_positive = sum(weight for hd_type, weight in hdtypes.items() if hd_type == active_hd_type)
        hdtype_negative = sum(weight for hd_type, weight in antihdtypes.items() if hd_type == active_hd_type)
        center_positive = sum(weight for center, weight in centers.items() if center in active_centers)
        center_negative = sum(weight for center, weight in anticenters.items() if center in active_centers)
        profile_positive = sum(weight for profile, weight in profiles.items() if profile == active_profile)
        profile_negative = sum(weight for profile, weight in antiprofiles.items() if profile == active_profile)
        authority_positive = sum(weight for authority, weight in authorities.items() if authority == active_authority)
        authority_negative = sum(weight for authority, weight in antiauthorities.items() if authority == active_authority)
        bazi_positive = sum(float(bazi_sign_weights.get(sign, 0.0)) * weight for sign, weight in bazisigns.items())
        bazi_negative = sum(float(bazi_sign_weights.get(sign, 0.0)) * weight for sign, weight in antibazisigns.items())

        positions_positive = 0.0
        positions_negative = 0.0
        for raw_position, criterion_weight in positions.items():
            bonus = _position_match_weight(raw_position, chart, use_houses, body_house_lookup, body_weights, sign_weights, house_weights, use_dominance_weighting=options.use_position_dominance_weighting)
            if bonus > 0:
                positions_positive += bonus * criterion_weight
                if debug is not None:
                    debug(
                        f"{debug_prefix} {chart_name}: {target_label(target)} position TRUE -> "
                        f"'{raw_position}' (+{bonus:.2f})"
                    )
        for raw_position, criterion_weight in antipositions.items():
            malus = _position_match_weight(raw_position, chart, use_houses, body_house_lookup, body_weights, sign_weights, house_weights, use_dominance_weighting=options.use_position_dominance_weighting)
            if malus > 0:
                positions_negative += malus * criterion_weight

        aspects_positive = _score_aspect_specs(
            chart,
            aspects,
            body_weights,
            chart_name,
            target,
            debug,
            debug_prefix=debug_prefix,
            parse_error_prefix=parse_error_prefix,
            target_label=target_label,
            anti=False,
            use_dominance_weighting=options.use_aspect_dominance_weighting,
        )
        aspects_negative = _score_aspect_specs(
            chart,
            antiaspects,
            body_weights,
            chart_name,
            target,
            debug,
            debug_prefix=debug_prefix,
            parse_error_prefix=parse_error_prefix,
            target_label=target_label,
            anti=True,
            use_dominance_weighting=options.use_aspect_dominance_weighting,
        )

        category_scores: dict[str, tuple[float, int]] = {}
        position_count, position_abs_weight = (len(positions) + len(antipositions), None)
        hdtype_count, hdtype_abs_weight = (len(hdtypes) + len(antihdtypes), None)
        profile_count, profile_abs_weight = (len(profiles) + len(antiprofiles), None)
        authority_count, authority_abs_weight = (len(authorities) + len(antiauthorities), None)
        if options.use_mutual_exclusive_bucket_scoring:
            position_count, position_abs_weight = _bucketed_criteria_count_and_abs_weight(
                positions, antipositions, bucket_for_key=_singleton_position_bucket
            )
            hdtype_count, hdtype_abs_weight = _bucketed_criteria_count_and_abs_weight(
                hdtypes, antihdtypes, bucket_for_key=_one_bucket
            )
            profile_count, profile_abs_weight = _bucketed_criteria_count_and_abs_weight(
                profiles, antiprofiles, bucket_for_key=_one_bucket
            )
            authority_count, authority_abs_weight = _bucketed_criteria_count_and_abs_weight(
                authorities, antiauthorities, bucket_for_key=_one_bucket
            )

        raw_category_pairs = {
            "signs": (sign_positive, sign_negative, len(signs) + len(antisigns)),
            "bodies": (body_positive, body_negative, len(bodies) + len(antibodies)),
            "nakshatras": (nakshatra_positive, nakshatra_negative, len(nakshatras) + len(antinakshatras)),
            "houses": (house_positive, house_negative, (len(houses) + len(antihouses)) if use_houses else 0),
            "gates": (gates_positive, gates_negative, len(gates) + len(antigates)),
            "channels": (channels_positive, channels_negative, len(channels) + len(antichannels)),
            "positions": (positions_positive, positions_negative, position_count),
            "aspects": (aspects_positive, aspects_negative, len(aspects) + len(antiaspects)),
        }
        for category, (positive, negative, count) in raw_category_pairs.items():
            if use_legacy_category_delta:
                value = normalize_category_delta(positive, negative, criteria_count=count, anti_factor=anti_factor)
            else:
                value = positive - (anti_factor * abs(negative))
                if options.average_scores_by_criterion_count and count > 0:
                    value /= float(count)
            category_scores[category] = (value, count)

        metadata_category_pairs = {
            "hdtypes": (hdtype_positive, hdtype_negative, hdtype_count),
            "centers": (center_positive, center_negative, len(centers) + len(anticenters)),
            "profiles": (profile_positive, profile_negative, profile_count),
            "authorities": (authority_positive, authority_negative, authority_count),
            "bazisigns": (bazi_positive, bazi_negative, len(bazisigns) + len(antibazisigns)),
        }
        for category, (positive, negative, count) in metadata_category_pairs.items():
            value = positive - (anti_factor * abs(negative))
            if not use_legacy_category_delta and options.average_scores_by_criterion_count and count > 0:
                value /= float(count)
            category_scores[category] = (value, count)

        target_total_abs_weight = 0.0
        target_category_stats = category_background_stats.get(target, {}) if isinstance(category_background_stats, Mapping) else {}
        category_weight_total = 0.0
        for category, (delta, _count) in category_scores.items():
            if score_mode == PREDICTION_SCORE_MODE_CATEGORY_Z:
                delta = _z_score(delta, target_category_stats.get(category) if isinstance(target_category_stats, Mapping) else None)
            weighted_category = weights_by_category[category] * criterion_multiplier_for_target(factors, category)
            scores[target] += weighted_category * delta
            if score_mode == PREDICTION_SCORE_MODE_CATEGORY_Z and _count > 0 and weighted_category > 0:
                category_weight_total += weighted_category
        if score_mode == PREDICTION_SCORE_MODE_CATEGORY_Z and category_weight_total > 0:
            scores[target] /= category_weight_total

        for values in (
            signs, antisigns, bodies, antibodies, nakshatras, antinakshatras,
            houses, antihouses, gates, antigates, channels, antichannels,
            centers, anticenters, bazisigns, antibazisigns, aspects, antiaspects,
        ):
            target_total_abs_weight += sum(abs(float(weight)) for weight in values.values())
        if options.use_mutual_exclusive_bucket_scoring:
            target_total_abs_weight += float(position_abs_weight or 0.0)
            target_total_abs_weight += float(hdtype_abs_weight or 0.0)
            target_total_abs_weight += float(profile_abs_weight or 0.0)
            target_total_abs_weight += float(authority_abs_weight or 0.0)
        else:
            for values in (hdtypes, antihdtypes, profiles, antiprofiles, authorities, antiauthorities, positions, antipositions):
                target_total_abs_weight += sum(abs(float(weight)) for weight in values.values())
        if score_mode in {PREDICTION_SCORE_MODE_OPPORTUNITY, PREDICTION_SCORE_MODE_BACKGROUND_Z}:
            scores[target] = _apply_type_signature_scale(
                scores[target],
                target_total_abs_weight,
                options.normalized_type_signature_scale_mode(),
            )
        if score_mode == PREDICTION_SCORE_MODE_BACKGROUND_Z:
            stats = background_score_stats.get(target) if isinstance(background_score_stats, Mapping) else None
            scores[target] = _z_score(scores[target], stats)
    return scores


def _position_match_weight(
    raw_position: str,
    chart: Any,
    use_houses: bool,
    body_house_lookup: Mapping[str, int],
    body_weights: Mapping[str, float],
    sign_weights: Mapping[str, float],
    house_weights: Mapping[int, float],
    *,
    use_dominance_weighting: bool,
) -> float:
    parsed = parse_position_spec(raw_position)
    if parsed is None:
        return 0.0
    category, container, subject = parsed
    if category == "body_in_house" and isinstance(container, int) and use_houses:
        if body_house_lookup.get(subject) == container:
            if not use_dominance_weighting:
                return 1.0
            return float(body_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
    elif category == "sign_in_house" and isinstance(container, int) and use_houses:
        angle_for_house = {1: "AS", 4: "IC", 7: "DS", 10: "MC"}.get(container)
        if angle_for_house:
            angle_lon = (getattr(chart, "positions", None) or {}).get(angle_for_house)
            try:
                angle_lon_value = float(angle_lon)
            except (TypeError, ValueError):
                angle_lon_value = None
            if angle_lon_value is not None and sign_for_longitude(angle_lon_value) == subject:
                if not use_dominance_weighting:
                    return 1.0
                return float(sign_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
        for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
            body = normalize_factor_value(str(raw_body))
            if body not in body_house_lookup or body_house_lookup[body] != container:
                continue
            try:
                lon_value = float(lon)
            except (TypeError, ValueError):
                continue
            if sign_for_longitude(lon_value) == subject:
                if not use_dominance_weighting:
                    return 1.0
                return float(sign_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
    elif category == "body_in_sign" and isinstance(container, str):
        body_lon = (getattr(chart, "positions", None) or {}).get(subject)
        try:
            lon_value = float(body_lon)
        except (TypeError, ValueError):
            lon_value = None
        if lon_value is not None and sign_for_longitude(lon_value) == container:
            if not use_dominance_weighting:
                return 1.0
            return float(body_weights.get(subject, 0.0)) + float(sign_weights.get(container, 0.0))
    return 0.0


def _aspect_orb_quality(aspect: Mapping[str, Any]) -> float:
    aspect_type = str(aspect.get("type", "")).strip().lower()
    try:
        orb_deg = abs(float(aspect.get("delta", 0.0)))
    except (TypeError, ValueError):
        orb_deg = 0.0
    try:
        max_orb_deg = float(ASPECT_DEFS.get(aspect_type, {}).get("orb", 0.0))
    except (TypeError, ValueError):
        max_orb_deg = 0.0
    if max_orb_deg <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (orb_deg / max_orb_deg)))


def _score_aspect_specs(
    chart: Any,
    aspect_specs: Mapping[str, float],
    body_weights: Mapping[str, float],
    chart_name: str,
    target: Any,
    debug: Callable[[str], None] | None,
    *,
    debug_prefix: str,
    parse_error_prefix: str,
    target_label: Callable[[Any], str],
    anti: bool,
    use_dominance_weighting: bool,
) -> float:
    total = 0.0
    for raw_aspect, criterion_weight in aspect_specs.items():
        parsed = parse_aspect_spec(raw_aspect)
        if parsed is None:
            print(f"{parse_error_prefix} {chart_name}: could not parse aspect spec '{raw_aspect}'")
            continue
        left_body, aspect_type, right_body = parsed
        for aspect in getattr(chart, "aspects", []) or []:
            p1 = normalize_factor_value(str(aspect.get("p1", "")))
            p2 = normalize_factor_value(str(aspect.get("p2", "")))
            current_type = str(aspect.get("type", "")).strip().lower()
            if current_type != aspect_type:
                continue
            if {p1, p2} != {left_body, right_body}:
                continue
            if use_dominance_weighting:
                aspect_weight = float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0))
                value = float(body_weights.get(left_body, 0.0)) + aspect_weight + float(body_weights.get(right_body, 0.0))
            else:
                value = _aspect_orb_quality(aspect)
            total += value * float(criterion_weight)
            if debug is not None and not anti:
                debug(
                    f"{debug_prefix} {chart_name}: {target_label(target)} aspect TRUE -> "
                    f"'{raw_aspect}' (+{value:.2f})"
                )
            break
    return total
