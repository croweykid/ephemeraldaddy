"""Database View right-hand search panel UI builder.

This module intentionally owns Database View search-panel widgets and helper
logic directly.  It must not import :mod:`ephemeraldaddy.gui.app`; the main
window delegates here rather than the extracted panel reaching back into app.py
as a service locator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ephemeraldaddy.gui.settings_keys import (
    SETTINGS_KEY_HIDDEN_CHARTS_FILTER_MODE,
    SETTINGS_KEY_HIDE_PLACEHOLDER_CHARTS_FILTER,
)

from ephemeraldaddy.core.interpretations import (
    JONES_PLANETS,
    NATAL_CHART_MAX_YEAR,
    NATAL_CHART_MIN_YEAR,
)
from ephemeraldaddy.gui.tag_categories import tag_category_display_name


BODY_DYNAMICS_ROLE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Enabler", "enabler"),
    ("Antagonist", "antagonist"),
    ("Escalator", "escalator"),
)

# The Isolated Factors filter used to require 3x the next-highest weight.
# Lowering that requirement by 15% keeps the filter selective while allowing
# near-isolated dominance profiles to surface in Database View searches.
ISOLATED_DOMINANCE_NEXT_HIGHEST_MULTIPLIER = 3.0 * 0.85

def weight_is_at_least_triple_next_highest(
    weights: dict[str, float] | None,
    selected_key: str,
) -> bool:
    """Return whether a selected weight clears the isolated dominance bar.

    The historical threshold was 3x the next-highest peer. Database View
    searches now use a 15% looser threshold (2.55x) so the Isolated Factors
    filter can return near-isolated dominance profiles without becoming broad.

    ``selected_key == "Any"`` means any weighted key may satisfy the isolated
    dominance test. This is the active Isolated Factors wildcard behavior.
    """
    if not weights:
        return False

    def numeric_weight(weight_key: str) -> float | None:
        try:
            return float(weights.get(weight_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return None

    def key_is_isolated(candidate_key: str) -> bool:
        if candidate_key not in weights:
            return False
        selected_weight = numeric_weight(candidate_key)
        if selected_weight is None or selected_weight <= 0.0:
            return False

        next_highest_weight = 0.0
        for weight_key in weights:
            if str(weight_key) == candidate_key:
                continue
            other_weight = numeric_weight(str(weight_key))
            if other_weight is None:
                return False
            next_highest_weight = max(next_highest_weight, other_weight)
        return selected_weight >= (
            next_highest_weight * ISOLATED_DOMINANCE_NEXT_HIGHEST_MULTIPLIER
        )

    if selected_key == "Any":
        return any(key_is_isolated(str(weight_key)) for weight_key in weights)
    return key_is_isolated(selected_key)



def focus_database_search_input(window) -> None:
    """Move keyboard focus to Database View's chart search field."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLineEdit

    search_input = getattr(window, "search_text_input", None)
    if not isinstance(search_input, QLineEdit):
        return
    search_panel_button = getattr(window, "search_panel_button", None)
    if search_panel_button is not None and hasattr(search_panel_button, "setChecked"):
        search_panel_button.setChecked(True)
    show_search_panel = getattr(window, "_show_search_database_panel", None)
    if callable(show_search_panel):
        show_search_panel()
    search_input.setFocus(Qt.ShortcutFocusReason)
    search_input.selectAll()


def dominant_enneagram_types_for_search(chart) -> set[int]:
    """Return the dominant Enneagram type set used by Database View filters."""
    if chart is None:
        return set()
    weights = getattr(chart, "enneagram_type_weights", None)
    numeric_weights: dict[int, float] = {}
    if isinstance(weights, dict):
        for raw_type, raw_weight in weights.items():
            try:
                enneagram_type = int(raw_type)
                weight = float(raw_weight)
            except (TypeError, ValueError):
                continue
            if 1 <= enneagram_type <= 9:
                numeric_weights[enneagram_type] = weight
    if numeric_weights:
        max_weight = max(numeric_weights.values())
        return {
            enneagram_type
            for enneagram_type, weight in numeric_weights.items()
            if weight == max_weight
        }
    try:
        dominant_type = int(getattr(chart, "dominant_enneagram_type", 0) or 0)
    except (TypeError, ValueError):
        return set()
    return {dominant_type} if 1 <= dominant_type <= 9 else set()


def matched_expectations_value_for_chart(chart) -> int:
    """Return a clamped matched-expectations score for DBV search filters."""
    if chart is None:
        return 0
    raw_value = getattr(chart, "matched_expectations", 0)
    try:
        parsed_value = int(raw_value) if raw_value is not None else 0
    except (TypeError, ValueError):
        parsed_value = 0
    return max(-10, min(10, parsed_value))


def build_birthdate_filter_date(
    *,
    month: int | None,
    day: int | None,
    year: int | None,
    is_latest: bool,
):
    """Build an earliest/latest concrete date from partial DBV birthdate filters."""
    import calendar
    import datetime

    if month is None and day is None and year is None:
        return None
    resolved_year = int(year) if year is not None else (9999 if is_latest else 1)
    resolved_month = int(month) if month is not None else (12 if is_latest else 1)
    if day is not None:
        resolved_day = int(day)
    else:
        resolved_day = calendar.monthrange(resolved_year, resolved_month)[1] if is_latest else 1
    try:
        return datetime.date(resolved_year, resolved_month, resolved_day)
    except ValueError:
        return None


def parse_year_first_encountered_text(raw_value: str | None) -> int | None:
    """Parse a DBV year-first-encountered filter field."""
    value = (raw_value or "").strip()
    if value == "":
        return None
    if value.isdigit():
        return int(value)
    return None


def _dnd_prediction_adapter_for_window(window):
    """Return the Fantasy RPG prediction adapter factory from DBV or its owner."""
    adapter_factory = getattr(window, "_dnd_prediction_adapter", None)
    if callable(adapter_factory):
        return adapter_factory()

    owner_window = getattr(window, "_owner_window", None)
    owner = owner_window() if callable(owner_window) else getattr(window, "_app_owner", None)
    if owner is not None and owner is not window:
        adapter_factory = getattr(owner, "_dnd_prediction_adapter", None)
        if callable(adapter_factory):
            return adapter_factory()

    return None


