from __future__ import annotations

from PySide6.QtWidgets import QFrame, QPlainTextEdit, QWidget


class ChartDataTableOutput(QPlainTextEdit):
    """Read-only chart output widget using plain text rendering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFrameShape(QFrame.NoFrame)
