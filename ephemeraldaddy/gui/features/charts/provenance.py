"""Chart provenance constants and UI option labels."""

from __future__ import annotations

from ephemeraldaddy.core.db import (
    SOURCE_EVENT,
    SOURCE_NONHUMAN_ENTITY,
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
]

# App GUI keeps the old local name `_normalize_gui_source`; point it at DB's canonical logic.
normalize_gui_source = normalize_chart_type