def dnd_species_class_payload_for_chart(window, chart) -> dict[str, object]:
    """Return the appwide Fantasy RPG species/class cache for a chart."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        adapter = _dnd_prediction_adapter_for_window(window)
        if adapter is None:
            raise AttributeError("_dnd_prediction_adapter")
        return adapter.cache_species_class_metadata(chart)
    except Exception:
        logger.exception(
            "Failed to refresh Fantasy RPG species/class cache for chart UID %s.",
            getattr(chart, "chart_uid", None) or getattr(chart, "uid", None),
        )
        return {}


def cached_top_three_species_for_filter(window, chart) -> list[tuple[str, str]]:
    """Return Top 3 Species/Subspecies from the shared appwide cache."""
    payload = dnd_species_class_payload_for_chart(window, chart)
    species_payloads = payload.get("species") if isinstance(payload, dict) else None
    if not isinstance(species_payloads, list):
        return []
    top_three: list[tuple[str, str]] = []
    for entry in species_payloads[:3]:
        if not isinstance(entry, dict):
            continue
        family = str(entry.get("family", "") or "").strip()
        subtype = str(entry.get("subtype", "") or "").strip()
        if family:
            top_three.append((family, subtype))
    return top_three


def active_body_dynamics_filters(window) -> list[dict[str, object]]:
    """Return active Body Dynamics filter rows from the Database View search panel."""
    return [
        filters
        for filters in getattr(window, "_body_dynamics_filters", [])
        if str(filters["body"].currentData()) != "Any"
    ]


def body_dynamics_filters_are_active(window) -> bool:
    """Return whether any Body Dynamics filter row is selected."""
    return bool(active_body_dynamics_filters(window))


def reset_body_dynamics_filters(window) -> None:
    """Reset all Body Dynamics filter widgets to their default state."""
    for filters in getattr(window, "_body_dynamics_filters", []):
        filters["body"].setCurrentIndex(0)
        filters["role"].setCurrentIndex(0)
        filters["or"].setChecked(False)
        filters["exclude"].setChecked(False)
        filters["and"].setChecked(True)


def _body_dynamics_filter_matches(chart, filters: dict[str, object]) -> bool:
    body = str(filters["body"].currentData())
    role = str(filters["role"].currentData())
    if body == "Any" or not role:
        return False

    from ephemeraldaddy.core import db

    roles = db._parse_body_dynamics_roles(getattr(chart, "body_dynamics_roles", None))
    if body not in roles:
        roles = db._resolve_body_dynamics_roles(chart)
    return roles.get(body) == role


def chart_matches_body_dynamics_filters(window, chart, filters: list[dict[str, object]] | None = None) -> bool:
    """Apply active Body Dynamics AND/OR/EXCLUDE filters to a chart."""
    active_filters = list(filters if filters is not None else active_body_dynamics_filters(window))
    if not active_filters:
        return True

    and_filters = [filters for filters in active_filters if filters["and"].isChecked()]
    or_filters = [filters for filters in active_filters if filters["or"].isChecked()]
    exclude_filters = [filters for filters in active_filters if filters["exclude"].isChecked()]

    for filters in and_filters:
        if not _body_dynamics_filter_matches(chart, filters):
            return False
    if or_filters and not any(_body_dynamics_filter_matches(chart, filters) for filters in or_filters):
        return False
    for filters in exclude_filters:
        if _body_dynamics_filter_matches(chart, filters):
            return False
    return True


def _tree_scroll_value(tree) -> int:
    """Return a QTreeWidget vertical-scroll value without depending on app.py."""
    scrollbar_getter = getattr(tree, "verticalScrollBar", None)
    scrollbar = scrollbar_getter() if callable(scrollbar_getter) else None
    value_getter = getattr(scrollbar, "value", None)
    if not callable(value_getter):
        return 0
    try:
        return int(value_getter())
    except (TypeError, ValueError):
        return 0


def _restore_tree_scroll_value(tree, value: int) -> None:
    """Restore a QTreeWidget vertical-scroll value after a controlled rebuild."""
    scrollbar_getter = getattr(tree, "verticalScrollBar", None)
    scrollbar = scrollbar_getter() if callable(scrollbar_getter) else None
    setter = getattr(scrollbar, "setValue", None)
    if callable(setter):
        setter(int(value))


def _tree_expanded_state(tree) -> dict[str, bool]:
    """Capture top-level QTreeWidget expansion state by item UserRole/text key."""
    from PySide6.QtCore import Qt

    expanded_state: dict[str, bool] = {}
    if not hasattr(tree, "topLevelItemCount"):
        return expanded_state
    for index in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(index)
        if item is None:
            continue
        key = str(item.data(0, Qt.UserRole) or item.text(0) or "")
        if key:
            expanded_state[key.casefold()] = item.isExpanded()
    return expanded_state


def _tag_tree_signature(known_tags: list[str]) -> tuple[str, ...]:
    """Return the structural tag tree signature for rebuild deduping."""
    clean_tags = {str(tag or "").strip() for tag in known_tags if str(tag or "").strip()}
    return tuple(sorted(clean_tags, key=str.casefold))


def _trait_tree_signature() -> tuple[str, ...]:
    """Return the active trait-list signature for rebuild deduping."""
    from ephemeraldaddy.analysis.traits import list_traits

    names: list[str] = []
    seen: set[str] = set()
    for trait in list_traits(active_only=True):
        trait_name = str(trait.get("name", "")).strip()
        trait_key = trait_name.casefold()
        if trait_name and trait_key not in seen:
            seen.add(trait_key)
            names.append(trait_name)
    return tuple(sorted(names, key=str.casefold))


def _split_search_tag_category(tag: str) -> tuple[str, str]:
    clean_tag = str(tag or "").strip()
    if "." not in clean_tag:
        return "", clean_tag
    prefix, value = clean_tag.split(".", 1)
    return prefix.strip(), value.strip() or clean_tag


def _tag_value_display_name(value: str) -> str:
    clean_value = str(value or "").strip()
    return clean_value.replace("_", " ").replace("-", " ").title() if clean_value else ""

def refresh_search_tags_list(window, known_tags: list[str]) -> None:
    """Refresh the Database View tag-filter tree for ``window``."""
    if not hasattr(window, "search_tags_list_widget"):
        return
    search_tags_toggle = getattr(window, "search_tags_toggle", None)
    is_checked = getattr(search_tags_toggle, "isChecked", None)
    if callable(is_checked) and not is_checked():
        return

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QRadioButton, QWidget

    from ephemeraldaddy.gui.features.charts.tagging import parse_tag_text
    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    selected_tags = {
        tag.casefold()
        for tag in parse_tag_text(
            window.search_tags_input.text() if hasattr(window, "search_tags_input") else ""
        )
    }
    signature = _tag_tree_signature(known_tags)
    if signature == getattr(window, "_dbv_search_tag_tree_signature", None):
        sync_search_tags_list_selection(window, set(selected_tags))
        return

    existing_checkboxes = getattr(window, "search_tag_filter_checkboxes", {})
    existing_modes = {tag_name: checkbox.mode() for tag_name, checkbox in existing_checkboxes.items()}
    existing_logic = {
        tag_name: str(buttons.get("checked", "and"))
        for tag_name, buttons in getattr(window, "search_tag_filter_logic_buttons", {}).items()
    }
    tree = window.search_tags_list_widget
    scroll_value = _tree_scroll_value(tree)
    expanded_state = _tree_expanded_state(tree)
    window.search_tag_filter_checkboxes = {}
    window.search_tag_filter_logic_buttons = {}
    window.search_tag_category_checkboxes = {}
    window.search_tag_category_logic_buttons = {}
    tree.clear()
    QTreeWidgetItemClass = getattr(window, "_dbv_tag_tree_item_class", None)
    if QTreeWidgetItemClass is None:
        return

    grouped: dict[str, list[tuple[str, str]]] = {}
    uncategorized: list[tuple[str, str]] = []
    for tag in known_tags:
        prefix, value = _split_search_tag_category(tag)
        if prefix:
            grouped.setdefault(prefix, []).append((tag, value))
        else:
            uncategorized.append((tag, value))

    def make_logic_buttons(current: str) -> dict[str, object]:
        group = QButtonGroup(window)
        group.setExclusive(True)
        and_button = QRadioButton("&&")
        or_button = QRadioButton("OR")
        not_button = QRadioButton("🚫")
        for button in (and_button, or_button, not_button):
            button.setStyleSheet("font-size: 10px; margin: 0px; padding: 0px;")
            group.addButton(button)
        mapping = {"and": and_button, "or": or_button, "not": not_button}
        mapping.get(current, and_button).setChecked(True)
        return {
            "group": group,
            "and": and_button,
            "or": or_button,
            "not": not_button,
            "checked": current if current in mapping else "and",
        }

    def make_row(
        checkbox: QuadStateSlider,
        logic: dict[str, object],
        tag_name: str | None = None,
        category_prefix: str | None = None,
    ) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(3)
        row_layout.addWidget(checkbox, 1)
        for key in ("and", "or", "not"):
            button = logic[key]
            if category_prefix is not None:
                button.toggled.connect(
                    lambda checked, mode=key, prefix=category_prefix: on_search_tag_category_logic_changed(
                        window, prefix, mode, checked
                    )
                )
            else:
                button.toggled.connect(
                    lambda checked, mode=key, tag=tag_name: on_search_tag_logic_changed(
                        window, tag, mode, checked
                    )
                )
            row_layout.addWidget(button)
        return row

    def add_untagged_item() -> None:
        previous_checkbox = getattr(window, "search_untagged_checkbox", None)
        previous_mode = (
            previous_checkbox.mode()
            if previous_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        checkbox = QuadStateSlider("untagged")
        checkbox.setMode(previous_mode)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.search_untagged_checkbox = checkbox
        item = QTreeWidgetItemClass(["untagged"])
        tree.addTopLevelItem(item)
        if hasattr(checkbox, "_label"):
            checkbox._label.setStyleSheet("padding-left: 2px; font-style: italic;")
        logic = make_logic_buttons(
            "not" if checkbox.mode() == QuadStateSlider.MODE_FALSE else "and"
        )
        window.search_untagged_logic_buttons = logic

        def on_untagged_logic_changed(mode: str, checked: bool) -> None:
            if not checked:
                return
            logic["checked"] = mode
            checkbox.setMode(
                (
                    QuadStateSlider.MODE_FALSE
                    if mode == "not"
                    else QuadStateSlider.MODE_TRUE
                ),
                emit_signal=True,
            )

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(3)
        row_layout.addWidget(checkbox, 1)
        for key in ("and", "or", "not"):
            button = logic[key]
            button.toggled.connect(
                lambda checked, mode=key: on_untagged_logic_changed(mode, checked)
            )
            row_layout.addWidget(button)
        tree.setItemWidget(item, 0, row)

    add_untagged_item()

    def add_tag_item(parent_item, tag: str, value: str) -> None:
        display = _tag_value_display_name(value)
        item = QTreeWidgetItemClass([display])
        parent_item.addChild(item)
        checkbox = QuadStateSlider(display)
        checkbox.setMode(
            QuadStateSlider.MODE_TRUE
            if tag.casefold() in selected_tags
            else existing_modes.get(tag, QuadStateSlider.MODE_EMPTY)
        )
        checkbox.modeChanged.connect(lambda _mode, tag_name=tag: on_search_tag_mode_changed(window, tag_name))
        logic = make_logic_buttons(existing_logic.get(tag, "and"))
        window.search_tag_filter_checkboxes[tag] = checkbox
        window.search_tag_filter_logic_buttons[tag] = logic
        tree.setItemWidget(item, 0, make_row(checkbox, logic, tag))

    for prefix in sorted(grouped, key=lambda key: tag_category_display_name(key).casefold()):
        category_item = QTreeWidgetItemClass([tag_category_display_name(prefix)])
        category_item.setData(0, Qt.UserRole, prefix.casefold())
        tree.addTopLevelItem(category_item)
        category_checkbox = QuadStateSlider(tag_category_display_name(prefix))
        category_checkbox.modeChanged.connect(
            lambda mode, p=prefix: on_search_tag_category_mode_changed(window, p, mode)
        )
        category_logic = make_logic_buttons("and")
        window.search_tag_category_checkboxes[prefix] = category_checkbox
        window.search_tag_category_logic_buttons[prefix] = category_logic
        tree.setItemWidget(category_item, 0, make_row(category_checkbox, category_logic, None, prefix))
        for tag, value in sorted(grouped[prefix], key=lambda item: _tag_value_display_name(item[1]).casefold()):
            add_tag_item(category_item, tag, value)
        category_item.setExpanded(expanded_state.get(prefix.casefold(), False))
    for tag, value in sorted(uncategorized, key=lambda item: _tag_value_display_name(item[1]).casefold()):
        root_item = QTreeWidgetItemClass([_tag_value_display_name(value)])
        tree.addTopLevelItem(root_item)
        checkbox = QuadStateSlider(_tag_value_display_name(value))
        checkbox.setMode(
            QuadStateSlider.MODE_TRUE
            if tag.casefold() in selected_tags
            else existing_modes.get(tag, QuadStateSlider.MODE_EMPTY)
        )
        checkbox.modeChanged.connect(lambda _mode, tag_name=tag: on_search_tag_mode_changed(window, tag_name))
        logic = make_logic_buttons(existing_logic.get(tag, "and"))
        window.search_tag_filter_checkboxes[tag] = checkbox
        window.search_tag_filter_logic_buttons[tag] = logic
        tree.setItemWidget(root_item, 0, make_row(checkbox, logic, tag))

    window._dbv_search_tag_tree_signature = signature
    _restore_tree_scroll_value(tree, scroll_value)



def has_active_chart_filters(window) -> bool:
    """Return whether any Database View chart-search filter is active."""
    from ephemeraldaddy.gui.features.charts.search_text import database_search_text_is_active
    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    selected_sentiments = {
        name
        for name, checkbox in window.sentiment_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
    }
    excluded_sentiments = {
        name
        for name, checkbox in window.sentiment_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
    }
    include_none_sentiment = (
        "none" in window.sentiment_filter_checkboxes
        and window.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
    )
    exclude_none_sentiment = (
        "none" in window.sentiment_filter_checkboxes
        and window.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
    )
    selected_relationship_types = {
        name
        for name, checkbox in window.relationship_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
    }
    excluded_relationship_types = {
        name
        for name, checkbox in window.relationship_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
    }
    include_none_relationship = (
        "none" in window.relationship_filter_checkboxes
        and window.relationship_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
    )
    exclude_none_relationship = (
        "none" in window.relationship_filter_checkboxes
        and window.relationship_filter_checkboxes["none"].mode()
        == QuadStateSlider.MODE_FALSE
    )
    selected_genders = {
        name
        for name, checkbox in window.gender_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
    }
    excluded_genders = {
        name
        for name, checkbox in window.gender_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
    }
    include_none_gender = (
        "none" in window.gender_filter_checkboxes
        and window.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
    )
    exclude_none_gender = (
        "none" in window.gender_filter_checkboxes
        and window.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
    )
    selected_guessed_gender = str(window.gender_guessed_filter_combo.currentData() or "")
    selected_chart_types = {
        source
        for source, checkbox in window.chart_type_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE
    }
    excluded_chart_types = {
        source
        for source, checkbox in window.chart_type_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE
    }
    selected_data_ratings = {
        grade
        for grade, checkbox in window.data_rating_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE
    }
    excluded_data_ratings = {
        grade
        for grade, checkbox in window.data_rating_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE
    }
    selected_generations = {
        name
        for name, checkbox in window.generation_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE
    }
    excluded_generations = {
        name
        for name, checkbox in window.generation_filter_checkboxes.items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE
    }
    birthdate_earliest_month = window._parse_integer_filter_text(
        window._birthdate_earliest_month_input.text()
        if window._birthdate_earliest_month_input is not None
        else ""
    )
    birthdate_earliest_day = window._parse_integer_filter_text(
        window._birthdate_earliest_day_input.text()
        if window._birthdate_earliest_day_input is not None
        else ""
    )
    birthdate_earliest_year = window._parse_integer_filter_text(
        window._birthdate_earliest_year_input.text()
        if window._birthdate_earliest_year_input is not None
        else ""
    )
    birthdate_latest_month = window._parse_integer_filter_text(
        window._birthdate_latest_month_input.text()
        if window._birthdate_latest_month_input is not None
        else ""
    )
    birthdate_latest_day = window._parse_integer_filter_text(
        window._birthdate_latest_day_input.text()
        if window._birthdate_latest_day_input is not None
        else ""
    )
    birthdate_latest_year = window._parse_integer_filter_text(
        window._birthdate_latest_year_input.text()
        if window._birthdate_latest_year_input is not None
        else ""
    )
    selected_search_tags, optional_search_tags, excluded_search_tags = collect_search_tag_filter_sets(window)
    (
        required_present_search_traits,
        excluded_present_search_traits,
        required_absent_search_traits,
        excluded_absent_search_traits,
    ) = collect_search_trait_filter_sets(window)
    selected_enneagram_types = {
        int(enneagram_type)
        for enneagram_type, checkbox in getattr(window, "enneagram_type_filter_checkboxes", {}).items()
        if checkbox.mode() == QuadStateSlider.MODE_TRUE
    }
    excluded_enneagram_types = {
        int(enneagram_type)
        for enneagram_type, checkbox in getattr(window, "enneagram_type_filter_checkboxes", {}).items()
        if checkbox.mode() == QuadStateSlider.MODE_FALSE
    }
    search_untagged_mode = (
        window.search_untagged_checkbox.mode()
        if hasattr(window, "search_untagged_checkbox")
        and window.search_untagged_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )

    active_body_filters = [
        filters
        for filters in window._search_body_filters
        if str(filters["sign"].currentData()) != "Any"
        or str(filters["house"].currentData()) != "Any"
    ]
    active_aspect_filters = [
        filters
        for filters in window._aspect_filters
        if str(filters["planet_1"].currentData()) != "Any"
        or str(filters["aspect"].currentData()) != "Any"
        or str(filters["planet_2"].currentData()) != "Any"
    ]
    active_dominant_sign_filters = [
        filters
        for filters in window._dominant_sign_filters
        if str(filters["sign"].currentData()) != "Any"
    ]
    active_subordinate_sign_filters = [
        filters
        for filters in getattr(window, "_subordinate_sign_filters", [])
        if str(filters["sign"].currentData()) != "Any"
    ]
    active_dominant_planet_filters = [
        filters
        for filters in window._dominant_planet_filters
        if str(filters["planet"].currentData()) != "Any"
    ]
    active_subordinate_planet_filters = [
        filters
        for filters in getattr(window, "_subordinate_planet_filters", [])
        if str(filters["planet"].currentData()) != "Any"
    ]
    active_body_dynamics_filter_rows = active_body_dynamics_filters(window)
    selected_isolated_dominant_body = (
        str(window._isolated_dominant_body_filter_combo.currentData())
        if window._isolated_dominant_body_filter_combo is not None
        else "Any"
    )
    selected_isolated_dominant_sign = (
        str(window._isolated_dominant_sign_filter_combo.currentData())
        if window._isolated_dominant_sign_filter_combo is not None
        else "Any"
    )
    active_dominant_mode_filters = [
        filters
        for filters in window._dominant_mode_filters
        if filters["mode"].currentData() != "Any"
    ]
    selected_decan_sign = (
        str(window._decan_sign_filter_combo.currentData())
        if window._decan_sign_filter_combo is not None
        else "Any"
    )
    selected_decan_number = (
        str(window._decan_number_filter_combo.currentData())
        if window._decan_number_filter_combo is not None
        else "Any"
    )
    active_dominant_nakshatra_filters = [
        filters
        for filters in window._dominant_nakshatra_filters
        if str(filters["nakshatra"].currentData()) != "Any"
    ]
    active_subordinate_nakshatra_filters = [
        filters
        for filters in getattr(window, "_subordinate_nakshatra_filters", [])
        if str(filters["nakshatra"].currentData()) != "Any"
    ]
    active_dominant_element_filters = [
        filters
        for filters in window._dominant_element_filters
        if str(filters["element"].currentData()) != "Any"
    ]
    year_first_encountered_earliest = (
        window._year_first_encountered_earliest_input.text().strip()
        if window._year_first_encountered_earliest_input is not None
        else ""
    )
    year_first_encountered_latest = (
        window._year_first_encountered_latest_input.text().strip()
        if window._year_first_encountered_latest_input is not None
        else ""
    )
    year_first_encountered_blank_state = (
        window._year_first_encountered_blank_checkbox.mode()
        if window._year_first_encountered_blank_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    guessed_gender_filter = str(window.gender_guessed_filter_combo.currentData() or "")
    positive_sentiment_intensity_min = window._parse_integer_filter_text(
        window._positive_sentiment_intensity_min_input.text()
        if window._positive_sentiment_intensity_min_input is not None
        else ""
    )
    positive_sentiment_intensity_max = window._parse_integer_filter_text(
        window._positive_sentiment_intensity_max_input.text()
        if window._positive_sentiment_intensity_max_input is not None
        else ""
    )
    negative_sentiment_intensity_min = window._parse_integer_filter_text(
        window._negative_sentiment_intensity_min_input.text()
        if window._negative_sentiment_intensity_min_input is not None
        else ""
    )
    negative_sentiment_intensity_max = window._parse_integer_filter_text(
        window._negative_sentiment_intensity_max_input.text()
        if window._negative_sentiment_intensity_max_input is not None
        else ""
    )
    familiarity_min = window._parse_integer_filter_text(
        window._familiarity_min_input.text()
        if window._familiarity_min_input is not None
        else ""
    )
    familiarity_max = window._parse_integer_filter_text(
        window._familiarity_max_input.text()
        if window._familiarity_max_input is not None
        else ""
    )
    alignment_score_min = window._parse_signed_integer_filter_text(
        window._alignment_score_min_input.text()
        if window._alignment_score_min_input is not None
        else ""
    )
    alignment_score_max = window._parse_signed_integer_filter_text(
        window._alignment_score_max_input.text()
        if window._alignment_score_max_input is not None
        else ""
    )
    include_blank_alignment = bool(
        window._alignment_score_blank_checkbox is not None
        and window._alignment_score_blank_checkbox.isChecked()
    )
    matched_expectations_min = window._parse_signed_integer_filter_text(
        window._matched_expectations_min_input.text()
        if window._matched_expectations_min_input is not None
        else ""
    )
    matched_expectations_max = window._parse_signed_integer_filter_text(
        window._matched_expectations_max_input.text()
        if window._matched_expectations_max_input is not None
        else ""
    )
    include_blank_matched_expectations = bool(
        window._matched_expectations_blank_checkbox is not None
        and window._matched_expectations_blank_checkbox.isChecked()
    )
    notes_comments_mode = (
        window._notes_comments_filter_checkbox.mode()
        if window._notes_comments_filter_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    notes_comments_text = (
        window._notes_comments_filter_input.text().strip()
        if window._notes_comments_filter_input is not None
        else ""
    )
    notes_bio_mode = (
        window._notes_bio_filter_checkbox.mode()
        if window._notes_bio_filter_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    notes_bio_text = (
        window._notes_bio_filter_input.text().strip()
        if window._notes_bio_filter_input is not None
        else ""
    )
    notes_quotes_mode = (
        window._notes_quotes_filter_checkbox.mode()
        if window._notes_quotes_filter_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    notes_quotes_text = (
        window._notes_quotes_filter_input.text().strip()
        if window._notes_quotes_filter_input is not None
        else ""
    )
    notes_rectification_mode = (
        window._notes_rectification_filter_checkbox.mode()
        if window._notes_rectification_filter_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    notes_rectification_text = (
        window._notes_rectification_filter_input.text().strip()
        if window._notes_rectification_filter_input is not None
        else ""
    )
    notes_source_mode = (
        window._notes_source_filter_checkbox.mode()
        if window._notes_source_filter_checkbox is not None
        else QuadStateSlider.MODE_EMPTY
    )
    notes_source_text = (
        window._notes_source_filter_input.text().strip()
        if window._notes_source_filter_input is not None
        else ""
    )
    notes_comments_active = (
        notes_comments_mode != QuadStateSlider.MODE_EMPTY and bool(notes_comments_text)
    )
    notes_bio_active = (
        notes_bio_mode != QuadStateSlider.MODE_EMPTY and bool(notes_bio_text)
    )
    notes_quotes_active = (
        notes_quotes_mode != QuadStateSlider.MODE_EMPTY and bool(notes_quotes_text)
    )
    notes_rectification_active = (
        notes_rectification_mode != QuadStateSlider.MODE_EMPTY and bool(notes_rectification_text)
    )
    notes_source_active = (
        notes_source_mode != QuadStateSlider.MODE_EMPTY and bool(notes_source_text)
    )
    selected_human_design_channels = {
        str(combo.currentData())
        for combo in window._human_design_channel_filters
        if str(combo.currentData()) != "Any"
    }
    selected_human_design_gates = {
        (
            int(filters["gate"].currentData()) if str(filters["gate"].currentData()) != "Any" else "Any",
            int(filters["line"].currentData()) if str(filters["line"].currentData()) != "Any" else "Any",
        )
        for filters in getattr(window, "_human_design_gate_line_filters", [])
        if str(filters["gate"].currentData()) != "Any"
        or str(filters["line"].currentData()) != "Any"
    }
    selected_human_design_type = (
        str(window._human_design_type_filter_combo.currentData())
        if window._human_design_type_filter_combo is not None
        else "Any"
    )
    selected_human_design_profile = (
        str(window._human_design_profile_filter_combo.currentData())
        if window._human_design_profile_filter_combo is not None
        else "Any"
    )
    selected_human_design_defined_centers = {
        str(combo.currentData())
        for combo in window._human_design_defined_center_filters
        if str(combo.currentData()) != "Any"
    }
    dnd_stat_ranges_active = any(
        (
            window._parse_integer_filter_text(min_input.text()) is not None
            or window._parse_integer_filter_text(
                window._dnd_stat_filter_max_inputs.get(stat_key).text()
                if stat_key in window._dnd_stat_filter_max_inputs
                else ""
            )
            is not None
        )
        for stat_key, min_input in window._dnd_stat_filter_min_inputs.items()
    )

    return not (
        not getattr(window, "_hide_hypothetical_charts", False)
        and window.incomplete_birthdate_checkbox.mode() == QuadStateSlider.MODE_EMPTY
        and (
            not getattr(window, "_show_hidden_charts", False)
            or not hasattr(window, "hidden_charts_checkbox")
            or window.hidden_charts_checkbox.mode() == QuadStateSlider.MODE_EMPTY
        )
        and window.birthtime_unknown_checkbox.mode() == QuadStateSlider.MODE_EMPTY
        and window.retconned_checkbox.mode() == QuadStateSlider.MODE_EMPTY
        and (window.living_checkbox is None or window.living_checkbox.mode() == QuadStateSlider.MODE_EMPTY)
        and not selected_sentiments
        and not excluded_sentiments
        and not include_none_sentiment
        and not exclude_none_sentiment
        and not selected_relationship_types
        and not excluded_relationship_types
        and not include_none_relationship
        and not exclude_none_relationship
        and not selected_genders
        and not excluded_genders
        and not include_none_gender
        and not exclude_none_gender
        and not active_body_filters
        and not active_aspect_filters
        and not active_dominant_sign_filters
        and not active_subordinate_sign_filters
        and not active_dominant_planet_filters
        and not active_subordinate_planet_filters
        and selected_isolated_dominant_body == "Any"
        and selected_isolated_dominant_sign == "Any"
        and selected_decan_sign == "Any"
        and selected_decan_number == "Any"
        and not active_body_dynamics_filter_rows
        and not active_dominant_mode_filters
        and not active_dominant_nakshatra_filters
        and not active_subordinate_nakshatra_filters
        and not active_dominant_element_filters
        and not year_first_encountered_earliest
        and not year_first_encountered_latest
        and year_first_encountered_blank_state == QuadStateSlider.MODE_EMPTY
        and not selected_chart_types
        and not excluded_chart_types
        and not selected_data_ratings
        and not excluded_data_ratings
        and not selected_generations
        and not excluded_generations
        and birthdate_earliest_month is None
        and birthdate_earliest_day is None
        and birthdate_earliest_year is None
        and birthdate_latest_month is None
        and birthdate_latest_day is None
        and birthdate_latest_year is None
        and window.species_filter_combo.currentData() == "Any"
        and (
            not hasattr(window, "subspecies_filter_combo")
            or window.subspecies_filter_combo.currentData() == "Any"
        )
        and (
            not hasattr(window, "dnd_class_filter_combo")
            or window.dnd_class_filter_combo.currentData() == "Any"
        )
        and not dnd_stat_ranges_active
        and not guessed_gender_filter
        and positive_sentiment_intensity_min is None
        and positive_sentiment_intensity_max is None
        and negative_sentiment_intensity_min is None
        and negative_sentiment_intensity_max is None
        and familiarity_min is None
        and familiarity_max is None
        and alignment_score_min is None
        and alignment_score_max is None
        and not include_blank_alignment
        and matched_expectations_min is None
        and matched_expectations_max is None
        and not (
            include_blank_matched_expectations
            and (
                matched_expectations_min is not None
                or matched_expectations_max is not None
            )
        )
        and not notes_comments_active
        and not notes_bio_active
        and not notes_quotes_active
        and not notes_rectification_active
        and not notes_source_active
        and not selected_human_design_channels
        and not selected_human_design_gates
        and selected_human_design_type == "Any"
        and selected_human_design_profile == "Any"
        and not selected_human_design_defined_centers
        and not database_search_text_is_active(window.search_text_input.text())
        and (
            window._search_location_country_input is None
            or not window._search_location_country_input.text().strip()
        )
        and (
            window._search_location_city_input is None
            or not window._search_location_city_input.text().strip()
        )
        and (
            window._search_location_state_input is None
            or not window._search_location_state_input.text().strip()
        )
        and (
            not hasattr(window, "search_tags_input")
            or not window.search_tags_input.text().strip()
        )
        and (
            not hasattr(window, "search_untagged_checkbox")
            or search_untagged_mode == QuadStateSlider.MODE_EMPTY
        )
        and not selected_search_tags
        and not optional_search_tags
        and not excluded_search_tags
        and not required_present_search_traits
        and not excluded_present_search_traits
        and not required_absent_search_traits
        and not excluded_absent_search_traits
        and not selected_enneagram_types
        and not excluded_enneagram_types
    )


def has_active_search_tag_filters(window) -> bool:
    """Return whether any Database View tag-search filter is active."""
    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    search_tag_text = (
        window.search_tags_input.text().strip()
        if hasattr(window, "search_tags_input")
        else ""
    )
    if search_tag_text:
        return True
    if any(
        checkbox.mode() in {QuadStateSlider.MODE_TRUE, QuadStateSlider.MODE_FALSE}
        for checkbox in getattr(window, "search_tag_filter_checkboxes", {}).values()
    ):
        return True
    search_untagged_checkbox = getattr(window, "search_untagged_checkbox", None)
    return (
        isinstance(search_untagged_checkbox, QuadStateSlider)
        and search_untagged_checkbox.mode() != QuadStateSlider.MODE_EMPTY
    )


def on_search_tags_changed(window, *_: object) -> None:
    """Refresh Database View typed-tag preview/selection state after tag text changes."""
    from ephemeraldaddy.gui.features.charts.tagging import parse_tag_text, render_tag_chip_preview

    tags = parse_tag_text(window.search_tags_input.text())
    render_tag_chip_preview(window.search_tags_preview_label, tags)
    sync_search_tags_list_selection(window, set(tags))
    window._on_filter_changed()


def apply_search_location_completer(window, line_edit, choices: list[str]) -> None:
    """Install a contains-matching completer on a Database View location field."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QCompleter, QLineEdit

    if not isinstance(line_edit, QLineEdit):
        return
    completer = QCompleter(choices, line_edit)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    line_edit.setCompleter(completer)


