"""Detect Rankings label/membership changes from hydrated database rows."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def ranking_presentation_changes(
    previous_rows: Iterable[Sequence[Any]], current_rows: Iterable[Sequence[Any]],
) -> frozenset[str]:
    """Return UIDs whose labels or eligibility need refreshing, never scoring.

    These are the existing list_charts row slots: permanent UID (30), name (1),
    chart type (14), and placeholder status (15). Row order and tags/notes do
    not change this view. Numerical freshness belongs to the astro journal.
    """
    def presentation(rows: Iterable[Sequence[Any]]) -> dict[str, tuple[Any, ...]]:
        return {
            uid: (str(row[1] or ""), str(row[14] or ""), bool(row[15]))
            for row in rows
            if len(row) > 30 and (uid := str(row[30] or "").strip().upper())
        }

    previous = presentation(previous_rows)
    current = presentation(current_rows)
    return frozenset(
        uid for uid in previous.keys() | current.keys()
        if previous.get(uid) != current.get(uid)
    )
