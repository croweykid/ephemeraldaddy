"""Cancellable worker and GUI-thread relay for short Personal Transit ranges."""

from __future__ import annotations

import datetime
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .personal_timeline_generation import generate_personal_transit_range


class PersonalTransitRangeRelay(QObject):
    ready = Signal(int, object)
    failed = Signal(int, str)

    @Slot(int, object)
    def forward_ready(self, generation: int, windows: object) -> None:
        self.ready.emit(generation, windows)

    @Slot(int, str)
    def forward_failed(self, generation: int, error: str) -> None:
        self.failed.emit(generation, error)


class PersonalTransitRangeWorker(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(
        self,
        generation: int,
        chart_uid: str,
        chart: Any,
        start: datetime.datetime,
        end: datetime.datetime,
        transit_location: tuple[float, float],
    ) -> None:
        super().__init__()
        self._generation = generation
        self._chart_uid = chart_uid
        self._chart = chart
        self._start = start
        self._end = end
        self._transit_location = transit_location

    @Slot()
    def run(self) -> None:
        thread = QThread.currentThread()
        try:
            windows = generate_personal_transit_range(
                self._chart_uid,
                self._chart,
                start=self._start,
                end=self._end,
                cancelled=thread.isInterruptionRequested,
                transit_location=self._transit_location,
            )
        except Exception as exc:
            self.failed.emit(self._generation, str(exc))
            return
        if thread.isInterruptionRequested():
            self.failed.emit(self._generation, "Cancelled")
            return
        self.finished.emit(self._generation, windows)
