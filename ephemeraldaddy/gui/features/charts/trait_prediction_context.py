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


# Transitional facade: remove these imports when remaining GUI evidence callers migrate.
from ephemeraldaddy.analysis.trait_evidence import (
    _copy_matches, _store_trait_matches, _cached_trait_matches,
    _ensure_trait_matches, _calculate_trait_scores_with_context,
)


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
        if not kwargs.get("cached_only", False):
            result["factor_matches"] = _ensure_trait_matches(chart, resolved_traits)
        return result

    core.trait_metadata_for_chart = metadata_with_factor_evidence
    core._trait_prediction_context_installed = True
