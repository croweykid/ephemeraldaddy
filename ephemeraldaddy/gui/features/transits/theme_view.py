"""Theme-oriented presentation helpers for Transit popouts.

``core.theme_reference`` intentionally does not assign aspect geometries to
Themes.  An aspect is a relationship/modifier, not a subject by itself.  Transit
Theme View therefore derives thematic membership from the aspect endpoints and
available natal placement context, while continuing to display the aspect type
as the relationship between those factors.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable

from ephemeraldaddy.core.aspect_display import aspect_axis_display_label
from ephemeraldaddy.core.theme_reference import THEMES, theme_item_weight
from ephemeraldaddy.gui.features.transits.context_windows import (
    STATUS_ACTIVE,
    STATUS_ORDER,
    STATUS_RECENT,
    STATUS_UPCOMING,
    TransitContextWindow,
)


@dataclass(frozen=True, slots=True)
class TransitThemeGroup:
    theme_key: str
    label: str
    score: float
    windows: tuple[TransitContextWindow, ...]



def _window_factors(window: TransitContextWindow) -> tuple[tuple[str, object], ...]:
    hit = window.representative_hit
    factors: list[tuple[str, object]] = [
        ("bodies", hit.a.name),
        ("bodies", hit.b.name),
    ]
    if hit.b.sign:
        factors.append(("signs", hit.b.sign))
    if hit.b.house is not None:
        factors.append(("houses", int(hit.b.house)))
    # The context scanner's transit endpoint may not carry a sign/house because
    # those values can change during a long window.  If a caller supplied a
    # point-in-time hit that does carry them, use that evidence too.
    if hit.a.sign:
        factors.append(("signs", hit.a.sign))
    if hit.a.house is not None:
        factors.append(("houses", int(hit.a.house)))
    return tuple(factors)



def theme_scores_for_window(window: TransitContextWindow) -> dict[str, float]:
    """Return non-zero Theme membership scores for one transit event."""
    factors = _window_factors(window)
    scores: dict[str, float] = {}
    for theme_key in THEMES:
        score = sum(
            float(theme_item_weight(theme_key, property_name, item))
            for property_name, item in factors
        )
        if score > 0.0:
            scores[theme_key] = score
    return scores



def group_context_windows_by_theme(
    windows: Iterable[TransitContextWindow],
) -> tuple[TransitThemeGroup, ...]:
    """Group transit events by Theme; membership is intentionally non-exclusive."""
    score_totals: dict[str, float] = {}
    grouped: dict[str, list[TransitContextWindow]] = {}
    unclassified: list[TransitContextWindow] = []

    for window in windows:
        scores = theme_scores_for_window(window)
        if not scores:
            unclassified.append(window)
            continue
        for theme_key, score in scores.items():
            score_totals[theme_key] = score_totals.get(theme_key, 0.0) + score
            grouped.setdefault(theme_key, []).append(window)

    definition_order = {key: index for index, key in enumerate(THEMES)}
    theme_keys = sorted(
        grouped,
        key=lambda key: (
            -score_totals.get(key, 0.0),
            definition_order.get(key, len(definition_order)),
        ),
    )
    groups = [
        TransitThemeGroup(
            theme_key=theme_key,
            label=str(THEMES[theme_key].get("label", theme_key)),
            score=score_totals[theme_key],
            windows=tuple(grouped[theme_key]),
        )
        for theme_key in theme_keys
    ]
    if unclassified:
        groups.append(
            TransitThemeGroup(
                theme_key="__unclassified__",
                label="Other / Unclassified",
                score=0.0,
                windows=tuple(unclassified),
            )
        )
    return tuple(groups)



def _endpoint_label(name: str) -> str:
    return aspect_axis_display_label(name) or name



def _default_range_formatter(
    start: datetime | None,
    end: datetime | None,
) -> str:
    start_text = start.strftime("%m-%d-%Y") if start is not None else "…"
    end_text = end.strftime("%m-%d-%Y") if end is not None else "…"
    return f"{start_text} -> {end_text}"



def format_theme_view_text(
    windows: Iterable[TransitContextWindow],
    *,
    range_formatter: Callable[[datetime | None, datetime | None], str] | None = None,
) -> str:
    """Build the initial plain-text Theme View used by the shared popout shell."""
    formatter = range_formatter or _default_range_formatter
    groups = group_context_windows_by_theme(windows)
    if not groups:
        return "No recent, active, or approaching Life Forecast transits in this window."

    status_labels = {
        STATUS_RECENT: "Recently Ended",
        STATUS_ACTIVE: "Active",
        STATUS_UPCOMING: "Approaching",
    }
    parts: list[str] = []
    for group in groups:
        parts.append(group.label)
        by_status = {status: [] for status in STATUS_ORDER}
        for window in group.windows:
            by_status.setdefault(window.status, []).append(window)
        for status in STATUS_ORDER:
            rows = by_status.get(status, [])
            if not rows:
                continue
            parts.append(f"  {status_labels.get(status, status.title())}")
            for window in rows:
                transit_label = _endpoint_label(window.transiting_body)
                natal_label = _endpoint_label(window.natal_body)
                aspect_label = window.aspect_name.replace("_", " ")
                dates = formatter(window.start, window.end)
                parts.append(
                    f"    - {transit_label} {aspect_label} {natal_label}    {dates}"
                )
        parts.append("")
    return "\n".join(parts).rstrip()
