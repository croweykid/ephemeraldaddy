from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter

from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from ephemeraldaddy.gui.style import MIDDLE_PANEL_ACCENT_COLOR
CHART_ROW_PLACE_COLOR = "#9c7a53"
HYPOTHETICAL_ROW_COLOR = "#c9b3ff"


class ChartRowDelegate(QStyledItemDelegate):
    """Renders segmented colors for Manage Charts list rows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segment_colors = {
            "status": QColor("#ff6b6b"),
            "chart": QColor("#c7a56a"),
            "name": QColor(MIDDLE_PANEL_ACCENT_COLOR),
            "alias": QColor("#7a7a7a"),
            "from_whence": QColor("#7a7a7a"),
            "date": QColor("#8d6e63"),
            "time": QColor("#6b705c"),
            "retcon_time": QColor("#4a7bd1"),
            "place": QColor(CHART_ROW_PLACE_COLOR),
        }
        self._duplicate_likelihood_colors = {
            "definite": QColor("#7CFF00"),
            "likely": QColor("#54D26A"),
            "probable_name": QColor("#54D26A"),
            "mid_birth_date": QColor("#3CB371"),
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
        alias_text = str(segment_data.get("alias", "")).strip()
        from_whence_text = str(segment_data.get("from_whence", "")).strip()
        if alias_text:
            alias_text = f"({alias_text})"
        if from_whence_text:
            from_whence_text = f"({from_whence_text})"
        chart_info_segments = self._normalize_chart_info_segments(
            segment_data.get("chart_info")
        )
        date_text = str(segment_data.get("date", "??.??.????"))
        time_text = str(segment_data.get("time", "??:??"))
        retcon_time_text = str(segment_data.get("retcon_time", ""))
        place_text = str(segment_data.get("place", ""))
        status_text = "💀" if bool(segment_data.get("is_deceased", False)) else ""

        is_placeholder = bool(segment_data.get("is_placeholder", False))
        is_hypothetical = bool(segment_data.get("is_hypothetical", False))
        duplicate_likelihood = str(segment_data.get("duplicate_likelihood", "")).strip()

        segments: list[dict[str, object]] = [
            {"key": "status", "text": status_text},
            {"key": "chart", "text": chart_text},
            {"key": "name", "text": name_text},
            {"key": "alias", "text": alias_text},
            {"key": "from_whence", "text": from_whence_text},
            *chart_info_segments,
            {"key": "date", "text": date_text},
            {"key": "time", "text": time_text},
            {"key": "retcon_time", "text": retcon_time_text},
            {"key": "place", "text": place_text},
        ]

        x = rect.x()
        for segment in segments:
            key = str(segment.get("key", ""))
            text = str(segment.get("text", ""))
            if not text:
                continue
            color_value = segment.get("color")
            color = (
                QColor(str(color_value))
                if color_value
                else self._segment_colors.get(key, opt.palette.text().color())
            )
            if is_hypothetical:
                color = QColor(HYPOTHETICAL_ROW_COLOR)
            elif is_placeholder and key != "chart_info":
                color = QColor("#4a7bd1")
            elif duplicate_likelihood and key in {
                "chart",
                "name",
                "from_whence",
                "date",
                "time",
                "retcon_time",
                "place",
            }:
                color = self._duplicate_likelihood_colors.get(duplicate_likelihood, color)
            if opt.state & QStyle.State_Selected:
                color = color.lighter(125)
            painter.setPen(color)
            if is_hypothetical or is_placeholder or key == "retcon_time":
                italic_font = painter.font()
                italic_font.setItalic(True)
                painter.setFont(italic_font)
            else:
                painter.setFont(opt.font)
            painter.drawText(x, baseline, text)
            x += metrics.horizontalAdvance(text)
            if bool(segment.get("space_after", True)):
                x += spacing
            if x >= rect.right():
                break

        painter.restore()

    @staticmethod
    def _normalize_chart_info_segments(raw_segments: object) -> list[dict[str, object]]:
        if not isinstance(raw_segments, list):
            return []

        segments: list[dict[str, object]] = []
        for raw_segment in raw_segments:
            if not isinstance(raw_segment, dict):
                continue
            text = str(raw_segment.get("text", ""))
            if not text:
                continue
            segments.append(
                {
                    "key": "chart_info",
                    "text": text,
                    "color": str(raw_segment.get("color", "")),
                    "space_after": bool(raw_segment.get("space_after", True)),
                }
            )
        return segments
