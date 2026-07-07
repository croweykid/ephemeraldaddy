"""Chart View right-panel stack helpers."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QPoint, QThread, QTimer, Qt, Signal, Slot
try:
    from PySide6.QtGui import QColor, QPainter
except Exception:  # pragma: no cover - test stubs may omit QtGui
    QColor = None  # type: ignore[assignment]
    QPainter = None  # type: ignore[assignment]
from PySide6.QtWidgets import (
    QAbstractButton,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import MODE_KEYWORDS


logger = logging.getLogger(__name__)
PREDICTIONS_BACKGROUND_TIMEOUT_MS = 120_000


MODE_POPOUT_COLORS: dict[str, str] = {
    "cardinal": "#993333",
    "mutable": "#6699ff",
    "fixed": "#336600",
}


class _PredictionsWarmupWorker(QObject):
    """Precompute slow Predictions data away from the GUI thread."""

    finished = Signal(object, str, object)

    def __init__(self, owner: object, chart: object, render_token: str) -> None:
        super().__init__()
        self._owner = owner
        self._chart = chart
        self._render_token = render_token
        self._cancelled = False

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        error: Exception | None = None
        try:
            if self._cancelled or QThread.currentThread().isInterruptionRequested():
                self.finished.emit(self._chart, self._render_token, None)
                return
            cache_enneagram = getattr(self._owner, "_cache_enneagram_prediction_metadata", None)
            if callable(cache_enneagram):
                cache_enneagram(self._chart)
            if self._cancelled or QThread.currentThread().isInterruptionRequested():
                self.finished.emit(self._chart, self._render_token, None)
                return
            adapter_factory = getattr(self._owner, "_dnd_prediction_adapter", None)
            if callable(adapter_factory):
                adapter = adapter_factory()
                cache_dnd = getattr(adapter, "cache_metadata", None)
                if callable(cache_dnd):
                    cache_dnd(self._chart)
        except Exception as exc:  # pragma: no cover - defensive UI path
            logger.warning(
                "Predictions warmup failed for %s: %s",
                _chart_display_name(self._chart),
                exc,
                exc_info=True,
            )
            error = exc
        self.finished.emit(self._chart, self._render_token, error)


class _PredictionsWarmupReceiver(QObject):
    """Deliver Predictions warmup completion to the GUI thread and own its watchdog."""

    def __init__(self, owner: object, chart: object, render_token: str) -> None:
        parent = owner if isinstance(owner, QWidget) else None
        super().__init__(parent)
        self._owner = owner
        self._chart = chart
        self._render_token = render_token
        self._thread: QThread | None = None
        self._worker: QObject | None = None
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._handle_timeout)

    def set_job(self, thread: QThread, worker: QObject) -> None:
        self._thread = thread
        self._worker = worker

    def start_watchdog(self) -> None:
        self._watchdog.start(PREDICTIONS_BACKGROUND_TIMEOUT_MS)

    @Slot(object, str, object)
    def handle_finished(self, chart: object, render_token: str, error: object) -> None:
        self._watchdog.stop()
        _finish_background_prediction_render(self._owner, chart, render_token, error)

    @Slot()
    def _handle_timeout(self) -> None:
        active_token = getattr(self._owner, "_predictions_background_render_token", None)
        if active_token != self._render_token:
            return
        chart_name = _chart_display_name(self._chart)
        logger.error("Predictions warmup timed out for %s", chart_name)
        worker = self._worker
        thread = self._thread
        if worker is not None and hasattr(worker, "cancel"):
            try:
                worker.cancel()
            except RuntimeError:
                pass
        if isinstance(thread, QThread):
            try:
                thread.requestInterruption()
                thread.quit()
            except RuntimeError:
                pass
        _finish_background_prediction_render(
            self._owner,
            self._chart,
            self._render_token,
            "Timed out while preparing predictions. Try reopening the panel; check the terminal log for the stuck scorer.",
        )

    @Slot()
    def cleanup(self) -> None:
        self._watchdog.stop()
        self.deleteLater()


@dataclass
class ChartRightPanelStack:
    """Container + controls used by Chart View's right-side panel stack."""

    container: QWidget
    analytics_button: QPushButton
    predictions_button: QPushButton
    subjective_notes_button: QPushButton
    abc_button: QPushButton
    material_facts_button: QPushButton
    time_sensitivity_button: QPushButton
    photo_gallery_button: QPushButton
    stack: QStackedWidget
    analytics_scroll: QScrollArea
    predictions_scroll: QScrollArea
    subjective_notes_scroll: QScrollArea
    abc_scroll: QScrollArea
    material_facts_scroll: QScrollArea
    time_sensitivity_scroll: QScrollArea
    photo_gallery_scroll: QScrollArea


