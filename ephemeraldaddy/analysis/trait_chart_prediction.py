"""One-chart Trait requests and cached results, independent of windows and Qt."""
from __future__ import annotations
from typing import Any, Callable
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.analysis.trait_prediction_results import metadata_from_vectors
from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature
from ephemeraldaddy.analysis.trait_prediction_metadata_cache import (
    cached_trait_prediction_metadata, retain_trait_prediction_metadata, trait_metadata_cache_key,
)
from ephemeraldaddy.core.prediction_norms import trait_norm_values
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core import db


def _mark_unavailable_traits(metadata: dict[str, Any], traits: list[dict[str, Any]]) -> None:
    unavailable = sorted({t['name'] for t in traits} - metadata['database_averages'].keys())
    if unavailable:
        metadata['unavailable_traits'] = unavailable
        metadata['unavailable_trait_reason'] = 'Static DB norms unavailable for: ' + ', '.join(unavailable) + '. Generate DB Norms explicitly in Developer Tools.'


def cached_chart_prediction(
    chart: Any, traits: list[dict[str, Any]], *, chart_signature: str | None = None,
) -> dict[str, Any] | None:
    """Prefer accepted chart-local results, then read the shared persisted index."""
    signature = chart_signature or chart_prediction_signature(chart)
    metadata = cached_trait_prediction_metadata(chart, traits, chart_signature=signature)
    if metadata is not None:
        return metadata
    uid = str(getattr(chart, 'chart_uid', '') or '').strip().upper()
    if not uid:
        return None
    result = global_trait_prediction_index().results_for_uids([uid], traits, chart_signatures={uid: signature}).get(uid)
    if result is None:
        return None
    metadata = metadata_from_vectors(
        likelihoods=result.likelihoods, database_averages=result.database_averages,
        stale_chart_vector=result.stale_chart_vector, stale_trait_definition=result.stale_trait_definition,
        stale_db_baseline=result.stale_db_baseline, stale_trait_names=set(result.stale_trait_names), updated_at=result.updated_at,
    )
    _mark_unavailable_traits(metadata, traits)
    return metadata


def calculate_chart_prediction(chart: Any, traits: list[dict[str, Any]], *, include_gender: bool = False, include_evidence: bool = True, should_cancel: Callable[[], bool] = lambda: False) -> dict[str, Any] | None:
    index = global_trait_prediction_index()
    signature = chart_prediction_signature(chart)
    cache_key = trait_metadata_cache_key(chart, traits, chart_signature=signature)
    scores = index.chart_likelihoods(chart, traits, chart_signature=signature)
    averages = trait_norm_values(traits, include_houses=chart_uses_houses(chart))
    metadata = metadata_from_vectors(likelihoods=scores, database_averages=averages)
    if include_evidence:
        from ephemeraldaddy.analysis.trait_evidence import _ensure_trait_matches
        metadata['factor_matches'] = _ensure_trait_matches(chart, traits)
    if should_cancel():
        return None
    uid = str(getattr(chart, 'chart_uid', '') or '').upper()
    if uid:
        saved = db.load_chart_by_uid(uid)
        if saved is not None and chart_prediction_signature(saved) == signature:
            if should_cancel():
                return None
            index.persist_scores(chart, traits, scores)
            from datetime import datetime, timezone
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if include_gender:
        from ephemeraldaddy.analysis.trait_gender import calculate_trait_likelihoods_with_gender, _gender_traits_for_chart
        gender_traits = _gender_traits_for_chart(chart, traits)
        adjusted = calculate_trait_likelihoods_with_gender(chart, gender_traits)
        overlay = {**scores, **adjusted}
        metadata.update(metadata_from_vectors(likelihoods=overlay, database_averages=averages))
        metadata['gender_criterion_traits'] = sorted(adjusted)
    _mark_unavailable_traits(metadata, traits)
    if should_cancel():
        return None
    if not metadata.get('gender_criterion_traits'):
        if not retain_trait_prediction_metadata(chart, traits, metadata, expected_signature=cache_key):
            return None
    return metadata
