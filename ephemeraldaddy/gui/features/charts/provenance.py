"""Chart provenance constants and UI option labels."""

from __future__ import annotations

from ephemeraldaddy.core.db import (
    SOURCE_EVENT,
    SOURCE_PARASOCIAL,
    SOURCE_PERSONAL,
    SOURCE_PERSONAL_TRANSIT,
    SOURCE_PUBLIC_DB,
    SOURCE_SYNASTRY,
    normalize_chart_type,
)
from PySide6.QtWidgets import QComboBox

SOURCE_OPTIONS: list[tuple[str, str]] = [
    ("Public DB", SOURCE_PUBLIC_DB),
    ("Personal", SOURCE_PERSONAL),
    ("Parasocial", SOURCE_PARASOCIAL),
    ("Event", SOURCE_EVENT),
    ("Synastry", SOURCE_SYNASTRY),
    ("Personal Transit", SOURCE_PERSONAL_TRANSIT),
]

# App GUI keeps the old local name `_normalize_gui_source`; point it at DB's canonical logic.
normalize_gui_source = normalize_chart_type


def populate_chart_source_combo(
    combo: QComboBox,
    *,
    any_label: str | None = None,
) -> None:
    """Populate a chart-type combo with the canonical source options."""
    combo.clear()
    if any_label is not None:
        combo.addItem(any_label, "")
    for source_label, source_value in SOURCE_OPTIONS:
        combo.addItem(source_label, source_value)
