"""Styled, row-clickable tables used by Transit Theme View tabs."""

from __future__ import annotations

import datetime
import html
from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    ASPECT_KEYWORDS,
    PLANET_COLORS,
    PLANET_KEYWORDS,
)
from ephemeraldaddy.core.theme_reference import THEMES
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    RELATIVE_YEAR_COLORS,
    TRANSIT_THEME_TABLE_STYLE,
)


THEME_ASPECT_ROLE = Qt.UserRole + 41

_THEME_FAMILY_FALLBACK_COLORS = {
    "self_agency_power": "#d89b48",
    "mind_language_truth": "#7fa7d8",
    "relationship_attachment_society": "#c982b5",
    "material_life_work_survival": "#7fa36d",
    "shadow_crisis_transformation": "#9b73bd",
    "change_boundaries_disappearance": "#5faea8",
    "imagination_expanded_perspective": "#8594d6",
}


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


def _aspect_key(value: object) -> str:
    return str(value).lower().replace("-", "").replace("_", "").replace(" ", "")


def _keyword_summary(body: str) -> str:
    keywords = PLANET_KEYWORDS.get(body, {})
    return str(keywords.get("summary") or next(iter(keywords.get("nouns", ())), body))


def _event_name_markup(entry: dict[str, Any]) -> str:
    """Color the semantic event-name phrases by their source bodies/aspect."""
    body_a = str(entry.get("p1", ""))
    body_b = str(entry.get("p2", ""))
    aspect = str(entry.get("type", "aspect"))
    aspect_key = _aspect_key(aspect)

    first_summary = _keyword_summary(body_a)
    second_summary = _keyword_summary(body_b)
    aspect_phrase = str(next(iter(ASPECT_KEYWORDS.get(aspect_key, ())), aspect))

    # transit_aspect_event_name() capitalizes the combined phrase. Preserve that
    # visual contract while retaining independent spans for semantic coloring.
    first_text = first_summary[:1].upper() + first_summary[1:].lower()
    aspect_text = aspect_phrase.lower()
    second_text = second_summary.lower()
    return (
        f'<span style="color:{PLANET_COLORS.get(body_a, "#f5f5f5")}">{html.escape(first_text)}</span> '
        f'<span style="color:{ASPECT_COLORS.get(aspect_key, "#f5f5f5")}">{html.escape(aspect_text)}</span> '
        f'<span style="color:{PLANET_COLORS.get(body_b, "#f5f5f5")}">{html.escape(second_text)}</span>'
    )


def _technical_aspect_markup(entry: dict[str, Any]) -> str:
    body_a = str(entry.get("p1", ""))
    body_b = str(entry.get("p2", ""))
    aspect = str(entry.get("type", "aspect"))
    aspect_key = _aspect_key(aspect)
    return (
        f'<span style="color:{PLANET_COLORS.get(body_a, "#f5f5f5")}">{html.escape(body_a)}</span> '
        f'<span style="color:{ASPECT_COLORS.get(aspect_key, "#f5f5f5")}">{html.escape(aspect.lower())}</span> '
        f'<span style="color:{PLANET_COLORS.get(body_b, "#f5f5f5")}">{html.escape(body_b)}</span>'
    )


def _rich_cell(table: QTableWidget, row: int, column: int, markup: str) -> None:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    table.setItem(row, column, item)
    label = QLabel(markup)
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label.setMargin(5)
    label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    label.setAttribute(Qt.WA_TransparentForMouseEvents)
    table.setCellWidget(row, column, label)


def _theme_definition(theme_label: str) -> dict[str, Any] | None:
    wanted = theme_label.replace("&&", "&")
    for theme in THEMES.values():
        if str(theme.get("label", "")) == wanted:
            return theme
    return None


