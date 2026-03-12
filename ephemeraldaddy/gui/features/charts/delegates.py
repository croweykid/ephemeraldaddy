from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from ephemeraldaddy.gui.style import MIDDLE_PANEL_ACCENT_COLOR

from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)


class ChartRowDelegate(QStyledItemDelegate):
    """Renders segmented colors for Manage Charts list rows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segment_colors = {
            "chart": QColor("#c7a56a"),
            "name": QColor(MIDDLE_PANEL_ACCENT_COLOR),
            "date": QColor("#8d6e63"),
            "time": QColor("#6b705c"),
            "retcon_time": QColor("#4a7bd1"),
            "place": QColor("#9c7a53"),
        }

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        segment_data = index.data(Qt.UserRole + 1)
        if not isinstance(segment_data, dict):
            super().paint(painter, option, index)
            return

        painter.save()
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, widget)

        rect = opt.rect.adjusted(8, 0, -8, 0)
        metrics = QFontMetrics(opt.font)
        baseline = rect.y() + (rect.height() + metrics.ascent() - metrics.descent()) // 2
        spacing = metrics.horizontalAdvance("  ")

        position_text = str(segment_data.get("position", "?"))
        chart_text = f"#{position_text}"
        name_text = str(segment_data.get("name", "Unnamed"))
        date_text = str(segment_data.get("date", "??.??.????"))
        time_text = str(segment_data.get("time", "??:??"))
        retcon_time_text = str(segment_data.get("retcon_time", ""))
        place_text = str(segment_data.get("place", ""))

        is_placeholder = bool(segment_data.get("is_placeholder", False))

        segments = [
            ("chart", chart_text),
            ("name", name_text),
            ("date", date_text),
            ("time", time_text),
            ("retcon_time", retcon_time_text),
            ("place", place_text),
        ]

        x = rect.x()
        for key, text in segments:
            if not text:
                continue
            color = self._segment_colors.get(key, opt.palette.text().color())
            if is_placeholder:
                color = QColor("#4a7bd1")
            if opt.state & QStyle.State_Selected:
                color = color.lighter(125)
            painter.setPen(color)
            if is_placeholder or key == "retcon_time":
                italic_font = painter.font()
                italic_font.setItalic(True)
                painter.setFont(italic_font)
            else:
                painter.setFont(opt.font)
            painter.drawText(x, baseline, text)
            x += metrics.horizontalAdvance(text) + spacing
            if x >= rect.right():
                break

        painter.restore()

