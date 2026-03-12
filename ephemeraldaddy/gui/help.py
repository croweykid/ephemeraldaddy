"""Help overlay notes and search index for the GUI.

This module intentionally keeps explanatory text out of `app.py` so future
contributors can update help copy in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HelpEntry:
    title: str
    description: str
    keywords: tuple[str, ...] = ()


HELP_ENTRIES: tuple[HelpEntry, ...] = (
    HelpEntry(
        title="New Chart",
        description="Reset the form so you can enter a fresh person/event chart.",
        keywords=("new", "blank", "create"),
    ),
    HelpEntry(
        title="Export Chart",
        description="Export the currently loaded chart as a JSON file.",
        keywords=("export", "json", "save"),
    ),
    HelpEntry(
        title="Manage Charts",
        description="Open the database/manager view where you can browse and edit saved charts.",
        keywords=("database", "list", "batch"),
    ),
    HelpEntry(
        title="Get Transits",
        description="Generate a personal transit popout for the currently loaded chart.",
        keywords=("transit", "current", "popout"),
    ),
    HelpEntry(
        title="Pop Out",
        description="Open the chart wheel and interpretation in a detached popout window.",
        keywords=("window", "separate", "chart"),
    ),
    HelpEntry(
        title="Search Place",
        description="Resolve a city/place into coordinates before generating a chart.",
        keywords=("location", "geocode", "birthplace"),
    ),
    HelpEntry(
        title="Save Chart",
        description="Write current edits to the database (new chart or updates to existing chart).",
        keywords=("save", "update", "database"),
    ),
    HelpEntry(
        title="Unknown Time (?)",
        description="Use noon fallback if exact birth time is unknown.",
        keywords=("unknown", "noon", "birth time"),
    ),
)


_TOOLTIP_BY_OBJECT_NAME: dict[str, str] = {
    "help_overlay_toggle": "Toggle Help Overlay mode.",
    "new_chart_button": "Start a brand-new chart entry.",
    "export_chart_button": "Export the active chart as JSON.",
    "manage_button": "Use the back arrow to return to the Manage Charts database view.",
    "current_transits_button": "Open current transits for this chart and chosen location.",
    "place_search_button": "Search for a place and fill latitude/longitude.",
    "update_button": "Save this chart to the database.",
    "manage_help_overlay_toggle": "Open the Database View help overlay.",
    "manage_new_chart_button": "Start a fresh chart entry and jump to Chart View.",
    "manage_delete_chart_button": "Delete the selected chart(s) from the database list.",
    "manage_import_csv_button": "Import chart rows from a CSV file into the database.",
    "manage_export_selected_csv_button": "Export only the currently selected chart rows to CSV.",
    "manage_backup_database_button": "Create a full database backup file.",
    "manage_restore_database_button": "Restore charts from a previously exported database backup.",
    "manage_force_refresh_button": "Recompute all database analytics and refresh every metric panel.",
    "manage_retcon_engine_button": "Open Retcon Engine tools for timeline/date experimentation.",
    "manage_composite_chart_button": "Build a composite chart from two selected saved charts.",
    "manage_toggle_transits_panel_button": "Toggle the Transit panel in the left sidebar.",
    "manage_toggle_database_metrics_panel_button": "Toggle the Database Metrics panel in the left sidebar.",
    "manage_toggle_similarities_panel_button": "Toggle the Similarities panel in the left sidebar.",
    "manage_toggle_batch_edit_panel_button": "Toggle the Batch Edit panel for multi-chart updates.",
    "manage_toggle_search_panel_button": "Toggle the Search/Filter panel on the right.",
    "manage_sort_button": "Sort the chart list (date, alphabetical, cursedness, age, birthdate, familiarity, time known, or social score).",
}

_TOOLTIP_BY_TEXT: dict[str, str] = {
    "Name": "Primary label/name for the person or event.",
    "Birth time": "Exact local birth time used for houses and rising sign.",
    "Retcon Time": "Optional override used by Retcon workflows.",
    "use retcon": "Enable Retcon time as the active time value.",
    "Delete Chart": "Delete the selected chart(s) from the database.",
    "Sort: Alphabetical": "Open sorting options for the saved chart list.",
}


def tooltip_for_widget(object_name: str, text: str) -> str:
    normalized_text = (text or "").strip()
    if object_name and object_name in _TOOLTIP_BY_OBJECT_NAME:
        return _TOOLTIP_BY_OBJECT_NAME[object_name]
    if normalized_text in _TOOLTIP_BY_TEXT:
        return _TOOLTIP_BY_TEXT[normalized_text]
    if normalized_text:
        return f"{normalized_text}: no custom note yet. Add details in ephemeraldaddy/gui/help.py."
    return "No help note yet. Add details in ephemeraldaddy/gui/help.py."


def search_help_entries(query: str) -> Iterable[HelpEntry]:
    needle = (query or "").strip().lower()
    if not needle:
        return HELP_ENTRIES
    return tuple(
        entry
        for entry in HELP_ENTRIES
        if needle in entry.title.lower()
        or needle in entry.description.lower()
        or any(needle in keyword.lower() for keyword in entry.keywords)
    )
