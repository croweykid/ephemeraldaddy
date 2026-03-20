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
        title="FAQs: What is EphemeralDaddy?",
        description=(
            """Q. What is EphemeralDaddy?
A. EphemeralDaddy (ED) is part astrology lab, part database notebook, part user-defined memoir, part weird toy box."""
        ),
        keywords=("faq", "what is", "overview"),
    ),
    HelpEntry(
        title="FAQs: Why would someone use ED?",
        description=(
            """Q. Why would someone use ED?
A. Some reasons:
1) Debunking/Bunking
You wonder if there's any merit to astrology at all. Does it work? Probably not, right? But what the hell, it's been around awhile. So have a lot of idiotic things. If only there were a way to confirm or discredit it once and for all! (Yes, there were those bad faith "studies" done based solely on sun signs being used to predict things astrology can't claim to predict, but they were obviously whack; the 'twin study' was the only piece of legitimate science in the mainstream skeptic camp, and I disagree with how it was interpreted, albeit not with the methods of execution) - WELL here. Have a DIY kit for evaluating the people in your life as an experiment. lol Then decide for yourself.

2) Dark mode
You need dark mode and wanted a free astrology app.

3) Privacy / Data Control
You wanted a secure, private offline astro chart database that's easy to access.

4) Nakshatras
You wanted an app that calculated tropical zodiac signs but also included nakshatras in a way that is readable for those more familiar with Western (Tropical/Grecoroman) astrological tradition.

5) Anti-Cloud
You wanted an good offline astrology app that wouldn't force automated updates on you or start locking features behind a paywall as the universal quality declines, and features get dumbed down.

6) Sociological/Psychological Intrigue
You wondered how many people you've met in life & could remember & wanted to see if there were any patterns in your relationships. While ED is essentially an astrological app at its core, I am increasingly rolling out mundane sociological metrics as well, for those who just want to analyze patterns in their relationships in a purely science-driven manner, independent of birth date shiz.

If you treat it like a research workspace (not an omniscient oracle), you’ll have a good time."""
        ),
        keywords=("why", "reasons", "privacy", "dark mode", "nakshatra"),
    ),
    HelpEntry(
        title="1A) Chart View (Chart Entry / Editor)",
        description=(
            """This is where you create or edit one chart at a time.

Key features:
- Name / Alias / Birth date / Birth place inputs
- Chart Type dropdown
- placeholder (check if birth date/year is unknown) checkbox
- Save/update controls
- Right-side metrics and mini-analysis widgets

Use this window when you want to:
- Enter a new chart
- Edit an existing one
- Mark a chart as a placeholder
- Set chart classification manually"""
        ),
        keywords=("chart view", "entry", "editor"),
    ),
    HelpEntry(
        title="1B) Database View (Manage Charts)",
        description=(
            """This is mission control for your whole chart collection.

Key features:
- Chart list in the center
- Search/filter panel (includes Chart Type)
- Sorting options (including Cursedness)
- Data management actions (backup/import/export)
- Buttons for Transit View and 🧬 Composite

Use this window when you want to:
- Browse and filter lots of charts
- Batch-manage records
- Open transit/composite tools
- Import or export CSV datasets"""
        ),
        keywords=("database", "manage", "filters", "sort"),
    ),
    HelpEntry(
        title="1C/1D) Transit + Composite tools",
        description=(
            """C. Transit View
This is for current/dated transit overlays and “what’s active now” checks.

Use it when you want:
- Transit snapshots
- Daily vibe / life forecast style transit windows
- A practical, quick-look timing tool

D. Composite / Synastry tools
This currently gives you a basic chart-over-chart aspect workflow.

Use it when you want:
- A rough compatibility lens
- Overlay-style chart comparison

⚠️ Synastry Tools are still early-stage (details below in the Synastry section)."""
        ),
        keywords=("transit", "composite", "synastry"),
    ),
    HelpEntry(
        title="2) Chart calculation: methods & philosophy",
        description=(
            """- Planetary positions are computed with Swiss Ephemeris-backed logic (with offline setup supported).
- The app computes positions, houses, and aspects, then derives distributions and ranking-style metrics.
- Philosophy-wise: this is built as an exploratory tool. It favors inspectable intermediate outputs over pretending every interpretation is settled truth.
- Practical takeaway: treat calculations as structured inputs; treat textual interpretations as draft commentary."""
        ),
        keywords=("calculation", "swiss ephemeris", "method"),
    ),
    HelpEntry(
        title="2) Chart Types + placeholders + interpretations",
        description=(
            """Chart Types
- Chart Type is a classifier/tag for what a chart record is (for example: personal, public database import, event, synastry-generated contexts).
- You set this manually in Natal Chart View (Chart Entry/Edit).
- The app also assigns defaults in some generation/import pathways.
- In Manage Charts, Chart Type is filterable, so you can separate personal notes from imported/public datasets.

Sign/Position descriptions (important reality check)
Short version: useful as rough prompts, not gospel.

Placeholder charts
What they are:
- A reminder/contact-style chart entry when exact birth data is missing.

What they’re good for:
- Relationship notes
- Sentiment/history tracking
- Non-astrological organization

What they’re not good for:
- Serious astrological inference"""
        ),
        keywords=("chart type", "placeholder", "interpretation"),
    ),
    HelpEntry(
        title="2) Nakshatras + gates/lines + toy metrics",
        description=(
            """Nakshatras
- Zodiac sign framework in this app is tropical.
- Nakshatras are handled separately in the usual Vedic-style spirit.
- The author’s nakshatra notes are intentionally rough research notes, not a finished published doctrine.

Gates, Lines & Channels
For anyone familiar with the framework: in Chart View, G stands for gates, and L stands for lines, but I haven't done anything with channels yet, nor included any interpretations of I Ching hexagrams, nor calculated "Earth Signs", etc.

Weird toy metrics (D&D Species, Cursedness, Gender Guesser)
These exist. They are fun. They are not commandments."""
        ),
        keywords=("nakshatra", "gates", "lines", "cursedness"),
    ),
    HelpEntry(
        title="3/4/Final Takeaways",
        description=(
            """3) Data + privacy essentials
- Your database is local (stored in your home directory), not bundled inside the app folder.
- Sharing the app directory alone does not automatically share your chart database.
- Use built-in import/export/backup tools for intentional migration or sharing.

4) Suggested new-user workflow (fast start)
1. Create your own chart in Natal Chart View.
2. Add 5–20 known people in Manage Charts.
3. Use Chart Type tags early (future-you will be grateful).
4. Use placeholders for unknown birth-time/date cases.
5. Run transit/composite tools for pattern exploration.

Final Takeaways
EphemeralDaddy is best used like a field notebook with a calculator attached.
If you expect a perfect oracle, you’ll be disappointed.
If you want a lively research cockpit with honest rough edges, you’re in exactly the right place."""
        ),
        keywords=("privacy", "workflow", "takeaways"),
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
    "manage_sort_button": "Sort the chart list (date, alphabetical, cursedness, age, birthdate, familiarity, time known, alignment, or social score).",
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
