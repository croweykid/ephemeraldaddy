"""Settings panel builders for display preferences and optional module visibility."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout

from ephemeraldaddy.gui.settings.core import DATABASE_VIEW_ROW_INFO_OPTIONS


class VisibilityReader(Protocol):
    def get(self, key: str) -> bool: ...


BuildLabel = Callable[[str], QLabel]
BoolCallback = Callable[[bool], None]
RowInfoCallback = Callable[[str, bool], None]
MetricVisible = Callable[[str], bool]
ChartAnalyticsVisible = Callable[[str], bool]
ChartDataVisibilityCallback = Callable[[str, bool], None]
PredictionVisibilityCallback = Callable[[str, bool], None]
MetricVisibilityCallback = Callable[[str, bool], None]
ChartAnalyticsVisibilityCallback = Callable[[str, bool], None]
PopoutVisibilityCallback = Callable[[str, bool], None]


@dataclass(frozen=True)
class DisplayPreferencesConfig:
    visibility: VisibilityReader
    row_info_visibility: dict[str, bool]
    show_hidden_charts: bool
    astrotwin_granular_explanation: bool
    build_subheader_label: BuildLabel
    build_help_label: BuildLabel
    set_row_info_visibility: RowInfoCallback
    set_show_hidden_charts: BoolCallback
    set_chart_data_visibility: ChartDataVisibilityCallback
    set_standard_deviation_indicators: BoolCallback
    set_astrotwin_granular_explanation: BoolCallback


@dataclass(frozen=True)
class OptionalModulesConfig:
    visibility: VisibilityReader
    chart_analytics_section_visible: ChartAnalyticsVisible
    database_metric_section_visible: MetricVisible
    build_subheader_label: BuildLabel
    set_chart_data_visibility: ChartDataVisibilityCallback
    set_prediction_section_visibility: PredictionVisibilityCallback
    set_gender_predictor_visibility: BoolCallback
    set_chart_analytics_visibility: ChartAnalyticsVisibilityCallback
    set_database_metric_visibility: MetricVisibilityCallback
    set_popout_visibility: PopoutVisibilityCallback
    set_dnd_statblock_explainer_visibility: BoolCallback
    set_sexiness_visibility: BoolCallback
    set_predictability_visibility: BoolCallback


def _add_checkbox(
    section_layout: QVBoxLayout,
    label: str,
    checked: bool,
    callback: BoolCallback,
    *,
    tooltip: str | None = None,
) -> QCheckBox:
    checkbox = QCheckBox(label)
    checkbox.setChecked(bool(checked))
    if tooltip:
        checkbox.setToolTip(tooltip)
    checkbox.toggled.connect(callback)
    section_layout.addWidget(checkbox)
    return checkbox


def populate_display_preferences_section(
    section_layout: QVBoxLayout,
    config: DisplayPreferencesConfig,
) -> dict[str, QCheckBox]:
    """Populate Settings > Display Preferences without depending on app.py windows."""
    section_layout.addWidget(config.build_subheader_label("Database View"))
    section_layout.addWidget(
        config.build_subheader_label(
            "Database Analytics & Similarities Analysis (lefthand) Panels"
        )
    )
    _add_checkbox(
        section_layout,
        "Show standard deviation indicator lines",
        config.visibility.get("charts.standard_deviation_indicators"),
        config.set_standard_deviation_indicators,
    )

    section_layout.addWidget(config.build_subheader_label("Database (middle) Panel"))
    # section_layout.addWidget(
    #     config.build_help_label(
    #         "Choose which details appear in the middle-panel chart list. "
    #         "HD profile is shown only for charts whose chart_uses_houses flag is TRUE."
    #     )
    # )
    row_info_checkboxes: dict[str, QCheckBox] = {}
    for row_info_key, row_info_label in DATABASE_VIEW_ROW_INFO_OPTIONS:
        checkbox = _add_checkbox(
            section_layout,
            f"Show {row_info_label}",
            bool(config.row_info_visibility.get(row_info_key, True)),
            lambda checked, key=row_info_key: config.set_row_info_visibility(key, checked),
        )
        row_info_checkboxes[row_info_key] = checkbox

    _add_checkbox(
        section_layout,
        "Show Hidden Charts",
        config.show_hidden_charts,
        config.set_show_hidden_charts,
        tooltip="Show charts hidden from the Database View middle-panel list.",
    )

    section_layout.addSpacing(8)
    section_layout.addWidget(config.build_subheader_label("Chart Editor"))
    section_layout.addWidget(config.build_subheader_label("Chart Data Output Panel"))
    _add_checkbox(
        section_layout,
        "Show Human Design gates/lines",
        config.visibility.get("chart_data.human_design"),
        lambda checked: config.set_chart_data_visibility("chart_data.human_design", checked),
    )

    section_layout.addSpacing(8)
    section_layout.addWidget(config.build_subheader_label("Popout Windows"))
    astrotwin_checkbox = _add_checkbox(
        section_layout,
        "Astro Twin: show granular algorithmic breakdowns",
        config.astrotwin_granular_explanation,
        config.set_astrotwin_granular_explanation,
    )
    row_info_checkboxes["astrotwin_granular_explanation"] = astrotwin_checkbox
    return row_info_checkboxes


def populate_optional_modules_section(
    section_layout: QVBoxLayout,
    config: OptionalModulesConfig,
) -> dict[str, QCheckBox]:
    """Populate Settings > Optional Modules with explicit visibility callbacks."""
    checkboxes: dict[str, QCheckBox] = {}
    section_layout.addWidget(config.build_subheader_label("Predictions"))

    checkboxes["cursedness"] = _add_checkbox(
        section_layout,
        "Show Cursedness Score",
        config.visibility.get("chart_data.cursedness"),
        lambda checked: config.set_chart_data_visibility("chart_data.cursedness", checked),
    )
    checkboxes["dnd_output"] = _add_checkbox(
        section_layout,
        "Show Fantasy RPG Card",
        config.visibility.get("chart_data.dnd_output"),
        lambda checked: config.set_chart_data_visibility("chart_data.dnd_output", checked),
    )

    for section_key, label in (
        ("traits", "Show Traits predictions"),
        ("ocean", "Show OCEAN Personality predictions"),
        ("enneagram", "Show Enneagram Predictor"),
        ("dnd_statblock", "Show Fantasy RPG Stat Block"),
        ("dnd_species", "Show Fantasy RPG Species"),
        ("dnd_class", "Show Fantasy RPG Class"),
        ("dnd_alignment", "Show Fantasy RPG Alignment"),
    ):
        checkboxes[f"predictions.{section_key}"] = _add_checkbox(
            section_layout,
            label,
            config.visibility.get(f"predictions.{section_key}"),
            lambda checked, key=section_key: config.set_prediction_section_visibility(key, checked),
        )

    checkboxes["gender_predictor"] = _add_checkbox(
        section_layout,
        "Show Gender Predictor",
        config.visibility.get("chart_view.gender_guesser"),
        config.set_gender_predictor_visibility,
    )
    checkboxes["body_dynamics"] = _add_checkbox(
        section_layout,
        "Show Body Dynamics",
        config.chart_analytics_section_visible("planet_dynamics"),
        lambda checked: config.set_chart_analytics_visibility("planet_dynamics", checked),
    )
    checkboxes["bazi"] = _add_checkbox(
        section_layout,
        "Show BaZi",
        config.database_metric_section_visible("bazi"),
        lambda checked: config.set_database_metric_visibility("bazi", checked),
    )
    checkboxes["synastry_aspect_weights"] = _add_checkbox(
        section_layout,
        "Show Synastry Aspect Weights",
        config.visibility.get("popout.synastry_aspect_weights"),
        lambda checked: config.set_popout_visibility("popout.synastry_aspect_weights", checked),
    )
    checkboxes["dnd_statblock_explainers"] = _add_checkbox(
        section_layout,
        "Show Fantasy RPG Stat Block explainers",
        config.visibility.get("analytics.dnd_statblock_explainers"),
        config.set_dnd_statblock_explainer_visibility,
    )
    checkboxes["species_distribution"] = _add_checkbox(
        section_layout,
        "Show Fantasy RPG Typing",
        config.database_metric_section_visible("species_distribution"),
        lambda checked: config.set_database_metric_visibility("species_distribution", checked),
    )

    section_layout.addSpacing(8)
    section_layout.addWidget(config.build_subheader_label("Observations & Misc"))
    checkboxes["sexiness"] = _add_checkbox(
        section_layout,
        "Show Sexiness",
        config.visibility.get("chart_view.sexiness"),
        config.set_sexiness_visibility,
    )
    # The persisted section key remains "anagrams" for compatibility, but the
    # user-facing panel is now the broader Linguistics (ABC) panel because the
    # same visibility switch owns both Anagrams and Euphonics content.
    checkboxes["anagrams"] = _add_checkbox(
        section_layout,
        "Show Linguistics (ABC) panel",
        config.chart_analytics_section_visible("anagrams"),
        lambda checked: config.set_chart_analytics_visibility("anagrams", checked),
    )
    checkboxes["predictability"] = _add_checkbox(
        section_layout,
        "Show Predictability",
        config.visibility.get("chart_view.predictability"),
        config.set_predictability_visibility,
    )
    return checkboxes
