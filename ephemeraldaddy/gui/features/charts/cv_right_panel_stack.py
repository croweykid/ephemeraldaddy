"""Chart View right-panel stack helpers."""

from __future__ import annotations

import datetime
import html
import logging
import sys
import uuid
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

from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.interpretations import MODE_KEYWORDS
from ephemeraldaddy.gui.features.charts.prediction_loading_labels import start_prediction_loading_blink
from ephemeraldaddy.gui.style import (
    close_app_loading_progress,
    create_app_loading_progress,
    update_app_loading_progress,
)


logger = logging.getLogger(__name__)
PREDICTIONS_BACKGROUND_TIMEOUT_MS = 120_000
PREDICTIONS_BACKGROUND_TIMEOUT_STOP_WAIT_MS = 1_000


def _predictions_thread_debug_enabled(owner: object) -> bool:
    return bool(getattr(owner, "_predictions_thread_debug", False))


def _predictions_thread_debug(owner: object, message: str, *args: object) -> None:
    if not _predictions_thread_debug_enabled(owner):
        return
    rendered = message % args if args else message
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")
    logger.info("[predictions-thread-debug] %s", rendered)
    print(f"[predictions-thread-debug][{timestamp}] {rendered}", file=sys.stderr, flush=True)

MODE_POPOUT_COLORS: dict[str, str] = {
    "cardinal": "#993333",
    "mutable": "#6699ff",
    "fixed": "#336600",
}


class _PredictionsWarmupWorker(QObject):
    """Precompute slow Predictions data away from the GUI thread."""

    finished = Signal(object, str, str, object)
    progress = Signal(str, int)

    def __init__(self, owner: object, chart: object, render_token: str, job_token: str, sections: set[str] | None = None) -> None:
        super().__init__()
        self._owner = owner
        self._chart = chart
        self._render_token = render_token
        self._job_token = job_token
        self._cancelled = False
        self._sections = set(sections or {"enneagram", "dnd_statblock", "dnd_alignment"})

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
        _predictions_thread_debug(self._owner, "cancel requested job=%s chart=%s", self._job_token, _chart_display_name(self._chart))

    @Slot()
    def run(self) -> None:
        error: Exception | None = None
        _predictions_thread_debug(self._owner, "worker.run entered job=%s chart=%s thread=%s", self._job_token, _chart_display_name(self._chart), id(QThread.currentThread()))
        try:
            if self._cancelled or QThread.currentThread().isInterruptionRequested():
                _predictions_thread_debug(self._owner, "worker cancelled before Enneagram cache job=%s", self._job_token)
                self.finished.emit(self._chart, self._render_token, self._job_token, None)
                return
            if "enneagram" in self._sections:
                self.progress.emit("Preparing Enneagram predictions…", 15)
                cache_enneagram = getattr(self._owner, "_cache_enneagram_prediction_metadata", None)
                _predictions_thread_debug(self._owner, "Enneagram cache stage start job=%s callable=%s", self._job_token, callable(cache_enneagram))
                if callable(cache_enneagram):
                    cache_enneagram(self._chart)
                _predictions_thread_debug(self._owner, "Enneagram cache stage complete job=%s", self._job_token)
            if self._sections.intersection({"dnd_statblock", "dnd_alignment"}):
                self.progress.emit("Preparing D&D predictions…", 45)
            if self._cancelled or QThread.currentThread().isInterruptionRequested():
                _predictions_thread_debug(self._owner, "worker cancelled before D&D cache job=%s", self._job_token)
                self.finished.emit(self._chart, self._render_token, self._job_token, None)
                return
            adapter_factory = getattr(self._owner, "_dnd_prediction_adapter", None)
            _predictions_thread_debug(self._owner, "D&D adapter stage start job=%s callable=%s", self._job_token, callable(adapter_factory))
            if callable(adapter_factory) and self._sections.intersection({"dnd_statblock", "dnd_alignment"}):
                adapter = adapter_factory()
                if "dnd_statblock" in self._sections:
                    cache_dnd = getattr(adapter, "cache_metadata", None)
                    _predictions_thread_debug(self._owner, "D&D cache stage start job=%s callable=%s", self._job_token, callable(cache_dnd))
                    if callable(cache_dnd):
                        cache_dnd(self._chart)
                if "dnd_alignment" in self._sections:
                    self.progress.emit("Preparing alignment predictions…", 70)
                    cache_alignment = getattr(adapter, "cache_alignment_metadata", None)
                    if callable(cache_alignment):
                        cache_alignment(self._chart)
                _predictions_thread_debug(self._owner, "D&D cache stage complete job=%s", self._job_token)
            self.progress.emit("Finishing Predictions…", 90)
        except Exception as exc:  # pragma: no cover - defensive UI path
            logger.warning(
                "Predictions warmup failed for %s: %s",
                _chart_display_name(self._chart),
                exc,
                exc_info=True,
            )
            error = exc
        _predictions_thread_debug(self._owner, "worker emitting finished job=%s error=%s", self._job_token, error)
        self.finished.emit(self._chart, self._render_token, self._job_token, error)


