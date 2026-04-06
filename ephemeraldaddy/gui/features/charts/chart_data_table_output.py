from __future__ import annotations

import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ephemeraldaddy.core.interpretations import HOUSE_COLORS, PLANET_COLORS, SIGN_COLORS
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR

_DIVIDER = "---------"
_SECTION_NAMES = {
    "POSITIONS",
    "HOUSES",
    "ASPECTS",
    "D&D-ification",
    "D&D STATBLOCK",
    "CURSEDNESS",
    "Top 3 Species",
    "Top 3 Classes* (alpha phase prototype, not amazing yet)",
}


class ChartDataTableOutput(QPlainTextEdit):
    """Read-only chart output that renders section data as real QTableWidget tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFrameShape(QFrame.NoFrame)
        palette = self.palette()
        transparent_text = QColor(0, 0, 0, 0)
        palette.setColor(QPalette.Text, transparent_text)
        palette.setColor(QPalette.HighlightedText, transparent_text)
        self.setPalette(palette)
        self._plain_text = ""
        self._content_height = 0

        self._content_widget = QWidget(self.viewport())
        self._content_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._layout = QVBoxLayout(self._content_widget)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(6)

        self.verticalScrollBar().valueChanged.connect(self._position_content_widget)
        self.horizontalScrollBar().valueChanged.connect(self._position_content_widget)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_content_widget()

    def clear(self) -> None:
        self.setPlainText("")

    def toPlainText(self) -> str:
        return self._plain_text

    def setPlainText(self, text: str) -> None:
        self._plain_text = text or ""
        super().setPlainText(self._plain_text)
        self._rebuild_tables(self._plain_text)

    def _clear_layout(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _position_content_widget(self) -> None:
        viewport_rect = self.viewport().rect()
        width = max(viewport_rect.width(), self._content_widget.sizeHint().width())
        height = max(viewport_rect.height(), self._content_height)
        x = -self.horizontalScrollBar().value()
        y = -self.verticalScrollBar().value()
        self._content_widget.setGeometry(x, y, width, height)

    def _rebuild_tables(self, text: str) -> None:
        self._clear_layout()
        lines = [line.rstrip("\n") for line in text.splitlines()]
        section = "HEADER"
        bucket: list[str] = []

        def flush() -> None:
            if not bucket:
                return
            table = self._build_section_table(section, bucket)
            if table is not None:
                self._layout.addWidget(table)

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == _DIVIDER and i + 1 < len(lines) and lines[i + 1].strip() in _SECTION_NAMES:
                flush()
                section = lines[i + 1].strip()
                bucket = []
                i += 3
                continue
            bucket.append(line)
            i += 1

        flush()
        self._layout.addStretch(1)
        self._content_height = self._layout.sizeHint().height() + self._layout.contentsMargins().top() + self._layout.contentsMargins().bottom()
        self._position_content_widget()

    def _build_section_table(self, section: str, rows: list[str]) -> QTableWidget | None:
        parsed_rows = [self._parse_row(section, row) for row in rows if row.strip()]
        parsed_rows = [row for row in parsed_rows if row]
        if not parsed_rows:
            return None

        col_count = max(len(row) for row in parsed_rows)
        table = QTableWidget(len(parsed_rows), col_count)
        table.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        table.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setSortingEnabled(False)
        table.setFrameShape(QFrame.NoFrame)

        for r, row in enumerate(parsed_rows):
            for c in range(col_count):
                value = row[c] if c < len(row) else ""
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsEnabled)
                self._apply_item_style(item, section, c, value)
                table.setItem(r, c, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        width = table.verticalHeader().width() + 2 * table.frameWidth() + sum(table.columnWidth(i) for i in range(col_count))
        table.setMaximumWidth(width + 8)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        height = table.horizontalHeader().height() + 2 * table.frameWidth() + sum(table.rowHeight(i) for i in range(table.rowCount()))
        table.setFixedHeight(height + 4)
        return table

    def _parse_row(self, section: str, line: str) -> list[str]:
        if section == "HEADER":
            if ":" in line:
                left, right = line.split(":", 1)
                return [left.strip() + ":", right.strip()]
            return [line.strip()]
        if section == "POSITIONS":
            if "->" in line:
                return [line.strip()]
            if line.startswith("☉") or line.startswith("☽") or line.startswith("☿") or line.startswith("♀") or line.startswith("♂") or line.startswith("♃") or line.startswith("♄") or line.startswith("♅") or line.startswith("♆") or line.startswith("♇") or line.startswith("⚷") or line.startswith("⚳") or line.startswith("⚴") or line.startswith("⚵") or line.startswith("⚶") or line.startswith("🌅") or line.startswith("☊") or line.startswith("☋"):
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 4:
                    return parts[:5]
                first, *rest = line.strip().split(maxsplit=1)
                return [first, rest[0] if rest else ""]
            return re.split(r"\s{2,}", line.strip())
        if section == "HOUSES":
            if ":" in line:
                left, right = line.split(":", 1)
                right_parts = right.strip().split()
                if len(right_parts) >= 2:
                    return [left.strip() + ":", right_parts[0], " ".join(right_parts[1:])]
                return [left.strip() + ":", right.strip()]
            return [line.strip()]
        if section == "ASPECTS":
            core = line.replace("ⓘ", "").strip()
            return re.split(r"\s{2,}", core)
        if section == "D&D-ification":
            return re.split(r"\s{2,}", line.strip())
        return [line.strip()]

    def _apply_item_style(self, item: QTableWidgetItem, section: str, column: int, value: str) -> None:
        text = value.strip()
        font = item.font()

        if section in {"HEADER", "D&D-ification"} or text in {"Statblock ⓘ", "Top 3 Species"} or text.startswith("Top 3 Classes"):
            font.setBold(True)
            item.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        if section == "POSITIONS":
            if column == 0:
                for planet, color in PLANET_COLORS.items():
                    if color and planet in text:
                        item.setForeground(QColor(color))
                        break
            if column == 1:
                for sign, color in SIGN_COLORS.items():
                    if color and sign in text:
                        item.setForeground(QColor(color))
                        break
            if column == 4 and text.startswith("H"):
                color = HOUSE_COLORS.get(text[1:])
                if color:
                    item.setForeground(QColor(color))
        if section == "HOUSES" and column == 0:
            house_num = text.replace(":", "")
            if house_num.isdigit():
                color = HOUSE_COLORS.get(house_num)
                if color:
                    item.setForeground(QColor(color))
        if section == "ASPECTS" and column == 1:
            aspect_color = {
                "Conjunction": "#c7a56a",
                "Sextile": "#6b8ba4",
                "Square": "#8d6e63",
                "Trine": "#6b705c",
                "Opposition": "#c26d3a",
            }.get(text)
            if aspect_color:
                item.setForeground(QColor(aspect_color))

        item.setFont(font)
