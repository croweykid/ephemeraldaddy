from __future__ import annotations

import datetime
import html
import statistics
from collections import Counter
from typing import Callable

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QLinearGradient, QPainter, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QStyleOptionSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.chart import Chart, apply_unknown_sign_metadata
from ephemeraldaddy.gui.features.charts.presentation import sign_for_longitude
from ephemeraldaddy.core.ephemeris import planetary_positions
from ephemeraldaddy.core.interpretations import (
    PLANET_COLORS,
    PLANET_GLYPHS,
    PLANET_ORDER,
    SIGN_COLORS,
    ZODIAC_NAMES,
    ZODIAC_SIGNS,
)

from ephemeraldaddy.gui.features.charts.anagrams import build_anagrams_section
from ephemeraldaddy.gui.features.charts.loading_overlay import ChartLoadingOverlay
from ephemeraldaddy.gui.features.charts.cv_right_panel_stack import build_chart_right_panel_stack

CHART_INFO_PANEL_BUTTON_ATTRS: dict[str, str] = {
    "chart_info": "chart_info_toggle_button",
    "comments": "chart_comments_toggle_button",
    "rectification": "chart_rectification_toggle_button",
    "biography": "chart_bio_toggle_button",
    "source": "chart_source_toggle_button",
}

CHART_INFO_PANEL_CONTENT_ATTRS: dict[str, str] = {
    "chart_info": "chart_info_output",
    "comments": "comments_edit",
    "rectification": "rectification_edit",
    "biography": "biography_edit",
    "source": "source_edit",
}


