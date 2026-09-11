"""Install effective birth-time context handling for Chart View Trait Predictions."""

from __future__ import annotations

from typing import Any, Mapping

from ephemeraldaddy.analysis import traits as traits_module
from ephemeraldaddy.analysis import weighted_chart_predictor as predictor
from ephemeraldaddy.analysis.prediction_context import (
    EffectivePredictionContext,
    build_effective_prediction_context,
    calculate_weighted_criteria_scores_with_context,
    matched_weighted_criteria_with_context,
    prediction_profile_signature,
)


def _copy_matches(matches: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        "positive": [str(value) for value in matches.get("positive", [])],
        "negative": [str(value) for value in matches.get("negative", [])],
    }


def _store_trait_matches(
    chart: Any,
    context: EffectivePredictionContext,
    traits: list[dict[str, Any]],
    matches_by_name: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    by_name: dict[str, dict[str, list[str]]] = {}
    by_profile: dict[str, dict[str, list[str]]] = {}
    for trait in traits:
        name = str(trait.get("name", "") or "").strip()
        if not name:
            continue
        profile = trait.get("profile", {})
        profile = profile if isinstance(profile, Mapping) else {}
        matches = matches_by_name.get(name)
        if not isinstance(matches, Mapping):
            continue
        normalized = _copy_matches(matches)
        by_name[name] = normalized
        by_profile[prediction_profile_signature(profile)] = normalized
    payload = {
        "context_token": context.source_token,
        "by_name": by_name,
        "by_profile": by_profile,
    }
    try:
        setattr(chart, "_trait_prediction_factor_matches", payload)
    except Exception:
        pass
    return by_name


def _cached_trait_matches(
    chart: Any,
    factors: Mapping[str, Any],
    context: EffectivePredictionContext,
) -> dict[str, list[str]] | None:
    cache = getattr(chart, "_trait_prediction_factor_matches", None)
    if not isinstance(cache, Mapping) or cache.get("context_token") != context.source_token:
        return None
    by_profile = cache.get("by_profile", {})
    if not isinstance(by_profile, Mapping):
        return None
    matches = by_profile.get(prediction_profile_signature(factors))
    return _copy_matches(matches) if isinstance(matches, Mapping) else None


def _ensure_trait_matches(
    chart: Any,
    traits: list[dict[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    context = build_effective_prediction_context(chart)
    cache = getattr(chart, "_trait_prediction_factor_matches", None)
    active_names = {
        str(trait.get("name", "") or "").strip()
        for trait in traits
        if str(trait.get("name", "") or "").strip()
    }
    if isinstance(cache, Mapping) and cache.get("context_token") == context.source_token:
        cached_by_name = cache.get("by_name", {})
        if isinstance(cached_by_name, Mapping) and active_names <= set(cached_by_name):
            return {
                name: _copy_matches(cached_by_name[name])
                for name in active_names
                if isinstance(cached_by_name.get(name), Mapping)
            }

    matches_by_name: dict[str, dict[str, list[str]]] = {}
    for trait in traits:
        name = str(trait.get("name", "") or "").strip()
        if not name:
            continue
        profile = trait.get("profile", {})
        profile = profile if isinstance(profile, Mapping) else {}
        matches_by_name[name] = matched_weighted_criteria_with_context(
            chart,
            profile,
            prediction_context=context,
            _original_matcher=getattr(
                predictor,
                "_effective_context_original_matched_weighted_criteria",
                predictor.matched_weighted_criteria,
            ),
        )
    return _store_trait_matches(chart, context, traits, matches_by_name)


def _calculate_trait_scores_with_context(
    chart: Any,
    traits: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    trait_items = traits if traits is not None else traits_module.list_traits(active_only=True)
    trait_items = [item for item in trait_items if not bool(item.get("archived", False))]
    predictors = {
        str(item.get("name", "")): item.get("profile", {})
        for item in trait_items
        if str(item.get("name", "")).strip()
    }
    if not predictors:
        return {}

    context = build_effective_prediction_context(chart)
    matches: dict[str, dict[str, list[str]]] = {}
    raw_scores = calculate_weighted_criteria_scores_with_context(
        chart,
        predictors=predictors,
        prediction_context=context,
        matched_criteria_out=matches,
        _original_calculate=getattr(
            predictor,
            "_effective_context_original_calculate_weighted_criteria_scores",
            predictor.calculate_weighted_criteria_scores,
        ),
    )
    _store_trait_matches(chart, context, trait_items, matches)
    return {str(name): float(raw_scores.get(name, 0.0)) for name in predictors}


def install_trait_prediction_context(core: Any) -> None:
    """Route Trait score + evidence through one fresh effective chart context."""
    if bool(getattr(core, "_trait_prediction_context_installed", False)):
        return

    original_calculate = getattr(
        predictor,
        "_effective_context_original_calculate_weighted_criteria_scores",
        predictor.calculate_weighted_criteria_scores,
    )
    original_matcher = getattr(
        predictor,
        "_effective_context_original_matched_weighted_criteria",
        predictor.matched_weighted_criteria,
    )
    predictor._effective_context_original_calculate_weighted_criteria_scores = original_calculate
    predictor._effective_context_original_matched_weighted_criteria = original_matcher

    def context_calculate(chart: Any, *, predictors: Mapping[Any, Mapping[str, Any]], **kwargs: Any) -> dict[Any, float]:
        prediction_context = kwargs.pop("prediction_context", None)
        matched_criteria_out = kwargs.pop("matched_criteria_out", None)
        return calculate_weighted_criteria_scores_with_context(
            chart,
            predictors=predictors,
            prediction_context=prediction_context,
            matched_criteria_out=matched_criteria_out,
            _original_calculate=original_calculate,
            **kwargs,
        )

    def context_match(
        chart: Any,
        factors: Mapping[str, Any],
        *,
        prediction_context: EffectivePredictionContext | None = None,
    ) -> dict[str, list[str]]:
        context = prediction_context or build_effective_prediction_context(chart)
        cached = _cached_trait_matches(chart, factors, context)
        if cached is not None:
            return cached
        return matched_weighted_criteria_with_context(
            chart,
            factors,
            prediction_context=context,
            _original_matcher=original_matcher,
        )

    # traits.py imported the scorer by name, so update that alias as well as the
    # predictor module's public entry point. calculate_trait_likelihoods resolves
    # calculate_trait_scores through its module globals at call time.
    predictor.calculate_weighted_criteria_scores = context_calculate
    predictor.matched_weighted_criteria = context_match
    traits_module.calculate_weighted_criteria_scores = context_calculate
    traits_module.calculate_trait_scores = _calculate_trait_scores_with_context
    core.matched_weighted_criteria = context_match

    original_metadata_for_chart = core.trait_metadata_for_chart

    def metadata_with_factor_evidence(
        owner: Any,
        chart: Any,
        *,
        traits: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        resolved_traits = traits if traits is not None else traits_module.list_traits(active_only=True)
        metadata = original_metadata_for_chart(
            owner,
            chart,
            traits=resolved_traits,
            **kwargs,
        )
        if not isinstance(metadata, dict) or chart is None:
            return metadata
        result = dict(metadata)
        result["factor_matches"] = _ensure_trait_matches(chart, resolved_traits)
        return result

    core.trait_metadata_for_chart = metadata_with_factor_evidence
    core._trait_prediction_context_installed = True
