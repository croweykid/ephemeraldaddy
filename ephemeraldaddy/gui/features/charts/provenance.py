"""Chart provenance constants and UI option labels."""

from __future__ import annotations

from ephemeraldaddy.core.db import (
    SOURCE_EVENT,
    SOURCE_NONHUMAN_ENTITY,
    SOURCE_HYPOTHETICAL,
    SOURCE_PARASOCIAL,
    SOURCE_PERSONAL,
    SOURCE_PERSONAL_TRANSIT,
    SOURCE_PUBLIC_DB,
    SOURCE_SYNASTRY,
    normalize_chart_type,
)

SOURCE_OPTIONS: list[tuple[str, str]] = [
    ("Public DB", SOURCE_PUBLIC_DB),
    ("Personal", SOURCE_PERSONAL),
    ("Parasocial", SOURCE_PARASOCIAL),
    ("Event", SOURCE_EVENT),
    ("Nonhuman Entity", SOURCE_NONHUMAN_ENTITY),
    ("Synastry", SOURCE_SYNASTRY),
    ("Personal Transit", SOURCE_PERSONAL_TRANSIT),
    ("Hypothetical", SOURCE_HYPOTHETICAL),
]

# App GUI keeps the old local name `_normalize_gui_source`; point it at DB's canonical logic.
normalize_gui_source = normalize_chart_type


def is_hypothetical_chart_type(chart_type: str | None) -> bool:
    """Return True for the non-canonical Hypothetical chart type."""
    return normalize_chart_type(chart_type) == SOURCE_HYPOTHETICAL


def chart_is_non_aggregable(chart: object | None) -> bool:
    """Return True for charts excluded from analytics/similarity aggregation."""
    if chart is None:
        return False
    if bool(getattr(chart, "is_placeholder", False)):
        return True
    chart_type = getattr(chart, "chart_type", None) or getattr(chart, "source", None)
    normalized_type = normalize_chart_type(chart_type)
    return (
        normalized_type == SOURCE_HYPOTHETICAL
        or str(chart_type or "").strip().lower() == "placeholder"
    )


def chart_row_is_non_aggregable(row: tuple[object, ...] | list[object] | None) -> bool:
    """Return True for list_charts() rows excluded from database-wide math."""
    if row is None:
        return False
    if len(row) > 15 and bool(row[15]):
        return True
    chart_type = row[14] if len(row) > 14 else None
    return is_hypothetical_chart_type(str(chart_type or ""))
