from __future__ import annotations

import datetime
import html
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
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
    QStackedWidget,
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
            f"{_span('?:', safe_separator_color)}"
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

    chart_right_panel = build_chart_right_panel_stack(
        analytics_content_widget=metrics_content,
        subjective_notes_content_widget=subjective_notes_panel,
        on_show_analytics=lambda: owner._set_chart_right_panel("analytics"),
        on_show_subjective_notes=lambda: owner._set_chart_right_panel("subjective_notes"),
        scrollbar_style=scrollbar_style,
    )
    owner.metrics_panel = chart_right_panel.container
    owner.chart_analytics_panel_button = chart_right_panel.analytics_button
    owner.subjective_notes_panel_button = chart_right_panel.subjective_notes_button
    owner.chart_right_panel_stack = chart_right_panel.stack
    owner.chart_analytics_panel_scroll = chart_right_panel.analytics_scroll
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
