"""Small reusable Qt UI helpers shared across panels."""

from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QWidget


class EmojiTiledPanel(QWidget):
    """Panel container that paints a subtle tiled emoji background."""

    def __init__(
        self,
        emoji: str,
        font_size: int,
        opacity: float,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._emoji = emoji
        self._tile_font = QFont(self.font())
        self._tile_font.setPointSize(font_size)
        self._tile_opacity = max(0.0, min(1.0, float(opacity)))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        if self._tile_opacity <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setPen(Qt.white)
        painter.setFont(self._tile_font)
        painter.setOpacity(self._tile_opacity)

        metrics = QFontMetrics(self._tile_font)
        tile_width = max(1, metrics.horizontalAdvance(self._emoji) + 28)
        tile_height = max(1, metrics.height() + 28)
        baseline_offset = metrics.ascent()

        for y in range(0, self.height() + tile_height, tile_height):
            for x in range(0, self.width() + tile_width, tile_width):
                painter.drawText(x, y + baseline_offset, self._emoji)


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
