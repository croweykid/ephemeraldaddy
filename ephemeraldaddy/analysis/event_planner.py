"""Stub window for the Event Planner optional module."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

_EVENT_PLANNER_DARK_STYLE = """
QDialog {
    background-color: #181818;
    color: #ececec;
}
QWidget {
    background-color: #181818;
    color: #ececec;
}
"""


def create_event_planner_window(parent: QWidget | None = None) -> QDialog:
    """Create the blank dark-mode Event Planner stub window."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Event Planner")
    dialog.setWindowFlag(Qt.Window, True)
    dialog.setModal(False)
    dialog.resize(720, 520)
    dialog.setStyleSheet(_EVENT_PLANNER_DARK_STYLE)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(0)
    layout.addStretch(1)
    return dialog
