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
        title="What is EphemeralDaddy?",
        description=(
            "EphemeralDaddy is a hybrid astrology lab + local notebook for chart research, "
            "relationship pattern tracking, and exploratory analysis."
        ),
        keywords=("overview", "intro", "faq"),
    ),
    HelpEntry(
        title="Why people use it",
        description=(
            "Common use cases include personal chart study, private/offline data control, "
            "pattern-finding experiments, and a dark-mode-first astrology workspace."
        ),
        keywords=("use cases", "privacy", "dark mode", "research"),
    ),
    HelpEntry(
        title="Chart View (Entry / Editor)",
        description=(
            "Use Chart View to create or edit one chart at a time: name/alias, birth data, "
            "chart type, placeholder mode, and save/update actions."
        ),
        keywords=("chart view", "entry", "editor", "single chart"),
    ),
    HelpEntry(
        title="Database View (Manage Charts)",
        description=(
            "Use Manage Charts as mission control: browse records, search/filter by type, "
            "sort, batch-edit, back up, import/export, and launch transit/composite tools."
        ),
        keywords=("database", "manage", "filter", "sort", "backup"),
    ),
    HelpEntry(
        title="Transit View",
        description=(
            "Transit View is for dated/current overlays and quick 'what is active now' checks."
        ),
        keywords=("transits", "timing", "daily"),
    ),
    HelpEntry(
        title="Composite / Synastry tools",
        description=(
            "Composite/Synastry currently offers a practical early-stage chart-over-chart "
            "aspect workflow for compatibility exploration."
        ),
        keywords=("composite", "synastry", "compatibility", "aspects"),
    ),
    HelpEntry(
        title="Calculation philosophy",
        description=(
            "Planet positions are Swiss Ephemeris-backed. Treat computed metrics as structured "
            "inputs and text interpretations as editable draft commentary."
        ),
        keywords=("swiss ephemeris", "calculation", "method"),
    ),
    HelpEntry(
        title="Weighting methods",
        description=(
            "Scoring blends traditional astrology weighting (dignity/rulership-style logic) with "
            "project-specific experimental tuning for comparative research."
        ),
        keywords=("weights", "aspects", "houses", "scoring"),
    ),
    HelpEntry(
        title="Chart Types",
        description=(
            "Chart Type is a manual classifier/tag used to keep personal notes, imports, events, "
            "and generated contexts organized and filterable."
        ),
        keywords=("chart type", "classification", "tag"),
    ),
    HelpEntry(
        title="Interpretation text reality check",
        description=(
            "Built-in interpretations are still evolving and best treated as prompts. Verify or "
            "refine externally when you need polished or high-stakes conclusions."
        ),
        keywords=("interpretations", "prompts", "quality"),
    ),
    HelpEntry(
        title="Placeholder charts",
        description=(
            "Placeholder charts are reminder/contact records for incomplete birth data. Great for "
            "organization and notes, not for serious astrological inference."
        ),
        keywords=("placeholder", "unknown data", "reminder"),
    ),
    HelpEntry(
        title="Nakshatras",
        description=(
            "This app uses a tropical zodiac framework while exposing nakshatra outputs as separate "
            "research notes. You can refine interpretation definitions in core/interpretations.py."
        ),
        keywords=("nakshatra", "vedic", "tropical"),
    ),
    HelpEntry(
        title="Gates / Lines status",
        description=(
            "Chart View includes gate/line math outputs. Channel-level interpretation support is "
            "intentionally limited and still in-progress."
        ),
        keywords=("gates", "lines", "channels"),
    ),
    HelpEntry(
        title="Weird toy metrics",
        description=(
            "D&D Species, Cursedness, and Gender Guesser are playful comparative metrics. Useful "
            "for curiosity; not authoritative life-decision engines."
        ),
        keywords=("cursedness", "dnd", "gender guesser", "fun"),
    ),
    HelpEntry(
        title="Data + privacy essentials",
        description=(
            "Your chart database is local to your machine/home directory. Use import/export/backup "
            "tools when you intentionally want to migrate or share data."
        ),
        keywords=("privacy", "local", "backup", "database"),
    ),
    HelpEntry(
        title="Suggested quick-start workflow",
        description=(
            "Create your own chart, add a small known cohort, tag chart types early, use "
            "placeholders for missing data, and treat interpretations as draft notes."
        ),
        keywords=("workflow", "quick start", "new user"),
    ),
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
    lowered = normalized_text.lower()
    if object_name and object_name in _TOOLTIP_BY_OBJECT_NAME:
        return _TOOLTIP_BY_OBJECT_NAME[object_name]
    if normalized_text in _TOOLTIP_BY_TEXT:
        return _TOOLTIP_BY_TEXT[normalized_text]
    if lowered.startswith("sort"):
        return "Choose how records are ordered in the current list or panel."
    if lowered.startswith("search"):
        return "Find records or locations by entering keywords."
    if lowered.startswith("import"):
        return "Load external data into EphemeralDaddy."
    if lowered.startswith("export"):
        return "Save selected EphemeralDaddy data to an external file."
    if lowered.startswith("backup"):
        return "Create a restorable copy of your local database."
    if lowered.startswith("restore"):
        return "Load a previously saved backup into the local database."
    if lowered.startswith("delete"):
        return "Permanently remove selected item(s) from the database."
    if lowered.startswith("save") or lowered.startswith("update"):
        return "Write your current edits to the local database."
    if "chart type" in lowered:
        return "Set or filter the category/classifier for chart records."
    if "placeholder" in lowered:
        return "Mark this record as incomplete birth-data placeholder information."
    if "birth" in lowered and "time" in lowered:
        return "Birth time influences houses, angles, and timing-sensitive outputs."
    if "birth" in lowered and "date" in lowered:
        return "Birth date anchors planetary positions and core chart calculations."
    if "name" in lowered:
        return "Primary label used to identify this chart record."
    if "alias" in lowered:
        return "Optional alternate name or nickname for easier lookup."
    if "transit" in lowered:
        return "Open transit calculations for current or selected timing windows."
    if "composite" in lowered or "synastry" in lowered:
        return "Compare two charts using overlay/composite aspect workflows."
    if "manage" in lowered and "chart" in lowered:
        return "Open the chart database manager for search, sorting, and batch actions."
    if "help" in lowered:
        return "Open in-app guidance and searchable notes for visible controls."
    if normalized_text:
        return f"{normalized_text}: This control performs the action named on its label."
    return "This control performs the action named on its label."


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