def update_search_location_completers(window) -> None:
    """Refresh Database View country/city/state completers from loaded chart rows."""
    countries: set[str] = set()
    cities: set[str] = set()
    states: set[str] = set()
    for chart_row in getattr(window, "_chart_rows", []):
        birth_place = str(chart_row[5] if len(chart_row) > 5 else "" or "").strip()
        if not birth_place:
            continue
        country, city, state = window._normalized_location_components(birth_place)
        if country:
            countries.add(country)
        if city:
            cities.add(city)
        if state:
            states.add(state)

    apply_search_location_completer(
        window,
        getattr(window, "_search_location_country_input", None),
        sorted(countries),
    )
    apply_search_location_completer(
        window,
        getattr(window, "_search_location_city_input", None),
        sorted(cities),
    )
    apply_search_location_completer(
        window,
        getattr(window, "_search_location_state_input", None),
        sorted(states),
    )


def tag_completer_revision_from_rows(window) -> tuple[object, ...]:
    """Return the loaded-row fields that affect chart/tag/location completers."""
    return tuple(
        (
            row[0] if len(row) > 0 else None,
            row[5] if len(row) > 5 else None,
            row[25] if len(row) > 25 else None,
            row[26] if len(row) > 26 else None,
        )
        for row in getattr(window, "_chart_rows", [])
    )


def tag_completer_tags_for_session(window) -> list[str]:
    """Return recognized tags plus tags already known in this app session."""
    from ephemeraldaddy.core.db import list_recognized_tags
    from ephemeraldaddy.gui.features.charts.tagging import normalize_tag_list

    tags_by_key: dict[str, str] = {
        tag.casefold(): tag
        for tag in list_recognized_tags()
    }
    for tag in getattr(window, "_known_chart_tags", []) or []:
        normalized = str(tag or "").strip()
        if normalized:
            tags_by_key.setdefault(normalized.casefold(), normalized)
    for tag in normalize_tag_list(getattr(window, "_chart_tags_current", []) or []):
        tags_by_key.setdefault(tag.casefold(), tag)
    return sorted(tags_by_key.values(), key=lambda value: value.casefold())


def update_tag_completers_if_needed(window, *, force: bool = False) -> None:
    """Refresh Database View tag/location completers only when relevant rows changed."""
    revision_token = tag_completer_revision_from_rows(window)
    if not force and revision_token == getattr(window, "_tag_completer_revision_token", None):
        return
    window._update_tag_completers()
    window._tag_completer_revision_token = revision_token


def update_tag_completers(
    window,
    *,
    refresh_location_completers: bool = True,
    refresh_tag_lists: bool = True,
) -> None:
    """Refresh Chart View, Database View, and Batch tag completers from session tags."""
    from PySide6.QtWidgets import QLineEdit

    from ephemeraldaddy.gui.features.charts.tagging import apply_tag_completer

    known_tags = tag_completer_tags_for_session(window)
    window._known_chart_tags = known_tags
    for line_edit in (
        getattr(window, "chart_tags_input", None),
        getattr(window, "search_tags_input", None),
        getattr(window, "batch_tags_input", None),
    ):
        if isinstance(line_edit, QLineEdit):
            apply_tag_completer(line_edit, known_tags)

    update_reminds_me_of_completer = getattr(window, "_update_reminds_me_of_completer", None)
    if callable(update_reminds_me_of_completer):
        update_reminds_me_of_completer()
    if refresh_location_completers:
        window._update_location_completers()
    if refresh_tag_lists:
        refresh_search_tags_list(window, known_tags)
        refresh_batch_tags_list = getattr(window, "_refresh_batch_tags_list", None)
        if callable(refresh_batch_tags_list):
            refresh_batch_tags_list(known_tags)


def sync_search_tags_list_selection(window, selected_tags: set[str]) -> None:
    """Update existing tag-filter widgets for typed tag text without rebuilding the tree.

    Rebuilding the full tag tree on every ``QLineEdit.textChanged`` event is
    expensive for large tag catalogs and can make typing appear to freeze the
    app.  When the tag tree is visible, the typed tag list only needs to
    mark matching existing per-tag sliders active, so keep the tree structure
    intact and update modes in-place.
    """
    search_tags_toggle = getattr(window, "search_tags_toggle", None)
    is_checked = getattr(search_tags_toggle, "isChecked", None)
    if callable(is_checked) and not is_checked():
        return

    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    selected_casefolded = {str(tag).casefold() for tag in selected_tags}
    for tag_name, checkbox in getattr(window, "search_tag_filter_checkboxes", {}).items():
        if str(tag_name).casefold() not in selected_casefolded:
            continue
        if checkbox.mode() != QuadStateSlider.MODE_TRUE:
            checkbox.setMode(QuadStateSlider.MODE_TRUE, emit_signal=False)


def refresh_tag_catalog_for_added_tags(window, tags: list[str]) -> None:
    """Merge newly added tags into Database View tag UI state for this session.

    This is intentionally event-driven: callers should use it after an explicit
    tag-add action, not while the Database View tag search field is being typed
    into.
    """
    from PySide6.QtWidgets import QLineEdit

    from ephemeraldaddy.gui.features.charts.tagging import apply_tag_completer, normalize_tag_list

    normalized_tags = normalize_tag_list(tags)
    if not normalized_tags:
        return
    known_by_key = {
        tag.casefold(): tag
        for tag in getattr(window, "_known_chart_tags", [])
    }
    changed = False
    for tag in normalized_tags:
        key = tag.casefold()
        if key in known_by_key:
            continue
        known_by_key[key] = tag
        changed = True
    if not changed:
        return

    sorted_tags = sorted(known_by_key.values(), key=lambda value: value.casefold())
    window._known_chart_tags = sorted_tags
    for line_edit in (
        getattr(window, "chart_tags_input", None),
        getattr(window, "search_tags_input", None),
        getattr(window, "batch_tags_input", None),
    ):
        if isinstance(line_edit, QLineEdit):
            apply_tag_completer(line_edit, sorted_tags)

    refresh_search_tags_list(window, sorted_tags)
    refresh_batch_tags_list = getattr(window, "_refresh_batch_tags_list", None)
    if callable(refresh_batch_tags_list):
        refresh_batch_tags_list(sorted_tags)

def on_search_tag_logic_changed(window, tag_name: str | None, mode: str, checked: bool) -> None:
    if not checked:
        return
    if tag_name:
        buttons = getattr(window, "search_tag_filter_logic_buttons", {}).get(tag_name)
        if buttons is not None:
            buttons["checked"] = mode
        window._on_filter_changed()


def on_search_tag_category_logic_changed(window, prefix: str, mode: str, checked: bool) -> None:
    if not checked:
        return
    prefix_dot = f"{str(prefix).casefold()}."
    for tag_name, buttons in getattr(window, "search_tag_filter_logic_buttons", {}).items():
        if str(tag_name).casefold().startswith(prefix_dot):
            button = buttons.get(mode)
            if button is not None:
                button.setChecked(True)
            buttons["checked"] = mode
    window._on_filter_changed()


def on_search_tag_category_mode_changed(window, prefix: str, mode: int) -> None:
    prefix_dot = f"{str(prefix).casefold()}."
    for tag_name, checkbox in getattr(window, "search_tag_filter_checkboxes", {}).items():
        if str(tag_name).casefold().startswith(prefix_dot):
            checkbox.setMode(mode, emit_signal=False)
    window._on_filter_changed()


def on_search_tag_mode_changed(window, _tag_name: str) -> None:
    window._on_filter_changed()


def collect_search_tag_filter_sets(window) -> tuple[set[str], set[str], set[str]]:
    """Return (required, optional, excluded) tag filters from the search UI."""
    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    required_tags: set[str] = set()
    optional_tags: set[str] = set()
    excluded_tags: set[str] = set()
    tag_logic_buttons = getattr(window, "search_tag_filter_logic_buttons", {})
    for name, checkbox in getattr(window, "search_tag_filter_checkboxes", {}).items():
        logic_mode = str(tag_logic_buttons.get(name, {}).get("checked", "and"))
        if checkbox.mode() == QuadStateSlider.MODE_TRUE:
            if logic_mode == "or":
                optional_tags.add(name)
            elif logic_mode == "not":
                excluded_tags.add(name)
            else:
                required_tags.add(name)
        elif checkbox.mode() == QuadStateSlider.MODE_FALSE:
            excluded_tags.add(name)
    return required_tags, optional_tags, excluded_tags


def collect_search_trait_filter_sets(window) -> tuple[set[str], set[str], set[str], set[str]]:
    """Return trait filters from the search UI.

    The result is ``(required_present, excluded_present, required_absent,
    excluded_absent)``. "Present" traits are chart traits above the database
    norm; "absent" traits are chart traits below the database norm.
    """

    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    def text_traits(attribute_name: str) -> set[str]:
        widget = getattr(window, attribute_name, None)
        text_getter = getattr(widget, "text", lambda: "")
        return {value.strip() for value in str(text_getter() or "").split(",") if value.strip()}

    required_present = text_traits("search_traits_present_input")
    required_absent = text_traits("search_traits_absent_input")

    # Backward-compatible fallback for panels built before the split widgets existed.
    legacy_input = getattr(window, "search_traits_input", None)
    if legacy_input is not None and not required_present and not required_absent:
        legacy_traits = text_traits("search_traits_input")
        direction_combo = getattr(window, "search_traits_direction_combo", None)
        direction = str(direction_combo.currentData() if direction_combo is not None else "above")
        if direction == "below":
            required_absent.update(legacy_traits)
        else:
            required_present.update(legacy_traits)

    excluded_present: set[str] = set()
    for name, checkbox in getattr(window, "search_trait_present_filter_checkboxes", {}).items():
        if checkbox.mode() == QuadStateSlider.MODE_TRUE:
            required_present.add(name)
        elif checkbox.mode() == QuadStateSlider.MODE_FALSE:
            excluded_present.add(name)

    excluded_absent: set[str] = set()
    for name, checkbox in getattr(window, "search_trait_absent_filter_checkboxes", {}).items():
        if checkbox.mode() == QuadStateSlider.MODE_TRUE:
            required_absent.add(name)
        elif checkbox.mode() == QuadStateSlider.MODE_FALSE:
            excluded_absent.add(name)

    # Backward-compatible fallback for the former single trait checkbox tree.
    for name, checkbox in getattr(window, "search_trait_filter_checkboxes", {}).items():
        direction_combo = getattr(window, "search_traits_direction_combo", None)
        direction = str(direction_combo.currentData() if direction_combo is not None else "above")
        if checkbox.mode() == QuadStateSlider.MODE_TRUE:
            (required_absent if direction == "below" else required_present).add(name)
        elif checkbox.mode() == QuadStateSlider.MODE_FALSE:
            (excluded_absent if direction == "below" else excluded_present).add(name)

    return required_present, excluded_present, required_absent, excluded_absent


