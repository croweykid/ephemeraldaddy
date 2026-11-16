"""Refresh missing Weirdness sort values without blocking Database View."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from PySide6.QtCore import QObject, Qt, Signal, Slot
from ephemeraldaddy.analysis.distinguishing_factors import DISTINGUISHING_FORMULA_VERSION
from ephemeraldaddy.analysis.weirdness_cache import refresh_weirdness_scores
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.core.prediction_norms import distinguishing_norm_reference

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='weirdness-sort')


def apply_weirdness_results_to_rows(
    rows: list[tuple[Any, ...]], values: dict[str, float], signature: str,
) -> list[tuple[Any, ...]]:
    """Keep accepted scores and raw list_charts freshness columns in sync."""
    result = []
    for row in rows:
        uid = str(row[30] or "").strip().upper() if len(row) > 31 else ""
        if uid not in values:
            result.append(row)
            continue
        updated = list(row)
        updated[31] = values[uid]
        # Legacy 33-slot rows store provenance at 32, not freshness metadata.
        # Their normalizer keeps the separate metadata map intact.
        if len(updated) != 33:
            updated.extend([None] * max(0, 34 - len(updated)))
            updated[32:34] = (DISTINGUISHING_FORMULA_VERSION, signature)
        result.append(tuple(updated))
    return result


class WeirdnessSortController(QObject):
    completed = Signal(object, object)

    def __init__(self, parent: QObject, apply: Callable[[dict[str, float], str], None]) -> None:
        super().__init__(parent)
        self._apply = apply
        self._token: object = None
        self._attempted: object = None
        self._guards: dict[str, Callable[[], bool]] = {}
        self.completed.connect(self._deliver, Qt.QueuedConnection)

    def request_missing(self, rows: list[tuple[Any, ...]], metadata: dict[str, tuple[Any, ...]]) -> None:
        payloads, signature = distinguishing_norm_reference()
        if not payloads:
            return
        needed = tuple(str(row[30]) for row in rows if len(row) > 31 and row[30] and not bool(row[15]) and (row[31] is None or metadata.get(str(row[30])) != (DISTINGUISHING_FORMULA_VERSION, signature)))
        token = (needed, signature)
        if not needed or token == self._token:
            return
        if token == self._attempted and not any(obsolete() for obsolete in self._guards.values()):
            return
        self._token = token
        index = global_trait_prediction_index()
        self._guards = {uid: index.refresh_guard([uid], []) for uid in needed}
        future = _pool.submit(refresh_weirdness_scores, needed)
        def finished(result: Any) -> None:
            try:
                values = result.result()
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Weirdness sort refresh failed')
                values = {}
            try:
                self.completed.emit(token, values)
            except RuntimeError:
                pass
        future.add_done_callback(finished)

    @Slot(object, object)
    def _deliver(self, token: object, values: dict[str, float]) -> None:
        if token != self._token:
            return
        self._attempted = token
        self._token = None
        obsolete = {uid for uid, guard in self._guards.items() if guard()}
        accepted = {uid: value for uid, value in values.items() if uid in self._guards and uid not in obsolete}
        if accepted or obsolete:
            # Repainting even an empty accepted set lets the view request just
            # the rejected/missing UIDs again, after the chart save completes.
            self._apply(accepted, token[1])
