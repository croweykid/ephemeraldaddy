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
    position_info_map: Mapping[int, list[dict[str, object]]] | None = None,
) -> list[list[dict[str, Any]]]:
    """Dispatch the generic hook with primitive data for one chart position."""
    chart_sign_options: dict[str, list[str]] = {"Sun": [], "Moon": []}
    for entries in (position_info_map or {}).values():
        for entry in entries:
            luminary = str(entry.get("body", "")).strip().title()
            sign_name = str(entry.get("sign", "")).strip()
            if (
                luminary in chart_sign_options
                and sign_name
                and sign_name not in chart_sign_options[luminary]
            ):
                chart_sign_options[luminary].append(sign_name)

    for luminary in ("Sun", "Moon"):
        if chart_sign_options[luminary]:
            continue
        longitude = chart_positions.get(luminary)
        if longitude is None:
            continue
        try:
            chart_sign_options[luminary].append(sign_for_longitude(float(longitude)))
        except (TypeError, ValueError):
            continue

    selected_luminary = body.strip().title()
    if selected_luminary in chart_sign_options and sign in chart_sign_options[selected_luminary]:
        selected_options = chart_sign_options[selected_luminary]
        selected_options.insert(0, selected_options.pop(selected_options.index(sign)))

    chart_signs = {
        luminary: options[0]
        for luminary, options in chart_sign_options.items()
        if options
    }

    return chart_info_plugin_paragraphs(
        {
            "target": "position",
            "body": body,
            "sign": sign,
            "house_num": house_num,
            "chart_uses_houses": house_num is not None,
            "chart_signs": chart_signs,
            "chart_sign_options": {
                luminary: tuple(options)
                for luminary, options in chart_sign_options.items()
                if options
            },
        }
    )