def chart_matches_trait_filters(
    window,
    chart,
    *,
    required_present_traits: set[str],
    excluded_present_traits: set[str],
    required_absent_traits: set[str],
    excluded_absent_traits: set[str],
) -> bool:
    """Apply active derived-trait metadata filters to a chart."""
    if not (
        required_present_traits
        or excluded_present_traits
        or required_absent_traits
        or excluded_absent_traits
    ):
        return True
    from ephemeraldaddy.gui.features.charts.trait_predictions import trait_metadata_for_chart

    metadata = trait_metadata_for_chart(window, chart)
    present_traits = {str(name).casefold() for name in metadata.get("above", set())}
    absent_traits = {str(name).casefold() for name in metadata.get("below", set())}

    if any(trait.casefold() not in present_traits for trait in required_present_traits):
        return False
    if any(trait.casefold() in present_traits for trait in excluded_present_traits):
        return False
    if any(trait.casefold() not in absent_traits for trait in required_absent_traits):
        return False
    if any(trait.casefold() in absent_traits for trait in excluded_absent_traits):
        return False
    return True


def trait_autocomplete_names() -> list[str]:
    """Return active trait names for Database View trait search autocompleters."""
    from ephemeraldaddy.analysis.traits import list_traits

    names: list[str] = []
    seen: set[str] = set()
    for trait in list_traits(active_only=True):
        trait_name = str(trait.get("name", "")).strip()
        trait_key = trait_name.casefold()
        if not trait_name or trait_key in seen:
            continue
        seen.add(trait_key)
        names.append(trait_name)
    return sorted(names, key=str.casefold)


def install_trait_search_autocomplete(line_edit, traits: list[str]) -> None:
    """Install substring trait-name autocomplete on a trait search field."""
    from PySide6.QtCore import Qt, QStringListModel
    from PySide6.QtWidgets import QCompleter

    model = QStringListModel(traits, line_edit)
    completer = QCompleter(model, line_edit)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    completer.setMaxVisibleItems(12)
    line_edit.setCompleter(completer)
    line_edit._dbv_trait_completer_model = model


def refresh_trait_search_autocompletes(window) -> None:
    """Refresh trait autocomplete models without rebuilding the whole search UI."""
    traits = trait_autocomplete_names()
    for attr in (
        "search_traits_present_input",
        "search_traits_absent_input",
        "search_traits_input",
    ):
        line_edit = getattr(window, attr, None)
        if line_edit is None:
            continue
        model = getattr(line_edit, "_dbv_trait_completer_model", None)
        if model is not None and hasattr(model, "setStringList"):
            model.setStringList(traits)
        elif hasattr(line_edit, "setCompleter"):
            install_trait_search_autocomplete(line_edit, traits)


def apply_unique_trait_completion(line_edit) -> None:
    """Replace a partial trait search with its only matching saved trait, if unique."""
    text_getter = getattr(line_edit, "text", None)
    text_setter = getattr(line_edit, "setText", None)
    if not callable(text_getter) or not callable(text_setter):
        return
    query = str(text_getter() or "").strip()
    if not query or "," in query:
        return
    model = getattr(line_edit, "_dbv_trait_completer_model", None)
    string_list = getattr(model, "stringList", None)
    if not callable(string_list):
        return
    matches = [name for name in string_list() if query.casefold() in str(name).casefold()]
    if len(matches) == 1 and matches[0] != query:
        text_setter(matches[0])


def refresh_search_traits_list(window, kind: str = "present") -> None:
    """Refresh a Database View trait-filter tree for ``window``.

    ``kind`` is ``"present"`` for above-norm traits or ``"absent"`` for
    below-norm traits.
    """
    from PySide6.QtWidgets import QHBoxLayout, QTreeWidgetItem, QWidget

    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    kind = "absent" if kind == "absent" else "present"
    tree_attr = f"search_traits_{kind}_list_widget"
    checkboxes_attr = f"search_trait_{kind}_filter_checkboxes"
    tree = getattr(window, tree_attr, None)
    if tree is None and kind == "present":
        tree = getattr(window, "search_traits_list_widget", None)
        checkboxes_attr = "search_trait_filter_checkboxes"
    if tree is None:
        return
    signature_attr = f"_dbv_search_trait_{kind}_tree_signature"
    signature = _trait_tree_signature()
    if signature == getattr(window, signature_attr, None):
        return

    existing_modes = {
        trait_name: checkbox.mode()
        for trait_name, checkbox in getattr(window, checkboxes_attr, {}).items()
    }
    scroll_value = _tree_scroll_value(tree)
    tree.clear()
    setattr(window, checkboxes_attr, {})
    for trait_name in signature:
        item = QTreeWidgetItem()
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QuadStateSlider(trait_name)
        if trait_name in existing_modes:
            checkbox.setMode(existing_modes[trait_name])
        checkbox.modeChanged.connect(window._on_filter_changed)
        row_layout.addWidget(checkbox)
        row_layout.addStretch(1)
        tree.addTopLevelItem(item)
        tree.setItemWidget(item, 0, row)
        getattr(window, checkboxes_attr)[trait_name] = checkbox

    setattr(window, signature_attr, signature)
    _restore_tree_scroll_value(tree, scroll_value)


