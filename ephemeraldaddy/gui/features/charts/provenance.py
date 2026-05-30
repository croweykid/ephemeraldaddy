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


def is_placeholder_chart_type(chart_type: str | None) -> bool:
    """Return True for legacy placeholder chart-type markers."""
    return str(chart_type or "").strip().lower() == "placeholder"


def chart_is_placeholder(chart: object | None) -> bool:
    """Return True for placeholder charts that cannot participate in chart math."""
    if chart is None:
        return False
    if bool(getattr(chart, "is_placeholder", False)):
        return True
    chart_type = getattr(chart, "chart_type", None) or getattr(chart, "source", None)
    return is_placeholder_chart_type(str(chart_type or ""))


def chart_is_hypothetical(chart: object | None) -> bool:
    """Return True for hypothetical charts that should not be aggregation candidates."""
    if chart is None:
        return False
    chart_type = getattr(chart, "chart_type", None) or getattr(chart, "source", None)
    return is_hypothetical_chart_type(str(chart_type or ""))


def chart_is_non_aggregable(chart: object | None) -> bool:
    """Return True for charts excluded from database-wide aggregation results."""
    return chart_is_placeholder(chart) or chart_is_hypothetical(chart)


def chart_is_similarity_participant(chart: object | None) -> bool:
    """Return True for charts that can be directly compared in Similarities Analysis."""
    return chart is not None and not chart_is_placeholder(chart)


def chart_row_is_placeholder(row: tuple[object, ...] | list[object] | None) -> bool:
    """Return True for list_charts() rows that represent placeholders."""
    if row is None:
        return False
    if len(row) > 15 and bool(row[15]):
        return True
    chart_type = row[14] if len(row) > 14 else None
    return is_placeholder_chart_type(str(chart_type or ""))


def chart_row_is_hypothetical(row: tuple[object, ...] | list[object] | None) -> bool:
    """Return True for list_charts() rows that represent hypothetical charts."""
    if row is None:
        return False
    chart_type = row[14] if len(row) > 14 else None
    return is_hypothetical_chart_type(str(chart_type or ""))


def chart_row_is_non_aggregable(row: tuple[object, ...] | list[object] | None) -> bool:
    """Return True for list_charts() rows excluded from database-wide math."""
    return chart_row_is_placeholder(row) or chart_row_is_hypothetical(row)


def chart_row_is_similarity_participant(row: tuple[object, ...] | list[object] | None) -> bool:
    """Return True for rows that can be directly compared in Similarities Analysis."""
    return row is not None and not chart_row_is_placeholder(row)
