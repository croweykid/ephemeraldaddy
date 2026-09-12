"""Styled, row-clickable tables used by Transit Theme View tabs."""

from __future__ import annotations

import datetime
import html
from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QTableWidget, QTableWidgetItem

from ephemeraldaddy.core.interpretations import ASPECT_COLORS, PLANET_COLORS
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, RELATIVE_YEAR_COLORS


THEME_ASPECT_ROLE = Qt.UserRole + 41


def _year_color(year: int) -> str:
    delta = year - datetime.datetime.now(datetime.timezone.utc).year
    label = {
        -2: "year before last",
        -1: "last year",
        0: "current",
        1: "next",
        2: "year after next",
    }.get(delta, "other")
    return str(RELATIVE_YEAR_COLORS[label])


def _date_html(value: datetime.datetime) -> str:
    text = value.strftime("%m-%d-%Y")
    return f'<span style="color:{_year_color(value.year)}">{text}</span>'


def _rich_cell(table: QTableWidget, row: int, column: int, markup: str) -> None:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    table.setItem(row, column, item)
    label = QLabel(markup)
    label.setTextFormat(Qt.RichText)
    label.setMargin(5)
    label.setAttribute(Qt.WA_TransparentForMouseEvents)
    table.setCellWidget(row, column, label)


def build_theme_aspect_table(
    sections: Iterable[tuple[str, Iterable[dict[str, Any]]]],
    *,
    row_activated: Callable[[dict[str, Any]], None],
) -> QTableWidget:
    """Build a Traits-style table whose entire data rows activate Chart Info."""
    table = QTableWidget(0, 4)
    table.setHorizontalHeaderLabels(("Date Range", "Transit", "Aspect", "Natal"))
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    table.setStyleSheet(
        "QTableWidget { color:#f5f5f5; background:rgba(255,255,255,0.03); "
        "border:1px solid rgba(255,255,255,0.12); gridline-color:rgba(255,255,255,0.08); }"
        "QHeaderView::section { color:#f5f5f5; background:rgba(255,255,255,0.08); "
        "border:0; padding:3px 6px; } QTableWidget::item { padding:2px 6px; }"
    )

    for heading, entries_iter in sections:
        entries = list(entries_iter)
        header_row = table.rowCount()
        table.insertRow(header_row)
        header_item = QTableWidgetItem(heading)
        header_item.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        font = QFont(header_item.font())
        font.setBold(True)
        header_item.setFont(font)
        header_item.setFlags(Qt.ItemIsEnabled)
        table.setItem(header_row, 0, header_item)
        table.setSpan(header_row, 0, 1, 4)
        if not entries:
            empty_row = table.rowCount()
            table.insertRow(empty_row)
            empty_item = QTableWidgetItem("None")
            empty_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(empty_row, 0, empty_item)
            table.setSpan(empty_row, 0, 1, 4)
            continue
        for entry in entries:
            row = table.rowCount()
            table.insertRow(row)
            table.setRowHeight(row, 28)
            table.setItem(row, 0, QTableWidgetItem())
            table.item(row, 0).setData(THEME_ASPECT_ROLE, entry)
            start, end = entry.get("start"), entry.get("end")
            if isinstance(start, datetime.datetime) and isinstance(end, datetime.datetime):
                date_markup = (
                    _date_html(start)
                    if start == end
                    else f"{_date_html(start)} &ndash; {_date_html(end)}"
                )
            else:
                date_markup = html.escape(str(entry.get("date_label", "Unknown date")))
            _rich_cell(table, row, 0, date_markup)
            # _rich_cell replaces column zero's item, so retain activation data there.
            table.item(row, 0).setData(THEME_ASPECT_ROLE, entry)
            body_a = str(entry.get("p1", ""))
            body_b = str(entry.get("p2", ""))
            aspect = str(entry.get("type", "aspect"))
            aspect_key = aspect.lower().replace("-", "").replace("_", "").replace(" ", "")
            _rich_cell(table, row, 1, f'<span style="color:{PLANET_COLORS.get(body_a, "#f5f5f5")}">{html.escape(body_a)}</span>')
            _rich_cell(table, row, 2, f'<span style="color:{ASPECT_COLORS.get(aspect_key, "#f5f5f5")}">{html.escape(aspect.title())}</span>')
            _rich_cell(table, row, 3, f'<span style="color:{PLANET_COLORS.get(body_b, "#f5f5f5")}">{html.escape(body_b)}</span>')

    def _activate(row: int, _column: int) -> None:
        item = table.item(row, 0)
        entry = item.data(THEME_ASPECT_ROLE) if item is not None else None
        if isinstance(entry, dict):
            row_activated(entry)

    table.cellClicked.connect(_activate)
    return table
