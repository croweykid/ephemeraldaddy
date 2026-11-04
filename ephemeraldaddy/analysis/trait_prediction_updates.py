"""Scoped Trait refresh policy: model edits and the existing chart journal."""
from __future__ import annotations
import threading
from typing import Any
from ephemeraldaddy.core import db
from ephemeraldaddy.core.trait_invalidation import trait_definition_invalidation, trait_invalidation_for_chart_change
from ephemeraldaddy.analysis.traits import list_traits
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index

_lock = threading.RLock()
_cursors: dict[str, int] = {}


def synchronize_chart_changes() -> bool:
    """Consume only new astro/add/delete events; never rescore a population.

    The first hydration establishes the journal cursor. Missing older caches
    are filled on demand. Subsequent astro edits enqueue just their chart UIDs.
    """
    db.register_chart_saved_callback(synchronize_chart_changes)
    key = str(db.DB_PATH)
    with _lock:
        latest = db.latest_chart_change_sequence()
        previous = _cursors.get(key)
        _cursors[key] = latest
    if previous is None:
        return False
    changes = db.chart_changes_since(previous) if latest > previous else []
    index = global_trait_prediction_index()
    changed = set()
    for change in changes:
        uid = str(change['chart_uid'])
        index.invalidate_chart(uid)
        if change['change_type'] != 'deleted' and change['astro_data_changed']:
            changed.add(uid)
    impact = trait_invalidation_for_chart_change('astro_data', changed)
    if impact.score_chart_uids:
        from ephemeraldaddy.analysis.dnd.alignment_predictions import alignment_traits
        index.request_refresh(impact.score_chart_uids, list_traits(active_only=True) + alignment_traits())
    return bool(changes)


def trait_changed(trait: dict[str, Any], *, change_type: str) -> None:
    """Model changes refresh one column; labels/availability never rescore."""
    impact = trait_definition_invalidation(str(trait['name']), change_type=change_type)
    index = global_trait_prediction_index()
    if change_type != 'renamed':
        index.invalidate_trait(str(trait.get('uid') or trait.get('trait_uid') or ''))
    if change_type == 'deleted':
        db.purge_chart_trait_metadata_for_trait(trait_uid=str(trait.get('uid') or ''), trait_name=trait['name'])
    if change_type != 'definition_changed':
        index._publish((), [trait])
    if change_type == 'definition_changed' and impact.trait_names:
        index.request_refresh(db.prediction_chart_uids(), [trait])
