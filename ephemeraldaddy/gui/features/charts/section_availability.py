"""Data-availability rules for Chart Analytics sections."""

from collections.abc import Callable


def is_chart_analysis_section_available(
    section_key: str,
    chart: object | None,
    *,
    uses_houses: Callable[[object], bool],
) -> bool:
    """Return whether the current chart supports a Chart Analytics section."""
    if section_key == "dominant_houses" and chart is not None:
        return bool(uses_houses(chart))
    return True
