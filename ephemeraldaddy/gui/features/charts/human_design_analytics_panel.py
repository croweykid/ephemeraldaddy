"""Human Design popout right-panel analytics UI helpers."""

from __future__ import annotations

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
from ephemeraldaddy.gui.style import (
    COLLAPSIBLE_SECTION_CONTENT_STYLE,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    configure_collapsible_header_toggle,
)

def _theme_color(theme: dict[str, str], key: str, fallback: str) -> str:
    value = str(theme.get(key, "") or "").strip()
    return value or fallback

def build_human_design_top_splitter(
    *,
    chart_container: QWidget,
    hd_result: HumanDesignResult,
    chart_theme_colors: dict[str, str],
    subheader_style: str,
) -> QSplitter:
    """Build the Human Design popout top row with chart + collapsible analytics panel."""

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
    hd_analytics_scroll.setMinimumWidth(240)
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

    hd_section_layout = _add_local_collapsible_section(
        hd_analytics_panel,
        hd_analytics_layout,
        "HD Analytics",
        expanded=True,
    )

    hd_line_summary = QLabel("Line Distribution (Personality + Design activations)")
    hd_line_summary.setWordWrap(True)
    hd_line_summary.setStyleSheet(subheader_style)
    hd_section_layout.addWidget(hd_line_summary)

    line_counts = {line: 0 for line in range(1, 7)}
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        if 1 <= int(activation.line) <= 6:
            line_counts[int(activation.line)] += 1

    hd_line_chart_figure = Figure(figsize=(3.2, 2.6))
    hd_line_chart_canvas = FigureCanvas(hd_line_chart_figure)
    hd_line_chart_ax = hd_line_chart_figure.add_subplot(111)
    
    hd_line_chart_figure.patch.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))
    hd_line_chart_ax.set_facecolor(_theme_color(chart_theme_colors, "background", "#101010"))

    line_numbers = list(range(1, 7))
    line_values = [line_counts.get(line_number, 0) for line_number in line_numbers]
    bars = hd_line_chart_ax.bar(
        line_numbers,
        line_values,
        color="#5dc26a",
        edgecolor="#E0E0E0",
        linewidth=0.5,
        alpha=0.95,
    )
    hd_line_chart_ax.set_xticks(line_numbers)
    hd_line_chart_ax.set_xticklabels(
        [f"L{line_number}" for line_number in line_numbers],
        color=_theme_color(chart_theme_colors, "text", "#f0f0f0"),
    )
    hd_line_chart_ax.tick_params(axis="y", colors=_theme_color(chart_theme_colors, "text", "#f0f0f0"), labelsize=8)
    hd_line_chart_ax.tick_params(axis="x", labelsize=8)
    hd_line_chart_ax.set_ylim(0, max(1, max(line_values) + 1))
    hd_line_chart_ax.grid(axis="y", color=_theme_color(chart_theme_colors, "line", "#666666"), linewidth=0.6, alpha=0.4)
    for spine in hd_line_chart_ax.spines.values():
        spine.set_visible(False)
    for bar, value in zip(bars, line_values):
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
    hd_line_chart_figure.subplots_adjust(left=0.14, bottom=0.18, right=0.98, top=0.98)
    hd_line_chart_canvas.setMinimumHeight(210)
    hd_line_chart_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    hd_section_layout.addWidget(hd_line_chart_canvas)

    hd_analytics_layout.addStretch(1)
    hd_analytics_scroll.setWidget(hd_analytics_panel)
    hd_analytics_content_layout.addWidget(hd_analytics_scroll)
    hd_analytics_container_layout.addWidget(hd_analytics_content, 1)

    top_splitter = QSplitter(Qt.Horizontal)
    top_splitter.setChildrenCollapsible(False)
    top_splitter.addWidget(chart_container)
    top_splitter.addWidget(hd_analytics_container)
    top_splitter.setStretchFactor(0, 5)
    top_splitter.setStretchFactor(1, 2)

    hd_analytics_expanded_width = 300

    def _set_hd_analytics_expanded(expanded: bool) -> None:
        nonlocal hd_analytics_expanded_width
        if expanded:
            hd_analytics_content.show()
            hd_analytics_toggle.setArrowType(Qt.LeftArrow)
            hd_analytics_toggle.setToolTip("Collapse HD analytics panel")
            hd_analytics_container.setMinimumWidth(220)
            hd_analytics_container.setMaximumWidth(16777215)
            top_splitter.setSizes(
                [
                    max(560, top_splitter.width() - hd_analytics_expanded_width),
                    hd_analytics_expanded_width,
                ]
            )
            return
        hd_analytics_expanded_width = max(240, hd_analytics_container.width())
        hd_analytics_content.hide()
        hd_analytics_toggle.setArrowType(Qt.RightArrow)
        hd_analytics_toggle.setToolTip("Expand HD analytics panel")
        hd_analytics_container.setMinimumWidth(hd_analytics_toggle.width() + 2)
        hd_analytics_container.setMaximumWidth(hd_analytics_toggle.width() + 2)
        top_splitter.setSizes(
            [
                max(560, top_splitter.width() - (hd_analytics_toggle.width() + 2)),
                hd_analytics_toggle.width() + 2,
            ]
        )

    hd_analytics_toggle.toggled.connect(_set_hd_analytics_expanded)
    _set_hd_analytics_expanded(True)
    return top_splitter
