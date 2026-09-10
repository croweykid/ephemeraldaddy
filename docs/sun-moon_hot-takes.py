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
_ALTERNATE_DIVIDER = "────────────────────────────────"


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

    chart_sign_options = context.get("chart_sign_options")
    normalized_options: dict[str, list[str]] = {}
    if isinstance(chart_sign_options, Mapping):
        for luminary, raw_options in chart_sign_options.items():
            if isinstance(raw_options, (list, tuple)):
                options = [str(option).strip() for option in raw_options if str(option).strip()]
                normalized_options[_sign_key(luminary)] = list(dict.fromkeys(options))

    # Keep accepting the original singular context supplied by API v1 hosts.
    chart_signs = context.get("chart_signs")
    if isinstance(chart_signs, Mapping):
        for luminary, sign in chart_signs.items():
            sign_name = str(sign).strip()
            if sign_name:
                normalized_options.setdefault(_sign_key(luminary), [sign_name])

    sun_signs = normalized_options.get("sun", [])
    moon_signs = normalized_options.get("moon", [])
    if not sun_signs or not moon_signs:
        return []

    combinations = [
        (sun_sign, moon_sign, entry)
        for sun_sign in sun_signs
        for moon_sign in moon_signs
        if (entry := _lookup(sun_sign, moon_sign)) is not None
    ]
    if not combinations:
        return []

    paragraphs: list[list[dict[str, Any]]] = []
    for combination_index, (sun_sign, moon_sign, entry) in enumerate(combinations):
        if combination_index:
            paragraphs.append(
                [
                    {
                        "text": (
                            f"{_ALTERNATE_DIVIDER}\n"
                            "or! alternately! depending on exact birth time, "
                            "this might be the case...:\n"
                            f"{_ALTERNATE_DIVIDER}"
                        ),
                        "italic": True,
                    }
                ]
            )

        average = _text_property(entry, "average", "avg")
        best_case = _text_property(entry, "best_case", "best case")
        worst_case = _text_property(entry, "worst_case", "worst case")

        header_and_average: list[dict[str, Any]] = [
            {
                "text": f"Sun-Moon Hot Takes: {sun_sign} Sun / {moon_sign} Moon",
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

        paragraphs.append(header_and_average)
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
