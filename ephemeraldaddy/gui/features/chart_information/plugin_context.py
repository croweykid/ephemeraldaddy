"""Window-independent context construction and dispatch for Chart Info plugins."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ephemeraldaddy.analysis.plugins import chart_info_plugin_paragraphs


def position_plugin_paragraphs(
    *,
    body: str,
    sign: str,
    house_num: int | None,
    chart_positions: Mapping[str, Any],
    sign_for_longitude: Callable[[float], str],
) -> list[list[dict[str, Any]]]:
    """Dispatch the generic hook with primitive data for one chart position."""
    chart_signs: dict[str, str] = {}
    for luminary in ("Sun", "Moon"):
        longitude = chart_positions.get(luminary)
        if longitude is None:
            continue
        try:
            chart_signs[luminary] = sign_for_longitude(float(longitude))
        except (TypeError, ValueError):
            continue

    return chart_info_plugin_paragraphs(
        {
            "target": "position",
            "body": body,
            "sign": sign,
            "house_num": house_num,
            "chart_uses_houses": house_num is not None,
            "chart_signs": chart_signs,
        }
    )
