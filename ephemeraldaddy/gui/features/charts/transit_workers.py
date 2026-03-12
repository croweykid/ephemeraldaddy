import datetime
from time import perf_counter
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QDialog, QWidget

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.composite import (
    TransitAspectWindowCancelled,
    find_transit_aspect_window_result,
)


class TransitAspectWindowRelay(QObject):
    ready = Signal(str, str, str, object, object, object)
    failed = Signal(str, str, str, str)


class ManagedTransitPopoutDialog(QDialog):
    """Dialog that defers close until async worker shutdown completes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._async_shutdown: Callable[[Callable[[], None]], None] | None = None
        self._shutdown_started = False
        self._allow_close = False

    def set_async_shutdown(self, callback: Callable[[Callable[[], None]], None]) -> None:
        self._async_shutdown = callback

    def closeEvent(self, event) -> None:
        if self._allow_close or self._async_shutdown is None:
            super().closeEvent(event)
            return
        if self._shutdown_started:
            event.ignore()
            return

        self._shutdown_started = True
        event.ignore()

        def _complete_close() -> None:
            if self._allow_close:
                return
            self._allow_close = True
            self.close()

        self._async_shutdown(_complete_close)


class TransitAspectWindowWorker(QObject):
    finished = Signal(str, str, str, object, object, object)
    failed = Signal(str, str, str, str)

    def __init__(
        self,
        natal_chart: Chart,
        transit_datetime: datetime.datetime,
        transit_location: tuple[float, float],
        hit: Any,
        rules: Any,
        *,
        step_hours: float,
        precision_minutes: float,
    ) -> None:
        super().__init__()
        self._natal_chart = natal_chart
        self._transit_datetime = transit_datetime
        self._transit_location = transit_location
        self._hit = hit
        self._rules = rules
        self._step_hours = float(step_hours)
        self._precision_minutes = float(precision_minutes)

    def run(self) -> None:
        key = (self._hit.a.name, self._hit.aspect, self._hit.b.name)
        diagnostics: dict[str, int | float] = {}
        started_at = perf_counter()
        try:
            result = find_transit_aspect_window_result(
                self._natal_chart,
                self._transit_datetime,
                self._transit_location,
                self._hit,
                self._rules,
                step_hours=self._step_hours,
                precision_minutes=self._precision_minutes,
                should_cancel=lambda: QThread.currentThread().isInterruptionRequested(),
                diagnostics=diagnostics,
            )
        except TransitAspectWindowCancelled:
            self.failed.emit(key[0], key[1], key[2], "Cancelled")
            return
        except Exception as exc:
            self.failed.emit(key[0], key[1], key[2], str(exc))
            return

        if result.out_of_scope:
            self.failed.emit(
                key[0],
                key[1],
                key[2],
                "Transit date is outside the configured ephemeris scope.",
            )
            return

        metadata = {
            "start_truncated_to_scope": result.start_truncated_to_scope,
            "end_truncated_to_scope": result.end_truncated_to_scope,
            "duration_s": round(perf_counter() - started_at, 4),
            "diagnostics": diagnostics,
        }
        self.finished.emit(key[0], key[1], key[2], result.start, result.end, metadata)
