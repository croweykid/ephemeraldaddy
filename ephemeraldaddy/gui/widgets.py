"""Shared Qt widgets and widget helpers for the GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import QAbstractItemView, QListWidget


def handle_list_letter_jump(list_widget: QListWidget, event) -> bool:
    """Select the next item whose name starts with the typed letter."""
    if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
        return False

    typed = event.text()
    if len(typed) != 1 or not typed.isalpha():
        return False

    letter = typed.casefold()
    total = list_widget.count()
    if total <= 0:
        return False

    current_row = list_widget.currentRow()
    start_row = current_row if current_row >= 0 else -1

    for offset in range(1, total + 1):
        row = (start_row + offset) % total
        item = list_widget.item(row)
        if item is None:
            continue

        metadata = item.data(Qt.UserRole + 1)
        candidate_name = ""
        if isinstance(metadata, dict):
            candidate_name = (metadata.get("raw_name") or "").strip()
        if not candidate_name:
            candidate_name = item.text().strip()

        if candidate_name.casefold().startswith(letter):
            index = list_widget.indexFromItem(item)
            selection_model = list_widget.selectionModel()
            if selection_model is not None and index.isValid():
                selection_model.setCurrentIndex(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                list_widget.scrollTo(
                    index,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
            else:
                list_widget.clearSelection()
                item.setSelected(True)
                list_widget.setCurrentItem(item)
                list_widget.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
            return True

    return False


class ChartListWidget(QListWidget):
    """List widget with single-letter jump-to-name navigation."""

    def keyPressEvent(self, event) -> None:
        if self._handle_letter_jump(event):
            return
        super().keyPressEvent(event)

    def _handle_letter_jump(self, event) -> bool:
        return handle_list_letter_jump(self, event)
