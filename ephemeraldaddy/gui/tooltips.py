"""Tooltip helpers for GUI widgets."""

from __future__ import annotations

from typing import Mapping

from PySide6.QtWidgets import QAbstractButton, QLabel, QWidget

DEFAULT_TOOLTIP_OVERRIDES: dict[str, str] = {
    # Database View controls
    "manage_new_chart_button": "Create New Chart",
    "manage_delete_chart_button": "Delete Chart(s)",
    "manage_import_csv_button": "Import Charts to Database from CSV",
    "manage_export_selected_csv_button": "Export Selected Charts to CSV",
    "manage_backup_database_button": "Backup Database to File",
    "manage_restore_database_button": "Restore Database from File",
    "manage_retcon_engine_button": "Reverse Engineer a Chart",
    "manage_composite_chart_button": "Create Synastry Chart",
    "manage_force_refresh_button": "Refresh Database Analysis",
    "manage_settings_button": "Settings",
    "manage_help_overlay_toggle": "Help",
    "manage_toggle_database_metrics_panel_button": "Database Metrics",
    "manage_toggle_gen_pop_norms_panel_button": "General Population Norms",
    "manage_toggle_similarities_panel_button": "Similarities Analysis",
    "manage_toggle_search_panel_button": "Search",
    "manage_toggle_transits_panel_button": "Transit View",
    "manage_toggle_batch_edit_panel_button": "Batch Edit Panel",
    # Natal Chart View controls
    "manage_button": "Back to Database View",
    "database_view_button": "Close Chart View and return to Database View",
    "help_overlay_toggle": "Help",
}


def _has_textual_content(text: str) -> bool:
    return any(char.isalnum() for char in text)


def apply_default_text_tooltips(
    container: QWidget,
    tooltip_overrides: Mapping[str, str] | None = None,
) -> None:
    """Populate missing tooltips using readable text or object-name overrides."""
    overrides = dict(DEFAULT_TOOLTIP_OVERRIDES)
    if tooltip_overrides:
        overrides.update(tooltip_overrides)

    widgets = [
        *container.findChildren(QLabel),
        *container.findChildren(QAbstractButton),
    ]
    for widget in widgets:
        if widget.toolTip().strip():
            continue

        object_name = widget.objectName().strip()
        override_text = overrides.get(object_name, "").strip()
        if override_text:
            widget.setToolTip(override_text)
            continue

        text_getter = getattr(widget, "text", None)
        if not callable(text_getter):
            continue

        text = str(text_getter()).strip()
        if text and _has_textual_content(text):
            widget.setToolTip(text)
