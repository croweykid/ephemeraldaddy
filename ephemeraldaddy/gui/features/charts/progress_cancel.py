"""Shared cancellation helpers for long-running chart progress dialogs."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication, QProgressDialog, QPushButton


class OperationCanceled(Exception):
    """Raised when the user safely cancels a long-running GUI calculation."""


CANCEL_MESSAGE = "Stopping safely before changing anything else…"


def mark_progress_canceled(progress: QProgressDialog) -> None:
    progress.setProperty("operation_canceled", True)
    progress.setLabelText(CANCEL_MESSAGE)
    cancel_button = progress.findChild(QPushButton)
    if cancel_button is not None:
        cancel_button.setEnabled(False)
    QApplication.processEvents(QEventLoop.AllEvents, 50)


def progress_was_canceled(progress: QProgressDialog | None) -> bool:
    if progress is None:
        return False
    return bool(progress.property("operation_canceled")) or progress.wasCanceled()


def raise_if_progress_canceled(progress: QProgressDialog | None) -> None:
    if progress_was_canceled(progress):
        raise OperationCanceled(CANCEL_MESSAGE)
