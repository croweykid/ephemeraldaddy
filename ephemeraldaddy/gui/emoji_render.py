"""Render mapped emojis as inline PNG icons in text-based Qt widgets."""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from ephemeraldaddy.graphics.emoji_map import EMOJI_ALIASES, EMOJI_TO_PNG, emoji_png_path

_ORIGINAL_TEXT_PROP = "_edd_original_emoji_text"


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


def apply_emoji_pngs_to_label(label: QLabel) -> None:
    original = label.property(_ORIGINAL_TEXT_PROP)
    if not isinstance(original, str):
        original = label.text()
        label.setProperty(_ORIGINAL_TEXT_PROP, original)
    if not original or "<" in original:
        return
    px = label.fontMetrics().height()
    rendered = render_text_with_emoji_pngs(original, px)
    if rendered == original:
        return
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(rendered)


class EmojiPngEventFilter(QObject):
    """Keep QLabel emoji/icon sizing aligned with live font size changes."""

    _events = {QEvent.Type.Show, QEvent.Type.FontChange, QEvent.Type.Polish, QEvent.Type.Resize}

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in self._events and isinstance(watched, QLabel):
            apply_emoji_pngs_to_label(watched)
        return super().eventFilter(watched, event)


def install_emoji_png_rendering(app: QApplication, root: QWidget) -> None:
    filt = getattr(app, "_edd_emoji_png_filter", None)
    if filt is None:
        filt = EmojiPngEventFilter(app)
        app._edd_emoji_png_filter = filt
        app.installEventFilter(filt)

    for label in root.findChildren(QLabel):
        apply_emoji_pngs_to_label(label)
        label.installEventFilter(filt)
