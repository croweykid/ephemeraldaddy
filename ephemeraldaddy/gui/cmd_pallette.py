"""Command palette / quick switcher UI for app-wide actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class CommandPaletteAction:
    """A single command palette entry."""

    title: str
    callback: Callable[[], None]
    keywords: tuple[str, ...] = field(default_factory=tuple)
    subtitle: str = ""

    def searchable_text(self) -> str:
        return " ".join((self.title, self.subtitle, *self.keywords)).lower()


class CommandPaletteDialog(QDialog):
    """Small fuzzy-filtered command palette for keyboard-first navigation."""

    def __init__(self, parent: QWidget, actions: Iterable[CommandPaletteAction]):
        super().__init__(parent)
        self._all_actions = list(actions)
        self._visible_actions: list[CommandPaletteAction] = []
        self.setWindowTitle("Command Palette")
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Popup)
        self.setMinimumWidth(520)
        self.setStyleSheet(
            "QDialog { background-color: #111; border: 1px solid #6d5dfc; }"
            "QLabel { color: #d7d7ff; }"
            "QLineEdit { background: #050505; color: #f2f2ff; border: 1px solid #444;"
            " padding: 10px; font-size: 16px; selection-background-color: #6d5dfc; }"
            "QListWidget { background: #111; color: #eee; border: 0; font-size: 14px; }"
            "QListWidget::item { padding: 9px 10px; }"
            "QListWidget::item:selected { background: #332f73; color: #fff; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("⌘ Command Palette")
        hint = QLabel("Ctrl/Cmd+K • Enter to run • Esc to close")
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addWidget(hint, 1)
        layout.addLayout(header)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Type a command, panel, chart tool, or setting…")
        layout.addWidget(self.search_input)

        self.results_list = QListWidget(self)
        self.results_list.setUniformItemSizes(False)
        layout.addWidget(self.results_list)

        self.search_input.textChanged.connect(self._refresh_results)
        self.search_input.returnPressed.connect(self._run_selected)
        self.results_list.itemActivated.connect(lambda _item: self._run_selected())
        self._refresh_results("")

    def show_palette(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            parent_rect = parent.frameGeometry()
            self.adjustSize()
            width = max(self.minimumWidth(), min(720, parent_rect.width() - 80))
            self.resize(width, min(460, max(260, self.sizeHint().height())))
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.top() + max(48, parent_rect.height() // 7),
            )
        self.search_input.clear()
        self._refresh_results("")
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus(Qt.ShortcutFocusReason)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Escape,):
            self.close()
            return
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            self.results_list.setFocus(Qt.ShortcutFocusReason)
            self.results_list.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def _refresh_results(self, query: str) -> None:
        terms = [term for term in query.lower().split() if term]
        scored: list[tuple[int, CommandPaletteAction]] = []
        for action in self._all_actions:
            text = action.searchable_text()
            if not terms:
                score = 0
            elif all(term in text for term in terms):
                score = sum(text.find(term) for term in terms)
            else:
                continue
            scored.append((score, action))
        scored.sort(key=lambda item: (item[0], item[1].title.lower()))
        self._visible_actions = [action for _score, action in scored]

        self.results_list.clear()
        for action in self._visible_actions:
            label = action.title if not action.subtitle else f"{action.title}\n  {action.subtitle}"
            self.results_list.addItem(QListWidgetItem(label))
        if self.results_list.count():
            self.results_list.setCurrentRow(0)

    def _run_selected(self) -> None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self._visible_actions):
            return
        action = self._visible_actions[row]
        self.close()
        action.callback()


def install_command_palette(
    owner: QWidget,
    actions_factory: Callable[[], Iterable[CommandPaletteAction]],
) -> CommandPaletteDialog:
    """Install Ctrl+K and Cmd+K shortcuts on *owner* and return the palette."""

    palette = CommandPaletteDialog(owner, [])

    def open_palette() -> None:
        palette._all_actions = list(actions_factory())
        palette.show_palette()

    owner._command_palette_dialog = palette
    owner._shortcut_command_palette_ctrl = QShortcut(QKeySequence("Ctrl+K"), owner)
    owner._shortcut_command_palette_ctrl.activated.connect(open_palette)
    owner._shortcut_command_palette_cmd = QShortcut(QKeySequence("Meta+K"), owner)
    owner._shortcut_command_palette_cmd.activated.connect(open_palette)
    return palette
