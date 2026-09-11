"""Canonical chart provenance values and normalization without persistence imports."""

from __future__ import annotations

CHART_TYPE_PUBLIC_DB = "public_db"
CHART_TYPE_PERSONAL = "personal"
CHART_TYPE_PARASOCIAL = "parasocial"
CHART_TYPE_EVENT = "event"
CHART_TYPE_SYNASTRY = "synastry"
CHART_TYPE_PERSONAL_TRANSIT = "personal_transit"
CHART_TYPE_NONHUMAN_ENTITY = "nonhuman_entity"
CHART_TYPE_HYPOTHETICAL = "hypothetical"
SOURCE_USER_SUBMITTED = "user_submitted"

SOURCE_PUBLIC_DB = CHART_TYPE_PUBLIC_DB
SOURCE_PERSONAL = CHART_TYPE_PERSONAL
SOURCE_PARASOCIAL = CHART_TYPE_PARASOCIAL
SOURCE_EVENT = CHART_TYPE_EVENT
SOURCE_SYNASTRY = CHART_TYPE_SYNASTRY
SOURCE_PERSONAL_TRANSIT = CHART_TYPE_PERSONAL_TRANSIT
SOURCE_NONHUMAN_ENTITY = CHART_TYPE_NONHUMAN_ENTITY
SOURCE_HYPOTHETICAL = CHART_TYPE_HYPOTHETICAL

_KNOWN_CHART_TYPES = frozenset(
    {
        CHART_TYPE_PUBLIC_DB,
        CHART_TYPE_PERSONAL,
        CHART_TYPE_PARASOCIAL,
        CHART_TYPE_EVENT,
        CHART_TYPE_SYNASTRY,
        CHART_TYPE_PERSONAL_TRANSIT,
        CHART_TYPE_NONHUMAN_ENTITY,
        CHART_TYPE_HYPOTHETICAL,
    }
)


def normalize_chart_type(value: object) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    if normalized == SOURCE_USER_SUBMITTED:
        return CHART_TYPE_PERSONAL
    return normalized if normalized in _KNOWN_CHART_TYPES else CHART_TYPE_PERSONAL