class _PredictionsWarmupReceiver(QObject):
    """Deliver Predictions warmup completion to the GUI thread and own its watchdog."""

    def __init__(self, owner: object, chart: object, render_token: str, job_token: str) -> None:
        parent = owner if isinstance(owner, QWidget) else None
        super().__init__(parent)
        self._owner = owner
        self._chart = chart
        self._render_token = render_token
        self._job_token = job_token
        self._thread: QThread | None = None
        self._worker: QObject | None = None
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._handle_timeout)

    @Slot(str, int)
    def handle_progress(self, message: str, percent: int) -> None:
        progress = getattr(self._owner, "_predictions_background_progress", None)
        update_app_loading_progress(progress, message, percent)
        _set_predictions_status(self._owner, html.escape(message))

    def set_job(self, thread: QThread, worker: QObject) -> None:
        self._thread = thread
        self._worker = worker

    def start_watchdog(self) -> None:
        _predictions_thread_debug(self._owner, "watchdog start job=%s timeout_ms=%s", self._job_token, PREDICTIONS_BACKGROUND_TIMEOUT_MS)
        self._watchdog.start(PREDICTIONS_BACKGROUND_TIMEOUT_MS)

    @Slot(object, str, str, object)
    def handle_finished(self, chart: object, render_token: str, job_token: str, error: object) -> None:
        if job_token != self._job_token:
            _predictions_thread_debug(self._owner, "receiver ignored mismatched finish job=%s expected=%s", job_token, self._job_token)
            return
        _predictions_thread_debug(self._owner, "receiver.handle_finished job=%s error=%s", job_token, error)
        self._watchdog.stop()
        _finish_background_prediction_render(self._owner, chart, render_token, job_token, error)

    @Slot()
    def _handle_timeout(self) -> None:
        active_job_token = getattr(self._owner, "_predictions_background_job_token", None)
        if active_job_token != self._job_token:
            return
        chart_name = _chart_display_name(self._chart)
        logger.error("Predictions warmup timed out for %s", chart_name)
        _predictions_thread_debug(self._owner, "watchdog timeout job=%s chart=%s", self._job_token, chart_name)
        worker = self._worker
        thread = self._thread
        if worker is not None and hasattr(worker, "cancel"):
            try:
                worker.cancel()
            except RuntimeError:
                pass
        if isinstance(thread, QThread):
            try:
                setattr(thread, "_ephemeraldaddy_predictions_timed_out", True)
                thread.requestInterruption()
                thread.quit()
                if thread.isRunning():
                    logger.error(
                        "Predictions warmup did not stop after timeout; leaving worker in background for %s",
                        chart_name,
                    )
                    # Never block or forcibly terminate from the GUI thread.
                    # Some scorers call Python/Qt/SQLite code that cannot be safely
                    # killed with QThread.terminate(), and the previous wait +
                    # terminate path could freeze the whole app after the timeout.
            except RuntimeError:
                pass
        _finish_background_prediction_render(
            self._owner,
            self._chart,
            self._render_token,
            self._job_token,
            "Timed out while preparing predictions. Try reopening the panel; check the terminal log for the stuck scorer.",
        )

    @Slot()
    def cleanup(self) -> None:
        _predictions_thread_debug(self._owner, "receiver.cleanup job=%s", self._job_token)
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
    predictions_button = QPushButton("🔮")
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


def _start_prediction_loading_blink(label: QLabel) -> None:
    """Make a Predictions loading label pulse purple while fresh section data loads."""
    start_prediction_loading_blink(label)


