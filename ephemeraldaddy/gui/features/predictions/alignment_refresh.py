"""Queue automatic alignment scoring without doing numerical work in render()."""
from __future__ import annotations
import copy
from typing import Any, Callable
from PySide6.QtCore import QObject, Qt, Signal, Slot
from ephemeraldaddy.analysis.dnd.alignment_predictions import alignment_parts, alignment_traits
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index
from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature
from ephemeraldaddy.core.prediction_norms import trait_norm_signature


class AlignmentRefreshController(QObject):
    completed = Signal(object, object)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._token: object = None
        self._done: object = None
        self._parts: dict[str, Any] | None = None
        self._apply: Callable[..., Any] | None = None
        self.completed.connect(self._deliver, Qt.QueuedConnection)

    def request(self, chart: Any, apply: Callable[[dict[str, Any]], None]) -> dict[str, Any] | None:
        token = (str(getattr(chart, 'chart_uid', '') or ''), chart_prediction_signature(chart), tuple(trait_norm_signature(t) for t in alignment_traits()))
        self._apply = apply
        if token == self._done:
            return self._parts
        if token == self._token:
            return None
        self._token = token
        snapshot = copy.deepcopy(chart)
        def calculate() -> None:
            try:
                parts = alignment_parts(snapshot, calculate=True)
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Automatic alignment calculation failed')
                parts = {}
            try:
                self.completed.emit(token, parts)
            except RuntimeError:
                pass
        global_trait_prediction_index().enqueue(calculate, key=('alignment-view', id(self), token))

    def invalidate(self) -> None:
        self._token = None
        self._apply = None

    @Slot(object, object)
    def _deliver(self, token: object, parts: dict[str, Any]) -> None:
        if token != self._token:
            return
        self._done = token
        self._parts = parts
        self._token = None
        if self._apply:
            self._apply(parts)
