"""Human Design popout right-panel analytics UI helpers."""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.human_design_system import HumanDesignResult
from ephemeraldaddy.analysis.human_design_reference import (
    HD_COLORS,
    HD_LINE_COLORS,
    HD_TONES,
    LINE_NICKNAMES,
)
from ephemeraldaddy.gui.style import (
    COLLAPSIBLE_SECTION_CONTENT_STYLE,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    configure_collapsible_header_toggle,
)

HD_ANALYTICS_SCROLL_MIN_WIDTH = 340
HD_ANALYTICS_CONTAINER_MIN_WIDTH = 320
HD_ANALYTICS_EXPANDED_WIDTH = 400

def _theme_color(theme: dict[str, str], key: str, fallback: str) -> str:
    value = str(theme.get(key, "") or "").strip()
    return value or fallback


def _normalize_matplotlib_hex(color_value: str, fallback: str) -> str:
    color_text = str(color_value or "").strip()
    if not color_text:
        return fallback
    if color_text.startswith("#"):
        return color_text
    if len(color_text) in {3, 6} and all(char in "0123456789abcdefABCDEF" for char in color_text):
        return f"#{color_text}"
    return color_text


def _color_name_to_hex(color_name: str) -> str:
    color_lookup = {
        "red": "#ff4d4d",
        "orange": "#ff9f1c",
        "yellow": "#ffd60a",
        "green": "#5dc26a",
        "blue": "#4f8cff",
        "violet": "#b388ff",
    }
    return color_lookup.get(str(color_name or "").strip().lower(), "#6fa8dc")


def _hd_meta_by_value(entries: object) -> dict[int, dict[str, object]]:
    """Normalize HD reference data into {value: metadata} for dict/list inputs."""
    if isinstance(entries, dict):
        normalized: dict[int, dict[str, object]] = {}
        for raw_key, raw_entry in entries.items():
            if not isinstance(raw_entry, dict):
                continue
            try:
                key = int(raw_key)
            except (TypeError, ValueError):
                continue
            normalized[key] = raw_entry
        return normalized

    normalized = {}
    if isinstance(entries, (list, tuple)):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            raw_value = raw_entry.get("value")
            try:
                key = int(raw_value)
            except (TypeError, ValueError):
                continue
            normalized[key] = raw_entry
    return normalized