def _theme_color(theme_label: str) -> QColor:
    """Resolve a theme color from explicit metadata or its member-body palette."""
    theme = _theme_definition(theme_label)
    if theme is None:
        return QColor(CHART_DATA_HIGHLIGHT_COLOR)

    for explicit in theme.get("color", ()):
        candidate = QColor(str(explicit))
        if candidate.isValid():
            return candidate

    body_colors = [
        QColor(PLANET_COLORS[str(body)])
        for body in theme.get("bodies", ())
        if str(body) in PLANET_COLORS and QColor(PLANET_COLORS[str(body)]).isValid()
    ]
    if body_colors:
        count = len(body_colors)
        return QColor(
            round(sum(color.red() for color in body_colors) / count),
            round(sum(color.green() for color in body_colors) / count),
            round(sum(color.blue() for color in body_colors) / count),
        )

    return QColor(
        _THEME_FAMILY_FALLBACK_COLORS.get(
            str(theme.get("family", "")),
            CHART_DATA_HIGHLIGHT_COLOR,
        )
    )


def _contrast_text(color: QColor) -> str:
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    return "#17171d" if luminance >= 145 else "#f5f5f5"


def _style_theme_button(button: QPushButton, theme_label: str) -> None:
    color = _theme_color(theme_label)
    color_hex = color.name()
    button.setStyleSheet(
        "QPushButton {"
        f"border: 1px solid {color_hex}; color: {color_hex}; background: #24242c;"
        "border-radius: 4px; padding: 4px 8px;"
        "}"
        "QPushButton:checked {"
        f"background: {color_hex}; color: {_contrast_text(color)};"
        "}"
    )


