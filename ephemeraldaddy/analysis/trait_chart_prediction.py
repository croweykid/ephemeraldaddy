"""One-chart Trait calculation request, independent of windows and Qt."""
from __future__ import annotations
from typing import Any, Callable
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.analysis.trait_prediction_results import metadata_from_vectors
from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature
from ephemeraldaddy.core.prediction_norms import trait_norm_values
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core import db


def calculate_chart_prediction(chart: Any, traits: list[dict[str, Any]], *, include_gender: bool = False, include_evidence: bool = True, should_cancel: Callable[[], bool] = lambda: False) -> dict[str, Any] | None:
    index = global_trait_prediction_index()
    scores = index.chart_likelihoods(chart, traits, chart_signature=chart_prediction_signature(chart))
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
        if saved is not None and chart_prediction_signature(saved) == chart_prediction_signature(chart):
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
    unavailable = sorted({t['name'] for t in traits} - averages.keys())
    if unavailable:
        metadata['unavailable_traits'] = unavailable
        metadata['unavailable_trait_reason'] = 'Static DB norms unavailable for: ' + ', '.join(unavailable) + '. Generate DB Norms explicitly in Developer Tools.'
    return metadata if not should_cancel() else None