def _prediction_loading_html(message: str) -> str:
    escaped = html.escape(message)
    return (
        "<div style='color:#c77dff; font-style:italic; font-weight:700; "
        "padding:18px 8px; text-align:center;'>"
        f"●&nbsp;{escaped}&nbsp;●"
        "</div>"
    )


def _set_prediction_label_loading(label: QLabel, message: str, *, alignment: Qt.AlignmentFlag | Qt.Alignment | None = None) -> None:
    """Put a section QLabel into the same blinking purple loading state as graph placeholders."""
    label.setText(f"●  {message}  ●")
    if alignment is not None:
        label.setAlignment(alignment)
    _start_prediction_loading_blink(label)


def _clear_layout_for_prediction_placeholder(owner: object, layout_attr: str, canvas_attr: str | None, message: str) -> None:
    """Replace a Predictions section body with a cheap loading placeholder."""
    layout = getattr(owner, layout_attr, None)
    if layout is None:
        return
    clear_layout = getattr(owner, "_clear_layout_widgets", None)
    if callable(clear_layout):
        clear_layout(layout)
    if canvas_attr:
        try:
            setattr(owner, canvas_attr, None)
        except Exception:
            pass
    label = QLabel(f"●  {message}  ●")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignCenter)
    _start_prediction_loading_blink(label)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    layout.addWidget(label)


def _show_predictions_panel_pending_placeholders(owner: object, chart: object | None) -> None:
    """Paint lightweight section placeholders before any cached prediction lookup runs."""
    chart_name = html.escape(_chart_display_name(chart))
    _set_predictions_status(owner, f"Opening Predictions for <b>{chart_name}</b>…")
    traits_label = getattr(owner, "traits_prediction_label", None)
    if isinstance(traits_label, QLabel):
        loading_html = "●  Loading trait predictions…  ●" #for this chart's UID
        try:
            owner._traits_prediction_above_avg_html = loading_html
            owner._traits_prediction_below_avg_html = loading_html
        except Exception:
            pass
        _set_prediction_label_loading(
            traits_label,
            "Loading trait predictions…", #for this chart's UID
            alignment=Qt.AlignLeft | Qt.AlignTop,
        )
        traits_label.setVisible(True)
        traits_label.adjustSize()
        traits_label.setMinimumHeight(traits_label.sizeHint().height())
        rows_model = getattr(owner, "_traits_prediction_rows_model", None)
        if hasattr(rows_model, "set_rows"):
            rows_model.set_rows([])
        traits_table = getattr(owner, "traits_prediction_table", None)
        if hasattr(traits_table, "setVisible"):
            traits_table.setVisible(False)
    _clear_layout_for_prediction_placeholder(
        owner,
        "enneagram_prediction_chart_layout",
        "enneagram_prediction_canvas",
        "Loading cached Enneagram predictions…",
    )
    tritype_label = getattr(owner, "enneagram_prediction_tritype_label", None)
    if isinstance(tritype_label, QLabel):
        _set_prediction_label_loading(
            tritype_label,
            "Loading Enneagram predictions…", #for this chart's UID
            alignment=Qt.AlignLeft | Qt.AlignTop,
        )
    _clear_layout_for_prediction_placeholder(
        owner,
        "dnd_predictions_chart_layout",
        "dnd_prediction_statblock_canvas",
        "Loading cached D&D statblock predictions…",
    )
    summary_label = getattr(owner, "dnd_prediction_top_three_label", None)
    if isinstance(summary_label, QLabel):
        summary_label.setText("<b>D&D Statblock:</b> <span style='color:#c77dff;'>● Loading predictions… ●</span>")  #for this UID
    species_label = getattr(owner, "dnd_prediction_species_label", None)
    if isinstance(species_label, QLabel):
        _set_prediction_label_loading(
            species_label,
            "Loading D&D species predictions…", #for this UID
            alignment=Qt.AlignLeft | Qt.AlignTop,
        )
    class_label = getattr(owner, "dnd_prediction_class_label", None)
    if isinstance(class_label, QLabel):
        _set_prediction_label_loading(
            class_label,
            "Loading D&D class predictions…", #for this UID
            alignment=Qt.AlignLeft | Qt.AlignTop,
        )
    _clear_layout_for_prediction_placeholder(
        owner,
        "dnd_alignment_chart_layout",
        "dnd_prediction_alignment_canvas",
        "Loading cached D&D alignment predictions…",
    )
    alignment_debug_label = getattr(owner, "dnd_prediction_alignment_debug_label", None)
    if isinstance(alignment_debug_label, QLabel):
        alignment_debug_label.setText("<b>Alignment debug deviations from DB norm:</b> <span style='color:#c77dff;'>● Loading predictions… ●</span>") #for this UID

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
        if panel_key == "predictions":
            latest_chart = getattr(owner, "_latest_chart", None)
            if _predictions_panel_render_is_current(owner, latest_chart):
                # Defer schedule() so the tab switch paints before cached sections refresh.
                QTimer.singleShot(0, schedule)
            else:
                _set_predictions_status(owner, f"Opening Predictions for <b>{html.escape(_chart_display_name(latest_chart))}</b>…")
                # Legacy source-test marker: _show_predictions_panel_pending_placeholders(owner, latest_chart)
                # Legacy source-test marker: QTimer.singleShot(0, schedule)
                QTimer.singleShot(16, lambda owner=owner, latest_chart=latest_chart: _show_predictions_panel_pending_placeholders(owner, latest_chart))
                QTimer.singleShot(33, schedule)
        else:
            schedule()