class _FlowButtonBar(QWidget):
    """A compact button strip that adds rows instead of clipping labels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._spacing = 6
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_buttons(self, buttons: Iterable[QPushButton]) -> None:
        for old in self._buttons:
            old.setParent(None)
            old.deleteLater()
        self._buttons = list(buttons)
        for button in self._buttons:
            button.setParent(self)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.ensurePolished()
            button.setMinimumWidth(button.sizeHint().width())
            button.show()
        self._relayout()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        if not self._buttons:
            self.setFixedHeight(0)
            return
        available = max(1, self.contentsRect().width())
        x = 0
        y = 0
        row_height = 0
        for button in self._buttons:
            hint = button.sizeHint()
            width = max(button.minimumWidth(), hint.width())
            height = hint.height()
            if x and x + width > available:
                x = 0
                y += row_height + self._spacing
                row_height = 0
            button.setGeometry(x, y, width, height)
            x += width + self._spacing
            row_height = max(row_height, height)
        total_height = y + row_height
        if self.height() != total_height:
            self.setFixedHeight(total_height)


class _WrappingThemeTable(QTableWidget):
    """Recompute row heights whenever wrapped columns change width."""

    def __init__(self) -> None:
        super().__init__(0, 3)
        self._last_viewport_width = -1

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        width = self.viewport().width()
        if width != self._last_viewport_width:
            self._last_viewport_width = width
            QTimer.singleShot(0, self.resizeRowsToContents)


def _build_rows_table(
    entries: Iterable[dict[str, Any]],
    *,
    row_activated: Callable[[dict[str, Any]], None],
) -> QTableWidget:
    table = _WrappingThemeTable()
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setWordWrap(True)
    table.setTextElideMode(Qt.ElideNone)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    aspect_width = table.fontMetrics().horizontalAdvance("0" * 15) + 18
    table.setColumnWidth(1, aspect_width)
    table.setStyleSheet(TRANSIT_THEME_TABLE_STYLE)

    for entry in entries:
        row = table.rowCount()
        table.insertRow(row)

        start, end = entry.get("start"), entry.get("end")
        if isinstance(start, datetime.datetime) and isinstance(end, datetime.datetime):
            start_markup = "…" if entry.get("start_truncated") else _date_html(start)
            end_markup = (
                f"after {_date_html(end)}" if entry.get("end_truncated") else _date_html(end)
            )
            date_markup = (
                start_markup
                if start == end
                and not entry.get("start_truncated")
                and not entry.get("end_truncated")
                else f"{start_markup} &ndash; {end_markup}"
            )
        else:
            date_markup = html.escape(str(entry.get("date_label", "Unknown date")))

        _rich_cell(table, row, 0, _event_name_markup(entry))
        table.item(row, 0).setData(THEME_ASPECT_ROLE, entry)
        _rich_cell(table, row, 1, _technical_aspect_markup(entry))
        _rich_cell(table, row, 2, date_markup)

    def _activate(row: int, _column: int) -> None:
        item = table.item(row, 0)
        entry = item.data(THEME_ASPECT_ROLE) if item is not None else None
        if isinstance(entry, dict):
            row_activated(entry)

    table.cellClicked.connect(_activate)
    QTimer.singleShot(0, table.resizeRowsToContents)
    return table


class ThemeAspectPage(QWidget):
    """One theme page with wrapping theme buttons and lazy time sections."""

    def __init__(
        self,
        sections: Iterable[tuple[str, Iterable[dict[str, Any]]]],
        *,
        row_activated: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__()
        self._row_activated = row_activated
        self._sections = [(str(label), tuple(entries)) for label, entries in sections]
        self._section_widgets: dict[int, QWidget] = {}
        self._theme_signature: tuple[str, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._theme_buttons = _FlowButtonBar(self)
        layout.addWidget(self._theme_buttons)

        section_bar = QHBoxLayout()
        section_bar.setContentsMargins(0, 0, 0, 0)
        section_bar.setSpacing(6)
        self._section_buttons: list[QPushButton] = []
        for index, (label, _entries) in enumerate(self._sections):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, index=index: self._select_section(index)
            )
            section_bar.addWidget(button)
            self._section_buttons.append(button)
        section_bar.addStretch(1)
        layout.addLayout(section_bar)

        self._section_stack = QStackedWidget()
        layout.addWidget(self._section_stack, 1)

        present_index = next(
            (
                index
                for index, (label, _entries) in enumerate(self._sections)
                if "present" in label.casefold()
            ),
            0,
        )
        if self._sections:
            self._select_section(present_index)

    def viewport(self) -> QWidget:
        """Compatibility with legacy QTableWidget cleanup in the popout owner."""
        current = self._section_stack.currentWidget()
        if isinstance(current, QTableWidget):
            return current.viewport()
        return self

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_theme_buttons)

    def _select_section(self, index: int) -> None:
        if not (0 <= index < len(self._sections)):
            return
        widget = self._section_widgets.get(index)
        if widget is None:
            label, entries = self._sections[index]
            if entries:
                widget = _build_rows_table(
                    entries,
                    row_activated=self._row_activated,
                )
            else:
                empty = QLabel(f"No {label.replace('🌖', '').replace('🌕', '').replace('🌒', '').strip().lower()} transits in this theme.")
                empty.setAlignment(Qt.AlignCenter)
                empty.setWordWrap(True)
                widget = empty
            self._section_widgets[index] = widget
            self._section_stack.addWidget(widget)
        self._section_stack.setCurrentWidget(widget)
        for button_index, button in enumerate(self._section_buttons):
            button.setChecked(button_index == index)

    def _ancestor_tabs(self) -> QTabWidget | None:
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parentWidget()
        return None

    def _sync_theme_buttons(self) -> None:
        tabs = self._ancestor_tabs()
        if tabs is None:
            return
        tabs.tabBar().hide()
        labels = tuple(tabs.tabText(index).replace("&&", "&") for index in range(tabs.count()))
        if labels == self._theme_signature:
            return
        self._theme_signature = labels
        current_index = tabs.currentIndex()
        buttons: list[QPushButton] = []
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(index == current_index)
            _style_theme_button(button, label)
            button.clicked.connect(
                lambda _checked=False, index=index, tabs=tabs: tabs.setCurrentIndex(index)
            )
            buttons.append(button)
        self._theme_buttons.set_buttons(buttons)


def build_theme_aspect_table(
    sections: Iterable[tuple[str, Iterable[dict[str, Any]]]],
    *,
    row_activated: Callable[[dict[str, Any]], None],
) -> ThemeAspectPage:
    """Build one Theme View page with lazy Past/Present/Future table materialization."""
    return ThemeAspectPage(sections, row_activated=row_activated)
