"""Deliver shared prediction-cache completion on the Qt GUI thread."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import QObject, Signal, Slot, Qt
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index


class TraitRefreshRelay(QObject):
    completed = Signal(object, object)

    def __init__(self, parent: QObject, callback: Callable[[frozenset[str], frozenset[str]], None]) -> None:
        super().__init__(parent)
        self._callback = callback
        self.completed.connect(self._deliver, Qt.QueuedConnection)
        unsubscribe = global_trait_prediction_index().subscribe(self.completed.emit)
        self.destroyed.connect(lambda *_: unsubscribe())

    @Slot(object, object)
    def _deliver(self, chart_uids: frozenset[str], trait_uids: frozenset[str]) -> None:
        self._callback(chart_uids, trait_uids)
