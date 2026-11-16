"""Qt job boundary for a value-only Trait calculation request."""
from __future__ import annotations
import copy
import threading
from typing import Any
from PySide6.QtCore import QObject, QThread, Signal, Slot
from ephemeraldaddy.analysis.trait_chart_prediction import calculate_chart_prediction
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index


class TraitPredictionWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(object, str)

    def __init__(self, chart: Any, traits: list[dict[str, Any]], token: object, *, include_gender: bool = False) -> None:
        super().__init__()
        self._chart = copy.deepcopy(chart)
        self._traits = copy.deepcopy(traits)
        self._token = token
        self._include_gender = include_gender
        self._cancelled = threading.Event()
        self._obsolete = global_trait_prediction_index().refresh_guard([str(getattr(chart, 'chart_uid', '') or '').upper()], traits)

    @Slot()
    def cancel(self) -> None:
        self._cancelled.set()

    def _is_cancelled(self) -> bool:
        return self._cancelled.is_set() or self._obsolete() or QThread.currentThread().isInterruptionRequested()

    @Slot()
    def run(self) -> None:
        if self._is_cancelled():
            self.failed.emit(self._token, 'cancelled')
            return
        try:
            metadata = calculate_chart_prediction(self._chart, self._traits, include_gender=self._include_gender, should_cancel=self._is_cancelled)
            if self._is_cancelled() or metadata is None:
                self.failed.emit(self._token, 'cancelled')
            else:
                self.finished.emit(self._token, metadata)
        except Exception as exc:
            self.failed.emit(self._token, str(exc))