class _SentimentEdgeSlider(QSlider):
    """One-sided sentiment handle for chart-view relevance spectrum."""

    committed = Signal()

    def __init__(self, side: str, emoji: str, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self._side = side
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setRange(0, 10)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setTickInterval(5)
        self.setValue(1)
        self.setMinimumHeight(34)
        self.setStyleSheet(
            "QSlider {"
            "background: transparent;"
            "}"
            "QSlider::groove:horizontal {"
            "height: 12px;"
            "border-radius: 6px;"
            "background: transparent;"
            "}"
            "QSlider::handle:horizontal {"
            "background: transparent;"
            "border: none;"
            "width: 20px;"
            "margin: -8px 0px;"
            "}"
        )
        self._emoji_marker = QLabel(self)
        self._emoji_marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._emoji_marker.setAlignment(Qt.AlignCenter)
        self._emoji_marker.setFixedSize(24, 24)
        self._emoji_marker.setText(emoji)
        self.valueChanged.connect(self._position_emoji_marker)
        self.sliderReleased.connect(self.committed.emit)
        self._position_emoji_marker()

    def intensity(self) -> int:
        return int(self.value())

    def set_intensity(self, value: int) -> None:
        normalized = max(0, min(10, int(value)))
        self.setValue(normalized)

    def refresh_marker_position(self) -> None:
        self._position_emoji_marker()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_emoji_marker()

    def _position_emoji_marker(self) -> None:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        handle_rect = self.style().subControlRect(
            QStyle.CC_Slider,
            opt,
            QStyle.SC_SliderHandle,
            self,
        )
        x = handle_rect.center().x() - (self._emoji_marker.width() // 2)
        y = handle_rect.center().y() - (self._emoji_marker.height() // 2)
        self._emoji_marker.move(x, y)


class _SentimentIntensitySpectrum(QWidget):
    """Dual-handle sentiment spectrum visualization for Chart View."""

    valuesCommitted = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(72)
        self._positive_slider = _SentimentEdgeSlider("positive", "💖", self)
        self._negative_slider = _SentimentEdgeSlider("negative", "💔", self)
        self._positive_slider.valueChanged.connect(self.update)
        self._negative_slider.valueChanged.connect(self.update)
        self._positive_slider.committed.connect(self._emit_committed_values)
        self._negative_slider.committed.connect(self._emit_committed_values)

    def positive_intensity(self) -> int:
        return self._positive_slider.intensity()

    def negative_intensity(self) -> int:
        return self._negative_slider.intensity()

    def set_values(self, positive_value: int, negative_value: int) -> None:
        self._positive_slider.blockSignals(True)
        self._negative_slider.blockSignals(True)
        self._positive_slider.set_intensity(positive_value)
        self._negative_slider.set_intensity(negative_value)
        self._positive_slider.blockSignals(False)
        self._negative_slider.blockSignals(False)
        self._positive_slider.refresh_marker_position()
        self._negative_slider.refresh_marker_position()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        half_width = max(1, self.width() // 2)
        self._negative_slider.setGeometry(QRect(0, 0, half_width, self.height()))
        self._positive_slider.setGeometry(
            QRect(half_width, 0, max(1, self.width() - half_width), self.height())
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        groove_rect = self.rect().adjusted(10, 18, -10, -(self.height() - 30))
        gradient = QLinearGradient(groove_rect.topLeft(), groove_rect.topRight())
        gradient.setColorAt(0.0, QColor("#c62828"))
        gradient.setColorAt(0.5, QColor("#6f6f6f"))
        gradient.setColorAt(1.0, QColor("#1565c0"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(groove_rect, 6, 6)
        painter.setPen(QColor("#ffd54f"))
        zero_x = self.width() // 2
        painter.drawLine(zero_x, groove_rect.top(), zero_x, groove_rect.bottom())
        painter.setPen(QColor("#ef9a9a"))
        painter.drawText(groove_rect.left() - 2, groove_rect.top() - 4, "🤬")
        painter.setPen(QColor("#90caf9"))
        painter.drawText(groove_rect.right() - 14, groove_rect.top() - 4, "🫂")
        painter.setPen(QColor("#d9d9d9"))
        painter.drawText(
            self.rect().adjusted(10, groove_rect.bottom() + 8, -10, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            (
                f"Frustration: {self.negative_intensity()} // "
                f"Enjoyment: {self.positive_intensity()}    "
            ),
        )

    def _average_x_position(self) -> int:
        signed_positive = self._positive_slider.intensity()
        signed_negative = -self._negative_slider.intensity()
        average_value = (signed_positive + signed_negative) / 2.0
        groove_width = max(1, self.width() - 20)
        normalized = (average_value - (-10.0)) / 20.0
        x_value = 10 + int(round(normalized * groove_width))
        return max(10, min(self.width() - 10, x_value))

    def _emit_committed_values(self) -> None:
        self.valuesCommitted.emit(self.positive_intensity(), self.negative_intensity())


def _install_chart_view_sentiment_relevance_spectrum(owner: QWidget) -> None:
    """Replace chart-view relevance sentiment spinbox rows with spectrum control."""
    positive_spinbox = getattr(owner, "positive_sentiment_intensity_spin", None)
    negative_spinbox = getattr(owner, "negative_sentiment_intensity_spin", None)
    on_sentiment_changed = getattr(owner, "_on_sentiment_metric_changed", None)
    if not isinstance(positive_spinbox, QSpinBox) or not isinstance(negative_spinbox, QSpinBox):
        return
    if not callable(on_sentiment_changed):
        return
    positive_spinbox.setRange(0, 10)
    negative_spinbox.setRange(0, 10)

    parent_widget = positive_spinbox.parentWidget()
    if parent_widget is None:
        return
    grid_layout = parent_widget.layout()
    if not isinstance(grid_layout, QGridLayout):
        return
    if hasattr(owner, "sentiment_intensity_spectrum"):
        return

    for row in (0, 1):
        for col in (0, 1):
            item = grid_layout.itemAtPosition(row, col)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setVisible(False)

    spectrum_label = QLabel("Sentiment Intensity Spectrum:")
    spectrum = _SentimentIntensitySpectrum(parent_widget)
    spectrum.setToolTip(
        "Drag 💖 and 💔. Values save when you release a handle."
    )
    spectrum.set_values(positive_spinbox.value(), negative_spinbox.value())

    def _sync_from_spinboxes(_value: int) -> None:
        spectrum.set_values(positive_spinbox.value(), negative_spinbox.value())

    def _commit_to_spinboxes(positive_value: int, negative_value: int) -> None:
        if (
            positive_spinbox.value() == int(positive_value)
            and negative_spinbox.value() == int(negative_value)
        ):
            return
        positive_spinbox.setValue(int(positive_value))
        negative_spinbox.setValue(int(negative_value))
        on_sentiment_changed(0)

    positive_spinbox.valueChanged.connect(_sync_from_spinboxes)
    negative_spinbox.valueChanged.connect(_sync_from_spinboxes)
    spectrum.valuesCommitted.connect(_commit_to_spinboxes)

    owner.sentiment_intensity_spectrum = spectrum
    grid_layout.addWidget(spectrum_label, 0, 0, 1, 2)
    grid_layout.addWidget(spectrum, 1, 0, 1, 2)

def format_unknown_positions_summary_html(
    chart: Chart | None,
    *,
    text_color: str = "#f5f5f5",
    separator_color: str = "#9a9a9a",
    houses_unknown_font_px: int = 10,
) -> str:
    """Build Chart View unknown-position summary HTML for the placeholder row."""
    if not isinstance(chart, Chart):
        return ""

    apply_unknown_sign_metadata(chart)
    birthtime_unknown = bool(getattr(chart, "birthtime_unknown", False))
    signs_unknown = bool(getattr(chart, "signs_unknown", False))
    if not birthtime_unknown and not signs_unknown:
        return ""

    safe_text_color = html.escape(text_color)
    safe_separator_color = html.escape(separator_color)
    houses_unknown_html = (
        f'<span style="color: {safe_separator_color}; '
        f'font-size: {max(8, int(houses_unknown_font_px))}px;">houses unknown</span>'
    )
    if not signs_unknown:
        return houses_unknown_html if birthtime_unknown else ""

    tzinfo = getattr(getattr(chart, "dt", None), "tzinfo", None)
    if tzinfo is None:
        return houses_unknown_html

    base_date = chart.dt.date()
    midnight = datetime.datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        0,
        0,
        tzinfo=tzinfo,
    )
    pre_midnight = datetime.datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        23,
        59,
        tzinfo=tzinfo,
    )
    positions_midnight = planetary_positions(midnight, chart.lat, chart.lon)
    positions_pre_midnight = planetary_positions(pre_midnight, chart.lat, chart.lon)
    sign_to_glyph = {name: glyph for name, glyph in zip(ZODIAC_NAMES, ZODIAC_SIGNS)}
    unknown_bodies = set(getattr(chart, "unknown_signs", []) or [])
    ordered_bodies = [
        body
        for body in PLANET_ORDER
        if body in unknown_bodies and body in positions_midnight and body in positions_pre_midnight
    ]
    ordered_bodies.extend(
        sorted(
            body
            for body in unknown_bodies
            if body not in ordered_bodies and body in positions_midnight and body in positions_pre_midnight
        )
    )

    def _span(text: str, color: str) -> str:
        return f'<span style="color: {html.escape(color)};">{html.escape(text)}</span>'

    segments: list[str] = []
    for body in ordered_bodies:
        sign_start = sign_for_longitude(positions_midnight[body])
        sign_end = sign_for_longitude(positions_pre_midnight[body])
        if sign_start == sign_end:
            continue
        body_color = PLANET_COLORS.get(body, safe_text_color)
        sign_start_color = SIGN_COLORS.get(sign_start, safe_text_color)
        sign_end_color = SIGN_COLORS.get(sign_end, safe_text_color)
        body_glyph = PLANET_GLYPHS.get(body, body)
        sign_start_glyph = sign_to_glyph.get(sign_start, sign_start)
        sign_end_glyph = sign_to_glyph.get(sign_end, sign_end)
        segments.append(
            f"{_span(body_glyph, body_color)}"
            f"{_span(':', safe_separator_color)}"
            f"{_span(sign_start_glyph, sign_start_color)}"
            f"{_span('/', safe_separator_color)}"
            f"{_span(sign_end_glyph, sign_end_color)}"
        )

    pipe_separator = _span(" | ", safe_separator_color)
    if segments:
        return f"{pipe_separator.join(segments)}{pipe_separator}{houses_unknown_html}"
    return houses_unknown_html

class ChartViewUndoController:
    """Adds Chart View-wide Ctrl/Cmd+Z support for text fields and dropdowns."""

    _COMBO_UNDO_STACK_PROP = "_chart_view_combo_undo_stack"
    _COMBO_LAST_INDEX_PROP = "_chart_view_combo_last_index"

    def __init__(self, *, owner: QWidget, scope_widget: QWidget) -> None:
        self._owner = owner
        self._scope_widget = scope_widget
        self._combo_undoing = False
        self._shortcuts: list[QShortcut] = []

    def install(self) -> None:
        self._install_combo_tracking()
        self._install_shortcuts()

    def _install_combo_tracking(self) -> None:
        for combo in self._scope_widget.findChildren(QComboBox):
            combo.setProperty(self._COMBO_UNDO_STACK_PROP, [])
            combo.setProperty(self._COMBO_LAST_INDEX_PROP, combo.currentIndex())
            combo.currentIndexChanged.connect(
                lambda _index, target_combo=combo: self._record_combo_change(target_combo)
            )

    def _install_shortcuts(self) -> None:
        for sequence in ("Ctrl+Z", "Meta+Z"):
            shortcut = QShortcut(QKeySequence(sequence), self._owner)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.undo_last_change)
            self._shortcuts.append(shortcut)

    def _record_combo_change(self, combo: QComboBox) -> None:
        if self._combo_undoing:
            return
        previous_index = combo.property(self._COMBO_LAST_INDEX_PROP)
        current_index = combo.currentIndex()
        if previous_index is None or previous_index == current_index:
            combo.setProperty(self._COMBO_LAST_INDEX_PROP, current_index)
            return
        undo_stack = list(combo.property(self._COMBO_UNDO_STACK_PROP) or [])
        undo_stack.append(int(previous_index))
        combo.setProperty(self._COMBO_UNDO_STACK_PROP, undo_stack[-100:])
        combo.setProperty(self._COMBO_LAST_INDEX_PROP, current_index)

    def undo_last_change(self) -> None:
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            focused_widget.undo()
            return
        if isinstance(focused_widget, (QPlainTextEdit, QTextEdit)):
            focused_widget.undo()
            return
        combo = self._resolve_combo_widget(focused_widget)
        if combo is not None:
            self._undo_combo_change(combo)

    def _resolve_combo_widget(self, widget: QWidget | None) -> QComboBox | None:
        if widget is None:
            return None
        if isinstance(widget, QComboBox):
            return widget
        combo = widget.parent()
        return combo if isinstance(combo, QComboBox) else None

    def _undo_combo_change(self, combo: QComboBox) -> None:
        undo_stack = list(combo.property(self._COMBO_UNDO_STACK_PROP) or [])
        if not undo_stack:
            return
        previous_index = undo_stack.pop()
        self._combo_undoing = True
        try:
            combo.setCurrentIndex(previous_index)
        finally:
            self._combo_undoing = False
        combo.setProperty(self._COMBO_UNDO_STACK_PROP, undo_stack)
        combo.setProperty(self._COMBO_LAST_INDEX_PROP, combo.currentIndex())


def install_chart_view_undo_shortcuts(*, owner: QWidget, scope_widget: QWidget) -> ChartViewUndoController:
    """Install Chart View undo shortcuts for text fields and dropdown controls."""
    controller = ChartViewUndoController(owner=owner, scope_widget=scope_widget)
    controller.install()
    return controller


def install_chart_info_panel_content_observers(owner: QWidget) -> None:
    """Attach content-change observers that keep Chart View panel tab styling in sync."""
    connected_signals: set[int] = set()
    for content_attr in CHART_INFO_PANEL_CONTENT_ATTRS.values():
        content_widget = getattr(owner, content_attr, None)
        if not isinstance(content_widget, (QTextEdit, QPlainTextEdit)):
            continue
        signal_id = id(content_widget)
        if signal_id in connected_signals:
            continue
        content_widget.textChanged.connect(owner._refresh_chart_info_panel_toggle_buttons)
        connected_signals.add(signal_id)


def refresh_chart_info_panel_toggle_button_styles(owner: QWidget) -> None:
    """Style Chart View panel tab buttons by content presence and active tab state."""
    active_mode = getattr(owner, "_chart_info_panel_mode", "comments")
    has_content_by_mode: dict[str, bool] = {}
    for mode, content_attr in CHART_INFO_PANEL_CONTENT_ATTRS.items():
        content_widget = getattr(owner, content_attr, None)
        if isinstance(content_widget, (QTextEdit, QPlainTextEdit)):
            has_content_by_mode[mode] = bool(content_widget.toPlainText().strip())
        else:
            has_content_by_mode[mode] = False

    for mode, button_attr in CHART_INFO_PANEL_BUTTON_ATTRS.items():
        button = getattr(owner, button_attr, None)
        if not isinstance(button, QPushButton):
            continue

        mode_is_active = mode == active_mode
        mode_has_content = has_content_by_mode.get(mode, False)
        background_rule = "background-color: #424f3d;" if mode_has_content else "" #lighter gray instead of #2f6a3f #green, but consider: #95a78e or #52634b or #424f3d
        border_rule = (
            "border: 1px solid #8fd3a1; border-radius: 4px;"
            if mode_is_active
            else "border: 1px solid transparent; border-radius: 4px;"
        )
        font_weight = "700" if mode_is_active else "400"
        style = (
            "QPushButton { "
            f"font-weight: {font_weight}; padding: 2px 8px; {background_rule} {border_rule}"
            "}"
        )
        button.blockSignals(True)
        button.setChecked(mode_is_active)
        button.blockSignals(False)
        button.setStyleSheet(style)


def resolve_weight_distribution_stats(values: list[float]) -> tuple[float | None, float, float, float, float] | None:
    numeric_values = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return None
    frequency_by_value = Counter(numeric_values)
    max_frequency = max(frequency_by_value.values(), default=0)
    modal_values = [
        value
        for value, frequency in frequency_by_value.items()
        if frequency == max_frequency
    ]
    mode_value: float | None = None
    if len(modal_values) == 1 and max_frequency > 1:
        mode_value = float(modal_values[0])
    avg_value = statistics.fmean(numeric_values)
    median_value = statistics.median(numeric_values)
    min_value = min(numeric_values)
    max_value = max(numeric_values)
    return (mode_value, avg_value, median_value, min_value, max_value)


def draw_weight_distribution_reference_lines(ax, values: list[float]) -> None:
    stats = resolve_weight_distribution_stats(values)
    if stats is None:
        return
    mode_value, avg_value, median_value, _min_value, _max_value = stats
    reference_lines: list[tuple[float, str]] = [
        (avg_value, "#ff4d4d"),
        (median_value, "#b22222"),
    ]
    if mode_value is not None:
        reference_lines.append((mode_value, "#ff7f7f"))
    for line_value, line_color in reference_lines:
        ax.axhline(
            y=line_value,
            color=line_color,
            linestyle="--",
            linewidth=1.1,
            alpha=0.95,
            zorder=1.5,
        )


def format_weight_distribution_html(
    values: list[float],
    *,
    metric_color_resolver: Callable[[str, float], str | None] | None = None,
) -> str:
    def _colored_metric(label: str, metric_key: str, value: float, value_text: str) -> str:
        color = metric_color_resolver(metric_key, value) if metric_color_resolver is not None else None
        if color:
            return f"<b>{label}:</b> <span style=\"color: {color};\">{value_text}</span>"
        return f"<b>{label}:</b> {value_text}"

    stats = resolve_weight_distribution_stats(values)
    if stats is None:
        return (
            f"{_colored_metric('Avg Weight', 'avg', 0.0, '0')}, "
            f"{_colored_metric('Median', 'median', 0.0, '0')}"
            "<br><b>Min:</b> 0, <b>Max:</b> 0, "
            f"{_colored_metric('Range', 'range', 0.0, '0')}, "
            f'<span title="the sum of all this chart\'s body weights">{_colored_metric("Total", "total", 0.0, "0")}</span>'
        )
    _mode_value, avg_value, median_value, min_value, max_value = stats
    total_value = sum(float(value) for value in values if isinstance(value, (int, float)))
    total_value_rounded = int(round(total_value))
    range_value = max_value - min_value
    return (
        f"{_colored_metric('Avg Weight', 'avg', avg_value, f'{avg_value:.2f}')}, "
        f"{_colored_metric('Median', 'median', median_value, f'{median_value:.2f}')}"
        f"<br><b>Min:</b> {min_value:.2f}, "
        f"<b>Max:</b> {max_value:.2f}, "
        f"{_colored_metric('Range', 'range', range_value, f'{range_value:.2f}')}, "
        f'<span title="the sum of all this chart\'s body weights">{_colored_metric("Total", "total", total_value, f"{total_value_rounded:,}")}</span>'
    )


def _require_owner_attrs(owner: QWidget, attrs: tuple[str, ...], *, context: str) -> None:
    """Fail fast with a clear error when Chart View helper preconditions are not met."""
    missing = [name for name in attrs if not hasattr(owner, name)]
    if not missing:
        return
    missing_rendered = ", ".join(sorted(missing))
    raise RuntimeError(
        f"{context} requires owner to define: {missing_rendered}"
    )


def build_chart_view_left_panel(
    owner: QWidget,
    *,
    main_splitter,
    apply_chart_data_highlighter: Callable[..., object],
) -> None:
    """Build Chart View's left chart-preview/info panel and attach it to splitter."""
    _require_owner_attrs(
        owner,
        (
            "manage_button",
            "database_view_button",
            "_set_chart_info_panel_mode",
        ),
        context="build_chart_view_left_panel",
    )

    chart_panel = QWidget()
    chart_panel_layout = QVBoxLayout()
    chart_panel.setLayout(chart_panel_layout)
    chart_panel.setMinimumWidth(280)

    owner.chart_container = QWidget()
    owner.chart_container_layout = QVBoxLayout()
    owner.chart_container_layout.setSpacing(0)
    owner.chart_canvas_container = QWidget()
    owner.chart_canvas_container_layout = QVBoxLayout()
    owner.chart_canvas_container_layout.setSpacing(0)
    owner.chart_canvas_container_layout.setContentsMargins(0, 0, 0, 0)
    owner.chart_canvas_container.setLayout(owner.chart_canvas_container_layout)

    owner.chart_canvas_overlay_container = QWidget()
    owner.chart_canvas_overlay_layout = QGridLayout()
    owner.chart_canvas_overlay_layout.setContentsMargins(0, 0, 0, 0)
    owner.chart_canvas_overlay_layout.setSpacing(0)
    owner.chart_canvas_overlay_container.setLayout(owner.chart_canvas_overlay_layout)
    owner.chart_loading_overlay = ChartLoadingOverlay(owner)
    owner.chart_canvas_overlay_layout.addWidget(owner.chart_canvas_container, 0, 0)

    chart_canvas_nav_buttons = QWidget()
    chart_canvas_nav_buttons_layout = QHBoxLayout()
    chart_canvas_nav_buttons_layout.setContentsMargins(0, 0, 0, 0)
    chart_canvas_nav_buttons_layout.setSpacing(6)
    chart_canvas_nav_buttons.setLayout(chart_canvas_nav_buttons_layout)
    chart_canvas_nav_buttons_layout.addWidget(owner.manage_button, 0, Qt.AlignLeft)
    chart_canvas_nav_buttons_layout.addWidget(owner.database_view_button, 0, Qt.AlignLeft)
    owner.chart_canvas_overlay_layout.addWidget(
        chart_canvas_nav_buttons,
        0,
        0,
        alignment=Qt.AlignTop | Qt.AlignLeft,
    )
    owner.chart_canvas_overlay_layout.setContentsMargins(6, 6, 0, 0)
    owner.manage_button.raise_()
    owner.database_view_button.raise_()
    owner.chart_container_layout.addWidget(owner.chart_canvas_overlay_container, 1)
    owner.chart_container.setLayout(owner.chart_container_layout)
    chart_panel_layout.addWidget(owner.chart_container, 1)

    chart_info_header = QWidget()
    chart_info_header_layout = QHBoxLayout()
    chart_info_header_layout.setContentsMargins(0, 0, 0, 0)
    chart_info_header_layout.setSpacing(6)
    chart_info_header.setLayout(chart_info_header_layout)

    owner.chart_info_toggle_button = QPushButton("ⓘ")
    owner.chart_info_toggle_button.setCheckable(True)
    owner.chart_info_toggle_button.setCursor(Qt.PointingHandCursor)
    owner.chart_info_toggle_button.setMinimumHeight(24)
    owner.chart_info_toggle_button.clicked.connect(
        lambda: owner._set_chart_info_panel_mode("chart_info")
    )

    owner.chart_bio_toggle_button = QPushButton("👤") #Biography / #Bio
    owner.chart_bio_toggle_button.setCheckable(True)
    owner.chart_bio_toggle_button.setCursor(Qt.PointingHandCursor)
    owner.chart_bio_toggle_button.setMinimumHeight(24)
    owner.chart_bio_toggle_button.clicked.connect(
        lambda: owner._set_chart_info_panel_mode("biography")
    )

    owner.chart_comments_toggle_button = QPushButton("💭") #Personal thoughts / #Comments
    owner.chart_comments_toggle_button.setCheckable(True)
    owner.chart_comments_toggle_button.setCursor(Qt.PointingHandCursor)
    owner.chart_comments_toggle_button.setMinimumHeight(24)
    owner.chart_comments_toggle_button.clicked.connect(
        lambda: owner._set_chart_info_panel_mode("comments")
    )

    owner.chart_rectification_toggle_button = QPushButton("⏳💬") #Rectification Notes
    owner.chart_rectification_toggle_button.setCheckable(True)
    owner.chart_rectification_toggle_button.setCursor(Qt.PointingHandCursor)
    owner.chart_rectification_toggle_button.setMinimumHeight(24)
    owner.chart_rectification_toggle_button.clicked.connect(
        lambda: owner._set_chart_info_panel_mode("rectification")
    )

    owner.chart_source_toggle_button = QPushButton("🌐") #Source
    owner.chart_source_toggle_button.setCheckable(True)
    owner.chart_source_toggle_button.setCursor(Qt.PointingHandCursor)
    owner.chart_source_toggle_button.setMinimumHeight(24)
    owner.chart_source_toggle_button.clicked.connect(
        lambda: owner._set_chart_info_panel_mode("source")
    )

    chart_info_header_layout.addWidget(owner.chart_info_toggle_button, 0)
    chart_info_header_layout.addWidget(owner.chart_bio_toggle_button, 0)
    chart_info_header_layout.addWidget(owner.chart_comments_toggle_button, 0)
    chart_info_header_layout.addWidget(owner.chart_rectification_toggle_button, 0)
    chart_info_header_layout.addWidget(owner.chart_source_toggle_button, 0)
    chart_info_header_layout.addStretch(1)
    chart_panel_layout.addWidget(chart_info_header, 0)

    owner.chart_info_output = QTextEdit()
    owner.chart_info_output.setReadOnly(True)
    owner.chart_info_output.setPlaceholderText(
        "Click the ⓘ next to a position or aspect to see details/interpretation."
    )
    owner.chart_info_output.setMinimumHeight(140)
    owner._chart_info_highlighter = apply_chart_data_highlighter(
        owner.chart_info_output,
        emphasize_dnd_class_headers=True,
        emphasize_species_info_headers=True,
    )
    owner.chart_info_content_stack = QStackedWidget()
    owner.chart_info_content_stack.addWidget(owner.chart_info_output)
    chart_panel_layout.addWidget(owner.chart_info_content_stack, 0)
    main_splitter.addWidget(chart_panel)

def build_chart_view_middle_header_controls(
    owner: QWidget,
    *,
    middle_layout: QVBoxLayout,
) -> None:
    """Build Chart View middle-panel top header action controls."""
    _require_owner_attrs(
        owner,
        (
            "on_open_bazi_window",
            "on_get_human_design_info",
            "on_get_current_transits",
            "on_get_synastry_chart",
            "_show_similar_charts_popout",
            "on_create_gemstone_chartwheel",
            "on_open_chart_predictor_quiz",
        ),
        context="build_chart_view_middle_header_controls",
    )

    middle_header_controls = QWidget()
    middle_header_controls_layout = QHBoxLayout()
    middle_header_controls_layout.setContentsMargins(0, 0, 0, 0)
    middle_header_controls_layout.setSpacing(4)
    middle_header_controls.setLayout(middle_header_controls_layout)
    middle_header_controls_layout.addStretch(1)
    visibility_store = getattr(owner, "_visibility", None)
    get_visibility = getattr(visibility_store, "get", None)
    is_human_design_enabled = bool(
        callable(get_visibility)
        and get_visibility("chart_data.human_design_alpha_prototype")
    )

    button_specs: list[tuple[str, str, str, Callable[..., object]]] = [
        # BaZi Chart
        ("bazi", "🐉", "BaZi Chart", owner.on_open_bazi_window),
        # Personal Transit
        ("personal_transit", "🌎", "Personal Transit", owner.on_get_current_transits),
        # Synastry Chart
        ("synastry", "🧬", "Synastry Chart", owner.on_get_synastry_chart),
        ]
    if is_human_design_enabled:
        button_specs.insert(
            1,
            # Human Design Chart
            ("human_design", "🪷", "Human Design Chart", owner.on_get_human_design_info),
        )
    button_specs.extend(
        [
            # See Similar Charts
            ("similar_charts", "👯", "See Similar Charts", owner._show_similar_charts_popout),
            # Create Gemstone Chart
            ("gemstone_chart", "💎", "Create Gemstone Chart", owner.on_create_gemstone_chartwheel),
            # Chart Predictor Quiz
            ("chart_predictor_quiz", "🔮", "Chart Predictor Quiz", owner.on_open_chart_predictor_quiz),
        ]
    )

    owner.chart_view_middle_header_action_buttons = {}
    for button_key, button_label, button_tooltip, click_handler in button_specs:
        action_button = QPushButton(button_label)
        action_button.setObjectName(f"chart_view_middle_{button_key}_button")
        action_button.setToolTip(button_tooltip)
        action_button.setAutoDefault(False)
        action_button.setDefault(False)
        action_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        action_button.setMinimumWidth(0)
        action_button.setStyleSheet("padding: 1px 5px; font-size: 11px;")
        action_button.clicked.connect(click_handler)
        owner.chart_view_middle_header_action_buttons[button_key] = action_button
        middle_header_controls_layout.addWidget(action_button, 0, Qt.AlignHCenter)
    middle_header_controls_layout.addStretch(1)
    middle_layout.addWidget(middle_header_controls, 0, Qt.AlignTop)


def apply_chart_view_middle_panel_typography(
    *,
    middle_panel: QWidget,
    accent_color: str,
    placeholder_color_rgba: str,
) -> None:
    """Apply Chart View middle-panel typography and accent colors."""

    def _style_middle_panel_font(widget: QWidget) -> None:
        widget_font = QFont(widget.font())
        if widget_font.pointSize() > 1:
            widget_font.setPointSize(widget_font.pointSize() - 1)
        widget_font.setCapitalization(QFont.Capitalization.SmallCaps)
        widget.setFont(widget_font)

    for label in middle_panel.findChildren(QLabel):
        _style_middle_panel_font(label)
    for button in middle_panel.findChildren(QAbstractButton):
        _style_middle_panel_font(button)
    for line_edit in middle_panel.findChildren(QLineEdit):
        _style_middle_panel_font(line_edit)

    middle_panel.setStyleSheet(
        f"QLabel, QAbstractButton {{ color: {accent_color}; }}"
        f"QLineEdit::placeholder, QAbstractSpinBox::placeholder {{ color: {placeholder_color_rgba}; }}"
    )


def build_chart_view_right_panel(
    owner: QWidget,
    *,
    scrollbar_style: str,
    get_share_icon_path: Callable[[], str | None],
) -> None:
    """Build Chart View's right-side analytics/subjective notes stack."""
    _install_chart_view_sentiment_relevance_spectrum(owner)
    _require_owner_attrs(
        owner,
        (
            "_main_splitter",
            "sentiment_metrics_widget",
            "sentiment_relation_row_widget",
            "_register_metric_scroll_widget",
            "_create_chart_analysis_sections",
            "_create_similar_charts_section",
            "_add_chart_analysis_collapsible_section",
            "_set_chart_analysis_section_expanded",
            "_export_anagrams_share",
            "_on_anagram_link_activated",
            "_on_anagram_source_changed",
            "_sync_chart_analysis_section_visibility",
            "_set_chart_right_panel",
            "_chart_analysis_section_expanded",
        ),
        context="build_chart_view_right_panel",
    )

    metrics_content = QWidget()
    metrics_content.setFocusPolicy(Qt.StrongFocus)
    owner.metrics_layout = QVBoxLayout()
    owner.metrics_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
    owner.metrics_layout.setContentsMargins(6, 6, 6, 6)
    owner.metrics_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    metrics_content.setLayout(owner.metrics_layout)

    subjective_notes_panel = QWidget()
    subjective_notes_layout = QVBoxLayout()
    subjective_notes_layout.setContentsMargins(6, 6, 6, 6)
    subjective_notes_layout.setSpacing(6)
    subjective_notes_panel.setLayout(subjective_notes_layout)
    subjective_notes_layout.addWidget(owner.sentiment_metrics_widget)
    subjective_notes_layout.addWidget(owner.sentiment_relation_row_widget)
    subjective_notes_layout.addStretch(1)

    predictions_panel = QWidget()
    predictions_layout = QVBoxLayout()
    predictions_layout.setContentsMargins(6, 6, 6, 6)
    predictions_layout.setSpacing(6)
    predictions_panel.setLayout(predictions_layout)

    enneagram_section_layout = owner._add_chart_analysis_collapsible_section(
        panel=predictions_panel,
        layout=predictions_layout,
        title="Enneagram",
        expanded=True,
    )
    owner.enneagram_prediction_chart_panel = QWidget()
    owner.enneagram_prediction_chart_layout = QVBoxLayout()
    owner.enneagram_prediction_chart_layout.setContentsMargins(0, 0, 0, 0)
    owner.enneagram_prediction_chart_panel.setLayout(owner.enneagram_prediction_chart_layout)
    enneagram_section_layout.addWidget(owner.enneagram_prediction_chart_panel)
    owner.enneagram_prediction_tritype_label = QLabel("Predicted Tritype: —")
    owner.enneagram_prediction_tritype_label.setTextFormat(Qt.RichText)
    owner.enneagram_prediction_tritype_label.setWordWrap(True)
    owner.enneagram_prediction_tritype_label.setStyleSheet("color: #f5f5f5;")
    enneagram_section_layout.addWidget(owner.enneagram_prediction_tritype_label)
    predictions_layout.addStretch(1)

    chart_right_panel = build_chart_right_panel_stack(
        analytics_content_widget=metrics_content,
        predictions_content_widget=predictions_panel,
        subjective_notes_content_widget=subjective_notes_panel,
        on_show_analytics=lambda: owner._set_chart_right_panel("analytics"),
        on_show_predictions=lambda: owner._set_chart_right_panel("predictions"),
        on_show_subjective_notes=lambda: owner._set_chart_right_panel("subjective_notes"),
        scrollbar_style=scrollbar_style,
    )
    owner.metrics_panel = chart_right_panel.container
    owner.chart_analytics_panel_button = chart_right_panel.analytics_button
    owner.predictions_panel_button = chart_right_panel.predictions_button
    owner.subjective_notes_panel_button = chart_right_panel.subjective_notes_button
    owner.chart_right_panel_stack = chart_right_panel.stack
    owner.chart_analytics_panel_scroll = chart_right_panel.analytics_scroll
    owner.predictions_panel_scroll = chart_right_panel.predictions_scroll
    owner.subjective_notes_panel_scroll = chart_right_panel.subjective_notes_scroll

    owner._main_splitter.addWidget(owner.metrics_panel)
    owner.metrics_scroll = owner.chart_analytics_panel_scroll
    owner._register_metric_scroll_widget(owner.chart_analytics_panel_scroll)
    owner._register_metric_scroll_widget(metrics_content)

    owner._create_chart_analysis_sections(metrics_content)
    owner._create_similar_charts_section(metrics_content)
    anagrams_section = build_anagrams_section(
        panel=metrics_content,
        layout=owner.metrics_layout,
        add_collapsible_section=owner._add_chart_analysis_collapsible_section,
        on_toggled=lambda checked: owner._set_chart_analysis_section_expanded(
            "anagrams",
            checked,
        ),
        on_export_clicked=owner._export_anagrams_share,
        on_word_clicked=owner._on_anagram_link_activated,
        on_source_changed=owner._on_anagram_source_changed,
        get_share_icon_path=get_share_icon_path,
    )
    owner._chart_analysis_section_expanded["anagrams"] = False
    owner._anagrams_summary_label = anagrams_section.summary_label
    owner._anagrams_list_label = anagrams_section.list_label
    owner._anagrams_export_button = anagrams_section.export_button
    owner._anagrams_source_dropdown = anagrams_section.source_dropdown
    owner._sync_chart_analysis_section_visibility()
    owner.metrics_layout.addStretch(1)
    owner._active_chart_right_panel = "subjective_notes"
    owner._set_chart_right_panel("subjective_notes")