def build_human_design_analytics_panel(
    *,
    hd_result: HumanDesignResult,
    chart_theme_colors: dict[str, str],
    subheader_style: str,
    on_metric_selected: Callable[[str, int], None] | None = None,
) -> QWidget:
    """Build the Human Design popout right-side analytics panel widget."""

    hd_analytics_container = QWidget()
    hd_analytics_container.setObjectName("hd_popout_analytics_container")
    hd_analytics_container_layout = QHBoxLayout(hd_analytics_container)
    hd_analytics_container_layout.setContentsMargins(0, 0, 0, 0)
    hd_analytics_container_layout.setSpacing(0)

    hd_analytics_toggle = QToolButton()
    hd_analytics_toggle.setCheckable(True)
    hd_analytics_toggle.setChecked(True)
    hd_analytics_toggle.setAutoRaise(True)
    hd_analytics_toggle.setArrowType(Qt.LeftArrow)
    hd_analytics_toggle.setCursor(Qt.PointingHandCursor)
    hd_analytics_toggle.setToolTip("Collapse HD analytics panel")
    hd_analytics_toggle.setStyleSheet(
        "QToolButton { border: none; color: #B8860B; padding: 4px 2px; background: transparent; }"
        "QToolButton:hover { color: #FFD700; }"
    )
    hd_analytics_toggle.setFixedWidth(16)
    hd_analytics_container_layout.addWidget(hd_analytics_toggle, 0, Qt.AlignTop)

    hd_analytics_content = QWidget()
    hd_analytics_content_layout = QVBoxLayout(hd_analytics_content)
    hd_analytics_content_layout.setContentsMargins(6, 0, 0, 0)
    hd_analytics_content_layout.setSpacing(6)

    hd_analytics_scroll = QScrollArea()
    hd_analytics_scroll.setWidgetResizable(True)
    hd_analytics_scroll.setFrameShape(QScrollArea.NoFrame)
    hd_analytics_scroll.setMinimumWidth(HD_ANALYTICS_SCROLL_MIN_WIDTH)
    hd_analytics_scroll.setStyleSheet(
        "QScrollArea { background: transparent; border: none; }"
        "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }"
        "QScrollBar::handle:vertical { background: #666666; min-height: 20px; border-radius: 4px; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
    )

    def _add_local_collapsible_section(
        panel: QWidget,
        layout: QVBoxLayout,
        title: str,
        *,
        expanded: bool = True,
    ) -> QVBoxLayout:
        section = QWidget(panel)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)

        toggle = QToolButton(section)
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
        )

        content = QWidget(section)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 6, 8, 8)
        content_layout.setSpacing(6)
        content.setStyleSheet(COLLAPSIBLE_SECTION_CONTENT_STYLE)
        content.setVisible(expanded)

        def _toggle_content(checked: bool) -> None:
            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

        toggle.toggled.connect(_toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        layout.addWidget(section)
        return content_layout

    hd_analytics_panel = QWidget()
    hd_analytics_layout = QVBoxLayout(hd_analytics_panel)
    hd_analytics_layout.setContentsMargins(0, 0, 0, 0)
    hd_analytics_layout.setSpacing(6)

    line_section_layout = _add_local_collapsible_section(
        hd_analytics_panel,
        hd_analytics_layout,
        "Line Distribution",
        expanded=True,
    )

    hd_line_summary = QLabel("Line Distribution (Personality + Design activations)")
    hd_line_summary.setWordWrap(True)
    hd_line_summary.setStyleSheet(subheader_style)
    line_section_layout.addWidget(hd_line_summary)

    line_counts = {line: 0 for line in range(1, 7)}
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        if 1 <= int(activation.line) <= 6:
            line_counts[int(activation.line)] += 1

    hd_line_chart_figure = Figure(figsize=(2.6, 2.6))
    hd_line_chart_canvas = FigureCanvas(hd_line_chart_figure)
    hd_line_chart_ax = hd_line_chart_figure.add_subplot(111)
    
    hd_line_chart_figure.patch.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    hd_line_chart_ax.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))

    line_numbers = list(range(1, 7))
    line_values = [line_counts.get(line_number, 0) for line_number in line_numbers]
    line_colors = [
        _normalize_matplotlib_hex(HD_LINE_COLORS.get(line_number, "#5dc26a"), "#5dc26a")
        for line_number in line_numbers
    ]
    bars = hd_line_chart_ax.bar(
        line_numbers,
        line_values,
        color=line_colors,
        edgecolor="#E0E0E0",
        linewidth=0.5,
        alpha=0.95,
    )
    hd_line_chart_ax.set_xticks(line_numbers)
    line_labels = [
        f"L{line_number} ({str(LINE_NICKNAMES.get(line_number, {}).get('name', 'unknown'))})"
        for line_number in line_numbers
    ]
    hd_line_chart_ax.set_xticklabels(
        line_labels,
        color=_theme_color(chart_theme_colors, "text", "#f0f0f0"),
        rotation=45,
        ha="right",
    )
    hd_line_chart_ax.tick_params(axis="y", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    hd_line_chart_ax.tick_params(axis="x", labelsize=8)
    hd_line_chart_ax.set_ylim(0, max(1, max(line_values) + 1))
    hd_line_chart_ax.grid(axis="y", color=_theme_color(chart_theme_colors, "line", "#666666"), linewidth=0.6, alpha=0.4)
    for spine in hd_line_chart_ax.spines.values():
        spine.set_visible(False)
    for bar, value in zip(bars, line_values):
        line_value = int(round(float(bar.get_x() + 0.5)))
        bar.set_gid(f"hd_line:{line_value}")
        bar.set_picker(True)
        hd_line_chart_ax.text(
            bar.get_x() + (bar.get_width() / 2),
            value + 0.05,
            str(value),
            ha="center",
            va="bottom",
            color=_theme_color(chart_theme_colors, "text", "#f0f0f0"),
            fontsize=8,
            fontweight="bold",
        )
    hd_line_chart_figure.subplots_adjust(left=0.18, bottom=0.18, right=0.94, top=0.98)
    hd_line_chart_canvas.setMinimumHeight(210)
    hd_line_chart_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    line_section_layout.addWidget(hd_line_chart_canvas)

    color_meta_by_value = _hd_meta_by_value(HD_COLORS)
    tone_meta_by_value = _hd_meta_by_value(HD_TONES)
    color_counts = {int(value): 0 for value in color_meta_by_value}
    tone_counts = {int(value): 0 for value in tone_meta_by_value}
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        if int(activation.color) in color_counts:
            color_counts[int(activation.color)] += 1
        if int(activation.tone) in tone_counts:
            tone_counts[int(activation.tone)] += 1

    color_labels = [
        f"C{value} ({str(color_meta_by_value.get(value, {}).get('name', 'unknown')).lower()})"
        for value in sorted(color_counts)
    ]
    color_values = [color_counts[value] for value in sorted(color_counts)]
    color_bar_colors = [
        _color_name_to_hex(str(color_meta_by_value.get(value, {}).get("color", "")))
        for value in sorted(color_counts)
    ]
    hd_color_chart_figure = Figure(figsize=(2.6, 2.4))
    hd_color_chart_canvas = FigureCanvas(hd_color_chart_figure)
    hd_color_chart_ax = hd_color_chart_figure.add_subplot(111)
    hd_color_chart_figure.patch.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    hd_color_chart_ax.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    color_bars = hd_color_chart_ax.bar(color_labels, color_values, color=color_bar_colors, edgecolor="#E0E0E0", linewidth=0.5, alpha=0.95)
    for color_value, bar in zip(sorted(color_counts), color_bars):
        bar.set_gid(f"hd_color:{int(color_value)}")
        bar.set_picker(True)
    hd_color_chart_ax.tick_params(axis="x", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    for label in hd_color_chart_ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")
    hd_color_chart_ax.tick_params(axis="y", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    hd_color_chart_ax.set_ylim(0, max(1, max(color_values) + 1))
    hd_color_chart_ax.grid(axis="y", color=_theme_color(chart_theme_colors, "line", "#666666"), linewidth=0.6, alpha=0.4)
    for spine in hd_color_chart_ax.spines.values():
        spine.set_visible(False)
    for bar, value in zip(color_bars, color_values):
        hd_color_chart_ax.text(bar.get_x() + (bar.get_width() / 2), value + 0.05, str(value), ha="center", va="bottom", color=_theme_color(chart_theme_colors, "text", "#f0f0f0"), fontsize=8, fontweight="bold")
    hd_color_chart_figure.subplots_adjust(left=0.18, bottom=0.20, right=0.94, top=0.98)
    hd_color_chart_canvas.setMinimumHeight(190)
    hd_color_chart_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    color_section_layout = _add_local_collapsible_section(
        hd_analytics_panel,
        hd_analytics_layout,
        "Color Distribution",
        expanded=True,
    )
    color_section_layout.addWidget(QLabel("Color Distribution (C column)", styleSheet=subheader_style))
    color_section_layout.addWidget(hd_color_chart_canvas)

    tone_labels = [
        f"{value} ({str(tone_meta_by_value.get(value, {}).get('name', 'unknown')).lower()})"
        for value in sorted(tone_counts)
    ]
    tone_values = [tone_counts[value] for value in sorted(tone_counts)]
    tone_palette = ["#9ecae1", "#6baed6", "#4292c6", "#3182bd", "#2171b5", "#08519c"]
    tone_bar_colors = [tone_palette[index % len(tone_palette)] for index, _ in enumerate(sorted(tone_counts))]
    hd_tone_chart_figure = Figure(figsize=(2.6, 2.4))
    hd_tone_chart_canvas = FigureCanvas(hd_tone_chart_figure)
    hd_tone_chart_ax = hd_tone_chart_figure.add_subplot(111)
    hd_tone_chart_figure.patch.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    hd_tone_chart_ax.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    tone_bars = hd_tone_chart_ax.bar(tone_labels, tone_values, color=tone_bar_colors, edgecolor="#E0E0E0", linewidth=0.5, alpha=0.95)
    for tone_value, bar in zip(sorted(tone_counts), tone_bars):
        bar.set_gid(f"hd_tone:{int(tone_value)}")
        bar.set_picker(True)
    hd_tone_chart_ax.tick_params(axis="x", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    for label in hd_tone_chart_ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")
    hd_tone_chart_ax.tick_params(axis="y", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    hd_tone_chart_ax.set_ylim(0, max(1, max(tone_values) + 1))
    hd_tone_chart_ax.grid(axis="y", color=_theme_color(chart_theme_colors, "line", "#666666"), linewidth=0.6, alpha=0.4)
    for spine in hd_tone_chart_ax.spines.values():
        spine.set_visible(False)
    for bar, value in zip(tone_bars, tone_values):
        hd_tone_chart_ax.text(bar.get_x() + (bar.get_width() / 2), value + 0.05, str(value), ha="center", va="bottom", color=_theme_color(chart_theme_colors, "text", "#f0f0f0"), fontsize=8, fontweight="bold")
    hd_tone_chart_figure.subplots_adjust(left=0.18, bottom=0.20, right=0.94, top=0.98)
    hd_tone_chart_canvas.setMinimumHeight(190)
    hd_tone_chart_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    tone_section_layout = _add_local_collapsible_section(
        hd_analytics_panel,
        hd_analytics_layout,
        "Tone Distribution",
        expanded=True,
    )
    tone_section_layout.addWidget(QLabel("Tone Distribution (T column)", styleSheet=subheader_style))
    tone_section_layout.addWidget(hd_tone_chart_canvas)

    def _connect_metric_pick_events(canvas: FigureCanvas) -> None:
        if on_metric_selected is None:
            return

        def _on_pick(event: object) -> None:
            artist = getattr(event, "artist", None)
            gid = str(getattr(artist, "get_gid", lambda: "")() or "")
            if ":" not in gid:
                return
            metric_kind, _, raw_value = gid.partition(":")
            if metric_kind not in {"hd_line", "hd_color", "hd_tone"}:
                return
            if not raw_value.isdigit():
                return
            on_metric_selected(metric_kind, int(raw_value))

        canvas.mpl_connect("pick_event", _on_pick)

    _connect_metric_pick_events(hd_line_chart_canvas)
    _connect_metric_pick_events(hd_color_chart_canvas)
    _connect_metric_pick_events(hd_tone_chart_canvas)

    hd_analytics_layout.addStretch(1)
    hd_analytics_scroll.setWidget(hd_analytics_panel)
    hd_analytics_content_layout.addWidget(hd_analytics_scroll)
    hd_analytics_container_layout.addWidget(hd_analytics_content, 1)

    hd_analytics_expanded_width = HD_ANALYTICS_EXPANDED_WIDTH

    def _set_hd_analytics_expanded(expanded: bool) -> None:
        nonlocal hd_analytics_expanded_width
        if expanded:
            hd_analytics_content.show()
            hd_analytics_toggle.setArrowType(Qt.LeftArrow)
            hd_analytics_toggle.setToolTip("Collapse HD analytics panel")
            hd_analytics_container.setMinimumWidth(HD_ANALYTICS_CONTAINER_MIN_WIDTH)
            hd_analytics_container.setMaximumWidth(16777215)
            hd_analytics_container.setFixedWidth(hd_analytics_expanded_width)
            return
        
        hd_analytics_expanded_width = max(
            HD_ANALYTICS_SCROLL_MIN_WIDTH,
            hd_analytics_container.width(),
        )
        hd_analytics_content.hide()
        hd_analytics_toggle.setArrowType(Qt.RightArrow)
        hd_analytics_toggle.setToolTip("Expand HD analytics panel")
        hd_analytics_container.setMinimumWidth(hd_analytics_toggle.width() + 2)
        hd_analytics_container.setMaximumWidth(hd_analytics_toggle.width() + 2)
        hd_analytics_container.setFixedWidth(hd_analytics_toggle.width() + 2)

    hd_analytics_toggle.toggled.connect(_set_hd_analytics_expanded)
    _set_hd_analytics_expanded(True)
    return hd_analytics_container
