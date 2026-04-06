from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QWidget

from ephemeraldaddy.gui.style import CHART_DATA_MONOSPACE_FONT_FAMILY


class ChartDataTableOutput(QPlainTextEdit):
    """Read-only chart output widget using legacy plain-text rendering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFrameShape(QFrame.NoFrame)

        # Keep legacy chart-data text aesthetics in the widget itself so
        # summaries remain styled even if callers forget to set panel font.
        output_font = QFont(self.font())
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        output_font.setFixedPitch(True)
        if CHART_DATA_MONOSPACE_FONT_FAMILY:
            output_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        self.setFont(output_font)