class _AbcPanelButton(QPushButton):
    """Small tab button that paints A/B/C in violet, red, and baby blue."""

    def paintEvent(self, event: object) -> None:  # noqa: N802 - Qt override
        if QPainter is None or QColor is None:
            return super().paintEvent(event)
        from PySide6.QtWidgets import QStyle, QStyleOptionButton

        painter = QPainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        self.style().drawControl(QStyle.CE_PushButton, option, painter, self)

        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        letters = "ABC"
        colors = (QColor("#8f5cff"), QColor("#ff4b4b"), QColor("#9bd3ff"))
        spacing = 1
        widths = [metrics.horizontalAdvance(letter) for letter in letters]
        total_width = sum(widths) + spacing * (len(letters) - 1)
        x = int((self.width() - total_width) / 2)
        baseline = int((self.height() + metrics.ascent() - metrics.descent()) / 2)
        for letter, color, width in zip(letters, colors, widths, strict=True):
            painter.setPen(color)
            painter.drawText(x, baseline, letter)
            x += width + spacing
        painter.end()


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


def _configure_chart_right_panel_scroll_area(
    scroll_area: QScrollArea, content_widget: QWidget, scrollbar_style: str
) -> None:
    """Configure right-panel scroll areas so graph canvases cannot create horizontal overflow."""
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.NoFrame)
    scroll_area.setMinimumWidth(240)
    scroll_area.setStyleSheet(scrollbar_style)
    scroll_area.setFocusPolicy(Qt.StrongFocus)
    scroll_area.viewport().setFocusPolicy(Qt.StrongFocus)
    scroll_area.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    content_widget.setMinimumWidth(0)
    content_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    scroll_area.setWidget(content_widget)


