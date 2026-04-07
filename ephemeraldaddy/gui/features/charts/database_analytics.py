"""Database View analytics chart rendering helpers."""

from __future__ import annotations

import datetime
import math
import statistics
import textwrap
import warnings
from collections import Counter
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLayout, QSizePolicy

from ephemeraldaddy.analysis.country_lookup import normalize_country, resolve_country
from ephemeraldaddy.analysis.city_lookup import normalize_city
from ephemeraldaddy.analysis.us_state_lookup import normalize_us_state
from ephemeraldaddy.core.interpretations import (
    AGE_BRACKETS,
    ELEMENT_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    RELATION_TYPE,
    SENTIMENT_COLORS,
    SIGN_COLORS,
    ZODIAC_NAMES,
)
from ephemeraldaddy.analysis.human_design import (
    build_human_design_result,
    derive_human_design_profile,
)
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.gui.features.charts.presentation import format_percent as _format_percent
from ephemeraldaddy.gui.style import (
    ALIGNMENT_CUMULATIVE_SUBTITLE_WRAP_WIDTH,
    CHART_AXES_STYLE,
    CHART_THEME_COLORS,
    DND_STAT_EARTHTONE_COLORS,
    GENDER_GUESSER_COLORS,
    get_cycled_earthtone_colors,
    value_to_red_blue_rgb,
)


