"""Chart Information click-target interaction without application-window coupling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QPlainTextEdit, QStackedWidget, QWidget

from ephemeraldaddy.gui.style import apply_chart_info_link_cursor
from .perceived_accuracy import (
    PerceivedAccuracyThumbs,
    set_chart_information_control_mode,
)


CHART_INFORMATION_PANEL_MODES = (
    "chart_info", "comments", "quotes", "tags", "rectification", "biography", "source"
)


def set_chart_information_panel_mode(
    *,
    stack: QStackedWidget | None,
    control: PerceivedAccuracyThumbs | None,
    mode: str,
    preference_visible: bool,
    refresh_toggle_buttons: Callable[[], None],
    update_bio_button_visibility: Callable[[], None],
) -> bool:
    """Switch the Chart Editor info tab and synchronize property feedback."""
    if mode not in CHART_INFORMATION_PANEL_MODES:
        return False
    set_chart_information_control_mode(
        control, mode=mode, preference_visible=preference_visible
    )
    if stack is not None:
        stack.setCurrentIndex(CHART_INFORMATION_PANEL_MODES.index(mode))
    refresh_toggle_buttons()
    update_bio_button_visibility()
    return True


def summary_info_cursor_is_on_link(
    cursor: Any,
    position_info_map: dict[int, list[dict[str, object]]],
    aspect_info_map: dict[int, dict[str, object]],
    species_info_map: dict[int, list[dict[str, object]]],
    block_offset: int = 0,
) -> bool:
    """Return whether ``cursor`` points at a semantic Chart Information target."""
    block = cursor.block()
    block_number = block.blockNumber() + block_offset
    block_text = block.text()
    cursor_pos = cursor.positionInBlock()

    for entries in (
        species_info_map.get(block_number, []),
        position_info_map.get(block_number, []),
    ):
        for entry in entries:
            span_start = entry.get("span_start")
            span_end = entry.get("span_end")
            if (
                isinstance(span_start, int)
                and isinstance(span_end, int)
                and span_start <= cursor_pos < span_end
            ):
                return True
        icon_indices = [
            int(entry["icon_index"])
            for entry in entries
            if isinstance(entry.get("icon_index"), int)
            and int(entry.get("icon_index", -1)) >= 0
        ]
        if any(cursor_pos >= icon_index for icon_index in icon_indices):
            return True

    aspect_info = aspect_info_map.get(block_number)
    if not aspect_info:
        return False
    info_index = block_text.rfind("ⓘ")
    if info_index != -1 and cursor_pos >= info_index:
        return True
    span_start = aspect_info.get("span_start")
    span_end = aspect_info.get("span_end")
    return (
        isinstance(span_start, int)
        and isinstance(span_end, int)
        and span_start <= cursor_pos < span_end
    )


def update_summary_info_hover_cursor(
    output_widget: QPlainTextEdit,
    viewport: QWidget,
    position: Any,
    position_info_map: dict[int, list[dict[str, object]]],
    aspect_info_map: dict[int, dict[str, object]],
    species_info_map: dict[int, list[dict[str, object]]],
    block_offset: int = 0,
) -> None:
    """Apply the shared Chart Information cursor for a hovered target."""
    cursor = output_widget.cursorForPosition(position.toPoint())
    if summary_info_cursor_is_on_link(
        cursor,
        position_info_map,
        aspect_info_map,
        species_info_map,
        block_offset,
    ):
        apply_chart_info_link_cursor(viewport)
    else:
        viewport.unsetCursor()
