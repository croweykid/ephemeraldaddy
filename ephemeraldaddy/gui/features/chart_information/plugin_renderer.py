"""Qt rendering boundary for declarative Chart Info plugin supplements."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR


def append_plugin_paragraphs(
    output: QPlainTextEdit,
    paragraphs: list[list[dict[str, Any]]],
) -> None:
    """Append normalized plugin paragraphs without interpreting text as HTML."""
    if not isinstance(paragraphs, (list, tuple)):
        return
    valid_paragraphs = [
        [segment for segment in paragraph if isinstance(segment, dict) and segment.get("text")]
        for paragraph in paragraphs
        if isinstance(paragraph, (list, tuple))
    ]
    valid_paragraphs = [paragraph for paragraph in valid_paragraphs if paragraph]
    if not valid_paragraphs:
        return

    cursor = output.textCursor()
    cursor.movePosition(QTextCursor.End)
    existing_text = output.toPlainText()
    if existing_text:
        trailing_newlines = len(existing_text) - len(existing_text.rstrip("\n"))
        cursor.insertText("\n" * max(0, 2 - trailing_newlines))

    for paragraph_index, paragraph in enumerate(valid_paragraphs):
        if paragraph_index:
            cursor.insertText("\n\n")
        for segment in paragraph:
            text = str(segment.get("text", ""))
            if not text:
                continue
            char_format = QTextCharFormat()
            color = (
                CHART_DATA_HIGHLIGHT_COLOR
                if segment.get("color_role") == "highlight"
                else "#ffffff"
            )
            char_format.setForeground(QColor(color))
            char_format.setFontWeight(QFont.Bold if segment.get("bold") else QFont.Normal)
            char_format.setFontItalic(bool(segment.get("italic")))
            cursor.insertText(text, char_format)

    output.setTextCursor(cursor)
    reset_cursor = output.textCursor()
    reset_cursor.movePosition(QTextCursor.Start)
    output.setTextCursor(reset_cursor)
