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
        is_section_header = bool(line) and not str(line).lstrip().startswith("•") and str(line).rstrip().endswith(":")
        cursor.insertText(line, header_fmt if is_section_header else plain_fmt)
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
