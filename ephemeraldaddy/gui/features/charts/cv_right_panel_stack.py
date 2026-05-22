"""Chart View right-panel stack helpers."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QGraphicsOpacityEffect,
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
    container.setMinimumWidth(240)

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


def set_chart_right_panel_container_visible(owner: object, visible: bool) -> None:
    """Show/hide Chart View's entire right-hand panel container."""
    panel = getattr(owner, "metrics_panel", None)
    if panel is None:
        return
    panel.setVisible(visible)
    if visible:
        main_splitter = getattr(owner, "_main_splitter", None)
        configure_splitter = getattr(owner, "_configure_main_splitter", None)
        if main_splitter is None or not callable(configure_splitter):
            return
        sizes = main_splitter.sizes()
        if len(sizes) >= 3 and sizes[2] == 0:
            configure_splitter()


def prepare_chart_right_panel_for_loading(owner: object) -> None:
    """Hide Chart View right-hand panel while loading a chart transition."""
    panel = getattr(owner, "metrics_panel", None)
    if not isinstance(panel, QWidget):
        return
    setattr(owner, "_chart_right_panel_transition_active", True)
    setattr(owner, "_chart_right_panel_fade_in_progress", False)
    animation = getattr(owner, "_chart_right_panel_fade_animation", None)
    if isinstance(animation, QPropertyAnimation):
        animation.stop()
    effect = getattr(owner, "_chart_right_panel_opacity_effect", None)
    if not isinstance(effect, QGraphicsOpacityEffect) or effect.parent() is not panel:
        effect = QGraphicsOpacityEffect(panel)
        panel.setGraphicsEffect(effect)
        setattr(owner, "_chart_right_panel_opacity_effect", effect)
    effect.setOpacity(0.0)
    panel.setVisible(False)


def reveal_chart_right_panel_after_loading(owner: object) -> None:
    """Fade in Chart View right-hand panel once all chart sections are rendered."""
    transition_active = bool(getattr(owner, "_chart_right_panel_transition_active", False))
    if not transition_active:
        return
    setattr(owner, "_chart_right_panel_transition_active", False)
    panel = getattr(owner, "metrics_panel", None)
    effect = getattr(owner, "_chart_right_panel_opacity_effect", None)
    if not isinstance(panel, QWidget) or not isinstance(effect, QGraphicsOpacityEffect):
        setattr(owner, "_chart_right_panel_fade_in_progress", False)
        set_chart_right_panel_container_visible(owner, True)
        return
    panel.setVisible(True)
    effect.setOpacity(0.0)
    setattr(owner, "_chart_right_panel_fade_in_progress", True)
    animation = QPropertyAnimation(effect, b"opacity", panel)
    animation.setDuration(650)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
    animation.finished.connect(lambda: effect.setOpacity(1.0))
    animation.finished.connect(lambda: setattr(owner, "_chart_right_panel_fade_in_progress", False))
    setattr(owner, "_chart_right_panel_fade_animation", animation)
    animation.start()



def _scroll_expanded_section_into_view(toggle: QAbstractButton) -> None:
    """Scroll the nearest scroll area so an expanded collapsible section bottom stays visible."""
    if not toggle.isChecked():
        return

    section = toggle.parentWidget()
    while section is not None and section.layout() is None:
        section = section.parentWidget()
    if section is None:
        return

    parent = section.parentWidget()
    scroll_area = None
    while parent is not None:
        if isinstance(parent, QScrollArea):
            scroll_area = parent
            break
        parent = parent.parentWidget()
    if scroll_area is None:
        return

    scroll_widget = scroll_area.widget()
    viewport = scroll_area.viewport()
    scrollbar = scroll_area.verticalScrollBar()
    if scroll_widget is None or viewport is None or scrollbar is None:
        return

    section_bottom_y = section.mapTo(scroll_widget, QPoint(0, section.height())).y()
    target_value = section_bottom_y - viewport.height()
    scrollbar.setValue(max(scrollbar.minimum(), min(target_value, scrollbar.maximum())))


def _install_expand_autoscroll(owner: object) -> None:
    """Attach one-shot expandable-section autoscroll handlers for right-panel tabs."""
    if bool(getattr(owner, "_right_panel_expand_autoscroll_installed", False)):
        return
    setattr(owner, "_right_panel_expand_autoscroll_installed", True)

    for scroll_attr in ("chart_analytics_panel_scroll", "predictions_panel_scroll", "subjective_notes_panel_scroll"):
        scroll_area = getattr(owner, scroll_attr, None)
        if not isinstance(scroll_area, QScrollArea):
            continue
        content_widget = scroll_area.widget()
        if content_widget is None:
            continue
        for toggle in content_widget.findChildren(QAbstractButton):
            if not toggle.isCheckable():
                continue
            toggle.toggled.connect(
                lambda checked, current_toggle=toggle: (
                    QTimer.singleShot(0, lambda t=current_toggle: _scroll_expanded_section_into_view(t))
                    if checked
                    else None
                )
            )

