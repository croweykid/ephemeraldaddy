"""Background score refresh for Database View's cached Weirdness sort."""
from __future__ import annotations
from typing import Iterable
from ephemeraldaddy.analysis.distinguishing_factors import calculate_weirdness_score_from_metric_payloads, DISTINGUISHING_FORMULA_VERSION
from ephemeraldaddy.core import db
from ephemeraldaddy.core.prediction_norms import distinguishing_norm_reference


def refresh_weirdness_scores(chart_uids: Iterable[str]) -> dict[str, float]:
    payloads, signature = distinguishing_norm_reference()
    if not payloads:
        return {}
    values = {}
    uids = tuple(chart_uids)
    for start in range(0, len(uids), 64):
        for uid, chart in db.load_charts_by_uids(uids[start:start + 64]).items():
            if getattr(chart, 'is_placeholder', False):
                continue
            score, _ = calculate_weirdness_score_from_metric_payloads(chart, payloads)
            if score is not None:
                db.update_chart_weirdness_score_by_uid(uid, score, formula_version=DISTINGUISHING_FORMULA_VERSION, norm_signature=signature)
                values[uid] = score
    return values
