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
    start_truncated: bool = False
    end_truncated: bool = False


def _format_window_dates(
    start: datetime.datetime,
    end: datetime.datetime,
    *,
    start_truncated: bool,
    end_truncated: bool,
) -> str:
    """Make clipped scan boundaries visibly different from resolved dates."""
    start_text = f"before {start:%Y-%m-%d}" if start_truncated else f"{start:%Y-%m-%d}"
    end_text = f"after {end:%Y-%m-%d}" if end_truncated else f"{end:%Y-%m-%d}"
    return f"{start_text} – {end_text}"


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
                    start_truncated=bool(window.start_truncated),
                    end_truncated=bool(window.end_truncated),
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
            dates = _format_window_dates(
                entry.start,
                entry.end,
                start_truncated=entry.start_truncated,
                end_truncated=entry.end_truncated,
            )
            lines.append(f"- {dates}  {entry.aspect_label}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_transit_range_table(windows: Iterable[Any]) -> str:
    """Format recent and approaching major windows for the Table View."""
    ordered = sorted(windows, key=lambda window: (window.start, window.end, window.transit.label))
    if not ordered:
        return "SURROUNDING MAJOR TRANSITS (±30 DAYS)\n- None within configured major-transit orbs."
    lines = ["SURROUNDING MAJOR TRANSITS (±30 DAYS)"]
    lines.extend(
        f"- {_format_window_dates(window.start, window.end, start_truncated=window.start_truncated, end_truncated=window.end_truncated)}  {window.transit.label}"
        for window in ordered
    )
    return "\n".join(lines)


def format_global_transit_theme_view(aspects: Iterable[Any], when: datetime.datetime | None) -> str:
    """Group a global chart's aspects by Theme Reference body memberships."""
    grouped: dict[str, list[str]] = defaultdict(list)
    date_label = f"{when:%Y-%m-%d}" if when is not None else "Unknown date"
    for aspect in aspects:
        if isinstance(aspect, dict):
            # Global Chart aspects use the canonical p1/p2/type mapping schema.
            # Retain the older aliases only for callers that supply an adapted
            # aspect mapping rather than a Chart.aspects row.
            left = str(aspect.get("p1") or aspect.get("body1") or aspect.get("a") or "")
            right = str(aspect.get("p2") or aspect.get("body2") or aspect.get("b") or "")
            aspect_name = str(aspect.get("type") or aspect.get("aspect") or "aspect")
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