def _predictions_panel_render_is_current(owner: object, chart: object | None) -> bool:
    if chart is None:
        return False
    if not _predictions_panel_has_rendered_content(owner):
        return False
    state = getattr(owner, "_chart_right_panel_state", None)
    if state is None:
        return False
    try:
        render_token = _chart_right_panel_prediction_render_token(owner, chart)
    except Exception:
        return False
    return state.last_render_chart_token == render_token


def _predictions_panel_has_rendered_content(owner: object) -> bool:
    """Return whether Predictions widgets have been rendered beyond constructor defaults.

    The render token can be marked current by background/cache bookkeeping before
    the user ever opens the Predictions tab.  In that case the section labels
    still contain constructor/loading placeholders and the graph canvases have
    never been installed, so opening the tab must perform a real render even if
    the chart/norm token matches.
    """
    traits_label = getattr(owner, "traits_prediction_label", None)
    traits_text = traits_label.text() if isinstance(traits_label, QLabel) else ""
    traits_has_default_placeholder = "Loading trait predictions" in traits_text  #for this UID

    tritype_label = getattr(owner, "enneagram_prediction_tritype_label", None)
    tritype_text = tritype_label.text() if isinstance(tritype_label, QLabel) else ""
    tritype_has_default_placeholder = tritype_text.strip() in {
        "Predicted Tritype: —",
        "<b>Predicted Tritype:</b> —",
    }
    tritype_has_default_placeholder = (
        tritype_has_default_placeholder
        or "Loading Enneagram predictions" in tritype_text  #for this UID
    )

    species_label = getattr(owner, "dnd_prediction_species_label", None)
    species_text = species_label.text() if isinstance(species_label, QLabel) else ""
    class_label = getattr(owner, "dnd_prediction_class_label", None)
    class_text = class_label.text() if isinstance(class_label, QLabel) else ""
    dnd_has_default_placeholders = (
        (
            "Top 3 Species/Subspecies" in species_text
            and species_text.rstrip().endswith("—")
            and "Top 3 Classes" in class_text
            and class_text.rstrip().endswith("—")
        )
        or (
            "Loading D&D species predictions" in species_text  #for this UID
            and "Loading D&D class predictions" in class_text  #for this UID
        )
    )

    has_prediction_canvas = any(
        getattr(owner, attr, None) is not None
        for attr in (
            "enneagram_prediction_canvas",
            "dnd_prediction_statblock_canvas",
            "dnd_prediction_alignment_canvas",
        )
    )
    return has_prediction_canvas or not (
        traits_has_default_placeholder
        and tritype_has_default_placeholder
        and dnd_has_default_placeholders
    )


def _prediction_chart_uid(chart: object) -> str:
    for attr in ("chart_uid", "permanent_uid", "uid", "UID"):
        value = str(getattr(chart, attr, "") or "").strip()
        if value:
            return value.upper()
    return ""


