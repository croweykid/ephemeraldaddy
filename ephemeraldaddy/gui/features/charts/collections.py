"""Database View collection definitions and membership helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.gui.features.charts.provenance import (
    SOURCE_PARASOCIAL,
    SOURCE_PERSONAL,
    SOURCE_PUBLIC_DB,
    normalize_gui_source,
)

DEFAULT_COLLECTION_ALL = "all"
DEFAULT_COLLECTION_PERSONAL = "personal"
DEFAULT_COLLECTION_PARASOCIAL = "parasocial"
DEFAULT_COLLECTION_PUBLIC = "public"

DEFAULT_COLLECTION_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Personal", DEFAULT_COLLECTION_PERSONAL),
    ("Parasocial", DEFAULT_COLLECTION_PARASOCIAL),
    ("Public", DEFAULT_COLLECTION_PUBLIC),
    ("All", DEFAULT_COLLECTION_ALL),
)
DEFAULT_COLLECTION_IDS = {value for _label, value in DEFAULT_COLLECTION_OPTIONS}


@dataclass(slots=True, frozen=True)
class CustomCollection:
    collection_id: str
    name: str
    chart_ids: frozenset[int]


def sanitize_collection_name(name: object, *, fallback: str = "Untitled Collection") -> str:
    text = str(name or "").strip()
    return text or fallback


def normalize_collection_id(value: object, *, fallback: str = DEFAULT_COLLECTION_ALL) -> str:
    text = str(value or "").strip().lower()
    return text or fallback


def chart_belongs_to_collection(
    collection_id: str,
    *,
    chart: Chart | None,
    source: str | None = None,
    custom_collections: dict[str, CustomCollection] | None = None,
    chart_id: int | None = None,
) -> bool:
    normalized_collection_id = normalize_collection_id(collection_id)
    if normalized_collection_id == DEFAULT_COLLECTION_ALL:
        return True

    normalized_source = normalize_gui_source(source or getattr(chart, "source", SOURCE_PERSONAL))
    relationship_types = _normalized_relationship_types(chart)
    is_parasocial = (
        (normalized_source == SOURCE_PARASOCIAL)
        or ("parasocial" in relationship_types)
        or ("public figure" in relationship_types)
    )
    is_public = normalized_source == SOURCE_PUBLIC_DB

    if normalized_collection_id == DEFAULT_COLLECTION_PERSONAL:
        return (not is_parasocial) and (not is_public)
    if normalized_collection_id == DEFAULT_COLLECTION_PARASOCIAL:
        return is_parasocial
    if normalized_collection_id == DEFAULT_COLLECTION_PUBLIC:
        return is_public

    if custom_collections is None or chart_id is None:
        return False
    custom_collection = custom_collections.get(normalized_collection_id)
    if custom_collection is None:
        return False
    return chart_id in custom_collection.chart_ids


def _normalized_relationship_types(chart: Chart | None) -> set[str]:
    if chart is None:
        return set()
    raw_relationships = getattr(chart, "relationship_types", None) or []
    if isinstance(raw_relationships, str):
        raw_relationships = [part.strip() for part in raw_relationships.split(",")]
    normalized: set[str] = set()
    for value in raw_relationships:
        if isinstance(value, str):
            text = value.strip().casefold()
            if text:
                normalized.add(text)
    return normalized
