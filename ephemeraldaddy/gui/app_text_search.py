"""Reusable in-window text search bar for application popout windows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QTextCharFormat, QTextCursor, QColor, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


_HIGHLIGHT_STYLE = "background-color: #9b5cff; color: #ffffff;"
_CURRENT_HIGHLIGHT_STYLE = "background-color: #d58cff; color: #170026; font-weight: 700;"
_TAG_RE = re.compile(r"(<[^>]+>)")


@dataclass
class _TextMatch:
    widget: QWidget
    start: int = 0
    length: int = 0


@dataclass
class _LabelHighlightState:
    original_html: str
    highlighted_html: str


class AppTextSearchBar(QWidget):
    """Small Ctrl/Cmd+F search bar that highlights text inside a root widget."""

    def __init__(self, root: QWidget, *, parent: QWidget | None = None) -> None:
        super().__init__(parent or root)
        self._root = root
        self._matches: list[_TextMatch] = []
        self._current_index = -1
        self._label_highlights: dict[QLabel, _LabelHighlightState] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        label = QLabel("Find:")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search this window")
        self.search_button = QPushButton("Search")
        self.case_sensitive_checkbox = QCheckBox("case-sensitive")
        self.previous_button = QPushButton("<<")
        self.next_button = QPushButton(">>")
        self.results_label = QLabel("0 results")
        self.results_label.setMinimumWidth(110)

        layout.addWidget(label)
        layout.addWidget(self.query_input, 1)
        layout.addWidget(self.search_button)
        layout.addWidget(self.case_sensitive_checkbox)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.results_label)

        self.setVisible(False)
        self.setStyleSheet(
            "QWidget { background: #21142f; color: #f7f0ff; } "
            "QLineEdit { background: #120b1c; color: #ffffff; border: 1px solid #9b5cff; padding: 3px; } "
            "QPushButton { padding: 3px 8px; }"
        )
        self.search_button.clicked.connect(self.search)
        self.query_input.returnPressed.connect(self.search)
        self.case_sensitive_checkbox.stateChanged.connect(lambda _state: self.search())
        self.previous_button.clicked.connect(self.previous_result)
        self.next_button.clicked.connect(self.next_result)

        for sequence in (QKeySequence.Find, QKeySequence("Meta+F")):
            shortcut = QShortcut(sequence, root)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.open_bar)

    def open_bar(self) -> None:
        self.setVisible(True)
        self.query_input.setFocus(Qt.ShortcutFocusReason)
        self.query_input.selectAll()

    def search(self) -> None:
        self._clear_highlights()
        query = self.query_input.text()
        if not query:
            self._matches = []
            self._current_index = -1
            self._update_indicator()
            return
        flags = 0 if self.case_sensitive_checkbox.isChecked() else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        self._matches = []
        for widget in self._searchable_widgets():
            if isinstance(widget, QLabel):
                text = widget.text()
                plain = _TAG_RE.sub("", widget.text())
                found = list(pattern.finditer(plain))
                if found:
                    highlighted_html = self._highlight_label_html(text, pattern, current_plain_index=None)
                    self._label_highlights[widget] = _LabelHighlightState(
                        original_html=text,
                        highlighted_html=highlighted_html,
                    )
                    widget.setText(highlighted_html)
                    self._matches.extend(_TextMatch(widget) for _ in found)
            elif isinstance(widget, QTextEdit):
                plain = widget.toPlainText()
                for match in pattern.finditer(plain):
                    self._matches.append(_TextMatch(widget, match.start(), match.end() - match.start()))
                self._highlight_text_edit(widget, pattern)
        self._current_index = 0 if self._matches else -1
        self._render_current_result()

    def next_result(self) -> None:
        if not self._matches:
            return
        self._current_index = (self._current_index + 1) % len(self._matches)
        self._render_current_result()

    def previous_result(self) -> None:
        if not self._matches:
            return
        self._current_index = (self._current_index - 1) % len(self._matches)
        self._render_current_result()

    def _searchable_widgets(self) -> Iterable[QWidget]:
        for widget in self._root.findChildren(QWidget):
            if self.isAncestorOf(widget) or widget is self:
                continue
            if not widget.isVisible():
                continue
            if isinstance(widget, (QLabel, QTextEdit)):
                yield widget
            elif isinstance(widget, QAbstractButton) and widget.text():
                # Button text is counted but not highlighted; currently unused by panels.
                continue

    def _clear_highlights(self) -> None:
        for label, state in list(self._label_highlights.items()):
            if label.text() == state.highlighted_html:
                label.setText(state.original_html)
        self._label_highlights.clear()
        for text_edit in self._root.findChildren(QTextEdit):
            text_edit.setExtraSelections([])

    def _highlight_label_html(self, text: str, pattern: re.Pattern[str], *, current_plain_index: int | None) -> str:
        parts = _TAG_RE.split(text)
        visible_match_index = 0
        highlighted: list[str] = []
        for part in parts:
            if not part:
                continue
            if part.startswith("<") and part.endswith(">"):
                highlighted.append(part)
                continue
            def repl(match: re.Match[str]) -> str:
                nonlocal visible_match_index
                style = _CURRENT_HIGHLIGHT_STYLE if current_plain_index == visible_match_index else _HIGHLIGHT_STYLE
                visible_match_index += 1
                return f'<span style="{style}">{match.group(0)}</span>'
            highlighted.append(pattern.sub(repl, part))
        return "".join(highlighted)

    def _highlight_text_edit(self, widget: QTextEdit, pattern: re.Pattern[str]) -> None:
        selections = []
        document = widget.document()
        for match in pattern.finditer(widget.toPlainText()):
            selection = QTextEdit.ExtraSelection()
            cursor = QTextCursor(document)
            cursor.setPosition(match.start())
            cursor.setPosition(match.end(), QTextCursor.KeepAnchor)
            selection.cursor = cursor
            selection.format = QTextCharFormat()
            selection.format.setBackground(QColor("#9b5cff"))
            selection.format.setForeground(QColor("#ffffff"))
            selections.append(selection)
        widget.setExtraSelections(selections)

    def _render_current_result(self) -> None:
        query = self.query_input.text()
        flags = 0 if self.case_sensitive_checkbox.isChecked() else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags) if query else None
        if pattern is not None:
            # Re-render every matched label so only the active result uses the current-result shade.
            current_label_index: dict[QLabel, int] = {}
            label_seen: dict[QLabel, int] = {}
            for index, match in enumerate(self._matches):
                if isinstance(match.widget, QLabel):
                    local_index = label_seen.get(match.widget, 0)
                    if index == self._current_index:
                        current_label_index[match.widget] = local_index
                    label_seen[match.widget] = local_index + 1
            for label, state in self._label_highlights.items():
                highlighted_html = self._highlight_label_html(
                    state.original_html,
                    pattern,
                    current_plain_index=current_label_index.get(label),
                )
                state.highlighted_html = highlighted_html
                label.setText(highlighted_html)
        if 0 <= self._current_index < len(self._matches):
            match = self._matches[self._current_index]
            if isinstance(match.widget, QTextEdit):
                cursor = match.widget.textCursor()
                cursor.setPosition(match.start)
                cursor.setPosition(match.start + match.length, QTextCursor.KeepAnchor)
                match.widget.setTextCursor(cursor)
                match.widget.ensureCursorVisible()
            self._ensure_widget_visible(match.widget)
            match.widget.setFocus(Qt.OtherFocusReason)
        self._update_indicator()

    def _ensure_widget_visible(self, widget: QWidget) -> None:
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                parent.ensureWidgetVisible(widget)
                return
            parent = parent.parentWidget()

    def _update_indicator(self) -> None:
        total = len(self._matches)
        if total <= 0:
            text = "0 results"
        else:
            text = f"{self._current_index + 1}/{total} results"
        self.results_label.setText(text)
        self.previous_button.setEnabled(total > 0)
        self.next_button.setEnabled(total > 0)


def install_app_text_search(root: QWidget, layout: QHBoxLayout | QVBoxLayout) -> AppTextSearchBar:
    """Install a reusable text-search bar as the first item in a window layout."""

    search_bar = AppTextSearchBar(root, parent=root)
    layout.insertWidget(0, search_bar)
    return search_bar