def _chart_right_panel_prediction_render_token(owner: object, chart: object) -> str:
    """Return a UID-scoped token for prediction renders in the right-panel tab."""
    chart_uid = _prediction_chart_uid(chart)
    chart_scope = f"uid:{chart_uid}" if chart_uid else f"object:{id(chart)}"
    dt_value = getattr(chart, "dt", None)
    dt_token = dt_value.isoformat() if dt_value is not None else "nodt"
    chart_token = repr({
        "scope": chart_scope,
        "dt": dt_token,
        "dt_local": str(getattr(chart, "dt_local", "") or ""),
        "lat": str(getattr(chart, "lat", "") or ""),
        "lon": str(getattr(chart, "lon", "") or ""),
        "birth_place": str(getattr(chart, "birth_place", "") or ""),
        "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
        "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
        "retcon_hour": getattr(chart, "retcon_hour", None),
        "retcon_minute": getattr(chart, "retcon_minute", None),
        "rectification_range_used": bool(getattr(chart, "rectification_range_used", False)),
        "rectification_range_start_minute": getattr(chart, "rectification_range_start_minute", None),
        "rectification_range_end_minute": getattr(chart, "rectification_range_end_minute", None),
        "chart_uses_houses": bool(chart_uses_houses(chart)),
    })

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


