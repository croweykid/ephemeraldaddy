"""Sun-Moon Hot Takes Chart Info supplement for EphemeralDaddy."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

PLUGIN_MANIFEST = {
    "api_version": 1,
    "name": "Sun-Moon Hot Takes",
    "hooks": ["chart_info"],
    "data_files": ["sun_moon_hot_takes.json"],
}

_DATA_FILENAME = "sun_moon_hot_takes.json"


def _sign_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _text_property(entry: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


@lru_cache(maxsize=1)
def _load_hot_takes() -> dict[str, Any]:
    data_path = Path(__file__).with_name(_DATA_FILENAME)
    try:
        with data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _lookup(sun_sign: str, moon_sign: str) -> Mapping[str, Any] | None:
    table = _load_hot_takes()
    sun_data = table.get(_sign_key(sun_sign))
    if not isinstance(sun_data, Mapping):
        return None
    combination = sun_data.get(_sign_key(moon_sign))
    return combination if isinstance(combination, Mapping) else None


def chart_info(context: Mapping[str, Any]) -> list[list[dict[str, Any]]]:
    """Return styled Chart Info paragraphs for clicked Sun/Moon position rows."""
    if str(context.get("target", "")).strip().lower() != "position":
        return []

    body = str(context.get("body", "")).strip().title()
    if body not in {"Sun", "Moon"}:
        return []

    chart_signs = context.get("chart_signs")
    if not isinstance(chart_signs, Mapping):
        return []
    sun_sign = str(chart_signs.get("Sun", "")).strip()
    moon_sign = str(chart_signs.get("Moon", "")).strip()
    if not sun_sign or not moon_sign:
        return []

    entry = _lookup(sun_sign, moon_sign)
    if entry is None:
        return []

    average = _text_property(entry, "average", "avg")
    best_case = _text_property(entry, "best_case", "best case")
    worst_case = _text_property(entry, "worst_case", "worst case")

    header_and_average: list[dict[str, Any]] = [
        {
            "text": "Sun-Moon Hot Takes:",
            "bold": True,
            "color_role": "highlight",
        }
    ]
    if average is not None:
        header_and_average.extend(
            [
                {"text": "\n"},
                {"text": average, "italic": True},
            ]
        )

    paragraphs: list[list[dict[str, Any]]] = [header_and_average]
    if best_case is not None:
        paragraphs.append(
            [
                {"text": "Best case: ", "bold": True},
                {"text": best_case},
            ]
        )
    if worst_case is not None:
        paragraphs.append(
            [
                {"text": "Worst case: ", "bold": True},
                {"text": worst_case},
            ]
        )
    return paragraphs
