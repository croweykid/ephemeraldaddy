"""Aspect-distribution popout adapters shared by chart feature windows."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QWidget

from ephemeraldaddy.gui.features.charts.aspect_weight_graphs import (
    build_popout_left_panel as _build_popout_left_panel,
    collect_aspect_category_totals,
    collect_aspect_type_counts,
    draw_popout_aspect_distribution_chart as _draw_popout_aspect_distribution_chart,
    extract_aspect_weight,
    normalize_aspect_type,
)
from ephemeraldaddy.gui.features.charts.chart_data_output import ChartSummaryHighlighter
from ephemeraldaddy.gui.features.charts.exporters import export_aspect_distribution_csv_dialog
from ephemeraldaddy.gui.style import (
    CHART_DATA_INFO_LABEL_STYLE,
    CHART_THEME_COLORS,
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
)

if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart


def draw_popout_aspect_distribution_chart(
    analytics_ax: Any,
    *,
    mode: str,
    aspect_counts: OrderedDict[str, float],
    weighted_aspect_counts: OrderedDict[str, float],
    type_totals: OrderedDict[str, float],
    weighted_type_totals: OrderedDict[str, float],
    friction_totals: OrderedDict[str, float],
    weighted_friction_totals: OrderedDict[str, float],
) -> None:
    """Draw the standard app-themed popout aspect-distribution chart."""
    _draw_popout_aspect_distribution_chart(
        analytics_ax,
        mode=mode,
        aspect_counts=aspect_counts,
        weighted_aspect_counts=weighted_aspect_counts,
        type_totals=type_totals,
        weighted_type_totals=weighted_type_totals,
        friction_totals=friction_totals,
        weighted_friction_totals=weighted_friction_totals,
        chart_theme_colors=CHART_THEME_COLORS,
    )


def build_popout_left_panel(
    layout: QHBoxLayout,
    *,
    parent: QWidget,
    chart_info_placeholder: str,
    aspect_entries: list[Any],
    export_file_stem: str,
    get_share_icon_path: Callable[[], str | None],
    weighted_score_for_entry: Callable[[Any], float] | None = None,
    aspect_subheader: str | None = None,
    show_aspect_distribution: bool = True,
    awareness_stream_entries: list[dict[str, Any]] | None = None,
    circuit_entries: list[dict[str, Any]] | None = None,
    hd_placement_contexts: list[tuple[str, "Chart"]] | None = None,
) -> QPlainTextEdit:
    """Build the shared chart-data/aspect-distribution left panel."""
    return _build_popout_left_panel(
        layout,
        chart_info_placeholder=chart_info_placeholder,
        aspect_entries=aspect_entries,
        export_file_stem=export_file_stem,
        weighted_score_for_entry=weighted_score_for_entry,
        aspect_subheader=aspect_subheader,
        parent=parent,
        chart_summary_highlighter_cls=ChartSummaryHighlighter,
        export_aspect_distribution_csv_dialog=export_aspect_distribution_csv_dialog,
        get_share_icon_path=get_share_icon_path,
        chart_data_info_label_style=CHART_DATA_INFO_LABEL_STYLE,
        database_analytics_dropdown_style=DATABASE_ANALYTICS_DROPDOWN_STYLE,
        chart_theme_colors=CHART_THEME_COLORS,
        show_aspect_distribution=show_aspect_distribution,
        awareness_stream_entries=awareness_stream_entries,
        circuit_entries=circuit_entries,
        hd_placement_contexts=hd_placement_contexts,
    )