def set_chart_right_panel(owner: object, panel_key: str) -> None:
    """Activate a Chart View right-panel tab and synchronize toggle state."""
    _install_expand_autoscroll(owner)
    panel_stack = getattr(owner, "chart_right_panel_stack", None)
    if panel_stack is None:
        collapse = getattr(owner, "_collapse_similar_charts_section", None)
        if callable(collapse):
            collapse()
        return

    analytics_button = getattr(owner, "chart_analytics_panel_button", None)
    analytics_enabled = bool(analytics_button and analytics_button.isEnabled())
    if panel_key == "analytics" and not analytics_enabled:
        panel_key = "subjective_notes"
    if panel_key == "analytics":
        collapse = getattr(owner, "_collapse_similar_charts_section", None)
        if callable(collapse):
            collapse()

    if panel_key == "subjective_notes":
        active_scroll = getattr(owner, "subjective_notes_panel_scroll", None)
    elif panel_key == "predictions":
        active_scroll = getattr(owner, "predictions_panel_scroll", None)
    else:
        panel_key = "analytics"
        active_scroll = getattr(owner, "chart_analytics_panel_scroll", None)

    if active_scroll is None:
        return
    panel_stack.setCurrentWidget(active_scroll)
    setattr(owner, "metrics_scroll", active_scroll)

    state = getattr(owner, "_chart_right_panel_state", None)
    if state is not None:
        state.active_tab = panel_key
    setattr(owner, "_active_chart_right_panel", panel_key)

    if analytics_button is not None:
        analytics_button.setChecked(panel_key == "analytics")
    predictions_button = getattr(owner, "predictions_panel_button", None)
    if predictions_button is not None:
        predictions_button.setChecked(panel_key == "predictions")
    subjective_notes_button = getattr(owner, "subjective_notes_panel_button", None)
    if subjective_notes_button is not None:
        subjective_notes_button.setChecked(panel_key == "subjective_notes")

    if panel_key == "predictions":
        latest_chart = getattr(owner, "_latest_chart", None)
        rerender_enneagram = getattr(owner, "_render_enneagram_predictions", None)
        if latest_chart is not None and callable(rerender_enneagram):
            predictions_scroll = getattr(owner, "predictions_panel_scroll", None)
            predictions_widget = predictions_scroll.widget() if isinstance(predictions_scroll, QScrollArea) else None
            if isinstance(predictions_widget, QWidget):
                predictions_widget.setUpdatesEnabled(False)
            rerender_enneagram(latest_chart)
            if isinstance(predictions_widget, QWidget):
                predictions_widget.setUpdatesEnabled(True)
                predictions_widget.update()

    schedule = getattr(owner, "_schedule_chart_render_for_active_right_panel", None)
    if callable(schedule):
        schedule()


def schedule_chart_render_for_active_right_panel(owner: object) -> None:
    """Queue now-renderable sections after Chart View right-panel tab switches."""
    chart = getattr(owner, "_latest_chart", None)
    if chart is None:
        return
    state = getattr(owner, "_chart_right_panel_state", None)
    active_panel = getattr(state, "active_tab", None)
    if active_panel == "analytics":
        owner._schedule_chart_render(chart)
        return
    if active_panel == "predictions":
        owner._render_enneagram_predictions(chart)
        owner._render_dndification_predictions(chart)
        return
    if active_panel == "subjective_notes" and owner._is_chart_analysis_section_visible("anagrams"):
        owner._schedule_chart_render(chart, sections={"anagrams"})


def sync_chart_right_panel_placeholder_state(owner: object, chart: object | None) -> None:
    """Update right-panel toggle availability for placeholder vs saved charts."""
    analytics_button = getattr(owner, "chart_analytics_panel_button", None)
    predictions_button = getattr(owner, "predictions_panel_button", None)
    if analytics_button is None or predictions_button is None:
        return
    is_placeholder = bool(getattr(owner, "_is_placeholder_chart")(chart))
    is_saved_chart = bool(chart is not None and getattr(owner, "current_chart_id", None) is not None)
    analytics_available = bool(is_saved_chart and not is_placeholder)
    analytics_button.setVisible(analytics_available)
    analytics_button.setEnabled(analytics_available)
    predictions_button.setVisible(analytics_available)
    predictions_button.setEnabled(analytics_available)
    if not analytics_available:
        set_chart_right_panel(owner, "subjective_notes")
