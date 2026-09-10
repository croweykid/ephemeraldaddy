"""GUI-thread delivery boundaries for background-worker terminal signals.

PySide receiverless Python callables connected directly to signals emitted by a
``QObject`` living in a ``QThread`` do not provide a QObject thread-affinity
boundary. Terminal callbacks frequently update widgets or open dialogs, which
must run on the QApplication/main thread (and are fatal off-thread on macOS).

These small relays are created and parented on the GUI thread. Worker signals
connect to their typed slots with ``Qt.QueuedConnection``; the slots then invoke
the ordinary Python callbacks only after Qt has delivered the event to the
relay's GUI-thread event loop.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Slot


class SimilarChartsUiRelay(QObject):
    """Deliver Similar Charts completion/failure callbacks on the GUI thread."""

    def __init__(
        self,
        parent: QObject,
        *,
        on_finished: Callable[[str, object], None],
        on_failed: Callable[[str, str, object], None],
    ) -> None:
        super().__init__(parent)
        self._on_finished = on_finished
        self._on_failed = on_failed

    @Slot(str, object)
    def handle_finished(self, request_id: str, payload: object) -> None:
        try:
            self._on_finished(request_id, payload)
        finally:
            self.deleteLater()

    @Slot(str, str, object)
    def handle_failed(self, request_id: str, message: str, error: object) -> None:
        try:
            self._on_failed(request_id, message, error)
        finally:
            self.deleteLater()


class PlanetDynamicsUiRelay(QObject):
    """Deliver Planet Dynamics completion/failure callbacks on the GUI thread."""

    def __init__(
        self,
        parent: QObject,
        *,
        on_finished: Callable[[str, tuple[object, ...], object], None],
        on_failed: Callable[[str, tuple[object, ...], str], None],
    ) -> None:
        super().__init__(parent)
        self._on_finished = on_finished
        self._on_failed = on_failed

    @Slot(str, tuple, object)
    def handle_finished(
        self,
        request_id: str,
        signature: tuple[object, ...],
        scores: object,
    ) -> None:
        try:
            self._on_finished(request_id, signature, scores)
        finally:
            self.deleteLater()

    @Slot(str, tuple, str)
    def handle_failed(
        self,
        request_id: str,
        signature: tuple[object, ...],
        message: str,
    ) -> None:
        try:
            self._on_failed(request_id, signature, message)
        finally:
            self.deleteLater()


class TraitReassessmentUiRelay(QObject):
    """Deliver Trait norm reassessment results before any dialog is created."""

    def __init__(
        self,
        parent: QObject,
        *,
        on_finished: Callable[[dict[str, str]], None],
        on_failed: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self._on_finished = on_finished
        self._on_failed = on_failed

    @Slot(dict)
    def handle_finished(self, report: dict[str, str]) -> None:
        try:
            self._on_finished(report)
        finally:
            self.deleteLater()

    @Slot(str)
    def handle_failed(self, message: str) -> None:
        try:
            self._on_failed(message)
        finally:
            self.deleteLater()
