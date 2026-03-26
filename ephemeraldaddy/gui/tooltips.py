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

# IMPORTANT: these are intentionally exact-string mappings so tooltip behavior
# disappears automatically if visible labels are renamed.
EXACT_TEXT_TOOLTIP_OVERRIDES: dict[str, str] = {
    # Requested Chart View tooltips.
    "💀": "deceased?",
    "Use Rectified Time:": "birthtime is unknown or possibly incorrect; use speculated correct time",
    "?": "birthtime unknown?",
    "Comments": "Subjective Notes panel",
    "Subjective Notes": "Subjective Notes panel",
    "Chart Info": "Chart Analysis panel",
    "Chart Analysis": "Chart Analysis panel",
    "Source": "origin of birth/biographical info",
    "Alignment": "What's your impression of their morality, you judgy bastard?",
    "💖 Positive Sentiment Intensity:": "how much you love em",
    "💔 Negative Sentiment Intensity:": "how upsetting they are",
    "Familiarity:": "How well you think you know them",

    # Sentiment types (string-sensitive by checkbox text).
    "like": "friend",
    "love": "love",
    "lil crush": "you think they're cute",
    "lust": "you're fixated",
    "revere": "mentor",
    "dislike": "enemy",
    "despise": "archnemesis",

    # Relationship types (mirrors comments in interpretations.py RELATION_TYPE).
    "self": "it's just you",
    "ride or die": "structurally intertwined, Heavenly Creatures type stuff",
    "core posse": "inseparable, bosom chum",
    "homie": "your chum",
    "mentor": "helps you understand who/what you could be, and how",
    "ward": "a human in your care; you look after them as their caregiver/provider",
    "lover": "ya hooked up",
    "frenemy": "it's complicated",
    "minor foe": "we're not cool",
    "nemesis": "big problem",
    "fascination": "dw, you're just stalking them",
    "kin by marriage": "married into fam",
    "kin by blood": "ancestors, cousins & siblings",
    "colleague": "work with",
    "authority": "power dynamic",
    "acquaintance": "just seem em around, kinda know about them a little",
    "friend of family": "(they're just around)",
    "friend of friend": "(they're just around)",
    "family of friend": "(they're just around)",
    "your lover's ex": "(self-explanatory; here cos most people have feelings about it)",
    "your friend's ex": "(self-explanatory; here cos some people have feelings about it)",
    "pet": "a nonhuman creature in your care",
    "only talk online": "you've only met online",
    "never met": "maybe a friend of a friend you only know by reputation",
    "public figure": "icon, subject to projections",
    "place": "why does this require explanation? don't get philosophical on me.",
    "event": "aren't we all an event, in a sense? NO. EVENTS ARE EVENTS. jk do whatever you're gonna, ya freak",
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
        text_getter = getattr(widget, "text", None)
        text = str(text_getter()).strip() if callable(text_getter) else ""

        exact_override_text = EXACT_TEXT_TOOLTIP_OVERRIDES.get(text, "").strip()
        if exact_override_text:
            widget.setToolTip(exact_override_text)
            continue

        if widget.toolTip().strip():
            continue

        object_name = widget.objectName().strip()
        override_text = overrides.get(object_name, "").strip()
        if override_text:
            widget.setToolTip(override_text)
            continue

        if text and _has_textual_content(text):
            widget.setToolTip(text)
