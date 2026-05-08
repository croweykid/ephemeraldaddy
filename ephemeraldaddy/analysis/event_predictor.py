"""Stub UI for the Event Predictor optional module."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget


EVENT_PREDICTOR_WINDOW_STYLE = """
QDialog {
    background-color: #111111;
    color: #f5f5f5;
}
QWidget {
    background-color: #111111;
    color: #f5f5f5;
}
"""


def create_event_predictor_window(parent: QWidget | None = None) -> QDialog:
    """Create the blank dark-mode Event Predictor window."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Event Predictor")
    dialog.setWindowFlag(Qt.Window, True)
    dialog.resize(720, 520)
    dialog.setStyleSheet(EVENT_PREDICTOR_WINDOW_STYLE)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    return dialog
