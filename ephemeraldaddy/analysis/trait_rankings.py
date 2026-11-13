"""Rank persisted Trait scores against the selected static population reference."""
from __future__ import annotations
from typing import Any, Callable, Iterable
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.core import db


def ranked_trait_rows(
    chart_uids: Iterable[str], trait: dict[str, Any], *,
    hidden_uids: Iterable[str] = (), limit: int | None = None,
    refresh_missing: bool = False,
) -> list[dict[str, Any]]:
    """Read available rows, optionally queuing missing/stale cells in this scope."""
    name = str(trait["name"])
    index = global_trait_prediction_index()
    uids = tuple(dict.fromkeys(str(uid).strip().upper() for uid in chart_uids if str(uid).strip()))
    results = index.results_for_uids(uids, [trait])
    labels = db.prediction_chart_labels(uids if refresh_missing else results)
    hidden = {str(uid).strip().upper() for uid in hidden_uids}
    if refresh_missing:
        needed = [uid for uid in labels if uid not in hidden and (
            uid not in results or name not in results[uid].likelihoods
            or results[uid].stale_chart_vector or results[uid].stale_trait_definition
            or name in results[uid].stale_trait_names
        )]
        if needed:
            index.request_missing(needed, [trait])
    rows = [{"chart_uid": uid, "name": labels[uid], "likelihood": result.likelihoods[name], "deviation": result.deviations[name]}
            for uid, result in results.items() if uid in labels and uid not in hidden and name in result.deviations]
    rows.sort(key=lambda row: (-row["deviation"], -row["likelihood"], row["name"].casefold()))
    return rows if limit is None else rows[:max(0, limit)]


def accuracy_rankings(trait: dict[str, Any], progress: Callable[[float], None], should_cancel: Callable[[], bool]) -> list[dict[str, Any]]:
    from ephemeraldaddy.core.prediction_norms import trait_norm_preflight_values
    trait = {**trait, "archived": False}
    if trait["name"] not in trait_norm_preflight_values([trait]):
        raise ValueError("Stored DB norm unavailable. Generate DB Norms explicitly before rating this Trait's predictions.")
    uids = db.prediction_chart_uids()
    global_trait_prediction_index().collect(uids, [trait], calculate_missing=True, should_cancel=should_cancel, progress=lambda value: progress(value * .95))
    if should_cancel():
        return []
    progress(97.0)
    return [row for row in ranked_trait_rows(uids, trait) if row["deviation"] > 0][:40]