def _finish_background_prediction_render(
    owner: object,
    chart: object,
    render_token: str,
    job_token: str,
    error: object,
) -> None:
    active_job_token = getattr(owner, "_predictions_background_job_token", None)
    if active_job_token != job_token:
        _predictions_thread_debug(owner, "finish ignored inactive job=%s active=%s", job_token, active_job_token)
        return
    setattr(owner, "_predictions_background_render_token", None)
    setattr(owner, "_predictions_background_job_token", None)
    setattr(owner, "_predictions_background_chart", None)
    progress = getattr(owner, "_predictions_background_progress", None)
    if progress is not None:
        update_app_loading_progress(progress, "Rendering Predictions…", 95)
        close_app_loading_progress(progress)
        setattr(owner, "_predictions_background_progress", None)

    chart_name = _chart_display_name(chart)
    if error is not None:
        _predictions_thread_debug(owner, "finish failed job=%s chart=%s error=%s", job_token, chart_name, error)
        _set_predictions_status(owner, f"Predictions for <b>{html.escape(chart_name)}</b> failed: {html.escape(str(error))}")
        return

    _predictions_thread_debug(owner, "finish applying GUI render job=%s chart=%s", job_token, chart_name)
    state = getattr(owner, "_chart_right_panel_state", None)
    if getattr(owner, "_latest_chart", None) is chart:
        owner._render_enneagram_predictions(chart)
        owner._render_dndification_predictions(chart)
        schedule_metric_refreshes = getattr(owner, "_schedule_deferred_visible_metric_canvas_layout_refreshes", None)
        if callable(schedule_metric_refreshes):
            schedule_metric_refreshes((0, 25, 75, 150, 300, 600))
        if state is not None:
            state.last_render_chart_token = render_token
    _set_predictions_status(
        owner,
        f"Predictions for <b>{html.escape(chart_name)}</b> are ready: "
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
    _predictions_thread_debug(owner, "retained job thread=%s worker=%s receiver=%s active_jobs=%s", id(thread), id(worker), id(receiver) if receiver is not None else None, len(jobs))


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
                _predictions_thread_debug(owner, "forgot job thread=%s worker=%s remaining_jobs=%s", id(thread), id(worker), len(jobs))
                break
    if getattr(owner, "_predictions_background_thread", None) is thread:
        setattr(owner, "_predictions_background_thread", None)
    if getattr(owner, "_predictions_background_worker", None) is worker:
        setattr(owner, "_predictions_background_worker", None)
    if getattr(owner, "_predictions_background_receiver", None) is receiver:
        setattr(owner, "_predictions_background_receiver", None)


def stop_background_prediction_render(owner: object, wait_msecs: int | None = None) -> None:
    """Cancel in-flight Predictions warmup threads before owner or thread wrappers are destroyed."""
    _predictions_thread_debug(owner, "stop requested wait_msecs=%s", wait_msecs)
    setattr(owner, "_predictions_background_render_token", None)
    setattr(owner, "_predictions_background_job_token", None)
    setattr(owner, "_predictions_background_chart", None)
    progress = getattr(owner, "_predictions_background_progress", None)
    if progress is not None:
        close_app_loading_progress(progress)
        setattr(owner, "_predictions_background_progress", None)
    jobs = list(getattr(owner, "_predictions_background_jobs", []) or [])
    active_thread = getattr(owner, "_predictions_background_thread", None)
    active_worker = getattr(owner, "_predictions_background_worker", None)
    active_receiver = getattr(owner, "_predictions_background_receiver", None)
    if isinstance(active_thread, QThread) and all(
        (job[0] if isinstance(job, tuple) and len(job) >= 1 else None) is not active_thread
        for job in jobs
    ):
        jobs.append((active_thread, active_worker, active_receiver))
    retained_jobs: list[tuple[object, object, object]] = []
    for job in jobs:
        thread = job[0] if isinstance(job, tuple) and len(job) >= 1 else None
        worker = job[1] if isinstance(job, tuple) and len(job) >= 2 else None
        receiver = job[2] if isinstance(job, tuple) and len(job) >= 3 else None
        if not isinstance(thread, QThread):
            continue
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()
                timed_out = bool(getattr(thread, "_ephemeraldaddy_predictions_timed_out", False))
                if wait_msecs is None and not timed_out:
                    thread.wait()
                else:
                    timeout = (
                        PREDICTIONS_BACKGROUND_TIMEOUT_STOP_WAIT_MS
                        if wait_msecs is None
                        else max(0, int(wait_msecs))
                    )
                    if not thread.wait(timeout) and timed_out:
                        logger.error(
                            "Timed-out Predictions warmup thread still running during cleanup; "
                            "retaining references and not terminating from GUI thread"
                        )
                        retained_jobs.append((thread, worker, receiver))
        except RuntimeError:
            continue
    if isinstance(getattr(owner, "_predictions_background_jobs", None), list):
        owner._predictions_background_jobs[:] = retained_jobs
    if retained_jobs:
        retained_thread, retained_worker, retained_receiver = retained_jobs[0]
        setattr(owner, "_predictions_background_thread", retained_thread)
        setattr(owner, "_predictions_background_worker", retained_worker)
        setattr(owner, "_predictions_background_receiver", retained_receiver)
    else:
        setattr(owner, "_predictions_background_thread", None)
        setattr(owner, "_predictions_background_worker", None)
        setattr(owner, "_predictions_background_receiver", None)
    setattr(owner, "_predictions_background_job_token", None)


def _start_background_prediction_render(owner: object, chart: object, render_token: str, sections: set[str] | None = None) -> None:
    chart_name = _chart_display_name(chart)
    _predictions_thread_debug(owner, "start requested chart=%s render_token=%s", chart_name, render_token)
    _set_predictions_status(owner, f"Loading Predictions for <b>{html.escape(chart_name)}</b> in the background…")
    existing_progress = getattr(owner, "_predictions_background_progress", None)
    close_app_loading_progress(existing_progress)
    progress_parent = owner if isinstance(owner, QWidget) else None
    progress = create_app_loading_progress(
        parent=progress_parent,
        title="Loading Predictions",
        message=f"Preparing Predictions for {chart_name}…",
    )
    setattr(owner, "_predictions_background_progress", progress)
    thread = QThread()
    job_token = uuid.uuid4().hex
    worker = _PredictionsWarmupWorker(owner, chart, render_token, job_token, sections=sections)
    receiver = _PredictionsWarmupReceiver(owner, chart, render_token, job_token)
    receiver.set_job(thread, worker)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.progress.connect(receiver.handle_progress, Qt.QueuedConnection)
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
    setattr(owner, "_predictions_background_job_token", job_token)
    _retain_background_prediction_job(owner, thread, worker, receiver)
    receiver.start_watchdog()
    _predictions_thread_debug(owner, "thread.start job=%s thread=%s worker=%s receiver=%s", job_token, id(thread), id(worker), id(receiver))
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
        if (
            state is not None
            and state.last_render_chart_token == render_token
            and _predictions_panel_has_rendered_content(owner)
        ):
            return
        render_traits = getattr(owner, "_render_traits_predictions", None)
        if callable(render_traits):
            render_traits(chart)
        owner._render_enneagram_predictions(chart)
        owner._render_dndification_predictions(chart)
        if state is not None:
            state.last_render_chart_token = render_token
        _set_predictions_status(
            owner,
            f"Showing cached Predictions for <b>{html.escape(_chart_display_name(chart))}</b>. "
            "Use Calculate/Recalculate only when you want to refresh them.",
        )
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
