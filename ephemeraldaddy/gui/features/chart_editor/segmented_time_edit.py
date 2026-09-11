"""Time-entry widget used by the Chart Editor workflow."""

from __future__ import annotations

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtWidgets import QLineEdit, QWidget

from ephemeraldaddy.gui.style import CHART_VIEW_TIME_OVERWRITE_ENABLED


class SegmentedTimeEdit(QLineEdit):
    """Compact HH:mm editor with overwrite behavior and colon-safe navigation."""

    timeChanged = Signal(QTime)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_time = QTime(12, 0)
        self.setAlignment(Qt.AlignCenter)
        self.setMaxLength(5)
        self.setInputMask("99:99")
        self.setTime(self._current_time)

    def setDisplayFormat(self, _format: str) -> None:
        """Compatibility shim with QTimeEdit API."""
        return

    def time(self) -> QTime:
        return self._current_time

    def setTime(self, value: QTime) -> None:
        normalized = value if isinstance(value, QTime) and value.isValid() else QTime(12, 0)
        self._current_time = normalized
        self.setText(f"{normalized.hour():02d}:{normalized.minute():02d}")
        if self.cursorPosition() == 2:
            self.setCursorPosition(3)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key_Backspace:
            cursor = self.cursorPosition()
            if cursor == 3:
                self.setCursorPosition(1)
            elif cursor == 2:
                self.setCursorPosition(1)
            super().keyPressEvent(event)
            self._normalize_and_emit()
            return
        if key in (Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            super().keyPressEvent(event)
            if self.cursorPosition() == 2:
                if key == Qt.Key_Left:
                    self.setCursorPosition(1)
                else:
                    self.setCursorPosition(3)
            self._normalize_and_emit()
            return
        if event.text().isdigit() and CHART_VIEW_TIME_OVERWRITE_ENABLED:
            super().keyPressEvent(event)
            if self.cursorPosition() == 2:
                self.setCursorPosition(3)
            self._normalize_and_emit()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self.cursorPosition() == 2:
            self.setCursorPosition(3)

    def _normalize_and_emit(self) -> None:
        text = self.text()
        digits = [char for char in text if char.isdigit()]
        if len(digits) < 4:
            return
        hour = min(23, int("".join(digits[:2])))
        minute = min(59, int("".join(digits[2:4])))
        normalized = QTime(hour, minute)
        normalized_text = f"{hour:02d}:{minute:02d}"
        if text != normalized_text:
            cursor_position = self.cursorPosition()
            self.setText(normalized_text)
            self.setCursorPosition(3 if cursor_position == 2 else min(cursor_position, len(normalized_text)))
        if normalized != self._current_time:
            self._current_time = normalized
            self.timeChanged.emit(self._current_time)