def build_chart_right_panel_stack(
    *,
    analytics_content_widget: QWidget,
    predictions_content_widget: QWidget,
    subjective_notes_content_widget: QWidget,
    abc_content_widget: QWidget,
    material_facts_content_widget: QWidget,
    time_sensitivity_content_widget: QWidget,
    photo_gallery_content_widget: QWidget,
    on_show_analytics: Callable[[], None],
    on_show_predictions: Callable[[], None],
    on_show_subjective_notes: Callable[[], None],
    on_show_abc: Callable[[], None],
    on_show_material_facts: Callable[[], None],
    on_show_time_sensitivity: Callable[[], None],
    on_show_photo_gallery: Callable[[], None],
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
    abc_button = _AbcPanelButton("ABC")
    abc_button.setObjectName("chart_view_toggle_abc_panel_button")
    abc_button.setToolTip("ABC: Anagrams and Euphonics")
    abc_button.setStyleSheet("padding: 1px 5px; font-size: 11px; font-weight: 700; color: #c7e8ff;")
    abc_button.clicked.connect(on_show_abc)
    material_facts_button = QPushButton("🗒️")
    material_facts_button.setObjectName("chart_view_toggle_material_facts_panel_button")
    material_facts_button.clicked.connect(on_show_material_facts)
    time_sensitivity_button = QPushButton("⏱️")
    time_sensitivity_button.setObjectName("chart_view_toggle_time_sensitivity_panel_button")
    time_sensitivity_button.setToolTip("Time/Rectification Sensitivity")
    time_sensitivity_button.clicked.connect(on_show_time_sensitivity)
    photo_gallery_button = QPushButton("🖼️")
    photo_gallery_button.setObjectName("chart_view_toggle_photo_gallery_panel_button")
    photo_gallery_button.clicked.connect(on_show_photo_gallery)

    for control_button in (analytics_button, predictions_button, subjective_notes_button, abc_button, material_facts_button, photo_gallery_button, time_sensitivity_button):
        control_button.setCheckable(True)
        control_button.setAutoDefault(False)
        control_button.setDefault(False)
        control_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        control_button.setMinimumWidth(0)
        if control_button is not abc_button:
            control_button.setStyleSheet("padding: 1px 5px; font-size: 11px;")

    controls_row = QWidget()
    controls_layout = QHBoxLayout()
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(4)
    controls_row.setLayout(controls_layout)
    controls_layout.addWidget(analytics_button)
    controls_layout.addWidget(predictions_button)
    controls_layout.addWidget(subjective_notes_button)
    controls_layout.addWidget(abc_button)
    controls_layout.addWidget(material_facts_button)
    controls_layout.addWidget(time_sensitivity_button)
    controls_layout.addWidget(photo_gallery_button)
    controls_layout.addStretch(1)
    layout.addWidget(controls_row)

    stack = QStackedWidget()
    stack.setMinimumWidth(0)
    layout.addWidget(stack, 1)

    analytics_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        analytics_scroll, analytics_content_widget, scrollbar_style
    )
    stack.addWidget(analytics_scroll)

    predictions_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        predictions_scroll, predictions_content_widget, scrollbar_style
    )
    stack.addWidget(predictions_scroll)

    subjective_notes_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        subjective_notes_scroll, subjective_notes_content_widget, scrollbar_style
    )
    stack.addWidget(subjective_notes_scroll)

    abc_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        abc_scroll, abc_content_widget, scrollbar_style
    )
    stack.addWidget(abc_scroll)

    material_facts_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        material_facts_scroll, material_facts_content_widget, scrollbar_style
    )
    stack.addWidget(material_facts_scroll)

    time_sensitivity_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        time_sensitivity_scroll, time_sensitivity_content_widget, scrollbar_style
    )
    stack.addWidget(time_sensitivity_scroll)
    photo_gallery_scroll = QScrollArea()
    _configure_chart_right_panel_scroll_area(
        photo_gallery_scroll, photo_gallery_content_widget, scrollbar_style
    )
    stack.addWidget(photo_gallery_scroll)

    return ChartRightPanelStack(
        container=container,
        analytics_button=analytics_button,
        predictions_button=predictions_button,
        subjective_notes_button=subjective_notes_button,
        abc_button=abc_button,
        material_facts_button=material_facts_button,
        time_sensitivity_button=time_sensitivity_button,
        photo_gallery_button=photo_gallery_button,
        stack=stack,
        analytics_scroll=analytics_scroll,
        predictions_scroll=predictions_scroll,
        subjective_notes_scroll=subjective_notes_scroll,
        abc_scroll=abc_scroll,
        material_facts_scroll=material_facts_scroll,
        time_sensitivity_scroll=time_sensitivity_scroll,
        photo_gallery_scroll=photo_gallery_scroll,
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


def _stop_chart_right_panel_fade(owner: object) -> None:
    """Stop and detach any stale right-panel opacity animation/effect."""
    animation = getattr(owner, "_chart_right_panel_fade_animation", None)
    stop_animation = getattr(animation, "stop", None)
    if callable(stop_animation):
        stop_animation()
    setattr(owner, "_chart_right_panel_fade_animation", None)
    setattr(owner, "_chart_right_panel_fade_in_progress", False)

    panel = getattr(owner, "metrics_panel", None)
    if isinstance(panel, QWidget):
        panel.setGraphicsEffect(None)
    setattr(owner, "_chart_right_panel_opacity_effect", None)


def prepare_chart_right_panel_for_loading(owner: object) -> None:
    """Prepare a chart transition without hiding the interactive right panel."""
    # The loading overlay and per-section redraws already communicate chart-load
    # progress.  Hiding the full right panel here causes visible blanking during
    # normal render churn and can interrupt text entry in right-panel fields.
    _stop_chart_right_panel_fade(owner)
    setattr(owner, "_chart_right_panel_transition_active", False)


def reveal_chart_right_panel_after_loading(owner: object) -> None:
    """Leave the right panel visible after chart rendering completes."""
    _stop_chart_right_panel_fade(owner)
    setattr(owner, "_chart_right_panel_transition_active", False)


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

    for scroll_attr in (
        "chart_analytics_panel_scroll",
        "predictions_panel_scroll",
        "subjective_notes_panel_scroll",
        "abc_panel_scroll",
        "material_facts_panel_scroll",
        "photo_gallery_panel_scroll",
        "time_sensitivity_panel_scroll",
    ):
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



def _chart_right_panel_definitions(owner: object) -> dict[str, tuple[str, str]]:
    """Return tab key -> (scroll attr, button attr) mapping for right panel."""
    return {
        "analytics": ("chart_analytics_panel_scroll", "chart_analytics_panel_button"),
        "predictions": ("predictions_panel_scroll", "predictions_panel_button"),
        "subjective_notes": ("subjective_notes_panel_scroll", "subjective_notes_panel_button"),
        "abc": ("abc_panel_scroll", "abc_panel_button"),
        "material_facts": ("material_facts_panel_scroll", "material_facts_panel_button"),
        "time_sensitivity": ("time_sensitivity_panel_scroll","time_sensitivity_panel_button"),
        "photo_gallery": ("photo_gallery_panel_scroll", "photo_gallery_panel_button"),
    }


def _resolve_chart_right_panel_key(owner: object, panel_key: str) -> str:
    """Normalize + gate requested right-panel tab key."""
    definitions = _chart_right_panel_definitions(owner)
    normalized = panel_key if panel_key in definitions else "analytics"
    analytics_button = getattr(owner, "chart_analytics_panel_button", None)
    analytics_enabled = bool(analytics_button and analytics_button.isEnabled())
    if normalized == "analytics" and not analytics_enabled:
        return "subjective_notes"
    return normalized

def set_chart_right_panel(owner: object, panel_key: str) -> None:
    """Activate a Chart View right-panel tab and synchronize toggle state."""
    _install_expand_autoscroll(owner)
    panel_stack = getattr(owner, "chart_right_panel_stack", None)
    if panel_stack is None:
        collapse = getattr(owner, "_collapse_similar_charts_section", None)
        if callable(collapse):
            collapse()
        return

    panel_key = _resolve_chart_right_panel_key(owner, panel_key)
    if panel_key == "analytics":
        collapse = getattr(owner, "_collapse_similar_charts_section", None)
        if callable(collapse):
            collapse()

    definitions = _chart_right_panel_definitions(owner)
    scroll_attr, _button_attr = definitions[panel_key]
    active_scroll = getattr(owner, scroll_attr, None)
    if active_scroll is None:
        return
    panel_stack.setCurrentWidget(active_scroll)
    setattr(owner, "metrics_scroll", active_scroll)

    state = getattr(owner, "_chart_right_panel_state", None)
    if state is not None:
        state.active_tab = panel_key

    for tab_key, (_scroll_attr, button_attr) in definitions.items():
        button = getattr(owner, button_attr, None)
        if button is not None:
            button.setChecked(panel_key == tab_key)

    # if panel_key == "predictions":
    #     latest_chart = getattr(owner, "_latest_chart", None)
    #     rerender_enneagram = getattr(owner, "_render_enneagram_predictions", None)
    #     if latest_chart is not None and callable(rerender_enneagram):
    #         predictions_scroll = getattr(owner, "predictions_panel_scroll", None)
    #         predictions_widget = predictions_scroll.widget() if isinstance(predictions_scroll, QScrollArea) else None
    #         if isinstance(predictions_widget, QWidget):
    #             predictions_widget.setUpdatesEnabled(False)
    #         rerender_enneagram(latest_chart)
    #         if isinstance(predictions_widget, QWidget):
    #             predictions_widget.setUpdatesEnabled(True)
    #             predictions_widget.update()

    schedule = getattr(owner, "_schedule_chart_render_for_active_right_panel", None)
    if callable(schedule):
        schedule()


def _chart_right_panel_prediction_render_token(owner: object, chart: object) -> str:
    """Return a stable token for prediction renders in the right-panel tab."""
    cache_token = getattr(owner, "_chart_analytics_cache_token", None)
    if callable(cache_token):
        chart_token = str(cache_token(chart))
    else:
        chart_id = getattr(owner, "current_chart_id", None)
        chart_token = f"id:{chart_id}" if chart_id is not None else f"object:{id(chart)}"

    norms_token_fn = getattr(owner, "_prediction_norms_render_token", None)
    norms_token = str(norms_token_fn()) if callable(norms_token_fn) else "prediction_norms:unavailable"
    return f"{chart_token}|{norms_token}"


def _chart_display_name(chart: object | None) -> str:
    if chart is None:
        return "this chart"
    for attr in ("name", "full_name", "display_name"):
        value = str(getattr(chart, attr, "") or "").strip()
        if value:
            return value
    return "this chart"


def _set_predictions_status(owner: object, message: str) -> None:
    label = getattr(owner, "predictions_background_status_label", None)
    if isinstance(label, QLabel):
        label.setText(message)
        label.setVisible(True)


def _prompt_prediction_render_conflict(owner: object, requested_chart: object) -> bool:
    active_chart = getattr(owner, "_predictions_background_chart", None)
    active_name = _chart_display_name(active_chart)
    requested_name = _chart_display_name(requested_chart)
    message = QMessageBox(getattr(owner, "window", lambda: None)())
    message.setIcon(QMessageBox.Warning)
    message.setWindowTitle("Predictions still rendering")
    message.setText(
        f"Still currently rendering Predictions for {active_name}.\n\n"
        f"Continue, or predict for {requested_name} instead?"
    )
    continue_button = message.addButton("Continue", QMessageBox.AcceptRole)
    continue_button.setStyleSheet("background-color: #7b4dff; color: white; font-weight: bold;")
    replace_button = message.addButton(f"Predict for {requested_name} instead", QMessageBox.DestructiveRole)
    replace_button.setStyleSheet("background-color: #666; color: #eee;")
    message.exec()
    return message.clickedButton() is replace_button


def _finish_background_prediction_render(owner: object, chart: object, render_token: str, error: object) -> None:
    active_token = getattr(owner, "_predictions_background_render_token", None)
    if active_token != render_token:
        return
    setattr(owner, "_predictions_background_render_token", None)
    setattr(owner, "_predictions_background_chart", None)

    chart_name = _chart_display_name(chart)
    if error is not None:
        _set_predictions_status(owner, f"Predictions for <b>{html.escape(chart_name)}</b> failed: {html.escape(str(error))}")
        return

    state = getattr(owner, "_chart_right_panel_state", None)
    if getattr(owner, "_latest_chart", None) is chart:
        owner._render_enneagram_predictions(chart)
        owner._render_dndification_predictions(chart)
        if state is not None:
            state.last_render_chart_token = render_token
    _set_predictions_status(
        owner,
        f"Predictions for <b>{html.escape(chart_name)}</b> are ready. "
        "<a href='show-predictions'>Open Predictions</a>",
    )
    label = getattr(owner, "predictions_background_status_label", None)
    if isinstance(label, QLabel):
        previous_handler = getattr(label, "_ephemeraldaddy_predictions_status_link_handler", None)
        if previous_handler is not None:
            try:
                label.linkActivated.disconnect(previous_handler)
            except (TypeError, RuntimeError):
                pass
        handler = lambda _link: set_chart_right_panel(owner, "predictions")
        label.linkActivated.connect(handler)
        label._ephemeraldaddy_predictions_status_link_handler = handler


def _retain_background_prediction_job(
    owner: object,
    thread: QThread,
    worker: QObject,
    receiver: QObject | None = None,
) -> None:
    jobs = getattr(owner, "_predictions_background_jobs", None)
    if not isinstance(jobs, list):
        jobs = []
        setattr(owner, "_predictions_background_jobs", jobs)
    jobs.append((thread, worker, receiver))


def _forget_background_prediction_job(
    owner: object,
    thread: QThread,
    worker: QObject,
    receiver: QObject | None = None,
) -> None:
    jobs = getattr(owner, "_predictions_background_jobs", None)
    if isinstance(jobs, list):
        for job in list(jobs):
            job_thread = job[0] if isinstance(job, tuple) and len(job) >= 1 else None
            job_worker = job[1] if isinstance(job, tuple) and len(job) >= 2 else None
            if job_thread is thread and job_worker is worker:
                jobs.remove(job)
                break
    if getattr(owner, "_predictions_background_thread", None) is thread:
        setattr(owner, "_predictions_background_thread", None)
    if getattr(owner, "_predictions_background_worker", None) is worker:
        setattr(owner, "_predictions_background_worker", None)
    if getattr(owner, "_predictions_background_receiver", None) is receiver:
        setattr(owner, "_predictions_background_receiver", None)


def stop_background_prediction_render(owner: object, wait_msecs: int | None = None) -> None:
    """Cancel in-flight Predictions warmup threads before owner or thread wrappers are destroyed."""
    setattr(owner, "_predictions_background_render_token", None)
    setattr(owner, "_predictions_background_chart", None)
    jobs = list(getattr(owner, "_predictions_background_jobs", []) or [])
    active_thread = getattr(owner, "_predictions_background_thread", None)
    active_worker = getattr(owner, "_predictions_background_worker", None)
    active_receiver = getattr(owner, "_predictions_background_receiver", None)
    if isinstance(active_thread, QThread) and all(
        (job[0] if isinstance(job, tuple) and len(job) >= 1 else None) is not active_thread
        for job in jobs
    ):
        jobs.append((active_thread, active_worker, active_receiver))
    for job in jobs:
        thread = job[0] if isinstance(job, tuple) and len(job) >= 1 else None
        worker = job[1] if isinstance(job, tuple) and len(job) >= 2 else None
        if not isinstance(thread, QThread):
            continue
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()
                if wait_msecs is None:
                    thread.wait()
                else:
                    thread.wait(max(0, int(wait_msecs)))
        except RuntimeError:
            continue
    if isinstance(getattr(owner, "_predictions_background_jobs", None), list):
        owner._predictions_background_jobs.clear()
    setattr(owner, "_predictions_background_thread", None)
    setattr(owner, "_predictions_background_worker", None)
    setattr(owner, "_predictions_background_receiver", None)


def _start_background_prediction_render(owner: object, chart: object, render_token: str) -> None:
    chart_name = _chart_display_name(chart)
    _set_predictions_status(owner, f"Loading Predictions for <b>{html.escape(chart_name)}</b> in the background…")
    thread = QThread()
    worker = _PredictionsWarmupWorker(owner, chart, render_token)
    receiver = _PredictionsWarmupReceiver(owner, chart, render_token)
    receiver.set_job(thread, worker)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(receiver.handle_finished, Qt.QueuedConnection)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(receiver.cleanup, Qt.QueuedConnection)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(
        lambda t=thread, w=worker, r=receiver: _forget_background_prediction_job(owner, t, w, r)
    )
    setattr(owner, "_predictions_background_thread", thread)
    setattr(owner, "_predictions_background_worker", worker)
    setattr(owner, "_predictions_background_receiver", receiver)
    setattr(owner, "_predictions_background_chart", chart)
    setattr(owner, "_predictions_background_render_token", render_token)
    _retain_background_prediction_job(owner, thread, worker, receiver)
    receiver.start_watchdog()
    thread.start()


def _chart_right_panel_analytics_has_stale_sections(owner: object, chart: object) -> bool:
    """Return whether Analytics needs recalculation for the current chart token."""
    cache_token = getattr(owner, "_chart_analytics_cache_token", None)
    render_tokens = getattr(owner, "_chart_analytics_render_tokens", None)
    dirty_sections = getattr(owner, "_chart_analytics_lucy_goosey_sections", None)
    if not callable(cache_token) or not isinstance(render_tokens, dict):
        return True

    current_token = str(cache_token(chart))
    analytics_sections = (
        "signs",
        "planets",
        "houses",
        "elements",
        "nakshatra",
        "modal",
        "gender",
        "planet_dynamics",
        "chart_type",
        "similar_charts",
    )
    is_renderable = getattr(owner, "_is_chart_analytics_section_renderable", None)
    for section in analytics_sections:
        if callable(is_renderable) and not is_renderable(section):
            continue
        if dirty_sections is not None and section in dirty_sections:
            return True
        if render_tokens.get(section) != current_token:
            return True
    return False


def schedule_chart_render_for_active_right_panel(owner: object) -> None:
    """Queue right-panel work only when the active chart data token changes."""
    chart = getattr(owner, "_latest_chart", None)
    if chart is None:
        return
    state = getattr(owner, "_chart_right_panel_state", None)
    active_panel = getattr(state, "active_tab", None)
    if active_panel == "analytics":
        render_distinguishing = getattr(owner, "_render_distinguishing_factors", None)
        if (
            callable(render_distinguishing)
            and bool(getattr(owner, "_chart_analytics_distinguishing_factors_expanded", False))
        ):
            render_distinguishing(chart)
        if _chart_right_panel_analytics_has_stale_sections(owner, chart):
            owner._schedule_chart_render(chart)
        return
    if active_panel == "predictions":
        render_token = _chart_right_panel_prediction_render_token(owner, chart)
        if state is not None and state.last_render_chart_token == render_token:
            return
        active_token = getattr(owner, "_predictions_background_render_token", None)
        active_chart = getattr(owner, "_predictions_background_chart", None)
        if active_token is not None:
            if active_token == render_token:
                _set_predictions_status(
                    owner,
                    f"Loading Predictions for <b>{html.escape(_chart_display_name(chart))}</b> in the background…",
                )
                return
            if not _prompt_prediction_render_conflict(owner, chart):
                if active_chart is not None:
                    _set_predictions_status(
                        owner,
                        f"Still loading Predictions for <b>{html.escape(_chart_display_name(active_chart))}</b>…",
                    )
                return
            thread = getattr(owner, "_predictions_background_thread", None)
            if isinstance(thread, QThread):
                thread.requestInterruption()
                thread.quit()
                jobs = getattr(owner, "_predictions_background_jobs", None)
                if not isinstance(jobs, list) or not any(
                    (job[0] if isinstance(job, tuple) else None) is thread for job in jobs
                ):
                    worker = getattr(owner, "_predictions_background_worker", None)
                    receiver = getattr(owner, "_predictions_background_receiver", None)
                    _retain_background_prediction_job(owner, thread, worker, receiver)
        _start_background_prediction_render(owner, chart, render_token)
        return
    if active_panel in {"subjective_notes", "abc"} and owner._is_chart_analysis_section_visible("anagrams"):
        owner._schedule_chart_render(chart, sections={"anagrams"})


def sync_chart_right_panel_placeholder_state(owner: object, chart: object | None) -> None:
    """Update right-panel toggle availability for placeholder vs saved charts."""
    analytics_button = getattr(owner, "chart_analytics_panel_button", None)
    predictions_button = getattr(owner, "predictions_panel_button", None)
    time_sensitivity_button = getattr(owner, "time_sensitivity_panel_button", None)
    if analytics_button is None or predictions_button is None:
        return
    is_placeholder = bool(getattr(owner, "_is_placeholder_chart")(chart))
    is_saved_chart = bool(chart is not None and getattr(owner, "current_chart_id", None) is not None)
    analytics_available = bool(is_saved_chart and not is_placeholder)
    analytics_button.setVisible(analytics_available)
    analytics_button.setEnabled(analytics_available)
    predictions_button.setVisible(analytics_available)
    predictions_button.setEnabled(analytics_available)
    if time_sensitivity_button is not None:
        time_sensitivity_button.setVisible(is_saved_chart)
        time_sensitivity_button.setEnabled(is_saved_chart)
    if not analytics_available:
        set_chart_right_panel(owner, "subjective_notes")
