"""Layout helpers for Database View Similarities Analysis widgets."""

from __future__ import annotations


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
    visible_row_heights = [max(0, int(height)) for height in row_heights if int(height) > 0]
    if not visible_row_heights:
        return 0
    content_height = sum(visible_row_heights) + max(0, int(frame_padding))
    return min(max_height, max(1, content_height))
