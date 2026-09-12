"""Pure Theme View projection for Transit aspect windows."""

from __future__ import annotations

import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from ephemeraldaddy.core.theme_reference import THEMES


@dataclass(frozen=True, slots=True)
class TransitThemeEntry:
    theme_key: str
    theme_label: str
    aspect_label: str
    start: datetime.datetime
    end: datetime.datetime


def themes_for_aspect_bodies(transiting_body: str, natal_body: str) -> tuple[tuple[str, str], ...]:
    """Return themes evidenced by either endpoint of a transit aspect."""
    bodies = {str(transiting_body), str(natal_body)}
    matches = [
        (key, str(theme["label"]))
        for key, theme in THEMES.items()
        if bodies.intersection(str(body) for body in theme.get("bodies", ()))
    ]
    return tuple(sorted(matches, key=lambda item: item[1].casefold()))


def theme_entries_for_windows(windows: Iterable[Any]) -> tuple[TransitThemeEntry, ...]:
    entries: list[TransitThemeEntry] = []
    for window in windows:
        transit = window.transit
        for theme_key, theme_label in themes_for_aspect_bodies(
            transit.transiting_body, transit.natal_body
        ):
            entries.append(
                TransitThemeEntry(
                    theme_key=theme_key,
                    theme_label=theme_label,
                    aspect_label=transit.label,
                    start=window.start,
                    end=window.end,
                )
            )
    return tuple(sorted(entries, key=lambda entry: (entry.theme_label, entry.start, entry.aspect_label)))


def format_transit_theme_view(windows: Iterable[Any]) -> str:
    """Format aspect windows under Theme Reference headings with their dates."""
    grouped: dict[str, list[TransitThemeEntry]] = defaultdict(list)
    for entry in theme_entries_for_windows(windows):
        grouped[entry.theme_label].append(entry)
    if not grouped:
        return "No themed major transits occur in this ±30 day window."

    lines = ["TRANSIT THEMES · PREVIOUS 30 DAYS / NEXT 30 DAYS", ""]
    for theme_label in sorted(grouped, key=str.casefold):
        lines.append(theme_label.upper())
        for entry in grouped[theme_label]:
            lines.append(f"- {entry.start:%Y-%m-%d} – {entry.end:%Y-%m-%d}  {entry.aspect_label}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_transit_range_table(windows: Iterable[Any]) -> str:
    """Format recent and approaching major windows for the Table View."""
    ordered = sorted(windows, key=lambda window: (window.start, window.end, window.transit.label))
    if not ordered:
        return "SURROUNDING MAJOR TRANSITS (±30 DAYS)\n- None within configured major-transit orbs."
    lines = ["SURROUNDING MAJOR TRANSITS (±30 DAYS)"]
    lines.extend(
        f"- {window.start:%Y-%m-%d} – {window.end:%Y-%m-%d}  {window.transit.label}"
        for window in ordered
    )
    return "\n".join(lines)


def format_global_transit_theme_view(aspects: Iterable[Any], when: datetime.datetime | None) -> str:
    """Group a global chart's aspects by Theme Reference body memberships."""
    grouped: dict[str, list[str]] = defaultdict(list)
    date_label = f"{when:%Y-%m-%d}" if when is not None else "Unknown date"
    for aspect in aspects:
        if isinstance(aspect, dict):
            left = str(aspect.get("body1") or aspect.get("a") or "")
            right = str(aspect.get("body2") or aspect.get("b") or "")
            aspect_name = str(aspect.get("aspect") or "aspect")
        else:
            left_endpoint = getattr(aspect, "a", "")
            right_endpoint = getattr(aspect, "b", "")
            left = str(getattr(left_endpoint, "name", left_endpoint))
            right = str(getattr(right_endpoint, "name", right_endpoint))
            aspect_name = str(getattr(aspect, "aspect", "aspect"))
        label = f"{date_label}  {left} {aspect_name} {right}"
        for _theme_key, theme_label in themes_for_aspect_bodies(left, right):
            grouped[theme_label].append(label)
    if not grouped:
        return f"No themed global transit aspects occur on {date_label}."
    lines = ["GLOBAL TRANSIT THEMES", ""]
    for theme_label in sorted(grouped, key=str.casefold):
        lines.append(theme_label.upper())
        lines.extend(f"- {label}" for label in grouped[theme_label])
        lines.append("")
    return "\n".join(lines).rstrip()
