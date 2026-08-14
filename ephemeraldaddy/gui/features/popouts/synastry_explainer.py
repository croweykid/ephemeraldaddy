"""Native, dark-themed reader for the bundled Twine synastry conversation."""

from __future__ import annotations

from urllib.parse import unquote

from PySide6.QtCore import QEvent, QObject, Qt, QUrl
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QToolButton, QVBoxLayout, QWidget

from ephemeraldaddy.gui.style import (
    COLOR_ACCENT_PRIMARY,
    COLOR_BG_APP,
    COLOR_BG_SURFACE,
    COLOR_BORDER_STRONG,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    apply_button_cursor,
)
from ephemeraldaddy.gui.features.popouts.synastry_conversation import (
    load_synastry_conversation,
    passage_html,
)


def show_synastry_explainer(owner: QWidget) -> QDialog:
    """Open the 600×600 nonlinear synastry conversation window."""
    start_name, passages = load_synastry_conversation()
    dialog = QDialog(owner)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setWindowTitle("What is synastry?")
    dialog.resize(600, 600)
    dialog.setMinimumSize(600, 600)
    dialog.setStyleSheet(f"QDialog {{ background: {COLOR_BG_APP}; }}")

    layout = QVBoxLayout(dialog)
    browser = QTextBrowser(dialog)
    browser.setOpenLinks(False)
    browser.setStyleSheet(
        f"QTextBrowser {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY}; "
        f"border: 1px solid {COLOR_BORDER_STRONG}; padding: 18px; }}"
    )
    browser.document().setDefaultStyleSheet(
        f"body {{ color: {COLOR_TEXT_PRIMARY}; font-size: 15px; line-height: 1.45; }} "
        f"h1 {{ color: {COLOR_ACCENT_PRIMARY}; }} p, li {{ color: {COLOR_TEXT_SECONDARY}; }} "
        f"a {{ color: {COLOR_ACCENT_PRIMARY}; font-weight: 600; text-decoration: none; }}"
    )
    layout.addWidget(browser, 1)
    close_button = QPushButton("Close", dialog)
    apply_button_cursor(close_button)
    close_button.clicked.connect(dialog.close)
    layout.addWidget(close_button, 0, Qt.AlignRight)

    def _show_passage(name: str) -> None:
        passage = passages.get(name)
        if passage is None:
            return
        browser.setHtml(passage_html(passage))
        browser.verticalScrollBar().setValue(0)

    def _follow(url: QUrl) -> None:
        if url.scheme() == "twine":
            _show_passage(unquote(url.path()))

    browser.anchorClicked.connect(_follow)
    _show_passage(start_name)
    dialog.show()
    return dialog


class _SynastryExplainerButtonPositioner(QObject):
    def __init__(self, button: QPushButton, share_button: QToolButton) -> None:
        super().__init__(button)
        self.button = button
        self.share_button = share_button

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Resize, QEvent.Show, QEvent.LayoutRequest):
            self.position()
        return super().eventFilter(watched, event)

    def position(self) -> None:
        margin = 6
        self.button.adjustSize()
        self.button.move(max(margin, self.share_button.x() - self.button.width() - margin), margin)
        self.button.raise_()
        self.button.show()


def attach_synastry_explainer_button(owner: QWidget, share_button: QToolButton) -> QPushButton:
    """Attach the explainer immediately left of a synastry popout's share button."""
    host = share_button.parentWidget() or owner
    button = QPushButton("What is synastry?", host)
    button.setToolTip("Open an interactive introduction to synastry")
    apply_button_cursor(button)
    button.clicked.connect(lambda _checked=False: show_synastry_explainer(owner))
    positioner = _SynastryExplainerButtonPositioner(button, share_button)
    button._synastry_explainer_positioner = positioner
    host.installEventFilter(positioner)
    positioner.position()
    return button
