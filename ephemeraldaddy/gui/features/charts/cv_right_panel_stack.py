"""Chart View right-panel stack helpers."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import MODE_KEYWORDS


MODE_POPOUT_COLORS: dict[str, str] = {
    "cardinal": "#993333",
    "mutable": "#6699ff",
    "fixed": "#336600",
}


@dataclass
class ChartRightPanelStack:
    """Container + controls used by Chart View's right-side panel stack."""

    container: QWidget
    analytics_button: QPushButton
    predictions_button: QPushButton
    subjective_notes_button: QPushButton
    stack: QStackedWidget
    analytics_scroll: QScrollArea
    predictions_scroll: QScrollArea
    subjective_notes_scroll: QScrollArea


def format_mode_popout_info_html(
    *,
    mode_key: str,
    selected_mode: str,
    ranked_weights: dict[str, float],
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build formatted info-panel HTML for mode popout clicks."""
    normalized_mode = str(mode_key or "").strip().lower()
    if normalized_mode not in {"cardinal", "mutable", "fixed"}:
        return "No interpretation data available for this mode."

    sorted_modes = sorted(
        ["cardinal", "mutable", "fixed"],
        key=lambda key: float(ranked_weights.get(key, 0.0)),
        reverse=True,
    )
    rank_index = sorted_modes.index(normalized_mode)
    total_modes = len(sorted_modes)
    current_weight = float(ranked_weights.get(normalized_mode, 0.0))
    next_weight = (
        float(ranked_weights.get(sorted_modes[rank_index + 1], 0.0))
        if (rank_index + 1) < total_modes
        else None
    )
    total_weight = sum(float(ranked_weights.get(key, 0.0)) for key in sorted_modes)
    share_percent = ((current_weight / total_weight) * 100.0) if total_weight > 0 else 0.0
    rank_delta_percent = (
        ((current_weight - next_weight) / current_weight) * 100.0
        if next_weight is not None and current_weight > 0
        else None
    )
    rank_blurb = (
        f"(#{rank_index + 1} of {total_modes} by {rank_delta_percent:.2f}%; "
        f"{share_percent:.2f}% of all mode weights)"
        if rank_delta_percent is not None
        else f"(#{rank_index + 1} of {total_modes}; {share_percent:.2f}% of all mode weights)"
    )

    keywords = sorted(
        {
            str(keyword).strip()
            for keyword in MODE_KEYWORDS.get(normalized_mode, set())
            if str(keyword).strip()
        }
    )
    if not keywords:
        return f"No interpretation data available for {normalized_mode.title()} mode."

    header_color = MODE_POPOUT_COLORS.get(normalized_mode, fallback_text_color)
    section_header_style = f"font-weight: bold; color: {highlight_color};"
    keyword_list = "".join(
        f"<li>{html.escape(keyword)}</li>"
        for keyword in keywords
    )
    mode_label = normalized_mode.title()
    measurement_label = "prevalence" if selected_mode == "modal_prevalence" else "dominance"
    return (
        "<h3>"
        f'<span style="color: {html.escape(header_color)};">'
        f"{html.escape(mode_label)} {html.escape(rank_blurb)}"
        "</span>"
        "</h3>"
        f'<div style="{section_header_style}">Keywords:</div>'
        f"<ul>{keyword_list}</ul>"
        f'<div style="{section_header_style}">Current Measurement Mode:</div>'
        f"<div>This chart is currently displaying <b>{html.escape(measurement_label)}</b> values for modes.</div>"
    )


def apply_mode_pick_metadata(
    *,
    wedges: list[object],
    legend_texts: list[object],
    modal_order: list[str],
) -> None:
    """Attach mode pick metadata to modal pie wedges + legend labels."""
    for wedge, mode in zip(wedges, modal_order, strict=True):
        set_gid = getattr(wedge, "set_gid", None)
        set_picker = getattr(wedge, "set_picker", None)
        if callable(set_gid):
            set_gid(f"mode:{mode}")
        if callable(set_picker):
            set_picker(True)

    for text, mode in zip(legend_texts, modal_order, strict=True):
        set_gid = getattr(text, "set_gid", None)
        set_picker = getattr(text, "set_picker", None)
        if callable(set_gid):
            set_gid(f"mode:{mode}")
        if callable(set_picker):
            set_picker(True)


def build_chart_right_panel_stack(
    *,
    analytics_content_widget: QWidget,
    predictions_content_widget: QWidget,
    subjective_notes_content_widget: QWidget,
    on_show_analytics: Callable[[], None],
    on_show_predictions: Callable[[], None],
    on_show_subjective_notes: Callable[[], None],
    scrollbar_style: str,
) -> ChartRightPanelStack:
    """Build the Chart View right panel with analytics/subjective notes toggle."""
    container = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    container.setLayout(layout)
    container.setMinimumWidth(200)

    analytics_button = QPushButton("📊")
    analytics_button.setObjectName("chart_view_toggle_analytics_panel_button")
    analytics_button.clicked.connect(on_show_analytics)
    predictions_button = QPushButton("🎱")
    predictions_button.setObjectName("chart_view_toggle_predictions_panel_button")
    predictions_button.clicked.connect(on_show_predictions)
    subjective_notes_button = QPushButton("💭")
    subjective_notes_button.setObjectName("chart_view_toggle_subjective_notes_panel_button")
    subjective_notes_button.clicked.connect(on_show_subjective_notes)

    for control_button in (analytics_button, predictions_button, subjective_notes_button):
        control_button.setCheckable(True)
        control_button.setAutoDefault(False)
        control_button.setDefault(False)
        control_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        control_button.setMinimumWidth(0)
        control_button.setStyleSheet("padding: 1px 5px; font-size: 11px;")

    controls_row = QWidget()
    controls_layout = QHBoxLayout()
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(4)
    controls_row.setLayout(controls_layout)
    controls_layout.addWidget(analytics_button)
    controls_layout.addWidget(predictions_button)
    controls_layout.addWidget(subjective_notes_button)
    controls_layout.addStretch(1)
    layout.addWidget(controls_row)

    stack = QStackedWidget()
    stack.setMinimumWidth(0)
    layout.addWidget(stack, 1)

    analytics_scroll = QScrollArea()
    analytics_scroll.setWidgetResizable(True)
    analytics_scroll.setFrameShape(QScrollArea.NoFrame)
    analytics_scroll.setMinimumWidth(240)
    analytics_scroll.setStyleSheet(scrollbar_style)
    analytics_scroll.setFocusPolicy(Qt.StrongFocus)
    analytics_scroll.setWidget(analytics_content_widget)
    stack.addWidget(analytics_scroll)

    predictions_scroll = QScrollArea()
    predictions_scroll.setWidgetResizable(True)
    predictions_scroll.setFrameShape(QScrollArea.NoFrame)
    predictions_scroll.setMinimumWidth(240)
    predictions_scroll.setStyleSheet(scrollbar_style)
    predictions_scroll.setFocusPolicy(Qt.StrongFocus)
    predictions_scroll.setWidget(predictions_content_widget)
    stack.addWidget(predictions_scroll)

    subjective_notes_scroll = QScrollArea()
    subjective_notes_scroll.setWidgetResizable(True)
    subjective_notes_scroll.setFrameShape(QScrollArea.NoFrame)
    subjective_notes_scroll.setMinimumWidth(240)
    subjective_notes_scroll.setStyleSheet(scrollbar_style)
    subjective_notes_scroll.setFocusPolicy(Qt.StrongFocus)
    subjective_notes_scroll.setWidget(subjective_notes_content_widget)
    stack.addWidget(subjective_notes_scroll)

    return ChartRightPanelStack(
        container=container,
        analytics_button=analytics_button,
        predictions_button=predictions_button,
        subjective_notes_button=subjective_notes_button,
        stack=stack,
        analytics_scroll=analytics_scroll,
        predictions_scroll=predictions_scroll,
        subjective_notes_scroll=subjective_notes_scroll,
    )
