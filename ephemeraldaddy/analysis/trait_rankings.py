"""Rank persisted Trait scores against the selected static population reference."""
from __future__ import annotations
from typing import Any, Callable, Iterable
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.core import db


def ranked_trait_rows(chart_uids: Iterable[str], trait: dict[str, Any], *, hidden_uids: Iterable[str] = (), limit: int | None = None) -> list[dict[str, Any]]:
    name = str(trait["name"])
    index = global_trait_prediction_index()
    results = index.results_for_uids(chart_uids, [trait])
    labels = db.prediction_chart_labels(results)
    hidden = set(hidden_uids)
    rows = [{"chart_uid": uid, "name": labels[uid], "likelihood": result.likelihoods[name], "deviation": result.deviations[name]}
            for uid, result in results.items() if uid in labels and uid not in hidden and name in result.deviations]
    rows.sort(key=lambda row: (-row["deviation"], -row["likelihood"], row["name"].casefold()))
    return rows if limit is None else rows[:max(0, limit)]


def accuracy_rankings(trait: dict[str, Any], progress: Callable[[float], None], should_cancel: Callable[[], bool]) -> list[dict[str, Any]]:
    from ephemeraldaddy.core.prediction_norms import prediction_norms_reference, trait_norm_values
    trait = {**trait, "archived": False}
    reference = prediction_norms_reference()
    if not any(
        trait["name"] in trait_norm_values([trait], reference, include_houses=mode)
        for mode in (False, True)
    ):
        raise ValueError("Stored DB norm unavailable. Generate DB Norms explicitly before rating this Trait's predictions.")
    uids = db.prediction_chart_uids()
    global_trait_prediction_index().collect(uids, [trait], calculate_missing=True, should_cancel=should_cancel, progress=lambda value: progress(value * .95))
    if should_cancel():
        return []
    progress(97.0)
    return [row for row in ranked_trait_rows(uids, trait) if row["deviation"] > 0][:40]
