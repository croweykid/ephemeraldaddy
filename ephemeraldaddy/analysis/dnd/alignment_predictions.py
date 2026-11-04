"""Fantasy RPG alignment through the shared Trait engine and static norms."""
from __future__ import annotations
from typing import Any
from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_ALIGNMENTS
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.core.prediction_norms import trait_norm_values
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature
from ephemeraldaddy.core import db


def alignment_traits() -> list[dict[str, Any]]:
    items = []
    for key in ('good', 'evil', 'lawful', 'chaotic'):
        definition = DND_ALIGNMENTS.get(key, {})
        label = str(definition.get('label') or key.title()).strip()
        profile = {name: value for name, value in definition.items() if name not in {'label', 'name', 'confidence', 'color', 'motivation', 'description', 'quotes', 'samples', 'archived'}}
        items.append({'uid': f'dnd_alignment_{key}', 'name': label, 'profile': profile})
    return items


def alignment_parts(chart: Any, *, calculate: bool = False) -> dict[str, dict[str, float]]:
    if chart is None:
        return {}
    traits = alignment_traits()
    index = global_trait_prediction_index()
    uid = str(getattr(chart, 'chart_uid', '') or '').upper()
    if calculate:
        scores = index.chart_likelihoods(chart, traits, chart_signature=chart_prediction_signature(chart))
        saved = db.load_chart_by_uid(uid) if uid else None
        if saved is not None and chart_prediction_signature(saved) == chart_prediction_signature(chart):
            index.persist_scores(chart, traits, scores)
    else:
        cached = index.results_for_uids([uid], traits).get(uid) if uid else None
        scores = cached.likelihoods if cached else {}
    averages = trait_norm_values(traits, include_houses=chart_uses_houses(chart))
    return {name.casefold(): {'chart': value, 'database': averages[name], 'deviation': value - averages[name]} for name, value in scores.items() if name in averages}