class DatabaseAnalyticsChartsMixin:
    DND_STAT_KEYS: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    HD_DEFINED_CENTER_ORDER: tuple[str, ...] = (
        "Head",
        "Ajna",
        "Throat",
        "G",
        "Ego",
        "Spleen",
        "Solar Plexus",
        "Sacral",
        "Root",
    )
    HD_CENTER_COLORS: dict[str, str] = {
        str(center_data.get("center", "")).strip(): str(center_data.get("color", "#6fa8dc"))
        for center_data in HD_CENTERS
        if str(center_data.get("center", "")).strip()
    }

    @staticmethod
    def _apply_tight_layout(figure: Figure) -> None:
        """Apply tight layout while silencing benign layout-fit warnings."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=(
                    "Tight layout not applied. The left and right margins cannot be "
                    "made large enough to accommodate all Axes decorations."
                ),
                category=UserWarning,
            )
            figure.tight_layout()

    @staticmethod
    def _set_x_limits_with_padding(
        ax,
        minimum: float,
        maximum: float,
        pad_px: float = 10.0,
    ) -> None:
        fig = ax.figure
        axes_width_px = (
            fig.get_size_inches()[0] * fig.dpi * ax.get_position().width
        )
        data_range = maximum - minimum
        if data_range <= 0:
            center = float(minimum)
            # Avoid identical low/high limits, which triggers a Matplotlib warning.
            delta = max(abs(center) * 0.01, 0.5)
            ax.set_xlim(center - delta, center + delta)
            return
        if axes_width_px <= (pad_px * 2):
            ax.set_xlim(minimum, maximum)
            return
        pad_ratio = pad_px / axes_width_px
        data_pad = (pad_ratio * data_range) / max(1 - (2 * pad_ratio), 0.01)
        ax.set_xlim(minimum - data_pad, maximum + data_pad)

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    @staticmethod
    def _configure_left_panel_canvas(
        canvas: FigureCanvas,
        figure: Figure,
    ) -> None:
        height = int(round(figure.get_size_inches()[1] * figure.dpi))
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        canvas.setMinimumHeight(height)
        canvas.setMaximumHeight(height)
        #adds trackpad scrolling & hoverstate arrow scroll:
        canvas.setFocusPolicy(Qt.NoFocus)
        canvas.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    @staticmethod
    def _format_database_count_label(label: str, count: float | int) -> str:
        if isinstance(count, float) and not float(count).is_integer():
            count_text = f"{count:,.1f}"
        else:
            count_text = f"{int(round(count)):,.0f}"
        return f"({count_text}) {label}"

    def _format_selection_database_count_label(
        self,
        label: str,
        database_count: float | int,
        selected_count: float | int,
        show_selected: bool,
    ) -> str:
        if not show_selected:
            return self._format_database_count_label(label, database_count)
        if isinstance(selected_count, float) and not float(selected_count).is_integer():
            selected_text = f"{selected_count:,.1f}"
        else:
            selected_text = f"{int(round(selected_count)):,.0f}"
        if isinstance(database_count, float) and not float(database_count).is_integer():
            database_text = f"{database_count:,.1f}"
        else:
            database_text = f"{int(round(database_count)):,.0f}"
        database_count_value = float(database_count)
        selected_count_value = float(selected_count)
        percent_text = (
            _format_percent(selected_count_value / database_count_value)
            if database_count_value
            else "0%"
        )
        return f"({selected_text} of {database_text} : {percent_text}) {label}"

    def _extract_human_design_profile(
        self,
        chart: Any,
    ) -> tuple[list[int], list[int], list[str], list[str]]:
        if getattr(chart, "positions", None):
            hd_gates, hd_lines, hd_channels, hd_type = derive_human_design_profile(chart)
            hd_result = build_human_design_result(chart)
            hd_defined_centers = sorted(
                {str(center).strip() for center in hd_result.defined_centers if str(center).strip()},
                key=lambda center_name: (
                    self.HD_DEFINED_CENTER_ORDER.index(center_name)
                    if center_name in self.HD_DEFINED_CENTER_ORDER
                    else len(self.HD_DEFINED_CENTER_ORDER),
                    center_name,
                ),
            )
            chart.human_design_gates = list(hd_gates)
            chart.human_design_lines = list(hd_lines)
            chart.human_design_channels = list(hd_channels)
            chart.human_design_defined_centers = list(hd_defined_centers)
            if hd_type:
                chart.human_design_type = hd_type
            return hd_gates, hd_lines, hd_channels, hd_defined_centers

        hd_gates = [
            int(gate)
            for gate in (getattr(chart, "human_design_gates", []) or [])
            if isinstance(gate, int) and 1 <= int(gate) <= 64
        ]
        hd_lines = [
            int(line)
            for line in (getattr(chart, "human_design_lines", []) or [])
            if isinstance(line, int) and 1 <= int(line) <= 6
        ]
        hd_channels = [
            str(channel)
            for channel in (getattr(chart, "human_design_channels", []) or [])
            if str(channel).strip()
        ]
        hd_defined_centers = [
            str(center)
            for center in (getattr(chart, "human_design_defined_centers", []) or [])
            if str(center).strip()
        ]
        return hd_gates, hd_lines, hd_channels, hd_defined_centers

    @staticmethod
    def _human_design_mode_payload(
        mode: str,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
    ) -> tuple[list[str], dict[str, int], dict[str, int], float, float]:
        if mode == "hd_lines":
            labels = [str(line) for line in range(1, 7)]
            selection_counts = {
                label: int(selection_cache["human_design_line_totals"].get(int(label), 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_line_totals"].get(int(label), 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_line_total_count"]),
                float(database_cache["human_design_line_total_count"]),
            )
        if mode == "hd_channels":
            labels = sorted(
                set(selection_cache["human_design_channel_totals"].keys())
                | set(database_cache["human_design_channel_totals"].keys()),
                key=lambda label: (
                    int(label.split("-")[0]) if "-" in label and label.split("-")[0].isdigit() else 999,
                    int(label.split("-")[1]) if "-" in label and len(label.split("-")) > 1 and label.split("-")[1].isdigit() else 999,
                    label,
                ),
            )
            selection_counts = {
                label: int(selection_cache["human_design_channel_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_channel_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_channel_total_count"]),
                float(database_cache["human_design_channel_total_count"]),
            )
        if mode == "hd_defined_centers":
            labels = list(DatabaseAnalyticsChartsMixin.HD_DEFINED_CENTER_ORDER)
            selection_counts = {
                label: int(selection_cache["human_design_defined_center_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_defined_center_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_defined_center_total_count"]),
                float(database_cache["human_design_defined_center_total_count"]),
            )
        labels = [str(gate) for gate in range(1, 65)]
        selection_counts = {
            label: int(selection_cache["human_design_gate_totals"].get(int(label), 0))
            for label in labels
        }
        database_counts = {
            label: int(database_cache["human_design_gate_totals"].get(int(label), 0))
            for label in labels
        }
        return (
            labels,
            selection_counts,
            database_counts,
            float(selection_cache["human_design_gate_total_count"]),
            float(database_cache["human_design_gate_total_count"]),
        )

     #DB View's Lefthand Panel: Selection Comparison Chart 2: Relationship Distribution Chart
    def _build_relationship_distribution_chart(
        self,
        selection_relationships: dict[str, float],
        database_relationships: dict[str, float],
        selection_relationship_counts: dict[str, float],
        database_relationship_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        relationship_figure = Figure(figsize=(4.8, 5.8))
        relationship_figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        relationship_ax = relationship_figure.add_subplot(111)
        relationship_ax.set_facecolor(CHART_THEME_COLORS["background"])
        relationship_labels = list(RELATION_TYPE)
        relationship_display_labels = [
            self._format_selection_database_count_label(
                relationship,
                database_relationship_counts.get(relationship, 0),
                selection_relationship_counts.get(relationship, 0),
                loaded_charts > 0,
            )
            for relationship in relationship_labels
        ]
        relationship_positions = list(range(len(relationship_labels)))
        relationship_colors = get_cycled_earthtone_colors(len(relationship_labels))
        selection_values = [
            selection_relationships[relationship]
            for relationship in relationship_labels
        ]
        database_values = [
            database_relationships[relationship]
            for relationship in relationship_labels
        ]
        if loaded_charts == 0:
            relationship_bars = relationship_ax.barh(
                relationship_positions,
                database_values,
                color=relationship_colors,
                height=bar_height,
                zorder=2,
            )
            relationship_ax.set_xlim(0, 1)
            relationship_ax.set_yticks(
                relationship_positions,
                labels=relationship_display_labels,
            )
            relationship_ax.invert_yaxis()
            relationship_ax.tick_params(axis="y", **CHART_AXES_STYLE["y_tick"])
            relationship_ax.tick_params(axis="x", **CHART_AXES_STYLE["x_tick"])
            relationship_ax.set_xlabel("")
            relationship_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            relationship_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(relationship_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                relationship_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            widths = [abs(value) for value in differences]
            relationship_bars = relationship_ax.barh(
                relationship_positions,
                widths,
                left=[
                    0 if value >= 0 else -abs(value) for value in differences
                ],
                color=relationship_colors,
                height=bar_height,
                zorder=2,
            )
            relationship_ax.set_xlim(-1, 1)
            relationship_ax.set_yticks(
                relationship_positions,
                labels=relationship_display_labels,
            )
            relationship_ax.invert_yaxis()
            relationship_ax.tick_params(axis="y", **CHART_AXES_STYLE["y_tick"])
            relationship_ax.tick_params(axis="x", **CHART_AXES_STYLE["x_tick"])
            relationship_ax.set_xlabel("")
            relationship_ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            relationship_ax.set_xticklabels(
                [_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]]
            )
            relationship_ax.axvline(
                0,
                color=CHART_THEME_COLORS["spine"],
                linewidth=1.5,
                zorder=1,
            )
            for bar, diff_value in zip(relationship_bars, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = (
                        selection_value if diff_value >= 0 else -selection_value
                    )
                    if label_x >= 0:
                        label_x = min(label_x + 0.02, 0.95)
                    else:
                        label_x = max(label_x - 0.02, -0.95)
                    relationship_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in relationship_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in relationship_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(relationship_figure)
        relationship_figure.subplots_adjust(**CHART_AXES_STYLE["barh_adjust"])

        relationship_canvas = FigureCanvas(relationship_figure)
        self._configure_left_panel_canvas(
            relationship_canvas,
            relationship_figure,
        )
        relationship_canvas.draw_idle()
        return relationship_canvas

    #DB View's Lefthand Panel: Selection Comparison Chart 1: Sentiment Distribution Chart
    def _build_sentiment_chart(
        self,
        display_labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        selection_counts: list[float],
        database_counts: list[float],
        loaded_charts: int,
        positive_labels: list[str],
        negative_labels: list[str],
        positive_total_label: str,
        negative_total_label: str,
    ) -> FigureCanvas:
        # DB View's lefthand panel top graph dimensions
        figure = Figure(figsize=(5.6, 6.8))  # graph dimensions
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])
        positive_total_color = "#39ff14"
        negative_total_color = "#ff1744"
        negative_start_display = len(positive_labels) + 1
        if negative_labels:
            ax.axhspan(
                negative_start_display - 0.5,
                len(display_labels) - 0.5,
                facecolor="#222222",
                zorder=0,
            )

        colors = []
        for label in display_labels:
            if label == positive_total_label:
                colors.append(positive_total_color)
            elif label == negative_total_label:
                colors.append(negative_total_color)
            else:
                colors.append(SENTIMENT_COLORS.get(label, "#6fa8dc"))
        display_labels_with_counts = [
            self._format_selection_database_count_label(
                label,
                database_count,
                selection_count,
                loaded_charts > 0,
            )
            for label, selection_count, database_count in zip(
                display_labels,
                selection_counts,
                database_counts,
            )
        ]
        y_positions = list(range(len(display_labels)))
        bar_height = 0.6  # how tall (or wide for horizontal graphs) are the bars?
        if loaded_charts == 0:
            selection_bars = ax.barh(
                y_positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            self._set_x_limits_with_padding(ax, 0, 1)
            ax.set_yticks(y_positions, labels=display_labels_with_counts)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(selection_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            difference_values = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            difference_widths = [abs(value) for value in difference_values]
            selection_bars = ax.barh(
                y_positions,
                difference_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in difference_values
                ],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            self._set_x_limits_with_padding(ax, -1, 1)
            ax.set_yticks(y_positions, labels=display_labels_with_counts)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            ax.set_xticklabels(
                [_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]]
            )
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, difference_value in zip(selection_bars, difference_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(difference_value)
                    label_x = (
                        selection_value if difference_value >= 0 else -selection_value
                    )
                    if label_x >= 0:
                        label_x = min(label_x + 0.02, 0.95)
                    else:
                        label_x = max(label_x - 0.02, -0.95)
                    ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if difference_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label, label in zip(ax.get_yticklabels(), display_labels):
            tick_label.set_ha("right")
            if label == positive_total_label:
                tick_label.set_color(positive_total_color)
            elif label == negative_total_label:
                tick_label.set_color(negative_total_color)        
        self._apply_tight_layout(figure)
        # DB View's lefthand panel's graph margins.
        # Lower the top bound to reserve space for the title.
        figure.subplots_adjust(left=0.36, bottom=0.12, right=0.97, top=0.96)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas
                
    #DB View's Lefthand Panel: Selection Comparison Chart 2: Sign Distribution Chart
    def _build_sign_distribution_chart(
        self,
        selection_signs: dict[str, float],
        database_signs: dict[str, float],
        selection_sign_counts: dict[str, float],
        database_sign_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        # DB View's lefthand panel graph dimensions (for sign graph)?
        sign_figure = Figure(figsize=(4.8, 5.8))
        sign_figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        sign_ax = sign_figure.add_subplot(111)
        sign_ax.set_facecolor(CHART_THEME_COLORS["background"])
        sign_labels = list(ZODIAC_NAMES)
        sign_display_labels = [
            self._format_selection_database_count_label(
                sign,
                database_sign_counts.get(sign, 0),
                selection_sign_counts.get(sign, 0),
                loaded_charts > 0,
            )
            for sign in sign_labels
        ]
        sign_colors = [SIGN_COLORS.get(sign, "#6fa8dc") for sign in sign_labels]
        sign_positions = list(range(len(sign_labels)))
        selection_sign_values = [selection_signs[sign] for sign in sign_labels]
        database_sign_values = [database_signs[sign] for sign in sign_labels]
        if loaded_charts == 0:
            sign_bars = sign_ax.barh(
                sign_positions,
                database_sign_values,
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            sign_ax.set_xlim(0, 1)
            sign_ax.set_yticks(sign_positions, labels=sign_display_labels)
            sign_ax.invert_yaxis()
            sign_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            sign_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            sign_ax.set_xlabel("")
            sign_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            sign_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(sign_bars, database_sign_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                sign_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            sign_differences = [
                selection - database
                for selection, database in zip(
                    selection_sign_values,
                    database_sign_values,
                )
            ]
            sign_widths = [abs(value) for value in sign_differences]
            sign_bars = sign_ax.barh(
                sign_positions,
                sign_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in sign_differences
                ],
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            sign_ax.set_xlim(-1, 1)
            sign_ax.set_yticks(sign_positions, labels=sign_display_labels)
            sign_ax.invert_yaxis()
            sign_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            sign_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            sign_ax.set_xlabel("")
            sign_ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            sign_ax.set_xticklabels(
                [_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]]
            )
            sign_ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(sign_bars, sign_differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = (
                        selection_value if diff_value >= 0 else -selection_value
                    )
                    if label_x >= 0:
                        label_x = min(label_x + 0.02, 0.95)
                    else:
                        label_x = max(label_x - 0.02, -0.95)
                    sign_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in sign_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in sign_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(sign_figure)
        sign_figure.subplots_adjust(left=0.36, bottom=0.12, right=0.97, top=0.96)

        sign_canvas = FigureCanvas(sign_figure)
        self._configure_left_panel_canvas(sign_canvas, sign_figure)
        sign_canvas.draw_idle()
        return sign_canvas

    #DB View's Lefthand Panel: Selection Comparison Chart 3: Dominant Sign Chart
    def _build_dominant_sign_chart(
        self,
        selection_signs: dict[str, float],
        database_signs: dict[str, float],
        selection_sign_counts: dict[str, float],
        database_sign_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
        sign_labels: list[str] | None = None,
    ) -> FigureCanvas:
        dominant_figure = Figure(figsize=(4.8, 5.8))
        dominant_figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        dominant_ax = dominant_figure.add_subplot(111)
        dominant_ax.set_facecolor(CHART_THEME_COLORS["background"])
        sign_labels = list(sign_labels or ZODIAC_NAMES)
        sign_display_labels = [
            self._format_selection_database_count_label(
                sign,
                database_sign_counts.get(sign, 0),
                selection_sign_counts.get(sign, 0),
                loaded_charts > 0,
            )
            for sign in sign_labels
        ]
        sign_colors = [SIGN_COLORS.get(sign, "#6fa8dc") for sign in sign_labels]
        sign_positions = list(range(len(sign_labels)))
        selection_sign_values = [selection_signs[sign] for sign in sign_labels]
        database_sign_values = [database_signs[sign] for sign in sign_labels]
        if loaded_charts == 0:
            sign_bars = dominant_ax.barh(
                sign_positions,
                database_sign_values,
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            dominant_ax.set_xlim(0, 1)
            dominant_ax.set_yticks(sign_positions, labels=sign_display_labels)
            dominant_ax.invert_yaxis()
            dominant_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            dominant_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            dominant_ax.set_xlabel("")
            dominant_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            dominant_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(sign_bars, database_sign_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                dominant_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            sign_differences = [
                selection - database
                for selection, database in zip(
                    selection_sign_values,
                    database_sign_values,
                )
            ]
            sign_widths = [abs(value) for value in sign_differences]
            sign_bars = dominant_ax.barh(
                sign_positions,
                sign_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in sign_differences
                ],
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            dominant_ax.set_xlim(-1, 1)
            dominant_ax.set_yticks(sign_positions, labels=sign_display_labels)
            dominant_ax.invert_yaxis()
            dominant_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            dominant_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            dominant_ax.set_xlabel("")
            dominant_ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            dominant_ax.set_xticklabels(
                [_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]]
            )
            dominant_ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(sign_bars, sign_differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = (
                        selection_value if diff_value >= 0 else -selection_value
                    )
                    if label_x >= 0:
                        label_x = min(label_x + 0.02, 0.95)
                    else:
                        label_x = max(label_x - 0.02, -0.95)
                    dominant_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in dominant_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in dominant_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(dominant_figure)
        dominant_figure.subplots_adjust(left=0.36, bottom=0.12, right=0.97, top=0.96)

        dominant_canvas = FigureCanvas(dominant_figure)
        self._configure_left_panel_canvas(dominant_canvas, dominant_figure)
        dominant_canvas.draw_idle()
        return dominant_canvas

    def _build_dominant_planet_chart(
        self,
        selection_planets: dict[str, float],
        database_planets: dict[str, float],
        selection_planet_counts: dict[str, float],
        database_planet_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
        labels: list[str] | None = None,
        height_scale: float = 1.0,
    ) -> FigureCanvas:
        clamped_height_scale = max(0.5, float(height_scale))
        figure = Figure(figsize=(4.8, 5.8 * clamped_height_scale))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])
        labels = list(labels or selection_planets.keys())
        display_labels = [
            self._format_selection_database_count_label(
                label,
                database_planet_counts.get(label, 0),
                selection_planet_counts.get(label, 0),
                loaded_charts > 0,
            )
            for label in labels
        ]
        def _resolve_distribution_color(label: str) -> str:
            if label in DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS:
                return DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS[label]
            return PLANET_COLORS.get(
                label,
                HOUSE_COLORS.get(
                    label,
                    ELEMENT_COLORS.get(
                        label,
                        NAKSHATRA_PLANET_COLOR.get(label, (None, "#6fa8dc"))[1],
                    ),
                ),
            )
        colors = [_resolve_distribution_color(label) for label in labels]
        positions = list(range(len(labels)))
        selection_values = [selection_planets[label] for label in labels]
        database_values = [database_planets[label] for label in labels]
        if loaded_charts == 0:
            bars = ax.barh(positions, database_values, color=colors, height=bar_height, zorder=2)
            ax.set_xlim(0, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels([_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]])
            for bar, database_value in zip(bars, database_values):
                ax.text(min(database_value + 0.02, 0.95), bar.get_y() + (bar.get_height() / 2), _format_percent(database_value), va="center", ha="left", color=CHART_THEME_COLORS["text"], fontsize=7.5)
        else:
            differences = [selection - database for selection, database in zip(selection_values, database_values)]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            ax.set_xlim(-1, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            ax.set_xticklabels([_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]])
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(bars, differences):
                width = bar.get_width()
                if width <= 0:
                    continue
                label_x = width if diff_value >= 0 else -width
                label_x = min(label_x + 0.02, 0.95) if label_x >= 0 else max(label_x - 0.02, -0.95)
                ax.text(label_x, bar.get_y() + (bar.get_height() / 2), _format_percent(abs(diff_value)), va="center", ha="left" if diff_value >= 0 else "right", color=CHART_THEME_COLORS["text"], fontsize=7.5)

        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.36, bottom=0.12, right=0.97, top=0.96)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dominant_house_chart(
        self,
        selection_houses: dict[str, float],
        database_houses: dict[str, float],
        selection_house_counts: dict[str, float],
        database_house_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
        labels: list[str] | None = None,
    ) -> FigureCanvas:
        return self._build_dominant_planet_chart(
            selection_planets=selection_houses,
            database_planets=database_houses,
            selection_planet_counts=selection_house_counts,
            database_planet_counts=database_house_counts,
            loaded_charts=loaded_charts,
            bar_height=bar_height,
            labels=labels,
        )

    def _build_gender_distribution_chart(
        self,
        labels: list[str],
        selection_values: dict[str, float],
        database_values: dict[str, float],
        selection_counts: dict[str, int],
        database_counts: dict[str, int],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, max(2.8, min(8.0, (len(labels) * 0.42) + 0.8))))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])

        color_by_label = {
            "masculine": GENDER_GUESSER_COLORS["masculine"],
            "feminine": GENDER_GUESSER_COLORS["feminine"],
            "androgynous": GENDER_GUESSER_COLORS["androgynous"],
            "m": GENDER_GUESSER_COLORS["masculine"],
            "f": GENDER_GUESSER_COLORS["feminine"],
            "n/a": GENDER_GUESSER_COLORS["androgynous"],
        }
        display_labels = [
            self._format_selection_database_count_label(
                label,
                database_counts.get(label, 0),
                selection_counts.get(label, 0),
                loaded_charts > 0,
            )
            for label in labels
        ]
        colors = [
            color_by_label.get(
                str(label).strip().casefold(),
                "#6fa8dc",  # keep unknown labels such as "?" on default blue
            )
            for label in labels
        ]
        positions = list(range(len(labels)))
        selection_plot_values = [float(selection_values.get(label, 0.0)) for label in labels]
        database_plot_values = [float(database_values.get(label, 0.0)) for label in labels]

        if loaded_charts == 0:
            bars = ax.barh(positions, database_plot_values, color=colors, height=bar_height, zorder=2)
            ax.set_xlim(0, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels([_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]])
            for bar, database_value in zip(bars, database_plot_values):
                ax.text(
                    min(database_value + 0.02, 0.95),
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [selection - database for selection, database in zip(selection_plot_values, database_plot_values)]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            ax.set_xlim(-1, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
            ax.set_xticklabels([_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]])
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(bars, differences):
                width = bar.get_width()
                if width <= 0:
                    continue
                label_x = width if diff_value >= 0 else -width
                label_x = min(label_x + 0.02, 0.95) if label_x >= 0 else max(label_x - 0.02, -0.95)
                ax.text(
                    label_x,
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(abs(diff_value)),
                    va="center",
                    ha="left" if diff_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )

        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.36, bottom=0.12, right=0.97, top=0.96)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dominant_element_chart(
        self,
        selection_elements: dict[str, float],
        database_elements: dict[str, float],
        selection_element_counts: dict[str, float],
        database_element_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        return self._build_dominant_planet_chart(
            selection_planets=selection_elements,
            database_planets=database_elements,
            selection_planet_counts=selection_element_counts,
            database_planet_counts=database_element_counts,
            loaded_charts=loaded_charts,
            bar_height=bar_height,
        )

    def _build_species_distribution_chart(
        self,
        selection_species: dict[str, float],
        database_species: dict[str, float],
        selection_species_counts: dict[str, float],
        database_species_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.32,
        show_x_axis_labels: bool = False,
    ) -> FigureCanvas:
        labels = list(selection_species.keys())
        # Keep D&D species and class distributions visually consistent and compact
        # so the full graph remains visible above the fold.
        chart_height = 4.9
        figure = Figure(figsize=(4.8, chart_height))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])
        display_labels = [
            self._format_selection_database_count_label(
                species,
                database_species_counts.get(species, 0),
                selection_species_counts.get(species, 0),
                loaded_charts > 0,
            )
            for species in labels
        ]
        positions = list(range(len(labels)))
        colors = get_cycled_earthtone_colors(len(labels))
        selection_values = [selection_species[species] for species in labels]
        database_values = [database_species[species] for species in labels]
        if loaded_charts == 0:
            species_bars = ax.barh(
                positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            ax.set_xlim(0, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            if show_x_axis_labels:
                ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            else:
                ax.tick_params(axis="x", length=0, labelbottom=False)
            ax.set_xlabel("")
            if show_x_axis_labels:
                ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
                ax.set_xticklabels(
                    [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
                )
            for bar, database_value in zip(species_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            widths = [abs(value) for value in differences]
            species_bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            ax.set_xlim(-1, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            if show_x_axis_labels:
                ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            else:
                ax.tick_params(axis="x", length=0, labelbottom=False)
            ax.set_xlabel("")
            if show_x_axis_labels:
                ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
                ax.set_xticklabels(
                    [_format_percent(value) for value in [-1.0, -0.5, 0, 0.5, 1.0]]
                )
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(species_bars, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = selection_value if diff_value >= 0 else -selection_value
                    if label_x >= 0:
                        label_x = min(label_x + 0.02, 0.95)
                    else:
                        label_x = max(label_x - 0.02, -0.95)
                    ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.36, bottom=0.06, right=0.97, top=0.98)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_social_score_summary_chart(
        self,
        labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        loaded_charts: int,
        social_score_min: float | None = None,
        social_score_max: float | None = None,
        bar_height: float = 0.6,
        color_resolver: Any = None,
        fixed_axis_limit: float | None = None,
        value_precision: int = 2,
        figure_height: float = 2.8,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, figure_height))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])
        def _resolve_bar_color(label: str, value: float) -> Any:
            if callable(color_resolver):
                try:
                    return color_resolver(label, value)
                except TypeError:
                    # Backward compatibility for resolver callbacks that only
                    # accept the numeric value (e.g., alignment_score_to_rgb).
                    return color_resolver(value)
            return "#6fa8dc"

        def _is_percent_metric(metric_label: str) -> bool:
            return "(%)" in metric_label

        def _format_metric_value(metric_label: str, value: float, *, signed: bool = False) -> str:
            if _is_percent_metric(metric_label):
                return f"{value:+.{value_precision}f}%" if signed else f"{value:.{value_precision}f}%"
            return f"{value:+.{value_precision}f}" if signed else f"{value:.{value_precision}f}"

        display_labels = []
        for label, selection_value in zip(labels, selection_values):
            if loaded_charts > 0:
                display_labels.append(
                    f"({_format_metric_value(label, selection_value)}) {label}"
                )
            else:
                display_labels.append(label)

        positions = list(range(len(labels)))
        range_min = float(social_score_min) if social_score_min is not None else None
        range_max = float(social_score_max) if social_score_max is not None else None

        def _resolve_social_color(label: str, value: float) -> Any:
            if range_min is None or range_max is None:
                return _resolve_bar_color(label, value)
            return value_to_red_blue_rgb(value, range_min, range_max)

        if loaded_charts == 0:
            colors = [
                _resolve_social_color(label, value)
                for label, value in zip(labels, database_values)
            ]
            bars = ax.barh(
                positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            if fixed_axis_limit is not None:
                limit = float(fixed_axis_limit)
                lower_bound = -limit
                upper_bound = limit
                ax.set_xlim(-limit, limit)
            elif range_min is not None and range_max is not None:
                limit = max(abs(range_min), abs(range_max), 1.0)
                lower_bound = -limit
                upper_bound = limit
                ax.set_xlim(-limit, limit)
            else:
                lower_bound = min(0.0, min(database_values, default=0.0))
                upper_bound = max(0.0, max(database_values, default=0.0))
                self._set_x_limits_with_padding(ax, lower_bound, upper_bound)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            if lower_bound < 0 < upper_bound:
                ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, label, database_value in zip(bars, labels, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = database_value + (0.6 if database_value >= 0 else -0.6)
                ax.text(
                    label_x,
                    bar_center,
                    _format_metric_value(label, database_value),
                    va="center",
                    ha="left" if database_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            colors = [
                _resolve_social_color(label, value)
                for label, value in zip(labels, selection_values)
            ]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            max_abs_difference = max(1.0, max((abs(value) for value in differences), default=0.0))
            if fixed_axis_limit is not None:
                max_abs_difference = max(max_abs_difference, float(fixed_axis_limit))
                ax.set_xlim(-float(fixed_axis_limit), float(fixed_axis_limit))
            elif range_min is not None and range_max is not None:
                range_limit = max(abs(range_min), abs(range_max), 1.0)
                max_abs_difference = max(max_abs_difference, range_limit)
                ax.set_xlim(-range_limit, range_limit)
            else:
                self._set_x_limits_with_padding(ax, -max_abs_difference, max_abs_difference)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, label, difference in zip(bars, labels, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                width = bar.get_width()
                if width > 0:
                    label_x = width if difference >= 0 else -width
                    offset = max_abs_difference * 0.03
                    if label_x >= 0:
                        label_x += offset
                    else:
                        label_x -= offset
                    ax.text(
                        label_x,
                        bar_center,
                        _format_metric_value(label, difference, signed=True),
                        va="center",
                        ha="left" if difference >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        # Manual margins are explicitly set for this chart; skip tight_layout to avoid
        # benign "cannot be made large enough" warnings with long axis labels.
        figure.subplots_adjust(left=0.36, bottom=0.16, right=0.97, top=0.95)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dnd_statblock_summary_chart(
        self,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
        loaded_charts: int,
    ) -> FigureCanvas:
        labels = list(self.DND_STAT_KEYS)
        dnd_stat_colors = get_cycled_earthtone_colors(len(labels))
        stat_color_lookup = {
            label: dnd_stat_colors[index]
            for index, label in enumerate(labels)
        }
        selection_values_map = self._compute_dnd_statblock_averages(selection_cache)
        database_values_map = self._compute_dnd_statblock_averages(database_cache)
        selection_values = [selection_values_map[label] for label in labels]
        database_values = [database_values_map[label] for label in labels]
        return self._build_social_score_summary_chart(
            labels=labels,
            selection_values=selection_values,
            database_values=database_values,
            loaded_charts=loaded_charts,
            color_resolver=lambda label, _value: stat_color_lookup.get(
                label,
                DND_STAT_EARTHTONE_COLORS.get(label, "#6fa8dc"),
            ),
            fixed_axis_limit=20.0,
            value_precision=0,
        )

    def _compute_dnd_statblock_averages(
        self,
        metric_cache: dict[str, Any],
    ) -> dict[str, float]:
        labels = list(self.DND_STAT_KEYS)
        stat_count = float(metric_cache.get("dnd_stat_count", 0))
        stat_totals = metric_cache.get("dnd_stat_totals", {})
        return {
            label: (
                float(stat_totals.get(label, 0.0)) / stat_count
                if stat_count
                else 0.0
            )
            for label in labels
        }

    def _build_alignment_cumulative_chart(
        self,
        selection_cumulative: float,
        selection_average: float,
        database_average: float,
        loaded_charts: int,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, 1.6))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])

        ax.hlines(
            y=0,
            xmin=-10,
            xmax=10,
            color=CHART_THEME_COLORS["spine"],
            linewidth=6,
            zorder=1,
            alpha=0.6,
        )
        ax.hlines(y=0, xmin=-10, xmax=0, color="#c62828", linewidth=4, zorder=2, alpha=0.85)
        ax.hlines(y=0, xmin=0, xmax=10, color="#1565c0", linewidth=4, zorder=2, alpha=0.85)
        ax.vlines(0, -0.3, 0.3, color=CHART_THEME_COLORS["text"], linewidth=1.0, zorder=3)

        db_avg_clamped = max(-10.0, min(10.0, float(database_average)))
        ax.scatter(
            [db_avg_clamped],
            [0],
            marker="|",
            s=260,
            linewidths=2.0,
            color="#f4d35e",
            zorder=4,
        )

        if loaded_charts > 0:
            selection_avg_clamped = max(-10.0, min(10.0, float(selection_average)))
            ax.scatter(
                [selection_avg_clamped],
                [0],
                marker="o",
                s=44,
                color="#6fa8dc",
                edgecolors=CHART_THEME_COLORS["text"],
                linewidths=0.8,
                zorder=5,
            )
            subtitle = (
                f"Selection Total: {selection_cumulative:+.1f} | "
                f"Selection Avg: {selection_average:+.2f} | "
                f"DB Avg: {database_average:+.2f}"
            )
        else:
            subtitle = f"DB Avg Alignment: {database_average:+.2f}"

        subtitle = textwrap.fill(
            subtitle,
            width=ALIGNMENT_CUMULATIVE_SUBTITLE_WRAP_WIDTH,
            break_long_words=False,
        )

        ax.text(
            0.5,
            -0.48,
            subtitle,
            ha="center",
            va="top",
            transform=ax.transAxes,
            color=CHART_THEME_COLORS["text"],
            fontsize=7.5,
            wrap=True,
            clip_on=False,
        )

        ax.set_xlim(-10.7, 10.7)
        ax.set_ylim(-0.45, 0.8)
        ax.set_yticks([])
        ax.set_xticks([-10, -5, 0, 5, 10])
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        for spine in ax.spines.values():
            spine.set_visible(False)

        figure.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.34)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    @staticmethod
    def _minutes_to_label(total_minutes: float) -> str:
        minutes = int(round(total_minutes)) % (24 * 60)
        hours, mins = divmod(minutes, 60)
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def _extract_birthplace_components(raw_place: str) -> tuple[str | None, str | None, str | None]:
        parts = [part.strip() for part in (raw_place or "").split(",") if part.strip()]
        if not parts:
            return None, None, None
        city = parts[0] if parts else None
        state = parts[-2] if len(parts) >= 2 else None
        country = parts[-1] if len(parts) >= 2 else None
        if len(parts) == 1:
            country = None
            state = None
        return city, state, country

    @staticmethod
    def _bucket_age_value(age_value: int) -> str | None:
        for label, min_age, max_age in AGE_BRACKETS:
            if min_age is None:
                continue
            if age_value < min_age:
                continue
            if max_age is None or age_value < max_age:
                return label
        return None

    def _collect_age_analytics(self, chart_ids: list[int] | set[int]) -> dict[str, Any]:
        now_year = datetime.datetime.now(datetime.timezone.utc).year
        age_counts: Counter[int] = Counter()
        known_duration_counts: Counter[int] = Counter()
        age_bracket_counts: Counter[str] = Counter()

        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue
            if bool(getattr(chart, "is_placeholder", False)):
                continue

            birth_year_value = getattr(chart, "birth_year", None)
            if not isinstance(birth_year_value, int):
                dt_value = getattr(chart, "dt", None)
                if isinstance(dt_value, datetime.datetime):
                    birth_year_value = int(dt_value.year)
            if isinstance(birth_year_value, int):
                age_value = int(math.floor(now_year - int(birth_year_value)))
                if age_value >= 0:
                    age_counts[age_value] += 1
                    age_bracket = self._bucket_age_value(age_value)
                    if age_bracket is not None:
                        age_bracket_counts[age_bracket] += 1

            year_first_encountered = getattr(chart, "year_first_encountered", None)
            if isinstance(year_first_encountered, int):
                known_duration = now_year - int(year_first_encountered)
                if known_duration >= 0:
                    known_duration_counts[known_duration] += 1

        return {
            "age_counts": dict(age_counts),
            "age_bracket_counts": dict(age_bracket_counts),
            "known_duration_counts": dict(known_duration_counts),
        }

    def _collect_birth_analytics(self, chart_ids: list[int] | set[int]) -> dict[str, Any]:
        birth_minutes: list[int] = []
        birth_month_counts: Counter[int] = Counter()
        birth_date_counts: Counter[str] = Counter()
        city_counts: Counter[str] = Counter()
        country_counts: Counter[str] = Counter()
        us_state_counts: Counter[str] = Counter()

        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue

            dt_value = getattr(chart, "dt", None)
            has_known_time = (not bool(getattr(chart, "birthtime_unknown", False))) or bool(
                getattr(chart, "retcon_time_used", False)
            )
            if isinstance(dt_value, datetime.datetime) and has_known_time:
                birth_minutes.append((int(dt_value.hour) * 60) + int(dt_value.minute))

            is_placeholder = bool(getattr(chart, "is_placeholder", False))
            month_value = getattr(chart, "birth_month", None)
            day_value = getattr(chart, "birth_day", None)
            if (
                not is_placeholder
                and not isinstance(month_value, int)
                and isinstance(dt_value, datetime.datetime)
            ):
                month_value = int(dt_value.month)
            if (
                not is_placeholder
                and not isinstance(day_value, int)
                and isinstance(dt_value, datetime.datetime)
            ):
                day_value = int(dt_value.day)
            if isinstance(month_value, int) and 1 <= month_value <= 12:
                birth_month_counts[month_value] += 1
                if isinstance(day_value, int) and 1 <= day_value <= 31:
                    birth_date_counts[f"{month_value:02d}-{day_value:02d}"] += 1

            birthplace = str(getattr(chart, "birth_place", "") or "").strip()
            city, state, country = self._extract_birthplace_components(birthplace)
            canonical_city = normalize_city(city or "", country)
            if canonical_city:
                city_counts[canonical_city] += 1

            if country:
                canonical_country = normalize_country(country)
                if canonical_country:
                    country_counts[canonical_country] += 1

                resolved_country = resolve_country(country)
                if resolved_country and resolved_country.get("alpha_2") == "US":
                    canonical_state = normalize_us_state(state or birthplace)
                    if canonical_state:
                        us_state_counts[canonical_state] += 1

        mode_minutes = 0
        if birth_minutes:
            rounded_hours = [((minute + 30) // 60) % 24 for minute in birth_minutes]
            mode_hour = Counter(rounded_hours).most_common(1)[0][0]
            mode_minutes = mode_hour * 60

        return {
            "birth_minutes": birth_minutes,
            "mean_minutes": (sum(birth_minutes) / len(birth_minutes)) if birth_minutes else 0.0,
            "median_minutes": float(statistics.median(birth_minutes)) if birth_minutes else 0.0,
            "mode_hour_minutes": float(mode_minutes),
            "birth_month_counts": dict(birth_month_counts),
            "birth_date_counts": dict(birth_date_counts),
            "city_counts": dict(city_counts),
            "country_counts": dict(country_counts),
            "us_state_counts": dict(us_state_counts),
        }

    @staticmethod
    def _format_partial_birth_date(
        month_value: int | None,
        day_value: int | None,
        year_value: int | None,
    ) -> str:
        month_label = f"{month_value:02d}" if isinstance(month_value, int) and 1 <= month_value <= 12 else "?"
        day_label = f"{day_value:02d}" if isinstance(day_value, int) and 1 <= day_value <= 31 else "?"
        year_label = f"{year_value:04d}" if isinstance(year_value, int) and year_value > 0 else "?"
        return f"{month_label}.{day_label}.{year_label}"

    def _build_single_metric_chart(
        self,
        label: str,
        selection_value: float,
        database_value: float,
        loaded_charts: int,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, 1.8))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])

        display_value = selection_value if loaded_charts else database_value
        labels = [f"({self._minutes_to_label(display_value)}) {label}"]
        positions = [0]
        bars = ax.barh(positions, [display_value], color="#6fa8dc", height=0.55)
        ax.set_xlim(0, 24 * 60)
        ax.set_yticks(positions, labels=labels)
        ax.tick_params(axis="y", labelsize=8, colors=CHART_THEME_COLORS["text"], pad=6)
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        ax.set_xticks([0, 360, 720, 1080, 1439])
        ax.set_xticklabels(["00:00", "06:00", "12:00", "18:00", "23:59"])
        ax.set_xlabel("")
        for bar in bars:
            value = bar.get_width()
            ax.text(
                min(value + 20, (24 * 60) - 4),
                bar.get_y() + (bar.get_height() / 2),
                self._minutes_to_label(value),
                va="center",
                ha="left" if value < (24 * 60) - 40 else "right",
                color=CHART_THEME_COLORS["text"],
                fontsize=7.5,
            )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")

        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.30, bottom=0.24, right=0.97, top=0.9)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_count_distribution_chart(
        self,
        labels: list[str],
        selection_counts: list[int],
        database_counts: list[int],
        loaded_charts: int,
        auto_height: bool = False,
        use_earthtone_cycle: bool = False,
        bar_colors: list[str] | None = None,
    ) -> FigureCanvas:
        chart_height = max(2.8, min(12.0, (len(labels) * 0.32) + 0.8)) if auto_height else 2.8
        figure = Figure(figsize=(4.8, chart_height))
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])

        values = selection_counts if loaded_charts else database_counts
        display_labels = [f"({value}) {label}" for label, value in zip(labels, values)]
        positions = list(range(len(labels)))
        colors = (
            list(bar_colors)
            if bar_colors is not None
            else (
                get_cycled_earthtone_colors(len(labels))
                if use_earthtone_cycle
                else ["#6fa8dc" for _ in labels]
            )
        )
        bars = ax.barh(positions, values, color=colors, height=0.55, zorder=2)
        max_value = max(values, default=0)
        self._set_x_limits_with_padding(ax, 0.0, float(max(1, max_value)))
        ax.set_yticks(positions, labels=display_labels)
        ax.invert_yaxis()
        ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        ax.set_xlabel("")
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_width() + 0.06,
                bar.get_y() + (bar.get_height() / 2),
                str(value),
                va="center",
                ha="left",
                color=CHART_THEME_COLORS["text"],
                fontsize=7.5,
            )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")

        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.36, bottom=0.10, right=0.97, top=0.97)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas
