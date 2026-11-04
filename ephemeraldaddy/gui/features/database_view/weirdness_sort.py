"""Refresh missing Weirdness sort values without blocking Database View."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from PySide6.QtCore import QObject, Qt, Signal, Slot
from ephemeraldaddy.analysis.distinguishing_factors import DISTINGUISHING_FORMULA_VERSION
from ephemeraldaddy.analysis.weirdness_cache import refresh_weirdness_scores
from ephemeraldaddy.core.prediction_norms import distinguishing_norm_reference

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='weirdness-sort')


class WeirdnessSortController(QObject):
    completed = Signal(object, object)

    def __init__(self, parent: QObject, apply: Callable[[dict[str, float], str], None]) -> None:
        super().__init__(parent)
        self._apply = apply
        self._token: object = None
        self._attempted: object = None
        self.completed.connect(self._deliver, Qt.QueuedConnection)

    def request_missing(self, rows: list[tuple[Any, ...]], metadata: dict[str, tuple[Any, ...]]) -> None:
        payloads, signature = distinguishing_norm_reference()
        if not payloads:
            return
        needed = tuple(str(row[30]) for row in rows if len(row) > 31 and row[30] and not bool(row[15]) and (row[31] is None or metadata.get(str(row[30])) != (DISTINGUISHING_FORMULA_VERSION, signature)))
        token = (needed, signature)
        if not needed or token in (self._token, self._attempted):
            return
        self._token = token
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
        if values:
            self._apply(values, token[1])
