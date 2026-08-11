"""Render mapped emojis as inline PNG icons in text-based Qt widgets."""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QWidget

from ephemeraldaddy.graphics.emoji_map import (
    EMOJI_ALIASES,
    EMOJI_TO_PNG,
    VARIATION_SELECTOR_15,
    VARIATION_SELECTOR_16,
    emoji_png_path,
)

_ORIGINAL_TEXT_PROP = "_edd_original_emoji_text"
_RENDERING_PROP = "_edd_rendering_emoji_png"
_ICON_SOURCE_PROP = "_edd_emoji_icon_source"


def _emoji_img_tag(emoji: str, px: int) -> str | None:
    path = emoji_png_path(emoji)
    if path is None:
        return None
    src = Path(path).as_posix()
    size = max(10, int(px))
    return (
        f'<img src="{html.escape(src, quote=True)}" '
        f'width="{size}" height="{size}" '
        'style="vertical-align:middle;"/>'
    )


def render_text_with_emoji_pngs(text: str, px: int) -> str:
    if not text:
        return text
    out: list[str] = []
    replaced = False
    for ch in text:
        tag = _emoji_img_tag(ch, px)
        if tag is None:
            out.append(html.escape(ch))
            continue
        replaced = True
        out.append(tag)
    if not replaced:
        return text
    return "".join(out)


def _leading_emoji_icon_payload(text: str) -> tuple[str, str] | None:
    """Return ``(emoji, remaining_label)`` for a leading mapped emoji."""
    if not text:
        return None
    emoji = text[0]
    path = emoji_png_path(emoji)
    if path is None:
        return None
    label_start = 1
    while label_start < len(text) and text[label_start] in {
        VARIATION_SELECTOR_15,
        VARIATION_SELECTOR_16,
    }:
        label_start += 1
    return emoji, text[label_start:].lstrip()


def apply_emoji_png_to_button(button: QAbstractButton, *, icon_px: int | None = None) -> None:
    """Replace a leading mapped emoji in a button with the bundled PNG icon."""
    current = button.text() or ""
    original = button.property(_ORIGINAL_TEXT_PROP)
    if _leading_emoji_icon_payload(current) is not None:
        original = current
        button.setProperty(_ORIGINAL_TEXT_PROP, original)
    elif not isinstance(original, str):
        original = current
        button.setProperty(_ORIGINAL_TEXT_PROP, original)
    payload = _leading_emoji_icon_payload(original)
    if payload is None:
        return
    emoji, label = payload
    path = emoji_png_path(emoji)
    if path is None:
        return
    px = icon_px or max(12, button.fontMetrics().height())
    size = QSize(px, px)
    if button.text() != label:
        button.setText(label)
    icon_source = str(path)
    if button.property(_ICON_SOURCE_PROP) != icon_source:
        button.setIcon(QIcon(str(path)))
        button.setProperty(_ICON_SOURCE_PROP, icon_source)
    if button.iconSize() != size:
        button.setIconSize(size)


def apply_emoji_pngs_to_label(label: QLabel) -> None:
    original = label.property(_ORIGINAL_TEXT_PROP)
    if not isinstance(original, str):
        original = label.text()
        label.setProperty(_ORIGINAL_TEXT_PROP, original)
    if not original or "<" in original:
        return
    px = label.fontMetrics().height()
    rendered = render_text_with_emoji_pngs(original, px)
    if rendered == original or (
        label.textFormat() == Qt.TextFormat.RichText and label.text() == rendered
    ):
        return
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(rendered)


class EmojiPngEventFilter(QObject):
    """Keep QLabel emoji/icon sizing aligned with live font size changes."""

    _events = {QEvent.Type.Show, QEvent.Type.FontChange, QEvent.Type.Polish, QEvent.Type.Resize}

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in self._events and not watched.property(_RENDERING_PROP):
            watched.setProperty(_RENDERING_PROP, True)
            try:
                if isinstance(watched, QLabel):
                    apply_emoji_pngs_to_label(watched)
                elif isinstance(watched, QAbstractButton):
                    apply_emoji_png_to_button(watched)
            finally:
                watched.setProperty(_RENDERING_PROP, False)
        return super().eventFilter(watched, event)


def install_emoji_png_rendering(app: QApplication, root: QWidget) -> None:
    filt = getattr(app, "_edd_emoji_png_filter", None)
    if filt is None:
        filt = EmojiPngEventFilter(app)
        app._edd_emoji_png_filter = filt
        app.installEventFilter(filt)

    for label in root.findChildren(QLabel):
        apply_emoji_pngs_to_label(label)

    for button in root.findChildren(QAbstractButton):
        apply_emoji_png_to_button(button)
