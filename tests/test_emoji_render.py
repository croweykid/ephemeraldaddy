import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from ephemeraldaddy.gui.emoji_render import (
    EmojiPngEventFilter,
    apply_emoji_png_to_button,
    apply_emoji_pngs_to_label,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class CountingLabel(QLabel):
    def __init__(self, text: str) -> None:
        self.text_updates = 0
        super().__init__(text)

    def setText(self, text: str) -> None:
        self.text_updates += 1
        super().setText(text)


def test_label_rendering_is_idempotent() -> None:
    _app()
    label = CountingLabel("🏠 Home")

    apply_emoji_pngs_to_label(label)
    first_render = label.text()
    apply_emoji_pngs_to_label(label)

    assert label.text_updates == 1
    assert label.text() == first_render
    assert "<img " in first_render


def test_event_filter_ignores_reentrant_render_event(monkeypatch) -> None:
    _app()
    label = QLabel("🏠 Home")
    event_filter = EmojiPngEventFilter()
    calls = 0

    def render_with_nested_event(watched: QLabel) -> None:
        nonlocal calls
        calls += 1
        event_filter.eventFilter(watched, QEvent(QEvent.Type.Resize))

    monkeypatch.setattr(
        "ephemeraldaddy.gui.emoji_render.apply_emoji_pngs_to_label",
        render_with_nested_event,
    )

    event_filter.eventFilter(label, QEvent(QEvent.Type.Resize))

    assert calls == 1
    assert label.property("_edd_rendering_emoji_png") is False


def test_button_rendering_is_idempotent() -> None:
    _app()
    button = QPushButton("🏠 Home")

    apply_emoji_png_to_button(button)
    first_icon_key = button.icon().cacheKey()
    apply_emoji_png_to_button(button)

    assert button.text() == "Home"
    assert button.icon().cacheKey() == first_icon_key
