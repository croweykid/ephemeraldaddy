"""Resolved chart context shared by weighted prediction scoring and evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping

from ephemeraldaddy.core.aspects import find_aspects
from ephemeraldaddy.core.chart import (
    apply_time_specific_metadata_policy,
    chart_uses_houses,
    rectification_range_minutes,
)

WeightMap = Mapping[Any, float]
WeightCalculator = Callable[[Any], WeightMap]
UsesHouses = Callable[[Any], bool]


@dataclass
class EffectivePredictionContext:
    """One resolved chart state used by both prediction scores and explanations.

    The context deliberately owns freshly calculated dominance maps. Persisted
    ``chart.dominant_*`` payloads are display/cache data and are not trusted as
    scoring inputs because they can describe a different birth-time policy.
    """

    chart: Any
    source_token: str
    birth_time_policy: str
    rectification_range: tuple[int, int] | None
    use_houses: bool
    sign_weights: dict[str, float]
    body_weights: dict[str, float]
    house_weights: dict[int, float]
    nakshatra_weights: dict[str, float]
    matched_criteria_by_profile: dict[str, dict[str, list[str]]] = field(default_factory=dict)


_DERIVED_WEIGHT_ATTRS = (
    "dominant_sign_weights",
    "dominant_planet_weights",
    "dominant_nakshatra_weights",
    "dominant_element_weights",
)
_HD_CACHE_DEFAULTS: dict[str, Any] = {
    "human_design_gates": [],
    "human_design_lines": [],
    "human_design_channels": [],
    "human_design_type": "",
    "human_design_defined_centers": [],
    "human_design_profile": "",
    "human_design_authority": "",
}


def _stable_payload_hash(payload: Any) -> str:
    try:
        serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        serialized = repr(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def prediction_profile_signature(profile: Mapping[str, Any] | None) -> str:
    """Return a stable key for one weighted predictor profile."""
    return _stable_payload_hash(profile if isinstance(profile, Mapping) else {})


def _chart_context_token(chart: Any) -> str:
    positions = getattr(chart, "positions", None) or {}
    aspects = getattr(chart, "aspects", None) or []
    houses = getattr(chart, "houses", None) or []
    payload = {
        "dt": getattr(chart, "dt", None),
        "dt_local": getattr(chart, "dt_local", None),
        "lat": getattr(chart, "lat", None),
        "lon": getattr(chart, "lon", None),
        "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
        "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
        "retcon_hour": getattr(chart, "retcon_hour", None),
        "retcon_minute": getattr(chart, "retcon_minute", None),
        "rectification_range_used": bool(getattr(chart, "rectification_range_used", False)),
        "rectification_range_start_minute": getattr(chart, "rectification_range_start_minute", None),
        "rectification_range_end_minute": getattr(chart, "rectification_range_end_minute", None),
        "positions": positions,
        "aspects": aspects,
        "houses": houses,
    }
    return _stable_payload_hash(payload)


def _copy_chart_for_prediction(chart: Any) -> Any:
    effective = copy.copy(chart)
    for attr in ("positions",):
        raw = getattr(chart, attr, None)
        if isinstance(raw, Mapping):
            setattr(effective, attr, dict(raw))
    for attr in ("houses", "housesPo"):
        raw = getattr(chart, attr, None)
        if isinstance(raw, (list, tuple)):
            setattr(effective, attr, list(raw))
    aspects = getattr(chart, "aspects", None)
    if isinstance(aspects, (list, tuple)):
        setattr(
            effective,
            "aspects",
            [dict(item) if isinstance(item, Mapping) else item for item in aspects],
        )
    for attr in _DERIVED_WEIGHT_ATTRS:
        try:
            setattr(effective, attr, {})
        except Exception:
            pass
    for attr, empty_value in _HD_CACHE_DEFAULTS.items():
        try:
            setattr(effective, attr, copy.copy(empty_value))
        except Exception:
            pass
    return effective


def _birth_time_policy(chart: Any) -> tuple[str, tuple[int, int] | None]:
    unknown = bool(getattr(chart, "birthtime_unknown", False))
    retcon = bool(getattr(chart, "retcon_time_used", False))
    rectified_range = rectification_range_minutes(chart)
    if unknown and not retcon and rectified_range is not None:
        return "rectified_range", rectified_range
    if unknown and not retcon:
        return "full_unknown_range", None
    return "exact_time", None


def _default_sign_weight_calculator() -> WeightCalculator:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_sign_weights

    return calculate_dominant_sign_weights


def _default_body_weight_calculator() -> WeightCalculator:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_planet_weights

    return calculate_dominant_planet_weights


def _default_house_weight_calculator() -> WeightCalculator:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_house_weights

    return calculate_dominant_house_weights


def _default_nakshatra_weight_calculator() -> WeightCalculator:
    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_nakshatra_weights

    return calculate_dominant_nakshatra_weights


def build_effective_prediction_context(
    chart: Any,
    *,
    calculate_sign_weights: WeightCalculator | None = None,
    calculate_body_weights: WeightCalculator | None = None,
    calculate_house_weights: WeightCalculator | None = None,
    calculate_nakshatra_weights: WeightCalculator | None = None,
    uses_houses: UsesHouses = chart_uses_houses,
    force_rebuild: bool = False,
) -> EffectivePredictionContext:
    """Resolve the active birth-time policy and freshly derive scoring inputs.

    Rectification ranges use the same midpoint policy as ``core.chart``. The
    policy is applied to a copy, so prediction refreshes cannot mutate the live
    Chart View object. Dominance/HD caches are cleared before derivation.
    """
    source_token = _chart_context_token(chart)
    has_context_overrides = (
        calculate_sign_weights is not None
        or calculate_body_weights is not None
        or calculate_house_weights is not None
        or calculate_nakshatra_weights is not None
        or uses_houses is not chart_uses_houses
    )
    if not force_rebuild and not has_context_overrides:
        cached = getattr(chart, "_effective_prediction_context_cache", None)
        if isinstance(cached, EffectivePredictionContext) and cached.source_token == source_token:
            return cached

    effective = _copy_chart_for_prediction(chart)
    apply_time_specific_metadata_policy(effective)
    use_houses = bool(uses_houses(effective))

    # Resolve GUI-backed defaults only for callbacks the caller did not inject.
    # This keeps dependency injection usable in headless analysis/test contexts.
    sign_calculator = calculate_sign_weights
    if sign_calculator is None:
        sign_calculator = _default_sign_weight_calculator()
    body_calculator = calculate_body_weights
    if body_calculator is None:
        body_calculator = _default_body_weight_calculator()
    house_calculator = calculate_house_weights
    if use_houses and house_calculator is None:
        house_calculator = _default_house_weight_calculator()
    nakshatra_calculator = calculate_nakshatra_weights
    if nakshatra_calculator is None:
        nakshatra_calculator = _default_nakshatra_weight_calculator()

    # Unknown-time/range policy can replace planetary positions without rebuilding
    # natal aspects. Rebuild them here from the resolved effective positions so
    # aspect criteria and dominance weighting use the same time as placements.
    positions = getattr(effective, "positions", None) or {}
    if positions:
        effective.aspects = find_aspects(positions)

    sign_weights = {str(key): float(value) for key, value in sign_calculator(effective).items()}
    body_weights = {str(key): float(value) for key, value in body_calculator(effective).items()}
    house_weights = (
        {int(key): float(value) for key, value in house_calculator(effective).items()}
        if use_houses and house_calculator is not None
        else {}
    )
    nakshatra_weights = {
        str(key): float(value) for key, value in nakshatra_calculator(effective).items()
    }

    # The legacy scorer/matcher still probes these attributes first. Populate
    # them only with values derived from this effective context, never persistence.
    effective.dominant_sign_weights = dict(sign_weights)
    effective.dominant_planet_weights = dict(body_weights)
    effective.dominant_nakshatra_weights = dict(nakshatra_weights)

    policy, rectified_range = _birth_time_policy(effective)
    context = EffectivePredictionContext(
        chart=effective,
        source_token=source_token,
        birth_time_policy=policy,
        rectification_range=rectified_range,
        use_houses=use_houses,
        sign_weights=sign_weights,
        body_weights=body_weights,
        house_weights=house_weights,
        nakshatra_weights=nakshatra_weights,
    )
    # Only the default scoring policy is safe to retain as a chart-level cache.
    # Explicit calculators/house policies are caller-specific and must not leak
    # into later calls that request different scoring semantics.
    if not has_context_overrides:
        try:
            setattr(chart, "_effective_prediction_context_cache", context)
        except Exception:
            pass
    return context


def calculate_weighted_criteria_scores_with_context(
    chart: Any,
    *,
    predictors: Mapping[Any, Mapping[str, Any]],
    prediction_context: EffectivePredictionContext | None = None,
    matched_criteria_out: MutableMapping[Any, dict[str, list[str]]] | None = None,
    _original_calculate: Callable[..., dict[Any, float]] | None = None,
    **kwargs: Any,
) -> dict[Any, float]:
    """Run the weighted scorer against one explicit effective context.

    ``matched_criteria_out`` lets callers retain the exact criterion activation
    evidence associated with the same resolved context as the numerical score.
    """
    if _original_calculate is None:
        from ephemeraldaddy.analysis import weighted_chart_predictor as predictor

        _original_calculate = getattr(
            predictor,
            "_effective_context_original_calculate_weighted_criteria_scores",
            predictor.calculate_weighted_criteria_scores,
        )

    context = prediction_context
    if context is None:
        context = build_effective_prediction_context(
            chart,
            calculate_sign_weights=kwargs.get("calculate_sign_weights"),
            calculate_body_weights=kwargs.get("calculate_body_weights"),
            calculate_house_weights=kwargs.get("calculate_house_weights"),
            calculate_nakshatra_weights=kwargs.get("calculate_nakshatra_weights"),
            uses_houses=kwargs.get("uses_houses", chart_uses_houses),
        )

    scorer_kwargs = dict(kwargs)
    scorer_kwargs["calculate_sign_weights"] = lambda _chart: context.sign_weights
    scorer_kwargs["calculate_body_weights"] = lambda _chart: context.body_weights
    scorer_kwargs["calculate_house_weights"] = lambda _chart: context.house_weights
    scorer_kwargs["calculate_nakshatra_weights"] = lambda _chart: context.nakshatra_weights
    scorer_kwargs["uses_houses"] = lambda _chart: context.use_houses
    scores = _original_calculate(context.chart, predictors=predictors, **scorer_kwargs)

    if matched_criteria_out is not None:
        for target, raw_factors in predictors.items():
            factors = raw_factors if isinstance(raw_factors, Mapping) else {}
            matched_criteria_out[target] = matched_weighted_criteria_with_context(
                chart,
                factors,
                prediction_context=context,
            )
    return scores


def matched_weighted_criteria_with_context(
    chart: Any,
    factors: Mapping[str, Any],
    *,
    prediction_context: EffectivePredictionContext | None = None,
    _original_matcher: Callable[[Any, Mapping[str, Any]], dict[str, list[str]]] | None = None,
) -> dict[str, list[str]]:
    """Return criterion evidence from the same effective chart used for scoring."""
    if _original_matcher is None:
        from ephemeraldaddy.analysis import weighted_chart_predictor as predictor

        _original_matcher = getattr(
            predictor,
            "_effective_context_original_matched_weighted_criteria",
            predictor.matched_weighted_criteria,
        )
    context = prediction_context or build_effective_prediction_context(chart)
    profile_key = prediction_profile_signature(factors)
    cached = context.matched_criteria_by_profile.get(profile_key)
    if isinstance(cached, dict):
        return {
            "positive": list(cached.get("positive", [])),
            "negative": list(cached.get("negative", [])),
        }
    matches = _original_matcher(context.chart, factors)
    normalized = {
        "positive": [str(value) for value in matches.get("positive", [])],
        "negative": [str(value) for value in matches.get("negative", [])],
    }
    context.matched_criteria_by_profile[profile_key] = normalized
    return {key: list(values) for key, values in normalized.items()}
