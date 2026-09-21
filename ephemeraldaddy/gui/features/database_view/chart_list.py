"""Primary chart-list widget for the Database View workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PySide6.QtCore import (
    QEventLoop,
    QItemSelectionModel,
    QPoint,
    QSignalBlocker,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from ephemeraldaddy.gui.features.charts.delegates import CHART_ROW_OPEN_FEEDBACK_ROLE
from ephemeraldaddy.gui.features.database_view.collections import chart_drag_mime_data
from ephemeraldaddy.gui.ui_helpers import handle_list_letter_jump


@dataclass(frozen=True)
class ChartRosterViewState:
    """UID-owned selection and viewport state across a roster reconstruction."""

    selected_uids: tuple[str, ...]
    current_uid: str | None
    top_visible_uid: str | None
    top_visible_offset: int
    scrollbar_value: int
    ordered_uids: tuple[str, ...]


def _item_uid(item: QListWidgetItem | None) -> str | None:
    if item is None:
        return None
    value = str(item.data(Qt.UserRole) or "").strip().upper()
    return value or None


def capture_chart_roster_view_state(
    list_widget: QListWidget,
    *,
    selected_uids: Iterable[str] | None = None,
) -> ChartRosterViewState:
    """Capture list state without relying on labels or transient row positions."""
    ordered_uids = tuple(
        uid
        for row in range(list_widget.count())
        if (uid := _item_uid(list_widget.item(row))) is not None
    )
    top_item = list_widget.itemAt(QPoint(0, 0))
    if top_item is None and list_widget.count():
        top_item = list_widget.item(0)
    return ChartRosterViewState(
        selected_uids=(
            tuple(
                str(uid).strip().upper()
                for uid in selected_uids
                if str(uid).strip()
            )
            if selected_uids is not None
            else tuple(
                uid
                for item in list_widget.selectedItems()
                if (uid := _item_uid(item)) is not None
            )
        ),
        current_uid=_item_uid(list_widget.currentItem()),
        top_visible_uid=_item_uid(top_item),
        top_visible_offset=(list_widget.visualItemRect(top_item).top() if top_item else 0),
        scrollbar_value=list_widget.verticalScrollBar().value(),
        ordered_uids=ordered_uids,
    )


def restore_chart_roster_view_state(
    list_widget: QListWidget,
    state: ChartRosterViewState,
) -> None:
    """Restore state, using the nearest old neighbor when the anchor vanished."""
    items_by_uid = {
        uid: list_widget.item(row)
        for row in range(list_widget.count())
        if (uid := _item_uid(list_widget.item(row))) is not None
    }
    signal_blocker = QSignalBlocker(list_widget)
    selected = set(state.selected_uids)
    for uid, item in items_by_uid.items():
        item.setSelected(uid in selected)
    current_item = items_by_uid.get(state.current_uid or "")
    if current_item is not None:
        list_widget.setCurrentItem(current_item, QItemSelectionModel.NoUpdate)
    del signal_blocker

    anchor_uid = state.top_visible_uid
    if anchor_uid not in items_by_uid and anchor_uid in state.ordered_uids:
        old_index = state.ordered_uids.index(anchor_uid)
        anchor_uid = next(
            (
                state.ordered_uids[index]
                for distance in range(1, len(state.ordered_uids) + 1)
                for index in (old_index + distance, old_index - distance)
                if 0 <= index < len(state.ordered_uids)
                and state.ordered_uids[index] in items_by_uid
            ),
            None,
        )
    anchor_item = items_by_uid.get(anchor_uid or "")
    scrollbar = list_widget.verticalScrollBar()
    if anchor_item is None:
        scrollbar.setValue(min(state.scrollbar_value, scrollbar.maximum()))
        return
    list_widget.scrollToItem(anchor_item, QAbstractItemView.PositionAtTop)
    scrollbar.setValue(scrollbar.value() - state.top_visible_offset)


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