if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def build_dbv_search_bar_row(window) -> "QWidget":
    """Build the always-visible Database View search bars for the middle panel."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider

    row_widget = QWidget()
    row_layout = QHBoxLayout()
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)
    row_widget.setLayout(row_layout)

    def _apply_search_input_style(
        line_edit,
        *,
        background_color: str,
        placeholder_color: str,
        text_color: str | None = None,
    ) -> None:
        text_color_rule = f" color: {text_color};" if text_color else ""
        line_edit.setStyleSheet(
            f"QLineEdit {{ background-color: {background_color};{text_color_rule} }}"
            f"QLineEdit::placeholder {{ color: {placeholder_color}; }}"
        )

    database_cell = QWidget()
    database_row = QHBoxLayout()
    database_row.setContentsMargins(0, 0, 0, 0)
    database_row.setSpacing(4)
    database_cell.setLayout(database_row)
    window.search_text_input = QLineEdit()
    window.search_text_input.setPlaceholderText("Search names or birthplaces")
    window.search_text_input.textChanged.connect(window._on_filter_changed)
    window.search_text_input.returnPressed.connect(window._on_filter_changed)
    window.search_text_input.installEventFilter(window)
    database_row.addWidget(window.search_text_input, 1)
    database_search_button = QPushButton("🔍")
    database_search_button.clicked.connect(window._on_filter_changed)
    database_row.addWidget(database_search_button)
    row_layout.addWidget(database_cell, 2, Qt.AlignTop)

    astrotheme_cell = QWidget()
    astrotheme_row = QHBoxLayout()
    astrotheme_row.setContentsMargins(0, 0, 0, 0)
    astrotheme_row.setSpacing(4)
    astrotheme_cell.setLayout(astrotheme_row)
    window.astrotheme_search_input = QLineEdit()
    window.astrotheme_search_input.setPlaceholderText("Search Astrotheme.com/Wikipedia")
    _apply_search_input_style(
        window.astrotheme_search_input,
        background_color="#5900b3",
        placeholder_color="#8000ff",
    )
    window.astrotheme_search_input.returnPressed.connect(
        window._on_import_astrotheme_from_search_panel
    )
    window.astrotheme_search_input.installEventFilter(window)
    astrotheme_row.addWidget(window.astrotheme_search_input, 1)
    astrotheme_import_button = QPushButton("⬇️")
    astrotheme_import_button.clicked.connect(
        window._on_import_astrotheme_from_search_panel
    )
    astrotheme_row.addWidget(astrotheme_import_button)
    row_layout.addWidget(astrotheme_cell, 2, Qt.AlignTop)

    tag_cell = QWidget()
    tag_layout = QVBoxLayout()
    tag_layout.setContentsMargins(0, 0, 0, 0)
    tag_layout.setSpacing(2)
    tag_cell.setLayout(tag_layout)
    tag_search_row = QHBoxLayout()
    tag_search_row.setContentsMargins(0, 0, 0, 0)
    tag_search_row.setSpacing(4)
    window.search_tags_input = QLineEdit()
    window.search_tags_input.setPlaceholderText("Search by tag")
    _apply_search_input_style(
        window.search_tags_input,
        background_color="#e6b800",
        placeholder_color="#b38f00",
        text_color="#1f1f1f",
    )
    window.search_tags_input.textChanged.connect(window._on_search_tags_changed)
    window.search_tags_input.returnPressed.connect(window._on_filter_changed)
    tag_search_row.addWidget(window.search_tags_input, 1)
    tag_search_button = QPushButton("🔍")
    tag_search_button.clicked.connect(window._on_filter_changed)
    tag_search_row.addWidget(tag_search_button)
    tag_layout.addLayout(tag_search_row)
    window.search_tags_preview_label = QLabel()
    window.search_tags_preview_label.setWordWrap(True)
    window.search_tags_preview_label.setTextFormat(Qt.RichText)
    tag_layout.addWidget(window.search_tags_preview_label)
    row_layout.addWidget(tag_cell, 2, Qt.AlignTop)

    window.search_untagged_checkbox = QuadStateSlider("untagged")
    window.search_untagged_checkbox.modeChanged.connect(window._on_filter_changed)

    return row_widget


def build_dbv_search_panel(window) -> "QWidget":
    """Build the Database View search panel while mutating ``window`` state."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIntValidator
    from PySide6.QtWidgets import (
        QButtonGroup, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QRadioButton,
        QSizePolicy, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
    )

    from ephemeraldaddy.gui.emoji_render import apply_emoji_png_to_button, apply_emoji_pngs_to_label
    from ephemeraldaddy.gui.features.charts.presentation import abbreviate_body_label, abbreviate_nakshatra_label
    from ephemeraldaddy.gui.style import (
        COLLAPSIBLE_NESTED_SECTION_CONTENT_STYLE, COLLAPSIBLE_SECTION_CONTENT_STYLE,
        DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE, DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS,
        DATABASE_ANALYTICS_SUBHEADER_STYLE, DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        DATABASE_VIEW_PANEL_HEADER_STYLE, DEFAULT_DROPDOWN_STYLE, apply_shared_dropdown_style,
        configure_collapsible_header_toggle, configure_static_collapsible_header_label,
        create_divider,
    )
    from ephemeraldaddy.gui.ui_helpers import EmojiTiledPanel
    from ephemeraldaddy.gui.widgets.quad_state import QuadStateSlider
    from ephemeraldaddy.gui.widgets.search_controls import (
        ASPECT_DEFS, DND_CLASSES, FAMILY_SUBTYPES, GENERATION_FILTER_OPTIONS,
        HD_CHANNELS, NAKSHATRA_RANGES, RODDEN_RATING, SEARCH_GENDER_GUESSED_OPTIONS,
        SEARCH_GENDER_OPTIONS, SEARCH_RELATIONSHIP_TYPE_OPTIONS, SEARCH_SENTIMENT_OPTIONS,
        SOURCE_OPTIONS, SPECIES_FAMILIES, ZODIAC_NAMES,
    )

    # Search panel (right sidebar).
    panel = EmojiTiledPanel("🔎", font_size=100, opacity=0.12) #Search panel background
    panel.setMinimumWidth(260)
    layout = QVBoxLayout()
    panel.setLayout(layout)

    def apply_default_dropdown_style(dropdown: QComboBox) -> None:
        apply_shared_dropdown_style(dropdown)

    def center_dropdown_items(dropdown: QComboBox) -> None:
        dropdown.setEditable(False)
        for item_index in range(dropdown.count()):
            dropdown.setItemData(item_index, Qt.AlignCenter, Qt.TextAlignmentRole)
        dropdown.setStyleSheet(f"{DEFAULT_DROPDOWN_STYLE} QComboBox {{ text-align: center; }}")

    def narrow_dropdown_for_not_option(dropdown: QComboBox) -> None:
        target_width = max(120, dropdown.sizeHint().width() - 100)
        dropdown.setFixedWidth(target_width)

    def set_dropdown_width_chars(dropdown: QComboBox, chars: int) -> None:
        metrics = dropdown.fontMetrics()
        # Include room for content, lean item padding, and the dropdown arrow so
        # compact fixed-width combos still show their complete values instead of
        # wasting space on ellipses.
        width_px = (metrics.horizontalAdvance("0") * int(chars)) + 46
        dropdown.setMinimumWidth(width_px)
        dropdown.setMaximumWidth(width_px)
        dropdown.setFixedWidth(width_px)
        dropdown.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def compact_body_label(label: str) -> str:
        return abbreviate_body_label(str(label))

    def compact_nakshatra_label(label: str) -> str:
        return abbreviate_nakshatra_label(str(label))

    search_title = QLabel("Search Filters")
    search_title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
    apply_emoji_pngs_to_label(search_title)
    layout.addWidget(search_title)

    window.search_tags_toggle = QToolButton()
    configure_collapsible_header_toggle(
        window.search_tags_toggle,
        title="Advanced Tag Search",
        expanded=False,
        style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    )
    layout.addWidget(window.search_tags_toggle)

    window.search_tags_list_widget = QTreeWidget()
    window.search_tags_list_widget.setHeaderHidden(True)
    window.search_tags_list_widget.setSelectionMode(QListWidget.NoSelection)
    window.search_tags_list_widget.setIndentation(12)
    window.search_tags_list_widget.setMaximumHeight(220)
    window.search_tags_list_widget.setVisible(False)
    window.search_tag_filter_logic_buttons = {}
    window.search_tag_category_checkboxes = {}
    window.search_tag_category_logic_buttons = {}
    window._dbv_tag_tree_item_class = QTreeWidgetItem
    window.search_tags_toggle.toggled.connect(window.search_tags_list_widget.setVisible)
    window.search_tags_toggle.toggled.connect(
        lambda expanded: window._refresh_search_tags_list(
            getattr(window, "_known_chart_tags", [])
        ) if expanded else None
    )
    layout.addWidget(window.search_tags_list_widget)

    layout.addWidget(create_divider())

    def build_trait_search_layout(kind: str, title: str, placeholder: str) -> QVBoxLayout:
        trait_layout = QVBoxLayout()
        trait_layout.setContentsMargins(0, 0, 0, 0)
        trait_layout.setSpacing(4)

        input_attr = f"search_traits_{kind}_input"
        toggle_attr = f"search_traits_{kind}_toggle"
        list_attr = f"search_traits_{kind}_list_widget"
        checkboxes_attr = f"search_trait_{kind}_filter_checkboxes"

        trait_input = QLineEdit()
        trait_input.setPlaceholderText(placeholder)
        install_trait_search_autocomplete(trait_input, trait_autocomplete_names())
        trait_input.returnPressed.connect(lambda line_edit=trait_input: apply_unique_trait_completion(line_edit))
        trait_input.returnPressed.connect(window._on_filter_changed)
        completer = trait_input.completer()
        if completer is not None:
            completer.activated.connect(window._on_filter_changed)
        setattr(window, input_attr, trait_input)
        trait_layout.addWidget(trait_input)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        setattr(window, toggle_attr, toggle)
        trait_layout.addWidget(toggle)

        list_widget = QTreeWidget()
        list_widget.setHeaderHidden(True)
        list_widget.setSelectionMode(QListWidget.NoSelection)
        list_widget.setIndentation(12)
        list_widget.setMaximumHeight(220)
        list_widget.setVisible(False)
        setattr(window, list_attr, list_widget)
        setattr(window, checkboxes_attr, {})
        toggle.toggled.connect(list_widget.setVisible)
        toggle.toggled.connect(
            lambda expanded, trait_kind=kind: refresh_search_traits_list(window, trait_kind) if expanded else None
        )
        toggle.toggled.connect(lambda expanded: refresh_trait_search_autocompletes(window) if expanded else None)
        trait_layout.addWidget(list_widget)
        return trait_layout

    traits_present_search_row = build_trait_search_layout(
        "present",
        "Traits Present (above DB norm)",
        "Search by present trait",
    )
    traits_absent_search_row = build_trait_search_layout(
        "absent",
        "Traits Absent (below DB norm)",
        "Search by absent trait",
    )
    window.search_trait_filter_checkboxes = {}

    settings = getattr(window, "_settings", None)

    incomplete_birthdate_row = QHBoxLayout()
    window.incomplete_birthdate_checkbox = QuadStateSlider("placeholder charts")
    window.incomplete_birthdate_checkbox.setToolTip(
        "Show or hide all 'placeholder charts' (aka saved charts with insufficient birth data for astro calculations)"
    )
    if settings is not None and bool(
        settings.value(
            SETTINGS_KEY_HIDE_PLACEHOLDER_CHARTS_FILTER,
            0,
            type=int,
        )
    ):
        window.incomplete_birthdate_checkbox.setMode(QuadStateSlider.MODE_FALSE)
    window.incomplete_birthdate_checkbox.modeChanged.connect(window._on_incomplete_birthdate_filter_changed)
    incomplete_birthdate_row.addWidget(window.incomplete_birthdate_checkbox)
    incomplete_birthdate_row.addStretch(1)

    window.hidden_charts_filter_row = QWidget()
    hidden_charts_filter_layout = QHBoxLayout()
    hidden_charts_filter_layout.setContentsMargins(0, 0, 0, 0)
    window.hidden_charts_filter_row.setLayout(hidden_charts_filter_layout)
    window.hidden_charts_checkbox = QuadStateSlider("hidden charts")
    if settings is not None:
        hidden_charts_mode = settings.value(
            SETTINGS_KEY_HIDDEN_CHARTS_FILTER_MODE,
            QuadStateSlider.MODE_EMPTY,
            type=int,
        )
        if hidden_charts_mode in {
            QuadStateSlider.MODE_EMPTY,
            QuadStateSlider.MODE_TRUE,
            QuadStateSlider.MODE_FALSE,
        }:
            window.hidden_charts_checkbox.setMode(int(hidden_charts_mode))
    window.hidden_charts_checkbox.modeChanged.connect(window._on_filter_changed)
    hidden_charts_filter_layout.addWidget(window.hidden_charts_checkbox)
    hidden_charts_filter_layout.addStretch(1)
    window.hidden_charts_filter_row.setVisible(
        bool(getattr(window, "_show_hidden_charts", False))
    )

    header_layout = QHBoxLayout()
    header_layout.addStretch(1)
    #I removed this button, since there's a "Clear Filters" button on the bottom right now.
    #reset_button = QPushButton("Reset")
    #reset_button.clicked.connect(window._reset_filters)
    #header_layout.addWidget(reset_button)
    layout.addLayout(header_layout)

    def add_collapsible_section(
        title: str,
        *,
        nested: bool = False,
        expanded: bool = False,
        style_sheet: str = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    ) -> tuple[QWidget, QVBoxLayout]:
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section.setLayout(section_layout)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=style_sheet,
        )

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(8, 6, 8, 6)
        content.setLayout(content_layout)
        content_style = (
            COLLAPSIBLE_NESTED_SECTION_CONTENT_STYLE
            if nested
            else COLLAPSIBLE_SECTION_CONTENT_STYLE
        )
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            content_style = f"{content_style} {DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE}"
        content.setStyleSheet(content_style)
        content.setVisible(expanded)

        def set_toggle_expanded_state(checked: bool) -> None:
            toggle.setArrowType(Qt.NoArrow)

        def toggle_content(checked: bool) -> None:
            content.setVisible(checked)
            set_toggle_expanded_state(checked)
            content.adjustSize()
            section.adjustSize()
            panel.adjustSize()
            panel.updateGeometry()

        apply_emoji_png_to_button(toggle, icon_px=16)
        set_toggle_expanded_state(False)

        toggle.toggled.connect(toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        return section, content_layout

    # Search: Chart Type remains directly below the top search controls.
    chart_type_header_style = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE.replace(
        "color: #ffffff;",
        "color: #b56cff;",
        1,
    )
    chart_type_section, chart_type_group_layout = add_collapsible_section(
        "Chart Type",
        expanded=False,
        style_sheet=chart_type_header_style,
    )

    chart_type_layout = QGridLayout()
    chart_type_layout.setContentsMargins(0, 0, 0, 0)
    window.chart_type_filter_checkboxes = {}
    chart_type_rows = (len(SOURCE_OPTIONS) + 1) // 2
    for idx, (source_label, source_value) in enumerate(SOURCE_OPTIONS):
        checkbox = QuadStateSlider(source_label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.chart_type_filter_checkboxes[source_value] = checkbox
        row = idx % chart_type_rows
        col = idx // chart_type_rows
        chart_type_layout.addWidget(checkbox, row, col)
    chart_type_group_layout.addLayout(chart_type_layout)
    chart_type_group_layout.addLayout(incomplete_birthdate_row)
    chart_type_group_layout.addWidget(window.hidden_charts_filter_row)

    chart_type_button_row = QHBoxLayout()
    chart_type_button_row.addStretch(1)
    clear_chart_type_button = QPushButton("Clear Filters")
    clear_chart_type_button.clicked.connect(window._clear_chart_type_filters)
    chart_type_button_row.addWidget(clear_chart_type_button)
    chart_type_group_layout.addLayout(chart_type_button_row)

    layout.addWidget(chart_type_section)

    astro_category_section, astro_category_layout = add_collapsible_section("🪐Astro", nested=True)
    layout.addWidget(astro_category_section)
    human_design_category_section, human_design_category_layout = add_collapsible_section("🪷Human Design", nested=True)
    layout.addWidget(human_design_category_section)
    interactions_category_section, interactions_category_layout = add_collapsible_section("💭Observations", nested=True)
    layout.addWidget(interactions_category_section)
    predictions_category_section, predictions_category_layout = add_collapsible_section("🔮Predictions", nested=True)
    layout.addWidget(predictions_category_section)
    demographics_category_section, demographics_category_layout = add_collapsible_section("👥Demographics", nested=True)
    layout.addWidget(demographics_category_section)

    traits_present_section, traits_present_group_layout = add_collapsible_section("Traits Present", nested=True)
    traits_present_group_layout.addLayout(traits_present_search_row)
    predictions_category_layout.addWidget(traits_present_section)

    traits_absent_section, traits_absent_group_layout = add_collapsible_section("Traits Absent", nested=True)
    traits_absent_group_layout.addLayout(traits_absent_search_row)
    predictions_category_layout.addWidget(traits_absent_section)

    enneagram_section, enneagram_group_layout = add_collapsible_section("Enneagram", nested=True)
    enneagram_layout = QGridLayout()
    enneagram_layout.setContentsMargins(0, 0, 0, 0)
    window.enneagram_type_filter_checkboxes = {}
    for idx, enneagram_type in enumerate(range(1, 10)):
        checkbox = QuadStateSlider(f"Type {enneagram_type}")
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.enneagram_type_filter_checkboxes[enneagram_type] = checkbox
        enneagram_layout.addWidget(checkbox, idx // 3, idx % 3)
    enneagram_group_layout.addLayout(enneagram_layout)
    predictions_category_layout.addWidget(enneagram_section)

    #Search: data completeness & accuracy
    birth_info_status_section, birth_info_status_layout = add_collapsible_section(
        "🐣Data Quality", #data icon contenders: 🧮 🗄️ 🪪 𖦏 🔢 🧩 ℹ️
    )

    birth_status_mode_row = QHBoxLayout()
    birth_status_mode_row.addWidget(QLabel("🐣Time:"))
    birth_status_mode_row.addStretch(1)
    window.birth_status_filter_and = QRadioButton("AND")
    window.birth_status_filter_or = QRadioButton("OR")
    window.birth_status_filter_group = QButtonGroup(window)
    window.birth_status_filter_group.setExclusive(True)
    window.birth_status_filter_group.addButton(window.birth_status_filter_and)
    window.birth_status_filter_group.addButton(window.birth_status_filter_or)
    window.birth_status_filter_and.setChecked(True)
    window.birth_status_filter_and.toggled.connect(window._on_filter_changed)
    window.birth_status_filter_or.toggled.connect(window._on_filter_changed)
    birth_status_mode_row.addWidget(window.birth_status_filter_and)
    birth_status_mode_row.addWidget(window.birth_status_filter_or)
    birth_info_status_layout.addLayout(birth_status_mode_row)

    birth_filters_row = QHBoxLayout()
    window.birthtime_unknown_checkbox = QuadStateSlider("unknown")
    window.birthtime_unknown_checkbox.modeChanged.connect(window._on_filter_changed)
    window.retconned_checkbox = QuadStateSlider("rectified")
    window.retconned_checkbox.modeChanged.connect(window._on_filter_changed)
    birth_filters_row.addWidget(window.birthtime_unknown_checkbox)
    birth_filters_row.addWidget(window.retconned_checkbox)
    birth_filters_row.addStretch(1)
    birth_info_status_layout.addLayout(birth_filters_row)

    birth_info_status_layout.addWidget(create_divider())

    rodden_header = QLabel("Rodden Rating")
    rodden_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    birth_info_status_layout.addWidget(rodden_header)

    rodden_layout = QGridLayout()
    rodden_layout.setContentsMargins(0, 0, 0, 0)
    rodden_layout.setHorizontalSpacing(10)
    rodden_layout.setVerticalSpacing(4)
    window.data_rating_filter_checkboxes = {}
    rodden_rows = (len(RODDEN_RATING) + 1) // 2
    for idx, rating in enumerate(RODDEN_RATING):
        grade = str(rating.get("grade", "")).strip()
        if not grade:
            continue
        checkbox = QuadStateSlider(grade)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.data_rating_filter_checkboxes[grade] = checkbox
        row = idx % rodden_rows
        col = idx // rodden_rows
        rodden_layout.addWidget(checkbox, row, col)
    birth_info_status_layout.addLayout(rodden_layout)
    astro_category_layout.addWidget(birth_info_status_section)

    #Search: Astrological Positions section
    bodies_section, bodies_group_layout = add_collapsible_section("🪐Positions") #astrological positions

    bodies_layout = QFormLayout()
    bodies_layout.setLabelAlignment(Qt.AlignLeft)
    bodies_group_layout.addLayout(bodies_layout)

    for _ in range(10):
        filter_row = QWidget()
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_row.setLayout(filter_layout)

        body_combo = QComboBox()
        apply_default_dropdown_style(body_combo)
        body_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(body_combo, 10)
        for body_label, body_key in window._searchable_bodies():
            body_combo.addItem(compact_body_label(body_label), body_key)
        body_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        sign_combo = QComboBox()
        apply_default_dropdown_style(sign_combo)
        sign_combo.addItem("Any 🌟", "Any")
        set_dropdown_width_chars(sign_combo, 6)
        for sign in ZODIAC_NAMES:
            sign_combo.addItem(sign, sign)
        sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        house_combo = QComboBox()
        apply_default_dropdown_style(house_combo)
        house_combo.addItem("Any 🏠", "Any")
        set_dropdown_width_chars(house_combo, 6)
        for house_num in range(1, 13):
            house_combo.addItem(str(house_num), str(house_num))
        house_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_layout.addWidget(body_combo)
        filter_layout.addWidget(sign_combo, 1)
        filter_layout.addWidget(house_combo)
        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(filter_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)
        filter_layout.addWidget(filter_and)
        filter_layout.addWidget(filter_or)
        filter_layout.addWidget(filter_not)

        window._search_body_filters.append({
            "body": body_combo,
            "sign": sign_combo,
            "house": house_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        bodies_layout.addRow(filter_row)

    astro_category_layout.addWidget(bodies_section)

    #Search: Aspects section
    aspect_section, aspect_group_layout = add_collapsible_section("🪐Aspect") #astrological aspect

    aspect_layout = QFormLayout()
    aspect_layout.setLabelAlignment(Qt.AlignLeft)
    aspect_group_layout.addLayout(aspect_layout)

    aspect_options = [("Any 📐", "Any")]
    for aspect_name in sorted(ASPECT_DEFS):
        aspect_options.append((aspect_name.replace("_", " ").title(), aspect_name))

    searchable_planets = list(window._searchable_bodies())

    for _ in range(3):
        aspect_row = QWidget()
        aspect_row_layout = QHBoxLayout()
        aspect_row_layout.setContentsMargins(0, 0, 0, 0)
        aspect_row.setLayout(aspect_row_layout)

        planet_1_combo = QComboBox()
        apply_default_dropdown_style(planet_1_combo)
        planet_1_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(planet_1_combo, 10)
        for label, key in searchable_planets:
            planet_1_combo.addItem(compact_body_label(label), key)
        planet_1_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        aspect_combo = QComboBox()
        apply_default_dropdown_style(aspect_combo)
        for label, key in aspect_options:
            aspect_combo.addItem(label, key)
        set_dropdown_width_chars(aspect_combo, 17)
        aspect_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        planet_2_combo = QComboBox()
        apply_default_dropdown_style(planet_2_combo)
        planet_2_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(planet_2_combo, 10)
        for label, key in searchable_planets:
            planet_2_combo.addItem(compact_body_label(label), key)
        planet_2_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_group = QButtonGroup(aspect_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        aspect_row_layout.addWidget(planet_1_combo, 1)
        aspect_row_layout.addWidget(aspect_combo, 1)
        aspect_row_layout.addWidget(planet_2_combo, 1)
        aspect_row_layout.addWidget(filter_and)
        aspect_row_layout.addWidget(filter_or)

        window._aspect_filters.append(
            {
                "planet_1": planet_1_combo,
                "aspect": aspect_combo,
                "planet_2": planet_2_combo,
                "and": filter_and,
                "or": filter_or,
            }
        )
        aspect_layout.addRow(aspect_row)

    astro_category_layout.addWidget(aspect_section)

    #Search: Sign section
    dominant_section, dominant_group_layout = add_collapsible_section(
        "🪐Sign", #dominant/subordinate astrological sign
    )

    dominant_layout = QFormLayout()
    dominant_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_group_layout.addLayout(dominant_layout)

    def add_sign_filter_rows(target_filters: list[dict[str, object]]) -> None:
        for _ in range(3):
            sign_row = QWidget()
            sign_row_layout = QHBoxLayout()
            sign_row_layout.setContentsMargins(0, 0, 0, 0)
            sign_row.setLayout(sign_row_layout)

            sign_combo = QComboBox()
            apply_default_dropdown_style(sign_combo)
            sign_combo.addItem("Any 🌟", "Any")
            set_dropdown_width_chars(sign_combo, 6)
            for sign in ZODIAC_NAMES:
                sign_combo.addItem(sign)
            narrow_dropdown_for_not_option(sign_combo)
            sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

            filter_and = QRadioButton("&&")
            filter_or = QRadioButton("OR")
            filter_not = QRadioButton("🚫")
            filter_group = QButtonGroup(sign_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_group.addButton(filter_not)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(window._on_filter_changed)

            sign_row_layout.addWidget(sign_combo)
            sign_row_layout.addWidget(filter_and)
            sign_row_layout.addWidget(filter_or)
            sign_row_layout.addWidget(filter_not)
            sign_row_layout.addStretch(1)

            target_filters.append({
                "sign": sign_combo,
                "and": filter_and,
                "or": filter_or,
                "not": filter_not,
            })
            dominant_layout.addRow(sign_row)

    dominant_sign_header = QLabel("Dominant Sign")
    dominant_sign_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_layout.addRow(dominant_sign_header)
    add_sign_filter_rows(window._dominant_sign_filters)

    subordinate_sign_header = QLabel("Subordinate Sign")
    subordinate_sign_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_layout.addRow(subordinate_sign_header)
    add_sign_filter_rows(window._subordinate_sign_filters)

    astro_category_layout.addWidget(dominant_section)

    #Search: Body section
    dominant_planet_section, dominant_planet_group_layout = add_collapsible_section(
        "🪐Body", #dominant/subordinate astrological bodies
    )

    dominant_planet_layout = QFormLayout()
    dominant_planet_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_planet_group_layout.addLayout(dominant_planet_layout)

    def add_body_filter_rows(target_filters: list[dict[str, object]]) -> None:
        for _ in range(3):
            body_row = QWidget()
            body_row_layout = QHBoxLayout()
            body_row_layout.setContentsMargins(0, 0, 0, 0)
            body_row.setLayout(body_row_layout)

            planet_combo = QComboBox()
            apply_default_dropdown_style(planet_combo)
            planet_combo.addItem("Any 🪐", "Any")
            for planet_label, planet_key in window._searchable_bodies():
                if planet_key in {"AS", "IC", "DS", "MC"}:
                    continue
                planet_combo.addItem(compact_body_label(planet_label), planet_key)
            narrow_dropdown_for_not_option(planet_combo)
            planet_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

            filter_and = QRadioButton("&&")
            filter_or = QRadioButton("OR")
            filter_not = QRadioButton("🚫")
            filter_group = QButtonGroup(body_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_group.addButton(filter_not)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(window._on_filter_changed)

            body_row_layout.addWidget(planet_combo)
            body_row_layout.addWidget(filter_and)
            body_row_layout.addWidget(filter_or)
            body_row_layout.addWidget(filter_not)
            body_row_layout.addStretch(1)

            target_filters.append({
                "planet": planet_combo,
                "and": filter_and,
                "or": filter_or,
                "not": filter_not,
            })
            dominant_planet_layout.addRow(body_row)

    dominant_bodies_header = QLabel("Dominant Bodies")
    dominant_bodies_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_planet_layout.addRow(dominant_bodies_header)
    add_body_filter_rows(window._dominant_planet_filters)

    subordinate_bodies_header = QLabel("Subordinate Bodies")
    subordinate_bodies_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_planet_layout.addRow(subordinate_bodies_header)
    add_body_filter_rows(window._subordinate_planet_filters)

    astro_category_layout.addWidget(dominant_planet_section)

    #Search: Nakshatra section
    dominant_nakshatra_section, dominant_nakshatra_group_layout = add_collapsible_section(
        "🪐Nakshatra",
    )

    dominant_nakshatra_layout = QFormLayout()
    dominant_nakshatra_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_nakshatra_group_layout.addLayout(dominant_nakshatra_layout)

    def add_nakshatra_filter_rows(target_filters: list[dict[str, object]]) -> None:
        for _ in range(3):
            nakshatra_row = QWidget()
            nakshatra_row_layout = QHBoxLayout()
            nakshatra_row_layout.setContentsMargins(0, 0, 0, 0)
            nakshatra_row.setLayout(nakshatra_row_layout)

            nakshatra_combo = QComboBox()
            apply_default_dropdown_style(nakshatra_combo)
            nakshatra_combo.addItem("Any", "Any")
            for nakshatra_name, *_ in NAKSHATRA_RANGES:
                nakshatra_combo.addItem(compact_nakshatra_label(str(nakshatra_name)), str(nakshatra_name))
            narrow_dropdown_for_not_option(nakshatra_combo)
            nakshatra_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

            filter_and = QRadioButton("&&")
            filter_or = QRadioButton("OR")
            filter_not = QRadioButton("🚫")
            filter_group = QButtonGroup(nakshatra_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_group.addButton(filter_not)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(window._on_filter_changed)

            nakshatra_row_layout.addWidget(nakshatra_combo)
            nakshatra_row_layout.addWidget(filter_and)
            nakshatra_row_layout.addWidget(filter_or)
            nakshatra_row_layout.addWidget(filter_not)
            nakshatra_row_layout.addStretch(1)

            target_filters.append({
                "nakshatra": nakshatra_combo,
                "and": filter_and,
                "or": filter_or,
                "not": filter_not,
            })
            dominant_nakshatra_layout.addRow(nakshatra_row)

    dominant_nakshatras_header = QLabel("Dominant Nakshatras")
    dominant_nakshatras_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_nakshatra_layout.addRow(dominant_nakshatras_header)
    add_nakshatra_filter_rows(window._dominant_nakshatra_filters)

    subordinate_nakshatras_header = QLabel("Subordinate Nakshatras")
    subordinate_nakshatras_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_nakshatra_layout.addRow(subordinate_nakshatras_header)
    add_nakshatra_filter_rows(window._subordinate_nakshatra_filters)

    astro_category_layout.addWidget(dominant_nakshatra_section)

    #Search: Dominant Elements section
    dominant_element_section, dominant_element_group_layout = add_collapsible_section(
        "🪐Elements", #dominatn astrological elements
    )
    dominant_element_layout = QFormLayout()
    dominant_element_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_element_group_layout.addLayout(dominant_element_layout)
    dominant_element_header = QLabel("Dominant Element")
    dominant_element_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_element_layout.addRow(dominant_element_header)

    for _ in range(3):
        dominant_element_row = QWidget()
        dominant_element_row_layout = QHBoxLayout()
        dominant_element_row_layout.setContentsMargins(0, 0, 0, 0)
        dominant_element_row.setLayout(dominant_element_row_layout)

        element_combo = QComboBox()
        apply_default_dropdown_style(element_combo)
        element_combo.addItem("🔥🌬️💧🌱", "Any")
        for element in ("Fire", "Earth", "Air", "Water"):
            element_combo.addItem(element, element)
        narrow_dropdown_for_not_option(element_combo)
        element_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(dominant_element_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        #dominant_element_row_layout.addWidget(QLabel("")) #🧪
        dominant_element_row_layout.addWidget(element_combo)
        dominant_element_row_layout.addWidget(filter_and)
        dominant_element_row_layout.addWidget(filter_or)
        dominant_element_row_layout.addWidget(filter_not)
        dominant_element_row_layout.addStretch(1)

        window._dominant_element_filters.append({
            "element": element_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        dominant_element_layout.addRow(dominant_element_row)

    astro_category_layout.addWidget(dominant_element_section)

    #Search: Dominant Mode section
    dominant_mode_section, dominant_mode_group_layout = add_collapsible_section(
        "🪐Modes", #dominant astrological mode
    )

    dominant_mode_layout = QFormLayout()
    dominant_mode_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_mode_group_layout.addLayout(dominant_mode_layout)
    dominant_mode_header = QLabel("Dominant Mode")
    dominant_mode_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dominant_mode_layout.addRow(dominant_mode_header)

    dominant_mode_row = QWidget()
    dominant_mode_row_layout = QHBoxLayout()
    dominant_mode_row_layout.setContentsMargins(0, 0, 0, 0)
    dominant_mode_row.setLayout(dominant_mode_row_layout)

    mode_combo = QComboBox()
    apply_default_dropdown_style(mode_combo)
    mode_combo.addItem("Any", "Any")
    mode_combo.addItem("Cardinal", "cardinal")
    mode_combo.addItem("Mutable", "mutable")
    mode_combo.addItem("Fixed", "fixed")
    narrow_dropdown_for_not_option(mode_combo)
    mode_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    filter_and = QRadioButton("&&")
    filter_or = QRadioButton("OR")
    filter_not = QRadioButton("🚫")
    filter_group = QButtonGroup(dominant_mode_row)
    filter_group.setExclusive(True)
    filter_group.addButton(filter_and)
    filter_group.addButton(filter_or)
    filter_group.addButton(filter_not)
    filter_and.setChecked(True)
    filter_group.buttonClicked.connect(window._on_filter_changed)

    dominant_mode_row_layout.addWidget(mode_combo)
    dominant_mode_row_layout.addWidget(filter_and)
    dominant_mode_row_layout.addWidget(filter_or)
    dominant_mode_row_layout.addWidget(filter_not)
    dominant_mode_row_layout.addStretch(1)

    window._dominant_mode_filters.append({
        "mode": mode_combo,
        "and": filter_and,
        "or": filter_or,
        "not": filter_not,
    })
    dominant_mode_layout.addRow(dominant_mode_row)

    astro_category_layout.addWidget(dominant_mode_section)

    #Search: Body Dynamics section
    body_dynamics_section, body_dynamics_group_layout = add_collapsible_section(
        "🪐Body Dynamics",
    )

    body_dynamics_layout = QFormLayout()
    body_dynamics_layout.setLabelAlignment(Qt.AlignLeft)
    body_dynamics_group_layout.addLayout(body_dynamics_layout)

    for _ in range(3):
        body_dynamics_row = QWidget()
        body_dynamics_row_layout = QHBoxLayout()
        body_dynamics_row_layout.setContentsMargins(0, 0, 0, 0)
        body_dynamics_row.setLayout(body_dynamics_row_layout)

        body_combo = QComboBox()
        apply_default_dropdown_style(body_combo)
        body_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(body_combo, 10)
        for body in JONES_PLANETS:
            body_combo.addItem(compact_body_label(body), body)
        body_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        role_combo = QComboBox()
        apply_default_dropdown_style(role_combo)
        role_combo.addItem("Any ±", "any")
        set_dropdown_width_chars(role_combo, 10)
        for role_label, role_key in BODY_DYNAMICS_ROLE_OPTIONS:
            role_combo.addItem(role_label, role_key)
        role_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_exclude = QRadioButton("🚫")
        filter_group = QButtonGroup(body_dynamics_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_exclude)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        body_dynamics_row_layout.addWidget(body_combo, 1)
        body_dynamics_row_layout.addWidget(role_combo, 1)
        body_dynamics_row_layout.addWidget(filter_and)
        body_dynamics_row_layout.addWidget(filter_or)
        body_dynamics_row_layout.addWidget(filter_exclude)

        window._body_dynamics_filters.append({
            "body": body_combo,
            "role": role_combo,
            "and": filter_and,
            "or": filter_or,
            "exclude": filter_exclude,
        })
        body_dynamics_layout.addRow(body_dynamics_row)

    astro_category_layout.addWidget(body_dynamics_section)

    # Search: Decans section
    decan_section, decan_group_layout = add_collapsible_section("🪐Decans")
    decan_layout = QFormLayout()
    decan_layout.setLabelAlignment(Qt.AlignLeft)
    decan_group_layout.addLayout(decan_layout)

    decan_row = QWidget()
    decan_row_layout = QHBoxLayout()
    decan_row_layout.setContentsMargins(0, 0, 0, 0)
    decan_row.setLayout(decan_row_layout)

    decan_sign_combo = QComboBox()
    apply_default_dropdown_style(decan_sign_combo)
    decan_sign_combo.addItem("Any", "Any")
    for sign_name in ZODIAC_NAMES:
        decan_sign_combo.addItem(str(sign_name), str(sign_name))
    decan_sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    decan_number_combo = QComboBox()
    apply_default_dropdown_style(decan_number_combo)
    decan_number_combo.addItem("Any", "Any")
    decan_number_combo.addItem("1", "1")
    decan_number_combo.addItem("2", "2")
    decan_number_combo.addItem("3", "3")
    decan_number_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    #decan_row_layout.addWidget(QLabel("")) #🔟
    decan_row_layout.addWidget(decan_sign_combo, 1)
    decan_row_layout.addWidget(decan_number_combo, 1)
    decan_row_layout.addStretch(1)

    window._decan_sign_filter_combo = decan_sign_combo
    window._decan_number_filter_combo = decan_number_combo
    decan_layout.addRow(decan_row)
    astro_category_layout.addWidget(decan_section)

    #Search: Isolated Factors section
    isolated_factors_section, isolated_factors_group_layout = add_collapsible_section(
        "🪐Isolated Factors",
    )

    isolated_body_row = QHBoxLayout()
    isolated_body_row.addWidget(QLabel("Isolated dominance of"))
    window._isolated_dominant_body_filter_combo = QComboBox()
    apply_default_dropdown_style(window._isolated_dominant_body_filter_combo)
    window._isolated_dominant_body_filter_combo.addItem("Any 🪐", "Any")
    set_dropdown_width_chars(window._isolated_dominant_body_filter_combo, 10)
    for body_label, body_key in window._searchable_bodies():
        if body_key in {"AS", "IC", "DS", "MC"}:
            continue
        window._isolated_dominant_body_filter_combo.addItem(compact_body_label(body_label), body_key)
    window._isolated_dominant_body_filter_combo.currentIndexChanged.connect(
        window._on_astrological_filter_changed
    )
    isolated_body_row.addWidget(window._isolated_dominant_body_filter_combo, 1)
    isolated_factors_group_layout.addLayout(isolated_body_row)

    isolated_operator_row = QHBoxLayout()
    isolated_operator_row.addStretch(1)
    window._isolated_dominant_filter_and = QRadioButton("&&")
    window._isolated_dominant_filter_or = QRadioButton("OR")
    isolated_operator_group = QButtonGroup(window)
    isolated_operator_group.setExclusive(True)
    isolated_operator_group.addButton(window._isolated_dominant_filter_and)
    isolated_operator_group.addButton(window._isolated_dominant_filter_or)
    window._isolated_dominant_filter_and.setChecked(True)
    isolated_operator_group.buttonClicked.connect(window._on_filter_changed)
    isolated_operator_row.addWidget(window._isolated_dominant_filter_and)
    isolated_operator_row.addWidget(window._isolated_dominant_filter_or)
    isolated_operator_row.addStretch(1)
    isolated_factors_group_layout.addLayout(isolated_operator_row)

    isolated_sign_row = QHBoxLayout()
    isolated_sign_row.addWidget(QLabel("Isolated dominance of"))
    window._isolated_dominant_sign_filter_combo = QComboBox()
    apply_default_dropdown_style(window._isolated_dominant_sign_filter_combo)
    window._isolated_dominant_sign_filter_combo.addItem("Any 🌟", "Any")
    set_dropdown_width_chars(window._isolated_dominant_sign_filter_combo, 6)
    for sign in ZODIAC_NAMES:
        window._isolated_dominant_sign_filter_combo.addItem(sign, sign)
    window._isolated_dominant_sign_filter_combo.currentIndexChanged.connect(
        window._on_astrological_filter_changed
    )
    isolated_sign_row.addWidget(window._isolated_dominant_sign_filter_combo, 1)
    isolated_factors_group_layout.addLayout(isolated_sign_row)

    astro_category_layout.addWidget(isolated_factors_section)

    #Search: Human Design section
    human_design_group_layout = human_design_category_layout

    hd_channels_row = QHBoxLayout()
    hd_channels_row.addWidget(QLabel("Channels"))
    for _ in range(3):
        channel_combo = QComboBox()
        apply_default_dropdown_style(channel_combo)
        channel_combo.addItem("Any", "Any")
        channel_options = sorted(
            {
                str(channel_key).strip()
                for channel_key in HD_CHANNELS.keys()
                if str(channel_key).strip()
            },
            key=lambda value: (
                int(value.split("-")[0]) if "-" in value and value.split("-")[0].isdigit() else 999,
                int(value.split("-")[1]) if "-" in value and len(value.split("-")) > 1 and value.split("-")[1].isdigit() else 999,
                value,
            ),
        )
        for channel_label in channel_options:
            channel_combo.addItem(channel_label, channel_label)
        set_dropdown_width_chars(channel_combo, 7)
        channel_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_channel_filters.append(channel_combo)
        hd_channels_row.addWidget(channel_combo)
    window._human_design_channel_filter_and = QRadioButton("&&")
    window._human_design_channel_filter_or = QRadioButton("OR")
    hd_channel_group = QButtonGroup(window)
    hd_channel_group.setExclusive(True)
    hd_channel_group.addButton(window._human_design_channel_filter_and)
    hd_channel_group.addButton(window._human_design_channel_filter_or)
    window._human_design_channel_filter_and.setChecked(True)
    hd_channel_group.buttonClicked.connect(window._on_filter_changed)
    hd_channels_row.addWidget(window._human_design_channel_filter_and)
    hd_channels_row.addWidget(window._human_design_channel_filter_or)
    human_design_group_layout.addLayout(hd_channels_row)

    for row_index in range(3):
        hd_gates_row = QHBoxLayout()
        hd_gates_row.addWidget(QLabel("Gates" if row_index == 0 else ""))
        gate_combo = QComboBox()
        apply_default_dropdown_style(gate_combo)
        gate_combo.addItem("Any", "Any")
        for gate_value in range(1, 65):
            gate_combo.addItem(str(gate_value), gate_value)
        center_dropdown_items(gate_combo)
        set_dropdown_width_chars(gate_combo, 3)
        gate_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_gate_filters.append(gate_combo)
        hd_gates_row.addWidget(gate_combo)

        hd_gates_row.addWidget(QLabel("Line"))
        line_combo = QComboBox()
        apply_default_dropdown_style(line_combo)
        line_combo.addItem("Any", "Any")
        for line_value in range(1, 7):
            line_combo.addItem(str(line_value), line_value)
        center_dropdown_items(line_combo)
        set_dropdown_width_chars(line_combo, 4)
        line_combo.currentIndexChanged.connect(window._on_filter_changed)
        hd_gates_row.addWidget(line_combo)

        gate_filter_and = QRadioButton("&&")
        gate_filter_or = QRadioButton("OR")
        hd_gate_group = QButtonGroup(window)
        hd_gate_group.setExclusive(True)
        hd_gate_group.addButton(gate_filter_and)
        hd_gate_group.addButton(gate_filter_or)
        gate_filter_and.setChecked(True)
        hd_gate_group.buttonClicked.connect(window._on_filter_changed)
        hd_gates_row.addWidget(gate_filter_and)
        hd_gates_row.addWidget(gate_filter_or)
        human_design_group_layout.addLayout(hd_gates_row)

        window._human_design_gate_line_filters.append(
            {"gate": gate_combo, "line": line_combo, "and": gate_filter_and, "or": gate_filter_or}
        )
        if row_index == 0:
            window._human_design_gate_filter_and = gate_filter_and
            window._human_design_gate_filter_or = gate_filter_or

    hd_type_row = QHBoxLayout()
    hd_type_row.addWidget(QLabel("Type"))
    window._human_design_type_filter_combo = QComboBox()
    apply_default_dropdown_style(window._human_design_type_filter_combo)
    window._human_design_type_filter_combo.addItem("Any", "Any")
    window._human_design_type_filter_combo.addItem("Manifestor", "Manifestor")
    window._human_design_type_filter_combo.addItem("Generator", "Generator")
    window._human_design_type_filter_combo.addItem("Manifesting Generator", "Manifesting Generator")
    window._human_design_type_filter_combo.addItem("Projector", "Projector")
    set_dropdown_width_chars(window._human_design_type_filter_combo, 22)
    window._human_design_type_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    hd_type_row.addWidget(window._human_design_type_filter_combo)
    human_design_group_layout.addLayout(hd_type_row)

    hd_profile_row = QHBoxLayout()
    hd_profile_row.addWidget(QLabel("Profile"))
    window._human_design_profile_filter_combo = QComboBox()
    apply_default_dropdown_style(window._human_design_profile_filter_combo)
    window._human_design_profile_filter_combo.addItem("Any", "Any")
    for profile_label in getattr(window, "HD_STANDARD_PROFILES", ()):
        window._human_design_profile_filter_combo.addItem(profile_label, profile_label)
    set_dropdown_width_chars(window._human_design_profile_filter_combo, 6)
    window._human_design_profile_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    hd_profile_row.addWidget(window._human_design_profile_filter_combo)
    human_design_group_layout.addLayout(hd_profile_row)

    hd_defined_centers_row = QHBoxLayout()
    hd_defined_centers_row.addWidget(QLabel("Defined:"))
    for _ in range(3):
        center_combo = QComboBox()
        apply_default_dropdown_style(center_combo)
        center_combo.addItem("Any", "Any")
        for center_label in getattr(window, "HD_DEFINED_CENTER_ORDER", ()):
            center_combo.addItem(center_label, center_label)
        set_dropdown_width_chars(center_combo, 11)
        center_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_defined_center_filters.append(center_combo)
        hd_defined_centers_row.addWidget(center_combo)
    window._human_design_defined_center_filter_and = QRadioButton("&&")
    window._human_design_defined_center_filter_or = QRadioButton("OR")
    hd_defined_center_group = QButtonGroup(window)
    hd_defined_center_group.setExclusive(True)
    hd_defined_center_group.addButton(window._human_design_defined_center_filter_and)
    hd_defined_center_group.addButton(window._human_design_defined_center_filter_or)
    window._human_design_defined_center_filter_and.setChecked(True)
    hd_defined_center_group.buttonClicked.connect(window._on_filter_changed)
    hd_defined_centers_row.addWidget(window._human_design_defined_center_filter_and)
    hd_defined_centers_row.addWidget(window._human_design_defined_center_filter_or)
    human_design_group_layout.addLayout(hd_defined_centers_row)

    #Search: year first encountered
    year_first_encountered_section, year_first_encountered_group_layout = add_collapsible_section(
        "💭Year 1st Encountered", #year user first encountered
    )
    year_first_encountered_range_row = QHBoxLayout()
    year_first_encountered_range_row.addWidget(QLabel("Earliest"))
    window._year_first_encountered_earliest_input = QLineEdit()
    window._year_first_encountered_earliest_input.setMaxLength(4)
    window._year_first_encountered_earliest_input.setFixedWidth(56)
    window._year_first_encountered_earliest_input.setPlaceholderText("YYYY")
    window._year_first_encountered_earliest_input.setValidator(
        QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, window)
    )
    window._year_first_encountered_earliest_input.textChanged.connect(window._on_filter_changed)
    year_first_encountered_range_row.addWidget(window._year_first_encountered_earliest_input)
    year_first_encountered_range_row.addSpacing(10)
    year_first_encountered_range_row.addWidget(QLabel("Latest"))
    window._year_first_encountered_latest_input = QLineEdit()
    window._year_first_encountered_latest_input.setMaxLength(4)
    window._year_first_encountered_latest_input.setFixedWidth(56)
    window._year_first_encountered_latest_input.setPlaceholderText("YYYY")
    window._year_first_encountered_latest_input.setValidator(
        QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, window)
    )
    window._year_first_encountered_latest_input.textChanged.connect(window._on_filter_changed)
    year_first_encountered_range_row.addWidget(window._year_first_encountered_latest_input)
    year_first_encountered_range_row.addStretch(1)
    year_first_encountered_group_layout.addLayout(year_first_encountered_range_row)

    year_first_encountered_blank_row = QHBoxLayout()
    window._year_first_encountered_blank_checkbox = QuadStateSlider("blank")
    window._year_first_encountered_blank_checkbox.modeChanged.connect(window._on_filter_changed)
    year_first_encountered_blank_row.addWidget(window._year_first_encountered_blank_checkbox)
    year_first_encountered_blank_row.addStretch(1)
    year_first_encountered_group_layout.addLayout(year_first_encountered_blank_row)
    interactions_category_layout.addWidget(year_first_encountered_section)

    sentiment_section, sentiment_group_layout = add_collapsible_section("💭Sentiment")
    window.search_sentiment_section = sentiment_section

    #Search: Sentiments section
    sentiment_mode_layout = QHBoxLayout()
    sentiment_mode_layout.addWidget(QLabel("Sentiments"))
    sentiment_mode_layout.addStretch(1)
    window.sentiment_filter_and = QRadioButton("AND")
    window.sentiment_filter_or = QRadioButton("OR")
    window.sentiment_filter_group = QButtonGroup(window)
    window.sentiment_filter_group.setExclusive(True)
    window.sentiment_filter_group.addButton(window.sentiment_filter_and)
    window.sentiment_filter_group.addButton(window.sentiment_filter_or)
    window.sentiment_filter_and.setChecked(True)
    # Use group-level click handling so we only refresh once per selection
    # change and avoid transient states where neither option is checked.
    window.sentiment_filter_group.buttonClicked.connect(window._on_filter_changed)
    sentiment_mode_layout.addWidget(window.sentiment_filter_and)
    sentiment_mode_layout.addWidget(window.sentiment_filter_or)
    sentiment_group_layout.addLayout(sentiment_mode_layout)
    sentiment_layout = QGridLayout()
    sentiment_layout.setContentsMargins(0, 0, 0, 0)
    window.sentiment_filter_checkboxes = {}
    sentiment_rows = (len(SEARCH_SENTIMENT_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_SENTIMENT_OPTIONS):
        checkbox = QuadStateSlider(label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.sentiment_filter_checkboxes[label] = checkbox
        row = idx % sentiment_rows
        col = idx // sentiment_rows
        sentiment_layout.addWidget(checkbox, row, col)
    sentiment_group_layout.addLayout(sentiment_layout)

    sentiment_intensity_row = QHBoxLayout()
    sentiment_intensity_row.addWidget(QLabel("💖"))
    window._positive_sentiment_intensity_min_input = QLineEdit()
    window._positive_sentiment_intensity_min_input.setFixedWidth(44)
    window._positive_sentiment_intensity_min_input.setMaxLength(2)
    window._positive_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, window))
    window._positive_sentiment_intensity_min_input.setPlaceholderText("min")
    window._positive_sentiment_intensity_min_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._positive_sentiment_intensity_min_input)
    sentiment_intensity_row.addWidget(QLabel("max"))
    window._positive_sentiment_intensity_max_input = QLineEdit()
    window._positive_sentiment_intensity_max_input.setFixedWidth(44)
    window._positive_sentiment_intensity_max_input.setMaxLength(2)
    window._positive_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, window))
    window._positive_sentiment_intensity_max_input.setPlaceholderText("max")
    window._positive_sentiment_intensity_max_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._positive_sentiment_intensity_max_input)
    sentiment_intensity_row.addSpacing(10)
    sentiment_intensity_row.addWidget(QLabel("💔"))
    window._negative_sentiment_intensity_min_input = QLineEdit()
    window._negative_sentiment_intensity_min_input.setFixedWidth(44)
    window._negative_sentiment_intensity_min_input.setMaxLength(2)
    window._negative_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, window))
    window._negative_sentiment_intensity_min_input.setPlaceholderText("min")
    window._negative_sentiment_intensity_min_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._negative_sentiment_intensity_min_input)
    sentiment_intensity_row.addWidget(QLabel("max"))
    window._negative_sentiment_intensity_max_input = QLineEdit()
    window._negative_sentiment_intensity_max_input.setFixedWidth(44)
    window._negative_sentiment_intensity_max_input.setMaxLength(2)
    window._negative_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, window))
    window._negative_sentiment_intensity_max_input.setPlaceholderText("max")
    window._negative_sentiment_intensity_max_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._negative_sentiment_intensity_max_input)
    sentiment_intensity_row.addStretch(1)
    sentiment_group_layout.addLayout(sentiment_intensity_row)

    familiarity_row = QHBoxLayout()
    familiarity_row.addWidget(QLabel("Familiarity"))
    window._familiarity_min_input = QLineEdit()
    window._familiarity_min_input.setFixedWidth(44)
    window._familiarity_min_input.setMaxLength(2)
    window._familiarity_min_input.setValidator(QIntValidator(1, 10, window))
    window._familiarity_min_input.setPlaceholderText("min")
    window._familiarity_min_input.textChanged.connect(window._on_filter_changed)
    familiarity_row.addWidget(window._familiarity_min_input)
    familiarity_row.addWidget(QLabel("max"))
    window._familiarity_max_input = QLineEdit()
    window._familiarity_max_input.setFixedWidth(44)
    window._familiarity_max_input.setMaxLength(2)
    window._familiarity_max_input.setValidator(QIntValidator(1, 10, window))
    window._familiarity_max_input.setPlaceholderText("max")
    window._familiarity_max_input.textChanged.connect(window._on_filter_changed)
    familiarity_row.addWidget(window._familiarity_max_input)
    familiarity_row.addStretch(1)
    sentiment_group_layout.addLayout(familiarity_row)

    interactions_category_layout.addWidget(sentiment_section)

    #Search: Alignment section
    alignment_section, alignment_group_layout = add_collapsible_section("💭Alignment")
    window.search_alignment_section = alignment_section
    alignment_range_row = QHBoxLayout()
    alignment_range_row.addWidget(QLabel("💭Alignment"))
    window._alignment_score_min_input = QLineEdit()
    window._alignment_score_min_input.setFixedWidth(44)
    window._alignment_score_min_input.setMaxLength(3)
    window._alignment_score_min_input.setValidator(QIntValidator(-10, 10, window))
    window._alignment_score_min_input.setPlaceholderText("min")
    window._alignment_score_min_input.textChanged.connect(window._on_filter_changed)
    alignment_range_row.addWidget(window._alignment_score_min_input)
    alignment_range_row.addWidget(QLabel("max"))
    window._alignment_score_max_input = QLineEdit()
    window._alignment_score_max_input.setFixedWidth(44)
    window._alignment_score_max_input.setMaxLength(3)
    window._alignment_score_max_input.setValidator(QIntValidator(-10, 10, window))
    window._alignment_score_max_input.setPlaceholderText("max")
    window._alignment_score_max_input.textChanged.connect(window._on_filter_changed)
    alignment_range_row.addWidget(window._alignment_score_max_input)
    alignment_range_row.addStretch(1)
    alignment_group_layout.addLayout(alignment_range_row)

    window._alignment_score_blank_checkbox = QCheckBox("no alignment assigned")
    window._alignment_score_blank_checkbox.stateChanged.connect(window._on_filter_changed)
    alignment_group_layout.addWidget(window._alignment_score_blank_checkbox)
    interactions_category_layout.addWidget(alignment_section)

    #Search: relationship types section
    relationship_section, relationship_group_layout = add_collapsible_section(
        "💭Relationships",
    )
    window.search_relationship_section = relationship_section
    relationship_mode_layout = QHBoxLayout()
    relationship_mode_layout.addWidget(QLabel("Relationship type"))
    relationship_mode_layout.addStretch(1)
    window.relationship_filter_and = QRadioButton("AND")
    window.relationship_filter_or = QRadioButton("OR")
    window.relationship_filter_group = QButtonGroup(window)
    window.relationship_filter_group.setExclusive(True)
    window.relationship_filter_group.addButton(window.relationship_filter_and)
    window.relationship_filter_group.addButton(window.relationship_filter_or)
    window.relationship_filter_and.setChecked(True)
    window.relationship_filter_group.buttonClicked.connect(window._on_filter_changed)
    relationship_mode_layout.addWidget(window.relationship_filter_and)
    relationship_mode_layout.addWidget(window.relationship_filter_or)
    relationship_group_layout.addLayout(relationship_mode_layout)

    relationship_layout = QGridLayout()
    relationship_layout.setContentsMargins(0, 0, 0, 0)
    window.relationship_filter_checkboxes = {}
    relationship_rows = (len(SEARCH_RELATIONSHIP_TYPE_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_RELATIONSHIP_TYPE_OPTIONS):
        checkbox = QuadStateSlider(label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.relationship_filter_checkboxes[label] = checkbox
        row = idx % relationship_rows
        col = idx // relationship_rows
        relationship_layout.addWidget(checkbox, row, col)
    relationship_group_layout.addLayout(relationship_layout)
    interactions_category_layout.addWidget(relationship_section)

    #Search: Fantasy RPG section
    dnd_species_section, dnd_species_group_layout = add_collapsible_section(
        "⚔️Fantasy RPG",
    )
    class_filter_row = QHBoxLayout()
    class_filter_row.addWidget(QLabel("Top 3 Classes"))
    window.dnd_class_filter_combo = QComboBox()
    apply_default_dropdown_style(window.dnd_class_filter_combo)
    window.dnd_class_filter_combo.addItem("Any", "Any")
    for class_definition in DND_CLASSES.values():
        window.dnd_class_filter_combo.addItem(class_definition.display_name, class_definition.display_name)
    window.dnd_class_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    class_filter_row.addWidget(window.dnd_class_filter_combo, 1)
    dnd_species_group_layout.addLayout(class_filter_row)

    species_filter_row = QHBoxLayout()
    species_filter_row.addWidget(QLabel("Top 3 Species"))
    window.species_filter_combo = QComboBox()
    apply_default_dropdown_style(window.species_filter_combo)
    window.species_filter_combo.addItem("Any", "Any")
    for species in SPECIES_FAMILIES:
        window.species_filter_combo.addItem(species, species)
    species_filter_row.addWidget(window.species_filter_combo, 1)
    dnd_species_group_layout.addLayout(species_filter_row)

    subspecies_filter_row = QHBoxLayout()
    subspecies_filter_label = QLabel("Subspecies")
    subspecies_filter_row.addWidget(subspecies_filter_label)
    window.subspecies_filter_combo = QComboBox()
    apply_default_dropdown_style(window.subspecies_filter_combo)
    window.subspecies_filter_combo.addItem("Any", "Any")
    subspecies_filter_row.addWidget(window.subspecies_filter_combo, 1)
    dnd_species_group_layout.addLayout(subspecies_filter_row)

    def refresh_subspecies_filter_options() -> None:
        selected_species = str(window.species_filter_combo.currentData() or "Any")
        subtypes = list(FAMILY_SUBTYPES.get(selected_species, []))
        row_visible = selected_species != "Any" and bool(subtypes)
        subspecies_filter_label.setVisible(row_visible)
        window.subspecies_filter_combo.setVisible(row_visible)
        window.subspecies_filter_combo.blockSignals(True)
        try:
            previous_subspecies = str(window.subspecies_filter_combo.currentData() or "Any")
            window.subspecies_filter_combo.clear()
            window.subspecies_filter_combo.addItem("Any", "Any")
            for subtype in subtypes:
                window.subspecies_filter_combo.addItem(subtype, subtype)
            previous_index = window.subspecies_filter_combo.findData(previous_subspecies)
            window.subspecies_filter_combo.setCurrentIndex(previous_index if previous_index >= 0 else 0)
        finally:
            window.subspecies_filter_combo.blockSignals(False)

    def on_species_filter_changed() -> None:
        refresh_subspecies_filter_options()
        window._on_filter_changed()

    window.species_filter_combo.currentIndexChanged.connect(on_species_filter_changed)
    window.subspecies_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    refresh_subspecies_filter_options()

    dnd_stats_header = QLabel("Stat ranges")
    dnd_stats_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dnd_species_group_layout.addWidget(dnd_stats_header)
    dnd_stat_grid = QGridLayout()
    dnd_stat_grid.setContentsMargins(0, 0, 0, 0)
    dnd_stat_grid.setHorizontalSpacing(14)
    dnd_stat_grid.setVerticalSpacing(4)
    dnd_stat_filter_order = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    for idx, stat_key in enumerate(dnd_stat_filter_order):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        row_layout.addWidget(QLabel(stat_key))
        row_layout.addWidget(QLabel("min:"))
        min_input = QLineEdit()
        min_input.setFixedWidth(40)
        min_input.setMaxLength(2)
        min_input.setValidator(QIntValidator(1, 30, window))
        min_input.setPlaceholderText("min")
        min_input.textChanged.connect(window._on_filter_changed)
        row_layout.addWidget(min_input)
        row_layout.addWidget(QLabel("max:"))
        max_input = QLineEdit()
        max_input.setFixedWidth(40)
        max_input.setMaxLength(2)
        max_input.setValidator(QIntValidator(1, 30, window))
        max_input.setPlaceholderText("max")
        max_input.textChanged.connect(window._on_filter_changed)
        row_layout.addWidget(max_input)
        row_layout.addStretch(1)
        window._dnd_stat_filter_min_inputs[stat_key] = min_input
        window._dnd_stat_filter_max_inputs[stat_key] = max_input
        row = idx % 3
        col = idx // 3
        dnd_stat_grid.addLayout(row_layout, row, col)
    dnd_species_group_layout.addLayout(dnd_stat_grid)
    predictions_category_layout.addWidget(dnd_species_section)

    timing_section, timing_section_layout = add_collapsible_section("🕰️Lifespan")

    def add_birthdate_bound_row(
        row_label: str,
        month_attr: str,
        day_attr: str,
        year_attr: str,
    ) -> None:
        bound_row = QHBoxLayout()
        bound_row.setContentsMargins(0, 0, 0, 0)
        bound_row.setSpacing(4)
        bound_row.addWidget(QLabel(row_label))

        month_input = QLineEdit()
        month_input.setMaxLength(2)
        month_input.setFixedWidth(34)
        month_input.setValidator(QIntValidator(1, 12, window))
        month_input.setPlaceholderText("MM")
        month_input.textChanged.connect(window._on_filter_changed)
        setattr(window, month_attr, month_input)
        bound_row.addWidget(month_input)

        day_input = QLineEdit()
        day_input.setMaxLength(2)
        day_input.setFixedWidth(34)
        day_input.setValidator(QIntValidator(1, 31, window))
        day_input.setPlaceholderText("DD")
        day_input.textChanged.connect(window._on_filter_changed)
        setattr(window, day_attr, day_input)
        bound_row.addWidget(day_input)

        year_input = QLineEdit()
        year_input.setMaxLength(4)
        year_input.setFixedWidth(56)
        year_input.setValidator(QIntValidator(1, 9999, window))
        year_input.setPlaceholderText("YYYY")
        year_input.textChanged.connect(window._on_filter_changed)
        setattr(window, year_attr, year_input)
        bound_row.addWidget(year_input)
        bound_row.addStretch(1)
        timing_section_layout.addLayout(bound_row)

    add_birthdate_bound_row(
        "earliest:",
        "_birthdate_earliest_month_input",
        "_birthdate_earliest_day_input",
        "_birthdate_earliest_year_input",
    )
    add_birthdate_bound_row(
        "latest:",
        "_birthdate_latest_month_input",
        "_birthdate_latest_day_input",
        "_birthdate_latest_year_input",
    )

    timing_section_layout.addWidget(create_divider())

    generation_header = QLabel("Generation")
    generation_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    timing_section_layout.addWidget(generation_header)

    generation_layout = QGridLayout()
    generation_layout.setContentsMargins(0, 0, 0, 0)
    window.generation_filter_checkboxes = {}
    generation_rows = (len(GENERATION_FILTER_OPTIONS) + 1) // 2
    for idx, generation_name in enumerate(GENERATION_FILTER_OPTIONS):
        checkbox = QuadStateSlider(generation_name)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.generation_filter_checkboxes[generation_name] = checkbox
        row = idx % generation_rows
        col = idx // generation_rows
        generation_layout.addWidget(checkbox, row, col)
    timing_section_layout.addLayout(generation_layout)

    timing_section_layout.addWidget(create_divider())
    mortality_header = QLabel("Mortality")
    mortality_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    timing_section_layout.addWidget(mortality_header)
    mortality_row = QHBoxLayout()
    window.living_checkbox = QuadStateSlider("living")
    window.living_checkbox.modeChanged.connect(window._on_filter_changed)
    mortality_row.addWidget(window.living_checkbox)
    mortality_row.addStretch(1)
    timing_section_layout.addLayout(mortality_row)

    #Search: gender section
    gender_section, gender_group_layout = add_collapsible_section("⚧️Gender")
    gender_mode_layout = QHBoxLayout()
    gender_mode_layout.addWidget(QLabel("Gender"))
    gender_mode_layout.addStretch(1)
    window.gender_filter_and = QRadioButton("AND")
    window.gender_filter_or = QRadioButton("OR")
    window.gender_filter_group = QButtonGroup(window)
    window.gender_filter_group.setExclusive(True)
    window.gender_filter_group.addButton(window.gender_filter_and)
    window.gender_filter_group.addButton(window.gender_filter_or)
    window.gender_filter_and.setChecked(True)
    window.gender_filter_group.buttonClicked.connect(window._on_filter_changed)
    gender_mode_layout.addWidget(window.gender_filter_and)
    gender_mode_layout.addWidget(window.gender_filter_or)
    gender_group_layout.addLayout(gender_mode_layout)

    gender_layout = QGridLayout()
    gender_layout.setContentsMargins(0, 0, 0, 0)
    window.gender_filter_checkboxes = {}
    gender_rows = (len(SEARCH_GENDER_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_GENDER_OPTIONS):
        checkbox_label = "blank" if label == "none" else label
        checkbox = QuadStateSlider(checkbox_label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.gender_filter_checkboxes[label] = checkbox
        row = idx % gender_rows
        col = idx // gender_rows
        gender_layout.addWidget(checkbox, row, col)
    gender_group_layout.addLayout(gender_layout)

    gender_guessed_layout = QHBoxLayout()
    gender_guessed_layout.addWidget(QLabel("Gender Guessed"))
    window.gender_guessed_filter_combo = QComboBox()
    apply_default_dropdown_style(window.gender_guessed_filter_combo)
    for label, value in SEARCH_GENDER_GUESSED_OPTIONS:
        window.gender_guessed_filter_combo.addItem(label, value)
    window.gender_guessed_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    gender_guessed_layout.addWidget(window.gender_guessed_filter_combo)
    gender_group_layout.addLayout(gender_guessed_layout)


    #Search: Locations section
    locations_section, locations_group_layout = add_collapsible_section("📍Location")

    country_row = QHBoxLayout()
    country_row.addWidget(QLabel("Country"))
    window._search_location_country_input = QLineEdit()
    window._search_location_country_input.setPlaceholderText("e.g. USA, UK, Italy")
    window._search_location_country_input.textChanged.connect(window._on_filter_changed)
    window._search_location_country_input.returnPressed.connect(window._on_filter_changed)
    country_row.addWidget(window._search_location_country_input, 1)
    locations_group_layout.addLayout(country_row)

    city_row = QHBoxLayout()
    city_row.addWidget(QLabel("City"))
    window._search_location_city_input = QLineEdit()
    window._search_location_city_input.setPlaceholderText("e.g. London")
    window._search_location_city_input.textChanged.connect(window._on_filter_changed)
    window._search_location_city_input.returnPressed.connect(window._on_filter_changed)
    city_row.addWidget(window._search_location_city_input, 1)
    locations_group_layout.addLayout(city_row)

    state_row = QHBoxLayout()
    state_row.addWidget(QLabel("State"))
    window._search_location_state_input = QLineEdit()
    window._search_location_state_input.setPlaceholderText("e.g. CA, NY, PR")
    window._search_location_state_input.textChanged.connect(window._on_filter_changed)
    window._search_location_state_input.returnPressed.connect(window._on_filter_changed)
    state_row.addWidget(window._search_location_state_input, 1)
    locations_group_layout.addLayout(state_row)

    predictability_section, predictability_group_layout = add_collapsible_section(
        "💭Predictability",
    )
    window.search_predictability_section = predictability_section
    visibility_store = getattr(window, "_visibility", None)
    if visibility_store is not None and hasattr(visibility_store, "get"):
        predictability_section.setVisible(visibility_store.get("chart_view.predictability"))
    predictability_range_layout = QGridLayout()
    predictability_range_layout.setContentsMargins(0, 0, 0, 0)
    predictability_range_layout.addWidget(QLabel("Min"), 0, 0)
    window._matched_expectations_min_input = QLineEdit()
    window._matched_expectations_min_input.setPlaceholderText("-10")
    window._matched_expectations_min_input.setValidator(QIntValidator(-10, 10, window))
    window._matched_expectations_min_input.textChanged.connect(window._on_filter_changed)
    predictability_range_layout.addWidget(window._matched_expectations_min_input, 0, 1)
    predictability_range_layout.addWidget(QLabel("Max"), 1, 0)
    window._matched_expectations_max_input = QLineEdit()
    window._matched_expectations_max_input.setPlaceholderText("10")
    window._matched_expectations_max_input.setValidator(QIntValidator(-10, 10, window))
    window._matched_expectations_max_input.textChanged.connect(window._on_filter_changed)
    predictability_range_layout.addWidget(window._matched_expectations_max_input, 1, 1)
    predictability_group_layout.addLayout(predictability_range_layout)
    window._matched_expectations_blank_checkbox = QCheckBox("include blank")
    window._matched_expectations_blank_checkbox.toggled.connect(window._on_filter_changed)
    predictability_group_layout.addWidget(window._matched_expectations_blank_checkbox)
    interactions_category_layout.addWidget(predictability_section)

    #Search: Notes section
    notes_section, notes_group_layout = add_collapsible_section("💭Notes")
    window.search_notes_section = notes_section

    comments_row = QHBoxLayout()
    window._notes_comments_filter_checkbox = QuadStateSlider("Comments")
    window._notes_comments_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    comments_row.addWidget(window._notes_comments_filter_checkbox)
    window._notes_comments_filter_input = QLineEdit()
    window._notes_comments_filter_input.setPlaceholderText("contains text")
    window._notes_comments_filter_input.textChanged.connect(window._on_filter_changed)
    comments_row.addWidget(window._notes_comments_filter_input, 1)
    notes_group_layout.addLayout(comments_row)

    bio_row = QHBoxLayout()
    window._notes_bio_filter_checkbox = QuadStateSlider("Bio")
    window._notes_bio_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    bio_row.addWidget(window._notes_bio_filter_checkbox)
    window._notes_bio_filter_input = QLineEdit()
    window._notes_bio_filter_input.setPlaceholderText("contains text")
    window._notes_bio_filter_input.textChanged.connect(window._on_filter_changed)
    bio_row.addWidget(window._notes_bio_filter_input, 1)
    notes_group_layout.addLayout(bio_row)

    quotes_row = QHBoxLayout()
    window._notes_quotes_filter_checkbox = QuadStateSlider("Quotes")
    window._notes_quotes_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    quotes_row.addWidget(window._notes_quotes_filter_checkbox)
    window._notes_quotes_filter_input = QLineEdit()
    window._notes_quotes_filter_input.setPlaceholderText("contains text")
    window._notes_quotes_filter_input.textChanged.connect(window._on_filter_changed)
    quotes_row.addWidget(window._notes_quotes_filter_input, 1)
    notes_group_layout.addLayout(quotes_row)

    rectification_row = QHBoxLayout()
    window._notes_rectification_filter_checkbox = QuadStateSlider("Rectification")
    window._notes_rectification_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    rectification_row.addWidget(window._notes_rectification_filter_checkbox)
    window._notes_rectification_filter_input = QLineEdit()
    window._notes_rectification_filter_input.setPlaceholderText("contains text")
    window._notes_rectification_filter_input.textChanged.connect(window._on_filter_changed)
    rectification_row.addWidget(window._notes_rectification_filter_input, 1)
    notes_group_layout.addLayout(rectification_row)

    source_row = QHBoxLayout()
    window._notes_source_filter_checkbox = QuadStateSlider("Source")
    window._notes_source_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    source_row.addWidget(window._notes_source_filter_checkbox)
    window._notes_source_filter_input = QLineEdit()
    window._notes_source_filter_input.setPlaceholderText("contains text")
    window._notes_source_filter_input.textChanged.connect(window._on_filter_changed)
    source_row.addWidget(window._notes_source_filter_input, 1)
    notes_group_layout.addLayout(source_row)

    interactions_category_layout.addWidget(notes_section)

    demographics_category_layout.addWidget(locations_section)
    demographics_category_layout.addWidget(gender_section)
    demographics_category_layout.addWidget(timing_section)

    button_row = QHBoxLayout()
    button_row.addStretch(1)
    clear_button = QPushButton("Clear filters")
    clear_button.clicked.connect(lambda: window._clear_filters())
    button_row.addWidget(clear_button)
    layout.addLayout(button_row)

    layout.addStretch(1)
    return panel
