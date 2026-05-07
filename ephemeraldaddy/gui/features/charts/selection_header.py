"""Database View selection-summary label helpers.

This module keeps the Database View label formatting isolated from the main
window implementation.  The helpers are intentionally pure so they can be
unit-tested without Qt and safely called from existing UI refresh paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_OPTIONS,
    DEFAULT_COLLECTION_POSSIBLE_DUPLICATES,
    CustomCollection,
    normalize_collection_id,
)

_DEFAULT_COLLECTION_LABELS = {
    collection_id: label for label, collection_id in DEFAULT_COLLECTION_OPTIONS
}
_DEFAULT_COLLECTION_LABELS[DEFAULT_COLLECTION_POSSIBLE_DUPLICATES] = "possible duplicates"


@dataclass(frozen=True, slots=True)
class SelectionSummaryCounts:
    """Counts needed to render the Database View selection summary."""

    selected: int
    search_results: int
    current_collection: int
    database: int

    @classmethod
    def from_values(
        cls,
        *,
        selected: object,
        search_results: object,
        current_collection: object,
        database: object,
    ) -> "SelectionSummaryCounts":
        """Build clamped integer counts from UI-provided values."""

        return cls(
            selected=_coerce_non_negative_int(selected),
            search_results=_coerce_non_negative_int(search_results),
            current_collection=_coerce_non_negative_int(current_collection),
            database=_coerce_non_negative_int(database),
        )


def format_selection_summary(
    *,
    counts: SelectionSummaryCounts,
    active_collection_id: object,
    active_filters: bool,
    custom_collections: Mapping[str, CustomCollection] | None = None,
) -> str:
    """Return the Database View middle-panel selection-summary text."""

    collection_id = normalize_collection_id(active_collection_id)
    has_filtered_results = bool(active_filters)

    if collection_id == DEFAULT_COLLECTION_ALL:
        if has_filtered_results:
            return (
                f"Charts Selected: {counts.selected} of {counts.search_results} results. "
                f"{counts.database} in database"
            )
        return f"Charts Selected: {counts.selected} of {counts.database}"

    collection_name = collection_display_name(
        collection_id,
        custom_collections=custom_collections,
    )
    if has_filtered_results:
        return (
            f"Charts Selected: {counts.selected} of {counts.search_results} results. "
            f"{counts.current_collection} in {collection_name} collection. "
            f"({counts.database} in database)"
        )
    return (
        f"Charts Selected: {counts.selected} of {counts.current_collection} "
        f"in {collection_name} collection. ({counts.database} in database)"
    )


def collection_display_name(
    collection_id: object,
    *,
    custom_collections: Mapping[str, CustomCollection] | None = None,
) -> str:
    """Return a stable user-facing collection name for summary labels."""

    normalized_id = normalize_collection_id(collection_id)
    if custom_collections:
        custom_collection = custom_collections.get(normalized_id)
        if custom_collection is not None:
            return (
                str(custom_collection.name or "Untitled Collection").strip()
                or "Untitled Collection"
            )
    return _DEFAULT_COLLECTION_LABELS.get(normalized_id, "All")


def _coerce_non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
