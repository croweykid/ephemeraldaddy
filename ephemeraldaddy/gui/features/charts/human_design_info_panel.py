from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from ephemeraldaddy.analysis.human_design_reference import HD_LINE_COLORS, LINE_ARCHETYPES
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR

_HD_COLOR_HEX_LOOKUP = {
    "red": "#ff4d4d",
    "orange": "#ff9f1c",
    "yellow": "#ffd60a",
    "green": "#5dc26a",
    "blue": "#4f8cff",
    "violet": "#b388ff",
}


def resolve_hd_color_hex(color_name: str) -> str:
    return _HD_COLOR_HEX_LOOKUP.get(str(color_name or "").strip().lower(), CHART_DATA_HIGHLIGHT_COLOR)


def insert_human_design_info_body_line(
    cursor: QTextCursor,
    line: str,
    *,
    header_fmt: QTextCharFormat,
    plain_fmt: QTextCharFormat,
) -> None:
    """Insert a Human Design info body line with colon labels accented."""
    line_text = str(line)
    stripped_line = line_text.strip()
    if not stripped_line:
        cursor.insertText(line_text, plain_fmt)
        return

    is_section_header = (
        not stripped_line.startswith("•")
        and stripped_line.rstrip().endswith(":")
    )
    if is_section_header:
        cursor.insertText(line_text, header_fmt)
        return

    colon_index = line_text.find(":")
    if colon_index <= 0:
        cursor.insertText(line_text, plain_fmt)
        return

    label_start = 0
    while label_start < len(line_text) and line_text[label_start].isspace():
        label_start += 1

    inserted_prefix = False
    if line_text.startswith("•", label_start):
        bullet_end = label_start + 1
        if bullet_end < len(line_text) and line_text[bullet_end] == " ":
            bullet_end += 1
        cursor.insertText(line_text[:bullet_end], plain_fmt)
        label_start = bullet_end
        inserted_prefix = True

    if label_start >= colon_index:
        cursor.insertText(line_text[label_start:] if inserted_prefix else line_text, plain_fmt)
        return

    if label_start > 0 and not inserted_prefix:
        cursor.insertText(line_text[:label_start], plain_fmt)

    cursor.insertText(line_text[label_start:colon_index + 1], header_fmt)
    cursor.insertText(line_text[colon_index + 1:], plain_fmt)


def render_human_design_info_text_with_accent(
    output: QPlainTextEdit,
    header: str,
    body_lines: list[str],
    *,
    accent_color: str,
) -> None:
    output.clear()
    cursor = output.textCursor()
    cursor.movePosition(QTextCursor.Start)

    header_fmt = QTextCharFormat()
    header_fmt.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
    header_fmt.setFontWeight(QFont.Bold)

    accent_fmt = QTextCharFormat()
    accent_fmt.setForeground(QColor(accent_color))
    accent_fmt.setFontWeight(QFont.Bold)

    plain_fmt = QTextCharFormat()
    plain_fmt.setFontWeight(QFont.Normal)
    plain_fmt.setFontItalic(False)

    cursor.insertText(f"{header}\n\n", accent_fmt)
    for idx, line in enumerate(body_lines):
        insert_human_design_info_body_line(
            cursor,
            line,
            header_fmt=header_fmt,
            plain_fmt=plain_fmt,
        )
        if idx < len(body_lines) - 1:
            cursor.insertText("\n", plain_fmt)
    output.setTextCursor(cursor)
    reset_cursor = output.textCursor()
    reset_cursor.movePosition(QTextCursor.Start)
    output.setTextCursor(reset_cursor)


def render_human_design_line_info(output: QPlainTextEdit, line_number: int) -> None:
    raw_line_color = str(HD_LINE_COLORS.get(int(line_number), CHART_DATA_HIGHLIGHT_COLOR))
    line_color = raw_line_color if raw_line_color.startswith("#") else f"#{raw_line_color}"
    line_text = LINE_ARCHETYPES.get(int(line_number), "No line archetype available.")
    render_human_design_info_text_with_accent(
        output,
        f"Line {int(line_number)} Archetype",
        [f"• {line_text}"],
        accent_color=line_color,
    )
