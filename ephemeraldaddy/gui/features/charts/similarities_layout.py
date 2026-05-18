"""Layout helpers for Database View Similarities Analysis widgets."""

from __future__ import annotations

from typing import Any


SIMILARITIES_EXPANDED_MAX_HEIGHT_PROPERTY = "similarities_expanded_max_height"
SIMILARITIES_DEFAULT_ROW_HEIGHT = 32


def bounded_similarity_section_height(
    row_heights: list[int],
    maximum_height: int,
    *,
    frame_padding: int = 4,
) -> int:
    """Return a compact expanded height for a Similarities Analysis section.

    The configured section height is treated as a cap. Sections with only a few
    rendered factor rows can shrink to fit those rows instead of occupying the
    full cap.
    """
    max_height = max(0, int(maximum_height))
    if max_height <= 0:
        return 0
    visible_row_heights = [
        max(0, int(height)) for height in row_heights if int(height) > 0
    ]
    if not visible_row_heights:
        return 0
    content_height = sum(visible_row_heights) + max(0, int(frame_padding))
    return min(max_height, max(1, content_height))


def configure_similarity_section_list_height(section_list: Any, maximum_height: int) -> None:
    """Store and apply the expanded-height cap for a similarities section list."""
    max_height = max(0, int(maximum_height))
    section_list.setProperty(SIMILARITIES_EXPANDED_MAX_HEIGHT_PROPERTY, max_height)
    section_list.setFixedHeight(max_height)


def _similarity_section_row_heights(section_list: Any) -> list[int]:
    row_heights: list[int] = []
    for index in range(section_list.count()):
        item_height = section_list.item(index).sizeHint().height()
        if item_height <= 0:
            item_height = section_list.sizeHintForRow(index)
        if item_height <= 0:
            item_height = SIMILARITIES_DEFAULT_ROW_HEIGHT
        row_heights.append(item_height)
    return row_heights


def resize_similarity_section_to_contents(section_list: Any) -> int:
    """Resize a similarities section list to its row contents, capped at max height."""
    max_height = int(section_list.property(SIMILARITIES_EXPANDED_MAX_HEIGHT_PROPERTY) or 0)
    frame_padding = (section_list.frameWidth() * 2) + 2
    target_height = bounded_similarity_section_height(
        _similarity_section_row_heights(section_list),
        max_height,
        frame_padding=frame_padding,
    )
    section_list.setFixedHeight(target_height)
    return target_height
