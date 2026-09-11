"""Primary chart-list widget for the Database View workflow."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QWidget

from ephemeraldaddy.gui.features.charts.delegates import CHART_ROW_OPEN_FEEDBACK_ROLE
from ephemeraldaddy.gui.features.database_view.collections import chart_drag_mime_data
from ephemeraldaddy.gui.ui_helpers import handle_list_letter_jump


class ChartListWidget(QListWidget):
    """List widget with single-letter navigation, drag support, and open feedback."""

    _OPEN_FEEDBACK_DURATION_MS = 360
    _OPEN_FEEDBACK_INTERVAL_MS = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._open_feedback_item: QListWidgetItem | None = None
        self._open_feedback_step = 0
        self._open_feedback_steps = max(
            1,
            self._OPEN_FEEDBACK_DURATION_MS // self._OPEN_FEEDBACK_INTERVAL_MS,
        )
        self._open_feedback_timer = QTimer(self)
        self._open_feedback_timer.setInterval(self._OPEN_FEEDBACK_INTERVAL_MS)
        self._open_feedback_timer.timeout.connect(self._advance_open_feedback)
        self.setDragEnabled(True)

    def mimeData(self, items: list[QListWidgetItem]):
        return chart_drag_mime_data(super().mimeData(items), items)

    def keyPressEvent(self, event) -> None:
        if self._handle_letter_jump(event):
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is not None:
            self.start_open_feedback(item)
        super().mouseDoubleClickEvent(event)

    def start_open_feedback(self, item: QListWidgetItem) -> None:
        """Immediately pulse a row so double-click acknowledgement precedes loading."""
        self._clear_open_feedback()
        self._open_feedback_item = item
        self._open_feedback_step = 0
        item.setData(CHART_ROW_OPEN_FEEDBACK_ROLE, 1.0)
        index = self.indexFromItem(item)
        if index.isValid():
            self.viewport().repaint(self.visualRect(index))
        self._open_feedback_timer.start()
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def _advance_open_feedback(self) -> None:
        item = self._open_feedback_item
        if item is None:
            self._open_feedback_timer.stop()
            return
        self._open_feedback_step += 1
        progress = max(0.0, 1.0 - (self._open_feedback_step / self._open_feedback_steps))
        item.setData(CHART_ROW_OPEN_FEEDBACK_ROLE, progress)
        index = self.indexFromItem(item)
        if index.isValid():
            self.viewport().update(self.visualRect(index))
        if progress <= 0.0:
            self._clear_open_feedback()

    def _clear_open_feedback(self) -> None:
        if self._open_feedback_item is not None:
            self._open_feedback_item.setData(CHART_ROW_OPEN_FEEDBACK_ROLE, None)
            index = self.indexFromItem(self._open_feedback_item)
            if index.isValid():
                self.viewport().update(self.visualRect(index))
        self._open_feedback_item = None
        self._open_feedback_timer.stop()

    def _handle_letter_jump(self, event) -> bool:
        return handle_list_letter_jump(self, event)
