"""Asynchronous controller for Chart Editor fine-tune hourly scans."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .hourly_scan import (
    FineTuneHourlyScanRequest,
    FineTuneHourlyScanResult,
    compute_fine_tune_hourly_scan,
    fine_tune_calculation_signature,
)


class _FineTuneWorkerSignals(QObject):
    completed = Signal(int, object)
    failed = Signal(int, str)


class _FineTuneWorker(QRunnable):
    def __init__(
        self,
        token: int,
        chart: Any,
        request: FineTuneHourlyScanRequest,
        compute: Callable[[Any, FineTuneHourlyScanRequest], FineTuneHourlyScanResult],
    ) -> None:
        super().__init__()
        self.token = token
        self.chart = chart
        self.request = request
        self.compute = compute
        self.signals = _FineTuneWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.compute(self.chart, self.request)
        except Exception as exc:
            self.signals.failed.emit(self.token, str(exc))
            return
        self.signals.completed.emit(self.token, result)


class FineTuneHourlyScanController(QObject):
    """Run fine-tune calculations off-thread and discard superseded results."""

    started = Signal(object)
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        thread_pool: QThreadPool | None = None,
        compute: Callable[
            [Any, FineTuneHourlyScanRequest], FineTuneHourlyScanResult
        ] = compute_fine_tune_hourly_scan,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._compute = compute
        self._generation = 0
        self._active_chart_uid = ""
        self._active_calculation_signature: tuple[object, ...] = ()
        self._workers: set[_FineTuneWorker] = set()

    def start(self, chart: Any, request: FineTuneHourlyScanRequest) -> int:
        self._generation += 1
        token = self._generation
        self._active_chart_uid = request.chart_uid
        self._active_calculation_signature = fine_tune_calculation_signature(chart)
        worker = _FineTuneWorker(token, chart, request, self._compute)
        self._workers.add(worker)
        worker.signals.completed.connect(
            lambda completed_token, result, active=worker: self._complete(
                active, completed_token, result
            )
        )
        worker.signals.failed.connect(
            lambda failed_token, message, active=worker: self._fail(
                active, failed_token, message
            )
        )
        self.started.emit(request)
        self._thread_pool.start(worker)
        return token

    def invalidate(self) -> None:
        """Make every outstanding result stale without blocking its worker."""
        self._generation += 1
        self._active_chart_uid = ""
        self._active_calculation_signature = ()

    def _complete(
        self, worker: _FineTuneWorker, token: int, result: FineTuneHourlyScanResult
    ) -> None:
        self._workers.discard(worker)
        if token != self._generation or result.chart_uid != self._active_chart_uid:
            return
        if fine_tune_calculation_signature(worker.chart) != self._active_calculation_signature:
            return
        self.result_ready.emit(result)

    def _fail(self, worker: _FineTuneWorker, token: int, message: str) -> None:
        self._workers.discard(worker)
        if token != self._generation:
            return
        self.failed.emit(message)
