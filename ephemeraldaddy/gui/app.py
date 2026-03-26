# ephemeraldaddy/gui/app.py
import csv
import calendar
import copy
import ctypes
import datetime
import html
import json
import math
import logging
import numpy as np
import os
import random
import statistics
import subprocess
import sys
import traceback
import urllib.parse
from difflib import SequenceMatcher
from collections import Counter, OrderedDict
from typing import Any, Callable
from types import SimpleNamespace
from pathlib import Path
import re
from importlib import resources as importlib_resources
from zoneinfo import ZoneInfo


logger = logging.getLogger(__name__)

OUTLINED_PLANET_KEYS = frozenset({"Neptune", "Pluto", "Rahu", "Ketu"})

from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QIntValidator,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QWidget,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QDateEdit,
    QTimeEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QLabel,
    QGroupBox,
    QComboBox,
    QCompleter,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QTextEdit,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QMenu,
    QFileDialog,
    QProgressDialog,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QRadioButton,
    QButtonGroup,
    QToolButton,
    QSpinBox,
    QDoubleSpinBox,
    QStackedWidget,
    QSizePolicy,
    QLayout,
    QFrame,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QStyleOptionSlider,
    QAbstractButton,
    QSlider,
)
from PySide6.QtCore import (
    Qt,
    QObject,
    QCoreApplication,
    QSize,
    QPoint,
    QDate,
    QTime,
    QModelIndex,
    QTimer,
    QSettings,
    QEvent,
    QSignalBlocker,
    QThread,
    Signal,
    QEventLoop,
    QRegularExpression,
    QItemSelectionModel,
)
from PySide6.QtPositioning import QGeoPositionInfoSource


class _GlobalCloseShortcutFilter(QObject):
    """Ensures Ctrl/Cmd+W closes the currently active top-level window."""

    def eventFilter(self, _obj: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.KeyPress:
            return False
        if not event.matches(QKeySequence.Close):
            return False

        target = QApplication.activeModalWidget() or QApplication.activeWindow()
        if target is None:
            return False

        target.close()
        return True


class _StartupLoadingWidget(QWidget):
    """Lightweight loading indicator shown during cold start."""

    def __init__(self) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowTitle("Starting EphemeralDaddy")
        # During app startup keep this progress widget above other apps so
        # launch state is always visible until a primary app window is shown.
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(
            "QWidget { background-color: #141218; color: #efe9ff; }"
            "QLabel { color: #efe9ff; font-size: 12px; }"
            "QProgressBar {"
            "  border: 1px solid #47345d;"
            "  border-radius: 4px;"
            "  background-color: #0e0b12;"
            "  text-align: center;"
            "  min-height: 14px;"
            "}"
            "QProgressBar::chunk {"
            "  background-color: #9933ff;"
            "}"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        self.setLayout(layout)

        from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE

        title = QLabel("Ephemeral Daddy will be with you shortly…")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(title)

        self._status_label = QLabel("Preparing startup…")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(5)
        layout.addWidget(self._progress)

        self.setFixedWidth(360)
        self.adjustSize()
        self._center_on_primary_screen()

    def _center_on_primary_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        screen_rect = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen_rect.center())
        self.move(frame.topLeft())

    def update_status(self, message: str, progress: int) -> None:
        self._status_label.setText(message)
        self._progress.setValue(min(max(progress, 0), 100))
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)

from matplotlib import font_manager as mpl_font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ephemeraldaddy.core.deps import ensure_all_deps
from ephemeraldaddy.io.geocode import geocode_location, LocationLookupError, search_locations
from ephemeraldaddy.gui.astrotheme_search import (
    parse_astrotheme_profile,
    search_astrotheme_profile_url,
)
from ephemeraldaddy.gui.dev_tools import ManageMetadataLabelsDialog, SizeCheckerPopup
from ephemeraldaddy.gui.tooltips import apply_default_text_tooltips
from ephemeraldaddy.gui.window_chrome import (
    APP_DISPLAY_NAME,
    configure_application_identity,
    configure_main_window_chrome,
    configure_manage_dialog_chrome,
    configure_splitter_handle_resize_cursor,
)
from ephemeraldaddy.gui.window_placement import (
    WindowPlacement,
    apply_window_placement,
    capture_window_placement,
    clear_fullscreen_and_minimized,
)
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score, find_astro_twins
from ephemeraldaddy.core.ephemeris import (
    planetary_positions,
    planetary_retrogrades,
    is_offline_mode as ephemeris_offline_mode,
)
from ephemeraldaddy.core.hd import get_active_channels
from ephemeraldaddy.core.retcon import RETCON_BODIES
from ephemeraldaddy.core.aspects import ASPECT_DEFS
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    TRANSIT_ASPECT_RULES,
    assign_houses,
    compute_aspects,
    find_transit_aspect_window_result,
    normalize_chart,
    personal_transit_orb_cap,
    personal_transit_rules_for_mode,
    split_daily_vibe_hits_by_expected_duration,
)
from ephemeraldaddy.core.curse_scoring import (
    AspectRecord,
    chart_cursedness,
    MOST_CURSED_SCORE,
    chart_cursedness_max,
)
from ephemeraldaddy.graphics.wheel_plot import draw_chart_wheel
from ephemeraldaddy.graphics._chartwheel_generator_impl import draw_chartwheel
from ephemeraldaddy.core.db import (
    apply_metadata_label_change,
    save_chart,
    find_chart_name_matches_by_birth_day,
    list_charts,
    load_chart,
    load_dominant_sign_weights,
    delete_charts,
    update_chart,
    update_chart_dominant_sign_weights,
    set_current_chart,
    parse_relationship_types,
    list_recognized_tags,
    get_metadata_label_usage,
    backup_database,
    restore_database,
    append_database,
    check_database_health,
    find_self_tagged_chart,
    clear_self_tag_from_other_charts,
    resolve_user_age_details,
)

from ephemeraldaddy.data.age_distribution_estimator import discrete_age_distribution
from ephemeraldaddy.data.genpop import (
    GEN_POP_ACTUAL_GENDER_CAPTION,
    GEN_POP_ACTUAL_GENDER_UNKNOWN_LABELS,
    gen_pop_actual_gender_counts,
    INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED,
    SUN_SIGN_DISTRIBUTION_AGGREGATED,
)

from ephemeraldaddy.core.interpretations import (
    HOUSE_KEYWORDS,
    PLANET_KEYWORDS,
    SIGN_KEYWORDS,
    ASPECT_KEYWORDS,
    ELEMENT_COLORS,
    EXALTATION_WEIGHT,
    FALL_WEIGHT,
    HOUSE_WEIGHTS,
    DETRIMENT_WEIGHT,
    ANGULAR_AMPLIFICATION,
    NATURAL_HOUSE_PLANETS,
    NATURAL_HOUSE_SIGNS,
    NAKSHATRA_PLANET_COLOR,
    NAKSHATRA_RANGES,
    MODES,
    ASPECT_BODY_ALIASES,
    ASPECT_SORT_OPTIONS,
    ANGLE_WEIGHT,
    NATAL_WEIGHT,
    TRANSIT_WEIGHT,
    aspect_body_sign_duration,
    aspect_duration_score,
    aspect_pair_weight,
    aspect_score,
    PLANET_COLORS,
    PLANET_DETRIMENT,
    PLANET_EXALTATION,
    PLANET_FALL,
    PLANET_GLYPHS,
    PLANET_ORDER,
    PLANET_RULERSHIP,
    RELATION_TYPE,
    FAMILIARITY_INDEX,
    GENDER_GLYPHS,
    GENDER_OPTIONS,
    max_familiarity_score,
    normalized_familiarity_score,
    RULERSHIP_WEIGHT,
    SENTIMENT_COLORS,
    SENTIMENT_OPTIONS,
    HOUSE_COLORS,
    SIGN_COLORS,
    SIGN_ELEMENTS,
    ZODIAC_SIGNS,
    ZODIAC_NAMES,
    EPHEMERIS_MIN_DATE,
    EPHEMERIS_MAX_DATE,
    NATAL_CHART_MIN_DATE,
    NATAL_CHART_MAX_DATE,
    NATAL_CHART_MIN_YEAR,
    NATAL_CHART_MAX_YEAR,
    AGE_BRACKETS,
    GENERATIONAL_COHORTS,
    ASPECT_COLORS,
    ASPECT_FRICTION,
    ASPECT_TYPES,
)

from ephemeraldaddy.gui.features.charts.delegates import ChartRowDelegate
from ephemeraldaddy.gui.features.charts.provenance import (
    SOURCE_EVENT,
    SOURCE_OPTIONS,
    SOURCE_PERSONAL,
    SOURCE_PUBLIC_DB,
    normalize_gui_source as _normalize_gui_source,
)
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_IDS,
    DEFAULT_COLLECTION_OPTIONS,
    DEFAULT_COLLECTION_POSSIBLE_DUPLICATES,
    CustomCollection,
    chart_belongs_to_collection,
    normalize_collection_id,
    sanitize_collection_name,
)
from ephemeraldaddy.gui.features.charts.aspect_weight_graphs import (
    build_popout_left_panel as _build_popout_left_panel_widget,
    collect_aspect_category_totals as _collect_aspect_category_totals,
    collect_aspect_type_counts as _collect_aspect_type_counts,
    draw_popout_aspect_distribution_chart as _draw_popout_aspect_distribution_chart,
    extract_aspect_weight as _extract_aspect_weight,
    normalize_aspect_type as _normalize_aspect_type,
)
from ephemeraldaddy.gui.features.charts.duplicate_detection import (
    find_possible_duplicate_charts,
)

from ephemeraldaddy.gui.features.charts.aspect_sorting import (
    NATAL_ASPECT_SORT_OPTIONS,
    sort_natal_aspects as _sort_natal_aspects,
)
from ephemeraldaddy.gui.features.charts.tagging import (
    apply_tag_completer,
    normalize_tag_list,
    parse_tag_text,
    render_tag_chip_preview,
)
from ephemeraldaddy.gui.features.charts.tag_search import (
    chart_matches_tag_filters,
)

from ephemeraldaddy.gui.features.charts.database_analytics import DatabaseAnalyticsChartsMixin
from ephemeraldaddy.gui.features.charts.transit_workers import (
    ManagedTransitPopoutDialog,
    TransitAspectWindowRelay,
    TransitAspectWindowWorker,
)

from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_nakshatra_weights as _calculate_dominant_nakshatra_weights,
    calculate_dominant_element_weights as _calculate_dominant_element_weights,
    calculate_dominant_house_weights as _calculate_dominant_house_weights,
    calculate_dominant_planet_weights as _calculate_dominant_planet_weights,
    calculate_dominant_sign_weights as _calculate_dominant_sign_weights,
    calculate_element_prevalence_counts as _calculate_element_prevalence_counts,
    calculate_gender_prevalence_score as _calculate_gender_prevalence_score,
    calculate_gender_weight_score as _calculate_gender_weight_score,
    calculate_house_prevalence_counts as _calculate_house_prevalence_counts,
    calculate_modal_distribution_counts as _calculate_modal_distribution_counts,
    calculate_mode_weights as _calculate_mode_weights,
    calculate_planet_dynamics_scores as _calculate_planet_dynamics_scores,
    calculate_nakshatra_prevalence_counts as _calculate_nakshatra_prevalence_counts,
    calculate_sidereal_planet_prevalence_counts as _calculate_sidereal_planet_prevalence_counts,
    calculate_sign_prevalence_counts as _calculate_sign_prevalence_counts,
    chart_uses_houses as _chart_uses_houses,
    dominant_planet_keys as _dominant_planet_keys,
    house_for_longitude as _house_for_longitude,
    house_span_signs as _house_span_signs,
    planet_sign_weight as _planet_sign_weight,
    planet_weight as _planet_weight,
)

from ephemeraldaddy.gui.features.charts.algorithmic_transparency import (
    build_gender_guesser_breakdown_text as _build_gender_guesser_breakdown_text,
)

from ephemeraldaddy.gui.features.charts.aspect_interpretation import (
    build_aspect_interpretation_lines as _build_aspect_interpretation_lines,
)

from ephemeraldaddy.gui.features.charts.presentation import (
    apply_nakshatra_tick_info_markers as _apply_nakshatra_tick_info_markers,
    format_degree_minutes as _format_degree_minutes,
    format_hd_annotation as _format_hd_annotation,
    format_longitude as _format_longitude,
    format_nakshatra_description_text as _format_nakshatra_description_text,
    format_percent as _format_percent,
    format_transit_range as _format_transit_range,
    get_nakshatra as _get_nakshatra,
    sign_degrees as _sign_degrees,
    sign_for_longitude as _sign_for_longitude,
)
from ephemeraldaddy.gui.features.charts.sign_distribution import (
    SIGN_DISTRIBUTION_DROPDOWN_OPTIONS,
    SIGN_DISTRIBUTION_MODE_LABELS,
)
from ephemeraldaddy.gui.features.charts.exporters import (
    export_aspect_distribution_csv_dialog as _export_aspect_distribution_csv_dialog,
    get_text_export_path as _get_text_export_path,
)
from ephemeraldaddy.gui.features.charts.text_summary import (
    _aspect_body_with_sign,
    _aspect_duration_score,
    _aspect_label,
    _aspect_pair_weight,
    _aspect_score,
    _display_body_name,
    _display_body_with_glyph,
    _format_popout_aspect_endpoint,
    _is_structural_tautology,
    _normalize_aspect_body,
    _normalize_planet_weight_map,
    _overlay_aspect_segments,
    _synastry_pair_weight,
    format_chart_text,
    format_transit_chart_text,
)
from ephemeraldaddy.analysis.human_design import (
    build_awareness_stream_completion,
    build_human_design_result,
    build_human_design_chart_data_output,
    get_active_human_design_gates_and_lines,
)
from ephemeraldaddy.analysis.human_design_reference import format_gate_line_info
from ephemeraldaddy.gui.features.charts.human_design_plot import draw_human_design_chart
from ephemeraldaddy.gui.features.charts.right_panel_stack import (
    build_chart_right_panel_stack,
)
from ephemeraldaddy.gui.features.charts.loading_overlay import ChartLoadingOverlay
from ephemeraldaddy.gui.features.charts.anagrams import (
    ANAGRAM_SOURCE_LABELS,
    build_anagrams_section,
    collect_anagram_words,
    fetch_word_definition,
    render_anagrams_html,
    render_anagrams_text,
)
from ephemeraldaddy.gui.features.charts.similarity_norms import (
    SIMILARITY_THRESHOLD_EDITOR_ROWS,
    SimilarityThresholds,
    classify_similarity,
    compute_similarity_calibration,
    describe_similarity_bands,
    load_similarity_thresholds,
    save_similarity_calibration,
    save_similarity_thresholds,
)
from ephemeraldaddy.gui.features.charts.similarity_pairing import (
    SimilarityInputState,
    SimilarityPairResolution,
    build_chart_lookup,
    resolve_similarity_pair_targets,
)
from ephemeraldaddy.gui.features.retcon.transit_window import (
    TRANSIT_WINDOW_CACHE_LIMIT,
    resolve_transit_window_scan_config,
    validate_transit_window_mode_flags,
)
from ephemeraldaddy.gui.features.coordination.event_hub import FeatureEventHub
from ephemeraldaddy.gui.features.controllers.main_window import (
    ChartAnalysisSectionsController,
    ChartsController,
    EphemerisPrefetchController,
    RetconDialogController,
)
from ephemeraldaddy.gui.visibility import (
    CHART_DATA_KEYS,
    DATABASE_ANALYTICS_SECTION_KEYS,
    VisibilityStore,
)
from ephemeraldaddy.gui.features.import_export.parsing import (
    format_chart_row_datetime,
    normalize_csv_row,
    parse_datetime_value,
    trim_import_row,
)
from ephemeraldaddy.gui.features.import_export.pattern import (
    build_pattern_import_chart,
)
from ephemeraldaddy.gui.features.import_export.builders import (
    build_import_chart as _build_import_chart,
)
from ephemeraldaddy.gui.features.import_export.custom_db_export import (
    open_custom_db_export_dialog,
)

GEN_POP_UNSUPPORTED_SIGN_DISTRIBUTION_MODES: frozenset[str] = frozenset(
    {"Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "AS", "MC"}
)
GENDER_DROPDOWN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Actual Gender", "actual_gender"),
    ("Guessed by Weight", "guessed_weight"),
    ("Guessed by Prevalence", "guessed_prevalence"),
)
GEN_POP_UNSUPPORTED_GENDER_MODES: frozenset[str] = frozenset(
    {"guessed_weight", "guessed_prevalence"}
)
GEN_POP_HIDDEN_DATABASE_METRIC_SECTIONS: frozenset[str] = frozenset(
    {
        "sentiment_prevalence",
        "relationship_prevalence",
        "social_score_summary",
        "alignment_summary",
        "sign_prevalence",
        "dominant_signs",
        "cumulativedom_factors",
        "species_distribution",
        "birth_time",
        "age",
        "birth_month",
        "birthplace",
    }
)
SIMILAR_CHARTS_EXPORT_FORMAT_KEY = "exports/similar_charts_format"
CHART_VIEW_NAV_CACHE_LIMIT = 24

GENERATION_UNKNOWN_OPTION = "unknown"
GENERATION_FILTER_OPTIONS: tuple[str, ...] = tuple(
    [
        cohort["name"]
        for cohort in GENERATIONAL_COHORTS
        if isinstance(cohort.get("name"), str)
    ]
    + [GENERATION_UNKNOWN_OPTION]
)

# Explicit startup validation to avoid hidden import-time side effects.
validate_transit_window_mode_flags()

from ephemeraldaddy.gui.features.retcon.workers import RetconSearchWorker

from ephemeraldaddy.gui.features.dialogues import FamiliarityCalculatorDialog, RetconEngineDialog

from ephemeraldaddy.gui import help as help_notes
from ephemeraldaddy.gui.style import (
    CHART_VIEW_RECTIFIED_GROUP_LEFT_SPACER,
    CHART_VIEW_RECTIFIED_LABEL_CHECKBOX_SPACING,
    CHART_VIEW_TIME_INPUT_DISPLAY_FORMAT,
    CHART_VIEW_TIME_INPUT_WIDTH,
    CHART_VIEW_TIME_OVERWRITE_ENABLED,
    CRASH_MESSAGE,
    DATABASE_ANALYTICS_CHART_CONTENT_MARGINS,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    DATABASE_ANALYTICS_CONTENT_MARGINS,
    DATABASE_ANALYTICS_CONTENT_SPACING,
    DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    DATABASE_VIEW_PANEL_HEADER_STYLE,
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
    DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE,
    DATABASE_ANALYTICS_EXPORT_ICON_SIZE,
    DATABASE_ANALYTICS_HEADER_SPACING,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
    DATABASE_VIEW_SUBHEADER_WORD_WRAP,
    SETTINGS_COLLAPSIBLE_TOGGLE_STYLE,
    SETTINGS_SECTION_SUBHEADER_STYLE,
    DEFAULT_DROPDOWN_STYLE,
    FAILSAFE_EXIT_TIMEOUT_MS,
    CHART_DATA_COLON_LABELS,
    CHART_AXES_STYLE,
    CHART_DATA_COMMON_LABELS,
    CHART_DATA_INFO_LABEL_STYLE,
    CHART_DATA_POPOUT_HEADER_STYLE,
    CHART_DATA_DIVIDER,
    CHART_DATA_HIGHLIGHT_COLOR,
    CHART_DATA_MONOSPACE_FONT_FAMILY,
    CHART_DATA_SECTION_HEADERS,
    MIDDLE_PANEL_ACCENT_COLOR,
    MIDDLE_PANEL_PLACEHOLDER_COLOR_RGBA,
    RIGHT_PANEL_SCROLLBAR_STYLE,
    RELATIVE_YEAR_COLORS,
    SETTINGS_APP,
    SETTINGS_ORG,
    STANDARD_NCV_HORIZONTAL_BAR_CHART,
    PLANET_DYNAMICS_BAR_COLORS,
    STANDARD_NCV_PIE_CHART,
    STANDARD_NCV_POPOUT_LAYOUT,
    CHART_THEME_COLORS,
    GENDER_GUESSER_COLORS,
    INACTIVE_ACTION_BUTTON_STYLE,
    SIMILARITY_CALCULATE_BUTTON_ACTIVE_STYLE,
    SIMILARITY_CALCULATE_BUTTON_INACTIVE_STYLE,
    alignment_score_to_rgb,
    configure_collapsible_header_toggle,
    format_chart_header,
    QUAD_STATE_SLIDER_VISUALS,
    TRISTATE_SENTIMENT_STYLE,
)
from ephemeraldaddy.core.timeutils import localize_naive_datetime
from ephemeraldaddy.analysis.dnd.species_assigner import (
    SPECIES_FAMILIES,
    assign_top_three_species,
    assign_top_three_species_with_evidence,
)
from ephemeraldaddy.analysis.get_astro_age import chart_age_from_positions
from ephemeraldaddy.analysis.bazi_getter import build_bazi_chart_data
from ephemeraldaddy.analysis.country_lookup import resolve_country
from ephemeraldaddy.gui.features.charts.bazi_window import (
    BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE,
    create_bazi_window_dialog,
    validate_chart_for_bazi,
)


class SegmentedTimeEdit(QLineEdit):
    """Compact HH:mm editor with overwrite behavior and colon-safe navigation."""

    timeChanged = Signal(QTime)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_time = QTime(12, 0)
        self.setAlignment(Qt.AlignCenter)
        self.setMaxLength(5)
        self.setInputMask("99:99")
        self.setTime(self._current_time)

    def setDisplayFormat(self, _format: str) -> None:
        """Compatibility shim with QTimeEdit API."""
        return

    def time(self) -> QTime:
        return self._current_time

    def setTime(self, value: QTime) -> None:
        normalized = value if isinstance(value, QTime) and value.isValid() else QTime(12, 0)
        self._current_time = normalized
        self.setText(f"{normalized.hour():02d}:{normalized.minute():02d}")
        if self.cursorPosition() == 2:
            self.setCursorPosition(3)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key_Backspace:
            cursor = self.cursorPosition()
            if cursor == 3:
                self.setCursorPosition(1)
            elif cursor == 2:
                self.setCursorPosition(1)
            super().keyPressEvent(event)
            self._normalize_and_emit()
            return
        if key in (Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            super().keyPressEvent(event)
            if self.cursorPosition() == 2:
                if key == Qt.Key_Left:
                    self.setCursorPosition(1)
                else:
                    self.setCursorPosition(3)
            self._normalize_and_emit()
            return
        if event.text().isdigit() and CHART_VIEW_TIME_OVERWRITE_ENABLED:
            super().keyPressEvent(event)
            if self.cursorPosition() == 2:
                self.setCursorPosition(3)
            self._normalize_and_emit()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self.cursorPosition() == 2:
            self.setCursorPosition(3)

    def _normalize_and_emit(self) -> None:
        text = self.text()
        digits = [char for char in text if char.isdigit()]
        if len(digits) < 4:
            return
        hour = min(23, int("".join(digits[:2])))
        minute = min(59, int("".join(digits[2:4])))
        normalized = QTime(hour, minute)
        normalized_text = f"{hour:02d}:{minute:02d}"
        if text != normalized_text:
            cursor_position = self.cursorPosition()
            self.setText(normalized_text)
            self.setCursorPosition(3 if cursor_position == 2 else min(cursor_position, len(normalized_text)))
        if normalized != self._current_time:
            self._current_time = normalized
            self.timeChanged.emit(self._current_time)


class ResizablePixmapLabel(QLabel):
    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_pixmap = pixmap
        self.setAlignment(Qt.AlignCenter)
        self._update_scaled_pixmap()

    def set_base_pixmap(self, pixmap: QPixmap) -> None:
        self._base_pixmap = pixmap
        self._update_scaled_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._base_pixmap is None or self._base_pixmap.isNull():
            self.clear()
            return
        scaled = self._base_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)

class ChartSummaryHighlighter(QSyntaxHighlighter):
    _NAKSHATRA_INFO_FIELD_LABELS = (
        "Symbol:",
        "Shakti:",
        "Essence:",
        "Quality:",
        "Favorable Activities:",
        "Sidereal Sign:",
        "Archetypes:",
        "Deity:",
        "Ruler:",
        "Body Associations:",
        "Notes A:",
        "Notes B:",
    )

    def __init__(self, document) -> None:
        super().__init__(document)
        self._unknown_format = QTextCharFormat()
        self._unknown_format.setForeground(QColor("#666666"))
        self._unknown_format.setFontItalic(True)
        self._unknown_needles = (
            "unknown (birth time unknown)",
            "unknown (birthtime unknown)",
        )
        self._label_format = QTextCharFormat()
        self._label_format.setFontWeight(QFont.Bold)
        self._label_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        self._nakshatra_header_formats = {}
        for nakshatra, (_planet, color) in NAKSHATRA_PLANET_COLOR.items():
            header_format = QTextCharFormat(self._label_format)
            header_format.setForeground(QColor(color or CHART_DATA_HIGHLIGHT_COLOR))
            self._nakshatra_header_formats[nakshatra] = header_format
        self._section_format = QTextCharFormat()
        self._section_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        self._section_format.setFontWeight(QFont.Bold)
        self._time_variant_format = QTextCharFormat()
        self._time_variant_format.setFontItalic(True)
        self._time_variant_dawn_format = self._make_format("#d1863a", italic=True)
        self._time_variant_dusk_format = self._make_format("#4a7bd1", italic=True)
        self._aspect_formats = {
            "conjunction": self._make_format("#c7a56a"),
            "sextile": self._make_format("#6b8ba4"),
            "square": self._make_format("#8d6e63"),
            "trine": self._make_format("#6b705c"),
            "opposition": self._make_format("#c26d3a"),
        }
        self._planet_formats = {
            planet: self._make_format(color)
            for planet, color in PLANET_COLORS.items()
            if color
        }
        self._sign_formats = {
            sign: self._make_format(color)
            for sign, color in SIGN_COLORS.items()
            if color
        }
        self._house_formats = {
            str(house): self._make_format(color)
            for house, color in HOUSE_COLORS.items()
            if isinstance(house, (str, int)) and str(house).isdigit() and color
        }
        self._house_token_pattern = re.compile(r"\bH(1[0-2]|[1-9])\b")
        self._relative_year_formats = {
            label: self._make_format(color)
            for label, color in RELATIVE_YEAR_COLORS.items()
            if isinstance(color, str) and color
        }
        self._transit_range_date_pattern = re.compile(r"\d{2}-\d{2}-(\d{4})(?:\s+\d{2}:\d{2})?\*?")

    @staticmethod
    def _make_format(
        color: str,
        *,
        italic: bool = False,
    ) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if italic:
            text_format.setFontItalic(True)
        return text_format

    @staticmethod
    def _qt_len(text: str) -> int:
        return len(text.encode("utf-16-le")) // 2

    @classmethod
    def _qt_index(cls, text: str, index: int) -> int:
        return cls._qt_len(text[:index])

    def highlightBlock(self, text: str) -> None:
        lowered = text.lower()
        for needle in self._unknown_needles:
            start = 0
            while True:
                index = lowered.find(needle, start)
                if index == -1:
                    break
                self.setFormat(index, len(needle), self._unknown_format)
                start = index + len(needle)
        stripped_text = text.strip()
        lowered_stripped = stripped_text.lower()
        for header in CHART_DATA_SECTION_HEADERS:
            if stripped_text.upper() == header:
                self.setFormat(0, self._qt_len(text), self._section_format)
                break
        if lowered_stripped.startswith("synastry chart for "):
            self.setFormat(0, self._qt_len(text), self._section_format)
        if lowered_stripped.endswith(":") and " aspects to " in lowered_stripped:
            self.setFormat(0, self._qt_len(text), self._section_format)
        for label in (
            *CHART_DATA_COMMON_LABELS,
            *CHART_DATA_COLON_LABELS,
            *CHART_DATA_SECTION_HEADERS,
            *self._NAKSHATRA_INFO_FIELD_LABELS,
            "|",
        ):
            self._highlight_phrase(text, label, self._label_format)
        for nakshatra, header_format in self._nakshatra_header_formats.items():
            if stripped_text == nakshatra:
                self.setFormat(0, self._qt_len(text), header_format)
                break
        if "🌅" in text or "🌌" in text:
            self.setFormat(0, self._qt_len(text), self._time_variant_format)
            dawn_index = text.find("🌅")
            if dawn_index != -1:
                start = dawn_index + len("🌅")
                if start < len(text) and text[start] == " ":
                    start += 1
                if start < len(text):
                    start_qt = self._qt_index(text, start)
                    self.setFormat(
                        start_qt,
                        self._qt_len(text) - start_qt,
                        self._time_variant_dawn_format,
                    )
            dusk_index = text.find("🌌")
            if dusk_index != -1:
                start = dusk_index + len("🌌")
                if start < len(text) and text[start] == " ":
                    start += 1
                if start < len(text):
                    start_qt = self._qt_index(text, start)
                    self.setFormat(
                        start_qt,
                        self._qt_len(text) - start_qt,
                        self._time_variant_dusk_format,
                    )
        leading_token = text.split()[0] if text.split() else ""
        if leading_token in self._planet_formats:
            self.setFormat(0, self._qt_len(text), self._planet_formats[leading_token])
        else:
            for body, fmt in self._planet_formats.items():
                self._highlight_phrase(text, body, fmt)
        for aspect, fmt in self._aspect_formats.items():
            self._highlight_phrase(lowered, aspect, fmt)
        for sign, fmt in self._sign_formats.items():
            self._highlight_phrase(text, sign, fmt)
        house_match = re.match(r"^\s*(\d{1,2})\s*:\s+([^\d\s][^\d]*)\s+\d{2}°\d{2}'", text)
        if house_match:
            house_num = house_match.group(1)
            sign_name = house_match.group(2).strip()
            house_fmt = self._house_formats.get(house_num)
            if house_fmt:
                prefix_end = text.find(":") + 1
                if prefix_end > 0:
                    self.setFormat(0, prefix_end, house_fmt)
            sign_fmt = self._make_format(SIGN_COLORS.get(sign_name, CHART_DATA_HIGHLIGHT_COLOR))
            sign_start = text.find(sign_name)
            if sign_start != -1:
                self.setFormat(sign_start, len(sign_name), sign_fmt)
        for match in self._house_token_pattern.finditer(text):
            house_num = match.group(1)
            house_fmt = self._house_formats.get(house_num)
            if house_fmt:
                self.setFormat(match.start(), len(match.group(0)), house_fmt)

        current_year = datetime.datetime.now(datetime.timezone.utc).year
        for match in self._transit_range_date_pattern.finditer(text):
            year = int(match.group(1))
            year_delta = year - current_year
            if year_delta == -2:
                year_label = "year before last"
            elif year_delta == -1:
                year_label = "last year"
            elif year_delta == 0:
                year_label = "current"
            elif year_delta == 1:
                year_label = "next"
            elif year_delta == 2:
                year_label = "year after next"
            else:
                year_label = "other"
            text_format = self._relative_year_formats.get(year_label)
            if text_format:
                start_qt = self._qt_index(text, match.start())
                length_qt = self._qt_len(match.group(0))
                self.setFormat(start_qt, length_qt, text_format)

    def _highlight_phrase(self, text: str, phrase: str, text_format: QTextCharFormat) -> None:
        start = 0
        phrase_len = len(phrase)
        text_len = len(text)
        while True:
            index = text.find(phrase, start)
            if index == -1:
                break
            before_ok = index == 0 or not text[index - 1].isalnum()
            after_index = index + phrase_len
            after_ok = after_index >= text_len or not text[after_index].isalnum()
            if before_ok and after_ok:
                self.setFormat(
                    self._qt_index(text, index),
                    self._qt_len(phrase),
                    text_format,
                )
            start = index + phrase_len

def _available_screen_geometry():
    app = QApplication.instance()
    if app is None:
        return None
    screen = app.primaryScreen()
    if screen is None:
        return None
    return screen.availableGeometry()


def _apply_minimum_screen_height(window: QWidget) -> None:
    geometry = _available_screen_geometry()
    if geometry is None:
        return
    min_height = int(geometry.height() * 0.8)
    if min_height > 0:
        window.setMinimumHeight(min_height)


def _find_children_for_types(container: QObject, *widget_types: type[QObject]) -> list[QObject]:
    """Collect children for multiple widget types without passing a tuple to findChildren()."""
    matches: list[QObject] = []
    for widget_type in widget_types:
        matches.extend(container.findChildren(widget_type))
    return matches


class TriStateCheckBox(QCheckBox):
    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.setTristate(True)

    def nextCheckState(self) -> None:
        current_state = self.checkState()
        if current_state == Qt.Unchecked:
            self.setCheckState(Qt.Checked)
        elif current_state == Qt.Checked:
            self.setCheckState(Qt.PartiallyChecked)
        else:
            self.setCheckState(Qt.Unchecked)


class QuadStateSlider(QWidget):
    modeChanged = Signal(int)

    MODE_EMPTY = 0
    MODE_TRUE = 1
    MODE_FALSE = 2
    MODE_MIXED = 3

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = self.MODE_EMPTY
        self._button = QToolButton(self)
        self._button.setCheckable(False)
        self._button.clicked.connect(self._advance_mode)
        self._label = QLabel(label)
        self._label.setStyleSheet("padding-left: 2px;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)
        layout.addWidget(self._label)
        layout.addStretch(1)
        self.setLayout(layout)
        self._render_mode()

    def mode(self) -> int:
        return self._mode

    def setMode(self, mode: int, emit_signal: bool = False) -> None:
        mode = int(mode)
        if mode == self._mode:
            return
        self._mode = mode
        self._render_mode()
        if emit_signal:
            self.modeChanged.emit(self._mode)

    def _advance_mode(self) -> None:
        if self._mode in (self.MODE_EMPTY, self.MODE_MIXED):
            next_mode = self.MODE_TRUE
        elif self._mode == self.MODE_TRUE:
            next_mode = self.MODE_FALSE
        else:
            next_mode = self.MODE_EMPTY
        self.setMode(next_mode, emit_signal=True)

    def _render_mode(self) -> None:
        if self._mode == self.MODE_TRUE:
            visual = QUAD_STATE_SLIDER_VISUALS["true"]
        elif self._mode == self.MODE_FALSE:
            visual = QUAD_STATE_SLIDER_VISUALS["false"]
        elif self._mode == self.MODE_MIXED:
            visual = QUAD_STATE_SLIDER_VISUALS["mixed"]
        else:
            visual = QUAD_STATE_SLIDER_VISUALS["empty"]

        self._button.setText(visual["text"])
        self._button.setToolTip(visual["tooltip"])
        self._button.setFixedWidth(28)
        self._button.setStyleSheet(
            "QToolButton {"
            f"{visual['style']}"
            "border-radius: 10px; font-weight: bold; padding: 2px 0px;"
            "}"
        )

class AlignmentEmojiSlider(QSlider):
    """Horizontal alignment slider with an emoji marker that tracks thresholds."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setRange(-10, 10)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setTickInterval(5)
        self.setValue(0)
        self.setMinimumHeight(34)
        self.setStyleSheet(
            "QSlider::groove:horizontal {"
            "height: 12px;"
            "border-radius: 6px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "stop:0 #c62828, stop:0.5 #7f7f7f, stop:1 #1565c0);"
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
        self._refresh_emoji()
        self.valueChanged.connect(self._refresh_emoji)

    @staticmethod
    def _emoji_for_value(value: int) -> str:
        if value <= -10:
            return "😈"
        if value <= -5:
            return "😠"
        if value < 5:
            return "⚖️"
        if value < 10:
            return "🙂"
        return "😇"

    def _refresh_emoji(self) -> None:
        self._emoji_marker.setText(self._emoji_for_value(self.value()))
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


SEARCH_SENTIMENT_OPTIONS = ["none", *SENTIMENT_OPTIONS]
SEARCH_RELATIONSHIP_TYPE_OPTIONS = ["none", *RELATION_TYPE]
SEARCH_GENDER_OPTIONS = ["none", *GENDER_OPTIONS]
SEARCH_GENDER_BLANK_ALIASES = {"", "none", "unknown", "blank", "undefined", "__blank__"}
SEARCH_GENDER_GUESSED_OPTIONS = [
    ("Any", ""),
    ("Masculine", "masculine"),
    ("Androgynous", "androgynous"),
    ("Feminine", "feminine"),
]





def _font_supports_codepoints(font_path: str, codepoints: set[int]) -> bool:
    """Return whether a font file contains glyphs for every requested codepoint."""
    try:
        from matplotlib.ft2font import FT2Font

        charmap = FT2Font(font_path).get_charmap()
    except Exception:
        return False
    return all(cp in charmap for cp in codepoints)


def _register_packaged_symbol_fonts() -> None:
    """Register bundled symbol fonts so packaged apps render glyphs consistently."""
    font_paths: list[Path] = []

    # 1) project-local packaged fonts (works in source + bundled app resources)
    try:
        fonts_dir = importlib_resources.files("ephemeraldaddy.gui").joinpath("fonts")
        for item in fonts_dir.iterdir():
            if item.is_file() and item.suffix.lower() in {".ttf", ".otf", ".ttc"}:
                font_paths.append(Path(str(item)))
    except Exception:
        pass

    # 2) optional override path for ops/deployment testing
    extra_dir = os.environ.get("EPHEMERALDADDY_FONT_DIR", "").strip()
    if extra_dir:
        path = Path(extra_dir)
        if path.exists() and path.is_dir():
            for item in path.iterdir():
                if item.is_file() and item.suffix.lower() in {".ttf", ".otf", ".ttc"}:
                    font_paths.append(item)

    for font_path in font_paths:
        try:
            mpl_font_manager.fontManager.addfont(str(font_path))
        except Exception:
            continue


def _configure_matplotlib_info_marker_font() -> None:
    """Prefer chart-safe default fonts while allowing targeted symbol-font overrides."""

    def _collect_codepoints(symbols: list[str] | tuple[str, ...] | set[str]) -> set[int]:
        codepoints: set[int] = set()
        for symbol in symbols:
            for char in str(symbol):
                codepoints.add(ord(char))
        return codepoints

    required_codepoints = {
        # transit/chart glyphs we actually render in wheel + text output
        *_collect_codepoints(ZODIAC_SIGNS),
        *_collect_codepoints(set(PLANET_GLYPHS.values())),
        0x24D8,  # ⓘ
        0x26B3,  # ⚳ Ceres
        0x26B4,  # ⚴ Pallas
        0x26B5,  # ⚵ Juno
        0x26B6,  # ⚶ Vesta
        0x26B7,  # ⚷ Chiron
        0x26B8,  # ⚸ Lilith
    }

    # Prefer platform-native symbol fonts first.
    if sys.platform == "win32":
        candidates = [
            "Segoe UI Symbol",
            "Arial Unicode MS",
            "DejaVu Sans",
            "Symbola",
            "Apple Symbols",
        ]
    else:
        candidates = [
            "Arial Unicode MS",
            "Apple Symbols",
            "Segoe UI Symbol",
            "DejaVu Sans",
            "Symbola",
        ]
    try:
        entries = list(mpl_font_manager.fontManager.ttflist)
    except Exception:
        return

    paths_by_name: dict[str, list[str]] = {}
    for entry in entries:
        paths_by_name.setdefault(entry.name, []).append(entry.fname)

    selected: list[str] = []
    for name in candidates:
        for path in paths_by_name.get(name, []):
            if _font_supports_codepoints(path, required_codepoints):
                selected.append(name)
                break

    if not selected:
        return

    # use matplotlib rcParams without importing pyplot
    import matplotlib as _mpl

    sans = list(_mpl.rcParams.get("font.sans-serif", []))
    for name in reversed(selected):
        if name in sans:
            sans.remove(name)
        sans.insert(0, name)
    _mpl.rcParams["font.family"] = "sans-serif"
    _mpl.rcParams["font.sans-serif"] = sans


def _maybe_reexec_with_macos_app_name() -> None:
    """On macOS interpreter launches, re-exec with a friendlier argv[0].

    When launched as `python -m ephemeraldaddy.gui.app`, the Dock/taskbar label may
    still come from the Python interpreter process identity. Re-executing with a
    custom argv[0] can improve macOS labeling behavior in Terminal-driven runs.
    """
    if sys.platform != "darwin":
        return
    if os.environ.get("EPHEMERALDADDY_APPNAME_REEXEC") == "1":
        return
    if getattr(sys, "frozen", False):
        return

    exe_name = Path(sys.executable).name.lower()
    if not exe_name.startswith("python"):
        return

    env = os.environ.copy()
    env["EPHEMERALDADDY_APPNAME_REEXEC"] = "1"
    os.execve(
        sys.executable,
        [APP_DISPLAY_NAME, "-m", "ephemeraldaddy.gui.app", *sys.argv[1:]],
        env,
    )

def _get_qapp():
    """Return a QApplication instance, creating one if needed."""
    _configure_qt_input_scaling()
    QCoreApplication.setApplicationName(APP_DISPLAY_NAME)
    #QCoreApplication.setApplicationDisplayName(APP_DISPLAY_NAME)
    QCoreApplication.setOrganizationName(APP_DISPLAY_NAME)
    app = QApplication.instance()
    if app is None:
        if sys.platform == "win32":
            # Ensure Windows treats this process as the Ephemeral Daddy app
            # so the taskbar uses our icon/name instead of Python's defaults.
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
                    "ephemeraldaddy.desktop"
                )
            except Exception:
                pass

        if sys.platform == "darwin":
            # On macOS, process naming for interpreter-launched GUI apps can default
            # to "Python". Setting the low-level process name before constructing
            # QApplication helps Dock/taskbar hover labels pick up the app identity.
            try:
                libc = ctypes.CDLL(None)
                setprogname = getattr(libc, "setprogname", None)
                if setprogname is not None:
                    setprogname.argtypes = [ctypes.c_char_p]
                    setprogname.restype = None
                    setprogname(APP_DISPLAY_NAME.encode())
            except Exception:
                pass

            # If PyObjC is available, also update Cocoa's process/bundle identity.
            try:
                from Foundation import NSBundle, NSProcessInfo  # type: ignore

                NSProcessInfo.processInfo().setProcessName_(APP_DISPLAY_NAME)
                bundle_info = NSBundle.mainBundle().infoDictionary()
                if bundle_info is not None:
                    bundle_info["CFBundleName"] = APP_DISPLAY_NAME
                    bundle_info["CFBundleDisplayName"] = APP_DISPLAY_NAME
            except Exception:
                pass

            # Try updating the running application's localized UI name in Dock/menu.
            try:
                from AppKit import NSRunningApplication  # type: ignore

                running = NSRunningApplication.currentApplication()
                if running is not None:
                    running.setLocalizedName_(APP_DISPLAY_NAME)
            except Exception:
                pass

        # On macOS, Qt may derive Dock/app labeling from argv[0] when launched from
        # a Python interpreter. Provide an explicit program name so it does not show
        # up as "Python" in the Dock/taskbar hover label.
        qt_argv = [APP_DISPLAY_NAME, *sys.argv[1:]]
        app = QApplication(qt_argv)
    configure_application_identity(app)
    if not hasattr(app, "_edd_global_close_filter"):
        app._edd_global_close_filter = _GlobalCloseShortcutFilter(app)
        app.installEventFilter(app._edd_global_close_filter)
    return app


def _configure_qt_input_scaling() -> None:
    """Align Qt's input hit-testing with fractional desktop scale factors."""
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        # Best-effort compatibility guard for older Qt/PySide combinations.
        pass

def _get_app_icon_path() -> str | None:
    module_root = Path(__file__).resolve().parents[1]
    icon_path = module_root / "graphics" / "ephemeraldaddy1.png"
    if icon_path.exists():
        return str(icon_path)
    return None

def _get_share_icon_path() -> str | None:
    module_root = Path(__file__).resolve().parents[1]
    icon_path = module_root / "graphics" / "share_icon2.png"
    if icon_path.exists():
        return str(icon_path)
    return None


STARTUP_DEPENDENCY_CHECK_STAMP = "2026-03-23"


def _env_flag_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _should_run_startup_dependency_check(settings: QSettings) -> bool:
    """Gate heavyweight dependency imports to first-run and debug flows."""
    if _env_flag_enabled(os.environ.get("EPHEMERALDADDY_SKIP_DEP_CHECK")):
        return False
    if _env_flag_enabled(os.environ.get("EPHEMERALDADDY_FORCE_DEP_CHECK")):
        return True
    if _env_flag_enabled(os.environ.get("EPHEMERALDADDY_DEBUG")):
        return True
    previous_stamp = str(settings.value("startup/dependency_check_stamp", "") or "").strip()
    return previous_stamp != STARTUP_DEPENDENCY_CHECK_STAMP


def _mark_startup_dependency_check_complete(settings: QSettings) -> None:
    settings.setValue("startup/dependency_check_stamp", STARTUP_DEPENDENCY_CHECK_STAMP)
    settings.sync()


def _sanitize_export_token(value: str, fallback: str = "chart") -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "").strip()).strip("_")
    return token or fallback










class EmojiTiledPanel(QWidget):
    """Panel container that paints a subtle tiled emoji background."""

    def __init__(
        self,
        emoji: str,
        font_size: int,
        opacity: float,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._emoji = emoji
        self._tile_font = QFont(self.font())
        self._tile_font.setPointSize(font_size)
        self._tile_opacity = max(0.0, min(1.0, float(opacity)))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._tile_opacity <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setPen(Qt.white)
        painter.setFont(self._tile_font)
        painter.setOpacity(self._tile_opacity)

        metrics = QFontMetrics(self._tile_font)
        tile_width = max(1, metrics.horizontalAdvance(self._emoji) + 28)
        tile_height = max(1, metrics.height() + 28)
        baseline_offset = metrics.ascent()

        for y in range(0, self.height() + tile_height, tile_height):
            for x in range(0, self.width() + tile_width, tile_width):
                painter.drawText(x, y + baseline_offset, self._emoji)


def _handle_list_letter_jump(list_widget: QListWidget, event) -> bool:
    """Select the next item whose name starts with the typed letter."""
    if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
        return False

    typed = event.text()
    if len(typed) != 1 or not typed.isalpha():
        return False

    letter = typed.casefold()
    total = list_widget.count()
    if total <= 0:
        return False

    current_row = list_widget.currentRow()
    start_row = current_row if current_row >= 0 else -1

    for offset in range(1, total + 1):
        row = (start_row + offset) % total
        item = list_widget.item(row)
        if item is None:
            continue

        metadata = item.data(Qt.UserRole + 1)
        candidate_name = ""
        if isinstance(metadata, dict):
            candidate_name = (metadata.get("raw_name") or "").strip()
        if not candidate_name:
            candidate_name = item.text().strip()

        if candidate_name.casefold().startswith(letter):
            index = list_widget.indexFromItem(item)
            selection_model = list_widget.selectionModel()
            if selection_model is not None and index.isValid():
                selection_model.setCurrentIndex(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                list_widget.scrollTo(
                    index,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
            else:
                list_widget.clearSelection()
                item.setSelected(True)
                list_widget.setCurrentItem(item)
                list_widget.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
            return True

    return False

class ChartListWidget(QListWidget):
    """List widget with single-letter jump-to-name navigation."""

    def keyPressEvent(self, event) -> None:
        if self._handle_letter_jump(event):
            return
        super().keyPressEvent(event)

    def _handle_letter_jump(self, event) -> bool:
        return _handle_list_letter_jump(self, event)

# Database View / Manage Charts Window
class ManageChartsDialog(DatabaseAnalyticsChartsMixin, QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ephemeral Daddy: Astro App | Charts Manager")
        self.setWindowFlag(Qt.Window, True) #this makes the window come to the foreground
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._visibility = VisibilityStore(self._settings)
        self._feature_hub = FeatureEventHub()
        _apply_minimum_screen_height(self)

        # Database View sorting state.
        self._sort_mode = "alpha" #default sorting mode 1/2 of "manage charts" DB windows
        self._sort_descending = False
        self._chart_rows = []
        self._active_chart_rows_by_id: dict[int, tuple[Any, ...]] = {}
        self._chart_cache = {}
        # Dialog-side chart selection/render state mirrors MainWindow attributes
        # and is referenced by shared refresh helpers.
        self.current_chart_id: int | None = None
        self._latest_chart = None
        self._search_body_filters = []
        self._aspect_filters = []
        self._dominant_sign_filters = []
        self._dominant_planet_filters = []
        self._dominant_mode_filters = []
        self._year_first_encountered_earliest_input = None
        self._year_first_encountered_latest_input = None
        self._year_first_encountered_blank_checkbox = None
        self._positive_sentiment_intensity_min_input = None
        self._positive_sentiment_intensity_max_input = None
        self._negative_sentiment_intensity_min_input = None
        self._negative_sentiment_intensity_max_input = None
        self._familiarity_min_input = None
        self._familiarity_max_input = None
        self._alignment_score_min_input = None
        self._alignment_score_max_input = None
        self._alignment_score_blank_checkbox = None
        self._notes_comments_filter_checkbox = None
        self._notes_comments_filter_input = None
        self._notes_source_filter_checkbox = None
        self._notes_source_filter_input = None
        self.living_checkbox = None
        self.generation_filter_checkboxes: dict[str, QuadStateSlider] = {}
        self._dominant_element_primary_combo = None
        self._dominant_element_secondary_combo = None
        self._suppress_filter_refresh = False
        self._filter_refresh_running = False
        self._filter_refresh_pending = False
        self._filter_refresh_timer = QTimer(self)
        self._filter_refresh_timer.setSingleShot(True)
        self._filter_refresh_timer.setInterval(75)
        self._filter_refresh_timer.timeout.connect(self._run_scheduled_filter_refresh)
        self._custom_collections: dict[str, CustomCollection] = {}
        self._active_collection_id = DEFAULT_COLLECTION_ALL
        self._possible_duplicate_chart_ids: set[int] = set()
        self._possible_duplicate_related_names: dict[int, dict[str, list[str]]] = {}
        self._show_possible_duplicates_collection = False
        self._active_collection_total_count = 0
        self._analysis_chart_export_rows: dict[
            str,
            list[tuple[str, float, float, float, int, int, float]],
        ] = {}
        self._analysis_chart_filenames: dict[str, str] = {}
        self._analysis_chart_dropdowns: dict[str, QComboBox] = {}
        self._database_metrics_section_expanded: dict[str, bool] = {}
        self._database_metrics_section_visible: dict[str, bool] = {}
        self._incremental_metrics_refresh_sections: list[str] = []
        self._incremental_metrics_refresh_changed_ids: set[int] = set()
        self._incremental_metrics_force_full_refresh: bool = False
        self._incremental_metrics_refresh_scheduled = False
        self._database_metrics_chart_layouts: dict[str, QVBoxLayout] = {}
        self._database_metrics_section_widgets: dict[str, QWidget] = {}
        self._similarities_export_sections: list[
            tuple[str, list[tuple[str, int, int, int, int]]]
        ] = []
        self._similarities_pair_button: QPushButton | None = None
        self._similarities_pair_result_label: QLabel | None = None
        self._similarities_chart_lookup: dict[str, int] = {}
        self._similarities_first_chart_input: QLineEdit | None = None
        self._similarities_second_chart_input: QLineEdit | None = None
        self._similarities_first_use_checkbox: QCheckBox | None = None
        self._similarities_second_use_checkbox: QCheckBox | None = None
        self._sign_distribution_mode = "Sun"
        self._prevalence_mode = "sign_prevalence"
        self._dominant_factors_mode = "top3_signs"
        self._cumulativedom_factors_mode = "cumulative_signs"
        self._species_distribution_mode = "top_ranked"
        self._birth_time_mode = "mean"
        self._age_mode = "age_distribution"
        self._birth_month_mode = "month_distribution"
        self._birthplace_mode = "towns"
        self._gender_mode = "actual_gender"
        self._database_metrics_baseline_mode = "database"
        # Single source of truth for all Database Analytics panel charts.
        # Future charts should derive from snapshot/cache helpers below so
        # lazy changed-id refresh applies panel-wide by default.
        self._database_metric_snapshots: dict[int, dict[str, Any]] = {}
        self._database_metrics_cache: dict[str, Any] | None = None
        self._database_metrics_dirty_ids: set[int] = set()
        self._transit_chart_canvases: dict[QWidget, Chart] = {}
        self._transit_popout_dialogs: list[QDialog] = []
        self._gemstone_chartwheel_popouts: list[QDialog] = []
        self._popout_summary_contexts: dict[QWidget, dict[str, object]] = {}
        self._transit_window_result_cache: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()
        self._transit_window_metrics: dict[str, int | float] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "inflight_dedupes": 0,
            "completed_requests": 0,
        }
        self._transit_location_label = "0.0, 0.0"
        self._transit_lat = 0.0
        self._transit_lon = 0.0
        self._transit_location_source = "default"
        self._personal_transit_chart_lookup: dict[str, int] = {}
        self._help_overlay_active = False
        self._help_marker_buttons: list[QToolButton] = []
        self._settings_dialog: QDialog | None = None
        self._size_checker_popup: SizeCheckerPopup | None = None
        self._dev_user_age_label: QLabel | None = None
        self._dev_age_distribution_canvas: FigureCanvas | None = None
        # Toggle to broaden inference source data (personal-only by default).
        self._dev_age_inference_include_all_chart_types = False
        self._restore_manage_charts_preferences()
        self._restore_visibility_preferences()

        layout = QVBoxLayout()
        self.setLayout(layout)
        configure_manage_dialog_chrome(self, layout)

        self.todays_transits_panel_button = QPushButton("Transit View") #Transit View
        self.todays_transits_panel_button.setObjectName("manage_toggle_transits_panel_button")
        self.todays_transits_panel_button.clicked.connect(
            self._toggle_todays_transits_panel
        )

        self.database_metrics_panel_button = QPushButton("⛁📊") #🗂️Database Metrics
        self.database_metrics_panel_button.setObjectName("manage_toggle_database_metrics_panel_button")
        self.database_metrics_panel_button.clicked.connect(
            self._toggle_database_metrics_panel
        )

        self.gen_pop_norms_panel_button = QPushButton("👨‍👨‍👧‍👧📊")
        self.gen_pop_norms_panel_button.setObjectName("manage_toggle_gen_pop_norms_panel_button")
        self.gen_pop_norms_panel_button.clicked.connect(
            self._toggle_gen_pop_norms_panel
        )

        self.similarities_panel_button = QPushButton("👬📊") #Similarities Analysis
        self.similarities_panel_button.setObjectName("manage_toggle_similarities_panel_button")
        self.similarities_panel_button.clicked.connect(
            self._toggle_similarities_panel
        )

        self.manage_collections_button = QPushButton("Manage Collections")
        self.manage_collections_button.setObjectName(
            "manage_toggle_collections_panel_button"
        )
        self.manage_collections_button.clicked.connect(
            self._toggle_manage_collections_panel
        )

        self.edit_charts_button = QPushButton("📝Database Manager") #Batch Edit #✎𓂃
        self.edit_charts_button.setObjectName("manage_toggle_batch_edit_panel_button")
        self.edit_charts_button.clicked.connect(self._toggle_edit_panel)

        self.search_panel_button = QPushButton("🔎")
        self.search_panel_button.setObjectName("manage_toggle_search_panel_button")
        self.search_panel_button.clicked.connect(self._toggle_search_panel)

        self.manage_settings_button = QPushButton("⚙️")
        self.manage_settings_button.setObjectName("manage_settings_button")
        self.manage_settings_button.clicked.connect(self._on_open_settings)

        for control_button in (
            self.todays_transits_panel_button,
            self.database_metrics_panel_button,
            self.gen_pop_norms_panel_button,
            self.similarities_panel_button,
            self.manage_collections_button,
            self.edit_charts_button,
            self.manage_settings_button,
            self.search_panel_button,
        ):
            control_button.setAutoDefault(False)
            control_button.setDefault(False)
            control_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            control_button.setMinimumWidth(0)
            control_button.setStyleSheet("padding: 1px 5px; font-size: 11px;")

        self.sort_button = QPushButton("Sort: Alphabetical") #default sorting method pt 2/2
        self.sort_button.setObjectName("manage_sort_button")
        self.sort_menu = QMenu(self)
        self.sort_action_date = self.sort_menu.addAction("Date added")
        self.sort_action_alpha = self.sort_menu.addAction("Alphabetical")
        self.sort_action_cursedness = self.sort_menu.addAction("Cursedness")
        self.sort_action_age = self.sort_menu.addAction("Age")
        self.sort_action_birthdate = self.sort_menu.addAction("Birthdate (month/day)")
        self.sort_action_familiarity = self.sort_menu.addAction("Familiarity")
        self.sort_action_known_duration = self.sort_menu.addAction("Time Known")
        self.sort_action_alignment = self.sort_menu.addAction("Alignment")
        self.sort_action_social_score = self.sort_menu.addAction("Social Score")
        self.sort_action_date.triggered.connect(lambda: self._set_sort_mode("date"))
        self.sort_action_alpha.triggered.connect(lambda: self._set_sort_mode("alpha"))
        self.sort_action_cursedness.triggered.connect(
            lambda: self._set_sort_mode("cursedness")
        )
        self.sort_action_age.triggered.connect(lambda: self._set_sort_mode("age"))
        self.sort_action_birthdate.triggered.connect(
            lambda: self._set_sort_mode("birthdate")
        )
        self.sort_action_familiarity.triggered.connect(
            lambda: self._set_sort_mode("familiarity")
        )
        self.sort_action_known_duration.triggered.connect(
            lambda: self._set_sort_mode("known_duration")
        )
        self.sort_action_alignment.triggered.connect(
            lambda: self._set_sort_mode("alignment")
        )
        self.sort_action_social_score.triggered.connect(
            lambda: self._set_sort_mode("social_score")
        )
        self.sort_button.setMenu(self.sort_menu)

        # Database View - Right Panel stack (search/edit interface panels).
        self.search_panel = self._build_search_panel()
        self.edit_panel = self._build_edit_panel()
        self.manage_collections_panel = self._build_manage_collections_panel()
        self.search_panel_scroll = self._wrap_right_panel(self.search_panel)
        self.edit_panel_scroll = self._wrap_right_panel(self.edit_panel)
        self.manage_collections_panel_scroll = self._wrap_right_panel(
            self.manage_collections_panel
        )
        self.right_panel_stack = QStackedWidget()
        self.right_panel_stack.setMinimumWidth(0)
        self._right_panel_widgets = {
            "search": self.search_panel_scroll,
            "edit": self.edit_panel_scroll,
            "manage_collections": self.manage_collections_panel_scroll,
        }
        for widget in self._right_panel_widgets.values():
            self.right_panel_stack.addWidget(widget)
        self._right_panel_visible = True
        self._active_right_panel = "search"
        self._right_panel_sizes = None

        # Database View - Left panel stack (database metrics + similarities analysis).
        self.selection_sentiment_panel = self._build_selection_sentiment_panel()
        self.selection_sentiment_panel_scroll = self._wrap_left_panel(
            self.selection_sentiment_panel
        )
        self.todays_transits_panel = self._build_todays_transits_panel()
        self.todays_transits_panel_scroll = self._wrap_left_panel(
            self.todays_transits_panel
        )
        self.similarities_analysis_panel = self._build_similarities_analysis_panel()
        self.similarities_analysis_panel_scroll = self._wrap_left_panel(
            self.similarities_analysis_panel
        )
        self.left_panel_stack = QStackedWidget()
        self.left_panel_stack.setMinimumWidth(0)
        self._left_panel_widgets = {
            "todays_transits": self.todays_transits_panel_scroll,
            "database_metrics": self.selection_sentiment_panel_scroll,
            "gen_pop_norms": self.selection_sentiment_panel_scroll,
            "similarities": self.similarities_analysis_panel_scroll,
        }
        for widget in self._left_panel_widgets.values():
            self.left_panel_stack.addWidget(widget)
        self._left_panel_visible = True
        self._active_left_panel = "todays_transits"
        self._left_panel_sizes = None

        left_panel_container = QWidget()
        left_panel_container_layout = QVBoxLayout()
        left_panel_container_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_container_layout.setSpacing(0)
        left_panel_container.setLayout(left_panel_container_layout)
        left_panel_container_layout.addWidget(self.left_panel_stack, 1)

        right_panel_container = QWidget()
        right_panel_container_layout = QVBoxLayout()
        right_panel_container_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_container_layout.setSpacing(0)
        right_panel_container.setLayout(right_panel_container_layout)
        right_panel_container_layout.addWidget(self.right_panel_stack, 1)

        panel_controls_row = QWidget()
        panel_controls_layout = QHBoxLayout()
        panel_controls_layout.setContentsMargins(0, 0, 0, 0)
        panel_controls_layout.setSpacing(8)
        panel_controls_row.setLayout(panel_controls_layout)

        left_controls_row = QWidget()
        left_controls_layout = QHBoxLayout()
        left_controls_layout.setContentsMargins(0, 0, 0, 0)
        left_controls_layout.setSpacing(4)
        left_controls_row.setLayout(left_controls_layout)
        left_controls_layout.addWidget(self.todays_transits_panel_button)
        left_controls_layout.addWidget(self.database_metrics_panel_button)
        left_controls_layout.addWidget(self.gen_pop_norms_panel_button)
        left_controls_layout.addWidget(self.similarities_panel_button)

        right_controls_row = QWidget()
        right_controls_layout = QHBoxLayout()
        right_controls_layout.setContentsMargins(0, 0, 0, 0)
        right_controls_layout.setSpacing(4)
        right_controls_row.setLayout(right_controls_layout)
        right_controls_layout.addWidget(self.manage_settings_button)
        right_controls_layout.addWidget(self.search_panel_button)
        right_controls_layout.addWidget(self.edit_charts_button)
        right_controls_layout.addWidget(self.manage_collections_button)

        panel_controls_layout.addWidget(left_controls_row, alignment=Qt.AlignLeft)
        panel_controls_layout.addStretch(1)
        panel_controls_layout.addWidget(right_controls_row, alignment=Qt.AlignRight)
        layout.addWidget(panel_controls_row)

        # Database View - Center list panel (chart list).
        self.list_widget = ChartListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setItemDelegate(ChartRowDelegate(self.list_widget))
        self.list_widget.setStyleSheet(
            "QListWidget {"
            "  background-color: #151515;"
            "  border: 1px solid #333333;"
            "}"
            "QListWidget::item {"
            "  padding: 6px 8px;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #2b3a4a;"
            "}"
        )
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self._load_chart_from_item)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.installEventFilter(self)
        
        self.list_panel = QWidget()
        self.list_panel.setMinimumWidth(420)
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_panel.setLayout(list_layout)
        list_header_row = QWidget()
        list_header_layout = QHBoxLayout()
        list_header_layout.setContentsMargins(0, 0, 0, 0)
        list_header_layout.setSpacing(8)
        list_header_row.setLayout(list_header_layout)

        self.collection_combo = QComboBox()
        for collection_label, collection_id in DEFAULT_COLLECTION_OPTIONS:
            self.collection_combo.addItem(collection_label, collection_id)
        self.collection_combo.currentIndexChanged.connect(self._on_collection_changed)
        list_header_layout.addWidget(self.collection_combo)
        list_header_layout.addWidget(self.sort_button, alignment=Qt.AlignRight)
        self._update_sort_button_label()
        list_layout.addWidget(list_header_row)
        list_layout.addWidget(self.list_widget, 1)
        self.charts_header_label = QLabel("Charts Selected: 0 of 0")
        self.charts_header_label.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        list_layout.addWidget(self.charts_header_label)

        # Database View - Content splitter (left panel stack, center list, right panel stack).
        self._content_splitter = QSplitter(Qt.Horizontal)
        self._content_splitter.setHandleWidth(6)
        self._content_splitter.setChildrenCollapsible(False)
        self._content_splitter.addWidget(left_panel_container)
        self._content_splitter.addWidget(self.list_panel)
        self._content_splitter.addWidget(right_panel_container)
        self._content_splitter.setCollapsible(0, True)
        self._content_splitter.setCollapsible(2, True)
        left_panel_container.setAttribute(Qt.WA_AlwaysStackOnTop, False)
        self.list_panel.setAttribute(Qt.WA_AlwaysStackOnTop, False)
        right_panel_container.setAttribute(Qt.WA_AlwaysStackOnTop, False)
        self._content_splitter.setStretchFactor(0, 0)
        self._content_splitter.setStretchFactor(1, 1)
        self._content_splitter.setStretchFactor(2, 0)
        configure_splitter_handle_resize_cursor(self._content_splitter)
        layout.addWidget(self._content_splitter, 1)

        self._shortcut_close_ctrl = QShortcut(QKeySequence("Ctrl+W"), self)
        self._shortcut_close_ctrl.activated.connect(self.close)
        self._shortcut_close_cmd = QShortcut(QKeySequence("Meta+W"), self)
        self._shortcut_close_cmd.activated.connect(self.close)
        self._shortcut_fullscreen_toggle = QShortcut(QKeySequence("F12"), self)
        self._shortcut_fullscreen_toggle.activated.connect(self._toggle_fullscreen)

        self._initial_progress_pending = True
        self._restore_window_settings()
        self._refresh_collection_controls()
        self._initialize_transit_location_defaults()
        self._refresh_todays_transits_panel()
        self._refresh_charts()
        apply_default_text_tooltips(self)

    # Database & Selection Analysis Panel (left sidebar).
    #export chart function:
    def _create_analysis_chart_header(
        self,
        layout: QVBoxLayout,
        title_text: str,
        chart_key: str,
        default_filename: str,
        dropdown_options: list[tuple[str, str]] | None = None,
        show_title: bool = True,
    ) -> None:
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(DATABASE_ANALYTICS_HEADER_SPACING)
        header_row.setLayout(header_layout)

        if show_title:
            title = QLabel(title_text)
            title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
            header_layout.addWidget(title)
        header_layout.addStretch(1)

        options = dropdown_options or [(title_text, chart_key)]
        dropdown = QComboBox()
        dropdown_font = QFont(dropdown.font())
        dropdown_font.setCapitalization(QFont.AllUppercase)
        if dropdown_font.pointSize() > 0:
            dropdown_font.setPointSize(max(7, dropdown_font.pointSize() - 2))
        dropdown.setFont(dropdown_font)
        dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dropdown.setMinimumContentsLength(14)
        dropdown.setStyleSheet(DATABASE_ANALYTICS_DROPDOWN_STYLE)
        for option_label, option_value in options:
            dropdown.addItem(option_label.upper(), option_value)
        preferred_mode_by_chart = {
            "planetary_sign_prevalence": self._sign_distribution_mode,
            "sign_prevalence": self._prevalence_mode,
            "dominant_signs": self._dominant_factors_mode,
            "cumulativedom_factors": self._cumulativedom_factors_mode,
            "species_distribution": self._species_distribution_mode,
            "birth_time": self._birth_time_mode,
            "age": self._age_mode,
            "birth_month": self._birth_month_mode,
            "birthplace": self._birthplace_mode,
            "gender": self._gender_mode,
        }
        preferred_mode = preferred_mode_by_chart.get(chart_key)
        if preferred_mode is not None:
            selected_index = dropdown.findData(preferred_mode)
            if selected_index >= 0:
                dropdown.setCurrentIndex(selected_index)
        dropdown.currentIndexChanged.connect(
            lambda _index, key=chart_key: self._on_analysis_chart_dropdown_changed(key)
        )
        header_layout.addWidget(dropdown, alignment=Qt.AlignRight)
        self._analysis_chart_dropdowns[chart_key] = dropdown

        export_button = QPushButton()
        share_icon_path = _get_share_icon_path()
        if share_icon_path:
            export_button.setIcon(QIcon(share_icon_path))
            export_button.setIconSize(QSize(*DATABASE_ANALYTICS_EXPORT_ICON_SIZE))
        else:
            export_button.setText("↗")
        export_button.setFlat(True)
        export_button.setFixedSize(*DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE)
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.setToolTip(f"Export {title_text} as CSV")
        export_button.clicked.connect(
            lambda _checked=False, key=chart_key, title=title_text: self._export_database_analysis_chart_csv(
                key,
                title,
            )
        )
        header_layout.addWidget(export_button, alignment=Qt.AlignRight)

        self._analysis_chart_filenames[chart_key] = default_filename
        layout.addWidget(header_row)

    def _add_left_panel_collapsible_section(
        self,
        panel: QWidget,
        layout: QVBoxLayout,
        title: str,
        *,
        expanded: bool = False,
        on_toggled: Callable[[bool], None] | None = None,
        section_key: str | None = None,
    ) -> QVBoxLayout:
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        section.setLayout(section_layout)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
        )

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(*DATABASE_ANALYTICS_CONTENT_MARGINS)
        content_layout.setSpacing(DATABASE_ANALYTICS_CONTENT_SPACING)
        content.setLayout(content_layout)
        content.setVisible(expanded)

        def toggle_content(checked: bool) -> None:
            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            if on_toggled is not None:
                on_toggled(checked)
            content.adjustSize()
            section.adjustSize()
            panel.adjustSize()
            panel.updateGeometry()

        toggle.toggled.connect(toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        layout.addWidget(section)
        if section_key is not None:
            self._database_metrics_section_widgets[section_key] = section
        return content_layout

    def _create_database_analytics_chart_container(self) -> tuple[QWidget, QVBoxLayout]:
        chart_container = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(*DATABASE_ANALYTICS_CHART_CONTENT_MARGINS)
        chart_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        chart_container.setLayout(chart_layout)
        return chart_container, chart_layout

    def _set_database_metrics_section_expanded(
        self,
        section_key: str,
        expanded: bool,
    ) -> None:
        self._database_metrics_section_expanded[section_key] = expanded
        self._visibility.set(f"database_metrics.{section_key}", expanded)
        if not expanded:
            layout = self._database_metrics_chart_layouts.get(section_key)
            if layout is not None:
                self._clear_layout(layout)
            return
        if (
            self._left_panel_visible
            and self._active_left_panel in {"database_metrics", "gen_pop_norms"}
        ):
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={section_key},
            )

    def _is_database_metrics_section_expanded(self, section_key: str) -> bool:
        return self._database_metrics_section_expanded.get(section_key, False)

    def _is_database_metrics_section_visible(self, section_key: str) -> bool:
        return self._database_metrics_section_visible.get(section_key, True)

    def _set_database_metrics_section_visible(self, section_key: str, visible: bool) -> None:
        self._database_metrics_section_visible[section_key] = visible
        self._visibility.set(f"database_metrics_visibility.{section_key}", visible)
        self._sync_database_metrics_section_visibility()

    def _available_sign_distribution_dropdown_options(self) -> list[tuple[str, str]]:
        if self._database_metrics_baseline_mode != "gen_pop":
            return list(SIGN_DISTRIBUTION_DROPDOWN_OPTIONS)
        return [
            (label, value)
            for label, value in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
            if value not in GEN_POP_UNSUPPORTED_SIGN_DISTRIBUTION_MODES
        ]

    def _available_gender_dropdown_options(self) -> list[tuple[str, str]]:
        if self._database_metrics_baseline_mode != "gen_pop":
            return list(GENDER_DROPDOWN_OPTIONS)
        return [
            (label, value)
            for label, value in GENDER_DROPDOWN_OPTIONS
            if value not in GEN_POP_UNSUPPORTED_GENDER_MODES
        ]

    def _sync_database_metrics_section_visibility(self) -> None:
        is_gen_pop = self._database_metrics_baseline_mode == "gen_pop"
        for section_key, section_widget in self._database_metrics_section_widgets.items():
            if is_gen_pop:
                section_widget.setVisible(section_key not in GEN_POP_HIDDEN_DATABASE_METRIC_SECTIONS)
            else:
                section_widget.setVisible(self._is_database_metrics_section_visible(section_key))

    def _sync_gen_pop_panel_visibility(self) -> None:
        sign_dropdown = self._analysis_chart_dropdowns.get("planetary_sign_prevalence")
        if sign_dropdown is not None:
            options = self._available_sign_distribution_dropdown_options()
            allowed_modes = {value for _label, value in options}
            previous_mode = self._sign_distribution_mode
            if previous_mode not in allowed_modes:
                previous_mode = options[0][1] if options else "Sun"

            sign_dropdown.blockSignals(True)
            sign_dropdown.clear()
            for option_label, option_value in options:
                sign_dropdown.addItem(option_label.upper(), option_value)
            selected_index = sign_dropdown.findData(previous_mode)
            if selected_index < 0 and sign_dropdown.count() > 0:
                selected_index = 0
            if selected_index >= 0:
                sign_dropdown.setCurrentIndex(selected_index)
                current_mode = sign_dropdown.currentData()
                if isinstance(current_mode, str):
                    self._sign_distribution_mode = current_mode
            sign_dropdown.blockSignals(False)

        gender_dropdown = self._analysis_chart_dropdowns.get("gender")
        if gender_dropdown is not None:
            options = self._available_gender_dropdown_options()
            allowed_modes = {value for _label, value in options}
            previous_mode = self._gender_mode
            if previous_mode not in allowed_modes:
                previous_mode = options[0][1] if options else "actual_gender"

            gender_dropdown.blockSignals(True)
            gender_dropdown.clear()
            for option_label, option_value in options:
                gender_dropdown.addItem(option_label.upper(), option_value)
            selected_index = gender_dropdown.findData(previous_mode)
            if selected_index < 0 and gender_dropdown.count() > 0:
                selected_index = 0
            if selected_index >= 0:
                gender_dropdown.setCurrentIndex(selected_index)
                current_mode = gender_dropdown.currentData()
                if isinstance(current_mode, str):
                    self._gender_mode = current_mode
            gender_dropdown.blockSignals(False)

    def _chart_data_visibility_options(self) -> dict[str, bool]:
        return {
            "show_cursedness": self._visibility.get("chart_data.cursedness"),
            "show_dnd_species": self._visibility.get("chart_data.dnd_species"),
        }
    def _expanded_database_metric_sections(self) -> list[str]:
        section_order = [
            "planetary_sign_prevalence",
            "sentiment_prevalence",
            "relationship_prevalence",
            "social_score_summary",
            "alignment_summary",
            "sign_prevalence",
            "dominant_signs",
            "cumulativedom_factors",
            "species_distribution",
            "birth_time",
            "age",
            "birth_month",
            "birthplace",
            "gender",
        ]
        return [
            section_key
            for section_key in section_order
            if self._is_database_metrics_section_expanded(section_key)
            and not (
                self._database_metrics_baseline_mode == "gen_pop"
                and section_key in GEN_POP_HIDDEN_DATABASE_METRIC_SECTIONS
            )
        ]

    def _should_use_incremental_metrics_refresh(self) -> bool:
        expanded_sections = self._expanded_database_metric_sections()
        return len(expanded_sections) >= 4

    def _schedule_incremental_metrics_refresh(
        self,
        *,
        changed_ids: set[int] | None = None,
        force_full_refresh: bool = False,
    ) -> None:
        self._incremental_metrics_refresh_sections = self._expanded_database_metric_sections()
        self._incremental_metrics_refresh_changed_ids = set(changed_ids or set())
        self._incremental_metrics_force_full_refresh = force_full_refresh
        if self._incremental_metrics_refresh_scheduled:
            return
        self._incremental_metrics_refresh_scheduled = True
        QTimer.singleShot(0, self._run_incremental_metrics_refresh_step)

    def _run_incremental_metrics_refresh_step(self) -> None:
        if not self._incremental_metrics_refresh_sections:
            self._incremental_metrics_refresh_scheduled = False
            self._incremental_metrics_force_full_refresh = False
            self._incremental_metrics_refresh_changed_ids.clear()
            return

        section_key = self._incremental_metrics_refresh_sections.pop(0)
        changed_ids = (
            set(self._incremental_metrics_refresh_changed_ids)
            if self._incremental_metrics_force_full_refresh or self._incremental_metrics_refresh_changed_ids
            else None
        )
        self._update_sentiment_tally(
            update_database_metrics=True,
            update_similarities=False,
            sections_to_refresh={section_key},
            changed_ids=changed_ids,
            force_full_refresh=self._incremental_metrics_force_full_refresh,
        )
        self._incremental_metrics_force_full_refresh = False
        self._incremental_metrics_refresh_changed_ids.clear()
        QTimer.singleShot(0, self._run_incremental_metrics_refresh_step)

    def _update_position_sign_subheader(self) -> None:
        subheader = getattr(self, "position_sign_distribution_subheader", None)
        if subheader is None:
            return
        mode_label = SIGN_DISTRIBUTION_MODE_LABELS.get(
            self._sign_distribution_mode,
            "Sun Sign",
        )
        if self._database_metrics_baseline_mode == "gen_pop":
            subheader.setText(
                f"Distribution of {mode_label.lower()} compared to estimated general population"
            )
            return
        subheader.setText(f"Distribution of {mode_label.lower()} in database")


    def _update_gender_subheader(self) -> None:
        subheader = getattr(self, "gender_subheader", None)
        unknown_note = getattr(self, "gender_unknown_note", None)
        if subheader is None:
            return
        show_unknown_note = (
            self._database_metrics_baseline_mode == "gen_pop"
            and self._gender_mode == "actual_gender"
        )
        if show_unknown_note:
            subheader.setText(GEN_POP_ACTUAL_GENDER_CAPTION)
        else:
            subheader.setText("Actual + guessed gender distribution")
        if unknown_note is not None:
            unknown_note.setVisible(show_unknown_note)

    def _gen_pop_planet_sign_norms_for_database_size(
        self,
        chart_count: int,
    ) -> dict[str, dict[str, float]]:
        sun_norms = {
            sign: (float(details["percent"]) / 100.0)
            for sign, details in SUN_SIGN_DISTRIBUTION_AGGREGATED.items()
        }
        mercury_norms = {
            sign: (float(details["percent"]) / 100.0)
            for sign, details in INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED["Mercury"].items()
        }
        venus_norms = {
            sign: (float(details["percent"]) / 100.0)
            for sign, details in INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED["Venus"].items()
        }
        equal_norms = {sign: (1.0 / len(ZODIAC_NAMES)) for sign in ZODIAC_NAMES}
        return {
            "Sun": sun_norms,
            "Mercury": mercury_norms,
            "Venus": venus_norms,
            "Moon": equal_norms,
            "Mars": equal_norms,
            "Jupiter": equal_norms,
            "Saturn": equal_norms,
            "Uranus": equal_norms,
            "Neptune": equal_norms,
            "Pluto": equal_norms,
            "Rahu": equal_norms,
            "Ketu": equal_norms,
        }

    def _update_dominant_factors_subheader(self, *, use_selection_scope: bool = False) -> None:
        subheader = getattr(self, "dominant_factors_subheader", None)
        if subheader is None:
            return
        scope_label = "selection" if use_selection_scope else "database"
        label_by_mode = {
            "top3_signs": f"top 3 dominant signs for charts in {scope_label}",
            "top3_planets": f"top 3 dominant bodies for charts in {scope_label}",
            "top3_houses": f"top 3 dominant houses for charts in {scope_label}",
        }
        subheader.setText(label_by_mode.get(self._dominant_factors_mode, label_by_mode["top3_signs"]))

    def _update_cumulativedom_factors_subheader(self, *, use_selection_scope: bool = False) -> None:
        subheader = getattr(self, "cumulativedom_factors_subheader", None)
        if subheader is None:
            return
        scope_label = "selection" if use_selection_scope else "database"
        label_by_mode = {
            "cumulative_signs": f"Cumulative weight of signs across all charts in {scope_label}",
            "cumulative_planets": f"Cumulative weight of bodies across all charts in {scope_label}",
            "cumulative_houses": f"Cumulative weight of houses across all charts in {scope_label}",
        }
        subheader.setText(
            label_by_mode.get(self._cumulativedom_factors_mode, label_by_mode["cumulative_signs"])
        )

    def _update_prevalence_subheader(self) -> None:
        subheader = getattr(self, "prevalence_subheader", None)
        if subheader is None:
            return
        label_by_mode = {
            "sign_prevalence": "Distribution of signs (all positions) in database",
            "house_prevalence": "Distribution of houses (all positions) in database",
            "elemental_prevalence": "Distribution of elements in database",
            "nakshatra_prevalence": "Distribution of nakshatras in database",
        }
        subheader.setText(
            label_by_mode.get(self._prevalence_mode, label_by_mode["sign_prevalence"])
        )

    def _on_analysis_chart_dropdown_changed(self, chart_key: str) -> None:
        if chart_key == "species_distribution":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._species_distribution_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/species_distribution_mode",
                        self._species_distribution_mode,
                    )
            # Avoid list/filter repopulation when only the analytics display mode
            # changes. Re-render analytics from current cached data instead.
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "birth_time":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._birth_time_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/birth_time_mode",
                        self._birth_time_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "age":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._age_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/age_mode",
                        self._age_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "birth_month":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._birth_month_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/birth_month_mode",
                        self._birth_month_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return


        if chart_key == "gender":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._gender_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/gender_mode",
                        self._gender_mode,
                    )
            self._update_gender_subheader()
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "birthplace":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._birthplace_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/birthplace_mode",
                        self._birthplace_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "planetary_sign_prevalence":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._sign_distribution_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/sign_distribution_mode",
                        self._sign_distribution_mode,
                    )
            self._update_position_sign_subheader()
            self._update_gender_subheader()
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "sign_prevalence":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._prevalence_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/prevalence_mode",
                        self._prevalence_mode,
                    )
            self._update_prevalence_subheader()
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            return

        if chart_key == "dominant_signs":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._dominant_factors_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/dominant_factors_mode",
                        self._dominant_factors_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            self._update_dominant_factors_subheader(
                use_selection_scope=self.list_widget is not None and len(self.list_widget.selectedItems()) > 0
            )
            return

        if chart_key == "cumulativedom_factors":
            dropdown = self._analysis_chart_dropdowns.get(chart_key)
            if dropdown is not None:
                selected_mode = dropdown.currentData()
                if isinstance(selected_mode, str):
                    self._cumulativedom_factors_mode = selected_mode
                    self._settings.setValue(
                        "manage_charts/cumulativedom_factors_mode",
                        self._cumulativedom_factors_mode,
                    )
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
                sections_to_refresh={chart_key},
            )
            self._update_cumulativedom_factors_subheader()

    def _restore_manage_charts_preferences(self) -> None:
        stored_sort_mode = self._settings.value("manage_charts/sort_mode", "alpha")
        if isinstance(stored_sort_mode, str):
            self._sort_mode = (
                "alpha" if stored_sort_mode == "alpha_rev" else stored_sort_mode
            )

        stored_sort_desc = self._settings.value("manage_charts/sort_descending", None)
        if stored_sort_desc is None:
            self._sort_descending = stored_sort_mode in {
                "alpha_rev",
                "cursedness",
                "familiarity",
                "known_duration",
                "alignment",
                "social_score",
                "date",
            }
        else:
            self._sort_descending = str(stored_sort_desc).lower() in {"1", "true", "yes"}

        stored_sign_mode = self._settings.value(
            "manage_charts/sign_distribution_mode",
            self._sign_distribution_mode,
        )
        if isinstance(stored_sign_mode, str):
            self._sign_distribution_mode = stored_sign_mode

        stored_prevalence_mode = self._settings.value(
            "manage_charts/prevalence_mode",
            self._prevalence_mode,
        )
        if isinstance(stored_prevalence_mode, str):
            self._prevalence_mode = stored_prevalence_mode

        stored_dominant_factors_mode = self._settings.value(
            "manage_charts/dominant_factors_mode",
            self._dominant_factors_mode,
        )
        if isinstance(stored_dominant_factors_mode, str):
            self._dominant_factors_mode = {"dominant_signs":"top3_signs","dominant_planets":"top3_planets","dominant_houses":"top3_houses","dominant_sign_frequency":"top3_signs"}.get(stored_dominant_factors_mode, stored_dominant_factors_mode)

        stored_cumulativedom_factors_mode = self._settings.value(
            "manage_charts/cumulativedom_factors_mode",
            self._cumulativedom_factors_mode,
        )
        if isinstance(stored_cumulativedom_factors_mode, str):
            self._cumulativedom_factors_mode = {"cumulativedom_signs":"cumulative_signs","cumulativedom_planets":"cumulative_planets","cumulativedom_houses":"cumulative_houses"}.get(stored_cumulativedom_factors_mode, stored_cumulativedom_factors_mode)

        stored_species_mode = self._settings.value(
            "manage_charts/species_distribution_mode",
            self._species_distribution_mode,
        )
        if isinstance(stored_species_mode, str):
            self._species_distribution_mode = stored_species_mode

        stored_birth_time_mode = self._settings.value(
            "manage_charts/birth_time_mode",
            self._birth_time_mode,
        )
        if isinstance(stored_birth_time_mode, str):
            self._birth_time_mode = stored_birth_time_mode

        stored_age_mode = self._settings.value(
            "manage_charts/age_mode",
            self._age_mode,
        )
        if isinstance(stored_age_mode, str):
            self._age_mode = stored_age_mode

        stored_birth_month_mode = self._settings.value(
            "manage_charts/birth_month_mode",
            self._birth_month_mode,
        )
        if isinstance(stored_birth_month_mode, str):
            self._birth_month_mode = stored_birth_month_mode

        stored_birthplace_mode = self._settings.value(
            "manage_charts/birthplace_mode",
            self._birthplace_mode,
        )
        if isinstance(stored_birthplace_mode, str):
            self._birthplace_mode = stored_birthplace_mode

        stored_gender_mode = self._settings.value(
            "manage_charts/gender_mode",
            self._gender_mode,
        )
        if isinstance(stored_gender_mode, str):
            self._gender_mode = stored_gender_mode

        stored_baseline_mode = self._settings.value(
            "manage_charts/database_metrics_baseline_mode",
            self._database_metrics_baseline_mode,
        )
        if isinstance(stored_baseline_mode, str) and stored_baseline_mode in {
            "database",
            "gen_pop",
        }:
            self._database_metrics_baseline_mode = stored_baseline_mode

        self._custom_collections = self._load_custom_collections_from_settings()
        stored_collection_id = self._settings.value(
            "manage_charts/active_collection_id",
            DEFAULT_COLLECTION_ALL,
        )
        self._active_collection_id = self._coerce_active_collection_id(stored_collection_id)

    def _load_custom_collections_from_settings(self) -> dict[str, CustomCollection]:
        raw_value = self._settings.value("manage_charts/custom_collections", "[]")
        parsed: object = []
        if isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed = []
        elif isinstance(raw_value, list):
            parsed = raw_value

        collections: dict[str, CustomCollection] = {}
        if not isinstance(parsed, list):
            return collections
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            raw_name = entry.get("name")
            raw_id = entry.get("id")
            if raw_name is None:
                continue
            name = sanitize_collection_name(raw_name)
            collection_id = normalize_collection_id(raw_id or name.replace(" ", "_"))
            if collection_id in DEFAULT_COLLECTION_IDS or collection_id in collections:
                continue
            raw_chart_ids = entry.get("chart_ids", [])
            chart_ids: set[int] = set()
            if isinstance(raw_chart_ids, list):
                for value in raw_chart_ids:
                    try:
                        chart_ids.add(int(value))
                    except (TypeError, ValueError):
                        continue
            collections[collection_id] = CustomCollection(
                collection_id=collection_id,
                name=name,
                chart_ids=frozenset(chart_ids),
            )
        return collections

    def _save_custom_collections_to_settings(self) -> None:
        payload = [
            {
                "id": collection.collection_id,
                "name": collection.name,
                "chart_ids": sorted(collection.chart_ids),
            }
            for collection in self._custom_collections.values()
        ]
        self._settings.setValue("manage_charts/custom_collections", json.dumps(payload))

    def _coerce_active_collection_id(self, value: object) -> str:
        candidate = normalize_collection_id(value)
        if candidate == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES:
            if self._show_possible_duplicates_collection:
                return candidate
            return DEFAULT_COLLECTION_ALL
        if candidate in DEFAULT_COLLECTION_IDS or candidate in self._custom_collections:
            return candidate
        return DEFAULT_COLLECTION_ALL

    def _restore_visibility_preferences(self) -> None:
        for key in DATABASE_ANALYTICS_SECTION_KEYS:
            section_key = key.replace("database_metrics.", "", 1)
            self._database_metrics_section_expanded[section_key] = self._visibility.get(key)

        self._database_metrics_section_visible["species_distribution"] = self._visibility.get(
            "database_metrics_visibility.species_distribution"
        )

    def _update_sort_button_label(self) -> None:
        mode = self._sort_mode
        direction = "↓" if self._sort_descending else "↑"
        if mode == "date":
            self.sort_button.setText(f"Sort: Date added {direction}")
        elif mode == "alpha":
            self.sort_button.setText(f"Sort: Alphabetical {direction}")
        elif mode == "cursedness":
            self.sort_button.setText(f"Sort: Cursedness {direction}")
        elif mode == "age":
            self.sort_button.setText(f"Sort: Age {direction}")
        elif mode == "birthdate":
            self.sort_button.setText(f"Sort: Birthdate {direction}")
        elif mode == "familiarity":
            self.sort_button.setText(f"Sort: Familiarity {direction}")
        elif mode == "known_duration": #should we rename this to time_known?
            self.sort_button.setText(f"Sort: Time Known {direction}")
        elif mode == "alignment":
            self.sort_button.setText(f"Sort: Alignment {direction}")
        elif mode == "social_score":
            self.sort_button.setText(f"Sort: Social Score {direction}")
        else:
            self._sort_mode = "alpha"
            self._sort_descending = False
            self.sort_button.setText("Sort: Alphabetical ↑")

    def _build_analysis_export_rows(
        self,
        labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        selection_counts: list[int],
        database_counts: list[int],
        loaded_charts: int,
    ) -> list[tuple[str, float, float, float, int, int, float]]:
        rows = []
        total_database_count = float(sum(database_counts))
        for (
            label,
            selection_value,
            database_value,
            selection_count,
            database_count,
        ) in zip(
            labels,
            selection_values,
            database_values,
            selection_counts,
            database_counts,
        ):
            display_selection = selection_value if loaded_charts else database_value
            difference = display_selection - database_value
            display_selection_count = selection_count if loaded_charts else database_count
            database_count_value = int(database_count)
            percent_of_database = (
                (float(display_selection_count) / total_database_count)
                if total_database_count
                else 0.0
            )
            rows.append(
                (
                    label,
                    display_selection,
                    database_value,
                    difference,
                    int(display_selection_count),
                    database_count_value,
                    percent_of_database,
                )
            )
        return rows

    def _reactivate_database_view(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def _export_database_analysis_chart_csv(self, chart_key: str, chart_title: str) -> None:
        rows = self._analysis_chart_export_rows.get(chart_key) or []
        if not rows:
            QMessageBox.information(
                self,
                "incomplete birthdate",
                "There is incomplete birthdate available to export yet.",
            )
            return

        export_date = datetime.date.today().isoformat()
        default_stem = self._analysis_chart_filenames.get(chart_key, chart_key)
        default_filename = f"{default_stem}-{export_date}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {chart_title} as CSV",
            default_filename,
            "CSV Files (*.csv)",
        )
        # Native save dialogs can briefly reactivate the main Natal Chart View when
        # they close; force Database View back to the foreground.
        QTimer.singleShot(0, self._reactivate_database_view)
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "label",
                        "selection",
                        "database",
                        "difference",
                        "selection_qty",
                        "database_qty",
                        "% of DB",
                    ]
                )
                for (
                    label,
                    selection_value,
                    database_value,
                    difference,
                    selection_count,
                    database_count,
                    percent_of_database,
                ) in rows:
                    writer.writerow(
                        [
                            label,
                            round(selection_value, 8),
                            round(database_value, 8),
                            round(difference, 8),
                            selection_count,
                            database_count,
                            round(percent_of_database, 8),
                        ]
                    )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export {chart_title} as CSV:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved chart CSV to:\n{file_path}",
        )

    #Now the actual graphs:
    def _build_selection_sentiment_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)
        layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        panel.setLayout(layout)

        def add_database_subheader(text: str = "") -> QLabel:
            subheader = QLabel(text)
            subheader.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
            subheader.setWordWrap(DATABASE_VIEW_SUBHEADER_WORD_WRAP)
            return subheader

        self.database_metrics_panel_header_label = QLabel("Database Analytics")
        self.database_metrics_panel_header_label.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(self.database_metrics_panel_header_label)

        # PLANETARY/POSITION SIGN DISTRIBUTION SECTION
        position_sign_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Sign Distribution by Placement",
            section_key="planetary_sign_prevalence",
            expanded=self._is_database_metrics_section_expanded("planetary_sign_prevalence"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "planetary_sign_prevalence",
                checked,
            ),
        )
        self._database_metrics_section_expanded["planetary_sign_prevalence"] = self._is_database_metrics_section_expanded("planetary_sign_prevalence")
        self._create_analysis_chart_header(
            position_sign_section_layout,
            "Sign Distribution by Placement",
            "planetary_sign_prevalence",
            "planetary_sign_prevalence",
            dropdown_options=SIGN_DISTRIBUTION_DROPDOWN_OPTIONS,
            show_title=False,
        )
        self.position_sign_distribution_subheader = add_database_subheader()
        self._update_position_sign_subheader()
        position_sign_section_layout.addWidget(self.position_sign_distribution_subheader)
        (
            self.position_sign_distribution_chart_container,
            self.position_sign_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["planetary_sign_prevalence"] = (
            self.position_sign_distribution_chart_layout
        )
        position_sign_section_layout.addWidget(self.position_sign_distribution_chart_container)

        #SENTIMENT PREVALENCE SECTION
        sentiment_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Sentiment Prevalence",
            section_key="sentiment_prevalence",
            expanded=self._is_database_metrics_section_expanded("sentiment_prevalence"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "sentiment_prevalence",
                checked,
            ),
        )
        self._database_metrics_section_expanded["sentiment_prevalence"] = self._is_database_metrics_section_expanded("sentiment_prevalence")
        #Sentiment Prevalence Chart Header
        self._create_analysis_chart_header(
            sentiment_section_layout,
            "Sentiment Prevalence",
            "sentiment_prevalence",
            "sentiment_prevalence",
            show_title=False,
        )
        sentiment_subheader = add_database_subheader("Distribution of sentiments in database")
        sentiment_section_layout.addWidget(sentiment_subheader)
        #Sentiment Prevalence Chart
        (
            self.sentiment_chart_container,
            self.sentiment_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["sentiment_prevalence"] = (
            self.sentiment_chart_layout
        )
        sentiment_section_layout.addWidget(self.sentiment_chart_container)

        self.include_placeholder_sentiment_checkbox = QCheckBox(
            "include placeholders"
        )
        self.include_placeholder_sentiment_checkbox.setChecked(True)
        self.include_placeholder_sentiment_checkbox.toggled.connect(
            lambda _checked: self._update_sentiment_tally(update_similarities=False)
        )
        sentiment_section_layout.addWidget(self.include_placeholder_sentiment_checkbox)

        #RELATIONSHIP PREVALENCE SECTION
        relationship_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Relationship Prevalence",
            section_key="relationship_prevalence",
            expanded=self._is_database_metrics_section_expanded("relationship_prevalence"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "relationship_prevalence",
                checked,
            ),
        )
        self._database_metrics_section_expanded["relationship_prevalence"] = self._is_database_metrics_section_expanded("relationship_prevalence")
        #Relationship Prevalence Chart Header
        self._create_analysis_chart_header(
            relationship_section_layout,
            "Relationship Prevalence",
            "relationship_prevalence",
            "relationship_prevalence",
            show_title=False,
        )
        relationship_subheader = add_database_subheader(
            "Distribution of relationship types in database"
        )
        relationship_section_layout.addWidget(relationship_subheader)

        #Relationship Prevalence Chart
        (
            self.relationship_chart_container,
            self.relationship_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["relationship_prevalence"] = (
            self.relationship_chart_layout
        )
        relationship_section_layout.addWidget(self.relationship_chart_container)
        self.include_placeholder_relationship_checkbox = QCheckBox(
            "include placeholders"
        )
        self.include_placeholder_relationship_checkbox.setChecked(True)
        self.include_placeholder_relationship_checkbox.toggled.connect(
            lambda _checked: self._update_sentiment_tally(update_similarities=False)
        )
        relationship_section_layout.addWidget(
            self.include_placeholder_relationship_checkbox
        )

        #SOCIAL SCORE SUMMARY SECTION
        social_score_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Social Score",
            section_key="social_score_summary",
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "social_score_summary",
                checked,
            ),
        )
        self._database_metrics_section_expanded["social_score_summary"] = self._is_database_metrics_section_expanded("social_score_summary")
        self._create_analysis_chart_header(
            social_score_section_layout,
            "Social Score",
            "social_score_summary",
            "social_score_summary",
            show_title=False,
        )
        social_score_subheader = add_database_subheader(
            "Median and average social score"
        )
        social_score_section_layout.addWidget(social_score_subheader)
        (
            self.social_score_summary_chart_container,
            self.social_score_summary_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["social_score_summary"] = (
            self.social_score_summary_chart_layout
        )
        social_score_section_layout.addWidget(self.social_score_summary_chart_container)

        #ALIGNMENT SUMMARY SECTION
        alignment_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Alignment",
            section_key="alignment_summary",
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "alignment_summary",
                checked,
            ),
        )
        self._database_metrics_section_expanded["alignment_summary"] = self._is_database_metrics_section_expanded("alignment_summary")
        self._create_analysis_chart_header(
            alignment_section_layout,
            "Alignment",
            "alignment_summary",
            "alignment_summary",
            show_title=False,
        )
        alignment_norms_subheader = add_database_subheader(
            "Median and average alignment score"
        )
        alignment_section_layout.addWidget(alignment_norms_subheader)
        (
            self.alignment_summary_chart_container,
            self.alignment_summary_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["alignment_summary"] = (
            self.alignment_summary_chart_layout
        )
        alignment_section_layout.addWidget(self.alignment_summary_chart_container)

        alignment_cumulative_subheader = add_database_subheader(
            "Cumulative alignment of current selection"
        )
        alignment_section_layout.addWidget(alignment_cumulative_subheader)
        (
            self.alignment_cumulative_chart_container,
            self.alignment_cumulative_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["alignment_summary_cumulative"] = (
            self.alignment_cumulative_chart_layout
        )
        alignment_section_layout.addWidget(self.alignment_cumulative_chart_container)

        #SIGN PREVALENCE SECTION
        sign_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Prevalence",
            section_key="sign_prevalence",
            expanded=self._is_database_metrics_section_expanded("sign_prevalence"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "sign_prevalence",
                checked,
            ),
        )
        self._database_metrics_section_expanded["sign_prevalence"] = self._is_database_metrics_section_expanded("sign_prevalence")
        #Sign Prevalence Chart Header
        self._create_analysis_chart_header(
            sign_section_layout,
            "Prevalence",
            "sign_prevalence",
            "sign_prevalence",
            dropdown_options=[
                ("Sign Prevalence", "sign_prevalence"),
                ("House Prevalence", "house_prevalence"),
                ("Elemental Prevalence", "elemental_prevalence"),
                ("Nakshatra Prevalence", "nakshatra_prevalence"),
            ],
            show_title=False,
        )
        self.prevalence_subheader = add_database_subheader()
        self._update_prevalence_subheader()
        sign_section_layout.addWidget(self.prevalence_subheader)
        #Sign Prevalence Chart
        (
            self.sign_distribution_chart_container,
            self.sign_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["sign_prevalence"] = (
            self.sign_distribution_chart_layout
        )
        sign_section_layout.addWidget(self.sign_distribution_chart_container)

        #DOMINANT FACTORS SECTION
        dominant_sign_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Dominant Factors (by top 3)",
            section_key="dominant_signs",
            expanded=self._is_database_metrics_section_expanded("dominant_signs"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "dominant_signs",
                checked,
            ),
        )
        self._database_metrics_section_expanded["dominant_signs"] = self._is_database_metrics_section_expanded("dominant_signs")
        #Dominant Factors Chart Header
        self._create_analysis_chart_header(
            dominant_sign_section_layout,
            "Dominant Factors (by top 3)",
            "dominant_signs",
            "dominant_signs",
            dropdown_options=[
                ("Dominant Signs (Top 3)", "top3_signs"),
                ("Dominant Bodies (Top 3)", "top3_planets"),
                ("Dominant Houses (Top 3)", "top3_houses"),
            ],
            show_title=False,
        )
        self.dominant_factors_subheader = add_database_subheader("top 3 dominant signs for charts in database")
        dominant_sign_section_layout.addWidget(self.dominant_factors_subheader)
        self._update_dominant_factors_subheader()
        #Dominant Sign Chart
        (
            self.dominant_sign_chart_container,
            self.dominant_sign_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["dominant_signs"] = (
            self.dominant_sign_chart_layout
        )
        dominant_sign_section_layout.addWidget(self.dominant_sign_chart_container)

        #cumulativedom FACTORS SECTION
        cumulativedom_sign_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Dominant Factors (cumulative weight)",
            section_key="cumulativedom_factors",
            expanded=self._is_database_metrics_section_expanded("cumulativedom_factors"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "cumulativedom_factors",
                checked,
            ),
        )
        self._database_metrics_section_expanded["cumulativedom_factors"] = self._is_database_metrics_section_expanded("cumulativedom_factors")
        self._create_analysis_chart_header(
            cumulativedom_sign_section_layout,
            "Dominant Factors (cumulative weight)",
            "cumulativedom_factors",
            "cumulativedom_factors",
            dropdown_options=[
                ("Dominant Signs (Cumulative Weight)", "cumulative_signs"),
                ("Dominant Bodies (Cumulative Weight)", "cumulative_planets"),
                ("Dominant Houses (Cumulative Weight)", "cumulative_houses"),
            ],
            show_title=False,
        )
        self.cumulativedom_factors_subheader = add_database_subheader(
            "Dominant signs in database (by cumulative weight)"
        )
        cumulativedom_sign_section_layout.addWidget(self.cumulativedom_factors_subheader)
        self._update_cumulativedom_factors_subheader()
        (
            self.cumulativedom_sign_chart_container,
            self.cumulativedom_sign_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["cumulativedom_factors"] = (
            self.cumulativedom_sign_chart_layout
        )
        cumulativedom_sign_section_layout.addWidget(self.cumulativedom_sign_chart_container)

        #SPECIES DISTRIBUTION SECTION
        species_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Species Distribution",
            section_key="species_distribution",
            expanded=self._is_database_metrics_section_expanded("species_distribution"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "species_distribution",
                checked,
            ),
        )
        self._database_metrics_section_expanded["species_distribution"] = self._is_database_metrics_section_expanded("species_distribution")
        self._database_metrics_section_visible["species_distribution"] = self._is_database_metrics_section_visible("species_distribution")
        #Species Distribution Chart Header
        self._create_analysis_chart_header(
            species_section_layout,
            "Species Distribution",
            "species_distribution",
            "species_distribution",
            dropdown_options=[
                ("#1 Ranked", "top_ranked"),
                ("Top 3 Ranked", "top_three_ranked"),
                ("Top 2 & 3 Only", "top_two_three_only"),
            ],
            show_title=False,
        )
        species_subheader = add_database_subheader("Distribution of D&D species in database")
        species_section_layout.addWidget(species_subheader)

        #Species Distribution Chart
        (
            self.species_distribution_chart_container,
            self.species_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["species_distribution"] = (
            self.species_distribution_chart_layout
        )
        species_section_layout.addWidget(self.species_distribution_chart_container)
        
        #BIRTH TIME SECTION
        birth_time_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Birth Time",
            section_key="birth_time",
            expanded=self._is_database_metrics_section_expanded("birth_time"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "birth_time",
                checked,
            ),
        )
        self._database_metrics_section_expanded["birth_time"] = self._is_database_metrics_section_expanded("birth_time")
        self._create_analysis_chart_header(
            birth_time_section_layout,
            "Birth Time",
            "birth_time",
            "birth_time",
            dropdown_options=[
                ("Mean", "mean"),
                ("Mode (rounded hour)", "mode_hour"),
                ("Median", "median"),
            ],
            show_title=False,
        )
        birth_time_subheader = add_database_subheader("Birth time summary across loaded charts")
        birth_time_section_layout.addWidget(birth_time_subheader)
        (
            self.birth_time_chart_container,
            self.birth_time_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["birth_time"] = self.birth_time_chart_layout
        birth_time_section_layout.addWidget(self.birth_time_chart_container)

        # AGE SECTION
        age_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Age",
            section_key="age",
            expanded=self._is_database_metrics_section_expanded("age"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "age",
                checked,
            ),
        )
        self._database_metrics_section_expanded["age"] = self._is_database_metrics_section_expanded("age")
        self._create_analysis_chart_header(
            age_section_layout,
            "Age",
            "age",
            "age",
            dropdown_options=[
                ("Age", "age_distribution"),
                ("Time Known", "time_known_distribution"),
            ],
            show_title=False,
        )
        age_subheader = add_database_subheader("Distribution of age and total time known")
        age_section_layout.addWidget(age_subheader)
        (
            self.age_chart_container,
            self.age_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["age"] = self.age_chart_layout
        age_section_layout.addWidget(self.age_chart_container)

        #BIRTH MONTH SECTION
        birth_month_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Birthday",
            section_key="birth_month",
            expanded=self._is_database_metrics_section_expanded("birth_month"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "birth_month",
                checked,
            ),
        )
        self._database_metrics_section_expanded["birth_month"] = self._is_database_metrics_section_expanded("birth_month")
        self._create_analysis_chart_header(
            birth_month_section_layout,
            "Birth Month",
            "birth_month",
            "birth_month",
            dropdown_options=[
                ("Birth Month", "month_distribution"),
                ("Top Birth Dates", "top_birth_dates"),
            ],
            show_title=False,
        )
        birth_month_subheader = add_database_subheader("Birth month and recurring birth date patterns")
        birth_month_section_layout.addWidget(birth_month_subheader)
        (
            self.birth_month_chart_container,
            self.birth_month_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["birth_month"] = self.birth_month_chart_layout
        birth_month_section_layout.addWidget(self.birth_month_chart_container)

        #BIRTH PLACE SECTION
        birth_place_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Birthplace",
            section_key="birthplace",
            expanded=self._is_database_metrics_section_expanded("birthplace"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "birthplace",
                checked,
            ),
        )
        self._database_metrics_section_expanded["birthplace"] = self._is_database_metrics_section_expanded("birthplace")
        self._create_analysis_chart_header(
            birth_place_section_layout,
            "Birthplace",
            "birthplace",
            "birthplace",
            dropdown_options=[
                ("Most Common Birth Towns", "towns"),
                ("Most Common Countries", "countries"),
                ("Most Common US States", "us_states"),
            ],
            show_title=False,
        )
        birthplace_subheader = add_database_subheader("Birthplace distribution and recurring locations")
        birth_place_section_layout.addWidget(birthplace_subheader)
        (
            self.birthplace_chart_container,
            self.birthplace_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["birthplace"] = self.birthplace_chart_layout
        birth_place_section_layout.addWidget(self.birthplace_chart_container)

        # GENDER SECTION
        gender_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Gender",
            section_key="gender",
            expanded=self._is_database_metrics_section_expanded("gender"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "gender",
                checked,
            ),
        )
        self._database_metrics_section_expanded["gender"] = self._is_database_metrics_section_expanded("gender")
        self._create_analysis_chart_header(
            gender_section_layout,
            "Gender",
            "gender",
            "gender",
            dropdown_options=self._available_gender_dropdown_options(),
            show_title=False,
        )
        self.gender_subheader = add_database_subheader("Actual + guessed gender distribution")
        gender_section_layout.addWidget(self.gender_subheader)
        (
            self.gender_chart_container,
            self.gender_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["gender"] = self.gender_chart_layout
        gender_section_layout.addWidget(self.gender_chart_container)
        self.gender_unknown_note = add_database_subheader(
            f"*unknown for: {', '.join(GEN_POP_ACTUAL_GENDER_UNKNOWN_LABELS)}"
        )
        self.gender_unknown_note.setVisible(False)
        gender_section_layout.addWidget(self.gender_unknown_note)
        return panel

    def _build_todays_transits_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        panel.setLayout(layout)

        section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Transit View",
            expanded=True,
        )

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)

        self.transit_date_input = QDateEdit()
        self.transit_date_input.setDisplayFormat("yyyy-MM-dd")
        self.transit_date_input.setCalendarPopup(True)
        self.transit_date_input.setDateRange(
            QDate(EPHEMERIS_MIN_DATE.year, EPHEMERIS_MIN_DATE.month, EPHEMERIS_MIN_DATE.day),
            QDate(EPHEMERIS_MAX_DATE.year, EPHEMERIS_MAX_DATE.month, EPHEMERIS_MAX_DATE.day),
        )
        self.transit_date_input.setDate(QDate.currentDate())
        self.transit_date_input.dateChanged.connect(
            lambda _date: self._refresh_todays_transits_panel()
        )
        controls_layout.addWidget(self.transit_date_input)

        self.transit_time_input = QTimeEdit()
        self.transit_time_input.setDisplayFormat("HH:mm")
        self.transit_time_input.setTime(QTime.currentTime())
        self.transit_time_input.timeChanged.connect(
            lambda _time: self._refresh_todays_transits_panel()
        )
        controls_layout.addWidget(self.transit_time_input)

        section_layout.addLayout(controls_layout)

        location_layout = QHBoxLayout()
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setSpacing(6)

        self.transit_location_input = QLineEdit()
        self.transit_location_input.setPlaceholderText(
            "Location (city or lat,lon)"
        )
        self.transit_location_input.installEventFilter(self)
        location_layout.addWidget(self.transit_location_input, 1)

        self.transit_location_button = QPushButton("Set")
        self.transit_location_button.clicked.connect(
            self._on_transit_location_submitted
        )
        location_layout.addWidget(self.transit_location_button)

        section_layout.addLayout(location_layout)

        self.transit_location_label = QLabel("Location: 0.0, 0.0 (UTC)")
        self.transit_location_label.setStyleSheet(
            "font-size: 11px; color: #a5a5a5; padding: 0 2px 4px 2px;"
        )
        section_layout.addWidget(self.transit_location_label)

        personal_transit_controls_layout = QHBoxLayout()
        personal_transit_controls_layout.setContentsMargins(0, 0, 0, 0)
        personal_transit_controls_layout.setSpacing(6)

        self.personal_transit_chart_input = QLineEdit()
        self.personal_transit_chart_input.setPlaceholderText(
            "Enter chart name here!"
        )
        self.personal_transit_chart_input.returnPressed.connect(
            self._on_personal_transit_enter_pressed
        )
        personal_transit_controls_layout.addWidget(self.personal_transit_chart_input, 1)

        self.generate_personal_transit_button = QPushButton("Generate Personal Transit")
        self.generate_personal_transit_button.setStyleSheet(
            "QPushButton {"
            " background-color: #6f8f6f;"
            " color: #e9efe9;"
            " border: 1px solid #4f6850;"
            " border-radius: 4px;"
            " padding: 4px 10px;"
            "}"
            "QPushButton:hover { background-color: #789a77; }"
            "QPushButton:pressed { background-color: #5f7d5f; }"
        )
        self.generate_personal_transit_button.clicked.connect(
            self._on_generate_personal_transit
        )
        personal_transit_controls_layout.addWidget(self.generate_personal_transit_button)

        section_layout.addLayout(personal_transit_controls_layout)

        self.transit_use_time_checkbox = QCheckBox("Use exact time")
        self.transit_use_time_checkbox.setChecked(True)
        self.transit_use_time_checkbox.toggled.connect(
            self._on_transit_use_time_toggled
        )
        section_layout.addWidget(self.transit_use_time_checkbox)

        self._refresh_personal_transit_chart_options()

        self.todays_transits_updated_label = QLabel("")
        self.todays_transits_updated_label.setWordWrap(True)
        self.todays_transits_updated_label.setStyleSheet(
            "font-size: 11px; color: #a5a5a5; padding: 0 2px 4px 2px;"
        )
        section_layout.addWidget(self.todays_transits_updated_label)

        self.todays_transits_chart_container = QWidget()
        self.todays_transits_chart_layout = QVBoxLayout()
        self.todays_transits_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.todays_transits_chart_layout.setAlignment(Qt.AlignTop)
        self.todays_transits_chart_container.setLayout(self.todays_transits_chart_layout)
        section_layout.addWidget(self.todays_transits_chart_container)

        self.todays_transits_output = QPlainTextEdit()
        self.todays_transits_output.setReadOnly(True)
        output_font = self.todays_transits_output.font()
        output_font.setPointSize(9)
        self.todays_transits_output.setFont(output_font)
        self.todays_transits_output.setTabStopDistance(6)
        self.todays_transits_output._summary_highlighter = ChartSummaryHighlighter(
            self.todays_transits_output.document()
        )
        self.todays_transits_output.setPlaceholderText(
            "Transit chart summary will appear here."
        )
        self.todays_transits_output.setMinimumHeight(140)
        self.todays_transits_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        section_layout.addWidget(self.todays_transits_output, 1)

        refresh_button = QPushButton("Refresh Transit View")
        refresh_button.clicked.connect(self._refresh_todays_transits_panel)
        section_layout.addWidget(refresh_button)

        return panel


    def _apply_transit_location(self, *, show_errors: bool = True) -> None:
        raw_value = self.transit_location_input.text().strip()
        if not raw_value:
            self._refresh_todays_transits_panel()
            return

        parsed_lat = None
        parsed_lon = None
        if "," in raw_value:
            maybe_lat, maybe_lon = raw_value.split(",", 1)
            try:
                parsed_lat = float(maybe_lat.strip())
                parsed_lon = float(maybe_lon.strip())
            except ValueError:
                parsed_lat = None
                parsed_lon = None

        if parsed_lat is not None and parsed_lon is not None:
            if not (-90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0):
                if show_errors:
                    QMessageBox.warning(
                        self,
                        "Invalid coordinates",
                        "Latitude must be between -90 and 90, and longitude between -180 and 180.",
                    )
                return
            self._transit_lat = parsed_lat
            self._transit_lon = parsed_lon
            self._transit_location_label = f"{parsed_lat:.4f}, {parsed_lon:.4f}"
            self._transit_location_source = "manual"
            self._save_transit_location_preference(raw_value)
            self._refresh_todays_transits_panel()
            return

        try:
            lat, lon, resolved_label = geocode_location(raw_value)
        except LocationLookupError as error:
            if show_errors:
                QMessageBox.warning(
                    self,
                    "Location lookup failed",
                    f"Could not resolve location '{raw_value}'.\n{error}",
                )
            return

        self._transit_lat = float(lat)
        self._transit_lon = float(lon)
        self._transit_location_label = resolved_label
        self._transit_location_source = "manual"
        self._save_transit_location_preference(raw_value)
        self._refresh_todays_transits_panel()

    def _on_transit_location_submitted(self, *_args) -> None:
        self._apply_transit_location()

    def _initialize_transit_location_defaults(self) -> None:
        gps_location = self._resolve_gps_transit_location()
        if gps_location is not None:
            lat, lon = gps_location
            self._transit_lat = lat
            self._transit_lon = lon
            self._transit_location_label = "Current Location (GPS)"
            self._transit_location_source = "gps"
            return

        stored_location = self._settings.value("manage_charts/transit_last_location")
        if isinstance(stored_location, str) and stored_location.strip():
            self.transit_location_input.setText(stored_location.strip())
            self._apply_transit_location(show_errors=False)

    def _save_transit_location_preference(self, raw_location: str) -> None:
        self._settings.setValue("manage_charts/transit_last_location", raw_location.strip())

    def _resolve_gps_transit_location(self) -> tuple[float, float] | None:
        source = QGeoPositionInfoSource.createDefaultSource(self)
        if source is None:
            return None

        loop = QEventLoop(self)
        result: dict[str, float] = {}

        def _capture_position(info) -> None:
            if info.isValid():
                coordinate = info.coordinate()
                if coordinate.isValid():
                    result["lat"] = float(coordinate.latitude())
                    result["lon"] = float(coordinate.longitude())
            if loop.isRunning():
                loop.quit()

        def _stop_waiting(*_args) -> None:
            if loop.isRunning():
                loop.quit()

        source.positionUpdated.connect(_capture_position)
        source.errorOccurred.connect(_stop_waiting)
        source.startUpdates()

        timeout_timer = QTimer(self)
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(_stop_waiting)
        timeout_timer.start(2500)
        loop.exec()

        source.stopUpdates()
        timeout_timer.stop()

        if "lat" not in result or "lon" not in result:
            return None
        return result["lat"], result["lon"]

    def _refresh_todays_transits_panel(self) -> None:
        if not hasattr(self, "todays_transits_chart_layout"):
            return

        self._clear_layout(self.todays_transits_chart_layout)
        self._transit_chart_canvases.clear()
        local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        selected_date = self.transit_date_input.date()
        selected_time = self.transit_time_input.time()
        include_time = self.transit_use_time_checkbox.isChecked()
        if not include_time:
            selected_time = QTime(12, 0)
        selected_local = datetime.datetime(
            selected_date.year(),
            selected_date.month(),
            selected_date.day(),
            selected_time.hour(),
            selected_time.minute(),
            tzinfo=local_tz,
        )
        selected_utc = selected_local.astimezone(datetime.timezone.utc)
        chart = Chart(
            "Transit View",
            selected_utc,
            self._transit_lat,
            self._transit_lon,
            tz=datetime.timezone.utc,
        )
        chart.birthtime_unknown = not include_time
        chart.retcon_time_used = False

        figure = Figure(figsize=(3.8, 3.8))
        canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        draw_chart_wheel(
            figure,
            chart,
            canvas=canvas,
            wheel_padding=0.03,
            show_title=False,
            symbol_scale=0.7,
            wheel_scale=1.3,
        )
        canvas.draw_idle()
        canvas.setMinimumSize(230, 230)
        canvas.installEventFilter(self)
        self._transit_chart_canvases[canvas] = chart
        self.todays_transits_chart_layout.addWidget(canvas)

        summary = format_transit_chart_text(chart, self._transit_location_label)
        self.todays_transits_output.setPlainText(summary)

        local_now = selected_utc.astimezone(local_tz)
        source_hint = ""
        if self._transit_location_source == "gps":
            source_hint = " [GPS]"
        elif self._transit_location_source == "manual":
            source_hint = " [Saved]"
        self.transit_location_label.setText(
            f"Location: {self._transit_location_label}{source_hint} | Lat/Lon: {self._transit_lat:.4f}, {self._transit_lon:.4f}"
        )
        if include_time:
            selected_label = local_now.strftime('%Y-%m-%d %H:%M %Z')
            self.todays_transits_updated_label.setText(
                f"Selected local time: {selected_label}"
            )
        else:
            selected_label = local_now.strftime('%Y-%m-%d')
            self.todays_transits_updated_label.setText(
                f"Selected date (time omitted): {selected_label}"
            )

    def _refresh_personal_transit_chart_options(self) -> None:
        self._personal_transit_chart_lookup = {}
        choices: list[str] = []
        for row in list_charts():
            chart_id, name, alias, *_rest = row
            display_name = name.strip() if isinstance(name, str) and name.strip() else f"Chart {chart_id}"
            if alias:
                display_name = f"{display_name} ({alias})"
            key = f"{display_name}  [#{chart_id}]"
            self._personal_transit_chart_lookup[key] = int(chart_id)
            choices.append(key)

        completer = QCompleter(choices, self.personal_transit_chart_input)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.activated[str].connect(self._on_personal_transit_completer_activated)
        self.personal_transit_chart_input.setCompleter(completer)

    def _on_transit_use_time_toggled(self, use_time: bool) -> None:
        self.transit_time_input.setEnabled(use_time)
        self._refresh_todays_transits_panel()

    def _selected_transit_datetime_utc(self) -> tuple[datetime.datetime, bool]:
        local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        include_time = self.transit_use_time_checkbox.isChecked()
        selected_date = self.transit_date_input.date()
        selected_time = self.transit_time_input.time() if include_time else QTime(12, 0)
        selected_local = datetime.datetime(
            selected_date.year(),
            selected_date.month(),
            selected_date.day(),
            selected_time.hour(),
            selected_time.minute(),
            tzinfo=local_tz,
        )
        return selected_local.astimezone(datetime.timezone.utc), include_time

    def _resolve_personal_transit_chart_id(self) -> int | None:
        raw = self.personal_transit_chart_input.text().strip()
        if not raw:
            return None
        chart_id = self._personal_transit_chart_lookup.get(raw)
        if chart_id is not None:
            return chart_id
        for label, candidate_id in self._personal_transit_chart_lookup.items():
            if raw.lower() == label.lower():
                return candidate_id
        return None

    def _matching_personal_transit_labels(self, raw: str) -> list[str]:
        query = raw.strip().lower()
        labels = list(self._personal_transit_chart_lookup.keys())
        if not query:
            return labels
        return [label for label in labels if query in label.lower()]

    def _on_personal_transit_completer_activated(self, label: str) -> None:
        selected_label = label.strip()
        if not selected_label:
            return
        self.personal_transit_chart_input.setText(selected_label)
        self.personal_transit_chart_input.setCursorPosition(len(selected_label))
        self._on_generate_personal_transit()

    def _on_personal_transit_enter_pressed(self) -> None:
        raw = self.personal_transit_chart_input.text().strip()
        chart_id = self._resolve_personal_transit_chart_id()
        if chart_id is not None:
            self._on_generate_personal_transit()
            return

        matches = self._matching_personal_transit_labels(raw)
        if not matches:
            QMessageBox.warning(
                self,
                "Generate Personal Transit",
                "Select a saved chart from autocomplete before generating.",
            )
            return

        first_match = matches[0]
        self.personal_transit_chart_input.setText(first_match)
        self.personal_transit_chart_input.setCursorPosition(len(first_match))

        if len(matches) == 1:
            self._on_generate_personal_transit()

    def _on_generate_personal_transit(self) -> None:
        chart_id = self._resolve_personal_transit_chart_id()
        if chart_id is None:
            QMessageBox.warning(
                self,
                "Generate Personal Transit",
                "Select a saved chart from autocomplete before generating.",
            )
            return

        try:
            natal_chart = load_chart(chart_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Generate Personal Transit", str(exc))
            return

        transit_datetime_utc, include_time = self._selected_transit_datetime_utc()
        place_label = getattr(self, "_transit_location_label", "Unknown")
        timestamp_label = (
            transit_datetime_utc.strftime("%Y-%m-%d %H:%M UTC")
            if include_time
            else transit_datetime_utc.strftime("%Y-%m-%d")
        )
        personal_transit_name = (
            f"Personal Transit Chart for {natal_chart.name} on {timestamp_label} @ {place_label}"
        )
        transit_chart = Chart(
            personal_transit_name,
            transit_datetime_utc,
            self._transit_lat,
            self._transit_lon,
            tz=datetime.timezone.utc,
        )
        transit_chart.birthtime_unknown = not include_time
        transit_chart.retcon_time_used = False

        natal_normalized = normalize_chart(natal_chart, chart_id=chart_id, chart_type="natal")
        transit_normalized = normalize_chart(transit_chart, chart_type="transit")
        transit_in_natal = assign_houses(
            transit_normalized.bodies,
            natal_normalized.houses,
            layer="TRANSIT",
        )
        natal_targets = assign_houses(
            natal_normalized.bodies,
            natal_normalized.houses,
            layer="NATAL",
        )
        life_forecast_hits = compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
        )
        daily_vibe_hits = compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        )

        self._show_personal_transit_chart_popout(
            natal_chart,
            transit_chart,
            transit_in_natal,
            {
                PERSONAL_TRANSIT_MODE_LIFE_FORECAST: life_forecast_hits,
                PERSONAL_TRANSIT_MODE_DAILY_VIBE: daily_vibe_hits,
            },
            include_time=include_time,
        )

    def _on_generate_composite_chart(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if len(selected_items) != 2:
            chart_ids = self._prompt_composite_chart_selection()
            if chart_ids is None:
                return
            self._generate_composite_chart_for_ids(*chart_ids)
            return

        try:
            base_chart_id = int(selected_items[0].data(Qt.UserRole))
            overlay_chart_id = int(selected_items[1].data(Qt.UserRole))
        except (TypeError, ValueError):
            QMessageBox.warning(
                self,
                "Generate Composite Chart",
                "Could not determine chart IDs from the current selection.",
            )
            return

        self._generate_composite_chart_for_ids(base_chart_id, overlay_chart_id)

    def _prompt_composite_chart_selection(
        self,
        default_first_chart_id: int | None = None,
        focus_second_input: bool = False,
    ) -> tuple[int, int] | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Composite Chart")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        chart_lookup: dict[str, int] = {}
        labels: list[str] = []
        for row in list_charts():
            chart_id, name, alias, *_rest = row
            display_name = name.strip() if isinstance(name, str) and name.strip() else f"Chart {chart_id}"
            if alias:
                display_name = f"{display_name} ({alias})"
            label = f"{display_name}  [#{chart_id}]"
            labels.append(label)
            chart_lookup[label] = int(chart_id)

        first_chart_input = QLineEdit(dialog)
        first_chart_input.setPlaceholderText("Select first chart")
        first_completer = QCompleter(labels, first_chart_input)
        first_completer.setCaseSensitivity(Qt.CaseInsensitive)
        first_completer.setFilterMode(Qt.MatchContains)
        first_chart_input.setCompleter(first_completer)
        layout.addWidget(first_chart_input)

        divider = QFrame(dialog)
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)

        second_chart_input = QLineEdit(dialog)
        second_chart_input.setPlaceholderText("Select second chart")

        if default_first_chart_id is not None:
            for label, chart_id in chart_lookup.items():
                if chart_id == default_first_chart_id:
                    first_chart_input.setText(label)
                    break
        second_completer = QCompleter(labels, second_chart_input)
        second_completer.setCaseSensitivity(Qt.CaseInsensitive)
        second_completer.setFilterMode(Qt.MatchContains)
        second_chart_input.setCompleter(second_completer)
        layout.addWidget(second_chart_input)

        synastrize_button = QPushButton("Synastrize!", dialog)
        layout.addWidget(synastrize_button)

        selected_chart_ids: tuple[int, int] | None = None

        def _resolve_chart_id(raw_value: str) -> int | None:
            query = raw_value.strip()
            if not query:
                return None
            direct_match = chart_lookup.get(query)
            if direct_match is not None:
                return direct_match
            for label, chart_id in chart_lookup.items():
                if query.lower() == label.lower():
                    return chart_id
            return None

        def _submit() -> None:
            nonlocal selected_chart_ids
            base_chart_id = _resolve_chart_id(first_chart_input.text())
            overlay_chart_id = _resolve_chart_id(second_chart_input.text())
            if base_chart_id is None or overlay_chart_id is None:
                QMessageBox.warning(
                    dialog,
                    "Generate Composite Chart",
                    "Select two saved charts from autocomplete before generating.",
                )
                return
            if base_chart_id == overlay_chart_id:
                QMessageBox.warning(
                    dialog,
                    "Generate Composite Chart",
                    "Select two different charts.",
                )
                return
            selected_chart_ids = (base_chart_id, overlay_chart_id)
            dialog.accept()

        synastrize_button.clicked.connect(_submit)
        first_chart_input.returnPressed.connect(_submit)
        second_chart_input.returnPressed.connect(_submit)

        if focus_second_input:
            QTimer.singleShot(0, second_chart_input.setFocus)
            QTimer.singleShot(0, second_chart_input.selectAll)

        if dialog.exec() != QDialog.Accepted:
            return None
        return selected_chart_ids

    def _generate_composite_chart_for_ids(self, base_chart_id: int, overlay_chart_id: int) -> None:
        try:
            base_chart = load_chart(base_chart_id)
            overlay_chart = load_chart(overlay_chart_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Generate Composite Chart", str(exc))
            return

        base_normalized = normalize_chart(
            base_chart,
            chart_id=base_chart_id,
            chart_type="natal",
        )
        overlay_normalized = normalize_chart(
            overlay_chart,
            chart_id=overlay_chart_id,
            chart_type="natal",
        )
        overlay_in_base = assign_houses(
            overlay_normalized.bodies,
            base_normalized.houses,
            layer="OVERLAY",
        )
        base_targets = assign_houses(
            base_normalized.bodies,
            base_normalized.houses,
            layer="BASE",
        )
        aspect_hits = compute_aspects(
            overlay_in_base.values(),
            base_targets.values(),
            TRANSIT_ASPECT_RULES,
        )

        self._show_composite_chart_popout(
            base_chart,
            overlay_chart,
            overlay_in_base,
            aspect_hits,
        )

    def _show_composite_chart_popout(
        self,
        base_chart: Chart,
        overlay_chart: Chart,
        overlay_positions_in_base_houses: dict[str, Any],
        aspect_hits: list[Any],
    ) -> None:
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle(
            f"Composite Chart: {base_chart.name} + {overlay_chart.name}"
        )
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)

        normalized_overlay_weights = _normalize_planet_weight_map(
            getattr(overlay_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(overlay_chart)
        )
        normalized_base_weights = _normalize_planet_weight_map(
            getattr(base_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(base_chart)
        )

        def _weighted_synastry_score(hit: Any) -> float:
            if not hasattr(hit, "a") or not hasattr(hit, "b"):
                return 0.0
            return max(
                0.0,
                _synastry_pair_weight(
                    hit.a.name,
                    hit.b.name,
                    normalized_overlay_weights,
                    normalized_base_weights,
                )
                * float(getattr(hit, "weight", 0.0))
                * float(getattr(hit, "exactness", 0.0)),
            )

        chart_info_output = self._build_popout_left_panel(
            layout,
            chart_info_placeholder="Composite view: first selected chart houses with second selected chart overlay.",
            aspect_entries=list(aspect_hits),
            export_file_stem=(
                f"{_sanitize_export_token(base_chart.name)}_x_{_sanitize_export_token(overlay_chart.name)}"
                "-synastry_aspect_distribution"
            ),
            weighted_score_for_entry=_weighted_synastry_score,
            aspect_subheader=(
                "Disclaimer: The creator of this app hasn't found Synastry aspect weighing to be useful or relevant. "
                "It predicts harmony with all my worst enemies, success in relationships that failed and strife in "
                "relationships that have gone well for a very long time. It may be that the objective innate "
                "goodness or awfulness of some people is far more critical in determining relationship outcomes "
                "than baseline 'compatibility'. Maybe there's a big difference in conflict based on being 'wired "
                "different' vs conflict based on differing levels of emotional maturity or sociopathy. lol But I "
                "suspect my algorithm is also wrong."
            ),
            show_aspect_distribution=self._visibility.get("popout.synastry_aspect_weights"),
        )

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout, 3)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        header_left = QLabel(
            "\n".join(
                [
                    f"Chart 1:    {base_chart.name}",
                    format_chart_header("when_where_compact", date_time=base_chart.dt.strftime("%m.%d.%Y %H:%M"), lat=base_chart.lat, lon=base_chart.lon),
                    "",
                    f"Chart 2: {overlay_chart.name}",
                    format_chart_header("when_where_compact", date_time=overlay_chart.dt.strftime("%m.%d.%Y %H:%M"), lat=overlay_chart.lat, lon=overlay_chart.lon),
                ]
            )
        )
        header_left.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        header_font = header_left.font()
        header_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        header_left.setFont(header_font)
        header_layout.addWidget(header_left, 0, Qt.AlignLeft | Qt.AlignTop)
        header_layout.addStretch(1)
        right_layout.addLayout(header_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        overlay_positions = {
            name: body.lon_deg
            for name, body in overlay_positions_in_base_houses.items()
            if name not in {"AS", "MC", "DS", "IC"}
        }
        base_for_plot = copy.deepcopy(base_chart)
        base_for_plot.name = f"{base_chart.name} + {overlay_chart.name}"
        base_for_plot.aspects = []
        overlay_aspects = _overlay_aspect_segments(aspect_hits)
        draw_chart_wheel(
            figure,
            base_for_plot,
            canvas=canvas,
            overlay_positions=overlay_positions,
            overlay_aspects=overlay_aspects,
            overlay_aspects_only=True,
            overlay_color="#b54a4a",
            overlay_sign_color="#de8a8a",
            base_monochrome_color="#4f72b8",
            wheel_padding=0.03,
            show_title=False,
            symbol_scale=0.7,
        )
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.draw_idle()
        right_layout.addWidget(canvas, 7)

        summary_controls = QHBoxLayout()
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        right_layout.addLayout(summary_controls)

        summary_output = QPlainTextEdit()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        summary_output._summary_highlighter = ChartSummaryHighlighter(summary_output.document())
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self)
        right_layout.addWidget(summary_output, 3)

        synastry_file_stem = (
            f"synastry_{self._sanitize_export_token(base_chart.name)}_x_{self._sanitize_export_token(overlay_chart.name)}"
        )
        summary_share_button = self._attach_popout_share_button(summary_output, synastry_file_stem)

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
            "share_button": summary_share_button,
        }
        self._popout_summary_contexts[popout_context_key] = popout_context
        dialog.destroyed.connect(lambda _=None, key=popout_context_key: self._popout_summary_contexts.pop(key, None))

        base_dominant_planet_weights = getattr(base_chart, "dominant_planet_weights", None)
        if not base_dominant_planet_weights:
            base_dominant_planet_weights = _calculate_dominant_planet_weights(base_chart)
        overlay_dominant_planet_weights = getattr(overlay_chart, "dominant_planet_weights", None)
        if not overlay_dominant_planet_weights:
            overlay_dominant_planet_weights = _calculate_dominant_planet_weights(overlay_chart)

        summary_header_lines = [
            f"Synastry Chart for {base_chart.name} & {overlay_chart.name}",
            "-----------------------------------",
            "",
            f"{overlay_chart.name}'s Aspects to {base_chart.name}:",
        ]

        def _refresh_summary() -> None:
            sort_mode = summary_sort_combo.currentText()
            lines = list(summary_header_lines)
            aspect_info_map: dict[int, dict[str, object]] = {}
            sorted_hits = self._sort_popout_aspects(
                aspect_hits,
                sort_mode,
                synastry_overlay_planet_weights=overlay_dominant_planet_weights,
                synastry_base_planet_weights=base_dominant_planet_weights,
            )
            if sorted_hits:
                for hit in sorted_hits: #for hit in sorted_hits[:80]: #<- this had previously been truncated
                    left_label = _format_popout_aspect_endpoint(hit.a, include_house=False)
                    right_label = _format_popout_aspect_endpoint(hit.b, include_house=True)
                    line = (
                        f"- {left_label:<26} {hit.aspect:<14} {right_label:<30} "
                        f"orb {_format_degree_minutes(hit.orb_deg, include_sign=False)} ⓘ"
                    )
                    aspect_type = str(hit.aspect).replace(" ", "_").lower()
                    angle = float(ASPECT_DEFS.get(aspect_type, {}).get("angle", 0.0))
                    aspect_info_map[len(lines)] = {
                        "p1": hit.a.name,
                        "p2": hit.b.name,
                        "type": str(hit.aspect),
                        "angle": angle,
                        "delta": float(hit.orb_deg),
                        "sign1": hit.a.sign,
                        "sign2": hit.b.sign,
                        "house1": hit.a.house,
                        "house2": hit.b.house,
                    }
                    lines.append(line)
            else:
                lines.append("- None within configured orbs.")
            summary_output.setPlainText("\n".join(lines))
            popout_context["aspect_info_map"] = aspect_info_map

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        _refresh_summary()

        dialog.resize(1320, 1080)
        self._register_popout_shortcuts(dialog)
        dialog.show()
        self._transit_popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._transit_popout_dialogs.remove(dialog)
            if dialog in self._transit_popout_dialogs
            else None
        )

    def _normalize_aspect_type(self, raw_aspect: Any) -> str:
        return _normalize_aspect_type(raw_aspect)

    def _extract_aspect_weight(self, aspect_entry: Any) -> float:
        return _extract_aspect_weight(aspect_entry)

    def _collect_aspect_type_counts(
        self,
        aspect_entries: list[Any],
        *,
        weighted: bool = False,
        weighted_score_for_entry: Callable[[Any], float] | None = None,
    ) -> OrderedDict[str, float]:
        return _collect_aspect_type_counts(
            aspect_entries,
            weighted=weighted,
            weighted_score_for_entry=weighted_score_for_entry,
        )

    def _collect_aspect_category_totals(
        self,
        aspect_counts: OrderedDict[str, float],
        *,
        categories: dict[str, dict[str, Any]],
    ) -> OrderedDict[str, float]:
        return _collect_aspect_category_totals(aspect_counts, categories=categories)

    def _draw_popout_aspect_distribution_chart(
        self,
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

    def _build_popout_left_panel(
        self,
        layout: QHBoxLayout,
        *,
        chart_info_placeholder: str,
        aspect_entries: list[Any],
        export_file_stem: str,
        weighted_score_for_entry: Callable[[Any], float] | None = None,
        aspect_subheader: str | None = None,
        show_aspect_distribution: bool = True,
        awareness_stream_entries: list[dict[str, Any]] | None = None,
    ) -> QPlainTextEdit:
        return _build_popout_left_panel_widget(
            layout,
            chart_info_placeholder=chart_info_placeholder,
            aspect_entries=aspect_entries,
            export_file_stem=export_file_stem,
            weighted_score_for_entry=weighted_score_for_entry,
            aspect_subheader=aspect_subheader,
            parent=self,
            chart_summary_highlighter_cls=ChartSummaryHighlighter,
            export_aspect_distribution_csv_dialog=_export_aspect_distribution_csv_dialog,
            get_share_icon_path=_get_share_icon_path,
            chart_data_info_label_style=CHART_DATA_INFO_LABEL_STYLE,
            database_analytics_dropdown_style=DATABASE_ANALYTICS_DROPDOWN_STYLE,
            chart_theme_colors=CHART_THEME_COLORS,
            show_aspect_distribution=show_aspect_distribution,
            awareness_stream_entries=awareness_stream_entries,
        )

    def _sort_popout_aspects(
        self,
        aspect_hits: list[Any],
        sort_mode: str,
        *,
        synastry_overlay_planet_weights: dict[str, float] | None = None,
        synastry_base_planet_weights: dict[str, float] | None = None,
    ) -> list[Any]:
        if sort_mode == "Aspect":
            return sorted(
                aspect_hits,
                key=lambda hit: (hit.aspect.replace("_", " ").title(), hit.a.name, hit.b.name, hit.orb_deg),
            )
        if sort_mode == "Position":
            return sorted(
                aspect_hits,
                key=lambda hit: (_aspect_pair_weight(hit.a.name, hit.b.name), -hit.exactness, -hit.weight),
                reverse=True,
            )
        if sort_mode == "Duration":
            return sorted(
                aspect_hits,
                key=lambda hit: (aspect_body_sign_duration(hit.a.name), hit.exactness, hit.weight, -hit.orb_deg),
                reverse=True,
            )
        if synastry_overlay_planet_weights is not None and synastry_base_planet_weights is not None:
            normalized_overlay_weights = _normalize_planet_weight_map(synastry_overlay_planet_weights)
            normalized_base_weights = _normalize_planet_weight_map(synastry_base_planet_weights)
            return sorted(
                aspect_hits,
                key=lambda hit: (
                    _synastry_pair_weight(
                        hit.a.name,
                        hit.b.name,
                        normalized_overlay_weights,
                        normalized_base_weights,
                    ) * float(hit.weight) * float(hit.exactness),
                    float(hit.exactness),
                    -float(hit.orb_deg),
                ),
                reverse=True,
            )
        return sorted(
            aspect_hits,
            key=lambda hit: (hit.exactness, hit.weight, -hit.orb_deg),
            reverse=True,
        )

    def _sanitize_export_token(self, value: str, fallback: str = "chart") -> str:
        return _sanitize_export_token(value, fallback)

    def _build_transit_export_file_stem(
        self,
        transit_chart: Chart,
        *,
        chart_name_for_personal_transit: str | None = None,
    ) -> str:
        transit_timestamp = (
            transit_chart.dt.strftime("%Y-%m-%d_%H%M")
            if transit_chart.dt
            else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%H%M")
        )
        default_stem = f"transit_{transit_timestamp}"
        return f"{default_stem}_{self._sanitize_export_token(chart_name_for_personal_transit)}"
        # return default_stem

    def _position_popout_share_button(self, output_widget: QPlainTextEdit, button: QToolButton) -> None:
        viewport = output_widget.viewport()
        margin = 6
        button.move(
            max(margin, viewport.x() + viewport.width() - button.width() - margin),
            max(margin, viewport.y() + margin),
        )
        button.raise_()
        button.show()

    def _attach_popout_share_button(
        self,
        output_widget: QPlainTextEdit,
        default_file_stem: str,
        export_text_provider: Callable[[], str] | None = None,
    ) -> QToolButton:
        share_button = QToolButton(output_widget)
        share_icon_path = _get_share_icon_path()
        if share_icon_path:
            share_button.setIcon(QIcon(share_icon_path))
            share_button.setIconSize(QSize(14, 14))
        else:
            share_button.setText("↗")
        share_button.setAutoRaise(True)
        share_button.setCursor(Qt.PointingHandCursor)
        share_button.setToolTip("Export chart data output as Markdown or text")
        share_button.clicked.connect(
            lambda _checked=False, widget=output_widget, stem=default_file_stem: self._export_popout_chart_data_output(widget, stem)
        )
        share_button.resize(22, 22)
        self._position_popout_share_button(output_widget, share_button)
        return share_button

    def _export_popout_chart_data_output(
        self,
        output_widget: QPlainTextEdit,
        default_file_stem: str,
        export_text_provider: Callable[[], str] | None = None,
    ) -> None:
        if callable(export_text_provider):
            summary_text = export_text_provider().strip()
        else:
            summary_text = output_widget.toPlainText().strip()
        if not summary_text:
            QMessageBox.information(
                self,
                "Nothing to export",
                "Generate or load a chart before exporting chart data output.",
            )
            return

        safe_stem = self._sanitize_export_token(default_file_stem, fallback="chart_data_output")
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Chart Data Output",
            f"{safe_stem}.md",
            "Markdown Files (*.md);;Text Files (*.txt)",
        )
        if not file_path:
            return

        selected_extension = ".txt" if "*.txt" in selected_filter else ".md"
        if not file_path.lower().endswith((".md", ".txt")):
            file_path = f"{file_path}{selected_extension}"

        try:
            with open(file_path, "w", encoding="utf-8") as output_file:
                output_file.write(summary_text)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export chart data output:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved chart data output to:\n{file_path}",
        )

    def _personal_transit_priority(
        self,
        hit: Any,
        mode: str,
        natal_planet_weights: dict[str, float] | None = None,
    ) -> float:
        orb_cap = personal_transit_orb_cap(mode, hit.a.name, hit.b.name, hit.aspect)
        if orb_cap <= 0:
            return 0.0
        orb_factor = max(0.0, 1.0 - (float(hit.orb_deg) / orb_cap))
        aspect_key = str(hit.aspect).replace(" ", "_").lower()
        aspect_angle = float(ASPECT_DEFS.get(aspect_key, {}).get("angle", 0.0))
        transit_weight = float(TRANSIT_WEIGHT.get(hit.a.name, 1.0))
        if natal_planet_weights:
            natal_weight = float(natal_planet_weights.get(hit.b.name, NATAL_WEIGHT.get(hit.b.name, 1.0)))
        else:
            natal_weight = float(NATAL_WEIGHT.get(hit.b.name, 1.0))
        angle_weight = float(ANGLE_WEIGHT.get(aspect_angle, 1.0))
        return (transit_weight + natal_weight) * angle_weight * orb_factor

    def _sort_personal_transit_mode_aspects(
        self,
        aspect_hits: list[Any],
        sort_mode: str,
        mode: str,
        natal_planet_weights: dict[str, float] | None = None,
    ) -> list[Any]:
        if sort_mode == "Priority":
            return sorted(
                aspect_hits,
                key=lambda hit: self._personal_transit_priority(
                    hit,
                    mode,
                    natal_planet_weights=natal_planet_weights,
                ),
                reverse=True,
            )
        return self._sort_popout_aspects(aspect_hits, sort_mode)

    def _show_personal_transit_chart_popout(
        self,
        natal_chart: Chart,
        transit_chart: Chart,
        transit_positions_in_natal_houses: dict[str, Any],
        aspect_hits_by_mode: dict[str, list[Any]],
                *,
        include_time: bool,
    ) -> None:
        dialog = ManagedTransitPopoutDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle(transit_chart.name)
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)

        all_hits = list(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_LIFE_FORECAST, []))
        all_hits.extend(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_DAILY_VIBE, []))
        hit_modes: dict[int, str] = {}
        for mode_name, mode_hits in aspect_hits_by_mode.items():
            for hit in mode_hits:
                hit_modes[id(hit)] = mode_name
        natal_planet_weights = getattr(natal_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(natal_chart)

        def _weighted_personal_transit_score(hit: Any) -> float:
            mode_name = hit_modes.get(id(hit), PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
            return max(
                0.0,
                self._personal_transit_priority(
                    hit,
                    mode_name,
                    natal_planet_weights=natal_planet_weights,
                ),
            )

        chart_info_output = self._build_popout_left_panel(
            layout,
            chart_info_placeholder="Personal Transit Chart: natal houses with transit planet overlay.",
            aspect_entries=all_hits,
            export_file_stem=f"{_sanitize_export_token(natal_chart.name)}-transit_aspect_distribution",
            weighted_score_for_entry=_weighted_personal_transit_score,
        )

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout, 3)

        location_label = getattr(self, "_transit_location_label", None) or "Unknown"
        local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        transit_dt_local = transit_chart.dt.astimezone(local_tz)
        date_label = transit_dt_local.strftime("%m.%d.%Y")
        time_label = transit_dt_local.strftime("%H:%M") if include_time else "omitted"
        timezone_label = transit_dt_local.strftime("%Z") or str(local_tz)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        header_left = QLabel(
            "\n".join(
                [
                    f"Name: {natal_chart.name}",
                    format_chart_header("when_where", date=date_label, time=time_label, timezone=timezone_label, location=location_label, lat=transit_chart.lat, lon=transit_chart.lon),
                ]
            )
        )
        header_left.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        header_font = header_left.font()
        header_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        header_left.setFont(header_font)
        header_layout.addWidget(header_left, 0, Qt.AlignLeft | Qt.AlignTop)
        header_layout.addStretch(1)

        export_button = QPushButton("Export Chart")
        export_button.clicked.connect(lambda _checked=False, export_chart=natal_chart: self._export_chart(export_chart))
        header_layout.addWidget(export_button, 0, Qt.AlignTop | Qt.AlignRight)
        right_layout.addLayout(header_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        overlay_positions = {
            name: body.lon_deg
            for name, body in transit_positions_in_natal_houses.items()
            if name not in {"AS", "MC", "DS", "IC"}
        }
        natal_for_plot = copy.deepcopy(natal_chart)
        natal_for_plot.name = transit_chart.name
        natal_for_plot.aspects = []
        overlay_aspects = _overlay_aspect_segments(all_hits)
        draw_chart_wheel(
            figure,
            natal_for_plot,
            canvas=canvas,
            overlay_positions=overlay_positions,
            overlay_aspects=overlay_aspects,
            overlay_aspects_only=True,
            overlay_color="#b54a4a",
            overlay_sign_color="#de8a8a",
            base_monochrome_color="#4f72b8",
            wheel_padding=0.03,
            show_title=False,
            symbol_scale=0.7,
        )
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.draw_idle()
        right_layout.addWidget(canvas, 7)

        summary_controls = QHBoxLayout()
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        right_layout.addLayout(summary_controls)

        summary_output = QPlainTextEdit()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        summary_output._summary_highlighter = ChartSummaryHighlighter(summary_output.document())
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self)
        right_layout.addWidget(summary_output, 3)

        transit_timestamp = transit_chart.dt.strftime("%Y-%m-%d_%H%M") if transit_chart.dt else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%H%M")
        transit_file_stem = self._build_transit_export_file_stem(
            transit_chart,
            chart_name_for_personal_transit=natal_chart.name,
        )
        summary_share_button = self._attach_popout_share_button(
            summary_output,
            transit_file_stem,
            export_text_provider=lambda: _build_personal_transit_export_text(),
        )

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
            "share_button": summary_share_button,
        }
        self._popout_summary_contexts[popout_context_key] = popout_context

        summary_header_lines = [
            "Personal Transit (Transit → Natal)",
            "---------------------------------",
            f"Name:      {natal_chart.name}",
            format_chart_header("when_where", date=date_label, time=time_label, timezone=timezone_label, location=location_label, lat=transit_chart.lat, lon=transit_chart.lon),
            "",
        ]
        transit_location = (transit_chart.lat, transit_chart.lon)
        transit_ranges: dict[tuple[str, str, str, str], dict[str, object]] = {}
        transit_workers: dict[tuple[str, str, str, str], tuple[QThread, TransitAspectWindowWorker]] = {}
        calendar_info_map: dict[int, dict[str, object]] = {}
        mode_labels = {
            PERSONAL_TRANSIT_MODE_LIFE_FORECAST: "Life Forecast",
            PERSONAL_TRANSIT_MODE_DAILY_VIBE: "Daily Vibe",
        }
        mode_rules = {
            PERSONAL_TRANSIT_MODE_LIFE_FORECAST: personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
            PERSONAL_TRANSIT_MODE_DAILY_VIBE: personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        }
        transit_scan_config = resolve_transit_window_scan_config()
        scan_step_hours = transit_scan_config.scan_step_hours
        scan_precision_minutes = transit_scan_config.scan_precision_minutes
        include_time = transit_scan_config.include_time
        natal_planet_weights = getattr(natal_chart, "dominant_planet_weights", None)
        if not natal_planet_weights:
            natal_planet_weights = _calculate_dominant_planet_weights(natal_chart)

        def _build_personal_transit_sections(sort_mode: str) -> list[tuple[str, str, list[tuple[Any, str]], str]]:
            daily_hits, rollover_hits = split_daily_vibe_hits_by_expected_duration(
                aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_DAILY_VIBE, [])
            )
            return [
                (
                    "Daily Vibe",
                    "(Short-term 1-3 day personal transits)",
                    [
                        (hit, PERSONAL_TRANSIT_MODE_DAILY_VIBE)
                        for hit in self._sort_personal_transit_mode_aspects(
                            daily_hits,
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ],
                    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                ),
                (
                    "Life Forecast",
                    "(Longer-term and structural transits)",
                    [
                        (hit, PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
                        for hit in self._sort_personal_transit_mode_aspects(
                            aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_LIFE_FORECAST, []),
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ]
                    + [
                        (hit, PERSONAL_TRANSIT_MODE_DAILY_VIBE)
                        for hit in self._sort_personal_transit_mode_aspects(
                            rollover_hits,
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ],
                    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
                ),
            ]

            #ojo: is this weird?
        def _window_cache_key(mode: str, hit_obj: Any) -> tuple[object, ...]:
            chart_dt = transit_chart.dt
            chart_dt_utc = chart_dt.astimezone(datetime.timezone.utc) if chart_dt.tzinfo else chart_dt.replace(tzinfo=datetime.timezone.utc)
            rules = mode_rules.get(mode, TRANSIT_ASPECT_RULES)
            return (
                mode,
                hit_obj.a.name,
                hit_obj.aspect,
                hit_obj.b.name,
                chart_dt_utc.isoformat(),
                round(float(transit_location[0]), 4),
                round(float(transit_location[1]), 4),
                tuple((asp.name, float(asp.angle_deg), float(asp.orb_deg)) for asp in rules.aspect_types),
                float(scan_step_hours),
                float(scan_precision_minutes),
            )

        def _window_cache_get(cache_key: tuple[object, ...]) -> dict[str, object] | None:
            cached = self._transit_window_result_cache.get(cache_key)
            if cached is None:
                return None
            self._transit_window_result_cache.move_to_end(cache_key)
            return dict(cached)

        def _window_cache_put(cache_key: tuple[object, ...], payload: dict[str, object]) -> None:
            self._transit_window_result_cache[cache_key] = dict(payload)
            self._transit_window_result_cache.move_to_end(cache_key)
            while len(self._transit_window_result_cache) > TRANSIT_WINDOW_CACHE_LIMIT:
                self._transit_window_result_cache.popitem(last=False)

        #ojo: changes here feel risky...
        def _begin_transit_worker_shutdown(on_complete: Callable[[], None]) -> None:
            for _worker_key, (thread, _worker) in list(transit_workers.items()):
                try:
                    thread.requestInterruption()
                    thread.quit()
                except RuntimeError:
                    continue
            transit_workers.clear()
            on_complete()

        dialog.destroyed.connect(lambda _=None, key=popout_context_key: self._popout_summary_contexts.pop(key, None))
        dialog.set_async_shutdown(_begin_transit_worker_shutdown)

        def _refresh_summary() -> None:
            vertical_scrollbar = summary_output.verticalScrollBar()
            horizontal_scrollbar = summary_output.horizontalScrollBar()
            previous_vertical_position = vertical_scrollbar.value()
            previous_horizontal_position = horizontal_scrollbar.value()
            sort_mode = summary_sort_combo.currentText()
            lines = list(summary_header_lines)
            aspect_info_map: dict[int, dict[str, object]] = {}
            calendar_info_map.clear()
            sections = _build_personal_transit_sections(sort_mode)
            for _section_title, _section_subtitle, entries, empty_mode in sections:
                lines.extend([_section_title, _section_subtitle, ""])
                if entries:
                    for hit, source_mode in entries[:80]:
                        key = (source_mode, hit.a.name, hit.aspect, hit.b.name)
                        state = transit_ranges.setdefault(
                            key,
                            {
                                "expanded": False,
                                "resolving": False,
                                "resolved": False,
                                "failed": False,
                                "start": None,
                                "end": None,
                                "start_truncated_to_scope": False,
                                "end_truncated_to_scope": False,
                                "error": "",
                                "hit": hit,
                                "cache_key": _window_cache_key(source_mode, hit),
                                "mode": source_mode,
                            },
                        )
                        state["hit"] = hit
                        state["cache_key"] = _window_cache_key(source_mode, hit)
                        state["mode"] = source_mode
                        suffix = "📆"
                        if state["resolving"]:
                            suffix = "📆 …"
                        elif state["failed"]:
                            error_text = state.get("error", "")
                            suffix = f"📆 ⚠ {error_text}" if error_text else "📆 ⚠"
                        elif state["expanded"] and state["resolved"]:
                            suffix = _format_transit_range(
                                state["start"],
                                state["end"],
                                include_time=include_time,
                                start_truncated_to_scope=bool(state.get("start_truncated_to_scope", False)),
                                end_truncated_to_scope=bool(state.get("end_truncated_to_scope", False)),
                            )
                        left_label = _format_popout_aspect_endpoint(hit.a, include_house=False)
                        right_label = _format_popout_aspect_endpoint(hit.b, include_house=True)
                        line = (
                            f"- {left_label:<26} {hit.aspect:<14} {right_label:<30} "
                            f"orb {_format_degree_minutes(hit.orb_deg, include_sign=False):<8}  ⓘ {suffix}"
                        )
                        aspect_type = str(hit.aspect).replace(" ", "_").lower()
                        angle = float(ASPECT_DEFS.get(aspect_type, {}).get("angle", 0.0))
                        aspect_info_map[len(lines)] = {
                            "p1": hit.a.name,
                            "p2": hit.b.name,
                            "type": str(hit.aspect),
                            "angle": angle,
                            "delta": float(hit.orb_deg),
                            "sign1": hit.a.sign,
                            "sign2": hit.b.sign,
                            "house1": hit.a.house,
                            "house2": hit.b.house,
                        }
                        icon_index = line.rfind("📆")
                        if icon_index >= 0:
                            calendar_info_map[len(lines)] = {
                                "key": key,
                                "icon_index": icon_index,
                            }
                        lines.append(line)
                else:
                    lines.append(f"- No {mode_labels.get(empty_mode, empty_mode)} aspects within configured orbs.")
                lines.append("")
            summary_output.setPlainText("\n".join(lines))
            popout_context["aspect_info_map"] = aspect_info_map
            vertical_scrollbar.setValue(min(previous_vertical_position, vertical_scrollbar.maximum()))
            horizontal_scrollbar.setValue(min(previous_horizontal_position, horizontal_scrollbar.maximum()))
        def _on_window_ready(key: tuple[str, str, str, str], start_dt: object, end_dt: object, metadata: object) -> None:
            worker_entry = transit_workers.pop(key, None)
            if worker_entry is not None:
                thread, worker = worker_entry
                try:
                    thread.quit()
                except RuntimeError:
                    pass
                thread.deleteLater()
                worker.deleteLater()
            state = transit_ranges.get(key)
            if state is None:
                return
            cache_key = state.get("cache_key")
            state["resolved"] = True
            state["resolving"] = False
            state["failed"] = False
            state["expanded"] = True
            state["start"] = start_dt
            state["end"] = end_dt
            if isinstance(metadata, dict):
                state["start_truncated_to_scope"] = bool(metadata.get("start_truncated_to_scope", False))
                state["end_truncated_to_scope"] = bool(metadata.get("end_truncated_to_scope", False))
            else:
                state["start_truncated_to_scope"] = False
                state["end_truncated_to_scope"] = False

            if isinstance(cache_key, tuple):
                _window_cache_put(cache_key, {"resolved": True, "failed": False, "start": start_dt, "end": end_dt, "start_truncated_to_scope": bool(state["start_truncated_to_scope"]), "end_truncated_to_scope": bool(state["end_truncated_to_scope"]), "error": ""})
            _refresh_summary()
            _drain_preload_queue()

        def _on_window_failed(key: tuple[str, str, str, str], error_text: str) -> None:
            worker_entry = transit_workers.pop(key, None)
            if worker_entry is not None:
                thread, worker = worker_entry
                try:
                    thread.quit()
                except RuntimeError:
                    pass
                thread.deleteLater()
                worker.deleteLater()
            state = transit_ranges.get(key)
            if state is None:
                return
            cache_key = state.get("cache_key")
            state["resolved"] = False
            state["resolving"] = False
            state["start_truncated_to_scope"] = False
            state["end_truncated_to_scope"] = False
            state["failed"] = error_text != "Cancelled"
            state["error"] = "" if error_text == "Cancelled" else error_text

            if error_text != "Cancelled" and isinstance(cache_key, tuple):
                _window_cache_put(cache_key, {"resolved": False, "failed": True, "start": None, "end": None, "start_truncated_to_scope": False, "end_truncated_to_scope": False, "error": error_text})
            _refresh_summary()
            _drain_preload_queue()

        MAX_TRANSIT_WINDOW_WORKERS = 2
        preload_queue: list[tuple[str, str, str, str]] = []

        def _start_window_worker(key: tuple[str, str, str, str], state: dict[str, object], *, refresh: bool) -> None:
            hit = state.get("hit")
            mode = str(state.get("mode", PERSONAL_TRANSIT_MODE_LIFE_FORECAST))
            if hit is None:
                return

            state["resolving"] = True
            state["failed"] = False
            state["error"] = ""
            state["start_truncated_to_scope"] = False
            state["end_truncated_to_scope"] = False
            if refresh:
                _refresh_summary()

            thread = QThread(dialog)
            worker = TransitAspectWindowWorker(
                natal_chart,
                transit_chart.dt,
                transit_location,
                hit,
                mode_rules.get(mode, TRANSIT_ASPECT_RULES),
                step_hours=scan_step_hours,
                precision_minutes=scan_precision_minutes,
            )
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(
                lambda a, b, c, start_dt, end_dt, metadata, mode=mode: _on_window_ready(
                    (mode, a, b, c),
                    start_dt,
                    end_dt,
                    metadata,
                )
            )
            worker.failed.connect(
                lambda a, b, c, error_text, mode=mode: _on_window_failed((mode, a, b, c), error_text)
            )
            transit_workers[key] = (thread, worker)
            thread.start()

        def _drain_preload_queue() -> None:
            while preload_queue and len(transit_workers) < MAX_TRANSIT_WINDOW_WORKERS:
                queue_key = preload_queue.pop(0)
                state = transit_ranges.get(queue_key)
                if state is None:
                    continue
                if state.get("resolved") or state.get("resolving") or state.get("failed"):
                    continue
                _start_window_worker(queue_key, state, refresh=False)
            if not transit_workers:
                _refresh_summary()

        def _ensure_window_async(key: tuple[str, str, str, str], state: dict[str, object]) -> None:
            if state["resolved"]:
                state["expanded"] = True
                _refresh_summary()
                return
            if state["resolving"]:
                return
            hit = state.get("hit")
            mode = str(state.get("mode", PERSONAL_TRANSIT_MODE_LIFE_FORECAST))
            if hit is None:
                return
            cache_key = state.get("cache_key")
            if isinstance(cache_key, tuple):
                cached_payload = _window_cache_get(cache_key)
                if isinstance(cached_payload, dict):
                    state["resolved"] = bool(cached_payload.get("resolved", False))
                    state["failed"] = bool(cached_payload.get("failed", False))
                    state["resolving"] = False
                    state["expanded"] = True
                    state["start"] = cached_payload.get("start")
                    state["end"] = cached_payload.get("end")
                    state["start_truncated_to_scope"] = bool(cached_payload.get("start_truncated_to_scope", False))
                    state["end_truncated_to_scope"] = bool(cached_payload.get("end_truncated_to_scope", False))
                    state["error"] = str(cached_payload.get("error", ""))
                    _refresh_summary()
                    return

            _start_window_worker(key, state, refresh=True)

        def _build_personal_transit_export_text() -> str:
            lines = list(summary_header_lines)
            sort_mode = summary_sort_combo.currentText()
            sections = _build_personal_transit_sections(sort_mode)
            for section_title, section_subtitle, entries, empty_mode in sections:
                lines.extend([section_title, section_subtitle, ""])
                if entries:
                    for hit, source_mode in entries[:80]:
                        key = (source_mode, hit.a.name, hit.aspect, hit.b.name)
                        state = transit_ranges.get(key, {})
                        start_dt = state.get("start")
                        end_dt = state.get("end")
                        start_truncated = bool(state.get("start_truncated_to_scope", False))
                        end_truncated = bool(state.get("end_truncated_to_scope", False))
                        resolved = bool(state.get("resolved", False))
                        failed = bool(state.get("failed", False))
                        error_text = str(state.get("error", "") or "")

                        if not resolved and not failed:
                            cache_key = _window_cache_key(source_mode, hit)
                            cached_payload = _window_cache_get(cache_key)
                            if isinstance(cached_payload, dict):
                                resolved = bool(cached_payload.get("resolved", False))
                                failed = bool(cached_payload.get("failed", False))
                                start_dt = cached_payload.get("start")
                                end_dt = cached_payload.get("end")
                                start_truncated = bool(cached_payload.get("start_truncated_to_scope", False))
                                end_truncated = bool(cached_payload.get("end_truncated_to_scope", False))
                                error_text = str(cached_payload.get("error", "") or "")

                        if not resolved and not failed:
                            try:
                                result = find_transit_aspect_window_result(
                                    natal_chart,
                                    transit_chart.dt,
                                    transit_location,
                                    hit,
                                    mode_rules.get(source_mode, TRANSIT_ASPECT_RULES),
                                    step_hours=scan_step_hours,
                                    precision_minutes=scan_precision_minutes,
                                )
                                if result.out_of_scope:
                                    failed = True
                                    error_text = "Transit date is outside the configured ephemeris scope."
                                else:
                                    start_dt = result.start
                                    end_dt = result.end
                                    start_truncated = bool(result.start_truncated_to_scope)
                                    end_truncated = bool(result.end_truncated_to_scope)
                                    resolved = True
                            except Exception:
                                failed = True
                                error_text = "window lookup failed"

                        if resolved:
                            window_text = _format_transit_range(
                                start_dt,
                                end_dt,
                                include_time=include_time,
                                start_truncated_to_scope=start_truncated,
                                end_truncated_to_scope=end_truncated,
                            )
                        elif failed:
                            window_text = f"Unavailable ({error_text})" if error_text else "Unavailable"
                        else:
                            window_text = "Unavailable"

                        left_label = _format_popout_aspect_endpoint(hit.a, include_house=False)
                        right_label = _format_popout_aspect_endpoint(hit.b, include_house=True)
                        lines.append(
                            f"- {left_label:<26} {hit.aspect:<14} {right_label:<30} "
                            f"orb {_format_degree_minutes(hit.orb_deg, include_sign=False):<8}  "
                            f"window {window_text}"
                        )
                else:
                    lines.append(f"- No {mode_labels.get(empty_mode, empty_mode)} aspects within configured orbs.")
                lines.append("")
            return "\n".join(lines)

        def _handle_calendar_click(cursor) -> bool:
            block_number = cursor.block().blockNumber()
            entry = calendar_info_map.get(block_number)
            if not entry:
                return False
            if cursor.positionInBlock() < entry["icon_index"]:
                return False
            key = entry["key"]
            state = transit_ranges.get(key)
            if state is None:
                return False
            if state["resolved"]:
                if not bool(state["expanded"]):
                    state["expanded"] = True
                    _refresh_summary()
                return True
            _ensure_window_async(key, state)
            return True

        popout_context["custom_click_handler"] = _handle_calendar_click

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        _refresh_summary()
        preload_queue[:] = [key for key, state in transit_ranges.items() if not state.get("resolved")]
        _drain_preload_queue()

        dialog.resize(1320, 1080)
        self._register_popout_shortcuts(dialog)
        dialog.show()
        self._transit_popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._transit_popout_dialogs.remove(dialog)
            if dialog in self._transit_popout_dialogs
            else None
        )


    def _show_transit_chart_popout(self, chart: Chart) -> None:
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle("Get Transit")
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)

        transit_planet_weights = getattr(chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(chart)

        def _weighted_transit_score(entry: Any) -> float:
            if isinstance(entry, dict):
                return max(0.0, float(_aspect_score(entry, planet_weights=transit_planet_weights)))
            if hasattr(entry, "exactness") and hasattr(entry, "weight"):
                return max(0.0, float(entry.exactness) * float(entry.weight))
            return 0.0

        chart_info_output = self._build_popout_left_panel(
            layout,
            chart_info_placeholder="Click the ⓘ in chart summary text to see details/interpretation.",
            aspect_entries=list(getattr(chart, "aspects", []) or []),
            export_file_stem=f"{_sanitize_export_token(chart.name)}-transit_aspect_distribution",
            weighted_score_for_entry=_weighted_transit_score,
        )

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout, 3)

        date_label = chart.dt.strftime("%m.%d.%Y") if chart.dt else "??.??.????"
        time_label = (
            "unknown"
            if getattr(chart, "birthtime_unknown", False)
            else chart.dt.strftime("%H:%M")
        )
        location_label = getattr(self, "_transit_location_label", None) or "Unknown"

        popout_header_layout = QHBoxLayout()
        popout_header_layout.setContentsMargins(0, 0, 0, 0)
        popout_header_layout.setSpacing(12)

        popout_header_left = QLabel(
            "\n".join(
                [
                    f"When/Where:     {date_label} @ {time_label} | {location_label}, {chart.lat:.4f}, {chart.lon:.4f}",
                ]
            )
        )
        popout_header_left.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        popout_header_left_font = popout_header_left.font()
        popout_header_left_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        popout_header_left.setFont(popout_header_left_font)
        popout_header_layout.addWidget(popout_header_left, 0, Qt.AlignLeft | Qt.AlignTop)
        popout_header_layout.addStretch(1)

        popout_export_button = QPushButton("Export Chart")
        popout_export_button.clicked.connect(lambda _checked=False, export_chart=chart: self._export_chart(export_chart))
        popout_header_layout.addWidget(popout_export_button, 0, Qt.AlignTop | Qt.AlignRight)

        right_layout.addLayout(popout_header_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        draw_chart_wheel(
            figure,
            chart,
            canvas=canvas,
            wheel_padding=0.03,
            show_title=False,
            symbol_scale=0.7,
        )
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.draw_idle()
        right_layout.addWidget(canvas, 7)

        summary_controls = QHBoxLayout()
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        right_layout.addLayout(summary_controls)

        summary_output = QPlainTextEdit()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        summary_output._summary_highlighter = ChartSummaryHighlighter(summary_output.document())
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self)
        right_layout.addWidget(summary_output, 3)

        transit_file_stem = self._build_transit_export_file_stem(
            chart,
            chart_name_for_personal_transit=chart.name if chart.name.startswith("Personal Transit Chart for ") else None,
        )
        summary_share_button = self._attach_popout_share_button(summary_output, transit_file_stem)

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
            "share_button": summary_share_button,
        }
        self._popout_summary_contexts[popout_context_key] = popout_context
        dialog.destroyed.connect(
            lambda _=None, key=popout_context_key: self._popout_summary_contexts.pop(key, None)
        )

        def _refresh_summary() -> None:
            sort_mode = summary_sort_combo.currentText()
            chart_summary_text, position_info_map, aspect_info_map, species_info_map = format_chart_text(
                chart,
                aspect_sort=sort_mode,
                **self._chart_data_visibility_options(),
            )
            summary_lines_local = chart_summary_text.splitlines()
            positions_start_index = next(
                (idx for idx, line in enumerate(summary_lines_local) if line.strip() == "POSITIONS"),
                0,
            )
            visible_summary_lines = summary_lines_local[positions_start_index:]
            transit_visible_lines: list[str] = []
            for line in visible_summary_lines:
                stripped = line.strip()
                if stripped.startswith("Birth date:"):
                    transit_visible_lines.append(line.replace("Birth date:", "Date:", 1))
                elif stripped.startswith("Birth time:"):
                    transit_visible_lines.append(line.replace("Birth time:", "Time:", 1))
                elif stripped.startswith("Birthplace:"):
                    transit_visible_lines.append(f"Location:   {location_label}, {chart.lat:.4f}, {chart.lon:.4f}")
                else:
                    transit_visible_lines.append(line)
            summary_output.setPlainText("\n".join(transit_visible_lines))
            popout_context["position_info_map"] = position_info_map
            popout_context["aspect_info_map"] = aspect_info_map
            popout_context["species_info_map"] = species_info_map
            popout_context["summary_block_offset"] = positions_start_index

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        _refresh_summary()

        dialog.resize(1320, 1080)
        self._register_popout_shortcuts(dialog)

        dialog.show()
        self._transit_popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._transit_popout_dialogs.remove(dialog)
            if dialog in self._transit_popout_dialogs
            else None
        )

    def _build_similarities_analysis_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        panel.setLayout(layout)

        title_row = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title_row.setLayout(title_layout)

        title = QLabel("Similarities Analysis")
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        title_layout.addWidget(title)
        title_layout.addStretch(1)

        export_button = QPushButton()
        share_icon_path = _get_share_icon_path()
        if share_icon_path:
            export_button.setIcon(QIcon(share_icon_path))
            export_button.setIconSize(QSize(14, 14))
        else:
            export_button.setText("↗")
        export_button.setFlat(True)
        export_button.setFixedSize(20, 20)
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.setToolTip("Export similarities analysis as CSV")
        export_button.clicked.connect(self._export_similarities_analysis_csv)
        title_layout.addWidget(export_button, alignment=Qt.AlignRight)
        layout.addWidget(title_row)

        # placeholder = QLabel("(Coming soon)")
        # placeholder.setStyleSheet("color: #888888;")
        # layout.addWidget(placeholder)
        self.similarities_status_label = QLabel(
            "Select 2 or more charts to view similarities across selected charts."
        )
        self.similarities_status_label.setWordWrap(True)
        self.similarities_status_label.setStyleSheet("color: #bbbbbb;")
        layout.addWidget(self.similarities_status_label)

        self._refresh_similarities_chart_options()
        use_this_checkbox_style = (
            "QCheckBox { color: #9ee09e; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
            "QCheckBox::indicator:unchecked {"
            "  border: 1px solid #3b5a3b;"
            "  background-color: #1b241b;"
            "}"
            "QCheckBox::indicator:checked {"
            "  border: 1px solid #4f8f4f;"
            "  background-color: #2f7f2f;"
            "}"
        )
        chart_labels = list(self._similarities_chart_lookup.keys())
        input_rows = (
            ("Select first chart", "_similarities_first_chart_input", "_similarities_first_use_checkbox"),
            ("Select second chart", "_similarities_second_chart_input", "_similarities_second_use_checkbox"),
        )
        for placeholder, input_attr, checkbox_attr in input_rows:
            input_row = QWidget()
            input_layout = QHBoxLayout()
            input_layout.setContentsMargins(0, 0, 0, 0)
            input_layout.setSpacing(6)
            input_row.setLayout(input_layout)

            chart_input = QLineEdit()
            chart_input.setPlaceholderText(placeholder)
            completer = QCompleter(chart_labels, chart_input)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            chart_input.setCompleter(completer)
            chart_input.textChanged.connect(lambda _text: self._update_similarities_analysis(self._selected_chart_ids()))
            input_layout.addWidget(chart_input, stretch=1)

            use_checkbox = QCheckBox("use this")
            use_checkbox.setStyleSheet(use_this_checkbox_style)
            use_checkbox.toggled.connect(lambda _checked: self._update_similarities_analysis(self._selected_chart_ids()))
            input_layout.addWidget(use_checkbox, stretch=0, alignment=Qt.AlignRight)

            setattr(self, input_attr, chart_input)
            setattr(self, checkbox_attr, use_checkbox)
            layout.addWidget(input_row)

        pair_row = QWidget()
        pair_layout = QHBoxLayout()
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(8)
        pair_row.setLayout(pair_layout)
        pair_button = QPushButton("Calculate Similarity")
        pair_button.setStyleSheet(SIMILARITY_CALCULATE_BUTTON_INACTIVE_STYLE)
        pair_button.setToolTip("Select exactly 2 charts to compare.")
        pair_button.clicked.connect(self._calculate_pair_similarity_from_selection)
        pair_layout.addWidget(pair_button, alignment=Qt.AlignLeft)
        pair_layout.addStretch(1)
        layout.addWidget(pair_row)
        self._similarities_pair_button = pair_button

        pair_result_label = QLabel("Select 2 charts, or use chart inputs with “use this” checked.")
        pair_result_label.setWordWrap(True)
        pair_result_label.setStyleSheet("color: #9b9b9b;")
        layout.addWidget(pair_result_label)
        self._similarities_pair_result_label = pair_result_label

        similarities_list_style = (
            "QListWidget {"
            "  background-color: #151515;"
            "  border: 1px solid #333333;"
            "}"
            "QListWidget::item {"
            "  padding: 4px 6px;"
            "}"
        )
        (
            self.similarities_common_positions_toggle,
            self.similarities_common_positions_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Signs in positions in common",
            min_height=160,
            list_style=similarities_list_style,
        )
        (
            self.similarities_houses_in_positions_toggle,
            self.similarities_houses_in_positions_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Houses in positions in common",
            min_height=120,
            list_style=similarities_list_style,
        )
        (
            self.similarities_signs_in_houses_toggle,
            self.similarities_signs_in_houses_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Signs in houses in common",
            min_height=120,
            list_style=similarities_list_style,
        )
        (
            self.similarities_dominant_signs_toggle,
            self.similarities_dominant_signs_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Top 3 Dominant Signs in common",
            min_height=100,
            list_style=similarities_list_style,
        )
        (
            self.similarities_dominant_nakshatras_toggle,
            self.similarities_dominant_nakshatras_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Dominant nakshatras in common",
            min_height=100,
            list_style=similarities_list_style,
        )
        (
            self.similarities_common_aspects_toggle,
            self.similarities_common_aspects_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Aspects in common",
            min_height=160,
            list_style=similarities_list_style,
        )
        (
            self.similarities_common_aspects_toggle,
            self.similarities_common_aspects_list,
        ) = self._add_similarities_collapsible_section(
            layout,
            "Aspects in common",
            min_height=160,
            list_style=similarities_list_style,
        )
        layout.addStretch(1)
        return panel

    def _selected_chart_ids(
        self,
        selected_items: list[QListWidgetItem] | None = None,
    ) -> list[int]:
        if selected_items is None:
            selected_items = self.list_widget.selectedItems() if self.list_widget is not None else []
        chart_ids: list[int] = []
        for item in selected_items:
            raw_chart_id = item.data(Qt.UserRole)
            if raw_chart_id is None or isinstance(raw_chart_id, bool):
                continue
            try:
                chart_ids.append(int(raw_chart_id))
            except (TypeError, ValueError):
                continue
        return chart_ids

    def _refresh_similarities_chart_options(self) -> None:
        similarity_rows = [
            normalized
            for row in list_charts()
            if (normalized := self._normalize_chart_row(row)) is not None
            and not bool(normalized[15])
        ]
        self._similarities_chart_lookup, choices = build_chart_lookup(similarity_rows)

        for field in (
            self._similarities_first_chart_input,
            self._similarities_second_chart_input,
        ):
            if field is None:
                continue
            completer = QCompleter(choices, field)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            field.setCompleter(completer)

    def _is_placeholder_chart_id(self, chart_id: int) -> bool:
        row = self._active_chart_rows_by_id.get(int(chart_id))
        if row is not None and len(row) > 15:
            return bool(row[15])
        chart = self._get_chart_for_filter(int(chart_id))
        return bool(chart is not None and getattr(chart, "is_placeholder", False))

    def _exclude_placeholder_chart_ids(self, chart_ids: list[int]) -> list[int]:
        return [
            int(chart_id)
            for chart_id in chart_ids
            if not self._is_placeholder_chart_id(int(chart_id))
        ]

    def _resolve_similarity_pair_targets(
        self, selected_chart_ids: list[int]
    ) -> SimilarityPairResolution:
        input_state = SimilarityInputState(
            selected_chart_ids=self._exclude_placeholder_chart_ids(selected_chart_ids),
            first_checked=bool(
                self._similarities_first_use_checkbox
                and self._similarities_first_use_checkbox.isChecked()
            ),
            second_checked=bool(
                self._similarities_second_use_checkbox
                and self._similarities_second_use_checkbox.isChecked()
            ),
            first_input_value=(
                self._similarities_first_chart_input.text()
                if self._similarities_first_chart_input
                else ""
            ),
            second_input_value=(
                self._similarities_second_chart_input.text()
                if self._similarities_second_chart_input
                else ""
            ),
        )
        return resolve_similarity_pair_targets(
            input_state=input_state,
            chart_lookup=self._similarities_chart_lookup,
        )

    def _calculate_pair_similarity_from_selection(self) -> None:
        if self._similarities_pair_result_label is None:
            return
        resolution = self._resolve_similarity_pair_targets(
            self._selected_chart_ids()
        )
        if resolution.first_chart_id is None or resolution.second_chart_id is None:
            QMessageBox.warning(
                self,
                "Calculate Similarity",
                resolution.guidance
                or "Please enter chart name in checked input(s), or select chart(s) from Database.",
            )
            self._similarities_pair_result_label.setText(
                resolution.guidance
                or "Select 2 charts, or use chart inputs with “use this” checked."
            )
            return
        first = self._get_chart_for_filter(resolution.first_chart_id)
        second = self._get_chart_for_filter(resolution.second_chart_id)
        if first is None or second is None:
            self._similarities_pair_result_label.setText("Could not load both selected charts.")
            return
        final_score, placement_score, aspect_score, distribution_score = chart_similarity_score(first, second)
        first_name = str(getattr(first, "name", "") or f"#{resolution.first_chart_id}")
        second_name = str(getattr(second, "name", "") or f"#{resolution.second_chart_id}")
        similarity_percent = final_score * 100.0
        band_label, band_color = self._similarity_band_for_percent(similarity_percent)
        self._similarities_pair_result_label.setText(
            f"{first_name} ↔ {second_name}: "
            f'<span style="color: {band_color}; font-weight: 600;">'
            f"{similarity_percent:.1f}% ({band_label})"
            f"</span> "
            f"(placements {placement_score * 100.0:.0f}%, "
            f"aspects {aspect_score * 100.0:.0f}%, "
            f"distribution {distribution_score * 100.0:.0f}%)."
        )

    def _similarity_band_for_percent(self, similarity_percent: float) -> tuple[str, str]:
        thresholds = load_similarity_thresholds(self._settings)
        band = classify_similarity(similarity_percent, thresholds)
        return band.label, band.color

    def _add_similarities_collapsible_section(
        self,
        layout: QVBoxLayout,
        title: str,
        *,
        min_height: int,
        list_style: str,
    ) -> tuple[QToolButton, QListWidget]:
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        section.setLayout(section_layout)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content.setLayout(content_layout)
        content.setVisible(False)

        section_list = QListWidget()
        section_list.setSelectionMode(QAbstractItemView.NoSelection)
        section_list.setFocusPolicy(Qt.NoFocus)
        section_list.setAlternatingRowColors(True)
        section_list.setStyleSheet(list_style)
        section_list.setMinimumHeight(min_height)
        content_layout.addWidget(section_list)

        def toggle_content(checked: bool) -> None:
            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

        toggle.toggled.connect(toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        layout.addWidget(section)

        return toggle, section_list

    def _set_similarities_section_matches(
        self,
        section_list: QListWidget,
        toggle: QToolButton,
        matches: list[tuple[str, int, int]],
        *,
        selection_total_count: int = 0,
        db_match_counts: dict[str, int] | None = None,
        db_total_count: int = 0,
        db_total_counts_by_label: dict[str, int] | None = None,
        show_no_match_row: bool = True,
    ) -> None:
        section_list.clear()
        if matches:
            for label, match_count, total_count in matches:
                percent_value = int(round((match_count / total_count) * 100)) if total_count else 0
                db_match_count = (db_match_counts or {}).get(label, 0)
                db_label_total_count = (
                    int((db_total_counts_by_label or {}).get(label, db_total_count))
                    if db_total_count
                    else 0
                )
                db_percent_value = (
                    int(round((db_match_count / db_label_total_count) * 100))
                    if db_label_total_count
                    else 0
                )
                percent_difference = abs(percent_value - db_percent_value)
                difference_ratio = min(percent_difference, 10) / 10.0
                # Keep zero-difference labels readable (dark red floor), then brighten
                # progressively toward vivid green as the deviation approaches/exceeds 10%.
                minimum_readable_red = 140
                maximum_bright_green = 255
                similarity_red = int(round(minimum_readable_red * (1.0 - difference_ratio)))
                similarity_green = int(round(maximum_bright_green * difference_ratio))
                item = QListWidgetItem()

                row_widget = QWidget(section_list)
                row_layout = QVBoxLayout(row_widget)
                row_layout.setContentsMargins(6, 2, 6, 2)
                row_layout.setSpacing(2)

                top_row = QWidget(row_widget)
                top_layout = QHBoxLayout(top_row)
                top_layout.setContentsMargins(0, 0, 0, 0)
                top_layout.setSpacing(10)

                label_widget = QLabel(f"({match_count}) {label}")  # this includes the total count in the label
                label_widget.setWordWrap(True)
                label_font = label_widget.font()
                label_font.setPointSize(max(1, label_font.pointSize() - 1))
                label_widget.setFont(label_font)
                label_widget.setStyleSheet(
                    f"color: rgb({similarity_red}, {similarity_green}, 0);"
                )
                top_layout.addWidget(label_widget, stretch=1)

                percent_bar = QProgressBar()
                percent_bar.setRange(0, 100)
                percent_bar.setValue(percent_value)
                percent_bar.setTextVisible(False)
                percent_bar.setFixedWidth(120)
                percent_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

                top_layout.addWidget(percent_bar, stretch=0, alignment=Qt.AlignRight)
                row_layout.addWidget(top_row)

                unknown_suffix = ""
                if selection_total_count > 0 and total_count < selection_total_count:
                    unknown_count = selection_total_count - total_count
                    unknown_percent_value = int(
                        round((unknown_count / selection_total_count) * 100)
                    )
                    unknown_suffix = f" | {unknown_percent_value}% unknown"
                tiny_label = QLabel(
                    f"{percent_value}% of selection | {db_percent_value}% of DB{unknown_suffix}"
                )
                tiny_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                tiny_label.setStyleSheet("color: #9f9f9f; font-size: 8px;")
                row_layout.addWidget(tiny_label, stretch=0, alignment=Qt.AlignLeft)

                section_list.addItem(item)
                row_height = max(row_widget.sizeHint().height() + 6, 32)
                item.setSizeHint(QSize(0, row_height))
                section_list.setItemWidget(item, row_widget)
            toggle.setChecked(True)
            return

        if show_no_match_row:
            section_list.addItem("No matches found.")
        toggle.setChecked(False)


    def _similarities_body_label(self, body: str) -> str:
        return body

    def _sorted_similarity_matches(
        self,
        counts: dict[str, int],
        total_count: int,
        total_counts_by_label: dict[str, int] | None = None,
    ) -> list[tuple[str, int, int]]:
        return [
            (label, count, int((total_counts_by_label or {}).get(label, total_count)))
            for label, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0].lower())
            )
            if count > 1
        ]

    def _build_common_position_signs(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        if len(chart_ids) < 2:
            return []

        charts = []
        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(chart_id)
            if chart is not None:
                charts.append(chart)
        chart_count = len(charts)
        if chart_count < 2:
            return []

        match_counts: dict[str, int] = {}
        total_counts_by_label: dict[str, int] = {}
        time_specific_chart_count = sum(1 for chart in charts if _chart_uses_houses(chart))
        angular_bodies = {"AS", "MC", "DS", "IC"}
        for body in PLANET_ORDER:
            signs_by_body: dict[str, int] = {}
            for chart in charts:
                if not _chart_uses_houses(chart) and body in angular_bodies:
                    continue
                if body not in chart.positions:
                    continue
                sign = _sign_for_longitude(chart.positions[body])
                label = f"{self._similarities_body_label(body)}: {sign}"
                signs_by_body[label] = signs_by_body.get(label, 0) + 1
                if label not in total_counts_by_label:
                    total_counts_by_label[label] = (
                        time_specific_chart_count if body in angular_bodies else chart_count
                    )
            for label, count in signs_by_body.items():
                match_counts[label] = match_counts.get(label, 0) + count
        return self._sorted_similarity_matches(
            match_counts,
            chart_count,
            total_counts_by_label=total_counts_by_label,
        )

    def _build_common_houses_in_positions(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        charts = [self._get_chart_for_filter(chart_id) for chart_id in chart_ids]
        charts = [chart for chart in charts if chart is not None]
        chart_count = sum(1 for chart in charts if _chart_uses_houses(chart))
        if chart_count < 2:
            return []

        match_counts: dict[str, int] = {}
        for body in PLANET_ORDER:
            houses_by_body: dict[str, int] = {}
            for chart in charts:
                if not _chart_uses_houses(chart):
                    continue
                lon = chart.positions.get(body)
                if lon is None:
                    continue
                house_num = _house_for_longitude(getattr(chart, "houses", None), lon)
                if house_num is None:
                    continue
                if (body, house_num) in {
                    ("AS", 1),
                    ("IC", 4),
                    ("DS", 7),
                    ("MC", 10),
                }:
                    continue
                label = f"{self._similarities_body_label(body)}: House {house_num}"
                houses_by_body[label] = houses_by_body.get(label, 0) + 1
            for label, count in houses_by_body.items():
                match_counts[label] = match_counts.get(label, 0) + count
        return self._sorted_similarity_matches(match_counts, chart_count)

    def _build_common_signs_in_houses(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        charts = [self._get_chart_for_filter(chart_id) for chart_id in chart_ids]
        charts = [chart for chart in charts if chart is not None]
        chart_count = sum(1 for chart in charts if _chart_uses_houses(chart))
        if chart_count < 2:
            return []

        match_counts: dict[str, int] = {}
        for house_index in range(12):
            signs_by_house: dict[str, int] = {}
            for chart in charts:
                houses = getattr(chart, "houses", None)
                if not _chart_uses_houses(chart) or not houses or len(houses) < 12:
                    continue
                sign = _sign_for_longitude(houses[house_index])
                label = f"House {house_index + 1}: {sign}"
                signs_by_house[label] = signs_by_house.get(label, 0) + 1
            for label, count in signs_by_house.items():
                match_counts[label] = match_counts.get(label, 0) + count
        return self._sorted_similarity_matches(match_counts, chart_count)

    def _build_common_dominant_signs(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        charts = [self._get_chart_for_filter(chart_id) for chart_id in chart_ids]
        charts = [chart for chart in charts if chart is not None]
        chart_count = len(charts)
        if chart_count < 2:
            return []

        sign_counts: dict[str, int] = {}
        for chart in charts:
            dominant_weights = getattr(chart, "dominant_sign_weights", None)
            if not dominant_weights:
                dominant_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_sign_weights = dominant_weights
            for sign in self._dominant_sign_top_three_labels(dominant_weights):
                sign_counts[sign] = sign_counts.get(sign, 0) + 1

        ordered_counts = {
            sign: sign_counts[sign] for sign in ZODIAC_NAMES if sign in sign_counts
        }
        return self._sorted_similarity_matches(ordered_counts, chart_count)

    @staticmethod
    def _dominant_sign_top_three_labels(
        dominant_weights: dict[str, float] | None,
    ) -> set[str]:
        if not dominant_weights:
            return set()
        ranked = sorted(
            (
                (sign, float(weight))
                for sign, weight in dominant_weights.items()
                if sign in ZODIAC_NAMES and float(weight) > 0
            ),
            key=lambda item: (-item[1], ZODIAC_NAMES.index(item[0])),
        )
        if not ranked:
            return set()
        return {sign for sign, _weight in ranked[:3]}

    @staticmethod
    def _dominant_planet_top_three_labels(
        dominant_weights: dict[str, float] | None,
    ) -> set[str]:
        if not dominant_weights:
            return set()
        planet_order = [
            body
            for body in PLANET_ORDER
            if body not in {"AS", "MC", "DS", "IC"} and body in NATAL_WEIGHT
        ]
        ranked = sorted(
            (
                (body, float(weight))
                for body, weight in dominant_weights.items()
                if body in planet_order and float(weight) > 0
            ),
            key=lambda item: (-item[1], planet_order.index(item[0])),
        )
        return {body for body, _weight in ranked[:3]}

    @staticmethod
    def _dominant_house_top_three_labels(
        dominant_weights: dict[int, float] | None,
    ) -> set[int]:
        if not dominant_weights:
            return set()
        ranked = sorted(
            (
                (house_num, float(weight))
                for house_num, weight in dominant_weights.items()
                if isinstance(house_num, int) and 1 <= house_num <= 12 and float(weight) > 0
            ),
            key=lambda item: (-item[1], item[0]),
        )
        return {house_num for house_num, _weight in ranked[:3]}

    def _build_common_dominant_nakshatras(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        charts = [self._get_chart_for_filter(chart_id) for chart_id in chart_ids]
        charts = [chart for chart in charts if chart is not None]
        chart_count = len(charts)
        if chart_count < 2:
            return []

        nakshatra_counts: dict[str, int] = {}
        for chart in charts:
            weighted_counts: dict[str, int] = {}
            use_houses = _chart_uses_houses(chart)
            for body in PLANET_ORDER:
                if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                    continue
                lon = chart.positions.get(body)
                if lon is None:
                    continue
                nakshatra = _get_nakshatra(lon)
                weighted_counts[nakshatra] = weighted_counts.get(nakshatra, 0) + (
                    NATAL_WEIGHT.get(body, 1)
                )

            if not weighted_counts:
                continue

            for name in {
                name
                for name, _weight in sorted(
                    weighted_counts.items(), key=lambda item: item[1], reverse=True
                )[:3]
            }:
                nakshatra_counts[name] = nakshatra_counts.get(name, 0) + 1

        return self._sorted_similarity_matches(nakshatra_counts, chart_count)

    def _build_common_aspects(
        self, chart_ids: list[int]
    ) -> list[tuple[str, int, int]]:
        charts = [self._get_chart_for_filter(chart_id) for chart_id in chart_ids]
        charts = [chart for chart in charts if chart is not None]
        chart_count = len(charts)
        if chart_count < 2:
            return []

        angular_bodies = {"AS", "MC", "DS", "IC"}
        aspect_counts: dict[str, int] = {}
        total_counts_by_label: dict[str, int] = {}
        time_specific_chart_count = sum(1 for chart in charts if _chart_uses_houses(chart))
        for chart in charts:
            chart_aspects: set[str] = set()
            use_houses = _chart_uses_houses(chart)
            for aspect in getattr(chart, "aspects", []) or []:
                if _is_structural_tautology(aspect):
                    continue
                raw_p1 = aspect.get("p1", "")
                raw_p2 = aspect.get("p2", "")
                if not use_houses and (
                    raw_p1 in angular_bodies or raw_p2 in angular_bodies
                ):
                    continue
                p1 = self._similarities_body_label(raw_p1)
                p2 = self._similarities_body_label(raw_p2)
                aspect_type = aspect.get("type", "")
                if not p1 or not p2 or not aspect_type:
                    continue
                body_a, body_b = sorted([p1, p2])
                aspect_label = f"{body_a} {_aspect_label(aspect_type).lower()} {body_b}"
                chart_aspects.add(aspect_label)
                if aspect_label not in total_counts_by_label:
                    total_counts_by_label[aspect_label] = (
                        time_specific_chart_count
                        if raw_p1 in angular_bodies or raw_p2 in angular_bodies
                        else chart_count
                    )
            for aspect_label in chart_aspects:
                aspect_counts[aspect_label] = aspect_counts.get(aspect_label, 0) + 1

        return self._sorted_similarity_matches(
            aspect_counts,
            chart_count,
            total_counts_by_label=total_counts_by_label,
        )

    def _update_similarities_analysis(self, chart_ids: list[int]) -> None:
        selected_non_placeholder_chart_ids = self._exclude_placeholder_chart_ids(chart_ids)
        db_chart_ids = [
            int(normalized[0])
            for row in self._chart_rows
            if (normalized := self._normalize_chart_row(row)) is not None
            and not bool(normalized[15])
        ]
        db_total_count = len(db_chart_ids)
        if self._similarities_pair_button is not None:
            resolution = self._resolve_similarity_pair_targets(selected_non_placeholder_chart_ids)
            self._similarities_pair_button.setStyleSheet(
                SIMILARITY_CALCULATE_BUTTON_ACTIVE_STYLE
                if resolution.allow_click
                else SIMILARITY_CALCULATE_BUTTON_INACTIVE_STYLE
            )
            self._similarities_pair_button.setToolTip(
                "Calculate similarity between the selected/input charts."
                if resolution.allow_click
                else (resolution.guidance or "Select 2 charts to compare.")
            )
        if self._similarities_pair_result_label is not None:
            resolution = self._resolve_similarity_pair_targets(selected_non_placeholder_chart_ids)
            if not resolution.allow_click:
                self._similarities_pair_result_label.setText(
                    resolution.guidance or "Select 2 charts to compare."
                )

        if len(selected_non_placeholder_chart_ids) < 2:
            self._similarities_export_sections = []
            if len(chart_ids) >= 2:
                self.similarities_status_label.setText(
                    "Placeholders are excluded from astrological similarities. "
                    "Select 2 or more non-placeholder charts."
                )
            else:
                self.similarities_status_label.setText(
                    "Select 2 or more charts to view similarities across selected charts."
                )
            self._set_similarities_section_matches(
                self.similarities_common_positions_list,
                self.similarities_common_positions_toggle,
                [],
                show_no_match_row=False,
            )
            self._set_similarities_section_matches(
                self.similarities_houses_in_positions_list,
                self.similarities_houses_in_positions_toggle,
                [],
                show_no_match_row=False,
            )
            self._set_similarities_section_matches(
                self.similarities_signs_in_houses_list,
                self.similarities_signs_in_houses_toggle,
                [],
                show_no_match_row=False,
            )
            self._set_similarities_section_matches(
                self.similarities_dominant_signs_list,
                self.similarities_dominant_signs_toggle,
                [],
                show_no_match_row=False,
            )
            self._set_similarities_section_matches(
                self.similarities_dominant_nakshatras_list,
                self.similarities_dominant_nakshatras_toggle,
                [],
                show_no_match_row=False,
            )
            self._set_similarities_section_matches(
                self.similarities_common_aspects_list,
                self.similarities_common_aspects_toggle,
                [],
                show_no_match_row=False,
            )
            return

        common_positions = self._build_common_position_signs(selected_non_placeholder_chart_ids)
        common_houses_in_positions = self._build_common_houses_in_positions(selected_non_placeholder_chart_ids)
        common_signs_in_houses = self._build_common_signs_in_houses(selected_non_placeholder_chart_ids)
        common_dominant_signs = self._build_common_dominant_signs(selected_non_placeholder_chart_ids)
        common_dominant_nakshatras = self._build_common_dominant_nakshatras(selected_non_placeholder_chart_ids)
        common_aspects = self._build_common_aspects(selected_non_placeholder_chart_ids)
        db_common_positions_matches = self._build_common_position_signs(db_chart_ids)
        db_common_positions = dict(
            (label, count) for label, count, _total in db_common_positions_matches
        )
        db_common_positions_totals = dict(
            (label, total) for label, _count, total in db_common_positions_matches
        )
        db_common_houses_in_positions_matches = self._build_common_houses_in_positions(db_chart_ids)
        db_common_houses_in_positions = dict(
            (label, count) for label, count, _total in db_common_houses_in_positions_matches
        )
        db_common_houses_in_positions_totals = dict(
            (label, total) for label, _count, total in db_common_houses_in_positions_matches
        )
        db_common_signs_in_houses_matches = self._build_common_signs_in_houses(db_chart_ids)
        db_common_signs_in_houses = dict(
            (label, count) for label, count, _total in db_common_signs_in_houses_matches
        )
        db_common_signs_in_houses_totals = dict(
            (label, total) for label, _count, total in db_common_signs_in_houses_matches
        )
        db_common_dominant_signs = dict(
            (label, count) for label, count, _total in self._build_common_dominant_signs(db_chart_ids)
        )
        db_common_dominant_nakshatras = dict(
            (label, count) for label, count, _total in self._build_common_dominant_nakshatras(db_chart_ids)
        )
        db_common_aspects_matches = self._build_common_aspects(db_chart_ids)
        db_common_aspects = dict(
            (label, count) for label, count, _total in db_common_aspects_matches
        )
        db_common_aspects_totals = dict(
            (label, total) for label, _count, total in db_common_aspects_matches
        )
        self._similarities_export_sections = [
            (
                "Signs in positions in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_positions.get(label, 0)),
                        int(db_common_positions_totals.get(label, db_total_count)),
                    )
                    for label, match_count, total_count in common_positions
                ],
            ),
            (
                "Houses in positions in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_houses_in_positions.get(label, 0)),
                        int(db_common_houses_in_positions_totals.get(label, db_total_count)),
                    )
                    for label, match_count, total_count in common_houses_in_positions
                ],
            ),
            (
                "Signs in houses in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_signs_in_houses.get(label, 0)),
                        int(db_common_signs_in_houses_totals.get(label, db_total_count)),
                    )
                    for label, match_count, total_count in common_signs_in_houses
                ],
            ),
            (
                "Top 3 Dominant Signs in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_dominant_signs.get(label, 0)),
                        db_total_count,
                    )
                    for label, match_count, total_count in common_dominant_signs
                ],
            ),
            (
                "Dominant nakshatras in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_dominant_nakshatras.get(label, 0)),
                        db_total_count,
                    )
                    for label, match_count, total_count in common_dominant_nakshatras
                ],
            ),
            (
                "Aspects in common",
                [
                    (
                        label,
                        match_count,
                        total_count,
                        int(db_common_aspects.get(label, 0)),
                        int(db_common_aspects_totals.get(label, db_total_count)),
                    )
                    for label, match_count, total_count in common_aspects
                ],
            ),
        ]

        total_matches = (
            len(common_positions)
            + len(common_houses_in_positions)
            + len(common_signs_in_houses)
            + len(common_dominant_signs)
            + len(common_dominant_nakshatras)
            + len(common_aspects)
        )
        if total_matches > 0:
            self.similarities_status_label.setText(
                f"{total_matches} shared pattern(s) found across "
                f"{len(selected_non_placeholder_chart_ids)} selected chart(s), each present in at least 2 charts."
            )
        else:
            self.similarities_status_label.setText(
                f"No shared similarities found in at least 2 charts across "
                f"{len(selected_non_placeholder_chart_ids)} selected chart(s)."
            )
        self._set_similarities_section_matches(
            self.similarities_common_positions_list,
            self.similarities_common_positions_toggle,
            common_positions,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_positions,
            db_total_count=db_total_count,
            db_total_counts_by_label=db_common_positions_totals,
        )
        self._set_similarities_section_matches(
            self.similarities_houses_in_positions_list,
            self.similarities_houses_in_positions_toggle,
            common_houses_in_positions,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_houses_in_positions,
            db_total_count=db_total_count,
            db_total_counts_by_label=db_common_houses_in_positions_totals,
        )
        self._set_similarities_section_matches(
            self.similarities_signs_in_houses_list,
            self.similarities_signs_in_houses_toggle,
            common_signs_in_houses,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_signs_in_houses,
            db_total_count=db_total_count,
            db_total_counts_by_label=db_common_signs_in_houses_totals,
        )
        self._set_similarities_section_matches(
            self.similarities_dominant_signs_list,
            self.similarities_dominant_signs_toggle,
            common_dominant_signs,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_dominant_signs,
            db_total_count=db_total_count,
        )
        self._set_similarities_section_matches(
            self.similarities_dominant_nakshatras_list,
            self.similarities_dominant_nakshatras_toggle,
            common_dominant_nakshatras,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_dominant_nakshatras,
            db_total_count=db_total_count,
        )
        self._set_similarities_section_matches(
            self.similarities_common_aspects_list,
            self.similarities_common_aspects_toggle,
            common_aspects,
            selection_total_count=len(selected_non_placeholder_chart_ids),
            db_match_counts=db_common_aspects,
            db_total_count=db_total_count,
            db_total_counts_by_label=db_common_aspects_totals,
        )

    def _export_similarities_analysis_csv(self) -> None:
        if not self._similarities_export_sections:
            QMessageBox.information(
                self,
                "No similarities data",
                "Select at least 2 charts to generate similarities before exporting.",
            )
            return

        header_name, accepted = QInputDialog.getText(
            self,
            "Selection name",
            "Name this selection (used as a CSV column header):",
            text="Selection",
        )
        if not accepted:
            return
        header_name = header_name.strip() or "Selection"

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        sanitized_header = re.sub(r"[^\w\s-]", "", header_name).strip() or "selection"
        sanitized_header = re.sub(r"\s+", "_", sanitized_header)
        default_filename = (
            f"ephemeraldaddy_{sanitized_header} similarities analysis_{timestamp}.csv"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export similarities analysis as CSV",
            default_filename,
            "CSV Files (*.csv)",
        )
        QTimer.singleShot(0, self._reactivate_database_view)
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"

        rows: list[list[str | int | float]] = []
        for section_title, matches in self._similarities_export_sections:
            if not matches:
                continue
            for label, match_count, total_count, database_match_count, database_total_count in matches:
                selection_percent = round((match_count / total_count) * 100, 2) if total_count else 0
                database_percent = (
                    round((database_match_count / database_total_count) * 100, 2)
                    if database_total_count
                    else 0
                )
                percent_difference = round(selection_percent - database_percent, 2)
                rows.append([
                    section_title,
                    label,
                    match_count,
                    total_count,
                    selection_percent,
                    database_match_count,
                    database_total_count,
                    database_percent,
                    percent_difference,
                ])

        if not rows:
            QMessageBox.information(
                self,
                "No similarities data",
                "No shared similarities are available to export yet.",
            )
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    "category",
                    header_name,
                    f"{header_name} match count",
                    "selected chart count",
                    f"{header_name} match percent",
                    "database match count",
                    "database chart count",
                    "database match percent",
                    f"{header_name} minus database match percent",
                ])
                writer.writerows(rows)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export similarities analysis as CSV:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved similarities analysis CSV to:\n{file_path}",
        )
            
    def _build_sentiment_averages(
        self,
        chart_ids: list[int],
        positive_labels: set[str],
        negative_labels: set[str],
        progress_callback: Callable[[], None] | None = None,
    ) -> tuple[dict[str, float], int, int, int]:
        totals = {label: 0 for label in SENTIMENT_OPTIONS}
        loaded_charts = 0
        positive_count = 0
        negative_count = 0
        for chart_id in chart_ids:
            if progress_callback:
                progress_callback()
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                continue
            loaded_charts += 1
            sentiments = getattr(chart, "sentiments", []) or []
            sentiment_set = set()
            for sentiment in sentiments:
                if sentiment in totals:
                    totals[sentiment] += 1
                    sentiment_set.add(sentiment)
            if positive_labels.intersection(sentiment_set):
                positive_count += 1
            if negative_labels.intersection(sentiment_set):
                negative_count += 1

        # total_sentiments = sum(totals.values()) #for total sentiments checked
        # if total_sentiments: #for total sentiments checked
        if loaded_charts:  # for total charts
            averages = {
                label: totals[label] / loaded_charts  # for total charts
                # label: totals[label] / total_sentiments #for total sentiments checked
                for label in SENTIMENT_OPTIONS
            }
        else:
            averages = {label: 0 for label in SENTIMENT_OPTIONS}
        return averages, loaded_charts, positive_count, negative_count

    def _build_sign_distribution(
        self,
        chart_ids: list[int],
        progress_callback: Callable[[], None] | None = None,
    ) -> dict[str, float]:
        totals = {sign: 0 for sign in ZODIAC_NAMES}
        total_count = 0.0
        for chart_id in chart_ids:
            if progress_callback:
                progress_callback()
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                continue
            use_houses = _chart_uses_houses(chart)
            for body in PLANET_ORDER:
                if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                    continue
                if body not in chart.positions:
                    continue
                lon = chart.positions[body]
                sign = _sign_for_longitude(lon)
                totals[sign] += 1
                total_count += 1

        if total_count:
            return {sign: totals[sign] / total_count for sign in ZODIAC_NAMES}
        return {sign: 0 for sign in ZODIAC_NAMES}

    def _build_dominant_sign_distribution(
        self,
        chart_ids: list[int],
        progress_callback: Callable[[], None] | None = None,
    ) -> dict[str, float]:
        totals = {sign: 0.0 for sign in ZODIAC_NAMES}
        total_weight = 0.0
        stored_weights = load_dominant_sign_weights(chart_ids)
        for chart_id in chart_ids:
            if progress_callback:
                progress_callback()
            dominant_weights = stored_weights.get(chart_id)
            if not dominant_weights:
                chart = self._get_chart_for_filter(chart_id)
                if chart is None:
                    continue
                dominant_weights = _calculate_dominant_sign_weights(chart)
                update_chart_dominant_sign_weights(
                    chart_id,
                    dominant_weights,
                )
            for sign in ZODIAC_NAMES:
                weight = dominant_weights.get(sign, 0)
                totals[sign] += weight
                total_weight += weight
        if total_weight:
            return {sign: totals[sign] / total_weight for sign in ZODIAC_NAMES}
        return {sign: 0 for sign in ZODIAC_NAMES}

    def _build_relationship_distribution(
        self,
        chart_ids: list[int],
        progress_callback: Callable[[], None] | None = None,
    ) -> dict[str, float]:
        totals = {relationship: 0 for relationship in RELATION_TYPE}
        total_count = 0.0
        for chart_id in chart_ids:
            if progress_callback:
                progress_callback()
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                continue
            relationship_types = getattr(chart, "relationship_types", []) or []
            for relationship in relationship_types:
                if relationship in totals:
                    totals[relationship] += 1
                    total_count += 1

        if total_count:
            return {
                relationship: totals[relationship] / total_count
                for relationship in RELATION_TYPE
            }
        return {relationship: 0 for relationship in RELATION_TYPE}

    def _build_species_distribution(
        self,
        chart_ids: list[int],
        progress_callback: Callable[[], None] | None = None,
        mode: str = "top_ranked",
    ) -> dict[str, float]:
        totals = {species: 0 for species in SPECIES_FAMILIES}
        total_count = 0
        for chart_id in chart_ids:
            if progress_callback:
                progress_callback()
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                continue
            try:
                species_top_three = assign_top_three_species(chart)
            except Exception:
                continue
            if not species_top_three:
                continue
            if mode == "top_three_ranked":
                for species_name, _subtype, _score in species_top_three[:3]:
                    if species_name in totals:
                        totals[species_name] += 1
                        total_count += 1
            elif mode == "top_two_three_only":
                for species_name, _subtype, _score in species_top_three[1:3]:
                    if species_name in totals:
                        totals[species_name] += 1
                        total_count += 1
            else:
                top_species = species_top_three[0][0]
                if top_species in totals:
                    totals[top_species] += 1
                    total_count += 1

        if total_count:
            return {
                species: totals[species] / total_count
                for species in SPECIES_FAMILIES
            }
        return {species: 0 for species in SPECIES_FAMILIES}

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

    @staticmethod
    def _generation_for_birth_year(birth_year: int | None) -> str | None:
        if not isinstance(birth_year, int):
            return None
        for cohort in GENERATIONAL_COHORTS:
            start_year = cohort.get("start_year")
            end_year = cohort.get("end_year")
            if not isinstance(start_year, int) or not isinstance(end_year, int):
                continue
            if start_year <= birth_year <= end_year:
                cohort_name = cohort.get("name")
                return str(cohort_name) if cohort_name else None
        return None

    @staticmethod
    def _chart_birth_year_for_filters(chart_row: tuple[Any, ...] | None, chart: Chart | None) -> int | None:
        if chart_row and len(chart_row) > 19 and isinstance(chart_row[19], int):
            return int(chart_row[19])

        # Placeholders with unspecified birth year should remain generation-unknown.
        if chart_row and len(chart_row) > 19 and bool(chart_row[15]) and chart_row[19] is None:
            return None

        if chart_row and len(chart_row) > 4:
            dt_value = parse_datetime_value(chart_row[4])
            if isinstance(dt_value, datetime.datetime):
                return int(dt_value.year)
        if chart is None:
            return None
        birth_year = getattr(chart, "birth_year", None)
        if isinstance(birth_year, int):
            return int(birth_year)

        if bool(getattr(chart, "is_placeholder", False)) and birth_year is None:
            return None

        dt_value = getattr(chart, "dt", None)
        if isinstance(dt_value, datetime.datetime):
            return int(dt_value.year)
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
            if city:
                city_counts[city] += 1
            if country:
                resolved_country = resolve_country(country)
                canonical_country = str(resolved_country.get("name", "")).strip() if resolved_country else ""
                country_counts[canonical_country or country] += 1
                if resolved_country and resolved_country.get("alpha_2") == "US" and state:
                    us_state_counts[state] += 1

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

    def _build_text_analysis_widget(self, lines: list[str]) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        widget.setLayout(layout)
        for line in lines:
            label = QLabel(line)
            label.setStyleSheet("font-size: 11px; color: #f5f5f5;")
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch(1)
        return widget

    def _empty_database_metrics_cache(self) -> dict[str, Any]:
        return {
            "chart_ids": set(),
            "loaded_charts": 0,
            "sentiment_totals": {label: 0 for label in SENTIMENT_OPTIONS},
            "positive_count": 0,
            "negative_count": 0,
            "sign_totals": {sign: 0 for sign in ZODIAC_NAMES},
            "sign_total_count": 0.0,
            "house_prevalence_totals": {house_num: 0.0 for house_num in range(1, 13)},
            "house_prevalence_total_count": 0.0,
            "element_prevalence_totals": {
                element: 0.0 for element in ("Fire", "Earth", "Air", "Water")
            },
            "element_prevalence_total_count": 0.0,
            "nakshatra_prevalence_totals": {
                name: 0.0 for name, *_ in NAKSHATRA_RANGES
            },
            "nakshatra_prevalence_total_count": 0.0,
            "position_sign_totals_by_body": {
                body: {sign: 0 for sign in ZODIAC_NAMES}
                for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
            },
            "position_sign_count_by_body": {
                body: 0.0 for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
            },
            "dominant_sign_totals": {sign: 0.0 for sign in ZODIAC_NAMES},
            "dominant_sign_total_weight": 0.0,
            "dominant_sign_frequency_totals": {sign: 0.0 for sign in ZODIAC_NAMES},
            "dominant_planet_totals": {
                body: 0.0
                for body in PLANET_ORDER
                if body not in {"AS", "MC", "DS", "IC"} and body in NATAL_WEIGHT
            },
            "dominant_planet_total_weight": 0.0,
            "dominant_planet_weight_totals": {
                body: 0.0
                for body in PLANET_ORDER
                if body not in {"AS", "MC", "DS", "IC"} and body in NATAL_WEIGHT
            },
            "dominant_planet_weight_total_weight": 0.0,
            "dominant_house_totals": {house_num: 0.0 for house_num in range(1, 13)},
            "dominant_house_total_weight": 0.0,
            "dominant_house_weight_totals": {house_num: 0.0 for house_num in range(1, 13)},
            "dominant_house_weight_total_weight": 0.0,
            "dominant_element_totals": {element: 0.0 for element in ("Fire", "Earth", "Air", "Water")},
            "dominant_element_total_weight": 0.0,
            "relationship_totals": {relationship: 0 for relationship in RELATION_TYPE},
            "relationship_total_count": 0.0,
            "species_totals_by_mode": {
                mode: {species: 0 for species in SPECIES_FAMILIES}
                for mode in ("top_ranked", "top_three_ranked", "top_two_three_only")
            },
            "species_total_count_by_mode": {
                "top_ranked": 0,
                "top_three_ranked": 0,
                "top_two_three_only": 0,
            },
            "social_score_total": 0.0,
            "alignment_score_total": 0.0,
        }

    def _build_chart_metric_snapshot(self, chart_id: int) -> dict[str, Any]:
        """Build one chart's analytics payload for the whole DB analytics panel."""
        snapshot = self._empty_database_metrics_cache()
        snapshot["loaded"] = 0
        chart = self._get_chart_for_filter(chart_id)
        if chart is None:
            return snapshot
        snapshot["loaded"] = 1
        snapshot["is_placeholder"] = bool(getattr(chart, "is_placeholder", False))
        snapshot["social_score"] = float(getattr(chart, "social_score", 0) or 0)
        snapshot["alignment_score"] = float(getattr(chart, "alignment_score", 0) or 0)
        sentiments = set(getattr(chart, "sentiments", []) or [])
        for sentiment in sentiments:
            if sentiment in snapshot["sentiment_totals"]:
                snapshot["sentiment_totals"][sentiment] += 1
        labels = list(SENTIMENT_OPTIONS)
        negative_start = SENTIMENT_OPTIONS.index("can't trust") if "can't trust" in SENTIMENT_OPTIONS else len(labels)
        positive_labels = set(labels[:negative_start])
        negative_labels = set(labels[negative_start:])
        snapshot["positive"] = int(bool(sentiments & positive_labels))
        snapshot["negative"] = int(bool(sentiments & negative_labels))

        use_houses = _chart_uses_houses(chart)
        for body in PLANET_ORDER:
            if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                continue
            if body not in chart.positions:
                continue
            sign = _sign_for_longitude(chart.positions[body])
            snapshot["sign_totals"][sign] += 1
            snapshot["sign_total_count"] += 1

        house_prevalence_counts = _calculate_house_prevalence_counts(chart)
        for house_num in range(1, 13):
            count = float(house_prevalence_counts.get(house_num, 0.0))
            snapshot["house_prevalence_totals"][house_num] += count
            snapshot["house_prevalence_total_count"] += count

        element_prevalence_counts = _calculate_element_prevalence_counts(chart)
        for element in ("Fire", "Earth", "Air", "Water"):
            count = float(element_prevalence_counts.get(element, 0.0))
            snapshot["element_prevalence_totals"][element] += count
            snapshot["element_prevalence_total_count"] += count

        nakshatra_prevalence_counts = _calculate_nakshatra_prevalence_counts(chart)
        for nakshatra_name, *_ in NAKSHATRA_RANGES:
            count = float(nakshatra_prevalence_counts.get(nakshatra_name, 0.0))
            snapshot["nakshatra_prevalence_totals"][nakshatra_name] += count
            snapshot["nakshatra_prevalence_total_count"] += count

        for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS:
            if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                continue
            lon = chart.positions.get(body)
            if lon is None:
                continue
            sign = _sign_for_longitude(lon)
            snapshot["position_sign_totals_by_body"][body][sign] += 1
            snapshot["position_sign_count_by_body"][body] += 1

        dominant_weights = getattr(chart, "dominant_sign_weights", None) or _calculate_dominant_sign_weights(chart)
        for sign in ZODIAC_NAMES:
            sign_weight = float(dominant_weights.get(sign, 0.0))
            if sign_weight <= 0:
                continue
            snapshot["dominant_sign_totals"][sign] += sign_weight
            snapshot["dominant_sign_total_weight"] += sign_weight
        for sign in self._dominant_sign_top_three_labels(dominant_weights):
            snapshot["dominant_sign_frequency_totals"][sign] += 1.0

        dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not dominant_planet_weights:
            dominant_planet_weights = _calculate_dominant_planet_weights(chart)
            chart.dominant_planet_weights = dominant_planet_weights
        for body in snapshot["dominant_planet_weight_totals"].keys():
            body_weight = float(dominant_planet_weights.get(body, 0.0)) if dominant_planet_weights else 0.0
            if body_weight <= 0:
                continue
            snapshot["dominant_planet_weight_totals"][body] += body_weight
            snapshot["dominant_planet_weight_total_weight"] += body_weight
        for body in self._dominant_planet_top_three_labels(dominant_planet_weights):
            snapshot["dominant_planet_totals"][body] += 1.0
            snapshot["dominant_planet_total_weight"] += 1.0

        dominant_house_weights = _calculate_dominant_house_weights(chart)
        for house_num in range(1, 13):
            house_weight = float(dominant_house_weights.get(house_num, 0.0))
            if house_weight <= 0:
                continue
            snapshot["dominant_house_weight_totals"][house_num] += house_weight
            snapshot["dominant_house_weight_total_weight"] += house_weight
        for house_num in self._dominant_house_top_three_labels(dominant_house_weights):
            snapshot["dominant_house_totals"][house_num] += 1.0
            snapshot["dominant_house_total_weight"] += 1.0

        dominant_element_weights = _calculate_dominant_element_weights(chart)
        element_order = ["Fire", "Earth", "Air", "Water"]
        ranked_elements = sorted(
            element_order,
            key=lambda element: (-float(dominant_element_weights.get(element, 0.0)), element_order.index(element)),
        )
        if ranked_elements and float(dominant_element_weights.get(ranked_elements[0], 0.0)) > 0:
            snapshot["dominant_element_totals"][ranked_elements[0]] += 1.0
            snapshot["dominant_element_total_weight"] += 1.0

        for relationship in getattr(chart, "relationship_types", []) or []:
            if relationship in snapshot["relationship_totals"]:
                snapshot["relationship_totals"][relationship] += 1
                snapshot["relationship_total_count"] += 1

        if not snapshot["is_placeholder"]:
            try:
                species_top_three = assign_top_three_species(chart)
            except Exception:
                species_top_three = []
            if species_top_three:
                top_species = species_top_three[0][0]
                if top_species in snapshot["species_totals_by_mode"]["top_ranked"]:
                    snapshot["species_totals_by_mode"]["top_ranked"][top_species] += 1
                    snapshot["species_total_count_by_mode"]["top_ranked"] += 1
                for species_name, _subtype, _score in species_top_three[:3]:
                    if species_name in snapshot["species_totals_by_mode"]["top_three_ranked"]:
                        snapshot["species_totals_by_mode"]["top_three_ranked"][species_name] += 1
                        snapshot["species_total_count_by_mode"]["top_three_ranked"] += 1
                for species_name, _subtype, _score in species_top_three[1:3]:
                    if species_name in snapshot["species_totals_by_mode"]["top_two_three_only"]:
                        snapshot["species_totals_by_mode"]["top_two_three_only"][species_name] += 1
                        snapshot["species_total_count_by_mode"]["top_two_three_only"] += 1
        return snapshot

    def _apply_snapshot_delta(self, totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
        totals["loaded_charts"] += direction * int(snapshot.get("loaded", 0))
        totals["positive_count"] += direction * int(snapshot.get("positive", 0))
        totals["negative_count"] += direction * int(snapshot.get("negative", 0))
        totals["sign_total_count"] += direction * float(snapshot.get("sign_total_count", 0.0))
        totals["dominant_sign_total_weight"] += direction * float(snapshot.get("dominant_sign_total_weight", 0.0))
        totals["dominant_planet_total_weight"] += direction * float(snapshot.get("dominant_planet_total_weight", 0.0))
        totals["dominant_planet_weight_total_weight"] += direction * float(
            snapshot.get("dominant_planet_weight_total_weight", 0.0)
        )
        totals["dominant_house_total_weight"] += direction * float(snapshot.get("dominant_house_total_weight", 0.0))
        totals["dominant_house_weight_total_weight"] += direction * float(
            snapshot.get("dominant_house_weight_total_weight", 0.0)
        )
        totals["dominant_element_total_weight"] += direction * float(snapshot.get("dominant_element_total_weight", 0.0))
        totals["relationship_total_count"] += direction * float(snapshot.get("relationship_total_count", 0.0))
        totals["social_score_total"] += direction * float(snapshot.get("social_score", 0.0))
        totals["alignment_score_total"] += direction * float(snapshot.get("alignment_score", 0.0))
        for body, count in snapshot.get("position_sign_count_by_body", {}).items():
            totals["position_sign_count_by_body"][body] += direction * float(count)
        for mode, count in snapshot.get("species_total_count_by_mode", {}).items():
            totals["species_total_count_by_mode"][mode] += direction * int(count)
        for key in SENTIMENT_OPTIONS:
            totals["sentiment_totals"][key] += direction * int(snapshot["sentiment_totals"].get(key, 0))
        for sign in ZODIAC_NAMES:
            totals["sign_totals"][sign] += direction * int(snapshot["sign_totals"].get(sign, 0))
            totals["dominant_sign_totals"][sign] += direction * float(snapshot["dominant_sign_totals"].get(sign, 0.0))
            totals["dominant_sign_frequency_totals"][sign] += direction * float(
                snapshot["dominant_sign_frequency_totals"].get(sign, 0.0)
            )
        for body in totals["dominant_planet_totals"]:
            totals["dominant_planet_totals"][body] += direction * float(snapshot["dominant_planet_totals"].get(body, 0.0))
            totals["dominant_planet_weight_totals"][body] += direction * float(
                snapshot["dominant_planet_weight_totals"].get(body, 0.0)
            )
        for house_num in range(1, 13):
            totals["house_prevalence_totals"][house_num] += direction * float(
                snapshot["house_prevalence_totals"].get(house_num, 0.0)
            )
            totals["dominant_house_totals"][house_num] += direction * float(snapshot["dominant_house_totals"].get(house_num, 0.0))
            totals["dominant_house_weight_totals"][house_num] += direction * float(
                snapshot["dominant_house_weight_totals"].get(house_num, 0.0)
            )
        totals["house_prevalence_total_count"] += direction * float(
            snapshot.get("house_prevalence_total_count", 0.0)
        )
        for element in ("Fire", "Earth", "Air", "Water"):
            totals["element_prevalence_totals"][element] += direction * float(
                snapshot["element_prevalence_totals"].get(element, 0.0)
            )
            totals["dominant_element_totals"][element] += direction * float(snapshot["dominant_element_totals"].get(element, 0.0))
        totals["element_prevalence_total_count"] += direction * float(
            snapshot.get("element_prevalence_total_count", 0.0)
        )
        totals["nakshatra_prevalence_total_count"] += direction * float(
            snapshot.get("nakshatra_prevalence_total_count", 0.0)
        )
        for nakshatra_name, *_ in NAKSHATRA_RANGES:
            totals["nakshatra_prevalence_totals"][nakshatra_name] += direction * float(
                snapshot["nakshatra_prevalence_totals"].get(nakshatra_name, 0.0)
            )
        for body, sign_totals in snapshot.get("position_sign_totals_by_body", {}).items():
            for sign in ZODIAC_NAMES:
                totals["position_sign_totals_by_body"][body][sign] += direction * int(sign_totals.get(sign, 0))
        for relationship in RELATION_TYPE:
            totals["relationship_totals"][relationship] += direction * int(snapshot["relationship_totals"].get(relationship, 0))
        for mode in ("top_ranked", "top_three_ranked", "top_two_three_only"):
            for species in SPECIES_FAMILIES:
                totals["species_totals_by_mode"][mode][species] += direction * int(snapshot["species_totals_by_mode"][mode].get(species, 0))

    def _refresh_database_metrics_cache(self, force_full_refresh: bool = False) -> None:
        if self._database_metrics_cache is None or force_full_refresh:
            cache = self._empty_database_metrics_cache()
            self._database_metric_snapshots = {}
            active_ids = {row[0] for row in self._chart_rows}
            cache["chart_ids"] = set(active_ids)
            for chart_id in active_ids:
                snapshot = self._build_chart_metric_snapshot(chart_id)
                self._database_metric_snapshots[chart_id] = snapshot
                self._apply_snapshot_delta(cache, snapshot, 1)
            self._database_metrics_cache = cache
            self._database_metrics_dirty_ids.clear()
            return
        cache = self._database_metrics_cache
        active_ids = {row[0] for row in self._chart_rows}
        removed_ids = set(cache["chart_ids"]) - active_ids
        for removed_id in removed_ids:
            previous = self._database_metric_snapshots.pop(removed_id, None)
            if previous:
                self._apply_snapshot_delta(cache, previous, -1)
        changed_ids = (self._database_metrics_dirty_ids | (active_ids - set(cache["chart_ids"]))) & active_ids
        for chart_id in changed_ids:
            previous = self._database_metric_snapshots.get(chart_id)
            if previous:
                self._apply_snapshot_delta(cache, previous, -1)
            self._chart_cache.pop(chart_id, None)
            current = self._build_chart_metric_snapshot(chart_id)
            self._database_metric_snapshots[chart_id] = current
            self._apply_snapshot_delta(cache, current, 1)
        cache["chart_ids"] = set(active_ids)
        self._database_metrics_dirty_ids.clear()

    def _iter_database_metric_snapshots(self, chart_ids: list[int] | set[int] | None = None):
        ids = list(chart_ids) if chart_ids is not None else list((self._database_metrics_cache or {}).get("chart_ids", set()))
        for chart_id in ids:
            snapshot = self._database_metric_snapshots.get(chart_id)
            if snapshot is None:
                self._chart_cache.pop(chart_id, None)
                snapshot = self._build_chart_metric_snapshot(chart_id)
                self._database_metric_snapshots[chart_id] = snapshot
            yield snapshot

    def _build_snapshot_totals(self, chart_ids: list[int] | set[int]) -> dict[str, Any]:
        totals = self._empty_database_metrics_cache()
        for snapshot in self._iter_database_metric_snapshots(chart_ids):
            self._apply_snapshot_delta(totals, snapshot, 1)
        return totals

    def _filter_chart_ids_for_placeholders(
        self,
        chart_ids: list[int] | set[int],
        *,
        include_placeholders: bool,
    ) -> list[int]:
        if include_placeholders:
            return list(chart_ids)
        filtered_ids: list[int] = []
        for chart_id in chart_ids:
            snapshot = self._database_metric_snapshots.get(chart_id)
            if snapshot is None:
                self._chart_cache.pop(chart_id, None)
                snapshot = self._build_chart_metric_snapshot(chart_id)
                self._database_metric_snapshots[chart_id] = snapshot
            if not snapshot.get("is_placeholder", False):
                filtered_ids.append(chart_id)
        return filtered_ids

    def _update_selection_header(self) -> None:
        selected_count = len(self.list_widget.selectedItems())
        shown_count = self.list_widget.count()
        total_count = self._active_collection_total_count

        if selected_count == 0 and self._has_active_chart_filters():
            self.charts_header_label.setText(
                f"Charts found: {shown_count} of {total_count}"
            )
        else:
            self.charts_header_label.setText(
                f"Charts Selected: {selected_count} of {total_count}"
            )
        self.charts_header_label.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)

    def _has_active_chart_filters(self) -> bool:
        selected_sentiments = {
            name
            for name, checkbox in self.sentiment_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_sentiments = {
            name
            for name, checkbox in self.sentiment_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_sentiment = (
            "none" in self.sentiment_filter_checkboxes
            and self.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_sentiment = (
            "none" in self.sentiment_filter_checkboxes
            and self.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
        )
        selected_relationship_types = {
            name
            for name, checkbox in self.relationship_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_relationship_types = {
            name
            for name, checkbox in self.relationship_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_relationship = (
            "none" in self.relationship_filter_checkboxes
            and self.relationship_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_relationship = (
            "none" in self.relationship_filter_checkboxes
            and self.relationship_filter_checkboxes["none"].mode()
            == QuadStateSlider.MODE_FALSE
        )
        selected_genders = {
            name
            for name, checkbox in self.gender_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_genders = {
            name
            for name, checkbox in self.gender_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_gender = (
            "none" in self.gender_filter_checkboxes
            and self.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_gender = (
            "none" in self.gender_filter_checkboxes
            and self.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
        )
        selected_guessed_gender = str(self.gender_guessed_filter_combo.currentData() or "")
        selected_chart_types = {
            source
            for source, checkbox in self.chart_type_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE
        }
        excluded_chart_types = {
            source
            for source, checkbox in self.chart_type_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE
        }
        selected_generations = {
            name
            for name, checkbox in self.generation_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE
        }
        excluded_generations = {
            name
            for name, checkbox in self.generation_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE
        }

        active_body_filters = [
            filters
            for filters in self._search_body_filters
            if filters["sign"].currentText() != "Any"
            or filters["house"].currentText() != "Any"
        ]
        active_aspect_filters = [
            filters
            for filters in self._aspect_filters
            if str(filters["planet_1"].currentData()) != "Any"
            or str(filters["aspect"].currentData()) != "Any"
            or str(filters["planet_2"].currentData()) != "Any"
        ]
        active_dominant_sign_filters = [
            filters
            for filters in self._dominant_sign_filters
            if filters["sign"].currentText() != "Any"
        ]
        active_dominant_planet_filters = [
            filters
            for filters in self._dominant_planet_filters
            if str(filters["planet"].currentData()) != "Any"
        ]
        active_dominant_mode_filters = [
            filters
            for filters in self._dominant_mode_filters
            if filters["mode"].currentData() != "Any"
        ]
        dominant_element_primary = (
            self._dominant_element_primary_combo.currentData()
            if self._dominant_element_primary_combo is not None
            else "Any"
        )
        dominant_element_secondary = (
            self._dominant_element_secondary_combo.currentData()
            if self._dominant_element_secondary_combo is not None
            else "Any"
        )
        year_first_encountered_earliest = (
            self._year_first_encountered_earliest_input.text().strip()
            if self._year_first_encountered_earliest_input is not None
            else ""
        )
        year_first_encountered_latest = (
            self._year_first_encountered_latest_input.text().strip()
            if self._year_first_encountered_latest_input is not None
            else ""
        )
        year_first_encountered_blank_state = (
            self._year_first_encountered_blank_checkbox.mode()
            if self._year_first_encountered_blank_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        guessed_gender_filter = str(self.gender_guessed_filter_combo.currentData() or "")
        positive_sentiment_intensity_min = self._parse_integer_filter_text(
            self._positive_sentiment_intensity_min_input.text()
            if self._positive_sentiment_intensity_min_input is not None
            else ""
        )
        positive_sentiment_intensity_max = self._parse_integer_filter_text(
            self._positive_sentiment_intensity_max_input.text()
            if self._positive_sentiment_intensity_max_input is not None
            else ""
        )
        negative_sentiment_intensity_min = self._parse_integer_filter_text(
            self._negative_sentiment_intensity_min_input.text()
            if self._negative_sentiment_intensity_min_input is not None
            else ""
        )
        negative_sentiment_intensity_max = self._parse_integer_filter_text(
            self._negative_sentiment_intensity_max_input.text()
            if self._negative_sentiment_intensity_max_input is not None
            else ""
        )
        familiarity_min = self._parse_integer_filter_text(
            self._familiarity_min_input.text()
            if self._familiarity_min_input is not None
            else ""
        )
        familiarity_max = self._parse_integer_filter_text(
            self._familiarity_max_input.text()
            if self._familiarity_max_input is not None
            else ""
        )
        alignment_score_min = self._parse_signed_integer_filter_text(
            self._alignment_score_min_input.text()
            if self._alignment_score_min_input is not None
            else ""
        )
        alignment_score_max = self._parse_signed_integer_filter_text(
            self._alignment_score_max_input.text()
            if self._alignment_score_max_input is not None
            else ""
        )
        include_blank_alignment = bool(
            self._alignment_score_blank_checkbox is not None
            and self._alignment_score_blank_checkbox.isChecked()
        )
        notes_comments_mode = (
            self._notes_comments_filter_checkbox.mode()
            if self._notes_comments_filter_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        notes_comments_text = (
            self._notes_comments_filter_input.text().strip()
            if self._notes_comments_filter_input is not None
            else ""
        )
        notes_source_mode = (
            self._notes_source_filter_checkbox.mode()
            if self._notes_source_filter_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        notes_source_text = (
            self._notes_source_filter_input.text().strip()
            if self._notes_source_filter_input is not None
            else ""
        )
        notes_comments_active = (
            notes_comments_mode != QuadStateSlider.MODE_EMPTY and bool(notes_comments_text)
        )
        notes_source_active = (
            notes_source_mode != QuadStateSlider.MODE_EMPTY and bool(notes_source_text)
        )

        return not (
            self.incomplete_birthdate_checkbox.mode() == QuadStateSlider.MODE_EMPTY
            and self.birthtime_unknown_checkbox.mode() == QuadStateSlider.MODE_EMPTY
            and self.retconned_checkbox.mode() == QuadStateSlider.MODE_EMPTY
            and (self.living_checkbox is None or self.living_checkbox.mode() == QuadStateSlider.MODE_EMPTY)
            and not selected_sentiments
            and not excluded_sentiments
            and not include_none_sentiment
            and not exclude_none_sentiment
            and not selected_relationship_types
            and not excluded_relationship_types
            and not include_none_relationship
            and not exclude_none_relationship
            and not selected_genders
            and not excluded_genders
            and not include_none_gender
            and not exclude_none_gender
            and not active_body_filters
            and not active_aspect_filters
            and not active_dominant_sign_filters
            and not active_dominant_planet_filters
            and not active_dominant_mode_filters
            and dominant_element_primary == "Any"
            and not year_first_encountered_earliest
            and not year_first_encountered_latest
            and year_first_encountered_blank_state == QuadStateSlider.MODE_EMPTY
            and dominant_element_secondary == "Any"
            and not selected_chart_types
            and not excluded_chart_types
            and not selected_generations
            and not excluded_generations
            and self.species_filter_combo.currentData() == "Any"
            and not guessed_gender_filter
            and positive_sentiment_intensity_min is None
            and positive_sentiment_intensity_max is None
            and negative_sentiment_intensity_min is None
            and negative_sentiment_intensity_max is None
            and familiarity_min is None
            and familiarity_max is None
            and alignment_score_min is None
            and alignment_score_max is None
            and not include_blank_alignment
            and not notes_comments_active
            and not notes_source_active
            and not self.search_text_input.text().strip()
            and (
                not hasattr(self, "search_tags_input")
                or not self.search_tags_input.text().strip()
            )
            and (
                not hasattr(self, "search_untagged_checkbox")
                or not self.search_untagged_checkbox.isChecked()
            )
        )

    def _update_sentiment_tally(
        self,
        show_progress: bool = False,
        force_full_refresh: bool = False,
        changed_ids: set[int] | None = None,
        *,
        update_database_metrics: bool = True,
        update_similarities: bool = True,
        sections_to_refresh: set[str] | None = None,
    ) -> None:
        if changed_ids:
            self._database_metrics_dirty_ids.update(changed_ids)

        self._update_selection_header()
        if not update_database_metrics and not update_similarities:
            return

        left_panel_scrollbar = None
        left_panel_scroll_value = None
        if update_database_metrics and self.selection_sentiment_panel_scroll is not None:
            left_panel_scrollbar = self.selection_sentiment_panel_scroll.verticalScrollBar()
            left_panel_scroll_value = left_panel_scrollbar.value()

        similarities_scrollbar = None
        similarities_scroll_value = None
        if update_similarities and self.similarities_analysis_panel_scroll is not None:
            similarities_scrollbar = self.similarities_analysis_panel_scroll.verticalScrollBar()
            similarities_scroll_value = similarities_scrollbar.value()

        selected_items = self.list_widget.selectedItems()
        chart_ids = self._selected_chart_ids(selected_items)

        labels = list(SENTIMENT_OPTIONS)
        negative_start = (
            SENTIMENT_OPTIONS.index("can't trust")
            if "can't trust" in SENTIMENT_OPTIONS
            else len(labels)
        )
        positive_labels = labels[:negative_start]
        negative_labels = labels[negative_start:]

        def _should_refresh_database_metric_section(section_key: str) -> bool:
            if (
                self._database_metrics_baseline_mode == "gen_pop"
                and section_key in GEN_POP_HIDDEN_DATABASE_METRIC_SECTIONS
            ):
                return False
            if not self._is_database_metrics_section_expanded(section_key):
                return False
            if sections_to_refresh is None:
                return True
            return section_key in sections_to_refresh

        if update_database_metrics:
            try:
                self._refresh_database_metrics_cache(force_full_refresh=force_full_refresh)
            except Exception:
                if show_progress:
                    traceback.print_exc()
                self._database_metrics_cache = self._empty_database_metrics_cache()

            database_cache = self._database_metrics_cache or self._empty_database_metrics_cache()
            selection_cache = self._build_snapshot_totals(chart_ids)
            include_sentiment_placeholders = bool(
                getattr(self, "include_placeholder_sentiment_checkbox", None)
                and self.include_placeholder_sentiment_checkbox.isChecked()
            )
            include_relationship_placeholders = bool(
                getattr(self, "include_placeholder_relationship_checkbox", None)
                and self.include_placeholder_relationship_checkbox.isChecked()
            )
            sentiment_selection_ids = self._filter_chart_ids_for_placeholders(
                chart_ids,
                include_placeholders=include_sentiment_placeholders,
            )
            sentiment_database_ids = self._filter_chart_ids_for_placeholders(
                database_cache["chart_ids"],
                include_placeholders=include_sentiment_placeholders,
            )
            relationship_selection_ids = self._filter_chart_ids_for_placeholders(
                chart_ids,
                include_placeholders=include_relationship_placeholders,
            )
            relationship_database_ids = self._filter_chart_ids_for_placeholders(
                database_cache["chart_ids"],
                include_placeholders=include_relationship_placeholders,
            )
            sentiment_selection_cache = self._build_snapshot_totals(sentiment_selection_ids)
            sentiment_database_cache = self._build_snapshot_totals(sentiment_database_ids)
            relationship_selection_cache = self._build_snapshot_totals(
                relationship_selection_ids
            )
            relationship_database_cache = self._build_snapshot_totals(
                relationship_database_ids
            )

            birth_sections_expanded = any(
                _should_refresh_database_metric_section(section_key)
                for section_key in ("birth_time", "birth_month", "birthplace")
            )
            age_section_expanded = _should_refresh_database_metric_section("age")
            birth_selection_analytics = (
                self._collect_birth_analytics(chart_ids)
                if birth_sections_expanded
                else {
                    "birth_minutes": [],
                    "mean_minutes": 0.0,
                    "median_minutes": 0.0,
                    "mode_hour_minutes": 0.0,
                    "birth_month_counts": {},
                    "birth_date_counts": {},
                    "city_counts": {},
                    "country_counts": {},
                    "us_state_counts": {},
                }
            )
            birth_database_analytics = (
                self._collect_birth_analytics(database_cache["chart_ids"])
                if birth_sections_expanded
                else {
                    "birth_minutes": [],
                    "mean_minutes": 0.0,
                    "median_minutes": 0.0,
                    "mode_hour_minutes": 0.0,
                    "birth_month_counts": {},
                    "birth_date_counts": {},
                    "city_counts": {},
                    "country_counts": {},
                    "us_state_counts": {},
                }
            )
            age_selection_analytics = (
                self._collect_age_analytics(chart_ids)
                if age_section_expanded
                else {
                    "age_bracket_counts": {},
                    "known_duration_counts": {},
                }
            )
            age_database_analytics = (
                self._collect_age_analytics(database_cache["chart_ids"])
                if age_section_expanded
                else {
                    "age_bracket_counts": {},
                    "known_duration_counts": {},
                }
            )
            
        if update_database_metrics:
            loaded_charts = int(selection_cache["loaded_charts"])
            database_loaded_charts = int(database_cache["loaded_charts"])
            self._update_dominant_factors_subheader(use_selection_scope=loaded_charts > 0)
            self._update_cumulativedom_factors_subheader(use_selection_scope=loaded_charts > 0)
            sentiment_loaded_charts = int(sentiment_selection_cache["loaded_charts"])
            sentiment_database_loaded_charts = int(
                sentiment_database_cache["loaded_charts"]
            )
            relationship_loaded_charts = int(
                relationship_selection_cache["loaded_charts"]
            )
            selection_positive_count = int(sentiment_selection_cache["positive_count"])
            selection_negative_count = int(sentiment_selection_cache["negative_count"])
            database_positive_count = int(sentiment_database_cache["positive_count"])
            database_negative_count = int(sentiment_database_cache["negative_count"])

            selection_averages = {
                label: (
                    sentiment_selection_cache["sentiment_totals"][label]
                    / sentiment_loaded_charts
                    if sentiment_loaded_charts
                    else 0
                )
                for label in SENTIMENT_OPTIONS
            }
            database_averages = {
                label: (
                    sentiment_database_cache["sentiment_totals"][label]
                    / sentiment_database_loaded_charts
                    if sentiment_database_loaded_charts
                    else 0
                )
                for label in SENTIMENT_OPTIONS
            }

            selection_signs = {
                sign: (selection_cache["sign_totals"][sign] / selection_cache["sign_total_count"] if selection_cache["sign_total_count"] else 0)
                for sign in ZODIAC_NAMES
            }
            database_signs = {
                sign: (database_cache["sign_totals"][sign] / database_cache["sign_total_count"] if database_cache["sign_total_count"] else 0)
                for sign in ZODIAC_NAMES
            }

            sign_distribution_mode = self._sign_distribution_mode
            selection_mode_count = selection_cache["position_sign_count_by_body"].get(sign_distribution_mode, 0.0)
            database_mode_count = database_cache["position_sign_count_by_body"].get(sign_distribution_mode, 0.0)
            selection_position_signs = {
                sign: (
                    selection_cache["position_sign_totals_by_body"][sign_distribution_mode][sign] / selection_mode_count
                    if selection_mode_count
                    else 0
                )
                for sign in ZODIAC_NAMES
            }
            baseline_total_charts = loaded_charts if loaded_charts > 0 else database_loaded_charts
            if self._database_metrics_baseline_mode == "gen_pop":
                gen_pop_norms_by_body = self._gen_pop_planet_sign_norms_for_database_size(
                    baseline_total_charts,
                )
                database_position_signs = {
                    sign: float(gen_pop_norms_by_body.get(sign_distribution_mode, {}).get(sign, 0.0))
                    for sign in ZODIAC_NAMES
                }
                baseline_position_sign_counts = {
                    sign: database_position_signs[sign] * float(baseline_total_charts)
                    for sign in ZODIAC_NAMES
                }
            else:
                database_position_signs = {
                    sign: (
                        database_cache["position_sign_totals_by_body"][sign_distribution_mode][sign] / database_mode_count
                        if database_mode_count
                        else 0
                    )
                    for sign in ZODIAC_NAMES
                }
                baseline_position_sign_counts = {
                    sign: float(database_cache["position_sign_totals_by_body"][sign_distribution_mode][sign])
                    for sign in ZODIAC_NAMES
                }

            selection_top3_dominant_signs = {
                sign: (
                    selection_cache["dominant_sign_frequency_totals"][sign] / loaded_charts
                    if loaded_charts
                    else 0
                )
                for sign in ZODIAC_NAMES
            }
            database_top3_dominant_signs = {
                sign: (
                    database_cache["dominant_sign_frequency_totals"][sign]
                    / database_loaded_charts
                    if database_loaded_charts
                    else 0
                )
                for sign in ZODIAC_NAMES
            }
            selection_dominant_signs = {
                sign: (selection_cache["dominant_sign_totals"][sign] / selection_cache["dominant_sign_total_weight"] if selection_cache["dominant_sign_total_weight"] else 0)
                for sign in ZODIAC_NAMES
            }
            database_dominant_signs = {
                sign: (database_cache["dominant_sign_totals"][sign] / database_cache["dominant_sign_total_weight"] if database_cache["dominant_sign_total_weight"] else 0)
                for sign in ZODIAC_NAMES
            }
            dominant_planet_labels = list(selection_cache["dominant_planet_totals"].keys())
            selection_top3_dominant_planets = {
                body: (
                    selection_cache["dominant_planet_totals"][body]
                    / selection_cache["dominant_planet_total_weight"]
                    if selection_cache["dominant_planet_total_weight"]
                    else 0
                )
                for body in dominant_planet_labels
            }
            database_top3_dominant_planets = {
                body: (
                    database_cache["dominant_planet_totals"][body]
                    / database_cache["dominant_planet_total_weight"]
                    if database_cache["dominant_planet_total_weight"]
                    else 0
                )
                for body in dominant_planet_labels
            }
            selection_dominant_planets = {
                body: (
                    selection_cache["dominant_planet_weight_totals"][body]
                    / selection_cache["dominant_planet_weight_total_weight"]
                    if selection_cache["dominant_planet_weight_total_weight"]
                    else 0
                )
                for body in dominant_planet_labels
            }
            database_dominant_planets = {
                body: (
                    database_cache["dominant_planet_weight_totals"][body]
                    / database_cache["dominant_planet_weight_total_weight"]
                    if database_cache["dominant_planet_weight_total_weight"]
                    else 0
                )
                for body in dominant_planet_labels
            }
            dominant_house_labels = [str(house_num) for house_num in range(1, 13)]
            selection_top3_dominant_houses = {
                str(house_num): (
                    selection_cache["dominant_house_totals"][house_num]
                    / selection_cache["dominant_house_total_weight"]
                    if selection_cache["dominant_house_total_weight"]
                    else 0
                )
                for house_num in range(1, 13)
            }
            database_top3_dominant_houses = {
                str(house_num): (
                    database_cache["dominant_house_totals"][house_num]
                    / database_cache["dominant_house_total_weight"]
                    if database_cache["dominant_house_total_weight"]
                    else 0
                )
                for house_num in range(1, 13)
            }
            selection_dominant_houses = {
                str(house_num): (
                    selection_cache["dominant_house_weight_totals"][house_num]
                    / selection_cache["dominant_house_weight_total_weight"]
                    if selection_cache["dominant_house_weight_total_weight"]
                    else 0
                )
                for house_num in range(1, 13)
            }
            database_dominant_houses = {
                str(house_num): (
                    database_cache["dominant_house_weight_totals"][house_num]
                    / database_cache["dominant_house_weight_total_weight"]
                    if database_cache["dominant_house_weight_total_weight"]
                    else 0
                )
                for house_num in range(1, 13)
            }
            cumulative_sign_labels = sorted(
                list(ZODIAC_NAMES),
                key=lambda sign: (
                    -database_dominant_signs.get(sign, 0),
                    -selection_dominant_signs.get(sign, 0),
                    sign,
                ),
            )
            cumulative_planet_labels = sorted(
                list(dominant_planet_labels),
                key=lambda body: (
                    -database_dominant_planets.get(body, 0),
                    -selection_dominant_planets.get(body, 0),
                    body,
                ),
            )
            cumulative_house_labels = sorted(
                list(dominant_house_labels),
                key=lambda house: (
                    -database_dominant_houses.get(house, 0),
                    -selection_dominant_houses.get(house, 0),
                    int(house),
                ),
            )

            selection_relationships = {
                relationship: (
                    relationship_selection_cache["relationship_totals"][relationship]
                    / relationship_selection_cache["relationship_total_count"]
                    if relationship_selection_cache["relationship_total_count"]
                    else 0
                )
                for relationship in RELATION_TYPE
            }
            database_relationships = {
                relationship: (
                    relationship_database_cache["relationship_totals"][relationship]
                    / relationship_database_cache["relationship_total_count"]
                    if relationship_database_cache["relationship_total_count"]
                    else 0
                )
                for relationship in RELATION_TYPE
            }

            species_mode = self._species_distribution_mode

            selection_social_scores = [
                float(snapshot.get("social_score", 0.0))
                for snapshot in self._iter_database_metric_snapshots(chart_ids)
            ]
            database_social_scores = [
                float(snapshot.get("social_score", 0.0))
                for snapshot in self._iter_database_metric_snapshots(database_cache["chart_ids"])
            ]
            selection_alignment_scores = [
                float(snapshot.get("alignment_score", 0.0))
                for snapshot in self._iter_database_metric_snapshots(chart_ids)
            ]
            database_alignment_scores = [
                float(snapshot.get("alignment_score", 0.0))
                for snapshot in self._iter_database_metric_snapshots(database_cache["chart_ids"])
            ]
            selection_social_total = float(sum(selection_social_scores))
            database_social_total = float(sum(database_social_scores))
            selection_alignment_total = float(sum(selection_alignment_scores))
            database_alignment_total = float(sum(database_alignment_scores))
            selection_social_average = (
                selection_social_total / loaded_charts if loaded_charts else 0.0
            )
            database_social_average = (
                database_social_total / database_loaded_charts
                if database_loaded_charts
                else 0.0
            )
            selection_alignment_average = (
                selection_alignment_total / loaded_charts if loaded_charts else 0.0
            )
            database_alignment_average = (
                database_alignment_total / database_loaded_charts
                if database_loaded_charts
                else 0.0
            )
            selection_social_median = (
                float(statistics.median(selection_social_scores))
                if selection_social_scores
                else 0.0
            )
            database_social_median = (
                float(statistics.median(database_social_scores))
                if database_social_scores
                else 0.0
            )
            selection_alignment_median = (
                float(statistics.median(selection_alignment_scores))
                if selection_alignment_scores
                else 0.0
            )
            database_alignment_median = (
                float(statistics.median(database_alignment_scores))
                if database_alignment_scores
                else 0.0
            )
            selection_species = {
                species: (selection_cache["species_totals_by_mode"][species_mode][species] / selection_cache["species_total_count_by_mode"][species_mode] if selection_cache["species_total_count_by_mode"][species_mode] else 0)
                for species in SPECIES_FAMILIES
            }
            database_species = {
                species: (database_cache["species_totals_by_mode"][species_mode][species] / database_cache["species_total_count_by_mode"][species_mode] if database_cache["species_total_count_by_mode"][species_mode] else 0)
                for species in SPECIES_FAMILIES
            }

            try:
                positive_total_label = "POSITIVE TOTAL"
                negative_total_label = "NEGATIVE TOTAL"
                positive_total_selection = (
                    selection_positive_count / sentiment_loaded_charts
                    if sentiment_loaded_charts
                    else 0
                )
                negative_total_selection = (
                    selection_negative_count / sentiment_loaded_charts
                    if sentiment_loaded_charts
                    else 0
                )
                positive_total_database = (
                    database_positive_count / sentiment_database_loaded_charts
                    if sentiment_database_loaded_charts
                    else 0
                )
                negative_total_database = (
                    database_negative_count / sentiment_database_loaded_charts
                    if sentiment_database_loaded_charts
                    else 0
                )
                display_labels = (
                    positive_labels
                    + [positive_total_label]
                    + negative_labels
                    + [negative_total_label]
                )
                selection_values = (
                    [selection_averages[label] for label in positive_labels]
                    + [positive_total_selection]
                    + [selection_averages[label] for label in negative_labels]
                    + [negative_total_selection]
                )
                database_values = (
                    [database_averages[label] for label in positive_labels]
                    + [positive_total_database]
                    + [database_averages[label] for label in negative_labels]
                    + [negative_total_database]
                )
                database_counts = (
                    [
                        sentiment_database_cache["sentiment_totals"][label]
                        for label in positive_labels
                    ]
                    + [database_positive_count]
                    + [
                        sentiment_database_cache["sentiment_totals"][label]
                        for label in negative_labels
                    ]
                    + [database_negative_count]
                )
                selection_counts = (
                    [
                        sentiment_selection_cache["sentiment_totals"][label]
                        for label in positive_labels
                    ]
                    + [selection_positive_count]
                    + [
                        sentiment_selection_cache["sentiment_totals"][label]
                        for label in negative_labels
                    ]
                    + [selection_negative_count]
                )
                if _should_refresh_database_metric_section("sentiment_prevalence"):
                    sentiment_canvas = self._build_sentiment_chart(
                        display_labels=display_labels,
                        selection_values=selection_values,
                        database_values=database_values,
                        selection_counts=selection_counts,
                        database_counts=database_counts,
                        loaded_charts=sentiment_loaded_charts,
                        positive_labels=positive_labels,
                        negative_labels=negative_labels,
                        positive_total_label=positive_total_label,
                        negative_total_label=negative_total_label,
                    )
                    self._clear_layout(self.sentiment_chart_layout)
                    self.sentiment_chart_layout.addWidget(
                        sentiment_canvas,
                        0,
                        Qt.AlignHCenter,
                    )
                self._analysis_chart_export_rows["sentiment_prevalence"] = (
                    self._build_analysis_export_rows(
                        labels=display_labels,
                        selection_values=selection_values,
                        database_values=database_values,
                        selection_counts=selection_counts,
                        database_counts=database_counts,
                        loaded_charts=sentiment_loaded_charts,
                    )
                )
            except Exception as exc:
                logger.exception("Failed to render sentiment prevalence section: %s", exc)
                self._analysis_chart_export_rows["sentiment_prevalence"] = []
                if _should_refresh_database_metric_section("sentiment_prevalence"):
                    self._clear_layout(self.sentiment_chart_layout)
                    self.sentiment_chart_layout.addWidget(
                        self._build_text_analysis_widget([
                            "Unable to render Sentiment Prevalence.",
                            f"Error: {exc}",
                        ]),
                        0,
                        Qt.AlignTop,
                    )

            if _should_refresh_database_metric_section("relationship_prevalence"):
                relationship_canvas = self._build_relationship_distribution_chart(
                    selection_relationships=selection_relationships,
                    database_relationships=database_relationships,
                    selection_relationship_counts=relationship_selection_cache[
                        "relationship_totals"
                    ],
                    database_relationship_counts=relationship_database_cache[
                        "relationship_totals"
                    ],
                    loaded_charts=relationship_loaded_charts,
                )
                self._clear_layout(self.relationship_chart_layout)
                self.relationship_chart_layout.addWidget(
                    relationship_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            self._analysis_chart_export_rows["relationship_prevalence"] = (
                self._build_analysis_export_rows(
                    labels=list(RELATION_TYPE),
                    selection_values=[
                        selection_relationships[relationship]
                        for relationship in RELATION_TYPE
                    ],
                    database_values=[
                        database_relationships[relationship]
                        for relationship in RELATION_TYPE
                    ],
                    selection_counts=[
                        relationship_selection_cache["relationship_totals"][relationship]
                        for relationship in RELATION_TYPE
                    ],
                    database_counts=[
                        relationship_database_cache["relationship_totals"][relationship]
                        for relationship in RELATION_TYPE
                    ],
                    loaded_charts=relationship_loaded_charts,
                )
            )

            social_score_labels = [
                "Median",
                "Avg",
            ]
            social_score_selection_values = [
                selection_social_median,
                selection_social_average,
            ]
            social_score_database_values = [
                database_social_median,
                database_social_average,
            ]
            social_score_selection_counts = [loaded_charts] * len(social_score_labels)
            social_score_database_counts = [database_loaded_charts] * len(social_score_labels)

            if _should_refresh_database_metric_section("social_score_summary"):
                social_score_canvas = self._build_social_score_summary_chart(
                    labels=social_score_labels,
                    selection_values=social_score_selection_values,
                    database_values=social_score_database_values,
                    loaded_charts=loaded_charts,
                )
                self._clear_layout(self.social_score_summary_chart_layout)
                self.social_score_summary_chart_layout.addWidget(
                    social_score_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            self._analysis_chart_export_rows["social_score_summary"] = (
                self._build_analysis_export_rows(
                    labels=social_score_labels,
                    selection_values=social_score_selection_values,
                    database_values=social_score_database_values,
                    selection_counts=social_score_selection_counts,
                    database_counts=social_score_database_counts,
                    loaded_charts=loaded_charts,
                )
            )

            alignment_labels = [
                "Median",
                "Avg",
                "Cumulative",
            ]
            alignment_selection_values = [
                selection_alignment_median,
                selection_alignment_average,
                selection_alignment_total,
            ]
            alignment_database_values = [
                database_alignment_median,
                database_alignment_average,
                database_alignment_total,
            ]
            alignment_selection_counts = [loaded_charts] * len(alignment_labels)
            alignment_database_counts = [database_loaded_charts] * len(alignment_labels)
            if _should_refresh_database_metric_section("alignment_summary"):
                alignment_summary_canvas = self._build_social_score_summary_chart(
                    labels=alignment_labels[:2],
                    selection_values=alignment_selection_values[:2],
                    database_values=alignment_database_values[:2],
                    loaded_charts=loaded_charts,
                    color_resolver=alignment_score_to_rgb,
                )
                self._clear_layout(self.alignment_summary_chart_layout)
                self.alignment_summary_chart_layout.addWidget(
                    alignment_summary_canvas,
                    0,
                    Qt.AlignHCenter,
                )
                alignment_cumulative_canvas = self._build_alignment_cumulative_chart(
                    selection_cumulative=selection_alignment_total,
                    selection_average=selection_alignment_average,
                    database_average=database_alignment_average,
                    loaded_charts=loaded_charts,
                )
                self._clear_layout(self.alignment_cumulative_chart_layout)
                self.alignment_cumulative_chart_layout.addWidget(
                    alignment_cumulative_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            self._analysis_chart_export_rows["alignment_summary"] = (
                self._build_analysis_export_rows(
                    labels=alignment_labels,
                    selection_values=alignment_selection_values,
                    database_values=alignment_database_values,
                    selection_counts=alignment_selection_counts,
                    database_counts=alignment_database_counts,
                    loaded_charts=loaded_charts,
                )
            )

            if _should_refresh_database_metric_section("planetary_sign_prevalence"):
                effective_loaded_charts = (
                    loaded_charts
                    if self._database_metrics_baseline_mode != "gen_pop" or loaded_charts > 0
                    else 0
                )
                position_selection_signs = (
                    selection_position_signs
                    if loaded_charts > 0
                    else database_position_signs
                )
                position_selection_counts = (
                    selection_cache["position_sign_totals_by_body"][sign_distribution_mode]
                    if loaded_charts > 0
                    else baseline_position_sign_counts
                )
                position_sign_canvas = self._build_sign_distribution_chart(
                    selection_signs=position_selection_signs,
                    database_signs=database_position_signs,
                    selection_sign_counts=position_selection_counts,
                    database_sign_counts=baseline_position_sign_counts,
                    loaded_charts=effective_loaded_charts,
                )
                self._clear_layout(self.position_sign_distribution_chart_layout)
                self.position_sign_distribution_chart_layout.addWidget(
                    position_sign_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            export_selection_values = (
                [selection_position_signs[sign] for sign in ZODIAC_NAMES]
                if loaded_charts > 0
                else [database_position_signs[sign] for sign in ZODIAC_NAMES]
            )
            export_selection_counts = (
                [
                    selection_cache["position_sign_totals_by_body"][sign_distribution_mode][sign]
                    for sign in ZODIAC_NAMES
                ]
                if loaded_charts > 0
                else [
                    baseline_position_sign_counts[sign]
                    for sign in ZODIAC_NAMES
                ]
            )
            self._analysis_chart_export_rows["planetary_sign_prevalence"] = (
                self._build_analysis_export_rows(
                    labels=list(ZODIAC_NAMES),
                    selection_values=export_selection_values,
                    database_values=[database_position_signs[sign] for sign in ZODIAC_NAMES],
                    selection_counts=export_selection_counts,
                    database_counts=[
                        baseline_position_sign_counts[sign]
                        for sign in ZODIAC_NAMES
                    ],
                    loaded_charts=loaded_charts,
                )
            )

            if _should_refresh_database_metric_section("dominant_signs"):
                dominant_mode = self._dominant_factors_mode
                if dominant_mode == "top3_planets":
                    dominant_sign_canvas = self._build_dominant_planet_chart(
                        selection_planets=selection_top3_dominant_planets,
                        database_planets=database_top3_dominant_planets,
                        selection_planet_counts=selection_cache["dominant_planet_totals"],
                        database_planet_counts=database_cache["dominant_planet_totals"],
                        loaded_charts=loaded_charts,
                    )
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=dominant_planet_labels,
                        selection_values=[selection_top3_dominant_planets[label] for label in dominant_planet_labels],
                        database_values=[database_top3_dominant_planets[label] for label in dominant_planet_labels],
                        selection_counts=[int(selection_cache["dominant_planet_totals"][label]) for label in dominant_planet_labels],
                        database_counts=[int(database_cache["dominant_planet_totals"][label]) for label in dominant_planet_labels],
                        loaded_charts=loaded_charts,
                    )
                elif dominant_mode == "top3_houses":
                    dominant_sign_canvas = self._build_dominant_house_chart(
                        selection_houses=selection_top3_dominant_houses,
                        database_houses=database_top3_dominant_houses,
                        selection_house_counts={str(num): selection_cache["dominant_house_totals"][num] for num in range(1, 13)},
                        database_house_counts={str(num): database_cache["dominant_house_totals"][num] for num in range(1, 13)},
                        loaded_charts=loaded_charts,
                    )
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=dominant_house_labels,
                        selection_values=[selection_top3_dominant_houses[label] for label in dominant_house_labels],
                        database_values=[database_top3_dominant_houses[label] for label in dominant_house_labels],
                        selection_counts=[int(selection_cache["dominant_house_totals"][int(label)]) for label in dominant_house_labels],
                        database_counts=[int(database_cache["dominant_house_totals"][int(label)]) for label in dominant_house_labels],
                        loaded_charts=loaded_charts,
                    )
                elif dominant_mode == "top3_signs":
                    dominant_sign_canvas = self._build_dominant_sign_chart(
                        selection_signs=selection_top3_dominant_signs,
                        database_signs=database_top3_dominant_signs,
                        selection_sign_counts=selection_cache["dominant_sign_frequency_totals"],
                        database_sign_counts=database_cache["dominant_sign_frequency_totals"],
                        loaded_charts=loaded_charts,
                    )
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=list(ZODIAC_NAMES),
                        selection_values=[selection_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        database_values=[database_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        selection_counts=[selection_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        database_counts=[database_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        loaded_charts=loaded_charts,
                    )
                else:
                    dominant_sign_canvas = self._build_dominant_sign_chart(
                        selection_signs=selection_top3_dominant_signs,
                        database_signs=database_top3_dominant_signs,
                        selection_sign_counts=selection_cache["dominant_sign_frequency_totals"],
                        database_sign_counts=database_cache["dominant_sign_frequency_totals"],
                        loaded_charts=loaded_charts,
                    )
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=list(ZODIAC_NAMES),
                        selection_values=[selection_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        database_values=[database_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        selection_counts=[selection_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        database_counts=[database_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        loaded_charts=loaded_charts,
                    )
                self._clear_layout(self.dominant_sign_chart_layout)
                self.dominant_sign_chart_layout.addWidget(
                    dominant_sign_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            if not _should_refresh_database_metric_section("dominant_signs"):
                dominant_mode = self._dominant_factors_mode
                if dominant_mode == "top3_planets":
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=dominant_planet_labels,
                        selection_values=[selection_top3_dominant_planets[label] for label in dominant_planet_labels],
                        database_values=[database_top3_dominant_planets[label] for label in dominant_planet_labels],
                        selection_counts=[int(selection_cache["dominant_planet_totals"][label]) for label in dominant_planet_labels],
                        database_counts=[int(database_cache["dominant_planet_totals"][label]) for label in dominant_planet_labels],
                        loaded_charts=loaded_charts,
                    )
                elif dominant_mode == "top3_houses":
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=dominant_house_labels,
                        selection_values=[selection_top3_dominant_houses[label] for label in dominant_house_labels],
                        database_values=[database_top3_dominant_houses[label] for label in dominant_house_labels],
                        selection_counts=[int(selection_cache["dominant_house_totals"][int(label)]) for label in dominant_house_labels],
                        database_counts=[int(database_cache["dominant_house_totals"][int(label)]) for label in dominant_house_labels],
                        loaded_charts=loaded_charts,
                    )
                elif dominant_mode == "top3_signs":
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=list(ZODIAC_NAMES),
                        selection_values=[selection_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        database_values=[database_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        selection_counts=[selection_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        database_counts=[database_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        loaded_charts=loaded_charts,
                    )
                else:
                    self._analysis_chart_export_rows["dominant_signs"] = self._build_analysis_export_rows(
                        labels=list(ZODIAC_NAMES),
                        selection_values=[selection_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        database_values=[database_top3_dominant_signs[sign] for sign in ZODIAC_NAMES],
                        selection_counts=[selection_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        database_counts=[database_cache["dominant_sign_frequency_totals"][sign] for sign in ZODIAC_NAMES],
                        loaded_charts=loaded_charts,
                    )

            if _should_refresh_database_metric_section("cumulativedom_factors"):
                cumulativedom_mode = self._cumulativedom_factors_mode
                if cumulativedom_mode == "cumulative_planets":
                    cumulativedom_sign_canvas = self._build_dominant_planet_chart(
                        selection_planets=selection_dominant_planets,
                        database_planets=database_dominant_planets,
                        selection_planet_counts=selection_cache["dominant_planet_weight_totals"],
                        database_planet_counts=database_cache["dominant_planet_weight_totals"],
                        loaded_charts=loaded_charts,
                        labels=cumulative_planet_labels,
                    )
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_planet_labels,
                        selection_values=[selection_dominant_planets[label] for label in cumulative_planet_labels],
                        database_values=[database_dominant_planets[label] for label in cumulative_planet_labels],
                        selection_counts=[selection_cache["dominant_planet_weight_totals"][label] for label in cumulative_planet_labels],
                        database_counts=[database_cache["dominant_planet_weight_totals"][label] for label in cumulative_planet_labels],
                        loaded_charts=loaded_charts,
                    )
                elif cumulativedom_mode == "cumulative_houses":
                    cumulativedom_sign_canvas = self._build_dominant_house_chart(
                        selection_houses=selection_dominant_houses,
                        database_houses=database_dominant_houses,
                        selection_house_counts={str(num): selection_cache["dominant_house_weight_totals"][num] for num in range(1, 13)},
                        database_house_counts={str(num): database_cache["dominant_house_weight_totals"][num] for num in range(1, 13)},
                        loaded_charts=loaded_charts,
                        labels=cumulative_house_labels,
                    )
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_house_labels,
                        selection_values=[selection_dominant_houses[label] for label in cumulative_house_labels],
                        database_values=[database_dominant_houses[label] for label in cumulative_house_labels],
                        selection_counts=[selection_cache["dominant_house_weight_totals"][int(label)] for label in cumulative_house_labels],
                        database_counts=[database_cache["dominant_house_weight_totals"][int(label)] for label in cumulative_house_labels],
                        loaded_charts=loaded_charts,
                    )
                else:
                    cumulativedom_sign_canvas = self._build_dominant_sign_chart(
                        selection_signs=selection_dominant_signs,
                        database_signs=database_dominant_signs,
                        selection_sign_counts=selection_cache["dominant_sign_totals"],
                        database_sign_counts=database_cache["dominant_sign_totals"],
                        loaded_charts=loaded_charts,
                        sign_labels=cumulative_sign_labels,
                    )
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_sign_labels,
                        selection_values=[selection_dominant_signs[sign] for sign in cumulative_sign_labels],
                        database_values=[database_dominant_signs[sign] for sign in cumulative_sign_labels],
                        selection_counts=[selection_cache["dominant_sign_totals"][sign] for sign in cumulative_sign_labels],
                        database_counts=[database_cache["dominant_sign_totals"][sign] for sign in cumulative_sign_labels],
                        loaded_charts=loaded_charts,
                    )
                self._clear_layout(self.cumulativedom_sign_chart_layout)
                self.cumulativedom_sign_chart_layout.addWidget(
                    cumulativedom_sign_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            if not _should_refresh_database_metric_section("cumulativedom_factors"):
                cumulativedom_mode = self._cumulativedom_factors_mode
                if cumulativedom_mode == "cumulative_planets":
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_planet_labels,
                        selection_values=[selection_dominant_planets[label] for label in cumulative_planet_labels],
                        database_values=[database_dominant_planets[label] for label in cumulative_planet_labels],
                        selection_counts=[selection_cache["dominant_planet_weight_totals"][label] for label in cumulative_planet_labels],
                        database_counts=[database_cache["dominant_planet_weight_totals"][label] for label in cumulative_planet_labels],
                        loaded_charts=loaded_charts,
                    )
                elif cumulativedom_mode == "cumulative_houses":
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_house_labels,
                        selection_values=[selection_dominant_houses[label] for label in cumulative_house_labels],
                        database_values=[database_dominant_houses[label] for label in cumulative_house_labels],
                        selection_counts=[selection_cache["dominant_house_weight_totals"][int(label)] for label in cumulative_house_labels],
                        database_counts=[database_cache["dominant_house_weight_totals"][int(label)] for label in cumulative_house_labels],
                        loaded_charts=loaded_charts,
                    )
                else:
                    self._analysis_chart_export_rows["cumulativedom_factors"] = self._build_analysis_export_rows(
                        labels=cumulative_sign_labels,
                        selection_values=[selection_dominant_signs[sign] for sign in cumulative_sign_labels],
                        database_values=[database_dominant_signs[sign] for sign in cumulative_sign_labels],
                        selection_counts=[selection_cache["dominant_sign_totals"][sign] for sign in cumulative_sign_labels],
                        database_counts=[database_cache["dominant_sign_totals"][sign] for sign in cumulative_sign_labels],
                        loaded_charts=loaded_charts,
                    )

            prevalence_mode = self._prevalence_mode
            if prevalence_mode == "house_prevalence":
                prevalence_labels = [str(num) for num in range(1, 13)]
                selection_prevalence = {
                    label: (
                        selection_cache["house_prevalence_totals"][int(label)]
                        / selection_cache["house_prevalence_total_count"]
                        if selection_cache["house_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                database_prevalence = {
                    label: (
                        database_cache["house_prevalence_totals"][int(label)]
                        / database_cache["house_prevalence_total_count"]
                        if database_cache["house_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                selection_prevalence_counts = {
                    label: selection_cache["house_prevalence_totals"][int(label)]
                    for label in prevalence_labels
                }
                database_prevalence_counts = {
                    label: database_cache["house_prevalence_totals"][int(label)]
                    for label in prevalence_labels
                }
            elif prevalence_mode == "elemental_prevalence":
                prevalence_labels = ["Fire", "Earth", "Air", "Water"]
                selection_prevalence = {
                    label: (
                        selection_cache["element_prevalence_totals"][label]
                        / selection_cache["element_prevalence_total_count"]
                        if selection_cache["element_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                database_prevalence = {
                    label: (
                        database_cache["element_prevalence_totals"][label]
                        / database_cache["element_prevalence_total_count"]
                        if database_cache["element_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                selection_prevalence_counts = {
                    label: selection_cache["element_prevalence_totals"][label]
                    for label in prevalence_labels
                }
                database_prevalence_counts = {
                    label: database_cache["element_prevalence_totals"][label]
                    for label in prevalence_labels
                }
            elif prevalence_mode == "nakshatra_prevalence":
                prevalence_labels = [name for name, *_ in NAKSHATRA_RANGES]
                selection_prevalence = {
                    label: (
                        selection_cache["nakshatra_prevalence_totals"][label]
                        / selection_cache["nakshatra_prevalence_total_count"]
                        if selection_cache["nakshatra_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                database_prevalence = {
                    label: (
                        database_cache["nakshatra_prevalence_totals"][label]
                        / database_cache["nakshatra_prevalence_total_count"]
                        if database_cache["nakshatra_prevalence_total_count"]
                        else 0.0
                    )
                    for label in prevalence_labels
                }
                selection_prevalence_counts = {
                    label: selection_cache["nakshatra_prevalence_totals"][label]
                    for label in prevalence_labels
                }
                database_prevalence_counts = {
                    label: database_cache["nakshatra_prevalence_totals"][label]
                    for label in prevalence_labels
                }
            else:
                prevalence_labels = list(ZODIAC_NAMES)
                selection_prevalence = {label: selection_signs[label] for label in prevalence_labels}
                database_prevalence = {label: database_signs[label] for label in prevalence_labels}
                selection_prevalence_counts = {
                    label: selection_cache["sign_totals"][label] for label in prevalence_labels
                }
                database_prevalence_counts = {
                    label: database_cache["sign_totals"][label] for label in prevalence_labels
                }

            if _should_refresh_database_metric_section("sign_prevalence"):
                if prevalence_mode == "sign_prevalence":
                    sign_canvas = self._build_sign_distribution_chart(
                        selection_signs=selection_prevalence,
                        database_signs=database_prevalence,
                        selection_sign_counts=selection_prevalence_counts,
                        database_sign_counts=database_prevalence_counts,
                        loaded_charts=loaded_charts,
                    )
                else:
                    sign_canvas = self._build_dominant_planet_chart(
                        selection_planets=selection_prevalence,
                        database_planets=database_prevalence,
                        selection_planet_counts=selection_prevalence_counts,
                        database_planet_counts=database_prevalence_counts,
                        loaded_charts=loaded_charts,
                    )
                self._clear_layout(self.sign_distribution_chart_layout)
                self.sign_distribution_chart_layout.addWidget(
                    sign_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            self._analysis_chart_export_rows["sign_prevalence"] = (
                self._build_analysis_export_rows(
                    labels=prevalence_labels,
                    selection_values=[selection_prevalence[label] for label in prevalence_labels],
                    database_values=[database_prevalence[label] for label in prevalence_labels],
                    selection_counts=[selection_prevalence_counts[label] for label in prevalence_labels],
                    database_counts=[database_prevalence_counts[label] for label in prevalence_labels],
                    loaded_charts=loaded_charts,
                )
            )

            if _should_refresh_database_metric_section("species_distribution"):
                species_canvas = self._build_species_distribution_chart(
                    selection_species=selection_species,
                    database_species=database_species,
                    selection_species_counts=selection_cache["species_totals_by_mode"][
                        species_mode
                    ],
                    database_species_counts=database_cache["species_totals_by_mode"][
                        species_mode
                    ],
                    loaded_charts=loaded_charts,
                )
                self._clear_layout(self.species_distribution_chart_layout)
                self.species_distribution_chart_layout.addWidget(
                    species_canvas,
                    0,
                    Qt.AlignHCenter,
                )
            self._analysis_chart_export_rows["species_distribution"] = (
                self._build_analysis_export_rows(
                    labels=list(SPECIES_FAMILIES),
                    selection_values=[
                        selection_species[species] for species in SPECIES_FAMILIES
                    ],
                    database_values=[database_species[species] for species in SPECIES_FAMILIES],
                    selection_counts=[
                        selection_cache["species_totals_by_mode"][species_mode][species]
                        for species in SPECIES_FAMILIES
                    ],
                    database_counts=[
                        database_cache["species_totals_by_mode"][species_mode][species]
                        for species in SPECIES_FAMILIES
                    ],
                    loaded_charts=loaded_charts,
                )
            )

            gender_mode = self._gender_mode
            if gender_mode == "actual_gender":
                selection_gender_counts_raw: Counter[str] = Counter()
                for chart_id in chart_ids:
                    chart = self._get_chart_for_filter(chart_id)
                    if chart is None:
                        continue
                    raw_gender = self._normalize_gender_value(getattr(chart, "gender", None))
                    selection_gender_counts_raw[raw_gender if raw_gender else "blank"] += 1

                if self._database_metrics_baseline_mode == "gen_pop":
                    gender_labels = ["F", "M"]
                    selection_gender_counts = {
                        label: int(selection_gender_counts_raw.get(label, 0))
                        for label in gender_labels
                    }
                    baseline_sample_size = loaded_charts if loaded_charts > 0 else database_loaded_charts
                    gen_pop_counts = gen_pop_actual_gender_counts(baseline_sample_size)
                    database_gender_counts = {label: int(gen_pop_counts.get(label, 0)) for label in gender_labels}
                else:
                    database_gender_counts_raw: Counter[str] = Counter()
                    for chart_id in database_cache["chart_ids"]:
                        chart = self._get_chart_for_filter(chart_id)
                        if chart is None:
                            continue
                        raw_gender = self._normalize_gender_value(getattr(chart, "gender", None))
                        database_gender_counts_raw[raw_gender if raw_gender else "blank"] += 1

                    known_labels = ["blank", *GENDER_OPTIONS]
                    custom_labels = sorted(
                        label
                        for label in {
                            *selection_gender_counts_raw.keys(),
                            *database_gender_counts_raw.keys(),
                        }
                        - set(known_labels)
                        if selection_gender_counts_raw.get(label, 0) > 0
                        or database_gender_counts_raw.get(label, 0) > 0
                    )
                    # Keep the full known gender assignment set visible (even at zero)
                    # so this chart stays in sync with Chart View / Search dropdowns.
                    gender_labels = [*known_labels, *custom_labels]
                    selection_gender_counts = {label: int(selection_gender_counts_raw.get(label, 0)) for label in gender_labels}
                    database_gender_counts = {label: int(database_gender_counts_raw.get(label, 0)) for label in gender_labels}
            else:
                gender_labels = ["Masculine", "Androgynous", "Feminine"]
                selection_gender_counts = {label: 0 for label in gender_labels}
                database_gender_counts = {label: 0 for label in gender_labels}
                for chart_id in chart_ids:
                    chart = self._get_chart_for_filter(chart_id)
                    if chart is None:
                        continue
                    if gender_mode == "guessed_weight":
                        guessed = self._classify_guessed_gender(_calculate_gender_weight_score(chart))
                    else:
                        guessed = self._classify_guessed_gender(_calculate_gender_prevalence_score(chart))
                    if guessed == "masculine":
                        selection_gender_counts["Masculine"] += 1
                    elif guessed == "feminine":
                        selection_gender_counts["Feminine"] += 1
                    else:
                        selection_gender_counts["Androgynous"] += 1
                for chart_id in database_cache["chart_ids"]:
                    chart = self._get_chart_for_filter(chart_id)
                    if chart is None:
                        continue
                    if gender_mode == "guessed_weight":
                        guessed = self._classify_guessed_gender(_calculate_gender_weight_score(chart))
                    else:
                        guessed = self._classify_guessed_gender(_calculate_gender_prevalence_score(chart))
                    if guessed == "masculine":
                        database_gender_counts["Masculine"] += 1
                    elif guessed == "feminine":
                        database_gender_counts["Feminine"] += 1
                    else:
                        database_gender_counts["Androgynous"] += 1

            selection_gender_total = sum(selection_gender_counts.values())
            database_gender_total = sum(database_gender_counts.values())
            selection_gender_distribution = {
                label: (
                    selection_gender_counts[label] / selection_gender_total
                    if selection_gender_total
                    else 0.0
                )
                for label in gender_labels
            }
            database_gender_distribution = {
                label: (
                    database_gender_counts[label] / database_gender_total
                    if database_gender_total
                    else 0.0
                )
                for label in gender_labels
            }
            if _should_refresh_database_metric_section("gender"):
                gender_canvas = self._build_gender_distribution_chart(
                    labels=gender_labels,
                    selection_values=selection_gender_distribution,
                    database_values=database_gender_distribution,
                    selection_counts=selection_gender_counts,
                    database_counts=database_gender_counts,
                    loaded_charts=loaded_charts,
                )
                self._clear_layout(self.gender_chart_layout)
                self.gender_chart_layout.addWidget(gender_canvas, 0, Qt.AlignHCenter)
            self._analysis_chart_export_rows["gender"] = self._build_analysis_export_rows(
                labels=gender_labels,
                selection_values=[selection_gender_distribution[label] for label in gender_labels],
                database_values=[database_gender_distribution[label] for label in gender_labels],
                selection_counts=[selection_gender_counts[label] for label in gender_labels],
                database_counts=[database_gender_counts[label] for label in gender_labels],
                loaded_charts=loaded_charts,
            )

            birth_time_mode = self._birth_time_mode
            birth_time_label_by_mode = {
                "mean": "Mean Birth Time",
                "mode_hour": "Mode Birth Time (rounded hour)",
                "median": "Median Birth Time",
            }
            selection_birth_time = {
                "mean": float(birth_selection_analytics["mean_minutes"]),
                "mode_hour": float(birth_selection_analytics["mode_hour_minutes"]),
                "median": float(birth_selection_analytics["median_minutes"]),
            }
            database_birth_time = {
                "mean": float(birth_database_analytics["mean_minutes"]),
                "mode_hour": float(birth_database_analytics["mode_hour_minutes"]),
                "median": float(birth_database_analytics["median_minutes"]),
            }
            if _should_refresh_database_metric_section("birth_time"):
                birth_time_canvas = self._build_single_metric_chart(
                    label=birth_time_label_by_mode.get(birth_time_mode, "Birth Time"),
                    selection_value=selection_birth_time.get(birth_time_mode, 0.0),
                    database_value=database_birth_time.get(birth_time_mode, 0.0),
                    loaded_charts=loaded_charts,
                )
                self._clear_layout(self.birth_time_chart_layout)
                self.birth_time_chart_layout.addWidget(birth_time_canvas, 0, Qt.AlignHCenter)
            self._analysis_chart_export_rows["birth_time"] = [
                (
                    birth_time_label_by_mode.get(birth_time_mode, "Birth Time"),
                    selection_birth_time.get(birth_time_mode, 0.0) if loaded_charts else database_birth_time.get(birth_time_mode, 0.0),
                    database_birth_time.get(birth_time_mode, 0.0),
                    (selection_birth_time.get(birth_time_mode, 0.0) if loaded_charts else database_birth_time.get(birth_time_mode, 0.0)) - database_birth_time.get(birth_time_mode, 0.0),
                    len(birth_selection_analytics["birth_minutes"]) if loaded_charts else len(birth_database_analytics["birth_minutes"]),
                    len(birth_database_analytics["birth_minutes"]),
                    (float(len(birth_selection_analytics["birth_minutes"])) / float(len(birth_database_analytics["birth_minutes"]))) if loaded_charts and len(birth_database_analytics["birth_minutes"]) else 1.0 if len(birth_database_analytics["birth_minutes"]) else 0.0,
                )
            ]

            age_mode = self._age_mode
            age_axis_label = "Age" if age_mode == "age_distribution" else "Time Known"
            if age_mode == "age_distribution":
                ordered_bracket_labels = [label for label, _min_age, _max_age in AGE_BRACKETS]
                age_selection_counts = {
                    label: int(age_selection_analytics["age_bracket_counts"].get(label, 0))
                    for label in ordered_bracket_labels
                }
                age_database_counts = {
                    label: int(age_database_analytics["age_bracket_counts"].get(label, 0))
                    for label in ordered_bracket_labels
                }
                age_labels = [
                    label
                    for label in ordered_bracket_labels
                    if (age_selection_counts.get(label, 0) > 0 if loaded_charts else age_database_counts.get(label, 0) > 0)
                ]
            else:
                age_selection_counts = {
                    str(int(key)): int(value)
                    for key, value in age_selection_analytics["known_duration_counts"].items()
                    if int(value) > 0
                }
                age_database_counts = {
                    str(int(key)): int(value)
                    for key, value in age_database_analytics["known_duration_counts"].items()
                    if int(value) > 0
                }
                age_labels = sorted(
                    age_selection_counts.keys() if loaded_charts else age_database_counts.keys(),
                    key=int,
                )
            if _should_refresh_database_metric_section("age"):
                self._clear_layout(self.age_chart_layout)
                if age_labels:
                    age_canvas = self._build_count_distribution_chart(
                        labels=age_labels,
                        selection_counts=[age_selection_counts.get(label, 0) for label in age_labels],
                        database_counts=[age_database_counts.get(label, 0) for label in age_labels],
                        loaded_charts=loaded_charts,
                        auto_height=True,
                    )
                    self.age_chart_layout.addWidget(age_canvas, 0, Qt.AlignHCenter)
                else:
                    self.age_chart_layout.addWidget(self._build_text_analysis_widget(["None available"]), 0, Qt.AlignTop)
            self._analysis_chart_export_rows["age"] = self._build_analysis_export_rows(
                labels=[f"{label} years" if age_mode == "time_known_distribution" else label for label in age_labels],
                selection_values=[float(age_selection_counts.get(label, 0)) for label in age_labels],
                database_values=[float(age_database_counts.get(label, 0)) for label in age_labels],
                selection_counts=[int(age_selection_counts.get(label, 0)) for label in age_labels],
                database_counts=[int(age_database_counts.get(label, 0)) for label in age_labels],
                loaded_charts=loaded_charts,
            ) if age_labels else [
                (
                    f"No {age_axis_label.lower()} data",
                    0.0,
                    0.0,
                    0.0,
                    0,
                    0,
                    0.0,
                )
            ]

            birth_month_mode = self._birth_month_mode
            month_labels = [calendar.month_name[month] for month in range(1, 13)]
            month_selection_counts = [int(birth_selection_analytics["birth_month_counts"].get(month, 0)) for month in range(1, 13)]
            month_database_counts = [int(birth_database_analytics["birth_month_counts"].get(month, 0)) for month in range(1, 13)]
            if birth_month_mode == "month_distribution":
                if _should_refresh_database_metric_section("birth_month"):
                    month_canvas = self._build_count_distribution_chart(
                        labels=month_labels,
                        selection_counts=month_selection_counts,
                        database_counts=month_database_counts,
                        loaded_charts=loaded_charts,
                    )
                    self._clear_layout(self.birth_month_chart_layout)
                    self.birth_month_chart_layout.addWidget(month_canvas, 0, Qt.AlignHCenter)
                self._analysis_chart_export_rows["birth_month"] = self._build_analysis_export_rows(
                    labels=month_labels,
                    selection_values=[float(value) for value in month_selection_counts],
                    database_values=[float(value) for value in month_database_counts],
                    selection_counts=month_selection_counts,
                    database_counts=month_database_counts,
                    loaded_charts=loaded_charts,
                )
            else:
                selection_date_counts = {
                    key: int(value)
                    for key, value in birth_selection_analytics["birth_date_counts"].items()
                    if int(value) > 1
                }
                database_date_counts = {
                    key: int(value)
                    for key, value in birth_database_analytics["birth_date_counts"].items()
                    if int(value) > 1
                }
                top_date_labels = [
                    item[0]
                    for item in sorted(
                        selection_date_counts.items() if loaded_charts else database_date_counts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )[:6]
                ]
                if _should_refresh_database_metric_section("birth_month"):
                    self._clear_layout(self.birth_month_chart_layout)
                    if top_date_labels:
                        date_canvas = self._build_count_distribution_chart(
                            labels=top_date_labels,
                            selection_counts=[selection_date_counts.get(label, 0) for label in top_date_labels],
                            database_counts=[database_date_counts.get(label, 0) for label in top_date_labels],
                            loaded_charts=loaded_charts,
                        )
                        self.birth_month_chart_layout.addWidget(date_canvas, 0, Qt.AlignHCenter)
                    else:
                        self.birth_month_chart_layout.addWidget(
                            self._build_text_analysis_widget(["None available"]),
                            0,
                            Qt.AlignTop,
                        )
                self._analysis_chart_export_rows["birth_month"] = (
                    self._build_analysis_export_rows(
                        labels=top_date_labels,
                        selection_values=[float(selection_date_counts.get(label, 0)) for label in top_date_labels],
                        database_values=[float(database_date_counts.get(label, 0)) for label in top_date_labels],
                        selection_counts=[int(selection_date_counts.get(label, 0)) for label in top_date_labels],
                        database_counts=[int(database_date_counts.get(label, 0)) for label in top_date_labels],
                        loaded_charts=loaded_charts,
                    )
                    if top_date_labels
                    else []
                )

            birthplace_mode = self._birthplace_mode
            selection_city_counts = {
                key: int(value)
                for key, value in birth_selection_analytics["city_counts"].items()
                if int(value) > 1
            }
            database_city_counts = {
                key: int(value)
                for key, value in birth_database_analytics["city_counts"].items()
                if int(value) > 1
            }
            selection_country_counts = {
                key: int(value)
                for key, value in birth_selection_analytics["country_counts"].items()
                if int(value) > 0
            }
            database_country_counts = {
                key: int(value)
                for key, value in birth_database_analytics["country_counts"].items()
                if int(value) > 0
            }
            selection_state_counts = {
                key: int(value)
                for key, value in birth_selection_analytics["us_state_counts"].items()
                if int(value) > 0
            }
            database_state_counts = {
                key: int(value)
                for key, value in birth_database_analytics["us_state_counts"].items()
                if int(value) > 0
            }

            if _should_refresh_database_metric_section("birthplace"):
                self._clear_layout(self.birthplace_chart_layout)
                if birthplace_mode == "countries":
                    country_labels = [
                        item[0]
                        for item in sorted(
                            selection_country_counts.items() if loaded_charts else database_country_counts.items(),
                            key=lambda item: (-item[1], item[0]),
                        )
                    ]
                    if country_labels:
                        country_canvas = self._build_count_distribution_chart(
                            labels=country_labels,
                            selection_counts=[selection_country_counts.get(label, 0) for label in country_labels],
                            database_counts=[database_country_counts.get(label, 0) for label in country_labels],
                            loaded_charts=loaded_charts,
                            auto_height=True,
                        )
                        self.birthplace_chart_layout.addWidget(country_canvas, 0, Qt.AlignHCenter)
                    else:
                        self.birthplace_chart_layout.addWidget(self._build_text_analysis_widget(["None available"]), 0, Qt.AlignTop)
                else:
                    if birthplace_mode == "towns":
                        source_counts = selection_city_counts if loaded_charts else database_city_counts
                    else:
                        source_counts = selection_state_counts if loaded_charts else database_state_counts
                    top_items = sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))
                    lines: list[str] = []
                    if top_items:
                        lines.extend([f"• {label} ({count})" for label, count in top_items])
                    else:
                        lines.append("None available")
                    self.birthplace_chart_layout.addWidget(self._build_text_analysis_widget(lines), 0, Qt.AlignTop)

            if birthplace_mode == "countries":
                country_labels = [
                    item[0]
                    for item in sorted(
                        selection_country_counts.items() if loaded_charts else database_country_counts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ]
                self._analysis_chart_export_rows["birthplace"] = self._build_analysis_export_rows(
                    labels=country_labels,
                    selection_values=[float(selection_country_counts.get(label, 0)) for label in country_labels],
                    database_values=[float(database_country_counts.get(label, 0)) for label in country_labels],
                    selection_counts=[int(selection_country_counts.get(label, 0)) for label in country_labels],
                    database_counts=[int(database_country_counts.get(label, 0)) for label in country_labels],
                    loaded_charts=loaded_charts,
                )
            elif birthplace_mode == "towns":
                town_labels = [
                    item[0]
                    for item in sorted(
                        selection_city_counts.items() if loaded_charts else database_city_counts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ]
                self._analysis_chart_export_rows["birthplace"] = self._build_analysis_export_rows(
                    labels=town_labels,
                    selection_values=[float(selection_city_counts.get(label, 0)) for label in town_labels],
                    database_values=[float(database_city_counts.get(label, 0)) for label in town_labels],
                    selection_counts=[int(selection_city_counts.get(label, 0)) for label in town_labels],
                    database_counts=[int(database_city_counts.get(label, 0)) for label in town_labels],
                    loaded_charts=loaded_charts,
                )
            else:
                state_labels = [
                    item[0]
                    for item in sorted(
                        selection_state_counts.items() if loaded_charts else database_state_counts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ]
                self._analysis_chart_export_rows["birthplace"] = self._build_analysis_export_rows(
                    labels=state_labels,
                    selection_values=[float(selection_state_counts.get(label, 0)) for label in state_labels],
                    database_values=[float(database_state_counts.get(label, 0)) for label in state_labels],
                    selection_counts=[int(selection_state_counts.get(label, 0)) for label in state_labels],
                    database_counts=[int(database_state_counts.get(label, 0)) for label in state_labels],
                    loaded_charts=loaded_charts,
                )

        if update_similarities:
            self._update_similarities_analysis(chart_ids)
            self._stabilize_left_scroll_panel_layout(self.similarities_analysis_panel_scroll)

        if update_database_metrics:
            self._stabilize_left_scroll_panel_layout(self.selection_sentiment_panel_scroll)

        if left_panel_scrollbar is not None and left_panel_scroll_value is not None:
            self._restore_scrollbar_position(
                left_panel_scrollbar,
                left_panel_scroll_value,
            )
        if similarities_scrollbar is not None and similarities_scroll_value is not None:
            self._restore_scrollbar_position(
                similarities_scrollbar,
                similarities_scroll_value,
            )

    @staticmethod
    def _restore_scrollbar_position(scrollbar, previous_value: int) -> None:
        pending_handler = getattr(scrollbar, "_ephemeraldaddy_restore_handler", None)
        if pending_handler is not None:
            try:
                scrollbar.rangeChanged.disconnect(pending_handler)
            except Exception:
                pass

        pending_timer = getattr(scrollbar, "_ephemeraldaddy_restore_cleanup_timer", None)
        if pending_timer is not None:
            pending_timer.stop()
            pending_timer.deleteLater()

        target_value = max(scrollbar.minimum(), min(previous_value, scrollbar.maximum()))

        def _apply_target() -> None:
            bounded_value = max(scrollbar.minimum(), min(target_value, scrollbar.maximum()))
            scrollbar.setValue(bounded_value)

        def _cleanup_handler() -> None:
            if getattr(scrollbar, "_ephemeraldaddy_restore_handler", None) is not _on_range_changed:
                return
            try:
                scrollbar.rangeChanged.disconnect(_on_range_changed)
            except Exception:
                pass
            scrollbar._ephemeraldaddy_restore_handler = None
            cleanup_timer = getattr(scrollbar, "_ephemeraldaddy_restore_cleanup_timer", None)
            if cleanup_timer is not None:
                cleanup_timer.stop()
                cleanup_timer.deleteLater()
            scrollbar._ephemeraldaddy_restore_cleanup_timer = None

        cleanup_timer = QTimer(scrollbar)
        cleanup_timer.setSingleShot(True)
        cleanup_timer.setInterval(750)
        cleanup_timer.timeout.connect(_cleanup_handler)

        def _on_range_changed(*_) -> None:
            _apply_target()
            cleanup_timer.start()

        scrollbar._ephemeraldaddy_restore_handler = _on_range_changed
        scrollbar._ephemeraldaddy_restore_cleanup_timer = cleanup_timer
        scrollbar.rangeChanged.connect(_on_range_changed)

        _apply_target()
        QTimer.singleShot(0, _apply_target)
        QTimer.singleShot(60, _apply_target)
        QTimer.singleShot(220, _apply_target)
        cleanup_timer.start()

    @staticmethod
    def _stabilize_left_scroll_panel_layout(scroll_area: QScrollArea) -> None:
        panel_widget = scroll_area.widget()
        if panel_widget is None:
            return
        panel_layout = panel_widget.layout()
        if panel_layout is not None:
            panel_layout.activate()
        panel_widget.updateGeometry()

    @staticmethod
    def _wrap_right_panel(panel: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setMinimumWidth(panel.minimumWidth())
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(RIGHT_PANEL_SCROLLBAR_STYLE)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        scroll.setWidget(panel)
        return scroll

    @staticmethod
    def _wrap_left_panel(panel: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setMinimumWidth(panel.minimumWidth())
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(RIGHT_PANEL_SCROLLBAR_STYLE)
        scroll.setWidget(panel)
        return scroll

    def _build_search_panel(self) -> QWidget:
        # Search panel (right sidebar).
        panel = EmojiTiledPanel("🔎", font_size=100, opacity=0.12) #Search panel background
        panel.setMinimumWidth(420)
        layout = QVBoxLayout()
        panel.setLayout(layout)

        def apply_default_dropdown_style(dropdown: QComboBox) -> None:
            dropdown.setStyleSheet(DEFAULT_DROPDOWN_STYLE)

        search_title = QLabel("Database search")
        search_title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(search_title)

        self.search_text_input = QLineEdit()
        self.search_text_input.setPlaceholderText(
            "Search names or birthplaces"
        )
        self.search_text_input.textChanged.connect(self._on_filter_changed)
        self.search_text_input.returnPressed.connect(self._on_filter_changed)
        self.search_text_input.installEventFilter(self)
        layout.addWidget(self.search_text_input)

        astrotheme_row = QHBoxLayout()
        self.astrotheme_search_input = QLineEdit()
        self.astrotheme_search_input.setPlaceholderText(
            "Search Astrotheme.com's public 📚"
        )
        self.astrotheme_search_input.returnPressed.connect(
            self._on_import_astrotheme_from_search_panel
        )
        astrotheme_row.addWidget(self.astrotheme_search_input, 1)
        astrotheme_import_button = QPushButton("Import")
        astrotheme_import_button.clicked.connect(
            self._on_import_astrotheme_from_search_panel
        )
        astrotheme_row.addWidget(astrotheme_import_button)
        layout.addLayout(astrotheme_row)

        tags_search_row = QVBoxLayout()
        tags_search_row.setContentsMargins(0, 0, 0, 0)
        tags_search_row.setSpacing(4)
        self.search_tags_input = QLineEdit()
        self.search_tags_input.setPlaceholderText(
            "Search by tags (comma-separated)"
        )
        self.search_tags_input.textChanged.connect(self._on_search_tags_changed)
        self.search_tags_input.returnPressed.connect(self._on_filter_changed)
        tags_search_row.addWidget(self.search_tags_input)
        self.search_tags_preview_label = QLabel()
        self.search_tags_preview_label.setWordWrap(True)
        self.search_tags_preview_label.setTextFormat(Qt.RichText)
        tags_search_row.addWidget(self.search_tags_preview_label)
        self.search_untagged_checkbox = QCheckBox("untagged")
        self.search_untagged_checkbox.stateChanged.connect(self._on_filter_changed)
        tags_search_row.addWidget(self.search_untagged_checkbox)

        self.search_tags_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.search_tags_toggle,
            title="Tags",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        tags_search_row.addWidget(self.search_tags_toggle)

        self.search_tags_list_widget = QListWidget()
        self.search_tags_list_widget.setSelectionMode(QListWidget.NoSelection)
        self.search_tags_list_widget.setMaximumHeight(180)
        self.search_tags_list_widget.itemClicked.connect(self._on_search_tag_item_clicked)
        self.search_tags_list_widget.setVisible(False)
        self.search_tags_toggle.toggled.connect(self.search_tags_list_widget.setVisible)
        tags_search_row.addWidget(self.search_tags_list_widget)
        layout.addLayout(tags_search_row)

        divider = QFrame()
        divider.setFixedHeight(4)
        divider.setStyleSheet(
            "background-color: #1f1f1f;"
            "border-top: 1px solid #3b3b3b;"
            "border-bottom: 1px solid #0d0d0d;"
        )
        layout.addWidget(divider)

        header_layout = QHBoxLayout()
        title = QLabel("Search Filters")
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        #I removed this button, since there's a "Clear Filters" button on the bottom right now.
        #reset_button = QPushButton("Reset")
        #reset_button.clicked.connect(self._reset_filters)
        #header_layout.addWidget(reset_button)
        layout.addLayout(header_layout)

        def add_collapsible_section(title: str) -> tuple[QWidget, QVBoxLayout]:
            section = QWidget()
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section.setLayout(section_layout)

            toggle = QToolButton()
            configure_collapsible_header_toggle(
                toggle,
                title=title,
                expanded=False,
                style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
            )

            content = QWidget()
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(8, 6, 8, 6)
            content.setLayout(content_layout)
            content.setVisible(False)

            def toggle_content(checked: bool) -> None:
                content.setVisible(checked)
                toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
                content.adjustSize()
                section.adjustSize()
                panel.adjustSize()
                panel.updateGeometry()

            toggle.toggled.connect(toggle_content)

            section_layout.addWidget(toggle)
            section_layout.addWidget(content)
            return section, content_layout

        birth_info_status_section, birth_info_status_layout = add_collapsible_section(
            "Birth Info Status"
        )

        incomplete_birthdate_row = QHBoxLayout()
        self.incomplete_birthdate_checkbox = QuadStateSlider("incomplete birthdate")
        self.incomplete_birthdate_checkbox.modeChanged.connect(self._on_filter_changed)
        incomplete_birthdate_row.addWidget(self.incomplete_birthdate_checkbox)
        incomplete_birthdate_row.addStretch(1)
        birth_info_status_layout.addLayout(incomplete_birthdate_row)

        birth_status_mode_row = QHBoxLayout()
        birth_status_mode_row.addWidget(QLabel("Birth time:"))
        birth_status_mode_row.addStretch(1)
        self.birth_status_filter_and = QRadioButton("AND")
        self.birth_status_filter_or = QRadioButton("OR")
        self.birth_status_filter_group = QButtonGroup(self)
        self.birth_status_filter_group.setExclusive(True)
        self.birth_status_filter_group.addButton(self.birth_status_filter_and)
        self.birth_status_filter_group.addButton(self.birth_status_filter_or)
        self.birth_status_filter_and.setChecked(True)
        self.birth_status_filter_and.toggled.connect(self._on_filter_changed)
        self.birth_status_filter_or.toggled.connect(self._on_filter_changed)
        birth_status_mode_row.addWidget(self.birth_status_filter_and)
        birth_status_mode_row.addWidget(self.birth_status_filter_or)
        birth_info_status_layout.addLayout(birth_status_mode_row)

        birth_filters_row = QHBoxLayout()
        self.birthtime_unknown_checkbox = QuadStateSlider("BT unknown")
        self.birthtime_unknown_checkbox.modeChanged.connect(self._on_filter_changed)
        self.retconned_checkbox = QuadStateSlider("BT retconned")
        self.retconned_checkbox.modeChanged.connect(self._on_filter_changed)
        birth_filters_row.addWidget(self.birthtime_unknown_checkbox)
        birth_filters_row.addWidget(self.retconned_checkbox)
        birth_filters_row.addStretch(1)
        birth_info_status_layout.addLayout(birth_filters_row)
        layout.addWidget(birth_info_status_section)

        mortality_section, mortality_section_layout = add_collapsible_section("Mortality")
        mortality_row = QHBoxLayout()
        self.living_checkbox = QuadStateSlider("living")
        self.living_checkbox.modeChanged.connect(self._on_filter_changed)
        mortality_row.addWidget(self.living_checkbox)
        mortality_row.addStretch(1)
        mortality_section_layout.addLayout(mortality_row)

        generation_divider = QFrame()
        generation_divider.setFrameShape(QFrame.HLine)
        generation_divider.setStyleSheet("color: #2f2f2f;")
        mortality_section_layout.addWidget(generation_divider)

        generation_header = QLabel("Generation")
        generation_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
        mortality_section_layout.addWidget(generation_header)

        generation_layout = QGridLayout()
        generation_layout.setContentsMargins(0, 0, 0, 0)
        self.generation_filter_checkboxes = {}
        generation_rows = (len(GENERATION_FILTER_OPTIONS) + 1) // 2
        for idx, generation_name in enumerate(GENERATION_FILTER_OPTIONS):
            checkbox = QuadStateSlider(generation_name)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.generation_filter_checkboxes[generation_name] = checkbox
            row = idx % generation_rows
            col = idx // generation_rows
            generation_layout.addWidget(checkbox, row, col)
        mortality_section_layout.addLayout(generation_layout)

        layout.addWidget(mortality_section)

        chart_type_section, chart_type_group_layout = add_collapsible_section(
            "Chart Type"
        )
        chart_type_layout = QGridLayout()
        chart_type_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_type_filter_checkboxes = {}
        chart_type_rows = (len(SOURCE_OPTIONS) + 1) // 2
        for idx, (source_label, source_value) in enumerate(SOURCE_OPTIONS):
            checkbox = QuadStateSlider(source_label)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.chart_type_filter_checkboxes[source_value] = checkbox
            row = idx % chart_type_rows
            col = idx // chart_type_rows
            chart_type_layout.addWidget(checkbox, row, col)
        chart_type_group_layout.addLayout(chart_type_layout)
        layout.addWidget(chart_type_section)

        year_first_encountered_section, year_first_encountered_group_layout = add_collapsible_section(
            "Year 1st Encountered"
        )
        year_first_encountered_range_row = QHBoxLayout()
        year_first_encountered_range_row.addWidget(QLabel("Earliest"))
        self._year_first_encountered_earliest_input = QLineEdit()
        self._year_first_encountered_earliest_input.setMaxLength(4)
        self._year_first_encountered_earliest_input.setFixedWidth(56)
        self._year_first_encountered_earliest_input.setPlaceholderText("YYYY")
        self._year_first_encountered_earliest_input.setValidator(
            QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, self)
        )
        self._year_first_encountered_earliest_input.textChanged.connect(self._on_filter_changed)
        year_first_encountered_range_row.addWidget(self._year_first_encountered_earliest_input)
        year_first_encountered_range_row.addSpacing(10)
        year_first_encountered_range_row.addWidget(QLabel("Latest"))
        self._year_first_encountered_latest_input = QLineEdit()
        self._year_first_encountered_latest_input.setMaxLength(4)
        self._year_first_encountered_latest_input.setFixedWidth(56)
        self._year_first_encountered_latest_input.setPlaceholderText("YYYY")
        self._year_first_encountered_latest_input.setValidator(
            QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, self)
        )
        self._year_first_encountered_latest_input.textChanged.connect(self._on_filter_changed)
        year_first_encountered_range_row.addWidget(self._year_first_encountered_latest_input)
        year_first_encountered_range_row.addStretch(1)
        year_first_encountered_group_layout.addLayout(year_first_encountered_range_row)

        year_first_encountered_blank_row = QHBoxLayout()
        self._year_first_encountered_blank_checkbox = QuadStateSlider("blank")
        self._year_first_encountered_blank_checkbox.modeChanged.connect(self._on_filter_changed)
        year_first_encountered_blank_row.addWidget(self._year_first_encountered_blank_checkbox)
        year_first_encountered_blank_row.addStretch(1)
        year_first_encountered_group_layout.addLayout(year_first_encountered_blank_row)
        layout.addWidget(year_first_encountered_section)

        sentiment_section, sentiment_group_layout = add_collapsible_section("Sentiments")

        sentiment_mode_layout = QHBoxLayout()
        sentiment_mode_layout.addWidget(QLabel("Sentiment type"))
        sentiment_mode_layout.addStretch(1)
        self.sentiment_filter_and = QRadioButton("AND")
        self.sentiment_filter_or = QRadioButton("OR")
        self.sentiment_filter_group = QButtonGroup(self)
        self.sentiment_filter_group.setExclusive(True)
        self.sentiment_filter_group.addButton(self.sentiment_filter_and)
        self.sentiment_filter_group.addButton(self.sentiment_filter_or)
        self.sentiment_filter_and.setChecked(True)
        # Use group-level click handling so we only refresh once per selection
        # change and avoid transient states where neither option is checked.
        self.sentiment_filter_group.buttonClicked.connect(self._on_filter_changed)
        sentiment_mode_layout.addWidget(self.sentiment_filter_and)
        sentiment_mode_layout.addWidget(self.sentiment_filter_or)
        sentiment_group_layout.addLayout(sentiment_mode_layout)
        sentiment_layout = QGridLayout()
        sentiment_layout.setContentsMargins(0, 0, 0, 0)
        self.sentiment_filter_checkboxes = {}
        sentiment_rows = (len(SEARCH_SENTIMENT_OPTIONS) + 1) // 2
        for idx, label in enumerate(SEARCH_SENTIMENT_OPTIONS):
            checkbox = QuadStateSlider(label)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.sentiment_filter_checkboxes[label] = checkbox
            row = idx % sentiment_rows
            col = idx // sentiment_rows
            sentiment_layout.addWidget(checkbox, row, col)
        sentiment_group_layout.addLayout(sentiment_layout)

        sentiment_intensity_row = QHBoxLayout()
        sentiment_intensity_row.addWidget(QLabel("💖"))
        self._positive_sentiment_intensity_min_input = QLineEdit()
        self._positive_sentiment_intensity_min_input.setFixedWidth(44)
        self._positive_sentiment_intensity_min_input.setMaxLength(2)
        self._positive_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, self))
        self._positive_sentiment_intensity_min_input.setPlaceholderText("min")
        self._positive_sentiment_intensity_min_input.textChanged.connect(self._on_filter_changed)
        sentiment_intensity_row.addWidget(self._positive_sentiment_intensity_min_input)
        sentiment_intensity_row.addWidget(QLabel("max"))
        self._positive_sentiment_intensity_max_input = QLineEdit()
        self._positive_sentiment_intensity_max_input.setFixedWidth(44)
        self._positive_sentiment_intensity_max_input.setMaxLength(2)
        self._positive_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, self))
        self._positive_sentiment_intensity_max_input.setPlaceholderText("max")
        self._positive_sentiment_intensity_max_input.textChanged.connect(self._on_filter_changed)
        sentiment_intensity_row.addWidget(self._positive_sentiment_intensity_max_input)
        sentiment_intensity_row.addSpacing(10)
        sentiment_intensity_row.addWidget(QLabel("💔"))
        self._negative_sentiment_intensity_min_input = QLineEdit()
        self._negative_sentiment_intensity_min_input.setFixedWidth(44)
        self._negative_sentiment_intensity_min_input.setMaxLength(2)
        self._negative_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, self))
        self._negative_sentiment_intensity_min_input.setPlaceholderText("min")
        self._negative_sentiment_intensity_min_input.textChanged.connect(self._on_filter_changed)
        sentiment_intensity_row.addWidget(self._negative_sentiment_intensity_min_input)
        sentiment_intensity_row.addWidget(QLabel("max"))
        self._negative_sentiment_intensity_max_input = QLineEdit()
        self._negative_sentiment_intensity_max_input.setFixedWidth(44)
        self._negative_sentiment_intensity_max_input.setMaxLength(2)
        self._negative_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, self))
        self._negative_sentiment_intensity_max_input.setPlaceholderText("max")
        self._negative_sentiment_intensity_max_input.textChanged.connect(self._on_filter_changed)
        sentiment_intensity_row.addWidget(self._negative_sentiment_intensity_max_input)
        sentiment_intensity_row.addStretch(1)
        sentiment_group_layout.addLayout(sentiment_intensity_row)

        familiarity_row = QHBoxLayout()
        familiarity_row.addWidget(QLabel("Familiarity"))
        self._familiarity_min_input = QLineEdit()
        self._familiarity_min_input.setFixedWidth(44)
        self._familiarity_min_input.setMaxLength(2)
        self._familiarity_min_input.setValidator(QIntValidator(1, 10, self))
        self._familiarity_min_input.setPlaceholderText("min")
        self._familiarity_min_input.textChanged.connect(self._on_filter_changed)
        familiarity_row.addWidget(self._familiarity_min_input)
        familiarity_row.addWidget(QLabel("max"))
        self._familiarity_max_input = QLineEdit()
        self._familiarity_max_input.setFixedWidth(44)
        self._familiarity_max_input.setMaxLength(2)
        self._familiarity_max_input.setValidator(QIntValidator(1, 10, self))
        self._familiarity_max_input.setPlaceholderText("max")
        self._familiarity_max_input.textChanged.connect(self._on_filter_changed)
        familiarity_row.addWidget(self._familiarity_max_input)
        familiarity_row.addStretch(1)
        sentiment_group_layout.addLayout(familiarity_row)

        layout.addWidget(sentiment_section)

        alignment_section, alignment_group_layout = add_collapsible_section("Alignments")
        alignment_range_row = QHBoxLayout()
        alignment_range_row.addWidget(QLabel("Alignment"))
        self._alignment_score_min_input = QLineEdit()
        self._alignment_score_min_input.setFixedWidth(44)
        self._alignment_score_min_input.setMaxLength(3)
        self._alignment_score_min_input.setValidator(QIntValidator(-10, 10, self))
        self._alignment_score_min_input.setPlaceholderText("min")
        self._alignment_score_min_input.textChanged.connect(self._on_filter_changed)
        alignment_range_row.addWidget(self._alignment_score_min_input)
        alignment_range_row.addWidget(QLabel("max"))
        self._alignment_score_max_input = QLineEdit()
        self._alignment_score_max_input.setFixedWidth(44)
        self._alignment_score_max_input.setMaxLength(3)
        self._alignment_score_max_input.setValidator(QIntValidator(-10, 10, self))
        self._alignment_score_max_input.setPlaceholderText("max")
        self._alignment_score_max_input.textChanged.connect(self._on_filter_changed)
        alignment_range_row.addWidget(self._alignment_score_max_input)
        alignment_range_row.addStretch(1)
        alignment_group_layout.addLayout(alignment_range_row)

        self._alignment_score_blank_checkbox = QCheckBox("no alignment assigned")
        self._alignment_score_blank_checkbox.stateChanged.connect(self._on_filter_changed)
        alignment_group_layout.addWidget(self._alignment_score_blank_checkbox)
        layout.addWidget(alignment_section)

        relationship_section, relationship_group_layout = add_collapsible_section(
            "Relationship Types"
        )
        relationship_mode_layout = QHBoxLayout()
        relationship_mode_layout.addWidget(QLabel("Relationship type"))
        relationship_mode_layout.addStretch(1)
        self.relationship_filter_and = QRadioButton("AND")
        self.relationship_filter_or = QRadioButton("OR")
        self.relationship_filter_group = QButtonGroup(self)
        self.relationship_filter_group.setExclusive(True)
        self.relationship_filter_group.addButton(self.relationship_filter_and)
        self.relationship_filter_group.addButton(self.relationship_filter_or)
        self.relationship_filter_and.setChecked(True)
        self.relationship_filter_group.buttonClicked.connect(self._on_filter_changed)
        relationship_mode_layout.addWidget(self.relationship_filter_and)
        relationship_mode_layout.addWidget(self.relationship_filter_or)
        relationship_group_layout.addLayout(relationship_mode_layout)

        relationship_layout = QGridLayout()
        relationship_layout.setContentsMargins(0, 0, 0, 0)
        self.relationship_filter_checkboxes = {}
        relationship_rows = (len(SEARCH_RELATIONSHIP_TYPE_OPTIONS) + 1) // 2
        for idx, label in enumerate(SEARCH_RELATIONSHIP_TYPE_OPTIONS):
            checkbox = QuadStateSlider(label)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.relationship_filter_checkboxes[label] = checkbox
            row = idx % relationship_rows
            col = idx // relationship_rows
            relationship_layout.addWidget(checkbox, row, col)
        relationship_group_layout.addLayout(relationship_layout)
        layout.addWidget(relationship_section)

        gender_section, gender_group_layout = add_collapsible_section("Gender")
        gender_mode_layout = QHBoxLayout()
        gender_mode_layout.addWidget(QLabel("Gender"))
        gender_mode_layout.addStretch(1)
        self.gender_filter_and = QRadioButton("AND")
        self.gender_filter_or = QRadioButton("OR")
        self.gender_filter_group = QButtonGroup(self)
        self.gender_filter_group.setExclusive(True)
        self.gender_filter_group.addButton(self.gender_filter_and)
        self.gender_filter_group.addButton(self.gender_filter_or)
        self.gender_filter_and.setChecked(True)
        self.gender_filter_group.buttonClicked.connect(self._on_filter_changed)
        gender_mode_layout.addWidget(self.gender_filter_and)
        gender_mode_layout.addWidget(self.gender_filter_or)
        gender_group_layout.addLayout(gender_mode_layout)

        gender_layout = QGridLayout()
        gender_layout.setContentsMargins(0, 0, 0, 0)
        self.gender_filter_checkboxes = {}
        gender_rows = (len(SEARCH_GENDER_OPTIONS) + 1) // 2
        for idx, label in enumerate(SEARCH_GENDER_OPTIONS):
            checkbox_label = "blank" if label == "none" else label
            checkbox = QuadStateSlider(checkbox_label)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.gender_filter_checkboxes[label] = checkbox
            row = idx % gender_rows
            col = idx // gender_rows
            gender_layout.addWidget(checkbox, row, col)
        gender_group_layout.addLayout(gender_layout)

        gender_guessed_layout = QHBoxLayout()
        gender_guessed_layout.addWidget(QLabel("Gender Guessed"))
        self.gender_guessed_filter_combo = QComboBox()
        apply_default_dropdown_style(self.gender_guessed_filter_combo)
        for label, value in SEARCH_GENDER_GUESSED_OPTIONS:
            self.gender_guessed_filter_combo.addItem(label, value)
        self.gender_guessed_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        gender_guessed_layout.addWidget(self.gender_guessed_filter_combo)
        gender_group_layout.addLayout(gender_guessed_layout)

        layout.addWidget(gender_section)

        bodies_section, bodies_group_layout = add_collapsible_section("Bodies/Angles")

        bodies_layout = QFormLayout()
        bodies_layout.setLabelAlignment(Qt.AlignLeft)
        bodies_group_layout.addLayout(bodies_layout)

        for idx in range(len(self._searchable_bodies())):
            filter_row = QWidget()
            filter_layout = QHBoxLayout()
            filter_layout.setContentsMargins(0, 0, 0, 0)
            filter_row.setLayout(filter_layout)

            body_combo = QComboBox()
            apply_default_dropdown_style(body_combo)
            for body_label, body_key in self._searchable_body_options():
                body_combo.addItem(body_label, body_key)
            body_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            sign_combo = QComboBox()
            apply_default_dropdown_style(sign_combo)
            sign_combo.addItem("Any")
            for sign in ZODIAC_NAMES:
                sign_combo.addItem(sign)
            sign_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            house_combo = QComboBox()
            apply_default_dropdown_style(house_combo)
            house_combo.addItem("Any")
            for house_num in range(1, 13):
                house_combo.addItem(str(house_num))
            house_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_layout.addWidget(QLabel("🪐"))
            filter_layout.addWidget(body_combo)
            filter_layout.addWidget(QLabel("🪧"))
            filter_layout.addWidget(sign_combo, 1)
            filter_layout.addWidget(QLabel("🏠"))
            filter_layout.addWidget(house_combo)
            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(filter_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)
            filter_layout.addWidget(filter_and)
            filter_layout.addWidget(filter_or)

            self._search_body_filters.append({
                "body": body_combo,
                "sign": sign_combo,
                "house": house_combo,
                "and": filter_and,
                "or": filter_or,
            })
            bodies_layout.addRow(filter_row)

        layout.addWidget(bodies_section)

        aspect_section, aspect_group_layout = add_collapsible_section("Search by Aspect")

        aspect_layout = QFormLayout()
        aspect_layout.setLabelAlignment(Qt.AlignLeft)
        aspect_group_layout.addLayout(aspect_layout)

        aspect_options = [("Any", "Any")]
        for aspect_name in sorted(ASPECT_DEFS):
            aspect_options.append((aspect_name.replace("_", " ").title(), aspect_name))

        searchable_planets = [
            (label, key)
            for label, key in self._searchable_bodies()
            if key not in {"AS", "IC", "DS", "MC"}
        ]

        for _ in range(3):
            aspect_row = QWidget()
            aspect_row_layout = QHBoxLayout()
            aspect_row_layout.setContentsMargins(0, 0, 0, 0)
            aspect_row.setLayout(aspect_row_layout)

            planet_1_combo = QComboBox()
            apply_default_dropdown_style(planet_1_combo)
            planet_1_combo.addItem("Any", "Any")
            for label, key in searchable_planets:
                planet_1_combo.addItem(label, key)
            planet_1_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            aspect_combo = QComboBox()
            apply_default_dropdown_style(aspect_combo)
            for label, key in aspect_options:
                aspect_combo.addItem(label, key)
            aspect_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            planet_2_combo = QComboBox()
            apply_default_dropdown_style(planet_2_combo)
            planet_2_combo.addItem("Any", "Any")
            for label, key in searchable_planets:
                planet_2_combo.addItem(label, key)
            planet_2_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(aspect_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)

            aspect_row_layout.addWidget(planet_1_combo, 1)
            aspect_row_layout.addWidget(aspect_combo, 1)
            aspect_row_layout.addWidget(planet_2_combo, 1)
            aspect_row_layout.addWidget(filter_and)
            aspect_row_layout.addWidget(filter_or)

            self._aspect_filters.append(
                {
                    "planet_1": planet_1_combo,
                    "aspect": aspect_combo,
                    "planet_2": planet_2_combo,
                    "and": filter_and,
                    "or": filter_or,
                }
            )
            aspect_layout.addRow(aspect_row)

        layout.addWidget(aspect_section)

        dominant_section, dominant_group_layout = add_collapsible_section(
            "Dominant Sign"
        )

        dominant_layout = QFormLayout()
        dominant_layout.setLabelAlignment(Qt.AlignLeft)
        dominant_group_layout.addLayout(dominant_layout)

        for _ in range(3):
            dominant_row = QWidget()
            dominant_row_layout = QHBoxLayout()
            dominant_row_layout.setContentsMargins(0, 0, 0, 0)
            dominant_row.setLayout(dominant_row_layout)

            sign_combo = QComboBox()
            apply_default_dropdown_style(sign_combo)
            sign_combo.addItem("Any")
            for sign in ZODIAC_NAMES:
                sign_combo.addItem(sign)
            sign_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(dominant_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)

            dominant_row_layout.addWidget(QLabel("🪧"))
            dominant_row_layout.addWidget(sign_combo, 1)
            dominant_row_layout.addWidget(filter_and)
            dominant_row_layout.addWidget(filter_or)

            self._dominant_sign_filters.append({
                "sign": sign_combo,
                "and": filter_and,
                "or": filter_or,
            })
            dominant_layout.addRow(dominant_row)

        layout.addWidget(dominant_section)

        dominant_planet_section, dominant_planet_group_layout = add_collapsible_section(
            "Dominant Bodies"
        )

        dominant_planet_layout = QFormLayout()
        dominant_planet_layout.setLabelAlignment(Qt.AlignLeft)
        dominant_planet_group_layout.addLayout(dominant_planet_layout)

        for _ in range(3):
            dominant_planet_row = QWidget()
            dominant_planet_row_layout = QHBoxLayout()
            dominant_planet_row_layout.setContentsMargins(0, 0, 0, 0)
            dominant_planet_row.setLayout(dominant_planet_row_layout)

            planet_combo = QComboBox()
            apply_default_dropdown_style(planet_combo)
            planet_combo.addItem("Any", "Any")
            for planet_label, planet_key in self._searchable_bodies():
                if planet_key in {"AS", "IC", "DS", "MC"}:
                    continue
                planet_combo.addItem(planet_label, planet_key)
            planet_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(dominant_planet_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)

            dominant_planet_row_layout.addWidget(QLabel("🪐"))
            dominant_planet_row_layout.addWidget(planet_combo, 1)
            dominant_planet_row_layout.addWidget(filter_and)
            dominant_planet_row_layout.addWidget(filter_or)

            self._dominant_planet_filters.append({
                "planet": planet_combo,
                "and": filter_and,
                "or": filter_or,
            })
            dominant_planet_layout.addRow(dominant_planet_row)

        layout.addWidget(dominant_planet_section)

        dominant_mode_section, dominant_mode_group_layout = add_collapsible_section(
            "Dominant Mode"
        )

        dominant_mode_layout = QFormLayout()
        dominant_mode_layout.setLabelAlignment(Qt.AlignLeft)
        dominant_mode_group_layout.addLayout(dominant_mode_layout)

        for _ in range(3):
            dominant_mode_row = QWidget()
            dominant_mode_row_layout = QHBoxLayout()
            dominant_mode_row_layout.setContentsMargins(0, 0, 0, 0)
            dominant_mode_row.setLayout(dominant_mode_row_layout)

            mode_combo = QComboBox()
            apply_default_dropdown_style(mode_combo)
            mode_combo.addItem("Any", "Any")
            mode_combo.addItem("Cardinal", "cardinal")
            mode_combo.addItem("Mutable", "mutable")
            mode_combo.addItem("Fixed", "fixed")
            mode_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(dominant_mode_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)

            dominant_mode_row_layout.addWidget(QLabel("⚙️"))
            dominant_mode_row_layout.addWidget(mode_combo, 1)
            dominant_mode_row_layout.addWidget(filter_and)
            dominant_mode_row_layout.addWidget(filter_or)

            self._dominant_mode_filters.append({
                "mode": mode_combo,
                "and": filter_and,
                "or": filter_or,
            })
            dominant_mode_layout.addRow(dominant_mode_row)

        layout.addWidget(dominant_mode_section)

        dominant_element_section, dominant_element_group_layout = add_collapsible_section(
            "Elemental Dominance"
        )
        dominant_element_layout = QFormLayout()
        dominant_element_layout.setLabelAlignment(Qt.AlignLeft)
        dominant_element_group_layout.addLayout(dominant_element_layout)

        primary_row = QHBoxLayout()
        primary_row.addWidget(QLabel("1st"))
        self._dominant_element_primary_combo = QComboBox()
        apply_default_dropdown_style(self._dominant_element_primary_combo)
        self._dominant_element_primary_combo.addItem("Any", "Any")
        for element in ("Fire", "Earth", "Air", "Water"):
            self._dominant_element_primary_combo.addItem(element, element)
        self._dominant_element_primary_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)
        primary_row.addWidget(self._dominant_element_primary_combo, 1)
        dominant_element_layout.addRow(primary_row)

        secondary_row = QHBoxLayout()
        secondary_row.addWidget(QLabel("2nd"))
        self._dominant_element_secondary_combo = QComboBox()
        apply_default_dropdown_style(self._dominant_element_secondary_combo)
        self._dominant_element_secondary_combo.addItem("Any", "Any")
        for element in ("Fire", "Earth", "Air", "Water"):
            self._dominant_element_secondary_combo.addItem(element, element)
        self._dominant_element_secondary_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)
        secondary_row.addWidget(self._dominant_element_secondary_combo, 1)
        dominant_element_layout.addRow(secondary_row)

        layout.addWidget(dominant_element_section)

        dnd_species_section, dnd_species_group_layout = add_collapsible_section(
            "D&&D Species"
        )
        species_filter_row = QHBoxLayout()
        species_filter_row.addWidget(QLabel("Top 3 result"))
        self.species_filter_combo = QComboBox()
        apply_default_dropdown_style(self.species_filter_combo)
        self.species_filter_combo.addItem("Any", "Any")
        for species in SPECIES_FAMILIES:
            self.species_filter_combo.addItem(species, species)
        self.species_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        species_filter_row.addWidget(self.species_filter_combo, 1)
        dnd_species_group_layout.addLayout(species_filter_row)
        layout.addWidget(dnd_species_section)

        notes_section, notes_group_layout = add_collapsible_section("Notes")

        comments_row = QHBoxLayout()
        self._notes_comments_filter_checkbox = QuadStateSlider("Comments")
        self._notes_comments_filter_checkbox.modeChanged.connect(self._on_filter_changed)
        comments_row.addWidget(self._notes_comments_filter_checkbox)
        self._notes_comments_filter_input = QLineEdit()
        self._notes_comments_filter_input.setPlaceholderText("contains text")
        self._notes_comments_filter_input.textChanged.connect(self._on_filter_changed)
        comments_row.addWidget(self._notes_comments_filter_input, 1)
        notes_group_layout.addLayout(comments_row)

        source_row = QHBoxLayout()
        self._notes_source_filter_checkbox = QuadStateSlider("Source")
        self._notes_source_filter_checkbox.modeChanged.connect(self._on_filter_changed)
        source_row.addWidget(self._notes_source_filter_checkbox)
        self._notes_source_filter_input = QLineEdit()
        self._notes_source_filter_input.setPlaceholderText("contains text")
        self._notes_source_filter_input.textChanged.connect(self._on_filter_changed)
        source_row.addWidget(self._notes_source_filter_input, 1)
        notes_group_layout.addLayout(source_row)

        layout.addWidget(notes_section)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        clear_button = QPushButton("Clear filters")
        clear_button.clicked.connect(lambda: self._clear_filters())
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

        layout.addStretch(1)
        return panel

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            active_modal = QApplication.activeModalWidget()
            focus_widget = QApplication.focusWidget()
            if active_modal is None or active_modal is self:
                if focus_widget is self.list_widget or self.list_widget.hasFocus():
                    self._on_delete()
                    return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            active_modal = QApplication.activeModalWidget()
            if active_modal is None or active_modal is self:
                focus_widget = QApplication.focusWidget()
                if isinstance(focus_widget, QAbstractButton):
                    focus_widget.click()
                    return
                if focus_widget is self.transit_location_input:
                    self._on_transit_location_submitted()
                    return
                if focus_widget is self.personal_transit_chart_input:
                    self._on_personal_transit_enter_pressed()
                    return
                if isinstance(focus_widget, QListWidget):
                    item = focus_widget.currentItem()
                    if item is not None and focus_widget is self.list_widget:
                        self._load_chart_from_item(item)
                        return
                if self.list_widget.hasFocus():
                    item = self.list_widget.currentItem()
                    if item is None:
                        selected_items = self.list_widget.selectedItems()
                        item = selected_items[0] if selected_items else None
                    if item is not None:
                        self._load_chart_from_item(item)
                        return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if (
            hasattr(self, "transit_location_input")
            and obj is self.transit_location_input
            and event.type() == QEvent.KeyPress
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
        ):
            self._on_transit_location_submitted()
            return True
        list_widget = getattr(self, "list_widget", None)
        if list_widget is not None and obj is list_widget and event.type() == QEvent.KeyPress:
            if self._handle_list_letter_jump(event):
                return True
        popout_context = self._popout_summary_contexts.get(obj)
        if popout_context is not None:
            if event.type() == QEvent.Resize:
                share_button = popout_context.get("share_button")
                output_widget = popout_context.get("output_widget")
                if isinstance(share_button, QToolButton) and isinstance(output_widget, QPlainTextEdit):
                    self._position_popout_share_button(output_widget, share_button)
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                output_widget = popout_context["output_widget"]
                cursor = output_widget.cursorForPosition(event.position().toPoint())
                custom_handler = popout_context.get("custom_click_handler")
                if callable(custom_handler) and custom_handler(cursor):
                    return True
                parent = self.parent()
                if parent is not None and hasattr(parent, "_handle_summary_info_click"):
                    return parent._handle_summary_info_click(
                        output_widget,
                        cursor,
                        popout_context["position_info_map"],
                        popout_context["aspect_info_map"],
                        popout_context["species_info_map"],
                        popout_context["chart_info_output"],
                        popout_context.get("summary_block_offset", 0),
                    )
            return False
        if (
            obj is self.search_text_input
            and event.type() == QEvent.KeyPress
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
        ):
            self._on_filter_changed()
            return True
        if obj in self._transit_chart_canvases:
            if event.type() == QEvent.Enter:
                obj.setCursor(Qt.PointingHandCursor)
            if (
                event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton
            ):
                chart = self._transit_chart_canvases.get(obj)
                if chart is not None:
                    self._show_transit_chart_popout(chart)
                    return True
        return super().eventFilter(obj, event)

    def _handle_list_letter_jump(self, event) -> bool:
        return _handle_list_letter_jump(self.list_widget, event)

    def _on_import_astrotheme_from_search_panel(self) -> None:
        raw_query = self.astrotheme_search_input.text().strip()
        if not raw_query:
            QMessageBox.information(self, "Astrotheme import", "Enter a name or Astrotheme profile URL.")
            return

        parent = self.parent()
        if parent is None or not hasattr(parent, "_confirm_discard_or_save"):
            QMessageBox.warning(self, "Astrotheme import", "Unable to open chart editor.")
            return

        if not parent._confirm_discard_or_save():
            return

        query = raw_query
        try:
            if raw_query.lower().startswith(("http://", "https://")):
                query = raw_query
            else:
                resolved_url = search_astrotheme_profile_url(raw_query)
                if not resolved_url:
                    raise ValueError("No matching Astrotheme profile was found.")
                query = resolved_url

            profile_data = parse_astrotheme_profile(query)
        except Exception as exc:
            QMessageBox.warning(self, "Astrotheme import", f"Could not load Astrotheme profile:\n{exc}")
            return

        parent._reset_new_chart_form()
        parent.name_edit.setText(profile_data["name"])
        parent._set_birth_date_fields_from_qdate(
            QDate(
                profile_data["birth_year"],
                profile_data["birth_month"],
                profile_data["birth_day"],
            )
        )
        parent.place_edit.setText(profile_data["birth_place"])
        parent.time_unknown_checkbox.setChecked(profile_data["time_unknown"])
        profile_time = QTime(profile_data["birth_hour"], profile_data["birth_minute"])
        parent.time_edit.setTime(profile_time)
        parent.retcon_time_edit.setTime(profile_time)
        parent.source_edit.setPlainText(profile_data["profile_url"])
        parent._set_relationship_type_selection(["public figure"])
        parent._set_chart_type_selection(SOURCE_PUBLIC_DB)

        chart_result = parent._build_chart_from_inputs(show_feedback=False)
        if chart_result is None:
            parent._reset_new_chart_form()
            QMessageBox.warning(
                self,
                "Astrotheme import",
                "Astrotheme import failed: chart creation could not be completed.",
            )
            return
        chart, place, _, _ = chart_result
        chart.source = SOURCE_PUBLIC_DB
        chart.relationship_types = ["public figure"]
        chart.chart_data_source = profile_data["profile_url"]
        chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
        chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
        chart.is_placeholder = False

        try:
            chart_id = save_chart(
                chart,
                birth_place=place,
                retcon_time_used=False,
                is_placeholder=False,
                birth_month=profile_data["birth_month"],
                birth_day=profile_data["birth_day"],
                birth_year=profile_data["birth_year"],
                chart_type=SOURCE_PUBLIC_DB,
            )
        except Exception as exc:
            parent._reset_new_chart_form()
            QMessageBox.warning(
                self,
                "Astrotheme import",
                f"Astrotheme import failed while saving the chart:\n{exc}",
            )
            return
        set_current_chart(chart_id)
        parent.current_chart_id = chart_id
        parent._manage_charts_pending_changed_ids.add(chart_id)
        parent._loaded_birth_place = place
        parent._loaded_lat = chart.lat
        parent._loaded_lon = chart.lon
        parent._latest_chart = chart
        parent.update_button.setText("Update Chart")
        parent._set_lucygoosey(False)
        parent._set_chart_right_panel_container_visible(True)
        parent._schedule_chart_render(chart)
        self._refresh_charts(
            selected_ids={chart_id},
            changed_ids={chart_id},
        )

        if isinstance(parent, QWidget):
            if isinstance(parent, MainWindow):
                parent._show_chart_view_maximized(maximize=self.isMaximized(), source_window=self)
            else:
                parent.showNormal()
                parent.raise_()
                parent.activateWindow()
        self.lower()

        QMessageBox.information(
            self,
            "Astrotheme import",
            f"Imported and saved chart #{chart_id} from Astrotheme.",
        )

    def _register_popout_shortcuts(self, dialog: QDialog) -> None:
        dialog._shortcut_close_ctrl = QShortcut(QKeySequence("Ctrl+W"), dialog)
        dialog._shortcut_close_ctrl.activated.connect(dialog.close)
        dialog._shortcut_close_cmd = QShortcut(QKeySequence("Meta+W"), dialog)
        dialog._shortcut_close_cmd.activated.connect(dialog.close)

    def _export_chart(self, chart: Chart | None) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_export_chart"):
            parent._export_chart(chart)
            return
        QMessageBox.warning(self, "Export unavailable", "Chart export is unavailable right now.")

    def _build_edit_panel(self) -> QWidget:
        # Batch edit panel (right sidebar).
        panel = EmojiTiledPanel("✏️", font_size=70, opacity=0.10) #Batch Edit panelbackground
        panel.setMinimumWidth(420)
        layout = QVBoxLayout()
        panel.setLayout(layout)

        header_layout = QHBoxLayout()
        title = QLabel("Database Manager")
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        layout.addLayout(header_layout)

        action_button_style = (
            "QPushButton {"
            "padding: 2px 6px;"
            "font-size: 11px;"
            "border: 1px solid #3f3f3f;"
            "background-color: #1a1a1a;"
            "color: #f0f0f0;"
            "}"
            "QPushButton:hover { background-color: #262626; }"
            "QPushButton:disabled { background-color: #202020; color: #666666; border-color: #2f2f2f; }"
        )

        actions_row_database = QWidget()
        actions_row_database_layout = QGridLayout(actions_row_database)
        actions_row_database_layout.setContentsMargins(0, 2, 0, 2)
        actions_row_database_layout.setHorizontalSpacing(4)
        actions_row_database_layout.setVerticalSpacing(4)

        #Database Actions Buttons: should be a single row
        self.batch_backup_database_button = QPushButton("Backup 📚") #Backup Database
        self.batch_backup_database_button.clicked.connect(self._on_export_database)
        self.batch_backup_database_button.setObjectName("manage_backup_database_button")
        self.batch_backup_database_button.setStyleSheet(action_button_style)
        actions_row_database_layout.addWidget(self.batch_backup_database_button, 0, 0)

        self.batch_restore_database_button = QPushButton("Restore 📚") #Restore Database
        self.batch_restore_database_button.clicked.connect(self._on_import_database)
        self.batch_restore_database_button.setObjectName("manage_restore_database_button")
        self.batch_restore_database_button.setStyleSheet(action_button_style)
        actions_row_database_layout.addWidget(self.batch_restore_database_button, 0, 1)

        self.batch_append_database_button = QPushButton("Append 📚") #Append Database
        self.batch_append_database_button.clicked.connect(self._on_append_database_placeholder)
        self.batch_append_database_button.setStyleSheet(action_button_style)
        actions_row_database_layout.addWidget(self.batch_append_database_button, 0, 2)

        self.batch_refresh_database_button = QPushButton("Refresh 📚") #Refresh Database
        self.batch_refresh_database_button.clicked.connect(self._on_force_refresh_database_analysis)
        self.batch_refresh_database_button.setObjectName("manage_force_refresh_button")
        self.batch_refresh_database_button.setStyleSheet(action_button_style)
        actions_row_database_layout.addWidget(self.batch_refresh_database_button, 0, 3)
        #single row of database action buttons end here

        for button in (
            self.batch_backup_database_button,
            self.batch_restore_database_button,
            self.batch_append_database_button,
            self.batch_refresh_database_button,
        ):
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(28)
        for idx in range(4):
            actions_row_database_layout.setColumnStretch(idx, 1)
        layout.addWidget(actions_row_database)

        actions_row_bottom = QWidget()
        actions_row_bottom_layout = QHBoxLayout(actions_row_bottom)
        actions_row_bottom_layout.setContentsMargins(0, 2, 0, 2)
        actions_row_bottom_layout.setSpacing(4)

        self.batch_export_selection_button = QPushButton("Export Selection to CSV")
        self.batch_export_selection_button.clicked.connect(self._on_export_selected)
        self.batch_export_selection_button.setStyleSheet(action_button_style)
        actions_row_bottom_layout.addWidget(self.batch_export_selection_button)

        self.batch_import_csv_button = QPushButton("Import from CSV")
        self.batch_import_csv_button.clicked.connect(self._on_import_csv)
        self.batch_import_csv_button.setStyleSheet(action_button_style)
        actions_row_bottom_layout.addWidget(self.batch_import_csv_button)

        self.batch_check_duplicates_button = QPushButton("Check for Duplicates")
        self.batch_check_duplicates_button.clicked.connect(self._on_check_for_duplicates)
        self.batch_check_duplicates_button.setStyleSheet(action_button_style)
        actions_row_bottom_layout.addWidget(self.batch_check_duplicates_button)

        layout.addWidget(actions_row_bottom)

        divider_actions_charts = QFrame()
        divider_actions_charts.setFrameShape(QFrame.HLine)
        divider_actions_charts.setFrameShadow(QFrame.Sunken)
        divider_actions_charts.setStyleSheet("color: #2f2f2f;")
        layout.addWidget(divider_actions_charts)

        actions_row_top = QWidget()
        actions_row_top_layout = QHBoxLayout(actions_row_top)
        actions_row_top_layout.setContentsMargins(0, 2, 0, 2)
        actions_row_top_layout.setSpacing(4)

        self.batch_new_chart_button = QPushButton("+ New Chart")
        self.batch_new_chart_button.clicked.connect(self._on_new_chart)
        self.batch_new_chart_button.setStyleSheet(
            action_button_style + "QPushButton { color: #6fe06f; font-weight: 600; }"
        )
        actions_row_top_layout.addWidget(self.batch_new_chart_button)

        self.batch_delete_chart_button = QPushButton("❌ Delete 0 Charts")
        self.batch_delete_chart_button.clicked.connect(self._on_delete)
        self.batch_delete_chart_button.setStyleSheet(
            action_button_style + "QPushButton { color: #ff7b7b; font-weight: 600; }"
        )
        actions_row_top_layout.addWidget(self.batch_delete_chart_button)

        self.batch_rename_chart_button = QPushButton("Rename chart")
        self.batch_rename_chart_button.setStyleSheet(action_button_style)
        self.batch_rename_chart_button.clicked.connect(self._on_rename_selected_chart)
        self.batch_rename_chart_button.setEnabled(False)
        actions_row_top_layout.addWidget(self.batch_rename_chart_button)

        self.batch_synastry_chart_button = QPushButton("Synastry Chart")
        self.batch_synastry_chart_button.clicked.connect(self._on_generate_composite_chart)
        self.batch_synastry_chart_button.setObjectName("manage_composite_chart_button")
        self.batch_synastry_chart_button.setStyleSheet(action_button_style)
        actions_row_top_layout.addWidget(self.batch_synastry_chart_button)
        layout.addWidget(actions_row_top)

        divider_chart_editor = QFrame()
        divider_chart_editor.setFrameShape(QFrame.HLine)
        divider_chart_editor.setFrameShadow(QFrame.Sunken)
        divider_chart_editor.setStyleSheet("color: #2f2f2f;")
        layout.addWidget(divider_chart_editor)

        batch_editor_title = QLabel("Batch Editor")
        batch_editor_title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(batch_editor_title)

        self._update_batch_edit_action_buttons()

        description = QLabel(
            "Apply changes to all selected charts at once."
        )
        description.setWordWrap(True)
        layout.addWidget(description)


        def add_collapsible_section(title: str) -> tuple[QWidget, QVBoxLayout]:
            section = QWidget()
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section.setLayout(section_layout)

            toggle = QToolButton()
            configure_collapsible_header_toggle(
                toggle,
                title=title,
                expanded=False,
                style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
            )

            content = QWidget()
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(8, 6, 8, 6)
            content.setLayout(content_layout)
            content.setVisible(False)

            def toggle_content(checked: bool) -> None:
                content.setVisible(checked)
                toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
                content.adjustSize()
                section.adjustSize()
                panel.adjustSize()
                panel.updateGeometry()

            toggle.toggled.connect(toggle_content)

            section_layout.addWidget(toggle)
            section_layout.addWidget(content)
            return section, content_layout

        sentiment_section, sentiment_section_layout = add_collapsible_section("Sentiment")

        self.batch_sentiment_checkboxes = {}
        sentiment_widget = QWidget()
        sentiment_layout = QGridLayout()
        sentiment_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_rows = (len(SENTIMENT_OPTIONS) + 1) // 2
        for idx, label in enumerate(SENTIMENT_OPTIONS):
            checkbox = QuadStateSlider(label)
            checkbox.modeChanged.connect(
                lambda state, name=label: self._on_batch_sentiment_state_changed(
                    name,
                    state,
                )
            )
            self.batch_sentiment_checkboxes[label] = checkbox
            row = idx % sentiment_rows
            col = idx // sentiment_rows
            sentiment_layout.addWidget(checkbox, row, col)
        sentiment_widget.setLayout(sentiment_layout)
        sentiment_section_layout.addWidget(sentiment_widget)
        layout.addWidget(sentiment_section)

        relationship_section, relationship_section_layout = add_collapsible_section("Relationship types")

        self.batch_relationship_type_checkboxes = {}
        relationship_widget = QWidget()
        relationship_layout = QGridLayout()
        relationship_layout.setContentsMargins(0, 0, 0, 0)
        relationship_rows = (len(RELATION_TYPE) + 1) // 2
        for idx, label in enumerate(RELATION_TYPE):
            checkbox = QuadStateSlider(label)
            checkbox.modeChanged.connect(
                lambda state, name=label: self._on_batch_relationship_type_state_changed(
                    name,
                    state,
                )
            )
            self.batch_relationship_type_checkboxes[label] = checkbox
            row = idx % relationship_rows
            col = idx // relationship_rows
            relationship_layout.addWidget(checkbox, row, col)
        relationship_widget.setLayout(relationship_layout)
        relationship_section_layout.addWidget(relationship_widget)
        layout.addWidget(relationship_section)

        tagging_section, tagging_section_layout = add_collapsible_section("Tagging")
        tagging_row = QHBoxLayout()
        self.batch_tags_input = QLineEdit()
        self.batch_tags_input.setPlaceholderText("comma-separated tags")
        self.batch_tags_input.textChanged.connect(
            lambda: render_tag_chip_preview(
                self.batch_tags_preview_label,
                parse_tag_text(self.batch_tags_input.text()),
            )
        )
        self.batch_tags_input.textChanged.connect(self._on_batch_tags_changed)
        self.batch_tags_input.textEdited.connect(
            lambda _text: setattr(self, "_batch_tags_lucygoosey", True)
        )
        tagging_row.addWidget(self.batch_tags_input, 1)
        batch_tags_apply_button = QPushButton("Apply")
        batch_tags_apply_button.clicked.connect(self._on_batch_tags_apply)
        tagging_row.addWidget(batch_tags_apply_button, 0)
        tagging_section_layout.addLayout(tagging_row)
        self.batch_tags_preview_label = QLabel()
        self.batch_tags_preview_label.setWordWrap(True)
        self.batch_tags_preview_label.setTextFormat(Qt.RichText)
        tagging_section_layout.addWidget(self.batch_tags_preview_label)
        self.batch_tags_selection_label = QLabel()
        self.batch_tags_selection_label.setWordWrap(True)
        self.batch_tags_selection_label.setTextFormat(Qt.RichText)
        self.batch_tags_selection_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.batch_tags_selection_label.setCursor(Qt.PointingHandCursor)
        self.batch_tags_selection_label.linkActivated.connect(self._on_batch_tag_remove_link_clicked)
        tagging_section_layout.addWidget(self.batch_tags_selection_label)
        self.batch_tags_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.batch_tags_toggle,
            title="Tags",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        tagging_section_layout.addWidget(self.batch_tags_toggle)
        self.batch_tags_list_widget = QListWidget()
        self.batch_tags_list_widget.setSelectionMode(QListWidget.NoSelection)
        self.batch_tags_list_widget.setMaximumHeight(180)
        self.batch_tags_list_widget.itemClicked.connect(self._on_batch_tag_item_clicked)
        self.batch_tags_list_widget.setVisible(False)
        self.batch_tags_toggle.toggled.connect(self.batch_tags_list_widget.setVisible)
        tagging_section_layout.addWidget(self.batch_tags_list_widget)
        self._bind_batch_enter_apply(self.batch_tags_input, batch_tags_apply_button.click)
        self._update_tag_completers()
        layout.addWidget(tagging_section)

        sentiment_metrics_section, sentiment_metrics_section_layout = add_collapsible_section("Sentiment metrics")

        sentiment_metrics_widget = QWidget()
        sentiment_metrics_layout = QGridLayout()
        sentiment_metrics_layout.setContentsMargins(0, 0, 0, 0)
        self._batch_metric_programmatic_update = False
        self._batch_last_selection_ids: set[int] = set()
        self._batch_selection_order: list[int] = []
        self._batch_metric_lucygoosey: dict[str, bool] = {
            "positive_sentiment_intensity": False,
            "negative_sentiment_intensity": False,
            "familiarity": False,
            "year_first_encountered": False,
        }
        self._batch_tags_lucygoosey = False
        
        self.batch_year_first_encountered_edit = QLineEdit()
        self.batch_year_first_encountered_edit.setPlaceholderText("blank")
        self.batch_year_first_encountered_edit.setMaxLength(4)
        self.batch_year_first_encountered_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$"), self)
        )
        batch_year_first_encountered_button = QPushButton("Apply")
        batch_year_first_encountered_button.clicked.connect(
            lambda: self._on_batch_sentiment_metric_assign(
                "year_first_encountered",
                "year 1st encountered",
                self._parse_year_first_encountered_text(self.batch_year_first_encountered_edit.text()),
            )
        )
        sentiment_metrics_layout.addWidget(QLabel("Year 1st Encountered"), 3, 0)
        sentiment_metrics_layout.addWidget(
            self.batch_year_first_encountered_edit,
            3,
            1,
        )
        sentiment_metrics_layout.addWidget(batch_year_first_encountered_button, 3, 2)

        self.batch_positive_sentiment_intensity_spin = QSpinBox()
        self.batch_positive_sentiment_intensity_spin.setRange(1, 10)
        self.batch_positive_sentiment_intensity_spin.setValue(1)
        self.batch_positive_sentiment_intensity_spin.valueChanged.connect(
            lambda _value: self._on_batch_metric_field_lucygoosey("positive_sentiment_intensity")
        )
        self.batch_positive_sentiment_intensity_spin.setFixedWidth(
            self.batch_positive_sentiment_intensity_spin.sizeHint().width() * 2
        )
        batch_positive_button = QPushButton("Apply")
        batch_positive_button.clicked.connect(
            lambda: self._on_batch_sentiment_metric_assign(
                "positive_sentiment_intensity",
                "positive sentiment intensity",
                self.batch_positive_sentiment_intensity_spin.value(),
            )
        )
        sentiment_metrics_layout.addWidget(QLabel("Positive intensity"), 0, 0)
        sentiment_metrics_layout.addWidget(
            self.batch_positive_sentiment_intensity_spin,
            0,
            1,
        )
        sentiment_metrics_layout.addWidget(batch_positive_button, 0, 2)

        self.batch_negative_sentiment_intensity_spin = QSpinBox()
        self.batch_negative_sentiment_intensity_spin.setRange(1, 10)
        self.batch_negative_sentiment_intensity_spin.setValue(1)
        self.batch_negative_sentiment_intensity_spin.valueChanged.connect(
            lambda _value: self._on_batch_metric_field_lucygoosey("negative_sentiment_intensity")
        )
        self.batch_negative_sentiment_intensity_spin.setFixedWidth(
            self.batch_negative_sentiment_intensity_spin.sizeHint().width() * 2
        )
        batch_negative_button = QPushButton("Apply")
        batch_negative_button.clicked.connect(
            lambda: self._on_batch_sentiment_metric_assign(
                "negative_sentiment_intensity",
                "negative sentiment intensity",
                self.batch_negative_sentiment_intensity_spin.value(),
            )
        )
        sentiment_metrics_layout.addWidget(QLabel("Negative intensity"), 1, 0)
        sentiment_metrics_layout.addWidget(
            self.batch_negative_sentiment_intensity_spin,
            1,
            1,
        )
        sentiment_metrics_layout.addWidget(batch_negative_button, 1, 2)

        self.batch_familiarity_spin = QSpinBox()
        self.batch_familiarity_spin.setRange(1, 10)
        self.batch_familiarity_spin.setValue(1)
        self.batch_familiarity_spin.valueChanged.connect(
            lambda _value: self._on_batch_metric_field_lucygoosey("familiarity")
        )
        self.batch_familiarity_spin.setFixedWidth(
            self.batch_familiarity_spin.sizeHint().width() * 2
        )
        batch_familiarity_button = QPushButton("Apply")
        batch_familiarity_button.clicked.connect(
            lambda: self._on_batch_sentiment_metric_assign(
                "familiarity",
                "familiarity",
                self.batch_familiarity_spin.value(),
            )
        )
        familiarity_label_widget = QWidget()
        familiarity_label_layout = QHBoxLayout()
        familiarity_label_layout.setContentsMargins(0, 0, 0, 0)
        familiarity_label_layout.setSpacing(4)
        familiarity_label_layout.addWidget(QLabel("Familiarity"))
        batch_familiarity_calculator_button = QToolButton()
        batch_familiarity_calculator_button.setText("📠")
        batch_familiarity_calculator_button.setAutoRaise(True)
        batch_familiarity_calculator_button.setStyleSheet("QToolButton { border: none; background: transparent; padding: 0; }")
        batch_familiarity_calculator_button.setToolTip("Open Familiarity Calculator")
        batch_familiarity_calculator_button.setCursor(Qt.CursorShape.PointingHandCursor)
        batch_familiarity_calculator_button.clicked.connect(self._open_batch_familiarity_calculator)
        familiarity_label_layout.addWidget(batch_familiarity_calculator_button)
        familiarity_label_widget.setLayout(familiarity_label_layout)
        sentiment_metrics_layout.addWidget(familiarity_label_widget, 2, 0)
        sentiment_metrics_layout.addWidget(
            self.batch_familiarity_spin,
            2,
            1,
        )
        sentiment_metrics_layout.addWidget(batch_familiarity_button, 2, 2)

        self._bind_batch_enter_apply(self.batch_positive_sentiment_intensity_spin, batch_positive_button.click)
        self._bind_batch_enter_apply(self.batch_negative_sentiment_intensity_spin, batch_negative_button.click)
        self._bind_batch_enter_apply(self.batch_familiarity_spin, batch_familiarity_button.click)
        self._bind_batch_enter_apply(self.batch_year_first_encountered_edit, batch_year_first_encountered_button.click) 
        self.batch_year_first_encountered_edit.textEdited.connect(
            lambda _text: self._on_batch_metric_field_lucygoosey("year_first_encountered")
        )

        sentiment_metrics_widget.setLayout(sentiment_metrics_layout)
        sentiment_metrics_section_layout.addWidget(sentiment_metrics_widget)
        layout.addWidget(sentiment_metrics_section)

        chart_type_section, chart_type_section_layout = add_collapsible_section("Chart Type")

        self.batch_source_combo = QComboBox()
        self.batch_source_combo.addItem("Mixed / unchanged", "")
        for source_option_label, source_option_value in SOURCE_OPTIONS:
            self.batch_source_combo.addItem(source_option_label, source_option_value)
        self.batch_source_combo.currentIndexChanged.connect(
            self._on_batch_source_selected
        )
        chart_type_section_layout.addWidget(self.batch_source_combo)
        layout.addWidget(chart_type_section)

        batch_gender_section, batch_gender_section_layout = add_collapsible_section("Gender")

        self.batch_gender_combo = QComboBox()
        self.batch_gender_combo.addItem("Mixed / unchanged", "")
        self.batch_gender_combo.addItem("blank", "__blank__")
        for gender_option in GENDER_OPTIONS:
            self.batch_gender_combo.addItem(gender_option, gender_option)
        self.batch_gender_combo.currentIndexChanged.connect(
            self._on_batch_gender_selected
        )
        batch_gender_section_layout.addWidget(self.batch_gender_combo)
        layout.addWidget(batch_gender_section)

        birthtime_unknown_section, birthtime_unknown_section_layout = add_collapsible_section("Birth info")

        self.batch_birthtime_unknown_checkbox = QuadStateSlider("birthtime unknown")
        self.batch_birthtime_unknown_checkbox.modeChanged.connect(
            self._on_batch_birthtime_unknown_state_changed
        )
        birthtime_unknown_section_layout.addWidget(self.batch_birthtime_unknown_checkbox)
        layout.addWidget(birthtime_unknown_section)

        mortality_section, mortality_section_layout = add_collapsible_section("Mortality")

        self.batch_deceased_checkbox = QuadStateSlider("💀")
        self.batch_deceased_checkbox.modeChanged.connect(
            self._on_batch_mortality_state_changed
        )
        mortality_section_layout.addWidget(self.batch_deceased_checkbox)
        layout.addWidget(mortality_section)

        alignment_section, alignment_section_layout = add_collapsible_section("Alignment")

        self.batch_alignment_slider = AlignmentEmojiSlider()
        self.batch_alignment_slider.valueChanged.connect(self._on_batch_alignment_changed)
        self.batch_alignment_score_label = QLabel()
        self._update_batch_alignment_score_label(self.batch_alignment_slider.value())
        self.batch_alignment_apply_button = QPushButton("Apply alignment")
        self.batch_alignment_apply_button.clicked.connect(self._on_batch_alignment_apply)

        alignment_section_layout.addWidget(
            QLabel("😈 Most evil   ⟷   Most altruistic 😇")
        )
        alignment_section_layout.addWidget(self.batch_alignment_slider)
        alignment_section_layout.addWidget(self.batch_alignment_score_label)
        alignment_section_layout.addWidget(self.batch_alignment_apply_button)
        layout.addWidget(alignment_section)

        layout.addStretch(1)

        self.clear_batch_edit_button = QPushButton("Clear")
        self.clear_batch_edit_button.clicked.connect(self._clear_batch_edits)
        layout.addWidget(self.clear_batch_edit_button)

        return panel

    def _confirm_batch_edit(self, action_label: str, selected_count: int) -> bool:
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Question)
        message_box.setWindowTitle("Confirm batch edit")
        message_box.setText(
            f"Are you sure you want to {action_label} {selected_count} chart(s)?"
        )
        yes_button = message_box.addButton(QMessageBox.Yes)
        no_button = message_box.addButton(QMessageBox.No)
        message_box.setDefaultButton(yes_button)
        message_box.setEscapeButton(no_button)
        response = message_box.exec()
        return response == QMessageBox.Yes


    @staticmethod
    def _set_batch_checkbox_state(
        checkbox: QuadStateSlider,
        state: int,
    ) -> None:
        checkbox.blockSignals(True)
        checkbox.setMode(int(state))
        checkbox.blockSignals(False)

    def _update_batch_edit_state(self) -> None:
        selected_items = self.list_widget.selectedItems()
        self._update_batch_edit_action_buttons()
        selected_chart_ids = self._selected_chart_ids(selected_items)
        chart_id_set = set(selected_chart_ids)
        preserve_lucygoosey_metrics = (
            bool(chart_id_set)
            and bool(self._batch_last_selection_ids)
            and bool(chart_id_set.intersection(self._batch_last_selection_ids))
        )
        if not selected_chart_ids:
            self._clear_batch_edits()
            return
        self._update_batch_selection_order(selected_chart_ids)

        # Selection can briefly contain stale ids during list refreshes
        # (e.g., right after delete/filter changes). Resolve ids from current
        # cache first and drop any rows no longer present in the database.
        resolved_items: list[tuple[int, Chart]] = []
        stale_ids: set[int] = set()
        for chart_id in selected_chart_ids:
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                stale_ids.add(chart_id)
                continue
            resolved_items.append((chart_id, chart))

        if stale_ids:
            QTimer.singleShot(
                0,
                lambda removed_ids=set(stale_ids): self._refresh_charts(changed_ids=removed_ids),
            )

        if not resolved_items:
            self._clear_batch_edits()
            return

        selected_count = len(resolved_items)
        sentiment_counts = {label: 0 for label in self.batch_sentiment_checkboxes}
        relationship_counts = {
            label: 0 for label in self.batch_relationship_type_checkboxes
        }
        birthtime_unknown_count = 0
        deceased_count = 0
        source_values: list[str] = []
        positive_intensities: list[int] = []
        negative_intensities: list[int] = []
        familiarity_values: list[int] = []
        tag_values: list[str] = []
        tag_counts: dict[str, int] = {}
        gender_values: list[str] = []
        year_first_encountered_values: list[int | None] = []
        for chart_id, chart in resolved_items:
            sentiments = set(getattr(chart, "sentiments", []) or [])
            relationships = set(getattr(chart, "relationship_types", []) or [])
            for label in sentiment_counts:
                if label in sentiments:
                    sentiment_counts[label] += 1
            for label in relationship_counts:
                if label in relationships:
                    relationship_counts[label] += 1
            if getattr(chart, "birthtime_unknown", False):
                birthtime_unknown_count += 1
            if bool(getattr(chart, "is_deceased", False)):
                deceased_count += 1
            source_value = _normalize_gui_source(getattr(chart, "source", SOURCE_PERSONAL) or SOURCE_PERSONAL)
            source_values.append(source_value)
            positive_intensities.append(
                int(getattr(chart, "positive_sentiment_intensity", 1) or 1)
            )
            negative_intensities.append(
                int(getattr(chart, "negative_sentiment_intensity", 1) or 1)
            )
            familiarity_values.append(
                int(getattr(chart, "familiarity", 1) or 1)
            )
            tag_values.append(
                ", ".join(normalize_tag_list(getattr(chart, "tags", [])))
            )
            for tag in set(normalize_tag_list(getattr(chart, "tags", []))):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            gender_values.append(
                self._normalize_gender_value(getattr(chart, "gender", None))
            )
            year_first_encountered_values.append(
                self._parse_year_first_encountered_text(str(getattr(chart, "year_first_encountered", "") or ""))
            )


        for label, checkbox in self.batch_sentiment_checkboxes.items():
            count = sentiment_counts[label]
            if count == 0:
                state = QuadStateSlider.MODE_EMPTY
            elif count == selected_count:
                state = QuadStateSlider.MODE_TRUE
            else:
                state = QuadStateSlider.MODE_MIXED
            self._set_batch_checkbox_state(checkbox, state)

        for label, checkbox in self.batch_relationship_type_checkboxes.items():
            count = relationship_counts[label]
            if count == 0:
                state = QuadStateSlider.MODE_EMPTY
            elif count == selected_count:
                state = QuadStateSlider.MODE_TRUE
            else:
                state = QuadStateSlider.MODE_MIXED
            self._set_batch_checkbox_state(checkbox, state)

        unique_sources = set(source_values)
        self.batch_source_combo.blockSignals(True)
        if len(unique_sources) == 1:
            source_value = next(iter(unique_sources))
            source_index = self.batch_source_combo.findData(source_value)
            self.batch_source_combo.setCurrentIndex(max(0, source_index))
            self.batch_source_combo.setToolTip("")
        else:
            self.batch_source_combo.setCurrentIndex(0)
            self.batch_source_combo.setToolTip(
                "Selected charts have mixed chart types. Choose one to overwrite all selected charts."
            )
        self.batch_source_combo.blockSignals(False)

        unique_genders = set(gender_values)
        self.batch_gender_combo.blockSignals(True)
        if len(unique_genders) == 1:
            gender_value = next(iter(unique_genders))
            gender_data = gender_value if gender_value else "__blank__"
            gender_index = self.batch_gender_combo.findData(gender_data)
            self.batch_gender_combo.setCurrentIndex(max(0, gender_index))
            self.batch_gender_combo.setToolTip("")
        else:
            self.batch_gender_combo.setCurrentIndex(0)
            self.batch_gender_combo.setToolTip(
                "Selected charts have mixed genders. Choose one to overwrite all selected charts."
            )
        self.batch_gender_combo.blockSignals(False)

        if birthtime_unknown_count == 0:
            birthtime_state = QuadStateSlider.MODE_EMPTY
        elif birthtime_unknown_count == selected_count:
            birthtime_state = QuadStateSlider.MODE_TRUE
        else:
            birthtime_state = QuadStateSlider.MODE_MIXED
        self._set_batch_checkbox_state(
            self.batch_birthtime_unknown_checkbox,
            birthtime_state,
        )
        if deceased_count == 0:
            deceased_state = QuadStateSlider.MODE_EMPTY
        elif deceased_count == selected_count:
            deceased_state = QuadStateSlider.MODE_TRUE
        else:
            deceased_state = QuadStateSlider.MODE_MIXED
        self._set_batch_checkbox_state(
            self.batch_deceased_checkbox,
            deceased_state,
        )
        self._set_batch_metric_spin_state(
            "positive_sentiment_intensity",
            self.batch_positive_sentiment_intensity_spin,
            positive_intensities,
            preserve_lucygoosey=preserve_lucygoosey_metrics,
        )
        self._set_batch_metric_spin_state(
            "negative_sentiment_intensity",
            self.batch_negative_sentiment_intensity_spin,
            negative_intensities,
            preserve_lucygoosey=preserve_lucygoosey_metrics,
        )
        self._set_batch_metric_spin_state(
            "familiarity",
            self.batch_familiarity_spin,
            familiarity_values,
            preserve_lucygoosey=preserve_lucygoosey_metrics,
        )
        self._set_batch_year_field_state(
            "year_first_encountered",
            self.batch_year_first_encountered_edit,
            year_first_encountered_values,
            preserve_lucygoosey=preserve_lucygoosey_metrics,
        )
        self._set_batch_tags_state(
            tag_values,
            preserve_lucygoosey=preserve_lucygoosey_metrics,
        )
        self._render_batch_selection_tag_summary(tag_counts, selected_count)
        self._set_batch_alignment_state(resolved_items)
        self._batch_last_selection_ids = chart_id_set

    def _update_batch_selection_order(self, selected_chart_ids: list[int]) -> None:
        selected_set = set(selected_chart_ids)
        self._batch_selection_order = [
            chart_id for chart_id in self._batch_selection_order if chart_id in selected_set
        ]
        for chart_id in selected_chart_ids:
            if chart_id not in self._batch_selection_order:
                self._batch_selection_order.append(chart_id)

    @staticmethod
    def _alignment_value_for_chart(chart: Chart) -> int:
        raw_value = getattr(chart, "alignment_score", 0)
        try:
            return int(raw_value) if raw_value is not None else 0
        except (TypeError, ValueError):
            return 0

    def _set_batch_alignment_state(self, items: list[tuple[int, Chart]]) -> None:
        if not items:
            self.batch_alignment_slider.blockSignals(True)
            self.batch_alignment_slider.setValue(0)
            self.batch_alignment_slider.blockSignals(False)
            self.batch_alignment_slider.setToolTip("")
            self._update_batch_alignment_score_label(0)
            return
        alignment_by_chart_id = {
            chart_id: self._alignment_value_for_chart(chart)
            for chart_id, chart in items
        }
        anchor_chart_id = next(
            (
                chart_id
                for chart_id in self._batch_selection_order
                if chart_id in alignment_by_chart_id
            ),
            items[0][0],
        )
        selected_value = alignment_by_chart_id.get(anchor_chart_id, 0)
        self.batch_alignment_slider.blockSignals(True)
        self.batch_alignment_slider.setValue(selected_value)
        self.batch_alignment_slider.blockSignals(False)
        self._update_batch_alignment_score_label(selected_value)
        if len(set(alignment_by_chart_id.values())) > 1:
            self.batch_alignment_slider.setToolTip(
                "Selected charts have mixed alignment scores. Applying will overwrite all selected charts."
            )
        else:
            self.batch_alignment_slider.setToolTip("")

    @staticmethod
    def _parse_year_first_encountered_text(raw_value: str | None) -> int | None:
        value = (raw_value or "").strip()
        if value == "":
            return None
        if value.isdigit():
            return int(value)
        return None

    def _update_tag_completers(self) -> None:
        known_tags = list_recognized_tags()
        self._known_chart_tags = known_tags
        chart_input = getattr(self, "chart_tags_input", None)
        search_input = getattr(self, "search_tags_input", None)
        batch_tags_input = getattr(self, "batch_tags_input", None)
        for line_edit in (chart_input, search_input, batch_tags_input):
            if not isinstance(line_edit, QLineEdit):
                continue
            apply_tag_completer(line_edit, known_tags)
        self._refresh_search_tags_list(known_tags)
        self._refresh_batch_tags_list(known_tags)

    def _on_search_tags_changed(self, *_: object) -> None:
        tags = parse_tag_text(self.search_tags_input.text())
        render_tag_chip_preview(self.search_tags_preview_label, tags)
        self._refresh_search_tags_list(getattr(self, "_known_chart_tags", []))
        self._on_filter_changed()

    def _refresh_search_tags_list(self, known_tags: list[str]) -> None:
        if not hasattr(self, "search_tags_list_widget"):
            return
        selected_tags = {
            tag.casefold()
            for tag in parse_tag_text(
                self.search_tags_input.text() if hasattr(self, "search_tags_input") else ""
            )
        }
        self.search_tags_list_widget.clear()
        for tag in known_tags:
            label = f"✓ {tag}" if tag.casefold() in selected_tags else tag
            self.search_tags_list_widget.addItem(label)

    def _on_search_tag_item_clicked(self, item: QListWidgetItem) -> None:
        tag_value = item.text().lstrip("✓").strip()
        if not tag_value:
            return
        self.search_tags_input.setText(tag_value)

    def _on_batch_tags_changed(self, *_: object) -> None:
        self._refresh_batch_tags_list(getattr(self, "_known_chart_tags", []))

    def _refresh_batch_tags_list(self, known_tags: list[str]) -> None:
        if not hasattr(self, "batch_tags_list_widget"):
            return
        selected_tags = {
            tag.casefold()
            for tag in parse_tag_text(
                self.batch_tags_input.text() if hasattr(self, "batch_tags_input") else ""
            )
        }
        self.batch_tags_list_widget.clear()
        for tag in known_tags:
            label = f"✓ {tag}" if tag.casefold() in selected_tags else tag
            self.batch_tags_list_widget.addItem(label)

    def _on_batch_tag_item_clicked(self, item: QListWidgetItem) -> None:
        tag_value = item.text().lstrip("✓").strip()
        if not tag_value:
            return

        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before assigning tags.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = f"Add tag '{tag_value}' to"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        normalized_key = tag_value.casefold()
        changed_ids: set[int] = set()
        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                existing_tags = normalize_tag_list(getattr(chart, "tags", []))
                if any(tag.casefold() == normalized_key for tag in existing_tags):
                    continue
                chart.tags = existing_tags + [tag_value]
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
                changed_ids.add(int(chart_id))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Couldn't assign tag '{tag_value}' to selected charts:\n{exc}",
            )
            return

        if not changed_ids:
            QMessageBox.information(
                self,
                "No changes applied",
                f"All selected charts already have the tag '{tag_value}'.",
            )
            self._update_batch_edit_state()
            return

        self._batch_tags_lucygoosey = False
        self.batch_tags_input.setText(tag_value)
        self._update_tag_completers()
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    @staticmethod
    def _parse_integer_filter_text(raw_value: str | None) -> int | None:
        value = (raw_value or "").strip()
        if value == "":
            return None
        if value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _parse_signed_integer_filter_text(raw_value: str | None) -> int | None:
        value = (raw_value or "").strip()
        if value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _set_batch_year_field_state(
        self,
        field_key: str,
        line_edit: QLineEdit,
        values: list[int | None],
        *,
        preserve_lucygoosey: bool = False,
    ) -> None:
        if not values:
            self._batch_metric_programmatic_update = True
            line_edit.setText("")
            self._batch_metric_programmatic_update = False
            self._set_batch_metric_lucygoosey_state(field_key, False)
            line_edit.setToolTip("")
            return
        if preserve_lucygoosey and self._batch_metric_lucygoosey.get(field_key, False):
            return
        first_value = values[0]
        self._batch_metric_programmatic_update = True
        line_edit.blockSignals(True)
        line_edit.setText("" if first_value is None else str(first_value))
        line_edit.blockSignals(False)
        self._batch_metric_programmatic_update = False
        self._set_batch_metric_lucygoosey_state(field_key, False)
        if len({value for value in values}) > 1:
            line_edit.setToolTip(
                "Selected charts have mixed values. Applying will overwrite all selected charts."
            )
        else:
            line_edit.setToolTip("")

    def _set_batch_tags_state(
        self,
        values: list[str],
        *,
        preserve_lucygoosey: bool = False,
    ) -> None:
        if not hasattr(self, "batch_tags_input"):
            return
        if preserve_lucygoosey and bool(getattr(self, "_batch_tags_lucygoosey", False)):
            return
        self.batch_tags_input.blockSignals(True)
        first_value = values[0] if values else ""
        self.batch_tags_input.setText(first_value)
        self.batch_tags_input.blockSignals(False)
        render_tag_chip_preview(
            getattr(self, "batch_tags_preview_label", None),
            parse_tag_text(first_value),
        )
        self._batch_tags_lucygoosey = False
        if values and len(set(values)) > 1:
            self.batch_tags_input.setToolTip(
                "Selected charts have mixed tag values. Applying will overwrite all selected charts."
            )
        else:
            self.batch_tags_input.setToolTip("")

    def _render_batch_selection_tag_summary(
        self,
        tag_counts: dict[str, int],
        selected_count: int,
    ) -> None:
        if not hasattr(self, "batch_tags_selection_label"):
            return
        if selected_count <= 0:
            self.batch_tags_selection_label.setText("")
            return
        if not tag_counts:
            self.batch_tags_selection_label.setText(
                "<span style='color:#8d8d8d;'>No tags on selected charts.</span>"
            )
            return

        chips: list[str] = []
        for tag in sorted(tag_counts, key=lambda value: value.casefold()):
            count = int(tag_counts.get(tag, 0))
            is_global = count >= selected_count
            chip_style = (
                "background:#d9d9d9;color:#222;border:1px solid #bdbdbd;"
                if is_global
                else "background:#2d2d2d;color:#bdbdbd;border:1px solid #4a4a4a;"
            )
            encoded_tag = urllib.parse.quote(tag, safe="")
            chips.append(
                "<span style='display:inline-block;"
                f"{chip_style}"
                "border-radius:8px;padding:1px 6px;margin:2px 4px 2px 0;'>"
                f"{html.escape(tag)}"
                f"<a href='remove_tag:{encoded_tag}' style='color:#ff6f6f;text-decoration:none;font-weight:700;'> ✕</a>"
                "</span>"
            )
        self.batch_tags_selection_label.setText("".join(chips))

    def _on_batch_tag_remove_link_clicked(self, link: str) -> None:
        prefix = "remove_tag:"
        if not link.startswith(prefix):
            return
        encoded_tag = link[len(prefix):]
        tag_to_remove = urllib.parse.unquote(encoded_tag).strip()
        if not tag_to_remove:
            return

        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before removing tags.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = f"Remove tag '{tag_to_remove}' from"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            normalized_remove_key = tag_to_remove.casefold()
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                existing_tags = normalize_tag_list(getattr(chart, "tags", []))
                chart.tags = [
                    tag
                    for tag in existing_tags
                    if tag.casefold() != normalized_remove_key
                ]
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Couldn't remove '{tag_to_remove}' from selected charts:\n{exc}",
            )
            return

        self._batch_tags_lucygoosey = False
        changed_ids = set(chart_ids)
        self._update_tag_completers()
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    @staticmethod
    def _bind_batch_enter_apply(widget: QWidget, callback: Callable[[], None]) -> None:
        shortcut = QShortcut(QKeySequence("Return"), widget)
        shortcut.activated.connect(callback)
        widget._batch_apply_enter_shortcut = shortcut
        shortcut2 = QShortcut(QKeySequence("Enter"), widget)
        shortcut2.activated.connect(callback)
        widget._batch_apply_enter_shortcut2 = shortcut2
        widget._batch_enter_apply_callback = callback

    def _set_batch_metric_spin_state(
        self,
        field_key: str,
        spinbox: QSpinBox,
        values: list[int],
        *,
        preserve_lucygoosey: bool = False,
    ) -> None:
        if not values:
            self._batch_metric_programmatic_update = True
            spinbox.setValue(1)
            self._batch_metric_programmatic_update = False
            self._set_batch_metric_lucygoosey_state(field_key, False)
            spinbox.setToolTip("")
            return
        if preserve_lucygoosey and self._batch_metric_lucygoosey.get(field_key, False):
            return
        self._batch_metric_programmatic_update = True
        spinbox.blockSignals(True)
        spinbox.setValue(values[0])
        spinbox.blockSignals(False)
        self._batch_metric_programmatic_update = False
        self._set_batch_metric_lucygoosey_state(field_key, False)
        if len(set(values)) > 1:
            spinbox.setToolTip(
                "Selected charts have mixed values. Applying will overwrite all selected charts."
            )
        else:
            spinbox.setToolTip("")

    def _refresh_filters_after_batch_edit(self, chart_ids: set[int] | None = None) -> None:
        selected_chart_ids = set(chart_ids or [])
        if self.current_chart_id is not None and int(self.current_chart_id) in selected_chart_ids:
            self._mark_chart_analytics_sections_dirty()
            if self._latest_chart is not None:
                self._schedule_chart_render(self._latest_chart)

        if not selected_chart_ids:
            selected_chart_ids = set(self._selected_chart_ids())

        def _refresh_and_restore_selection() -> None:
            if not self.isVisible():
                return
            try:
                self._refresh_charts(
                    selected_ids=selected_chart_ids,
                    changed_ids=selected_chart_ids,
                )
                if not selected_chart_ids:
                    return

                self._flash_batch_updated_rows(selected_chart_ids)
                self._on_selection_changed()
            except RuntimeError:
                # Dialog widgets may be gone if the user navigated away before
                # this deferred callback runs.
                return
            except Exception as exc:
                traceback.print_exc()
                QMessageBox.critical(
                    self,
                    "Filter error",
                    f"Could not apply filters:\n{exc}",
                )

        QTimer.singleShot(0, _refresh_and_restore_selection)

    def _flash_batch_updated_rows(self, chart_ids: set[int]) -> None:
        if not chart_ids:
            return

        flash_brush = QBrush(QColor(84, 84, 84, 110))
        original_backgrounds: dict[int, QBrush] = {}
        flashed_items: list[QListWidgetItem] = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            chart_id = item.data(Qt.UserRole)
            if chart_id not in chart_ids:
                continue
            original_backgrounds[row] = item.background()
            item.setBackground(flash_brush)
            flashed_items.append(item)

        if not flashed_items:
            return

        def _clear_flash() -> None:
            if not self.isVisible():
                return
            for row, brush in original_backgrounds.items():
                item = self.list_widget.item(row)
                if item is not None:
                    item.setBackground(brush)

        QTimer.singleShot(260, _clear_flash)

    def _on_batch_sentiment_toggled(self, sentiment: str, state: int) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        checked = state == QuadStateSlider.MODE_TRUE
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = (
            f"Apply sentiment '{sentiment}' to"
            if checked
            else f"Remove sentiment '{sentiment}' from"
        )
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                sentiments = list(getattr(chart, "sentiments", []) or [])
                if checked and sentiment not in sentiments:
                    sentiments.append(sentiment)
                if not checked:
                    sentiments = [value for value in sentiments if value != sentiment]
                chart.sentiments = sentiments
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    sentiments=sentiments,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Could not update selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_relationship_type_toggled(
        self,
        relationship_type: str,
        state:int,
    ) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        checked = state == QuadStateSlider.MODE_TRUE
        chart_ids = list(dict.fromkeys(self._selected_chart_ids()))
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        if relationship_type.lower() == "self" and checked:
            if selected_count > 1:
                QMessageBox.warning(
                    self,
                    "Batch edit not allowed",
                    "'There can be only one!' Sorry, just one chart can be tagged 'self' at a time, bud.",
                )
                self._update_batch_edit_state()
                return
            if not self._confirm_self_reassignment(chart_ids[0]):
                self._update_batch_edit_state()
                return

        action_label = (
            f"Apply relationship type '{relationship_type}' to"
            if checked
            else f"Remove relationship type '{relationship_type}' from"
        )
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                relationship_types = list(
                    getattr(chart, "relationship_types", []) or []
                )
                if checked and relationship_type not in relationship_types:
                    relationship_types.append(relationship_type)
                if not checked:
                    relationship_types = [
                        value
                        for value in relationship_types
                        if value != relationship_type
                    ]
                chart.relationship_types = relationship_types
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    relationship_types=relationship_types,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Sorry for sucking. Couldn't update selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _score_familiarity_from_factors(self, familiarity_factors: list[str]) -> int:
        selected_set = set(familiarity_factors)
        total = 0
        for item in FAMILIARITY_INDEX:
            label, weight = list(item.items())[0]
            if label in selected_set:
                total += int(weight)
        return max(1, min(10, round(normalized_familiarity_score(total))))

    def _batch_familiarity_labels_for_selection(
        self,
        chart_ids: list[int],
    ) -> list[str]:
        if len(chart_ids) != 1:
            return []
        try:
            selected_chart = load_chart(chart_ids[0])
        except Exception:
            return []
        return list(getattr(selected_chart, "familiarity_factors", []) or [])

    def _open_batch_familiarity_calculator(self) -> None:
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before using the familiarity calculator.",
            )
            return

        selected_labels = self._batch_familiarity_labels_for_selection(chart_ids)
        dialog = FamiliarityCalculatorDialog(selected_labels, self)

        def _apply_changes():
            familiarity_factors = dialog.selected_labels()
            familiarity_value = dialog.calculated_score()
            self.batch_familiarity_spin.setValue(familiarity_value)
            self.batch_familiarity_spin.setToolTip(
                ", ".join(familiarity_factors) if familiarity_factors else ""
            )
            try:
                for chart_id in chart_ids:
                    chart = load_chart(chart_id)
                    chart.familiarity_factors = list(familiarity_factors)
                    chart.familiarity = familiarity_value
                    chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                    chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                    update_chart(
                        chart_id,
                        chart,
                        retcon_time_used=getattr(chart, "retcon_time_used", False),
                    )
                    self._chart_cache[chart_id] = chart
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Batch edit error",
                    f"ARGHH...Couldn't update the selected charts:\n{exc}",
                )
                return

            changed_ids = set(chart_ids)
            self._update_sentiment_tally(
                show_progress=True,
                changed_ids=changed_ids,
            )
            self._update_batch_edit_state()
            self._refresh_filters_after_batch_edit(changed_ids)

        dialog.accepted.connect(_apply_changes)
        dialog.exec()

    def _open_chart_familiarity_calculator(self) -> None:
        selected_labels = list(getattr(self, "_chart_familiarity_factors", []))
        dialog = FamiliarityCalculatorDialog(selected_labels, self)

        def _apply_changes():
            familiarity_factors = dialog.selected_labels()
            familiarity_value = dialog.calculated_score()
            self._chart_familiarity_factors = familiarity_factors
            self.familiarity_spin.setValue(familiarity_value)
            self.familiarity_spin.setToolTip(
                ", ".join(familiarity_factors) if familiarity_factors else ""
            )
            if not self._suppress_lucygoosey:
                self._set_lucygoosey(True)
                if self._should_auto_update_sentiments():
                    self._sentiment_metrics_autosave_timer.start(2000)

        dialog.accepted.connect(_apply_changes)
        dialog.exec()

    def _on_batch_sentiment_metric_assign(
        self,
        metric_attr: str,
        metric_label: str,
        value: int | None,
    ) -> None:
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Psst...Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        display_value = "blank" if value is None else value
        action_label = f"Set {metric_label} to {display_value} for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                setattr(chart, metric_attr, value)
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"*sepukkus* Couldn't update the selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._set_batch_metric_lucygoosey_state(metric_attr, False)
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_metric_field_lucygoosey(self, field_key: str) -> None:
        if self._batch_metric_programmatic_update:
            return
        self._set_batch_metric_lucygoosey_state(field_key, True)

    def _on_batch_tags_apply(self) -> None:
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        parsed_tags = parse_tag_text(self.batch_tags_input.text())
        display_tags = ", ".join(parsed_tags) if parsed_tags else "blank"
        selected_count = len(chart_ids)
        action_label = f"Set tags to '{display_tags}' for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.tags = list(parsed_tags)
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Couldn't update selected chart tags:\n{exc}",
            )
            return

        self._batch_tags_lucygoosey = False
        changed_ids = set(chart_ids)
        self._update_tag_completers()
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _update_batch_alignment_score_label(self, value: int) -> None:
        self.batch_alignment_score_label.setText(f"Alignment score: {int(value)}")

    def _on_batch_alignment_changed(self, value: int) -> None:
        self._update_batch_alignment_score_label(value)

    def _on_batch_alignment_apply(self) -> None:
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Psst...Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        alignment_value = int(self.batch_alignment_slider.value())
        selected_count = len(chart_ids)
        action_label = f"Set alignment score to {alignment_value} for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.alignment_score = alignment_value
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"*sepukkus* Couldn't update the selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _batch_metric_widget_for_key(self, field_key: str) -> QWidget | None:
        mapping: dict[str, QWidget] = {
            "positive_sentiment_intensity": self.batch_positive_sentiment_intensity_spin,
            "negative_sentiment_intensity": self.batch_negative_sentiment_intensity_spin,
            "familiarity": self.batch_familiarity_spin,
            "year_first_encountered": self.batch_year_first_encountered_edit,
        }
        return mapping.get(field_key)

    def _set_batch_metric_lucygoosey_state(self, field_key: str, is_lucygoosey: bool) -> None:
        self._batch_metric_lucygoosey[field_key] = is_lucygoosey
        widget = self._batch_metric_widget_for_key(field_key)
        if widget is None:
            return
        style = (
            "color: #a9a9a9; font-style: italic;"
            if is_lucygoosey
            else ""
        )
        widget.setStyleSheet(style)
        if isinstance(widget, QSpinBox):
            line_edit = widget.lineEdit()
            if line_edit is not None:
                line_edit.setStyleSheet(style)

    def _on_batch_sentiment_state_changed(
        self,
        sentiment: str,
        state: int,
    ) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        self._on_batch_sentiment_toggled(sentiment, state)

    def _on_batch_relationship_type_state_changed(
        self,
        relationship_type: str,
        state: int,
    ) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        self._on_batch_relationship_type_toggled(
            relationship_type,
            state,
        )

    def _confirm_self_reassignment(self, current_chart_id: int | None) -> bool:
        existing_self = find_self_tagged_chart(exclude_chart_id=current_chart_id)
        if existing_self is None:
            return True

        _former_chart_id, former_chart_name = existing_self
        choice = QMessageBox.question(
            self,
            "There's only one you, baby. ('Self' relationship already assigned)",
            f"Remove 'self' from {former_chart_name}? y/n",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return False

        removed_ids = clear_self_tag_from_other_charts(
            current_chart_id if current_chart_id is not None else -1
        )
        for removed_id in removed_ids:
            self._chart_cache.pop(removed_id, None)
        return True

    def _on_batch_source_selected(self, index: int) -> None:
        source = self.batch_source_combo.itemData(index)
        if not source:
            return
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits, ya goose.",
            )
            self.batch_source_combo.blockSignals(True)
            self.batch_source_combo.setCurrentIndex(0)
            self.batch_source_combo.blockSignals(False)
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = f"Set chart type to '{source}' for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.source = source
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    chart_type=source,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Could not update selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_gender_selected(self, index: int) -> None:
        gender = self.batch_gender_combo.itemData(index)
        if gender == "":
            return
        resolved_gender = None if gender == "__blank__" else gender
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self.batch_gender_combo.blockSignals(True)
            self.batch_gender_combo.setCurrentIndex(0)
            self.batch_gender_combo.blockSignals(False)
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        display_gender = "blank" if resolved_gender is None else resolved_gender
        action_label = f"Set gender to '{display_gender}' for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.gender = resolved_gender
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Could not update selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_birthtime_unknown_toggled(self, state: int) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        checked = state == QuadStateSlider.MODE_TRUE
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = (
            "Mark birthtime unknown for"
            if checked
            else "Clear birthtime unknown for"
        )
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.birthtime_unknown = checked
                chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                update_chart(
                    chart_id,
                    chart,
                    birthtime_unknown=checked,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"*computer explodes* Couldn't update selected charts:\n{exc}",
            )
            return
        
        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_birthtime_unknown_state_changed(self, state: int) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        self._on_batch_birthtime_unknown_toggled(state)

    def _on_batch_deceased_toggled(self, state: int) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        checked = state == QuadStateSlider.MODE_TRUE
        chart_ids = self._selected_chart_ids()
        if not chart_ids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            self._update_batch_edit_state()
            return

        selected_count = len(chart_ids)
        action_label = "Mark as dead 💀 for" if checked else "Mark as living for"
        if not self._confirm_batch_edit(action_label, selected_count):
            self._update_batch_edit_state()
            return

        try:
            for chart_id in chart_ids:
                chart = load_chart(chart_id)
                chart.is_deceased = checked
                update_chart(
                    chart_id,
                    chart,
                    is_deceased=checked,
                    retcon_time_used=getattr(chart, "retcon_time_used", False),
                )
                self._chart_cache[chart_id] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Batch edit error",
                f"Couldn't update selected charts:\n{exc}",
            )
            return

        changed_ids = set(chart_ids)
        self._update_sentiment_tally(
            show_progress=True,
            changed_ids=changed_ids,
        )
        self._update_batch_edit_state()
        self._refresh_filters_after_batch_edit(changed_ids)

    def _on_batch_mortality_state_changed(self, state: int) -> None:
        if state == QuadStateSlider.MODE_MIXED:
            return
        self._on_batch_deceased_toggled(state)

    def _build_manage_collections_panel(self) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(6, 6, 6, 6)
        panel_layout.setSpacing(8)
        panel.setLayout(panel_layout)

        header_label = QLabel("Manage Collections")
        header_label.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        panel_layout.addWidget(header_label)

        detail_label = QLabel(
            "Default collections are auto-generated by chart type.\n"
            "Create custom collections and add/remove selected charts."
        )
        detail_label.setWordWrap(True)
        panel_layout.addWidget(detail_label)

        self.collections_list_widget = QListWidget()
        self.collections_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.collections_list_widget.itemSelectionChanged.connect(
            self._update_collection_membership_buttons
        )
        panel_layout.addWidget(self.collections_list_widget, 1)

        actions_row = QHBoxLayout()
        self.collection_create_button = QPushButton("New")
        self.collection_create_button.clicked.connect(self._on_create_custom_collection)
        self.collection_rename_button = QPushButton("Rename")
        self.collection_rename_button.clicked.connect(self._on_rename_custom_collection)
        self.collection_delete_button = QPushButton("Delete")
        self.collection_delete_button.clicked.connect(self._on_delete_custom_collection)
        actions_row.addWidget(self.collection_create_button)
        actions_row.addWidget(self.collection_rename_button)
        actions_row.addWidget(self.collection_delete_button)
        panel_layout.addLayout(actions_row)

        membership_row = QHBoxLayout()
        self.collection_add_selected_button = QPushButton("Add Selected Charts")
        self.collection_add_selected_button.clicked.connect(self._on_add_selection_to_collection)
        self.collection_remove_selected_button = QPushButton("Remove Selected Charts")
        self.collection_remove_selected_button.clicked.connect(self._on_remove_selection_from_collection)
        membership_row.addWidget(self.collection_add_selected_button)
        membership_row.addWidget(self.collection_remove_selected_button)
        panel_layout.addLayout(membership_row)
        self._update_collection_membership_buttons()

        return panel

    def _is_right_panel_collapsed(self) -> bool:
        sizes = self._content_splitter.sizes()
        return len(sizes) >= 3 and sizes[2] <= 0

    def _set_right_panel_visible(self, visible: bool, *, restore_default_size: bool = False) -> None:
        if self._right_panel_visible == visible:
            if visible and restore_default_size:
                self._content_splitter.setSizes(self._default_content_splitter_sizes())
            return
        self._right_panel_visible = visible
        self.right_panel_stack.setVisible(visible)
        if not visible:
            self._right_panel_sizes = self._content_splitter.sizes()
            sizes = self._right_panel_sizes
            if len(sizes) >= 3:
                total = sum(sizes)
                left_size = sizes[0]
                middle_size = max(0, total - left_size)
                self._content_splitter.setSizes([left_size, middle_size, 0])
            return

        if restore_default_size:
            self._content_splitter.setSizes(self._default_content_splitter_sizes())
            return

        current_total = max(1, sum(self._content_splitter.sizes()))
        left_hidden = (not self._left_panel_visible) or self._is_left_panel_collapsed()

        if self._right_panel_sizes and len(self._right_panel_sizes) >= 3:
            sizes = list(self._right_panel_sizes)
            right_size = max(0, sizes[2])
            if left_hidden:
                self._content_splitter.setSizes([0, max(0, current_total - right_size), right_size])
                return
            self._content_splitter.setSizes(sizes)
            return

        default_sizes = self._default_content_splitter_sizes()
        right_size = max(0, default_sizes[2])
        if left_hidden:
            self._content_splitter.setSizes([0, max(0, current_total - right_size), right_size])
            return
        self._content_splitter.setSizes(default_sizes)

    def _is_left_panel_collapsed(self) -> bool:
        sizes = self._content_splitter.sizes()
        return len(sizes) >= 3 and sizes[0] <= 0

    def _set_left_panel_visible(self, visible: bool, *, restore_default_size: bool = False) -> None:
        if self._left_panel_visible == visible:
            if visible and restore_default_size:
                self._content_splitter.setSizes(self._default_content_splitter_sizes())
            return
        self._left_panel_visible = visible
        self.left_panel_stack.setVisible(visible)
        if not visible:
            self._left_panel_sizes = self._content_splitter.sizes()
            sizes = self._left_panel_sizes
            if len(sizes) >= 3:
                total = sum(sizes)
                right_size = sizes[2]
                middle_size = max(0, total - right_size)
                self._content_splitter.setSizes([0, middle_size, right_size])
            return

        if restore_default_size:
            self._content_splitter.setSizes(self._default_content_splitter_sizes())
            return

        current_total = max(1, sum(self._content_splitter.sizes()))
        right_hidden = (not self._right_panel_visible) or self._is_right_panel_collapsed()

        if self._left_panel_sizes and len(self._left_panel_sizes) >= 3:
            sizes = self._normalize_content_splitter_sizes(self._left_panel_sizes)
            left_size = max(0, sizes[0])
            if right_hidden:
                self._content_splitter.setSizes([left_size, max(0, current_total - left_size), 0])
                return
            self._content_splitter.setSizes(sizes)
            return

        default_sizes = self._default_content_splitter_sizes()
        left_size = max(0, default_sizes[0])
        if right_hidden:
            self._content_splitter.setSizes([left_size, max(0, current_total - left_size), 0])
            return
        self._content_splitter.setSizes(default_sizes)

    def _show_left_panel(self, panel_name: str) -> None:
        try:
            widget = self._left_panel_widgets[panel_name]
        except KeyError as exc:
            raise ValueError(f"Unknown panel name: {panel_name}") from exc
        self.left_panel_stack.setCurrentWidget(widget)
        self._active_left_panel = panel_name
        self._set_left_panel_visible(True)

        if panel_name == "database_metrics":
            self.database_metrics_panel_header_label.setText("Database Analytics")
            self._database_metrics_baseline_mode = "database"
            self._settings.setValue(
                "manage_charts/database_metrics_baseline_mode",
                self._database_metrics_baseline_mode,
            )
            self._sync_gen_pop_panel_visibility()
            self._sync_database_metrics_section_visibility()
            self._update_position_sign_subheader()
            self._update_gender_subheader()
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
            )
        elif panel_name == "gen_pop_norms":
            self.database_metrics_panel_header_label.setText("General Population")
            self._database_metrics_baseline_mode = "gen_pop"
            self._settings.setValue(
                "manage_charts/database_metrics_baseline_mode",
                self._database_metrics_baseline_mode,
            )
            self._sync_gen_pop_panel_visibility()
            self._sync_database_metrics_section_visibility()
            self._update_position_sign_subheader()
            self._update_gender_subheader()
            self._update_sentiment_tally(
                update_database_metrics=True,
                update_similarities=False,
            )
        elif panel_name == "similarities":
            self._update_sentiment_tally(
                update_database_metrics=False,
                update_similarities=True,
            )

    def _toggle_database_metrics_panel(self) -> None:
        if (
            self._left_panel_visible
            and self._active_left_panel == "database_metrics"
            and not self._is_left_panel_collapsed()
        ):
            self._set_left_panel_visible(False)
            return
        self._show_left_panel("database_metrics")

    def _toggle_gen_pop_norms_panel(self) -> None:
        if (
            self._left_panel_visible
            and self._active_left_panel == "gen_pop_norms"
            and not self._is_left_panel_collapsed()
        ):
            self._set_left_panel_visible(False)
            return
        self._show_left_panel("gen_pop_norms")

    def _toggle_todays_transits_panel(self) -> None:
        if (
            self._left_panel_visible
            and self._active_left_panel == "todays_transits"
            and not self._is_left_panel_collapsed()
        ):
            self._set_left_panel_visible(False)
            return
        self._refresh_todays_transits_panel()
        self._show_left_panel("todays_transits")

    def _toggle_similarities_panel(self) -> None:
        if (
            self._left_panel_visible
            and self._active_left_panel == "similarities"
            and not self._is_left_panel_collapsed()
        ):
            self._set_left_panel_visible(False)
            return
        self._show_left_panel("similarities")

    def _show_database_analytics_panel(self) -> None:
        self._show_left_panel("database_metrics")

    def _show_current_transits_panel(self) -> None:
        self._refresh_todays_transits_panel()
        self._show_left_panel("todays_transits")

    def _show_similarities_panel(self) -> None:
        self._show_left_panel("similarities")

    def _show_gen_pop_comparison_panel(self) -> None:
        self._show_left_panel("gen_pop_norms")

    def _show_manage_collections_panel(self) -> None:
        self._show_right_panel("manage_collections")

    def _show_search_database_panel(self) -> None:
        self._show_right_panel("search")

    def _run_main_window_chart_action(self, action_name: str) -> None:
        parent = self.parent()
        if parent is None or not hasattr(parent, "_run_chart_action_from_active_context"):
            QMessageBox.warning(self, "Chart action", "Unable to access chart actions.")
            return
        parent._run_chart_action_from_active_context(action_name, requester=self)

    def _on_menu_interpret_astro_age(self) -> None:
        self._run_main_window_chart_action("interpret_astro_age")

    def _on_menu_create_gemstone_chart(self) -> None:
        self._run_main_window_chart_action("create_gemstone_chartwheel")

    def _on_menu_get_personal_transit(self) -> None:
        self._run_main_window_chart_action("get_personal_transit")

    def _on_menu_export_chart(self) -> None:
        self._run_main_window_chart_action("export_chart")

    def _on_menu_open_bazi_window(self) -> None:
        self._run_main_window_chart_action("open_bazi_window")

    def _on_menu_get_human_design_info(self) -> None:
        self._run_main_window_chart_action("get_human_design_info")

    def _ensure_right_panel_widget(self, panel_name: str) -> QWidget:
        if panel_name == "search":
            widget = self.search_panel_scroll
        elif panel_name == "edit":
            widget = self.edit_panel_scroll
        elif panel_name == "manage_collections":
            widget = self.manage_collections_panel_scroll
        else:
            raise ValueError(f"Unknown panel name: {panel_name}")
        if self.right_panel_stack.indexOf(widget) == -1:
            self.right_panel_stack.addWidget(widget)
        return widget

    def _show_right_panel(self, panel_name: str) -> None:
        try:
            widget = self._right_panel_widgets[panel_name]
        except KeyError as exc:
            raise ValueError(f"Unknown panel name: {panel_name}") from exc
        self.right_panel_stack.setCurrentWidget(widget)
        self._active_right_panel = panel_name
        self._set_right_panel_visible(True)

    def _toggle_search_panel(self) -> None:
        if (
            self._right_panel_visible
            and self._active_right_panel == "search"
            and not self._is_right_panel_collapsed()
        ):
            self._set_right_panel_visible(False)
            return
        self._show_right_panel("search")

    def _toggle_edit_panel(self) -> None:
        if (
            self._right_panel_visible
            and self._active_right_panel == "edit"
            and not self._is_right_panel_collapsed()
        ):
            self._set_right_panel_visible(False)
            return
        self._show_right_panel("edit")
        self._update_batch_edit_state()

    def _toggle_manage_collections_panel(self) -> None:
        if (
            self._right_panel_visible
            and self._active_right_panel == "manage_collections"
            and not self._is_right_panel_collapsed()
        ):
            self._set_right_panel_visible(False)
            return
        self._show_right_panel("manage_collections")

    def _refresh_collection_controls(self) -> None:
        active_collection_id = self._coerce_active_collection_id(self._active_collection_id)
        self._active_collection_id = active_collection_id
        self.collection_combo.blockSignals(True)
        self.collection_combo.clear()
        for collection_label, collection_id in DEFAULT_COLLECTION_OPTIONS:
            self.collection_combo.addItem(collection_label, collection_id)
        if self._show_possible_duplicates_collection:
            self.collection_combo.addItem(
                "*possible duplicates*",
                DEFAULT_COLLECTION_POSSIBLE_DUPLICATES,
            )
        for custom_collection in sorted(
            self._custom_collections.values(),
            key=lambda collection: collection.name.casefold(),
        ):
            self.collection_combo.addItem(custom_collection.name, custom_collection.collection_id)
        active_index = self.collection_combo.findData(active_collection_id)
        self.collection_combo.setCurrentIndex(max(0, active_index))
        self.collection_combo.blockSignals(False)
        self._refresh_collection_list_widget()

    def _refresh_collection_list_widget(self) -> None:
        if not hasattr(self, "collections_list_widget"):
            return
        self.collections_list_widget.clear()
        for collection_label, _collection_id in DEFAULT_COLLECTION_OPTIONS:
            item = QListWidgetItem(f"{collection_label} (default)")
            item.setData(Qt.UserRole, "")
            item.setFlags(Qt.ItemIsEnabled)
            self.collections_list_widget.addItem(item)
        for custom_collection in sorted(
            self._custom_collections.values(),
            key=lambda collection: collection.name.casefold(),
        ):
            item = QListWidgetItem(custom_collection.name)
            item.setData(Qt.UserRole, custom_collection.collection_id)
            self.collections_list_widget.addItem(item)
        self._update_collection_membership_buttons()

    def _update_collection_membership_buttons(self) -> None:
        selected_count = len(self.list_widget.selectedItems()) if hasattr(self, "list_widget") else 0
        selected_collection = self.collections_list_widget.currentItem()
        selected_collection_name = (
            selected_collection.text().strip()
            if selected_collection is not None
            else ""
        )
        can_manage_membership = selected_count > 0 and bool(selected_collection_name)

        if can_manage_membership:
            self.collection_add_selected_button.setText(
                f"Add {selected_count} to {selected_collection_name}"
            )
        else:
            self.collection_add_selected_button.setText("Add Selected Charts")

        self.collection_add_selected_button.setEnabled(can_manage_membership)
        self.collection_remove_selected_button.setEnabled(can_manage_membership)

        inactive_style = INACTIVE_ACTION_BUTTON_STYLE if not can_manage_membership else ""
        self.collection_add_selected_button.setStyleSheet(inactive_style)
        self.collection_remove_selected_button.setStyleSheet(inactive_style)

    def _on_collection_changed(self, index: int) -> None:
        previous_collection_id = self._active_collection_id
        collection_id = normalize_collection_id(self.collection_combo.itemData(index))
        self._active_collection_id = self._coerce_active_collection_id(collection_id)
        if (
            self._show_possible_duplicates_collection
            and previous_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES
            and self._active_collection_id != DEFAULT_COLLECTION_POSSIBLE_DUPLICATES
        ):
            self._show_possible_duplicates_collection = False
            self._refresh_collection_controls()
        persisted_collection_id = (
            DEFAULT_COLLECTION_ALL
            if self._active_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES
            else self._active_collection_id
        )
        self._settings.setValue("manage_charts/active_collection_id", persisted_collection_id)
        self._populate_list()

    def _on_check_for_duplicates(self) -> None:
        rows = [
            normalized
            for row in self._chart_rows
            if (normalized := self._normalize_chart_row(row)) is not None
        ]
        duplicate_ids, related_names = find_possible_duplicate_charts(
            rows,
            load_chart=self._get_chart_for_filter,
            similarity_threshold_percent=90.0,
            similarity_ceiling_percent=100.0,
        )
        if not duplicate_ids:
            self._possible_duplicate_chart_ids = set()
            self._possible_duplicate_related_names = {}
            self._show_possible_duplicates_collection = False
            if self._active_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES:
                self._active_collection_id = DEFAULT_COLLECTION_ALL
            self._refresh_collection_controls()
            self._populate_list()
            QMessageBox.information(
                self,
                "Possible duplicates",
                "No possible duplicates were found from names, birthdays, or 90–100% chart similarity.",
            )
            return
        self._possible_duplicate_chart_ids = duplicate_ids
        self._possible_duplicate_related_names = related_names
        self._show_possible_duplicates_collection = True
        self._active_collection_id = DEFAULT_COLLECTION_POSSIBLE_DUPLICATES
        self._refresh_collection_controls()
        self._populate_list()

    @staticmethod
    def _normalize_duplicate_name(value: object) -> str:
        text = str(value or "").strip().casefold()
        if not text:
            return ""
        return re.sub(r"[^a-z0-9]+", "", text)

    def _compute_possible_duplicate_chart_ids(
        self,
        rows: list[
            tuple[
                int,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
                str | None,
                int,
                int,
                int,
                int,
                int,
                int | None,
                int,
                str,
                int,
                int,
                int | None,
                int | None,
                int | None,
            ]
        ],
    ) -> set[int]:
        duplicate_ids: set[int] = set()
        birthday_groups: dict[tuple[int, int], list[int]] = {}
        name_groups: dict[str, list[int]] = {}
        names_by_id: dict[int, str] = {}
        for row in rows:
            chart_id = int(row[0])
            birth_month = row[17]
            birth_day = row[18]
            if isinstance(birth_month, int) and isinstance(birth_day, int):
                birthday_key = (birth_month, birth_day)
                birthday_groups.setdefault(birthday_key, []).append(chart_id)

            normalized_name = self._normalize_duplicate_name(row[1] or row[2] or "")
            if normalized_name:
                names_by_id[chart_id] = normalized_name
                name_groups.setdefault(normalized_name, []).append(chart_id)

        for chart_ids in birthday_groups.values():
            if len(chart_ids) >= 2:
                duplicate_ids.update(chart_ids)
        for chart_ids in name_groups.values():
            if len(chart_ids) >= 2:
                duplicate_ids.update(chart_ids)

        buckets: dict[str, list[tuple[int, str]]] = {}
        for chart_id, name in names_by_id.items():
            bucket_key = name[:1]
            buckets.setdefault(bucket_key, []).append((chart_id, name))
        for bucket_entries in buckets.values():
            for index, (left_id, left_name) in enumerate(bucket_entries):
                for right_id, right_name in bucket_entries[index + 1 :]:
                    if left_id == right_id:
                        continue
                    if abs(len(left_name) - len(right_name)) > 2:
                        continue
                    score = SequenceMatcher(None, left_name, right_name).ratio()
                    if score >= 0.88:
                        duplicate_ids.add(left_id)
                        duplicate_ids.add(right_id)
        return duplicate_ids

    def _selected_custom_collection_id(self) -> str | None:
        current_item = self.collections_list_widget.currentItem()
        if current_item is None:
            return None
        value = current_item.data(Qt.UserRole)
        collection_id = normalize_collection_id(value)
        if not collection_id or collection_id in DEFAULT_COLLECTION_IDS:
            return None
        if collection_id not in self._custom_collections:
            return None
        return collection_id

    def _on_create_custom_collection(self) -> None:
        name, accepted = QInputDialog.getText(self, "New Collection", "Collection name:")
        if not accepted:
            return
        clean_name = sanitize_collection_name(name)
        base_id = normalize_collection_id(clean_name.replace(" ", "_"))
        candidate = base_id
        suffix = 2
        while candidate in DEFAULT_COLLECTION_IDS or candidate in self._custom_collections:
            candidate = f"{base_id}_{suffix}"
            suffix += 1
        self._custom_collections[candidate] = CustomCollection(
            collection_id=candidate,
            name=clean_name,
            chart_ids=frozenset(),
        )
        self._save_custom_collections_to_settings()
        self._refresh_collection_controls()

    def _on_rename_custom_collection(self) -> None:
        collection_id = self._selected_custom_collection_id()
        if collection_id is None:
            QMessageBox.information(self, "Rename Collection", "Select a custom collection first.")
            return
        collection = self._custom_collections[collection_id]
        name, accepted = QInputDialog.getText(
            self,
            "Rename Collection",
            "Collection name:",
            text=collection.name,
        )
        if not accepted:
            return
        clean_name = sanitize_collection_name(name)
        self._custom_collections[collection_id] = CustomCollection(
            collection_id=collection.collection_id,
            name=clean_name,
            chart_ids=collection.chart_ids,
        )
        self._save_custom_collections_to_settings()
        self._refresh_collection_controls()

    def _on_delete_custom_collection(self) -> None:
        collection_id = self._selected_custom_collection_id()
        if collection_id is None:
            QMessageBox.information(self, "Delete Collection", "Select a custom collection first.")
            return
        collection = self._custom_collections[collection_id]
        answer = QMessageBox.question(
            self,
            "Delete Collection",
            f"Delete '{collection.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._custom_collections.pop(collection_id, None)
        if self._active_collection_id == collection_id:
            self._active_collection_id = DEFAULT_COLLECTION_ALL
            self._settings.setValue("manage_charts/active_collection_id", self._active_collection_id)
        self._save_custom_collections_to_settings()
        self._refresh_collection_controls()
        self._populate_list()

    def _on_add_selection_to_collection(self) -> None:
        collection_id = self._selected_custom_collection_id()
        if collection_id is None:
            QMessageBox.information(self, "Collections", "Select a custom collection first.")
            return
        chart_ids = set(self._selected_chart_ids())
        if not chart_ids:
            QMessageBox.information(self, "Collections", "Select one or more charts first.")
            return
        collection = self._custom_collections[collection_id]
        updated_ids = set(collection.chart_ids)
        updated_ids.update(chart_ids)
        self._custom_collections[collection_id] = CustomCollection(
            collection_id=collection.collection_id,
            name=collection.name,
            chart_ids=frozenset(updated_ids),
        )
        self._save_custom_collections_to_settings()
        self._refresh_collection_controls()
        self._populate_list()

    def _on_remove_selection_from_collection(self) -> None:
        collection_id = self._selected_custom_collection_id()
        if collection_id is None:
            QMessageBox.information(self, "Collections", "Select a custom collection first.")
            return
        chart_ids = set(self._selected_chart_ids())
        if not chart_ids:
            QMessageBox.information(self, "Collections", "Select one or more charts first.")
            return
        collection = self._custom_collections[collection_id]
        updated_ids = {int(chart_id) for chart_id in collection.chart_ids}
        updated_ids.difference_update(chart_ids)
        self._custom_collections[collection_id] = CustomCollection(
            collection_id=collection.collection_id,
            name=collection.name,
            chart_ids=frozenset(updated_ids),
        )
        self._save_custom_collections_to_settings()
        self._refresh_collection_controls()
        self._populate_list()

    def _clear_batch_edits(self) -> None:
        if hasattr(self, "_batch_last_selection_ids"):
            self._batch_last_selection_ids = set()
        if hasattr(self, "_batch_selection_order"):
            self._batch_selection_order = []
        for checkbox in self.batch_sentiment_checkboxes.values():
            self._set_batch_checkbox_state(checkbox, QuadStateSlider.MODE_EMPTY)
        for checkbox in self.batch_relationship_type_checkboxes.values():
            self._set_batch_checkbox_state(checkbox, QuadStateSlider.MODE_EMPTY)
        self.batch_source_combo.blockSignals(True)
        self.batch_source_combo.setCurrentIndex(0)
        self.batch_source_combo.setToolTip("")
        self.batch_source_combo.blockSignals(False)
        self.batch_gender_combo.blockSignals(True)
        self.batch_gender_combo.setCurrentIndex(0)
        self.batch_gender_combo.setToolTip("")
        self.batch_gender_combo.blockSignals(False)
        self._set_batch_checkbox_state(
            self.batch_birthtime_unknown_checkbox,
            QuadStateSlider.MODE_EMPTY,
        )
        self._set_batch_checkbox_state(
            self.batch_deceased_checkbox,
            QuadStateSlider.MODE_EMPTY,
        )
        self.batch_positive_sentiment_intensity_spin.setValue(1)
        self.batch_positive_sentiment_intensity_spin.setToolTip("")
        self.batch_negative_sentiment_intensity_spin.setValue(1)
        self.batch_negative_sentiment_intensity_spin.setToolTip("")
        self.batch_familiarity_spin.setValue(1)
        self.batch_familiarity_spin.setToolTip("")
        self.batch_year_first_encountered_edit.setText("")
        self.batch_year_first_encountered_edit.setToolTip("")
        if hasattr(self, "batch_tags_input"):
            self.batch_tags_input.setText("")
            self.batch_tags_input.setToolTip("")
        if hasattr(self, "batch_tags_preview_label"):
            self.batch_tags_preview_label.setText("")
        if hasattr(self, "batch_tags_selection_label"):
            self.batch_tags_selection_label.setText("")
        self._batch_tags_lucygoosey = False
        self.batch_alignment_slider.blockSignals(True)
        self.batch_alignment_slider.setValue(0)
        self.batch_alignment_slider.blockSignals(False)
        self._update_batch_alignment_score_label(0)
        self.batch_alignment_slider.setToolTip("")
        if hasattr(self, "_batch_metric_lucygoosey"):
            for metric_key in ("positive_sentiment_intensity", "negative_sentiment_intensity", "familiarity", "year_first_encountered"):
                self._set_batch_metric_lucygoosey_state(metric_key, False)



    def _default_content_splitter_sizes(self) -> list[int]:
        return [387, 530, 420]

    def _normalize_content_splitter_sizes(self, sizes: list[int]) -> list[int]:
        if len(sizes) < 3:
            return self._default_content_splitter_sizes()

        normalized = [max(0, int(size)) for size in sizes[:3]]
        if not self._left_panel_visible:
            normalized[0] = 0
            return normalized

        min_left_width = max(self._left_panel_widgets["database_metrics"].minimumWidth(), 320)
        if normalized[0] >= min_left_width:
            return normalized

        needed = min_left_width - normalized[0]
        normalized[0] = min_left_width

        take_from_middle = min(needed, normalized[1])
        normalized[1] -= take_from_middle
        needed -= take_from_middle

        if needed > 0:
            take_from_right = min(needed, normalized[2])
            normalized[2] -= take_from_right

        return normalized

    def _restore_window_settings(self) -> None:
        splitter_key = "manage_charts/splitter_sizes"
        sizes = self._settings.value(splitter_key)
        if sizes:
            restored_sizes = [int(size) for size in sizes]
            self._content_splitter.setSizes(
                self._normalize_content_splitter_sizes(restored_sizes)
            )
        else:
            self._content_splitter.setSizes(self._default_content_splitter_sizes())

        stored_active_left_panel = self._settings.value(
            "manage_charts/active_left_panel",
            "todays_transits",
        )
        if isinstance(stored_active_left_panel, str) and stored_active_left_panel in self._left_panel_widgets:
            self._active_left_panel = stored_active_left_panel
        self.left_panel_stack.setCurrentWidget(self._left_panel_widgets[self._active_left_panel])

        stored_left_panel_visible = self._settings.value("manage_charts/left_panel_visible", "1")
        self._left_panel_visible = str(stored_left_panel_visible).lower() in {"1", "true", "yes"}
        self.left_panel_stack.setVisible(self._left_panel_visible)

        stored_active_right_panel = self._settings.value(
            "manage_charts/active_right_panel",
            "search",
        )
        if isinstance(stored_active_right_panel, str) and stored_active_right_panel in self._right_panel_widgets:
            self._active_right_panel = stored_active_right_panel
        self.right_panel_stack.setCurrentWidget(self._right_panel_widgets[self._active_right_panel])

        stored_right_panel_visible = self._settings.value("manage_charts/right_panel_visible", "1")
        self._right_panel_visible = str(stored_right_panel_visible).lower() in {"1", "true", "yes"}
        self.right_panel_stack.setVisible(self._right_panel_visible)
        self.apply_launch_window_policy()

    def adopt_window_placement(self, source_window: QWidget | None) -> None:
        if source_window is None:
            return
        apply_window_placement(self, capture_window_placement(source_window))

    def apply_launch_window_policy(self) -> None:
        # Do not force Database View back to the primary screen or maximized state.
        # MainWindow coordinates placement handoff to avoid dual-monitor jumps.
        clear_fullscreen_and_minimized(self)
        self.raise_()
        self.activateWindow()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.setWindowState(
                (self.windowState() & ~Qt.WindowFullScreen) | Qt.WindowMaximized
            )
            return
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_help_scrim"):
            self._help_resize_overlay()
        # if self._help_overlay_active:
        #     self._rebuild_help_markers()

    def closeEvent(self, event) -> None:
        if self._help_overlay_active:
            self._disable_help_overlay()
        if self._size_checker_popup is not None:
            self._size_checker_popup.close()
            self._size_checker_popup = None
        self._settings.remove("manage_charts/geometry")
        self._settings.setValue(
            "manage_charts/splitter_sizes", self._content_splitter.sizes()
        )
        self._settings.setValue("manage_charts/sort_mode", self._sort_mode)
        self._settings.setValue(
            "manage_charts/sign_distribution_mode", self._sign_distribution_mode
        )
        self._settings.setValue(
            "manage_charts/species_distribution_mode", self._species_distribution_mode
        )
        self._settings.setValue("manage_charts/active_left_panel", self._active_left_panel)
        self._settings.setValue("manage_charts/left_panel_visible", int(self._left_panel_visible))
        self._settings.setValue("manage_charts/active_right_panel", self._active_right_panel)
        self._settings.setValue("manage_charts/right_panel_visible", int(self._right_panel_visible))
        persisted_collection_id = (
            DEFAULT_COLLECTION_ALL
            if self._active_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES
            else self._active_collection_id
        )
        self._settings.setValue("manage_charts/active_collection_id", persisted_collection_id)
        self._save_custom_collections_to_settings()
        self._settings.setValue("app/last_view", "database")

        parent = self.parent()
        if isinstance(parent, MainWindow):
            parent.allow_close_for_app_exit()

        super().closeEvent(event)

        #prevents ghost windows lingering
        if event.isAccepted():
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def _searchable_bodies(self) -> list[tuple[str, str]]:
        return [
            ("Sun", "Sun"),
            ("Moon", "Moon"),
            ("Mercury", "Mercury"),
            ("Venus", "Venus"),
            ("Mars", "Mars"),
            ("Jupiter", "Jupiter"),
            ("Saturn", "Saturn"),
            ("Uranus", "Uranus"),
            ("Neptune", "Neptune"),
            ("Pluto", "Pluto"),
            ("Rahu", "Rahu"),
            ("Ketu", "Ketu"),
            ("Chiron", "Chiron"),
            ("Ceres", "Ceres"),
            ("Pallas", "Pallas"),
            ("Juno", "Juno"),
            ("Vesta", "Vesta"),
            ("Lilith", "Lilith"),
            ("Part of Fortune", "Part of Fortune"),
            ("AS", "AS"),
            ("IC", "IC"),
            ("DS", "DS"),
            ("MC", "MC"),
        ]

    def _searchable_body_options(self) -> list[tuple[str, str]]:
        return [("Any", "Any"), *self._searchable_bodies()]

    def _clear_filter_selection(self) -> None:
        if not self.list_widget.selectedItems():
            return
        blocker = QSignalBlocker(self.list_widget)
        self.list_widget.clearSelection()
        blocker.unblock()

    def _on_filter_changed(self, *_: object) -> None:
        if self._suppress_filter_refresh:
            return
        self._filter_refresh_pending = True
        self._filter_refresh_timer.start()

    def _run_scheduled_filter_refresh(self) -> None:
        if self._suppress_filter_refresh:
            return
        if self._filter_refresh_running:
            self._filter_refresh_pending = True
            self._filter_refresh_timer.start()
            return
        if not self._filter_refresh_pending:
            return
        self._filter_refresh_pending = False
        self._filter_refresh_running = True
        try:
            if self.list_widget.selectedItems():
                blocker = QSignalBlocker(self.list_widget)
                self.list_widget.clearSelection()
                blocker.unblock()
            self._populate_list()
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Filter error",
                f"Could not apply filters:\n{exc}",
            )
        finally:
            self._filter_refresh_running = False
        if self._filter_refresh_pending:
            self._filter_refresh_timer.start()

    def _on_astrological_filter_changed(self, *_: object) -> None:
        self._auto_exclude_placeholders_for_astrological_filters()
        self._on_filter_changed()

    def _has_active_astrological_filters(self) -> bool:
        if any(
            filters["sign"].currentText() != "Any"
            or filters["house"].currentText() != "Any"
            for filters in self._search_body_filters
        ):
            return True
        if any(
            str(filters["planet_1"].currentData()) != "Any"
            or str(filters["aspect"].currentData()) != "Any"
            or str(filters["planet_2"].currentData()) != "Any"
            for filters in self._aspect_filters
        ):
            return True
        if any(
            filters["sign"].currentText() != "Any"
            for filters in self._dominant_sign_filters
        ):
            return True
        if any(
            str(filters["planet"].currentData()) != "Any"
            for filters in self._dominant_planet_filters
        ):
            return True
        if any(
            filters["mode"].currentData() != "Any"
            for filters in self._dominant_mode_filters
        ):
            return True
        if (
            self._dominant_element_primary_combo is not None
            and self._dominant_element_primary_combo.currentData() != "Any"
        ):
            return True
        if (
            self._dominant_element_secondary_combo is not None
            and self._dominant_element_secondary_combo.currentData() != "Any"
        ):
            return True
        return False

    def _auto_exclude_placeholders_for_astrological_filters(self) -> None:
        if self._suppress_filter_refresh:
            return
        if self.incomplete_birthdate_checkbox.mode() != QuadStateSlider.MODE_EMPTY:
            return
        if not self._has_active_astrological_filters():
            return
        blocker = QSignalBlocker(self.incomplete_birthdate_checkbox)
        self.incomplete_birthdate_checkbox.setMode(QuadStateSlider.MODE_FALSE)
        blocker.unblock()

    def _clear_filters(self, refresh: bool = True) -> None:
        self._suppress_filter_refresh = True
        try:
            self._clear_batch_edits()
            self._clear_filter_selection()
            self.incomplete_birthdate_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            self.birthtime_unknown_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            self.retconned_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            if self.living_checkbox is not None:
                self.living_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            for checkbox in self.generation_filter_checkboxes.values():
                checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            for checkbox in self.chart_type_filter_checkboxes.values():
                checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            self.species_filter_combo.setCurrentIndex(0)
            self.search_text_input.setText("")
            if hasattr(self, "search_tags_input") and self.search_tags_input is not None:
                self.search_tags_input.setText("")
            if (
                hasattr(self, "search_untagged_checkbox")
                and self.search_untagged_checkbox is not None
            ):
                self.search_untagged_checkbox.setChecked(False)
            for checkbox in self.sentiment_filter_checkboxes.values():
                checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            if self._positive_sentiment_intensity_min_input is not None:
                self._positive_sentiment_intensity_min_input.setText("")
            if self._positive_sentiment_intensity_max_input is not None:
                self._positive_sentiment_intensity_max_input.setText("")
            if self._negative_sentiment_intensity_min_input is not None:
                self._negative_sentiment_intensity_min_input.setText("")
            if self._negative_sentiment_intensity_max_input is not None:
                self._negative_sentiment_intensity_max_input.setText("")
            if self._familiarity_min_input is not None:
                self._familiarity_min_input.setText("")
            if self._familiarity_max_input is not None:
                self._familiarity_max_input.setText("")
            if self._alignment_score_min_input is not None:
                self._alignment_score_min_input.setText("")
            if self._alignment_score_max_input is not None:
                self._alignment_score_max_input.setText("")
            if self._alignment_score_blank_checkbox is not None:
                self._alignment_score_blank_checkbox.setChecked(False)
            if self._notes_comments_filter_checkbox is not None:
                self._notes_comments_filter_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            if self._notes_comments_filter_input is not None:
                self._notes_comments_filter_input.setText("")
            if self._notes_source_filter_checkbox is not None:
                self._notes_source_filter_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            if self._notes_source_filter_input is not None:
                self._notes_source_filter_input.setText("")
            for checkbox in self.relationship_filter_checkboxes.values():
                checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            for checkbox in self.gender_filter_checkboxes.values():
                checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            self.birth_status_filter_or.setChecked(False)
            self.birth_status_filter_and.setChecked(True)
            self.sentiment_filter_or.setChecked(False)
            self.sentiment_filter_and.setChecked(True)
            self.relationship_filter_or.setChecked(False)
            self.relationship_filter_and.setChecked(True)
            self.gender_filter_or.setChecked(False)
            self.gender_filter_and.setChecked(True)
            self.gender_guessed_filter_combo.setCurrentIndex(0)
            for filters in self._search_body_filters:
                filters["body"].setCurrentIndex(0)
                filters["sign"].setCurrentIndex(0)
                filters["house"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
            for filters in self._aspect_filters:
                filters["planet_1"].setCurrentIndex(0)
                filters["aspect"].setCurrentIndex(0)
                filters["planet_2"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
            for filters in self._dominant_sign_filters:
                filters["sign"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
            for filters in self._dominant_planet_filters:
                filters["planet"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
            for filters in self._dominant_mode_filters:
                filters["mode"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
            if self._year_first_encountered_earliest_input is not None:
                self._year_first_encountered_earliest_input.setText("")
            if self._year_first_encountered_latest_input is not None:
                self._year_first_encountered_latest_input.setText("")
            if self._year_first_encountered_blank_checkbox is not None:
                self._year_first_encountered_blank_checkbox.setMode(QuadStateSlider.MODE_EMPTY)
            if self._dominant_element_primary_combo is not None:
                self._dominant_element_primary_combo.setCurrentIndex(0)
            if self._dominant_element_secondary_combo is not None:
                self._dominant_element_secondary_combo.setCurrentIndex(0)
        finally:
            self._suppress_filter_refresh = False
        if refresh:
            self._on_filter_changed()

    def _on_selection_changed(self) -> None:
        self._cancel_inline_chart_rename()
        active_left_scrollbar = None
        active_left_scroll_value = None
        if self._left_panel_visible:
            active_left_panel = self._left_panel_widgets.get(self._active_left_panel)
            if isinstance(active_left_panel, QScrollArea):
                active_left_scrollbar = active_left_panel.verticalScrollBar()
                active_left_scroll_value = active_left_scrollbar.value()

        if self._right_panel_visible and self._active_right_panel == "edit":
            self._update_batch_edit_state()
        self._update_batch_edit_action_buttons()
        self._update_collection_membership_buttons()
        try:
            self._update_sentiment_tally(
                update_database_metrics=(
                    self._left_panel_visible
                    and self._active_left_panel in {"database_metrics", "gen_pop_norms"}
                ),
                update_similarities=(
                    self._left_panel_visible
                    and self._active_left_panel == "similarities"
                ),
            )
        finally:
            if active_left_scrollbar is not None and active_left_scroll_value is not None:
                self._restore_scrollbar_position(
                    active_left_scrollbar,
                    active_left_scroll_value,
                )

    def _update_batch_edit_action_buttons(self) -> None:
        selected_count = len(self.list_widget.selectedItems()) if hasattr(self, "list_widget") else 0
        if hasattr(self, "batch_delete_chart_button"):
            chart_label = "Chart" if selected_count == 1 else "Charts"
            self.batch_delete_chart_button.setText(
                f"❌ Delete {selected_count} {chart_label}"
            )
        if hasattr(self, "batch_rename_chart_button"):
            rename_enabled = selected_count == 1
            self.batch_rename_chart_button.setEnabled(rename_enabled)

    def _on_import_csv(self) -> None:
        self._on_import_csv_type_1()

    def _on_append_database_placeholder(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Append database",
            "",
            "Database Files (*.db)",
        )
        if not file_path:
            return

        backup_path = None
        try:
            backup_path = backup_database()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Backup failed",
                f"Could not back up the current database before append:\n{exc}",
            )
            return

        try:
            result = append_database(Path(file_path))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Append failed",
                (
                    "Could not append the selected database.\n"
                    f"Reason: {exc}\n\n"
                    f"Backup path: {backup_path}"
                ),
            )
            return

        self._refresh_charts(force_full_analysis_refresh=True)

        imported = int(result.get("imported", 0) or 0)
        skipped = int(result.get("skipped", 0) or 0)
        warnings = int(result.get("warnings", 0) or 0)
        issues = list(result.get("issues", []) or [])

        detail_lines: list[str] = []
        for issue in issues:
            severity = str(issue.get("severity", "warning")).upper()
            chart_id = issue.get("chart_id")
            chart_label = f"#{chart_id}" if chart_id is not None else "#?"
            chart_name = str(issue.get("name") or "Unnamed")
            error_text = str(issue.get("error") or "Unknown issue.")
            detail_lines.append(f"[{severity}] {chart_label} {chart_name}: {error_text}")
        details = "\n".join(detail_lines).strip()

        summary = (
            f"Appended {imported} chart(s).\n"
            f"Warnings flagged (⚠️): {warnings}\n"
            f"Skipped rows: {skipped}\n"
            f"Database backup: {backup_path}"
        )
        if issues:
            summary += "\n\nReview details for concerns/errors by chart."

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Append database complete")
        dialog.setIcon(
            QMessageBox.Warning
            if issues
            else QMessageBox.Information
        )
        dialog.setText(summary)
        if details:
            dialog.setDetailedText(details)
        dialog.exec()

    def _on_rename_selected_chart(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if len(selected_items) != 1:
            return
        self._start_inline_chart_rename(selected_items[0])

    def _start_inline_chart_rename(self, item: QListWidgetItem) -> None:
        chart_id = item.data(Qt.UserRole)
        if chart_id is None:
            return

        active_chart_id = getattr(self, "_inline_rename_chart_id", None)
        active_editor = getattr(self, "_inline_rename_editor", None)
        if active_chart_id == chart_id and isinstance(active_editor, QLineEdit):
            active_editor.setFocus()
            active_editor.selectAll()
            return

        self._cancel_inline_chart_rename()

        metadata = item.data(Qt.UserRole + 1) or {}
        current_name = str(metadata.get("raw_name", "")).strip() or "Unnamed"
        original_text = item.text()

        inline_editor = QLineEdit(current_name)
        inline_editor.setPlaceholderText("Chart name")
        inline_editor.setMinimumHeight(24)
        inline_editor.setStyleSheet(
            "QLineEdit {"
            "background-color: #121212;"
            "border: 1px solid #2f7f2f;"
            "color: #e8ffe8;"
            "padding: 2px 6px;"
            "}"
        )

        save_button = QPushButton("✅")
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setToolTip("Save chart name")
        save_button.setFixedWidth(34)
        save_button.setStyleSheet(
            "QPushButton {"
            "background-color: #1f6f1f;"
            "border: 1px solid #2f9f2f;"
            "color: #d8ffd8;"
            "font-weight: 700;"
            "padding: 0px;"
            "}"
            "QPushButton:hover { background-color: #2a8a2a; }"
        )

        inline_container = QWidget(self.list_widget)
        inline_layout = QHBoxLayout(inline_container)
        inline_layout.setContentsMargins(4, 2, 4, 2)
        inline_layout.setSpacing(4)
        inline_layout.addWidget(inline_editor, 1)
        inline_layout.addWidget(save_button, 0)
        inline_container.setLayout(inline_layout)

        item.setText("")
        self.list_widget.setItemWidget(item, inline_container)
        self.list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)

        self._inline_rename_item = item
        self._inline_rename_chart_id = int(chart_id)
        self._inline_rename_original_text = original_text
        self._inline_rename_editor = inline_editor

        save_button.clicked.connect(self._commit_inline_chart_rename)
        inline_editor.returnPressed.connect(self._commit_inline_chart_rename)

        inline_editor.setFocus()
        inline_editor.selectAll()

    def _cancel_inline_chart_rename(self) -> None:
        item = getattr(self, "_inline_rename_item", None)
        if item is not None:
            try:
                self.list_widget.removeItemWidget(item)
                item.setText(getattr(self, "_inline_rename_original_text", item.text()))
            except RuntimeError:
                pass

        self._inline_rename_item = None
        self._inline_rename_chart_id = None
        self._inline_rename_original_text = None
        self._inline_rename_editor = None

    def _commit_inline_chart_rename(self) -> None:
        chart_id = getattr(self, "_inline_rename_chart_id", None)
        editor = getattr(self, "_inline_rename_editor", None)
        if chart_id is None or not isinstance(editor, QLineEdit):
            return

        new_name = editor.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Rename chart", "Chart name can't be blank.")
            editor.setFocus()
            editor.selectAll()
            return

        try:
            chart = load_chart(int(chart_id))
            chart.name = new_name
            chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
            chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
            update_chart(
                int(chart_id),
                chart,
                retcon_time_used=getattr(chart, "retcon_time_used", False),
            )
            self._chart_cache[int(chart_id)] = chart
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Rename chart",
                f"Could not rename the selected chart:\n{exc}",
            )
            return

        self._cancel_inline_chart_rename()
        self._refresh_filters_after_batch_edit({int(chart_id)})

    def _reset_filters(self) -> None:
        self._clear_filters(refresh=False)
        self._set_sort_mode("alpha")
        self.list_widget.clearSelection()

    def _on_export_selected(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self,
                "Export charts",
                "Select one or more charts to export.",
            )
            return

        export_date = datetime.date.today().isoformat()
        default_filename = f"ephemeraldaddy_charts_export-{export_date}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export selected charts",
            default_filename,
            "CSV Files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"

        chart_ids = self._selected_chart_ids(selected_items)

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "id",
                        "name",
                        "birth_place",
                        "datetime_iso",
                        "tz_name",
                        "latitude",
                        "longitude",
                        "used_utc_fallback",
                        "sentiments",
                        "relationship_types",
                        "positive_sentiment_intensity",
                        "negative_sentiment_intensity",
                        "familiarity",
                        "dominant_planet_weights",
                        "dominant_sign_weights",
                        "chart_type",
                        "source",
                    ]
                )
                for chart_id in chart_ids:
                    chart = load_chart(chart_id)
                    dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
                    dominant_sign_weights = getattr(chart, "dominant_sign_weights", None)
                    if not dominant_planet_weights:
                        dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                    if not dominant_sign_weights:
                        dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                    positive_sentiment_intensity = getattr(
                        chart,
                        "positive_sentiment_intensity",
                        None,
                    )
                    negative_sentiment_intensity = getattr(
                        chart,
                        "negative_sentiment_intensity",
                        None,
                    )
                    familiarity = getattr(
                        chart,
                        "familiarity",
                        None,
                    )
                    writer.writerow(
                        [
                            chart_id,
                            chart.name,
                            getattr(chart, "birth_place", None),
                            chart.dt.isoformat(),
                            str(chart.dt.tzinfo) if chart.dt.tzinfo else "",
                            f"{chart.lat:.6f}",
                            f"{chart.lon:.6f}",
                            int(getattr(chart, "used_utc_fallback", False)),
                            ", ".join(getattr(chart, "sentiments", [])),
                            ", ".join(getattr(chart, "relationship_types", [])),
                            positive_sentiment_intensity
                            if positive_sentiment_intensity is not None
                            else "",
                            negative_sentiment_intensity
                            if negative_sentiment_intensity is not None
                            else "",
                            familiarity
                            if familiarity is not None
                            else "",
                            json.dumps(dominant_planet_weights, sort_keys=True),
                            json.dumps(dominant_sign_weights, sort_keys=True),
                            getattr(
                                chart,
                                "chart_type",
                                getattr(chart, "source", SOURCE_PERSONAL),
                            ),
                            getattr(
                                chart,
                                "source",
                                getattr(chart, "chart_type", SOURCE_PERSONAL),
                            ),
                        ]
                    )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export error",
                f"Blegh. Couldn't export selected charts:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Exported {len(chart_ids)} chart(s) to:\n{file_path}",
        )

    def _on_import_csv_type_1(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import charts from CSV",
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        imported = 0
        warnings = 0

        backup_path = None

        try:
            backup_path = backup_database()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Backup failed",
                f"Fumbled the database backup prior to import:\n{e}",
            )
            return

        try:
            geocode_cache: dict[str, tuple[float, float, str]] = {}
            with open(file_path, "r", newline="", encoding="utf-8") as csv_file:
                sample = csv_file.read(2048)
                csv_file.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(csv_file, dialect)

                progress = QProgressDialog(
                    "Importing charts...",
                    "Cancel",
                    0,
                    0,
                    self,
                )
                progress.setWindowTitle("Importing charts")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)

                for idx, raw_row in enumerate(reader, start=1):
                    if progress.wasCanceled():
                        break
                    if not raw_row or all(not cell.strip() for cell in raw_row):
                        continue
                    row = normalize_csv_row(raw_row)
                    if not row or all(not cell for cell in row):
                        continue
                    try:
                        chart, birth_place, used_fallback = _build_import_chart(
                            row,
                            geocode_cache=geocode_cache,
                        )
                    except ValueError:
                        continue
                    chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                    chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                    chart_id = save_chart(
                        chart,
                        birth_place=birth_place,
                        retcon_time_used=getattr(chart, "retcon_time_used", False),
                        chart_type=SOURCE_PUBLIC_DB,
                    )
                    imported += 1
                    if used_fallback:
                        warnings += 1
                    set_current_chart(chart_id)
                    progress.setLabelText(f"Importing charts... processed {idx}")
                    QApplication.processEvents()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import error",
                f"Shucks. Couldn't import those dang charts:\n{e}",
            )
            return

        self._refresh_charts(force_full_analysis_refresh=True)
        if progress.wasCanceled():
            QMessageBox.information(
                self,
                "Import canceled",
                (
                    f"Imported {imported} chart(s) before canceling.\n"
                    f"{warnings} chart(s) need edits to resolve correctly.\n"
                    f"Database backup: {backup_path}"
                    if warnings
                    else (
                        f"Imported {imported} chart(s) before canceling.\n"
                        f"Database backup: {backup_path}"
                    )
                ),
            )
            return
        QMessageBox.information(
            self,
            "Import complete",
            (
                f"Imported {imported} chart(s).\n"
                f"{warnings} chart(s) need edits to resolve correctly.\n"
                f"Database backup: {backup_path}"
                if warnings
                else (
                    f"Imported {imported} chart(s).\n"
                    f"Database backup: {backup_path}"
                )
            ),
        )

    def _on_import_csv_pattern(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import charts from The Pattern CSV",
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        imported = 0
        warnings = 0
        backup_path = None

        try:
            backup_path = backup_database()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Backup failed",
                f"Fumbled the database backup prior to import:\n{e}",
            )
            return

        progress = QProgressDialog(
            "Importing charts...",
            "Cancel",
            0,
            0,
            self,
        )
        progress.setWindowTitle("Importing charts")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        try:
            geocode_cache: dict[str, tuple[float, float, str]] = {}
            with open(file_path, "r", newline="", encoding="utf-8") as csv_file:
                sample = csv_file.read(2048)
                csv_file.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(csv_file, dialect)
                header: list[str] | None = None
                column_index_map: dict[str, int] = {}

                for idx, raw_row in enumerate(reader, start=1):
                    if progress.wasCanceled():
                        break
                    if not raw_row or all(not cell.strip() for cell in raw_row):
                        continue

                    row = normalize_csv_row(raw_row)
                    if not row or all(not cell for cell in row):
                        continue

                    if header is None:
                        header = [cell.casefold() for cell in row]
                        column_index_map = {label: i for i, label in enumerate(header)}
                        required = {
                            "full name",
                            "birthday",
                            "birth time",
                            "gender",
                            "birthtimezone",
                        }
                        if not required.issubset(column_index_map):
                            missing = sorted(required - set(column_index_map))
                            raise ValueError(
                                "Missing required columns for Pattern import: "
                                + ", ".join(missing)
                            )
                        continue

                    chart, birth_place, used_fallback = build_pattern_import_chart(
                        row,
                        column_index_map=column_index_map,
                        geocode_cache=geocode_cache,
                    )
                    chart.source = SOURCE_PUBLIC_DB
                    chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                    chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                    chart_id = save_chart(
                        chart,
                        birth_place=birth_place,
                        retcon_time_used=getattr(chart, "retcon_time_used", False),
                        chart_type=SOURCE_PUBLIC_DB,
                    )
                    imported += 1
                    if used_fallback:
                        warnings += 1
                    set_current_chart(chart_id)
                    progress.setLabelText(f"Importing charts... processed {idx}")
                    QApplication.processEvents()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import error",
                f"Shucks. Couldn't import those dang charts:\n{e}",
            )
            return

        self._refresh_charts(force_full_analysis_refresh=True)
        if progress.wasCanceled():
            QMessageBox.information(
                self,
                "Import canceled",
                (
                    f"Imported {imported} chart(s) before canceling.\n"
                    f"{warnings} chart(s) need edits to resolve correctly.\n"
                    f"Database backup: {backup_path}"
                    if warnings
                    else (
                        f"Imported {imported} chart(s) before canceling.\n"
                        f"Database backup: {backup_path}"
                    )
                ),
            )
            return
        QMessageBox.information(
            self,
            "Import complete",
            (
                f"Imported {imported} chart(s).\n"
                f"{warnings} chart(s) need edits to resolve correctly.\n"
                f"Database backup: {backup_path}"
                if warnings
                else (
                    f"Imported {imported} chart(s).\n"
                    f"Database backup: {backup_path}"
                )
            ),
        )

    def _on_export_database(self) -> None:
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export database",
            f"ephemeraldaddy_dbbackup_{timestamp}.db",
            "Database Files (*.db)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".db"):
            file_path = f"{file_path}.db"
        try:
            backup_database(Path(file_path))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export error",
                f"Try not to cry. The database couldn't be exported for some cockamamie reason:\n{e}",
            )
            return
        QMessageBox.information(
            self,
            "Export complete",
            f"Database backup saved to:\n{file_path}",
        )

    def _on_custom_db_export(self) -> None:
        open_custom_db_export_dialog(self)

    def _on_force_refresh_database_analysis(self) -> None:
        chart_ids: list[int] = []
        for row in self._chart_rows:
            normalized = self._normalize_chart_row(row)
            if normalized is None:
                raise RuntimeError(f"Encountered malformed chart row during refresh: {row!r}")
            chart_ids.append(normalized[0])
        if chart_ids:
            progress = QProgressDialog(
                "Refreshing stored dominance weights...",
                "Cancel",
                0,
                len(chart_ids),
                self,
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(250)
            progress.setValue(0)
            try:
                for index, chart_id in enumerate(chart_ids, start=1):
                    if progress.wasCanceled():
                        break
                    chart = self._get_chart_for_filter(chart_id)
                    if chart is not None and not getattr(chart, "is_placeholder", False):
                        chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
                        chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
                        update_chart(
                            chart_id,
                            chart,
                            dominant_sign_weights=chart.dominant_sign_weights,
                            dominant_planet_weights=chart.dominant_planet_weights,
                        )
                    progress.setValue(index)
                    QApplication.processEvents()
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Database refresh error",
                    f"Could not refresh stored dominance values:\n{exc}",
                )
                progress.close()
                return
            progress.close()

        self._chart_cache.clear()
        self._database_metrics_cache = None
        self._database_metric_snapshots = {}
        self._database_metrics_dirty_ids.clear()
        self._refresh_charts(force_full_analysis_refresh=True)

    def _on_import_database(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import database",
            "",
            "Database Files (*.db)",
        )
        if not file_path:
            return
        confirm = QMessageBox.question(
            self,
            "Confirm restore",
            (
                "Importing a database will overwrite your current charts.\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            restore_database(Path(file_path))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Restore error",
                f"Could not restore the database:\n{e}",
            )
            return
        QMessageBox.information(
            self,
            "Restore complete",
            "Database restored. Reloading charts.",
        )
        self._refresh_charts(force_full_analysis_refresh=True)
    def _set_sort_mode(self, mode: str) -> None:
        default_descending_by_mode = {
            "alpha": False,
            "date": True,
            "cursedness": True,
            "age": False,
            "birthdate": False,
            "familiarity": True,
            "alignment": True,
            "social_score": True,
            "known_duration": True,
        }
        if mode == self._sort_mode:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_mode = mode
            self._sort_descending = default_descending_by_mode.get(mode, False)
        self._update_sort_button_label()
        self._settings.setValue("manage_charts/sort_mode", self._sort_mode)
        self._settings.setValue("manage_charts/sort_descending", int(self._sort_descending))
        self._populate_list()

    @staticmethod
    def _age_sort_key(datetime_iso: str | None) -> datetime.datetime:
        if not datetime_iso:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        try:
            parsed = datetime.datetime.fromisoformat(datetime_iso)
        except ValueError:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed

    @staticmethod
    def _birthdate_sort_key(datetime_iso: str | None) -> tuple[int, int, str]:
        """Sort by month/day (time of year), then keep datetime text stable."""
        if not datetime_iso:
            return (13, 32, "")
        parsed_dt, _time_missing = parse_datetime_value(datetime_iso)
        if parsed_dt is None:
            return (13, 32, datetime_iso)
        return (parsed_dt.month, parsed_dt.day, datetime_iso)

    @staticmethod
    def _known_duration_sort_key(year_first_encountered: int | None) -> float:
        now_year = datetime.datetime.now(datetime.timezone.utc).year
        if year_first_encountered is None:
            return 0.0
        try:
            year_value = int(year_first_encountered)
        except (TypeError, ValueError):
            return 0.0
        return float(max(0, now_year - year_value))

    def _cursedness_score_for_chart(self, chart_id: int) -> float:
        chart = self._get_chart_for_filter(chart_id)
        if chart is None:
            return float("-inf")
        use_houses = _chart_uses_houses(chart)
        angular_bodies = {"AS", "MC", "DS", "IC"}
        houses = getattr(chart, "houses", None) if use_houses else None
        aspects = getattr(chart, "aspects", None) or []
        filtered_aspects = [
            aspect
            for aspect in aspects
            if not _is_structural_tautology(aspect)
            and (
                use_houses
                or (
                    aspect.get("p1") not in angular_bodies
                    and aspect.get("p2") not in angular_bodies
                )
            )
        ]
        if not filtered_aspects:
            return float("-inf")

        positions = getattr(chart, "positions", {})
        curse_aspects: list[AspectRecord] = []
        for aspect in filtered_aspects:
            lon_a = positions.get(aspect.get("p1"))
            lon_b = positions.get(aspect.get("p2"))
            if lon_a is None or lon_b is None:
                continue
            aspect_key = str(aspect.get("type", "")).replace(" ", "_").lower()
            max_orb_deg = float(ASPECT_DEFS.get(aspect_key, {}).get("orb", 0.0))
            house_a = _house_for_longitude(houses, lon_a) if use_houses else None
            house_b = _house_for_longitude(houses, lon_b) if use_houses else None
            curse_aspects.append(
                AspectRecord(
                    aspect=aspect_key,
                    body_a=aspect.get("p1", ""),
                    sign_a=_sign_for_longitude(lon_a),
                    house_a=house_a or 0,
                    body_b=aspect.get("p2", ""),
                    sign_b=_sign_for_longitude(lon_b),
                    house_b=house_b or 0,
                    orb_deg=abs(float(aspect.get("delta", 0.0))),
                    max_orb_deg=max_orb_deg,
                    applying=float(aspect.get("delta", 0.0)) < 0,
                )
            )
        if not curse_aspects:
            return float("-inf")
        return float(chart_cursedness(curse_aspects).get("total", 0.0))

    def _alignment_score_for_chart(self, chart_id: int) -> int:
        chart = self._get_chart_for_filter(chart_id)
        if chart is None:
            return 0
        try:
            return int(getattr(chart, "alignment_score", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _refresh_charts(
        self,
        selected_ids: set[int] | None = None,
        *,
        refresh_metrics: bool = True,
        changed_ids: set[int] | None = None,
        force_full_analysis_refresh: bool = False,
    ) -> None:
        try:
            self._chart_rows = list_charts()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Database error",
                f"Couldn't list saved charts:\n{e}",
            )
            self._chart_rows = []
        self._update_tag_completers()

        malformed_rows = [row for row in self._chart_rows if self._normalize_chart_row(row) is None]
        if malformed_rows:
            sample = malformed_rows[0]
            raise RuntimeError(
                "list_charts() returned malformed MUTANT row data. "
                f"Example row: {sample!r}"
            )
        if force_full_analysis_refresh:
            self._chart_cache = {}
            owner = self.parent()
            if owner is not None and hasattr(owner, "_invalidate_chart_view_navigation_cache"):
                owner._invalidate_chart_view_navigation_cache()
            self._database_metrics_cache = None
            self._database_metric_snapshots = {}
            self._database_metrics_dirty_ids.clear()
        elif changed_ids:
            self._database_metrics_dirty_ids.update(changed_ids)
            for chart_id in changed_ids:
                self._chart_cache.pop(chart_id, None)
            owner = self.parent()
            if owner is not None and hasattr(owner, "_invalidate_chart_view_navigation_cache"):
                owner._invalidate_chart_view_navigation_cache(changed_ids)
        self._populate_list(
            selected_ids=selected_ids,
            refresh_metrics=refresh_metrics,
            changed_ids=changed_ids,
            force_full_analysis_refresh=force_full_analysis_refresh,
        )

    @staticmethod
    def _normalize_chart_row(
        row: tuple | list | None,
    ) -> tuple[
        int,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        int,
        int,
        int,
        int,
        int,
        int | None,
        int,
        str,
        int,
        int,
        int | None,
        int | None,
        int | None,
    ] | None:
        if not row:
            return None
        padded = list(row)
        if len(padded) < 20:
            padded.extend([None] * (20 - len(padded)))
        return (
            int(padded[0]),
            padded[1],
            padded[2],
            padded[3],
            padded[4],
            padded[5],
            padded[6],
            int(padded[7] or 0),
            int(padded[8] or 0),
            int(padded[9] or 0),
            int(padded[10] or 1),
            max(0, int(padded[11] or 0)),
            int(padded[12]) if padded[12] is not None else None,
            int(padded[13] or 0),
            _normalize_gui_source(padded[14] if padded[14] else SOURCE_PERSONAL),
            int(padded[15] or 0),
            int(padded[16] or 0),
            int(padded[17]) if padded[17] is not None else None,
            int(padded[18]) if padded[18] is not None else None,
            int(padded[19]) if padded[19] is not None else None,
        )

    def _populate_list(
        self,
        selected_ids: set[int] | None = None,
        *,
        refresh_metrics: bool = True,
        changed_ids: set[int] | None = None,
        force_full_analysis_refresh: bool = False,
    ) -> None:
        self._refresh_personal_transit_chart_options()
        self._refresh_similarities_chart_options()
        list_signal_blocker = QSignalBlocker(self.list_widget)
        self.list_widget.clear()

        rows = [
            normalized
            for row in self._chart_rows
            if (normalized := self._normalize_chart_row(row)) is not None
        ]
        rows = [row for row in rows if self._chart_in_active_collection(row)]
        self._active_chart_rows_by_id = {int(row[0]): row for row in rows}
        self._active_collection_total_count = len(rows)
        if self._sort_mode == "alpha":
            rows.sort(key=lambda r: (r[1] or "").lower(), reverse=self._sort_descending)
        elif self._sort_mode == "birthdate":
            rows.sort(
                key=lambda r: self._birthdate_sort_key(r[4]),
                reverse=self._sort_descending,
            )
        elif self._sort_mode == "cursedness":
            rows.sort(
                key=lambda r: (self._cursedness_score_for_chart(r[0]), (r[1] or "").lower()),
                reverse=self._sort_descending,
            )
        elif self._sort_mode == "age":
            rows.sort(key=lambda r: self._age_sort_key(r[4]), reverse=self._sort_descending)
        elif self._sort_mode == "familiarity":
            rows.sort(key=lambda r: (r[10], (r[1] or "").lower()), reverse=self._sort_descending)
        elif self._sort_mode == "known_duration":
            rows.sort(
                key=lambda r: (
                    self._known_duration_sort_key(r[12]),
                    (r[1] or "").lower(),
                ),
                reverse=self._sort_descending,
            )
        elif self._sort_mode == "alignment":
            rows.sort(
                key=lambda r: (
                    self._alignment_score_for_chart(r[0]),
                    r[13],
                    (r[1] or "").lower(),
                ),
                reverse=self._sort_descending,
            )
        elif self._sort_mode == "social_score":
            rows.sort(key=lambda r: (r[13], (r[1] or "").lower()), reverse=self._sort_descending)
        else:
            rows.sort(key=lambda r: r[6], reverse=self._sort_descending)

        chart_positions = {
            row[0]: index for index, row in enumerate(rows, start=1)
        }
        try:
            for (
                cid,
                name,
                alias,
                gender,
                dt_iso,
                birth_place,
                _created_at,
                used_fallback,
                birthtime_unknown,
                retcon_time_used,
                _familiarity,
                _age_when_first_met,
                _year_first_encountered,
                _social_score,
                _source,
                is_placeholder,
                is_deceased,
                _birth_month,
                _birth_day,
                _birth_year,
            ) in rows:
                try:
                    matches_filters = self._chart_matches_filters(cid)
                except Exception:
                    matches_filters = False
                if not matches_filters:
                    continue
                display_name = name or "Unnamed"
                alias_text = (alias or "").strip()
                alias_label = f"({alias_text})" if alias_text else ""
                if used_fallback:
                    display_name = f"⚠️ {display_name}"
                date_label, time_label = format_chart_row_datetime(
                    dt_iso,
                    birthtime_unknown=bool(birthtime_unknown),
                )
                if is_placeholder:
                    chart = self._get_chart_for_filter(cid)
                    if chart is not None:
                        date_label = self._format_partial_birth_date(
                            getattr(chart, "birth_month", None),
                            getattr(chart, "birth_day", None),
                            getattr(chart, "birth_year", None),
                        )
                retcon_date_label, retcon_time_value = format_chart_row_datetime(
                    dt_iso,
                    birthtime_unknown=False,
                )
                has_known_retcon_time = (
                    retcon_date_label != "??.??.????"
                    and retcon_time_value not in {"??:??", "unknown"}
                )
                retcon_date_label, retcon_time_value = format_chart_row_datetime(
                    dt_iso,
                    birthtime_unknown=False,
                )
                has_known_retcon_time = (
                    retcon_date_label != "??.??.????"
                    and retcon_time_value not in {"??:??", "unknown"}
                )
                retcon_time_label = f"({retcon_time_value})" if retcon_time_used and has_known_retcon_time else ""
                place = birth_place or ""
                gender_glyph = GENDER_GLYPHS.get((gender or "").strip().upper(), "")
                place_with_gender = f"{place} {gender_glyph}".rstrip() if place or gender_glyph else ""
                row_prefix = "💀  " if bool(is_deceased) else ""
                label = (
                    f"{row_prefix}#{chart_positions.get(cid, '?')}  "
                    f"{display_name}  {alias_label}  {date_label}  {time_label}"
                    f"  {retcon_time_label}  {place_with_gender}"
                )
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, cid)
                if self._active_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES:
                    related_names = self._possible_duplicate_related_names.get(cid, {})
                    if related_names:
                        tooltip_sections: list[str] = []
                        name_matches = related_names.get("name", [])
                        if name_matches:
                            tooltip_names = ", ".join(name_matches[:5])
                            if len(name_matches) > 5:
                                tooltip_names = f"{tooltip_names}, …"
                            tooltip_sections.append(f"Similar name to: {tooltip_names}")
                        birthday_matches = related_names.get("birth_date", [])
                        if birthday_matches:
                            tooltip_names = ", ".join(birthday_matches[:5])
                            if len(birthday_matches) > 5:
                                tooltip_names = f"{tooltip_names}, …"
                            tooltip_sections.append(f"Similar birth date to: {tooltip_names}")
                        similarity_matches = related_names.get("chart_similarity_90_100", [])
                        if similarity_matches:
                            tooltip_names = ", ".join(similarity_matches[:5])
                            if len(similarity_matches) > 5:
                                tooltip_names = f"{tooltip_names}, …"
                            tooltip_sections.append(f"90–100% chart similarity to: {tooltip_names}")
                        if tooltip_sections:
                            item.setToolTip("; ".join(tooltip_sections))
                item.setData(
                    Qt.UserRole + 1,
                    {
                        "position": chart_positions.get(cid, "?"),
                        "name": display_name,
                        "raw_name": name or "Unnamed",
                        "alias": alias_text,
                        "date": date_label,
                        "time": time_label,
                        "retcon_time": retcon_time_label,
                        "place": place_with_gender,
                        "is_placeholder": bool(is_placeholder),
                        "is_deceased": bool(is_deceased),
                    },
                )
                self.list_widget.addItem(item)
                if selected_ids and cid in selected_ids:
                    item.setSelected(True)
        finally:
            del list_signal_blocker
        if refresh_metrics:
            if self._should_use_incremental_metrics_refresh():
                self._update_sentiment_tally(
                    update_database_metrics=False,
                    update_similarities=True,
                )
                self._schedule_incremental_metrics_refresh(
                    changed_ids=changed_ids,
                    force_full_refresh=force_full_analysis_refresh,
                )
            else:
                self._update_sentiment_tally(
                    force_full_refresh=force_full_analysis_refresh,
                    changed_ids=changed_ids,
                )
        self._update_collection_membership_buttons()

    def _chart_matches_filters(self, chart_id: int) -> bool:
        incomplete_birthdate_state = self.incomplete_birthdate_checkbox.mode()
        birthtime_unknown_state = self.birthtime_unknown_checkbox.mode()
        retconned_state = self.retconned_checkbox.mode()
        living_state = self.living_checkbox.mode() if self.living_checkbox is not None else QuadStateSlider.MODE_EMPTY
        search_text = self.search_text_input.text().strip()
        search_tags = parse_tag_text(
            self.search_tags_input.text() if hasattr(self, "search_tags_input") else ""
        )
        selected_chart_types = {
            source
            for source, checkbox in self.chart_type_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE
        }
        excluded_chart_types = {
            source
            for source, checkbox in self.chart_type_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE
        }
        selected_generations = {
            name
            for name, checkbox in self.generation_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE
        }
        excluded_generations = {
            name
            for name, checkbox in self.generation_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE
        }
        selected_species = self.species_filter_combo.currentData()
        selected_sentiments = {
            name
            for name, checkbox in self.sentiment_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_sentiments = {
            name
            for name, checkbox in self.sentiment_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_sentiment = (
            "none" in self.sentiment_filter_checkboxes
            and self.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_sentiment = (
            "none" in self.sentiment_filter_checkboxes
            and self.sentiment_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
        )
        selected_relationship_types = {
            name
            for name, checkbox in self.relationship_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_relationship_types = {
            name
            for name, checkbox in self.relationship_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_relationship = (
            "none" in self.relationship_filter_checkboxes
            and self.relationship_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_relationship = (
            "none" in self.relationship_filter_checkboxes
            and self.relationship_filter_checkboxes["none"].mode()
            == QuadStateSlider.MODE_FALSE
        )
        selected_genders = {
            name
            for name, checkbox in self.gender_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_TRUE and name != "none"
        }
        excluded_genders = {
            name
            for name, checkbox in self.gender_filter_checkboxes.items()
            if checkbox.mode() == QuadStateSlider.MODE_FALSE and name != "none"
        }
        include_none_gender = (
            "none" in self.gender_filter_checkboxes
            and self.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_TRUE
        )
        exclude_none_gender = (
            "none" in self.gender_filter_checkboxes
            and self.gender_filter_checkboxes["none"].mode() == QuadStateSlider.MODE_FALSE
        )
        selected_guessed_gender = str(
            self.gender_guessed_filter_combo.currentData() or ""
        )
        active_body_filters = [
            filters
            for filters in self._search_body_filters
            if filters["sign"].currentText() != "Any"
            or filters["house"].currentText() != "Any"
        ]
        active_aspect_filters = [
            filters
            for filters in self._aspect_filters
            if str(filters["planet_1"].currentData()) != "Any"
            or str(filters["aspect"].currentData()) != "Any"
            or str(filters["planet_2"].currentData()) != "Any"
        ]
        active_dominant_sign_filters = [
            filters
            for filters in self._dominant_sign_filters
            if filters["sign"].currentText() != "Any"
        ]
        active_dominant_planet_filters = [
            filters
            for filters in self._dominant_planet_filters
            if str(filters["planet"].currentData()) != "Any"
        ]
        active_dominant_mode_filters = [
            filters
            for filters in self._dominant_mode_filters
            if filters["mode"].currentData() != "Any"
        ]
        dominant_element_primary = (
            str(self._dominant_element_primary_combo.currentData())
            if self._dominant_element_primary_combo is not None
            else "Any"
        )
        dominant_element_secondary = (
            str(self._dominant_element_secondary_combo.currentData())
            if self._dominant_element_secondary_combo is not None
            else "Any"
        )
        year_first_encountered_earliest = self._parse_year_first_encountered_text(
            self._year_first_encountered_earliest_input.text()
            if self._year_first_encountered_earliest_input is not None
            else ""
        )
        year_first_encountered_latest = self._parse_year_first_encountered_text(
            self._year_first_encountered_latest_input.text()
            if self._year_first_encountered_latest_input is not None
            else ""
        )
        year_first_encountered_blank_state = (
            self._year_first_encountered_blank_checkbox.mode()
            if self._year_first_encountered_blank_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        positive_sentiment_intensity_min = self._parse_integer_filter_text(
            self._positive_sentiment_intensity_min_input.text()
            if self._positive_sentiment_intensity_min_input is not None
            else ""
        )
        positive_sentiment_intensity_max = self._parse_integer_filter_text(
            self._positive_sentiment_intensity_max_input.text()
            if self._positive_sentiment_intensity_max_input is not None
            else ""
        )
        negative_sentiment_intensity_min = self._parse_integer_filter_text(
            self._negative_sentiment_intensity_min_input.text()
            if self._negative_sentiment_intensity_min_input is not None
            else ""
        )
        negative_sentiment_intensity_max = self._parse_integer_filter_text(
            self._negative_sentiment_intensity_max_input.text()
            if self._negative_sentiment_intensity_max_input is not None
            else ""
        )
        familiarity_min = self._parse_integer_filter_text(
            self._familiarity_min_input.text()
            if self._familiarity_min_input is not None
            else ""
        )
        familiarity_max = self._parse_integer_filter_text(
            self._familiarity_max_input.text()
            if self._familiarity_max_input is not None
            else ""
        )
        alignment_score_min = self._parse_signed_integer_filter_text(
            self._alignment_score_min_input.text()
            if self._alignment_score_min_input is not None
            else ""
        )
        alignment_score_max = self._parse_signed_integer_filter_text(
            self._alignment_score_max_input.text()
            if self._alignment_score_max_input is not None
            else ""
        )
        include_blank_alignment = bool(
            self._alignment_score_blank_checkbox is not None
            and self._alignment_score_blank_checkbox.isChecked()
        )
        notes_comments_mode = (
            self._notes_comments_filter_checkbox.mode()
            if self._notes_comments_filter_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        notes_comments_text = (
            self._notes_comments_filter_input.text().strip()
            if self._notes_comments_filter_input is not None
            else ""
        )
        notes_source_mode = (
            self._notes_source_filter_checkbox.mode()
            if self._notes_source_filter_checkbox is not None
            else QuadStateSlider.MODE_EMPTY
        )
        notes_source_text = (
            self._notes_source_filter_input.text().strip()
            if self._notes_source_filter_input is not None
            else ""
        )

        if not self._has_active_chart_filters():
            return True

        chart_row = self._active_chart_rows_by_id.get(int(chart_id))
        if search_text:
            def matches(value: str | None) -> bool:
                return bool(value) and search_text.casefold() in value.casefold()

            name_value = chart_row[1] if chart_row else None
            alias_value = chart_row[2] if chart_row else None
            birth_place_value = chart_row[5] if chart_row else None
            source_value = chart_row[14] if chart_row else None
            gender_value = chart_row[3] if chart_row else None
            if chart_row is None:
                chart = self._get_chart_for_filter(chart_id)
                if chart is not None:
                    name_value = getattr(chart, "name", None)
                    alias_value = getattr(chart, "alias", None)
                    birth_place_value = getattr(chart, "birth_place", None)
                    source_value = getattr(chart, "source", None)
                    gender_value = getattr(chart, "gender", None)
            if not (
                matches(name_value)
                or matches(alias_value)
                or matches(birth_place_value)
                or matches(source_value)
                or matches(gender_value)
            ):
                return False
        if selected_chart_types or excluded_chart_types:
            source_value = chart_row[14] if chart_row else None
            if chart_row is None:
                chart = self._get_chart_for_filter(chart_id)
                source_value = getattr(chart, "source", None) if chart else None
            if source_value in excluded_chart_types:
                return False
            if selected_chart_types and source_value not in selected_chart_types:
                return False

        if selected_generations or excluded_generations:
            chart_for_generation = self._get_chart_for_filter(chart_id)
            chart_birth_year = self._chart_birth_year_for_filters(chart_row, chart_for_generation)
            generation_name = self._generation_for_birth_year(chart_birth_year) or GENERATION_UNKNOWN_OPTION
            if generation_name in excluded_generations:
                return False
            if selected_generations and generation_name not in selected_generations:
                return False

        if selected_species != "Any":
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                return False
            species_top_three = assign_top_three_species(chart)
            top_three_species = {
                species_name
                for species_name, _subtype, _score in species_top_three[:3]
            }
            if selected_species not in top_three_species:
                return False

        birth_status_filter_states: list[bool] = []
        if (
            birthtime_unknown_state != QuadStateSlider.MODE_EMPTY
            or retconned_state != QuadStateSlider.MODE_EMPTY
        ):
            birthtime_value = None
            if chart_row and len(chart_row) > 7:
                birthtime_value = chart_row[8]
            else:
                chart = self._get_chart_for_filter(chart_id)
                birthtime_value = getattr(chart, "birthtime_unknown", False)
            has_unknown_birthtime = bool(birthtime_value)

            retcon_value = None
            if chart_row and len(chart_row) > 8:
                retcon_value = chart_row[9]
            else:
                chart = self._get_chart_for_filter(chart_id)
                retcon_value = getattr(chart, "retcon_time_used", False)
            is_retconned = bool(retcon_value)

            if birthtime_unknown_state == QuadStateSlider.MODE_TRUE:
                birth_status_filter_states.append(has_unknown_birthtime)
            elif birthtime_unknown_state == QuadStateSlider.MODE_FALSE:
                birth_status_filter_states.append(not has_unknown_birthtime)

            if retconned_state == QuadStateSlider.MODE_TRUE:
                birth_status_filter_states.append(is_retconned)
            elif retconned_state == QuadStateSlider.MODE_FALSE:
                birth_status_filter_states.append(not is_retconned)

            if birth_status_filter_states:
                if self.birth_status_filter_or.isChecked():
                    if not any(birth_status_filter_states):
                        return False
                elif not all(birth_status_filter_states):
                    return False

        is_placeholder = bool(chart_row[15]) if chart_row and len(chart_row) > 15 else False
        if (
            incomplete_birthdate_state == QuadStateSlider.MODE_TRUE
            and not is_placeholder
        ):
            return False
        if (
            incomplete_birthdate_state == QuadStateSlider.MODE_FALSE
            and is_placeholder
        ):
            return False

        if living_state != QuadStateSlider.MODE_EMPTY:
            deceased_value = chart_row[16] if chart_row and len(chart_row) > 16 else None
            if deceased_value is None:
                chart_for_mortality = self._get_chart_for_filter(chart_id)
                deceased_value = bool(getattr(chart_for_mortality, "is_deceased", False)) if chart_for_mortality is not None else False
            is_living = not bool(deceased_value)
            if living_state == QuadStateSlider.MODE_TRUE and not is_living:
                return False
            if living_state == QuadStateSlider.MODE_FALSE and is_living:
                return False

        chart = self._get_chart_for_filter(chart_id)
        if chart is None:
            return incomplete_birthdate_state == QuadStateSlider.MODE_TRUE

        comments_filter_active = (
            notes_comments_mode != QuadStateSlider.MODE_EMPTY and bool(notes_comments_text)
        )
        if comments_filter_active:
            chart_comments = str(getattr(chart, "comments", "") or "")
            comments_match = notes_comments_text.casefold() in chart_comments.casefold()
            if notes_comments_mode == QuadStateSlider.MODE_TRUE and not comments_match:
                return False
            if notes_comments_mode == QuadStateSlider.MODE_FALSE and comments_match:
                return False

        source_filter_active = (
            notes_source_mode != QuadStateSlider.MODE_EMPTY and bool(notes_source_text)
        )
        if source_filter_active:
            chart_source_text = str(getattr(chart, "chart_data_source", "") or "")
            source_match = notes_source_text.casefold() in chart_source_text.casefold()
            if notes_source_mode == QuadStateSlider.MODE_TRUE and not source_match:
                return False
            if notes_source_mode == QuadStateSlider.MODE_FALSE and source_match:
                return False

        include_untagged = bool(
            hasattr(self, "search_untagged_checkbox")
            and self.search_untagged_checkbox.isChecked()
        )
        if (search_tags or include_untagged) and not chart_matches_tag_filters(
            getattr(chart, "tags", []),
            required_tags=search_tags,
            include_untagged=include_untagged,
        ):
            return False

        chart_year_first_encountered = getattr(chart, "year_first_encountered", None)
        if not isinstance(chart_year_first_encountered, int):
            chart_year_first_encountered = None

        if year_first_encountered_earliest is not None:
            if (
                chart_year_first_encountered is None
                or chart_year_first_encountered < year_first_encountered_earliest
            ):
                return False
        if year_first_encountered_latest is not None:
            if (
                chart_year_first_encountered is None
                or chart_year_first_encountered > year_first_encountered_latest
            ):
                return False
        if year_first_encountered_blank_state == QuadStateSlider.MODE_TRUE:
            if chart_year_first_encountered is not None:
                return False
        elif year_first_encountered_blank_state == QuadStateSlider.MODE_FALSE:
            if chart_year_first_encountered is None:
                return False

        chart_positive_sentiment_intensity = int(
            getattr(chart, "positive_sentiment_intensity", 1) or 1
        )
        chart_negative_sentiment_intensity = int(
            getattr(chart, "negative_sentiment_intensity", 1) or 1
        )
        chart_familiarity = int(getattr(chart, "familiarity", 1) or 1)

        if positive_sentiment_intensity_min is not None and (
            chart_positive_sentiment_intensity < positive_sentiment_intensity_min
        ):
            return False
        if positive_sentiment_intensity_max is not None and (
            chart_positive_sentiment_intensity > positive_sentiment_intensity_max
        ):
            return False
        if negative_sentiment_intensity_min is not None and (
            chart_negative_sentiment_intensity < negative_sentiment_intensity_min
        ):
            return False
        if negative_sentiment_intensity_max is not None and (
            chart_negative_sentiment_intensity > negative_sentiment_intensity_max
        ):
            return False
        if familiarity_min is not None and chart_familiarity < familiarity_min:
            return False
        if familiarity_max is not None and chart_familiarity > familiarity_max:
            return False

        chart_alignment_score_raw = getattr(chart, "alignment_score", None)
        chart_alignment_score = (
            int(chart_alignment_score_raw)
            if isinstance(chart_alignment_score_raw, int)
            else None
        )
        if alignment_score_min is not None:
            if chart_alignment_score is None or chart_alignment_score < alignment_score_min:
                return False
        if alignment_score_max is not None:
            if chart_alignment_score is None or chart_alignment_score > alignment_score_max:
                return False
        if include_blank_alignment and chart_alignment_score is not None:
            return False

        # if bool(getattr(chart, "is_placeholder", False)):
        #     return incomplete_birthdate_state != Qt.PartiallyChecked

        if (
            selected_sentiments
            or excluded_sentiments
            or include_none_sentiment
            or exclude_none_sentiment
        ):
            chart_sentiments = set(
                getattr(chart, "sentiments", []) or []
            )
            if exclude_none_sentiment and not chart_sentiments:
                return False
            if excluded_sentiments and chart_sentiments.intersection(excluded_sentiments):
                return False
            if selected_sentiments or include_none_sentiment:
                sentiment_match = False
                if include_none_sentiment and not chart_sentiments:
                    sentiment_match = True
                if selected_sentiments:
                    if self.sentiment_filter_and.isChecked():
                        if selected_sentiments.issubset(chart_sentiments):
                            sentiment_match = True
                    else:
                        if chart_sentiments.intersection(selected_sentiments):
                            sentiment_match = True
                if not sentiment_match:
                    return False

        if (
            selected_relationship_types
            or excluded_relationship_types
            or include_none_relationship
            or exclude_none_relationship
        ):
            chart_relationship_types = self._normalize_relationship_types(chart)
            if exclude_none_relationship and not chart_relationship_types:
                return False
            if (
                excluded_relationship_types
                and chart_relationship_types.intersection(excluded_relationship_types)
            ):
                return False
            if selected_relationship_types or include_none_relationship:
                relationship_match = False
                if include_none_relationship and not chart_relationship_types:
                    relationship_match = True
                if selected_relationship_types:
                    if self.relationship_filter_and.isChecked():
                        if selected_relationship_types.issubset(
                            chart_relationship_types
                        ):
                            relationship_match = True
                    else:
                        if chart_relationship_types.intersection(
                            selected_relationship_types
                        ):
                            relationship_match = True
                if not relationship_match:
                    return False

        if (
            selected_genders
            or excluded_genders
            or include_none_gender
            or exclude_none_gender
        ):
            chart_gender = self._normalize_gender_value(getattr(chart, "gender", None))
            normalized_selected_genders = {
                self._normalize_gender_value(value).casefold()
                for value in selected_genders
            }
            normalized_excluded_genders = {
                self._normalize_gender_value(value).casefold()
                for value in excluded_genders
            }
            normalized_chart_gender = chart_gender.casefold()
            if exclude_none_gender and not chart_gender:
                return False
            if (
                normalized_excluded_genders
                and normalized_chart_gender in normalized_excluded_genders
            ):
                return False
            if selected_genders or include_none_gender:
                gender_match = False
                if include_none_gender and not chart_gender:
                    gender_match = True
                if normalized_selected_genders:
                    if self.gender_filter_and.isChecked():
                        if normalized_selected_genders.issubset({normalized_chart_gender}):
                            gender_match = True
                    else:
                        if normalized_chart_gender in normalized_selected_genders:
                            gender_match = True
                if not gender_match:
                    return False

        if selected_guessed_gender:
            chart = self._get_chart_for_filter(chart_id)
            if chart is None:
                return False
            guessed_by_prevalence = self._classify_guessed_gender(
                _calculate_gender_prevalence_score(chart)
            )
            guessed_by_weight = self._classify_guessed_gender(
                _calculate_gender_weight_score(chart)
            )
            if (
                guessed_by_prevalence != selected_guessed_gender
                and guessed_by_weight != selected_guessed_gender
            ):
                return False

        for filters in active_body_filters:
            body = filters["body"].currentData()
            sign_value = filters["sign"].currentText()
            house_value = filters["house"].currentText()
            sign_active = sign_value != "Any"
            house_active = house_value != "Any"
            if sign_active and house_active:
                if filters["and"].isChecked():
                    if not self._chart_body_matches(chart, body, sign_value, house_value):
                        return False
                else:
                    sign_match = self._chart_body_matches(chart, body, sign_value, "Any")
                    house_match = self._chart_body_matches(chart, body, "Any", house_value)
                    if not (sign_match or house_match):
                        return False
            elif sign_active:
                if not self._chart_body_matches(chart, body, sign_value, "Any"):
                    return False
            elif house_active:
                if not self._chart_body_matches(chart, body, "Any", house_value):
                    return False

        if active_aspect_filters:
            aspect_and_filters = [
                filters for filters in active_aspect_filters if filters["and"].isChecked()
            ]
            aspect_or_filters = [
                filters for filters in active_aspect_filters if filters["or"].isChecked()
            ]
            for filters in aspect_and_filters:
                if not self._chart_aspect_matches(
                    chart,
                    str(filters["planet_1"].currentData()),
                    str(filters["aspect"].currentData()),
                    str(filters["planet_2"].currentData()),
                ):
                    return False
            if aspect_or_filters:
                if not any(
                    self._chart_aspect_matches(
                        chart,
                        str(filters["planet_1"].currentData()),
                        str(filters["aspect"].currentData()),
                        str(filters["planet_2"].currentData()),
                    )
                    for filters in aspect_or_filters
                ):
                    return False

        if active_dominant_sign_filters:
            dominant_and_filters = [
                filters for filters in active_dominant_sign_filters
                if filters["and"].isChecked()
            ]
            dominant_or_filters = [
                filters for filters in active_dominant_sign_filters
                if filters["or"].isChecked()
            ]
            for filters in dominant_and_filters:
                if not self._chart_dominant_sign_matches(
                    chart,
                    filters["sign"].currentText(),
                ):
                    return False
            if dominant_or_filters:
                if not any(
                    self._chart_dominant_sign_matches(
                        chart,
                        filters["sign"].currentText(),
                    )
                    for filters in dominant_or_filters
                ):
                    return False
        if active_dominant_mode_filters:
            dominant_mode_and_filters = [
                filters for filters in active_dominant_mode_filters
                if filters["and"].isChecked()
            ]
            dominant_mode_or_filters = [
                filters for filters in active_dominant_mode_filters
                if filters["or"].isChecked()
            ]
            for filters in dominant_mode_and_filters:
                if not self._chart_dominant_mode_matches(
                    chart,
                    str(filters["mode"].currentData()),
                ):
                    return False
            if dominant_mode_or_filters:
                if not any(
                    self._chart_dominant_mode_matches(
                        chart,
                        str(filters["mode"].currentData()),
                    )
                    for filters in dominant_mode_or_filters
                ):
                    return False

        if active_dominant_planet_filters:
            dominant_planet_and_filters = [
                filters for filters in active_dominant_planet_filters
                if filters["and"].isChecked()
            ]
            dominant_planet_or_filters = [
                filters for filters in active_dominant_planet_filters
                if filters["or"].isChecked()
            ]
            for filters in dominant_planet_and_filters:
                if not self._chart_dominant_planet_matches(
                    chart,
                    str(filters["planet"].currentData()),
                ):
                    return False
            if dominant_planet_or_filters:
                if not any(
                    self._chart_dominant_planet_matches(
                        chart,
                        str(filters["planet"].currentData()),
                    )
                    for filters in dominant_planet_or_filters
                ):
                    return False

        if dominant_element_primary != "Any" or dominant_element_secondary != "Any":
            dominant_elements = self._chart_ranked_dominant_elements(chart)
            if dominant_element_primary != "Any":
                if not dominant_elements or dominant_elements[0] != dominant_element_primary:
                    return False
            if dominant_element_secondary != "Any":
                if len(dominant_elements) < 2 or dominant_elements[1] != dominant_element_secondary:
                    return False

        return True

    def _chart_in_active_collection(
        self,
        normalized_row: tuple[
            int,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            int,
            int,
            int,
            int,
            int,
            int | None,
            int,
            str,
            int,
            int,
            int | None,
            int | None,
            int | None,
        ],
    ) -> bool:
        chart_id = normalized_row[0]
        if self._active_collection_id == DEFAULT_COLLECTION_POSSIBLE_DUPLICATES:
            return chart_id in self._possible_duplicate_chart_ids
        chart_source = normalized_row[14]
        chart = self._get_chart_for_filter(chart_id)
        return chart_belongs_to_collection(
            self._active_collection_id,
            chart=chart,
            source=chart_source,
            custom_collections=self._custom_collections,
            chart_id=chart_id,
        )

    @staticmethod
    def _normalize_relationship_types(chart: Chart | None) -> set[str]:
        if chart is None:
            return set()
        raw_relationships = getattr(chart, "relationship_types", None)
        if not raw_relationships:
            return set()
        if isinstance(raw_relationships, str):
            return set(parse_relationship_types(raw_relationships))
        try:
            return {
                relationship
                for relationship in raw_relationships
                if isinstance(relationship, str) and relationship
            }
        except TypeError:
            return set()

    @staticmethod
    def _normalize_gender_value(gender: object) -> str:
        if gender is None:
            return ""
        if isinstance(gender, str):
            normalized = gender.strip()
        else:
            normalized = str(gender).strip()
        if normalized.casefold() in SEARCH_GENDER_BLANK_ALIASES:
            return ""
        return normalized

    @staticmethod
    def _classify_guessed_gender(score: float) -> str:
        """Map gender score (0..10, where 5 is neutral) to a label.

        We treat androgynous as a narrow neutral window of ±0.05 around 5.0,
        which corresponds to ±0.5 percentage points around a perfect 50/50
        balance on the UI scale.
        """
        if score < 4.95:
            return "masculine"
        if score > 5.05:
            return "feminine"
        return "androgynous"

    def _get_chart_for_filter(self, chart_id: int):
        if chart_id in self._chart_cache:
            return self._chart_cache[chart_id]
        try:
            chart = load_chart(chart_id)
        except Exception:
            chart = None
        self._chart_cache[chart_id] = chart
        return chart

    def _chart_body_matches(
        self,
        chart: Chart,
        body: str,
        sign: str,
        house_text: str,
    ) -> bool:
        if body == "Any":
            return any(
                self._chart_body_matches(chart, body_key, sign, house_text)
                for _, body_key in self._searchable_bodies()
            )
        position = getattr(chart, "positions", {}).get(body)
        if position is None:
            return False

        if sign != "Any" and _sign_for_longitude(position) != sign:
            return False

        if house_text != "Any":
            if not _chart_uses_houses(chart):
                return False
            house_num = self._house_for_longitude(
                getattr(chart, "houses", None),
                position,
            )
            if house_num is None or str(house_num) != house_text:
                return False

        return True

    def _chart_aspect_matches(
        self,
        chart: Chart,
        planet_1: str,
        aspect_name: str,
        planet_2: str,
    ) -> bool:
        aspects = getattr(chart, "aspects", None) or []
        for aspect in aspects:
            left = str(aspect.get("p1", ""))
            right = str(aspect.get("p2", ""))
            current_aspect = str(aspect.get("type", "")).replace(" ", "_").lower()

            if aspect_name != "Any" and current_aspect != aspect_name:
                continue

            direct_match = (
                (planet_1 == "Any" or planet_1 == left)
                and (planet_2 == "Any" or planet_2 == right)
            )
            reverse_match = (
                (planet_1 == "Any" or planet_1 == right)
                and (planet_2 == "Any" or planet_2 == left)
            )
            if direct_match or reverse_match:
                return True
        return False

    def _chart_dominant_sign_matches(
        self,
        chart: Chart,
        sign: str,
    ) -> bool:
        if sign == "Any":
            return True
        dominant_weights = getattr(chart, "dominant_sign_weights", None)
        if not dominant_weights:
            dominant_weights = _calculate_dominant_sign_weights(chart)
            chart.dominant_sign_weights = dominant_weights
        if not dominant_weights:
            return False
        max_weight = max(dominant_weights.values(), default=None)
        if max_weight is None:
            return False
        dominant_signs = {
            weight_sign
            for weight_sign, weight in dominant_weights.items()
            if weight == max_weight
        }
        return sign in dominant_signs

    def _chart_dominant_mode_matches(
        self,
        chart: Chart,
        mode: str,
    ) -> bool:
        if mode == "Any":
            return True
        mode_weights = _calculate_mode_weights(chart)
        if not mode_weights:
            return False
        max_weight = max(mode_weights.values(), default=None)
        if max_weight is None:
            return False
        dominant_modes = {
            weighted_mode
            for weighted_mode, weight in mode_weights.items()
            if weight == max_weight
        }
        return mode in dominant_modes

    def _chart_dominant_planet_matches(
        self,
        chart: Chart,
        planet: str,
    ) -> bool:
        if planet == "Any":
            return True
        return planet in self._chart_dominant_planets(chart)

    def _chart_dominant_planets(self, chart: Chart) -> set[str]:
        dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not dominant_planet_weights:
            dominant_planet_weights = _calculate_dominant_planet_weights(chart)
            chart.dominant_planet_weights = dominant_planet_weights
        if not dominant_planet_weights:
            return set()
        numeric_weights = [
            float(weight)
            for weight in dominant_planet_weights.values()
            if isinstance(weight, (int, float))
        ]
        if not numeric_weights:
            return set()
        median_weight = statistics.median(numeric_weights)
        if median_weight <= 0:
            median_weight = max(numeric_weights)
        if median_weight <= 0:
            return set()
        dominant_threshold = median_weight * 1.25
        return {
            weighted_planet
            for weighted_planet, weight in dominant_planet_weights.items()
            if isinstance(weight, (int, float)) and float(weight) >= dominant_threshold
        }

    def _chart_ranked_dominant_elements(self, chart: Chart) -> list[str]:
        dominant_element_weights = _calculate_dominant_element_weights(chart)
        elements = ["Fire", "Earth", "Air", "Water"]
        ranked_elements = sorted(
            elements,
            key=lambda element: (-float(dominant_element_weights.get(element, 0.0)), elements.index(element)),
        )
        return [
            element
            for element in ranked_elements
            if float(dominant_element_weights.get(element, 0.0)) > 0
        ]

    @staticmethod
    def _house_for_longitude(
        cusps: list[float] | None,
        lon: float,
    ) -> int | None:
        return _house_for_longitude(cusps, lon)

    def _on_delete(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self,
                "Delete charts",
                "Select one or more charts to delete.",
            )
            return

        chart_ids = self._selected_chart_ids(selected_items)
        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete {len(chart_ids)} selected chart(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = delete_charts(chart_ids)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Delete error",
                f"Could not delete selected charts:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Charts deleted",
            f"Deleted {deleted} chart(s).",
        )
        parent = self.parent()
        if isinstance(parent, QWidget) and hasattr(parent, "_on_charts_deleted"):
            parent._on_charts_deleted(set(chart_ids))
        self._refresh_charts(changed_ids=set(chart_ids))

    def _on_new_chart(self) -> None:
        parent = self.parent()
        if parent is None or not hasattr(parent, "on_new_chart"):
            QMessageBox.warning(
                self,
                "New chart",
                "Unable to start a new chart.",
            )
            return
        parent.on_new_chart()
        if isinstance(parent, QWidget):
            if isinstance(parent, MainWindow):
                parent._show_chart_view_maximized(maximize=self.isMaximized(), source_window=self)
            else:
                parent.showNormal()
                parent.raise_()
                parent.activateWindow()
            if isinstance(parent, MainWindow):
                parent._retarget_size_checker_to_main_view()
        self.hide()

    def _on_manage_help_overlay(self) -> None:
        self._toggle_help_overlay()

    def _on_open_settings(self) -> None:
        dialog = self._ensure_settings_dialog()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _ensure_settings_dialog(self) -> QDialog:
        if self._settings_dialog is not None:
            self._resize_and_center_settings_dialog(self._settings_dialog)
            return self._settings_dialog

        dialog = QDialog(self)
        dialog.setWindowTitle("Settings & Preferences")
        dialog.setWindowFlag(Qt.Window, True)
        dialog.setModal(False)
        dialog.setMinimumSize(520, 520)
        dialog.setStyleSheet(
            "QDialog { background-color: #181818; color: #ececec; }"
            "QLabel { color: #ececec; }"
            "QToolButton {"
            "background-color: #262626;"
            "border: 1px solid #555555;"
            "padding: 6px 10px;"
            "font-weight: 600;"
            "color: #ececec;"
            "}"
            "QPushButton {"
            "background-color: #2f2f2f;"
            "border: 1px solid #666666;"
            "padding: 6px 10px;"
            "color: #f0f0f0;"
            "}"
            "QPushButton:hover { background-color: #3a3a3a; }"
            "QFrame#settings_section_content {"
            "background-color: #202020;"
            "border: 1px solid #4f4f4f;"
            "}"
            "QScrollArea { background-color: #181818; }"
        )

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        visibility_section = self._add_settings_collapsible_section(
            content_layout,
            "Visibility", #should use header format: bold & copper
        )
        visibility_section.addWidget(self._build_settings_subheader_label("Chart Data Panel (Chart View)"))

        cursedness_checkbox = QCheckBox("Show cursedness analysis")
        cursedness_checkbox.setChecked(self._visibility.get("chart_data.cursedness"))
        cursedness_checkbox.toggled.connect(
            lambda checked: self._set_chart_data_visibility("chart_data.cursedness", checked)
        )
        visibility_section.addWidget(cursedness_checkbox)

        dnd_species_checkbox = QCheckBox("Show D&&D species card")
        dnd_species_checkbox.setChecked(self._visibility.get("chart_data.dnd_species"))
        dnd_species_checkbox.toggled.connect(
            lambda checked: self._set_chart_data_visibility("chart_data.dnd_species", checked)
        )
        visibility_section.addWidget(dnd_species_checkbox)

        human_design_alpha_checkbox = QCheckBox("Show Human Design (alpha prototype)")
        human_design_alpha_checkbox.setChecked(
            self._visibility.get("chart_data.human_design_alpha_prototype")
        )
        human_design_alpha_checkbox.toggled.connect(
            lambda checked: self._set_chart_data_visibility(
                "chart_data.human_design_alpha_prototype",
                checked,
            )
        )
        visibility_section.addWidget(human_design_alpha_checkbox)

        visibility_section.addWidget(self._build_settings_subheader_label("Synastry Charts (Popout Charts)"))

        synastry_aspect_weights_checkbox = QCheckBox("Show Synastry popout Aspect Weights")
        synastry_aspect_weights_checkbox.setChecked(self._visibility.get("popout.synastry_aspect_weights"))
        synastry_aspect_weights_checkbox.toggled.connect(
            lambda checked: self._set_popout_visibility("popout.synastry_aspect_weights", checked)
        )
        visibility_section.addWidget(synastry_aspect_weights_checkbox)

        visibility_section.addWidget(self._build_settings_subheader_label("Chart Analytics Panel (Chart View View)"))

        planet_dynamics_checkbox = QCheckBox("Show Body Dynamics (Chart Analytics)")
        parent = self.parent()
        planet_dynamics_checkbox.setChecked(
            isinstance(parent, MainWindow)
            and parent._is_chart_analysis_section_visible("planet_dynamics")
        )
        planet_dynamics_checkbox.toggled.connect(
            lambda checked: self._set_chart_analytics_visibility_from_settings(
                "planet_dynamics",
                checked,
            )
        )
        visibility_section.addWidget(planet_dynamics_checkbox)

        anagrams_checkbox = QCheckBox("Show Anagrams (Chart Analytics)")
        anagrams_checkbox.setChecked(
            isinstance(parent, MainWindow)
            and parent._is_chart_analysis_section_visible("anagrams")
        )
        anagrams_checkbox.toggled.connect(
            lambda checked: self._set_chart_analytics_visibility_from_settings(
                "anagrams",
                checked,
            )
        )
        visibility_section.addWidget(anagrams_checkbox)

        visibility_section.addSpacing(8)
        visibility_section.addWidget(self._build_settings_subheader_label("Database Analytics Panel (DB View)"))

        species_distribution_checkbox = QCheckBox("Show Species Distribution")
        species_distribution_checkbox.setChecked(
            self._is_database_metrics_section_visible("species_distribution")
        )
        species_distribution_checkbox.toggled.connect(
            lambda checked: self._set_database_metric_section_visibility_from_settings(
                "species_distribution",
                checked,
            )
        )
        visibility_section.addWidget(species_distribution_checkbox)

        property_managers_section = self._add_settings_collapsible_section(content_layout, "Property Managers")
        property_managers_section.addWidget(QLabel("Manage reusable chart metadata and property groups."))

        manage_sentiments_button = QPushButton("Manage Sentiments")
        manage_sentiments_button.clicked.connect(self._launch_manage_sentiments_dialog)
        property_managers_section.addWidget(manage_sentiments_button)

        manage_relationship_types_button = QPushButton("Manage Relationship Types")
        manage_relationship_types_button.clicked.connect(self._launch_manage_relationship_types_dialog)
        property_managers_section.addWidget(manage_relationship_types_button)

        manage_collections_button = QPushButton("Manage Collections")
        manage_collections_button.clicked.connect(self._show_manage_collections_panel)
        property_managers_section.addWidget(manage_collections_button)

        dev_tools_section = self._add_settings_collapsible_section(content_layout, "Dev Tools") #should use header format: bold & copper
        dev_tools_section.addWidget(QLabel("Developer and maintenance utilities"))

        size_checker_button = QPushButton("Toggle Size Checker")
        size_checker_button.clicked.connect(self._toggle_size_checker)
        dev_tools_section.addWidget(size_checker_button)

        custom_db_export_button = QPushButton("Custom DB Export")
        custom_db_export_button.setToolTip(
            "Choose which chart properties to include in DB/CSV exports."
        )
        custom_db_export_button.clicked.connect(self._on_custom_db_export)
        dev_tools_section.addWidget(custom_db_export_button)

        calibrate_similarity_button = QPushButton("Calibrate Similarity Norms")
        calibrate_similarity_button.setToolTip(
            "Compute min/max/avg/median/mode similarity across saved chart pairs and save thresholds."
        )
        calibrate_similarity_button.clicked.connect(self._calibrate_similarity_norms)
        dev_tools_section.addWidget(calibrate_similarity_button)

        similarity_thresholds_label = QLabel("Similarity Thresholds (%)")
        similarity_thresholds_label.setStyleSheet(SETTINGS_SECTION_SUBHEADER_STYLE)
        dev_tools_section.addWidget(similarity_thresholds_label)
        dev_tools_section.addWidget(
            QLabel(
                "Manual override for band cutoffs (q20/q40/q60/q80). "
                "Values are auto-sorted and saved systemwide."
            )
        )

        thresholds_grid = QGridLayout()
        thresholds_grid.setContentsMargins(0, 0, 0, 0)
        thresholds_grid.setHorizontalSpacing(8)
        thresholds_grid.setVerticalSpacing(6)
        self._similarity_threshold_spinboxes = {}
        for row_index, (key, label_text) in enumerate(SIMILARITY_THRESHOLD_EDITOR_ROWS):
            label = QLabel(label_text)
            spinbox = QDoubleSpinBox()
            spinbox.setDecimals(1)
            spinbox.setRange(0.0, 100.0)
            spinbox.setSingleStep(0.5)
            spinbox.setSuffix("%")
            spinbox.setAlignment(Qt.AlignRight)
            thresholds_grid.addWidget(label, row_index, 0)
            thresholds_grid.addWidget(spinbox, row_index, 1)
            self._similarity_threshold_spinboxes[key] = spinbox
        dev_tools_section.addLayout(thresholds_grid)
        self._load_similarity_thresholds_into_controls()

        thresholds_button_row = QHBoxLayout()
        thresholds_save_button = QPushButton("Save Threshold Overrides")
        thresholds_save_button.clicked.connect(self._save_similarity_threshold_overrides)
        thresholds_reset_button = QPushButton("Reset Thresholds to Defaults")
        thresholds_reset_button.clicked.connect(self._reset_similarity_threshold_defaults)
        thresholds_button_row.addWidget(thresholds_save_button)
        thresholds_button_row.addWidget(thresholds_reset_button)
        thresholds_button_row.addStretch(1)
        dev_tools_section.addLayout(thresholds_button_row)

        age_tools_section = self._add_settings_collapsible_section(content_layout, "Age Tools") #should use header format: bold & copper
        age_tools_section.addWidget(QLabel("Age inference tools."))

        self._dev_user_age_label = QLabel("User Age: unavailable")
        self._dev_user_age_label.setWordWrap(True)
        age_tools_section.addWidget(self._dev_user_age_label)

        age_predictor_header = QLabel("Age Distribution Predictor")
        age_predictor_header.setStyleSheet(SETTINGS_SECTION_SUBHEADER_STYLE)
        age_tools_section.addWidget(age_predictor_header)

        refresh_predictor_button = QPushButton("Refresh Age Predictor")
        refresh_predictor_button.clicked.connect(self._refresh_dev_age_predictor)
        age_tools_section.addWidget(refresh_predictor_button, alignment=Qt.AlignLeft)

        get_estimated_age_button = QPushButton("Get Estimated Age")
        get_estimated_age_button.setToolTip(
            "Force-estimate age from network ages, even if a self chart age exists."
        )
        get_estimated_age_button.clicked.connect(
            lambda _checked=False: self._refresh_dev_age_predictor(force_guess=True)
        )
        age_tools_section.addWidget(get_estimated_age_button, alignment=Qt.AlignLeft)

        predictor_figure = Figure(figsize=(5.2, 2.6), dpi=100)
        predictor_figure.patch.set_facecolor("#1e1e1e")
        self._dev_age_distribution_canvas = FigureCanvas(predictor_figure)
        self._dev_age_distribution_canvas.setMinimumHeight(230)
        age_tools_section.addWidget(self._dev_age_distribution_canvas)

        self._refresh_dev_age_predictor()

        reset_section = self._add_settings_collapsible_section(content_layout, "Reset") #should use header format: bold & copper
        reset_section.addWidget(QLabel("Reset the interface to first-launch defaults."))

        reset_interface_button = QPushButton("Reset interface to default")
        reset_interface_button.clicked.connect(self._reset_interface_to_defaults)
        reset_section.addWidget(reset_interface_button)
        content_layout.addStretch(1)

        self._settings_dialog = dialog
        self._resize_and_center_settings_dialog(dialog)
        return dialog

    def _refresh_dev_age_predictor(self, force_guess: bool = False) -> None:
        if self._dev_user_age_label is None or self._dev_age_distribution_canvas is None:
            return

        try:
            details = resolve_user_age_details(
                force_inference=force_guess,
                include_all_chart_types_for_inference=(
                    self._dev_age_inference_include_all_chart_types
                ),
            )
        except Exception as exc:
            logger.exception("Dev Tools age predictor refresh failed")
            self._dev_user_age_label.setText(f"User Age: unavailable (error: {exc})")
            figure = self._dev_age_distribution_canvas.figure
            figure.clear()
            ax = figure.add_subplot(111)
            ax.axis("off")
            ax.text(
                0.5,
                0.5,
                "Age predictor refresh failed.",
                ha="center",
                va="center",
                color="#b0b0b0",
            )
            self._dev_age_distribution_canvas.draw_idle()
            return

        resolved_age = details.get("age")
        source = str(details.get("source") or "unavailable")
        chart_name = details.get("chart_name")

        if not isinstance(resolved_age, int):
            self._dev_user_age_label.setText("User Age: unavailable (no valid birth-year data in DB)")
            figure = self._dev_age_distribution_canvas.figure
            figure.clear()
            ax = figure.add_subplot(111)
            ax.axis("off")
            ax.text(0.5, 0.5, "Not enough data for predictor.", ha="center", va="center", color="#b0b0b0")
            self._dev_age_distribution_canvas.draw_idle()
            return

        if source == "self":
            source_label = f"self-defined ({chart_name or 'Unnamed chart'})"
        else:
            inference_scope = (
                "all chart types"
                if self._dev_age_inference_include_all_chart_types
                else "personal charts only"
            )
            source_label = f"predicted ({inference_scope}): {resolved_age}"

        logger.info("Dev Tools user-age resolver: age=%s source=%s", resolved_age, source_label)
        self._dev_user_age_label.setText(f"User Age: {resolved_age} [{source_label}]")

        distribution = discrete_age_distribution(
            float(resolved_age),
            bin_width=1,
            min_age=0,
            max_age=110,
        )
        if not distribution:
            figure = self._dev_age_distribution_canvas.figure
            figure.clear()
            self._dev_age_distribution_canvas.draw_idle()
            return

        ages = [age for age, _ in distribution]
        probs = [prob for _, prob in distribution]

        figure = self._dev_age_distribution_canvas.figure
        figure.clear()
        figure.patch.set_facecolor("#1e1e1e")
        ax = figure.add_subplot(111)
        ax.set_facecolor("#232323")
        ax.bar(ages, probs, width=0.85, color="#339933", edgecolor="#2d862d", linewidth=0.2)
        ax.set_title("Age Distribution Predictor", fontsize=10, color="#e6e6e6")
        ax.set_xlabel("Network age", fontsize=9, color="#d0d0d0")
        ax.set_ylabel("Probability", fontsize=9, color="#d0d0d0")
        ax.set_xlim(0, 110)
        ax.tick_params(axis="both", labelsize=8, colors="#c9c9c9")
        ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=0.6, color="#777777")
        for spine in ax.spines.values():
            spine.set_color("#666666")

        self._dev_age_distribution_canvas.draw_idle()

    def _reset_interface_to_defaults(self) -> None:
        choice = QMessageBox.question(
            self,
            "Reset interface",
            "Reset all interface visuals and saved view state to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return

        self._settings.remove("manage_charts")
        self._settings.remove("main_window")
        self._settings.remove("app/last_view")
        self._visibility.reset_defaults()
        self._restore_visibility_preferences()
        self._refresh_human_design_menu_visibility()

        self._sort_mode = "alpha"
        self._sort_descending = False
        self._update_sort_button_label()

        self._active_left_panel = "todays_transits"
        self.left_panel_stack.setCurrentWidget(self._left_panel_widgets[self._active_left_panel])
        self._left_panel_visible = True
        self.left_panel_stack.setVisible(True)

        self._active_right_panel = "search"
        self.right_panel_stack.setCurrentWidget(self._right_panel_widgets[self._active_right_panel])
        self._right_panel_visible = True
        self.right_panel_stack.setVisible(True)
        self._content_splitter.setSizes(self._default_content_splitter_sizes())

        parent = self.parent()
        if isinstance(parent, MainWindow):
            for section_key in ("planet_dynamics", "anagrams"):
                parent._chart_analysis_section_visible[section_key] = parent._visibility.get(
                    f"chart_analytics.{section_key}"
                )
            parent._sync_chart_analysis_section_visibility()
            parent._reset_interface_layout_to_defaults()

        QMessageBox.information(self, "Reset complete", "Interface has been reset to defaults.")

    def _add_settings_collapsible_section(
        self,
        parent_layout: QVBoxLayout,
        title: str,
    ) -> QVBoxLayout:
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=True,
            style_sheet=SETTINGS_COLLAPSIBLE_TOGGLE_STYLE,
        )
        toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        container_layout.addWidget(toggle)

        section_content = QFrame()
        section_content.setObjectName("settings_section_content")
        section_content_layout = QVBoxLayout(section_content)
        section_content_layout.setContentsMargins(12, 10, 12, 10)
        section_content_layout.setSpacing(8)
        container_layout.addWidget(section_content)

        def _toggle_section(checked: bool) -> None:
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            section_content.setVisible(checked)

        toggle.toggled.connect(_toggle_section)

        container.setMaximumWidth(640)
        container.setMinimumWidth(320)
        parent_layout.addWidget(container, alignment=Qt.AlignHCenter)
        return section_content_layout

    def _build_settings_subheader_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(SETTINGS_SECTION_SUBHEADER_STYLE)
        return label

    def _set_chart_data_visibility(self, key: str, checked: bool) -> None:
        self._visibility.set(key, checked)
        if key == "chart_data.human_design_alpha_prototype":
            self._refresh_human_design_menu_visibility()

        parent = self.parent()
        if isinstance(parent, MainWindow):
            parent._refresh_chart_preview()

    def _refresh_human_design_menu_visibility(self) -> None:
        layout = self.layout()
        if isinstance(layout, QVBoxLayout):
            configure_manage_dialog_chrome(self, layout)
        parent = self.parent()
        if isinstance(parent, MainWindow):
            configure_main_window_chrome(parent)

    def _set_popout_visibility(self, key: str, checked: bool) -> None:
        self._visibility.set(key, checked)

    def _set_chart_analytics_visibility_from_settings(self, section_key: str, checked: bool) -> None:
        parent = self.parent()
        if isinstance(parent, MainWindow):
            parent._set_chart_analysis_section_visible(section_key, checked)

    def _set_database_metric_section_visibility_from_settings(self, section_key: str, checked: bool) -> None:
        self._set_database_metrics_section_visible(section_key, checked)
        self._refresh_charts(refresh_metrics=True)

    def _resize_and_center_settings_dialog(self, dialog: QDialog) -> None:
        screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
        if screen is None:
            dialog.resize(520, 520)
            return
        geometry = screen.availableGeometry()
        width = min(560, geometry.width() - 40)
        height = min(680, geometry.height() - 40)
        x = geometry.x() + ((geometry.width() - width) // 2)
        y = geometry.y() + ((geometry.height() - height) // 2)
        dialog.setGeometry(x, y, width, height)

    def _toggle_size_checker(self) -> None:
        popup = self._size_checker_popup
        if popup is not None:
            try:
                if popup.isVisible():
                    popup.close()
                    self._size_checker_popup = None
                    main_window = self.parent()
                    if isinstance(main_window, MainWindow):
                        main_window._size_checker_popup = None
                    return
            except RuntimeError:
                popup = None
                self._size_checker_popup = None

        if popup is None:
            popup = SizeCheckerPopup(
                parent_window=self,
                splitter=self._content_splitter,
                title="Size Checker • Database View",
            )
        else:
            popup.set_target(
                parent_window=self,
                splitter=self._content_splitter,
                title="Size Checker • Database View",
            )
        popup.show()
        self._size_checker_popup = popup
        main_window = self.parent()
        if isinstance(main_window, MainWindow):
            main_window._size_checker_popup = popup

    def _launch_manage_sentiments_dialog(self) -> None:
        self._launch_manage_metadata_dialog(
            field=ManageMetadataLabelsDialog.FIELD_SENTIMENTS,
            title="Manage Sentiments",
        )

    def _launch_manage_relationship_types_dialog(self) -> None:
        self._launch_manage_metadata_dialog(
            field=ManageMetadataLabelsDialog.FIELD_RELATIONSHIPS,
            title="Manage Relationship Types",
        )

    def _launch_manage_metadata_dialog(self, *, field: str, title: str) -> None:
        all_labels = list(SENTIMENT_OPTIONS) + list(RELATION_TYPE)
        max_len = max((len(value) for value in all_labels), default=32)
        dialog = ManageMetadataLabelsDialog(
            parent=self,
            load_usage=get_metadata_label_usage,
            apply_change=apply_metadata_label_change,
            label_limit=max_len,
            initial_field=field,
            lock_field=True,
            window_title=title,
        )
        dialog.exec()
        self._refresh_charts(refresh_metrics=True, force_full_analysis_refresh=True)

    def _calibrate_similarity_norms(self) -> None:
        try:
            rows = list_charts()
        except Exception as exc:
            QMessageBox.warning(self, "Similarity calibration failed", f"Could not list charts:\n{exc}")
            return

        chart_ids: list[int] = []
        for row in rows:
            chart_id = int(row[0])
            is_placeholder = bool(row[15]) if len(row) > 15 else False
            if is_placeholder:
                continue
            chart_ids.append(chart_id)

        if len(chart_ids) < 2:
            QMessageBox.information(
                self,
                "Similarity calibration",
                "Need at least 2 non-placeholder charts in the database.",
            )
            return

        charts: list[tuple[int, Chart]] = []
        failed_loads = 0
        for chart_id in chart_ids:
            try:
                chart = load_chart(chart_id)
            except Exception:
                failed_loads += 1
                continue
            charts.append((chart_id, chart))

        if len(charts) < 2:
            QMessageBox.warning(
                self,
                "Similarity calibration failed",
                "Could not load enough charts to compute pairwise similarity.",
            )
            return

        calibration = compute_similarity_calibration([chart for _chart_id, chart in charts])
        if calibration is None:
            QMessageBox.warning(
                self,
                "Similarity calibration failed",
                "No valid chart pairs were available for calibration.",
            )
            return

        thresholds = save_similarity_calibration(self._settings, calibration)
        self._settings.sync()
        self._load_similarity_thresholds_into_controls()

        mode_label = ", ".join(f"{value:.1f}%" for value in calibration.mode_values)
        QMessageBox.information(
            self,
            "Similarity calibration complete",
            "\n".join(
                [
                    "Saved systemwide similarity norms.",
                    "",
                    f"Charts loaded: {len(charts)} ({failed_loads} failed to load)",
                    f"Pairwise comparisons: {calibration.pair_count}",
                    "",
                    f"Minimum: {calibration.minimum:.1f}%",
                    f"Maximum: {calibration.maximum:.1f}%",
                    f"Average: {calibration.average:.1f}%",
                    f"Median: {calibration.median:.1f}%",
                    f"Mode: {mode_label} ({calibration.mode_count} pair(s))",
                    "",
                    *describe_similarity_bands(thresholds),
                ]
            ),
        )

    def _save_similarity_threshold_overrides(self) -> None:
        spinboxes = getattr(self, "_similarity_threshold_spinboxes", None)
        if not isinstance(spinboxes, dict) or not spinboxes:
            return
        thresholds = SimilarityThresholds(
            q20=float(spinboxes["q20"].value()),
            q40=float(spinboxes["q40"].value()),
            q60=float(spinboxes["q60"].value()),
            q80=float(spinboxes["q80"].value()),
        )
        normalized = save_similarity_thresholds(self._settings, thresholds)
        self._settings.sync()
        self._load_similarity_thresholds_into_controls()
        QMessageBox.information(
            self,
            "Similarity thresholds saved",
            "\n".join(
                [
                    "Manual similarity thresholds saved systemwide:",
                    *describe_similarity_bands(normalized),
                ]
            ),
        )

    def _reset_similarity_threshold_defaults(self) -> None:
        save_similarity_thresholds(self._settings, SimilarityThresholds.defaults())
        self._settings.sync()
        self._load_similarity_thresholds_into_controls()

    def _load_similarity_thresholds_into_controls(self) -> None:
        spinboxes = getattr(self, "_similarity_threshold_spinboxes", None)
        if not isinstance(spinboxes, dict) or not spinboxes:
            return
        thresholds = load_similarity_thresholds(self._settings)
        values = {
            "q20": thresholds.q20,
            "q40": thresholds.q40,
            "q60": thresholds.q60,
            "q80": thresholds.q80,
        }
        for key, value in values.items():
            spinbox = spinboxes.get(key)
            if spinbox is None:
                continue
            blocker = QSignalBlocker(spinbox)
            spinbox.setValue(float(value))
            del blocker

    def _ensure_help_overlay_widgets(self) -> None:
        if hasattr(self, "_help_scrim"):
            return

        self._help_scrim = QWidget(self)
        self._help_scrim.hide()
        self._help_scrim.setStyleSheet("background-color: rgba(0, 0, 0, 26);")

        self._help_side_panel = QFrame(self._help_scrim)
        self._help_side_panel.setStyleSheet(
            "QFrame {"
            "background-color: #616161;"
            "border-right: 1px solid #f2c94c;"
            "}"
            "QLabel { color: #ffffff; }"
            "QLineEdit {"
            "background-color: #737373;"
            "border: 1px solid #f2c94c;"
            "color: #ffffff;"
            "padding: 6px;"
            "border-radius: 4px;"
            "}"
            "QListWidget {"
            "background-color: #6a6a6a;"
            "border: 1px solid #f2c94c;"
            "color: #ffffff;"
            "}"
        )
        panel_layout = QVBoxLayout(self._help_side_panel)
        panel_layout.setContentsMargins(14, 12, 14, 14)
        panel_layout.setSpacing(10)

        panel_title = QLabel("❓") #"Help"
        panel_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f2c94c;")
        panel_layout.addWidget(panel_title)

        panel_hint = QLabel("Search feature explanations and developer notes.")
        panel_hint.setWordWrap(True)
        panel_layout.addWidget(panel_hint)

        self._help_search_edit = QLineEdit()
        self._help_search_edit.setPlaceholderText("Search help notes…")
        self._help_search_edit.textChanged.connect(self._refresh_help_search_results)
        panel_layout.addWidget(self._help_search_edit)

        self._help_results_list = QListWidget()
        self._help_results_list.currentRowChanged.connect(self._show_selected_help_entry)
        panel_layout.addWidget(self._help_results_list, 1)

        self._help_entry_detail = QLabel()
        self._help_entry_detail.setWordWrap(True)
        self._help_entry_detail.setContentsMargins(10, 10, 10, 10)
        self._help_entry_detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._help_entry_detail.setStyleSheet(
            "background-color: #5a5a5a; border: 1px solid #f2c94c; border-radius: 4px; padding: 12px;"
        )
        self._help_entry_detail_scroll = QScrollArea()
        self._help_entry_detail_scroll.setWidgetResizable(True)
        self._help_entry_detail_scroll.setFrameShape(QScrollArea.NoFrame)
        self._help_entry_detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._help_entry_detail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._help_entry_detail_scroll.setMinimumHeight(240)
        self._help_entry_detail_scroll.setWidget(self._help_entry_detail)
        panel_layout.addWidget(self._help_entry_detail_scroll, 2)

        self._help_icon_button = QToolButton(self._help_side_panel)
        self._help_icon_button.setText("?")
        self._help_icon_button.setToolTip("Open the Help panel.")
        self._help_icon_button.clicked.connect(self._open_help_side_panel)
        self._help_icon_button.setStyleSheet(
            "QToolButton {"
            "background-color: #f2c94c;"
            "color: #14213d;"
            "border: 1px solid #14213d;"
            "border-radius: 10px;"
            "font-weight: 700;"
            "font-size: 16px;"
            "padding: 0px;"
            "}"
        )
        self._help_icon_button.setFixedSize(20, 20)

        self._help_icon_close = QPushButton("×", self._help_side_panel)
        self._help_icon_close.setToolTip("Close Help overlay")
        self._help_icon_close.clicked.connect(self._disable_help_overlay)
        self._help_icon_close.setFixedSize(18, 18)
        self._help_icon_close.setStyleSheet(
            "QPushButton {"
            "background-color: #9a9a9a;"
            "color: #2f2f2f;"
            "border: 1px solid #4f4f4f;"
            "border-radius: 9px;"
            "font-size: 16px;"
            "padding: 0px;"
            "}"
        )

        self._help_resize_overlay()
        self._refresh_help_search_results()

    def _help_resize_overlay(self) -> None:
        if not hasattr(self, "_help_scrim"):
            return
        self._help_scrim.setGeometry(0, 0, self.width(), self.height())
        self._help_side_panel.setGeometry(0, 0, 320, self._help_scrim.height())
        right_edge = self._help_side_panel.width() - 12
        self._help_icon_close.move(right_edge - self._help_icon_close.width(), 12)
        self._help_icon_button.move(
            self._help_icon_close.x() - 8 - self._help_icon_button.width(),
            12,
        )

    def _toggle_help_overlay(self) -> None:
        if self._help_overlay_active:
            self._disable_help_overlay()
        else:
            self._enable_help_overlay()

    def _enable_help_overlay(self) -> None:
        self._ensure_help_overlay_widgets()
        self._help_overlay_active = True
        self._help_scrim.show()
        self._help_scrim.raise_()
        self._help_side_panel.show()
        #self._rebuild_help_markers()

    def _disable_help_overlay(self) -> None:
        self._help_overlay_active = False
        self._clear_help_markers()
        if hasattr(self, "_help_scrim"):
            self._help_scrim.hide()

    def _open_help_side_panel(self) -> None:
        if not self._help_overlay_active:
            return
        self._help_side_panel.show()
        self._help_side_panel.raise_()
        self._help_search_edit.setFocus()

    def _clear_help_markers(self) -> None:
        for marker in self._help_marker_buttons:
            marker.deleteLater()
        self._help_marker_buttons.clear()

    def _rebuild_help_markers(self) -> None:
        if not self._help_overlay_active:
            return
        self._clear_help_markers()
        if not hasattr(self, "_help_scrim"):
            return

        for widget in self._iter_help_target_widgets():
            marker = QToolButton(self._help_scrim)
            marker.setText("?")
            marker.setFixedSize(14, 14)
            marker.setStyleSheet(
                "QToolButton {"
                "background-color: #f2c94c;"
                "color: #14213d;"
                "border: 1px solid #14213d;"
                "border-radius: 7px;"
                "font-size: 10px;"
                "font-weight: 700;"
                "padding: 0px;"
                "}"
            )
            widget_label = self._help_widget_label(widget)
            marker.setToolTip(help_notes.tooltip_for_widget(widget.objectName(), widget_label))
            top_right = widget.mapTo(self._help_scrim, QPoint(widget.width() - 2, 2))
            marker.move(top_right.x() - marker.width() // 2, top_right.y() - marker.height() // 2)
            marker.show()
            marker.raise_()
            self._help_marker_buttons.append(marker)

        self._help_side_panel.raise_()
        self._help_icon_button.raise_()
        self._help_icon_close.raise_()

    def _help_widget_label(self, widget: QWidget) -> str:
        if isinstance(widget, QAbstractButton):
            return widget.text().strip()
        if isinstance(widget, QLineEdit):
            return (widget.placeholderText() or widget.objectName()).strip()
        if isinstance(widget, QComboBox):
            return (widget.currentText() or widget.objectName()).strip()
        if isinstance(widget, (QDateEdit, QTimeEdit, QSpinBox)):
            return widget.objectName().strip()
        return ""

    def _iter_help_target_widgets(self) -> list[QWidget]:
        targets: list[QWidget] = []
        candidates = _find_children_for_types(
            self,
            QAbstractButton,
            QLineEdit,
            QComboBox,
            QDateEdit,
            QTimeEdit,
            QSpinBox,
        )
        excluded_widgets = {
            getattr(self, "_help_icon_button", None),
            getattr(self, "_help_icon_close", None),
            getattr(self, "manage_help_overlay_button", None),
        }
        for widget in candidates:
            if widget in excluded_widgets:
                continue
            if hasattr(self, "_help_side_panel") and self._help_side_panel.isAncestorOf(widget):
                continue
            if widget.window() is not self:
                continue
            if not widget.isVisibleTo(self):
                continue
            label = self._help_widget_label(widget)
            if not label:
                continue
            if widget.width() < 24 or widget.height() < 10:
                continue
            targets.append(widget)
        return targets

    def _refresh_help_search_results(self) -> None:
        if not hasattr(self, "_help_results_list"):
            return
        self._help_results_list.clear()
        self._help_search_results_cache = self._search_help_entries_for_current_view(
            self._help_search_edit.text()
        )
        for entry in self._help_search_results_cache:
            self._help_results_list.addItem(entry.title)
        if self._help_search_results_cache:
            self._help_results_list.setCurrentRow(0)
        else:
            self._help_entry_detail.setText("No help entries matched your search.")
            self._help_entry_detail_scroll.verticalScrollBar().setValue(0)

    def _search_help_entries_for_current_view(
        self,
        query: str,
    ) -> tuple[help_notes.HelpEntry, ...]:
        seen_titles: set[str] = set()
        entries: list[help_notes.HelpEntry] = []
        for widget in self._iter_help_target_widgets():
            title = self._help_widget_label(widget)
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            entries.append(
                help_notes.HelpEntry(
                    title=title,
                    description=help_notes.tooltip_for_widget(widget.objectName(), title),
                    keywords=(widget.objectName(),),
                )
            )

        for entry in help_notes.search_help_entries(query):
            if entry.title in seen_titles:
                continue
            seen_titles.add(entry.title)
            entries.append(entry)

        needle = (query or "").strip().lower()
        if not needle:
            return tuple(entries)
        return tuple(
            entry
            for entry in entries
            if needle in entry.title.lower()
            or needle in entry.description.lower()
            or any(needle in keyword.lower() for keyword in entry.keywords)
        )

    def _show_selected_help_entry(self, row: int) -> None:
        if not hasattr(self, "_help_search_results_cache"):
            return
        if row < 0 or row >= len(self._help_search_results_cache):
            self._help_entry_detail.setText("Select an entry to view details.")
            self._help_entry_detail_scroll.verticalScrollBar().setValue(0)
            return
        entry = self._help_search_results_cache[row]
        keywords = ", ".join(entry.keywords)
        suffix = f"\n\nKeywords: {keywords}" if keywords else ""
        self._help_entry_detail.setText(f"{entry.description}{suffix}")
        self._help_entry_detail_scroll.verticalScrollBar().setValue(0)

    def _on_retcon_engine(self) -> None:
        parent = self.parent()
        if parent is None or not hasattr(parent, "on_retcon_engine"):
            QMessageBox.warning(
                self,
                "Retcon Engine",
                "Unable to open Retcon Engine.",
            )
            return
        parent.on_retcon_engine()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self._load_chart_from_item(item)

    def _load_chart_from_item(self, item: QListWidgetItem) -> None:
        chart_id = item.data(Qt.UserRole)
        if chart_id is None:
            return
        parent = self.parent()
        if parent is None or not hasattr(parent, "load_chart_by_id"):
            QMessageBox.warning(
                self,
                "Load chart",
                "Unable to load the selected chart.",
            )
            return
        loaded = parent.load_chart_by_id(chart_id)
        if not loaded:
            return
        if isinstance(parent, QWidget):
            if isinstance(parent, MainWindow):
                parent._show_chart_view_maximized(maximize=self.isMaximized(), source_window=self)
            else:
                parent.showNormal()
                parent.raise_()
                parent.activateWindow()
            if isinstance(parent, MainWindow):
                parent._retarget_size_checker_to_main_view()
        self.hide()

    def _on_edit_chart_from_menu(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            selected = self.list_widget.selectedItems()
            if selected:
                item = selected[0]
        if item is None:
            QMessageBox.warning(
                self,
                "Edit chart",
                "Select a chart in the list before choosing Edit chart.",
            )
            return
        self._load_chart_from_item(item)

    def _on_generate_personal_transit_for_selected_chart(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            selected = self.list_widget.selectedItems()
            if selected:
                item = selected[0]
        if item is None:
            QMessageBox.warning(
                self,
                "Personal Transit Chart",
                "Select a chart in the list before generating a personal transit chart.",
            )
            return

        chart_id = item.data(Qt.UserRole)
        if chart_id is None:
            QMessageBox.warning(
                self,
                "Personal Transit Chart",
                "The selected row does not reference a saved chart.",
            )
            return

        self._refresh_personal_transit_chart_options()
        selected_label = None
        suffix = f"[#{int(chart_id)}]"
        for label in self._personal_transit_chart_lookup:
            if label.endswith(suffix):
                selected_label = label
                break
        if selected_label is None:
            QMessageBox.warning(
                self,
                "Personal Transit Chart",
                "Unable to resolve the selected chart for transit generation.",
            )
            return

        self.personal_transit_chart_input.setText(selected_label)
        self._show_current_transits_panel()
        self._on_generate_personal_transit()

    def _on_index_double_clicked(self, index: QModelIndex) -> None:
        item = self.list_widget.itemFromIndex(index)
        if item is None:
            return
        self._load_chart_from_item(item)

#Retcon Engine Window Begins
#Retcon Window Ends

#Familiarity Calculator Window

#Main Window Begins
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        configure_main_window_chrome(self)
        self._apply_dark_theme()
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._visibility = VisibilityStore(self._settings)
        self._feature_hub = FeatureEventHub()
        self._allow_app_exit_close = False
        self._restoring_window_layout = False
        self._window_layout_customized = False
        _apply_minimum_screen_height(self)

        # Chart Entry Window vs Chart Edit Window:
        # - Chart Entry Window: current_chart_id is None (blank fields/new chart).
        # - Chart Edit Window: current_chart_id is set (editing existing chart).
        self.current_chart_id = None
        self._loaded_birth_place = None
        self._loaded_lat = None
        self._loaded_lon = None
        self._searched_birth_place = None
        self._searched_lat = None
        self._searched_lon = None
        self._birth_time_user_overridden = False
        self._retcon_time_user_overridden = False
        self._alignment_score_assigned = False
        self._alignment_programmatic_update = False
        self._lucygoosey = False
        self._sentiment_metrics_autosave_timer = QTimer(self)
        self._sentiment_metrics_autosave_timer.setSingleShot(True)
        self._sentiment_metrics_autosave_timer.timeout.connect(
            self._flush_pending_sentiment_metrics_save
        )
        self._metadata_autosave_timer = QTimer(self)
        self._metadata_autosave_timer.setSingleShot(True)
        self._metadata_autosave_timer.timeout.connect(self._flush_pending_metadata_save)
        # Suppress startup widget signal noise while we populate default values.
        self._suppress_lucygoosey = True
        self._latest_chart = None
        self._sync_chart_right_panel_placeholder_state(None)
        self._pending_render_chart: Chart | None = None
        self._pending_render_sections: set[str] = set()
        self._pending_render_queue: list[str] = []
        self._chart_analytics_render_tokens: dict[str, str] = {}
        self._chart_analytics_dirty_sections: set[str] = {
            "signs",
            "planets",
            "houses",
            "elements",
            "nakshatra",
            "modal",
            "gender",
            "planet_dynamics",
            "similar_charts",
            "anagrams",
        }
        self._render_flush_timer = QTimer(self)
        self._render_flush_timer.setSingleShot(True)
        self._render_flush_timer.timeout.connect(self._flush_scheduled_chart_render)
        self.update_button = None
        self.delete_this_chart_button = None
        self._metric_scroll_widgets: set[QWidget] = set()
        self._metric_chart_titles: dict[QWidget, str] = {}
        self._metric_popout_dialogs: list[QDialog] = []
        self._gemstone_chartwheel_popouts: list[QDialog] = []
        self._chart_analysis_chart_dropdowns: dict[str, QComboBox] = {}
        self._chart_analysis_chart_filenames: dict[str, str] = {}
        self._chart_analysis_section_expanded: dict[str, bool] = {}
        self._chart_analysis_section_visible: dict[str, bool] = {}
        self._chart_analysis_section_layouts: dict[str, QVBoxLayout] = {}
        self._chart_analysis_section_widgets: dict[str, QWidget] = {}
        self._chart_analysis_subtitles: dict[str, QLabel] = {}
        self._chart_analysis_footer_labels: dict[str, QLabel] = {}
        self._chart_analysis_subtitle_by_mode: dict[str, dict[str, str]] = {}
        self._similar_charts_summary_label: QLabel | None = None
        self._similar_charts_mode_dropdown: QComboBox | None = None
        self._similar_charts_list_label: QLabel | None = None
        self._similar_charts_export_button: QToolButton | None = None
        self._similar_charts_export_rows: list[dict[str, Any]] = []
        self._similar_charts_subject_name: str = ""
        self._anagrams_summary_label: QLabel | None = None
        self._anagrams_list_label: QLabel | None = None
        self._anagrams_export_button: QToolButton | None = None
        self._anagrams_source_dropdown: QComboBox | None = None
        self._anagrams_selected_source: str = "name"
        self._anagrams_current_words: list[str] = []
        self._anagrams_clicked_definitions: dict[str, str] = {}
        self._anagrams_current_chart_text: str = ""
        self._anagrams_current_subject_label: str = "Chart name"
        self._chart_view_history: list[int] = []
        self._chart_view_history_index: int = -1
        self._chart_view_navigation_cache: OrderedDict[int, Chart] = OrderedDict()
        self._popout_summary_contexts: dict[QWidget, dict[str, object]] = {}
        self._help_overlay_active = False
        self._help_marker_buttons: list[QToolButton] = []
        self._size_checker_popup: SizeCheckerPopup | None = None
        self._manage_charts_pending_changed_ids: set[int] = set()
        self._charts_controller = ChartsController(
            confirm_discard_or_save=self._confirm_discard_or_save,
            get_or_create_manage_dialog=self._get_or_create_manage_charts_dialog,
            raise_manage_dialog=self._raise_manage_charts_dialog,
            get_pending_changed_ids=lambda: self._manage_charts_pending_changed_ids,
            clear_pending_changed_ids=self._manage_charts_pending_changed_ids.clear,
        )
        self._retcon_dialog_controller = RetconDialogController(self._create_retcon_dialog)
        self._ephemeris_prefetch_controller = EphemerisPrefetchController(
            owner=self,
            offline_mode_checker=ephemeris_offline_mode,
            on_failure=self._on_swiss_ephemeris_prefetch_error,
        )

        central = QWidget()
        self.setCentralWidget(central)

        # Natal Chart View Window: Create New Chart / Edit Individual Chart
        # Top-level layout: left = chart, middle = inputs + output, right = metrics
        root_layout = QVBoxLayout()
        central.setLayout(root_layout)

        # Back button (returns to Database View / Manage Charts window).
        # NOTE: intentionally no longer housed in a top controls row; it now overlays
        # the chart panel so Chart View can reclaim vertical space.
        self.manage_button = QPushButton("↩")
        self.manage_button.setObjectName("manage_button")
        self.manage_button.clicked.connect(self._on_chart_view_back_requested)
        self.manage_button.setToolTip("Back to Database View")
        self.manage_button.setFixedSize(36, 24)
        self.database_view_button = QPushButton("Database View")
        self.database_view_button.setObjectName("database_view_button")
        self.database_view_button.clicked.connect(self.on_manage_charts)
        self.database_view_button.setToolTip("Close Chart View and return to Database View")
        self.database_view_button.setFixedSize(110, 24)
        # Commented out per request: remove the top-row Chart View action buttons
        # and rely on window_chrome menus/actions instead.
        # top_controls.addStretch(1)
        #
        # # New Chart Button
        # self.new_chart_button = QPushButton("New Chart")
        # self.new_chart_button.setObjectName("new_chart_button")
        # self.new_chart_button.clicked.connect(self.on_new_chart)
        # top_controls.addWidget(self.new_chart_button, 0, Qt.AlignRight)
        #
        # # Export Charts Button
        # self.export_chart_button = QPushButton("Export Chart")
        # self.export_chart_button.setObjectName("export_chart_button")
        # self.export_chart_button.setEnabled(False)
        # self.export_chart_button.clicked.connect(self.on_export_chart)
        # top_controls.addWidget(self.export_chart_button, 0, Qt.AlignRight)
        #
        # # Get Current Transits button (makes current chart into a transit chart)
        # self.current_transits_button = QPushButton("Get Transit")
        # self.current_transits_button.setObjectName("current_transits_button")
        # self.current_transits_button.setEnabled(False)
        # self.current_transits_button.clicked.connect(self.on_get_current_transits)
        # self.current_transits_button.setToolTip(
        #     "Open a personal transit popout for this chart at the current UTC time."
        # )
        # top_controls.addWidget(self.current_transits_button, 0, Qt.AlignRight)
        #
        # self.gemstone_chartwheel_button = QPushButton("Create Gemstone Chartwheel")
        # self.gemstone_chartwheel_button.setObjectName("gemstone_chartwheel_button")
        # self.gemstone_chartwheel_button.setEnabled(False)
        # self.gemstone_chartwheel_button.clicked.connect(self.on_create_gemstone_chartwheel)
        # self.gemstone_chartwheel_button.setToolTip(
        #     "Render and export a gemstone chartwheel PNG for the currently open natal chart."
        # )
        # top_controls.addWidget(self.gemstone_chartwheel_button, 0, Qt.AlignRight)
        #
        # self.interpret_astro_age_button = QPushButton("Interpret Astro Age")
        # self.interpret_astro_age_button.setObjectName("interpret_astro_age_button")
        # self.interpret_astro_age_button.setEnabled(False)
        # self.interpret_astro_age_button.clicked.connect(self.on_interpret_astro_age)
        # self.interpret_astro_age_button.setToolTip(
        #     "Open an astro-age interpretation popout for the currently open chart."
        # )
        # top_controls.addWidget(self.interpret_astro_age_button, 0, Qt.AlignRight)
        #
        # self.open_bazi_window_button = QPushButton("Open BaZi Window")
        # self.open_bazi_window_button.setObjectName("open_bazi_window_button")
        # self.open_bazi_window_button.setEnabled(False)
        # self.open_bazi_window_button.clicked.connect(self.on_open_bazi_window)
        # self.open_bazi_window_button.setToolTip(
        #     "Open a BaZi chart window for the currently open chart when complete birth data is available."
        # )
        # top_controls.addWidget(self.open_bazi_window_button, 0, Qt.AlignRight)

        self.new_chart_button = None
        self.export_chart_button = None
        self.current_transits_button = None
        self.gemstone_chartwheel_button = None
        self.interpret_astro_age_button = None
        self.open_bazi_window_button = None

        #Help Button
        # self.help_overlay_button = QPushButton("❓") #"Help"
        # self.help_overlay_button.setObjectName("help_overlay_toggle")
        # self.help_overlay_button.setToolTip("Toggle Help Overlay mode.")
        # self.help_overlay_button.clicked.connect(self._toggle_help_overlay)
        # top_controls.addWidget(self.help_overlay_button, 0, Qt.AlignRight)

        # Top controls row intentionally disabled so Chart View content can shift up.
        # The one remaining back button is overlaid on the chart canvas instead.
        # root_layout.addLayout(top_controls)

        QTimer.singleShot(0, self._start_swiss_ephemeris_prefetch)

        self._main_splitter = QSplitter(Qt.Horizontal)
        self._main_splitter.setHandleWidth(6)
        configure_splitter_handle_resize_cursor(self._main_splitter)
        self._main_splitter.splitterMoved.connect(self._on_main_splitter_moved)
        root_layout.addWidget(self._main_splitter)

        # Chart Entry/Edit Window: LEFT panel (chart preview interface).
        chart_panel = QWidget()
        chart_panel_layout = QVBoxLayout()
        #chart_panel_layout.setContentsMargins(0, 0, 0, 0)
        chart_panel.setLayout(chart_panel_layout)
        chart_panel.setMinimumWidth(280) #was 420

        # Chart preview container within left panel.
        self.chart_container = QWidget()
        self.chart_container_layout = QVBoxLayout()
        #self.chart_container_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_container_layout.setSpacing(0)
        self.chart_canvas_container = QWidget()
        self.chart_canvas_container_layout = QVBoxLayout()
        self.chart_canvas_container_layout.setSpacing(0)
        self.chart_canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_canvas_container.setLayout(self.chart_canvas_container_layout)

        self.chart_canvas_overlay_container = QWidget()
        self.chart_canvas_overlay_layout = QGridLayout()
        self.chart_canvas_overlay_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_canvas_overlay_layout.setSpacing(0)
        self.chart_canvas_overlay_container.setLayout(self.chart_canvas_overlay_layout)
        self.chart_loading_overlay = ChartLoadingOverlay(self)
        self.chart_canvas_overlay_layout.addWidget(self.chart_canvas_container, 0, 0)
        chart_canvas_nav_buttons = QWidget()
        chart_canvas_nav_buttons_layout = QHBoxLayout()
        chart_canvas_nav_buttons_layout.setContentsMargins(0, 0, 0, 0)
        chart_canvas_nav_buttons_layout.setSpacing(6)
        chart_canvas_nav_buttons.setLayout(chart_canvas_nav_buttons_layout)
        chart_canvas_nav_buttons_layout.addWidget(self.manage_button, 0, Qt.AlignLeft)
        chart_canvas_nav_buttons_layout.addWidget(self.database_view_button, 0, Qt.AlignLeft)
        self.chart_canvas_overlay_layout.addWidget(
            chart_canvas_nav_buttons,
            0,
            0,
            alignment=Qt.AlignTop | Qt.AlignLeft,
        )
        self.chart_canvas_overlay_layout.setContentsMargins(6, 6, 0, 0)
        self.manage_button.raise_()
        self.database_view_button.raise_()
        self.chart_container_layout.addWidget(self.chart_canvas_overlay_container, 1)
        self.chart_container.setLayout(self.chart_container_layout)
        chart_panel_layout.addWidget(self.chart_container, 1)

        chart_info_header = QWidget()
        chart_info_header_layout = QHBoxLayout()
        chart_info_header_layout.setContentsMargins(0, 0, 0, 0)
        chart_info_header_layout.setSpacing(6)
        chart_info_header.setLayout(chart_info_header_layout)
        self.chart_info_toggle_button = QPushButton("Chart Info")
        self.chart_info_toggle_button.setCheckable(True)
        self.chart_info_toggle_button.setCursor(Qt.PointingHandCursor)
        self.chart_info_toggle_button.setMinimumHeight(24)
        self.chart_info_toggle_button.clicked.connect(
            lambda: self._set_chart_info_panel_mode("chart_info")
        )
        self.chart_comments_toggle_button = QPushButton("Comments")
        self.chart_comments_toggle_button.setCheckable(True)
        self.chart_comments_toggle_button.setCursor(Qt.PointingHandCursor)
        self.chart_comments_toggle_button.setMinimumHeight(24)
        self.chart_comments_toggle_button.clicked.connect(
            lambda: self._set_chart_info_panel_mode("comments")
        )
        self.chart_source_toggle_button = QPushButton("Source")
        self.chart_source_toggle_button.setCheckable(True)
        self.chart_source_toggle_button.setCursor(Qt.PointingHandCursor)
        self.chart_source_toggle_button.setMinimumHeight(24)
        self.chart_source_toggle_button.clicked.connect(
            lambda: self._set_chart_info_panel_mode("source")
        )
        chart_info_header_layout.addWidget(self.chart_info_toggle_button, 0)
        chart_info_header_layout.addWidget(self.chart_comments_toggle_button, 0)
        chart_info_header_layout.addWidget(self.chart_source_toggle_button, 0)
        chart_info_header_layout.addStretch(1)
        chart_panel_layout.addWidget(chart_info_header, 0)

        # Chart info output area beneath the preview.
        self.chart_info_output = QPlainTextEdit()
        self.chart_info_output.setReadOnly(True)
        self.chart_info_output.setPlaceholderText(
            "Click the ⓘ next to a position or aspect to see details/interpretation."
        )
        self.chart_info_output.setMinimumHeight(140)
        self._chart_info_highlighter = ChartSummaryHighlighter(self.chart_info_output.document())
        self.chart_info_content_stack = QStackedWidget()
        self.chart_info_content_stack.addWidget(self.chart_info_output)
        chart_panel_layout.addWidget(self.chart_info_content_stack, 0)
        self._main_splitter.addWidget(chart_panel)

        # Chart Entry/Edit Window: MIDDLE panel (inputs + output).
        middle_panel = QWidget()
        middle_layout = QVBoxLayout()
        #middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        middle_panel.setLayout(middle_layout)
        middle_panel.setMinimumWidth(360)
        
        self.inputs_layout = QVBoxLayout()
        #self.inputs_layout.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        #form.setContentsMargins(0, 0, 0, 0)
        self.inputs_layout.addLayout(form)

        # Natal Chart View : Middle Panel: INPUT FIELDS!

        #Name & Alias
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name: i.e. Cleopatra")
        self.name_edit.textChanged.connect(self._mark_lucygoosey)
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("Alias: i.e. wr.t nb.t-nfr.w ꜣḫ.t-zḥ")
        self.alias_edit.setText("Alias")
        self.alias_edit.textChanged.connect(self._mark_lucygoosey)
        self.gender_combo = QComboBox()
        self.gender_combo.addItem("Gender", "")
        for gender_option in GENDER_OPTIONS:
            self.gender_combo.addItem(gender_option, gender_option)
        self.gender_combo.setFixedWidth(120)
        self.gender_combo.currentIndexChanged.connect(self._mark_lucygoosey)
        name_row = QHBoxLayout()
        #name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(8)
        name_row.addWidget(self.name_edit, 1)
        name_row.addWidget(self.alias_edit, 0)
        self.alias_edit.setFixedWidth(180)
        name_row_widget = QWidget()
        name_row_widget.setLayout(name_row)
        form.addRow(name_row_widget)

        self.placeholder_chart_checkbox = QCheckBox(
            "placeholder (check if birth date/year is unknown)"
        )
        self.placeholder_chart_checkbox.toggled.connect(self._on_placeholder_toggled)
        self.placeholder_chart_checkbox.toggled.connect(self._mark_lucygoosey)
        placeholder_row = QHBoxLayout()
        placeholder_row.setContentsMargins(8, 0, 0, 0)
        placeholder_row.addWidget(self.placeholder_chart_checkbox, 0, Qt.AlignLeft)
        placeholder_row.addStretch(1)
        placeholder_row_widget = QWidget()
        placeholder_row_widget.setLayout(placeholder_row)
        form.addRow(placeholder_row_widget)
        
        #Birth date
        # Birth date (split fields: MM. DD. YYYY)
        self.birth_month_edit = QLineEdit()
        self.birth_month_edit.setPlaceholderText("MM")
        self.birth_month_edit.setMaxLength(2)
        self.birth_month_edit.setFixedWidth(31)
        self.birth_month_edit.setValidator(QIntValidator(1, 12, self))
        self.birth_month_edit.textChanged.connect(self._on_birth_date_field_changed)
        self.birth_month_edit.textChanged.connect(self._mark_lucygoosey)

        self.birth_day_edit = QLineEdit()
        self.birth_day_edit.setPlaceholderText("DD")
        self.birth_day_edit.setMaxLength(2)
        self.birth_day_edit.setFixedWidth(31)
        self.birth_day_edit.setValidator(QIntValidator(1, 31, self))
        self.birth_day_edit.textChanged.connect(self._on_birth_date_field_changed)
        self.birth_day_edit.textChanged.connect(self._mark_lucygoosey)

        self.birth_year_edit = QLineEdit()
        self.birth_year_edit.setPlaceholderText("YYYY")
        self.birth_year_edit.setMaxLength(4)
        self.birth_year_edit.setFixedWidth(49)
        self.birth_year_edit.setValidator(QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, self))
        self.birth_year_edit.textChanged.connect(self._on_birth_date_field_changed)
        self.birth_year_edit.textChanged.connect(self._mark_lucygoosey)
        self._set_birth_date_fields_from_qdate(QDate(1990, 1, 1))

        def _labeled_birth_date_field(label_text: str, field: QLineEdit) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignHCenter)
            layout.addWidget(label, 0, Qt.AlignHCenter)
            layout.addWidget(field, 0, Qt.AlignHCenter)
            container.setLayout(layout)
            return container

        birth_month_widget = _labeled_birth_date_field("MM", self.birth_month_edit)
        birth_day_widget = _labeled_birth_date_field("DD", self.birth_day_edit)
        birth_year_widget = _labeled_birth_date_field("YYYY", self.birth_year_edit)

        # Birth place: line edit + Search button
        place_row = QHBoxLayout()
        #place_row.setContentsMargins(0, 0, 0, 0)
        place_row.setSpacing(8)
        self.place_edit = QLineEdit()
        self.place_edit.setPlaceholderText("Birthplace: i.e. Alexandria, Egypt")
        self.place_edit.textChanged.connect(self._on_place_text_changed)

        self.place_search_button = QPushButton("Search")
        self.place_search_button.setObjectName("place_search_button")
        self.place_search_button.setFixedWidth(70)
        self.place_search_button.clicked.connect(self.on_search_place)

        place_row.addWidget(self.place_edit, 1)
        place_row.addWidget(self.place_search_button, 0)

        place_row_widget = QWidget()
        place_row_widget.setLayout(place_row)
        form.addRow(place_row_widget)

        #Birth time
        self.time_edit = SegmentedTimeEdit()
        self.time_edit.setDisplayFormat(CHART_VIEW_TIME_INPUT_DISPLAY_FORMAT)
        self.time_edit.setTime(QTime(12, 0))
        self.time_edit.setFixedWidth(CHART_VIEW_TIME_INPUT_WIDTH)
        self.time_unknown_checkbox = QCheckBox("unknown time")
        self.time_unknown_checkbox.toggled.connect(self._on_unknown_time_toggled)
        self.time_unknown_checkbox.toggled.connect(self._mark_lucygoosey)
        self.time_edit.timeChanged.connect(self._on_birth_time_changed)
        self.time_edit.timeChanged.connect(self._mark_lucygoosey)

        self.retcon_time_edit = SegmentedTimeEdit()
        self.retcon_time_edit.setDisplayFormat(CHART_VIEW_TIME_INPUT_DISPLAY_FORMAT)
        self.retcon_time_edit.setTime(QTime(12, 0))
        self.retcon_time_edit.setFixedWidth(CHART_VIEW_TIME_INPUT_WIDTH)
        self.retcon_time_checkbox = QCheckBox("")
        self.retcon_time_checkbox.toggled.connect(self._on_retcon_time_toggled)
        self.retcon_time_checkbox.toggled.connect(self._mark_lucygoosey)
        self.retcon_time_edit.timeChanged.connect(self._on_retcon_time_changed)
        self.retcon_time_edit.timeChanged.connect(self._mark_lucygoosey)
        self.time_unknown_checkbox.setText("?")


        self.year_first_encountered_edit = QLineEdit()
        self.year_first_encountered_edit.setMaxLength(4)
        self.year_first_encountered_edit.setPlaceholderText("Year 1st Encountered")
        self.year_first_encountered_edit.setFixedWidth(56)
        self.year_first_encountered_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$"), self)
        )
        self.year_first_encountered_edit.textChanged.connect(self._on_sentiment_metric_changed)

        self.deceased_checkbox = QCheckBox("💀")
        self.deceased_checkbox.setToolTip("Mark this chart as deceased")
        self.deceased_checkbox.toggled.connect(self._mark_lucygoosey)

        birth_time_row = QHBoxLayout()
        birth_time_row.setContentsMargins(8, 0, 0, 0)
        birth_time_row.setSpacing(8)
        birth_time_row.addWidget(QLabel("Birth date"), 0)
        birth_time_row.addWidget(birth_month_widget, 0)
        #birth_time_row.addWidget(QLabel("."), 0)
        birth_time_row.addWidget(birth_day_widget, 0)
        #birth_time_row.addWidget(QLabel("."), 0)
        birth_time_row.addWidget(birth_year_widget, 0)
        birth_time_row.addWidget(QLabel("Birth Time:"), 0)
        birth_time_row.addWidget(self.time_unknown_checkbox, 0)
        birth_time_row.addWidget(self.time_edit, 0)
        birth_time_row.addSpacing(CHART_VIEW_RECTIFIED_GROUP_LEFT_SPACER)
        birth_time_row.addWidget(QLabel("Use Rectified Time:"), 0) #used to be called "retcon"
        birth_time_row.addSpacing(CHART_VIEW_RECTIFIED_LABEL_CHECKBOX_SPACING)
        birth_time_row.addWidget(self.retcon_time_checkbox, 0)
        birth_time_row.addWidget(self.retcon_time_edit, 0)
        birth_time_row.addWidget(self.deceased_checkbox, 0)
        birth_time_row.addStretch(1)
        form.addRow("", birth_time_row)
        self._update_time_input_text_colors()

        self.chart_source_combo = QComboBox()
        for source_label, source_value in SOURCE_OPTIONS:
            self.chart_source_combo.addItem(source_label, source_value)
        self._chart_type_previous_index = self.chart_source_combo.currentIndex()
        self.chart_source_combo.currentIndexChanged.connect(self._on_chart_type_changed)

        # Sentiment selection panel (checkbox grid).
        self.sentiment_checkboxes = {}
        sentiment_widget = QWidget()
        sentiment_layout = QGridLayout()
        #sentiment_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_options = SENTIMENT_OPTIONS
        sentiment_columns = 2
        sentiment_rows = (len(sentiment_options) + sentiment_columns - 1) // sentiment_columns
        for idx, label in enumerate(sentiment_options):
            checkbox = QCheckBox(label)
            checkbox.toggled.connect(self._on_sentiment_toggled)
            self.sentiment_checkboxes[label] = checkbox
            row = idx % sentiment_rows
            col = idx // sentiment_rows
            sentiment_layout.addWidget(checkbox, row, col)
        sentiment_widget.setLayout(sentiment_layout)
        
        # Relationship selection panel (checkbox grid).
        self.relationship_type_checkboxes = {}
        relationship_widget = QWidget()
        relationship_layout = QGridLayout()
        #relationship_layout.setContentsMargins(0, 0, 0, 0)
        relationship_columns = 2
        relationship_rows = (len(RELATION_TYPE) + relationship_columns - 1) // relationship_columns
        for idx, label in enumerate(RELATION_TYPE):
            checkbox = QCheckBox(label)
            checkbox.toggled.connect(self._on_relationship_type_toggled)
            self.relationship_type_checkboxes[label] = checkbox
            row = idx % relationship_rows
            col = idx // relationship_rows
            relationship_layout.addWidget(checkbox, row, col)
        relationship_widget.setLayout(relationship_layout)

        self.sentiment_relation_row_widget = QWidget()
        self.sentiment_relation_row_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        sentiment_relation_layout = QVBoxLayout()
        sentiment_relation_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_relation_layout.setSpacing(8)
        sentiment_relation_layout.setAlignment(Qt.AlignTop)
        self.sentiment_relation_row_widget.setLayout(sentiment_relation_layout)

        # Sentiment group box container.
        sentiment_box = QFrame()
        sentiment_box.setStyleSheet(
            "QFrame {"
            "background-color: #1c1c1c;"
            "border: 1px solid #2b2b2b;"
            "border-radius: 6px;"
            "}"
        )
        sentiment_box_layout = QVBoxLayout()
        sentiment_box_layout.setContentsMargins(8, 8, 8, 8)
        sentiment_box_layout.setSpacing(6)
        sentiment_box.setLayout(sentiment_box_layout)
        sentiment_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.sentiment_panel_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.sentiment_panel_toggle,
            title="Sentiment Types",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        self.sentiment_panel_toggle.toggled.connect(
            lambda expanded: self._toggle_chart_panel_content(
                self.sentiment_panel_toggle,
                sentiment_widget,
                expanded,
            )
        )
        sentiment_box_layout.addWidget(self.sentiment_panel_toggle)
        sentiment_widget.setVisible(False)
        sentiment_box_layout.addWidget(sentiment_widget)

        # Relationship group box container.
        relationship_box = QFrame()
        relationship_box.setStyleSheet(
            "QFrame {"
            "background-color: #1c1c1c;"
            "border: 1px solid #2b2b2b;"
            "border-radius: 6px;"
            "}"
        )
        relationship_box_layout = QVBoxLayout()
        relationship_box_layout.setContentsMargins(8, 8, 8, 8)
        relationship_box_layout.setSpacing(6)
        relationship_box.setLayout(relationship_box_layout)
        relationship_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.relationship_panel_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.relationship_panel_toggle,
            title="Relationship Types",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        self.relationship_panel_toggle.toggled.connect(
            lambda expanded: self._toggle_chart_panel_content(
                self.relationship_panel_toggle,
                relationship_widget,
                expanded,
            )
        )
        relationship_box_layout.addWidget(self.relationship_panel_toggle)
        relationship_widget.setVisible(False)
        relationship_box_layout.addWidget(relationship_widget)

        sentiment_relation_layout.addWidget(sentiment_box)
        sentiment_relation_layout.addWidget(relationship_box)

        tags_box = QFrame()
        tags_box.setStyleSheet(
            "QFrame {"
            "background-color: #1c1c1c;"
            "border: 1px solid #2b2b2b;"
            "border-radius: 6px;"
            "}"
        )
        tags_box_layout = QVBoxLayout()
        tags_box_layout.setContentsMargins(8, 8, 8, 8)
        tags_box_layout.setSpacing(6)
        tags_box.setLayout(tags_box_layout)
        tags_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.tags_panel_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.tags_panel_toggle,
            title="Tags",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )
        tags_box_layout.addWidget(self.tags_panel_toggle)

        tags_content_widget = QWidget()
        tags_content_layout = QVBoxLayout()
        tags_content_layout.setContentsMargins(0, 0, 0, 0)
        tags_content_layout.setSpacing(4)
        tags_content_widget.setLayout(tags_content_layout)
        self.chart_tags_input = QLineEdit()
        self.chart_tags_input.setPlaceholderText("tumblr, style, comma-separated, tags")
        self.chart_tags_input.textChanged.connect(self._on_chart_tags_changed)
        tags_content_layout.addWidget(self.chart_tags_input)
        self.chart_tags_preview_label = QLabel()
        self.chart_tags_preview_label.setWordWrap(True)
        self.chart_tags_preview_label.setTextFormat(Qt.RichText)
        tags_content_layout.addWidget(self.chart_tags_preview_label)
        self.tags_panel_toggle.toggled.connect(
            lambda expanded: self._toggle_chart_panel_content(
                self.tags_panel_toggle,
                tags_content_widget,
                expanded,
            )
        )
        tags_content_widget.setVisible(False)
        tags_box_layout.addWidget(tags_content_widget)
        sentiment_relation_layout.addWidget(tags_box)
        self._update_tag_completers()

        sentiment_metrics_row = QWidget()
        sentiment_metrics_row.setSizePolicy(
            QSizePolicy.Maximum,
            QSizePolicy.Preferred,
        )
        #Chart Type Dropdown Box
        sentiment_metrics_row_layout = QHBoxLayout()
        sentiment_metrics_row_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_metrics_row_layout.setSpacing(6)
        sentiment_metrics_row_layout.setAlignment(Qt.AlignCenter)
        sentiment_metrics_row.setLayout(sentiment_metrics_row_layout)

        source_controls_widget = QWidget()
        source_controls_layout = QHBoxLayout()
        source_controls_layout.setContentsMargins(0, 0, 0, 0)
        source_controls_layout.setSpacing(6)
        source_controls_layout.addWidget(QLabel("Chart Type:"))
        source_controls_layout.addWidget(self.chart_source_combo)
        source_controls_layout.addWidget(QLabel("Gender:"))
        source_controls_layout.addWidget(self.gender_combo)
        source_controls_layout.addWidget(QLabel("1st Encounter:"))
        source_controls_layout.addWidget(self.year_first_encountered_edit)
        source_controls_layout.addStretch(1)
        source_controls_widget.setLayout(source_controls_layout)

        self.comments_edit = QTextEdit()
        self.comments_edit.setPlaceholderText("Comments")
        self.comments_edit.textChanged.connect(self._mark_lucygoosey)
        self.comments_edit.setMinimumHeight(140)
        self.chart_info_content_stack.addWidget(self.comments_edit)
        self.source_edit = QTextEdit()
        self.source_edit.setPlaceholderText("Source")
        self.source_edit.textChanged.connect(self._mark_lucygoosey)
        self.source_edit.setMinimumHeight(140)
        self.chart_info_content_stack.addWidget(self.source_edit)
        self._chart_info_panel_mode = "comments"
        self._set_chart_info_panel_mode("comments")

        # Chart metadata controls (hidden for Event chart type).
        self.sentiment_metrics_widget = QWidget()
        sentiment_metrics_container_layout = QVBoxLayout()
        sentiment_metrics_container_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_metrics_container_layout.setSpacing(6)
        self.sentiment_metrics_widget.setLayout(sentiment_metrics_container_layout)

        relevance_box = QFrame()
        relevance_box.setStyleSheet(
            "QFrame {"
            "background-color: #1c1c1c;"
            "border: 1px solid #2b2b2b;"
            "border-radius: 6px;"
            "}"
        )
        relevance_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        relevance_box_layout = QVBoxLayout()
        relevance_box_layout.setContentsMargins(8, 8, 8, 8)
        relevance_box_layout.setSpacing(6)
        relevance_box.setLayout(relevance_box_layout)

        self.relevance_panel_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.relevance_panel_toggle,
            title="Relevance",
            expanded=False,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )

        relevance_content_widget = QWidget()
        sentiment_metrics_layout = QGridLayout()
        sentiment_metrics_layout.setHorizontalSpacing(12)
        sentiment_metrics_layout.setVerticalSpacing(8)
        sentiment_metrics_layout.setContentsMargins(0, 0, 0, 0)
        sentiment_metrics_layout.setAlignment(Qt.AlignTop)
        relevance_content_widget.setLayout(sentiment_metrics_layout)
        self.relevance_panel_toggle.toggled.connect(
            lambda expanded: self._toggle_chart_panel_content(
                self.relevance_panel_toggle,
                relevance_content_widget,
                expanded,
            )
        )
        relevance_box_layout.addWidget(self.relevance_panel_toggle)
        relevance_content_widget.setVisible(False)
        relevance_box_layout.addWidget(relevance_content_widget)
        sentiment_metrics_container_layout.addWidget(relevance_box)
        self.positive_sentiment_intensity_spin = QSpinBox()
        self.positive_sentiment_intensity_spin.setRange(1, 10)
        self.positive_sentiment_intensity_spin.setValue(1)
        self.positive_sentiment_intensity_spin.valueChanged.connect(
            self._on_sentiment_metric_changed
        )
        self.negative_sentiment_intensity_spin = QSpinBox()
        self.negative_sentiment_intensity_spin.setRange(1, 10)
        self.negative_sentiment_intensity_spin.setValue(1)
        self.negative_sentiment_intensity_spin.valueChanged.connect(
            self._on_sentiment_metric_changed
        )
        self.familiarity_spin = QSpinBox()
        self.familiarity_spin.setRange(1, 10)
        self.familiarity_spin.setValue(1)
        self.familiarity_spin.setToolTip("")
        self._chart_familiarity_factors = []
        self.familiarity_spin.valueChanged.connect(self._on_sentiment_metric_changed)
        self.alignment_slider = AlignmentEmojiSlider()
        self.alignment_slider.valueChanged.connect(self._on_alignment_changed)
        self.alignment_score_label = QLabel()
        self._update_alignment_score_label(self.alignment_slider.value())
        for spinbox in (
            self.positive_sentiment_intensity_spin,
            self.negative_sentiment_intensity_spin,
            self.familiarity_spin,
        ):
            spinbox.setFixedWidth(max(53, spinbox.sizeHint().width()))
        
        sentiment_metrics_layout.addWidget(
            QLabel("💖 Positive Sentiment Intensity:"),
            0,
            0,
        )
        sentiment_metrics_layout.addWidget(
            self.positive_sentiment_intensity_spin,
            0,
            1,
        )
        sentiment_metrics_layout.addWidget(
            QLabel("💔 Negative Sentiment Intensity:"),
            1,
            0,
        )
        sentiment_metrics_layout.addWidget(
            self.negative_sentiment_intensity_spin,
            1,
            1,
        )
        familiarity_label_widget = QWidget()
        familiarity_label_layout = QHBoxLayout()
        familiarity_label_layout.setContentsMargins(0, 0, 0, 0)
        familiarity_label_layout.setSpacing(4)
        familiarity_label_layout.addWidget(QLabel("Familiarity:"))
        familiarity_calculator_button = QToolButton()
        familiarity_calculator_button.setText("📠")
        familiarity_calculator_button.setAutoRaise(True)
        familiarity_calculator_button.setStyleSheet("QToolButton { border: none; background: transparent; padding: 0; }")
        familiarity_calculator_button.setToolTip("Open Familiarity Calculator")
        familiarity_calculator_button.setCursor(Qt.CursorShape.PointingHandCursor)
        familiarity_calculator_button.clicked.connect(self._open_chart_familiarity_calculator)
        familiarity_label_layout.addWidget(familiarity_calculator_button)
        familiarity_label_widget.setLayout(familiarity_label_layout)
        sentiment_metrics_layout.addWidget(
            familiarity_label_widget,
            2,
            0,
        )
        sentiment_metrics_layout.addWidget(
            self.familiarity_spin,
            2,
            1,
        )
        alignment_box = QFrame()
        alignment_box.setStyleSheet(
            "QFrame {"
            "background-color: #1c1c1c;"
            "border: 1px solid #2b2b2b;"
            "border-radius: 6px;"
            "}"
        )
        alignment_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        alignment_box_layout = QVBoxLayout()
        alignment_box_layout.setContentsMargins(8, 8, 8, 8)
        alignment_box_layout.setSpacing(6)
        alignment_box.setLayout(alignment_box_layout)

        self.alignment_panel_toggle = QToolButton()
        configure_collapsible_header_toggle(
            self.alignment_panel_toggle,
            title="Alignment",
            expanded=True,
            style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
        )

        alignment_content_widget = QWidget()
        alignment_content_layout = QVBoxLayout()
        alignment_content_layout.setContentsMargins(0, 0, 0, 0)
        alignment_content_layout.setSpacing(4)
        alignment_content_layout.addWidget(
            QLabel("😈 Most evil   ⟷   Most altruistic 😇")
        )
        alignment_content_layout.addWidget(self.alignment_slider)
        alignment_content_layout.addWidget(self.alignment_score_label)
        alignment_content_widget.setLayout(alignment_content_layout)
        self.alignment_panel_toggle.toggled.connect(
            lambda expanded: self._toggle_chart_panel_content(
                self.alignment_panel_toggle,
                alignment_content_widget,
                expanded,
            )
        )
        alignment_box_layout.addWidget(self.alignment_panel_toggle)
        alignment_content_widget.setVisible(True)
        alignment_box_layout.addWidget(alignment_content_widget)
        self._toggle_chart_panel_content(
            self.alignment_panel_toggle,
            alignment_content_widget,
            True,
        )
        sentiment_metrics_container_layout.addWidget(alignment_box)

        sentiment_metrics_row_layout.addWidget(source_controls_widget, 0)
        self.inputs_layout.addWidget(sentiment_metrics_row, 0, Qt.AlignHCenter)
        self._apply_chart_type_ui_state(self.chart_source_combo.currentData())

        buttons_layout = QGridLayout()
        self.update_button = QPushButton("Save Chart")
        self.update_button.setObjectName("update_button")
        self.update_button.clicked.connect(
            lambda: self.on_update_chart(show_dialog=True)
        )
        buttons_layout.addWidget(self.update_button, 0, 0)
        self.delete_this_chart_button = QPushButton("❌ Delete This Chart")
        self.delete_this_chart_button.setObjectName("delete_this_chart_button")
        self.delete_this_chart_button.setStyleSheet(
            "QPushButton {"
            "color: #ff6b6b;"
            "font-weight: 700;"
            "}"
        )
        self.delete_this_chart_button.setToolTip(
            "Delete the currently open chart and return to Database View."
        )
        self.delete_this_chart_button.clicked.connect(self._on_delete_this_chart)
        buttons_layout.addWidget(self.delete_this_chart_button, 0, 1)
        self.inputs_layout.addLayout(buttons_layout)

        #keybinds for text input fields - makes hitting Enter work        
        for widget in (
            self.name_edit,
            self.alias_edit,
            self.gender_combo,
            self.birth_month_edit,
            self.birth_day_edit,
            self.birth_year_edit,
            self.time_edit,
            self.retcon_time_edit,
            self.chart_tags_input,
            self.positive_sentiment_intensity_spin,
            self.negative_sentiment_intensity_spin,
            self.familiarity_spin,
            self.alignment_slider,
            self.year_first_encountered_edit,
            self.chart_source_combo,
        ):
            self._bind_enter_update(widget, self.update_button.click)
        self.place_edit.returnPressed.connect(self.place_search_button.click)

        middle_layout.addLayout(self.inputs_layout)

        output_panel = QWidget()
        output_panel_layout = QVBoxLayout()
        output_panel_layout.setContentsMargins(0, 6, 0, 0)
        output_panel_layout.setSpacing(4)
        output_panel.setLayout(output_panel_layout)

        output_controls = QHBoxLayout()
        #output_controls.setContentsMargins(0, 0, 0, 0)
        output_controls.addStretch(1)
        self.aspects_sort_label = QLabel("Aspects")
        self.aspects_sort_label.setStyleSheet("font-weight: bold;")
        self.aspects_sort_combo = QComboBox()
        self.aspects_sort_combo.addItems(NATAL_ASPECT_SORT_OPTIONS)
        self.aspects_sort_combo.setCurrentText("Priority")
        self.aspects_sort_combo.setMinimumWidth(140)
        self.aspects_sort_combo.currentTextChanged.connect(
            self._on_aspects_sort_changed
        )
        output_controls.addWidget(self.aspects_sort_label)
        output_controls.addWidget(self.aspects_sort_combo)
        output_panel_layout.addLayout(output_controls)

        # Output panel: read-only chart summary (below inputs).
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        output_font = self.output_text.font()
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        output_font.setFixedPitch(True)
        output_font.setPointSize(max(output_font.pointSize() - 2, 1))
        self.output_text.setFont(output_font)
        self.output_text.setPlaceholderText(
            "Chart summary will appear here.\n\n"
            "Generate a chart to see positions, houses, and aspects."
        )
        self._output_highlighter = ChartSummaryHighlighter(
            self.output_text.document()
        )
        self.output_text.viewport().installEventFilter(self)
        self.output_share_button = QToolButton(self.output_text.viewport())
        share_icon_path = _get_share_icon_path()
        if share_icon_path:
            self.output_share_button.setIcon(QIcon(share_icon_path))
            self.output_share_button.setIconSize(QSize(14, 14))
        else:
            self.output_share_button.setText("↗")
        self.output_share_button.setAutoRaise(True)
        self.output_share_button.setCursor(Qt.PointingHandCursor)
        self.output_share_button.setToolTip("Export chart data output as Markdown or text")
        self.output_share_button.clicked.connect(self._export_chart_data_output)
        self.output_share_button.resize(22, 22)
        self._position_output_share_button()
        output_panel_layout.addWidget(self.output_text, 1)
        middle_layout.addWidget(output_panel, 1)

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
            f"QLabel, QAbstractButton {{ color: {MIDDLE_PANEL_ACCENT_COLOR}; }}"
            f"QLineEdit::placeholder, QAbstractSpinBox::placeholder {{ color: {MIDDLE_PANEL_PLACEHOLDER_COLOR_RGBA}; }}"
        )

        self._main_splitter.addWidget(middle_panel)

        # Chart Analytics scroll content panel.
        metrics_content = QWidget()
        metrics_content.setFocusPolicy(Qt.StrongFocus)
        self.metrics_layout = QVBoxLayout()
        self.metrics_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.metrics_layout.setContentsMargins(6, 6, 6, 6)
        self.metrics_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        metrics_content.setLayout(self.metrics_layout)

        subjective_notes_panel = QWidget()
        subjective_notes_layout = QVBoxLayout()
        subjective_notes_layout.setContentsMargins(6, 6, 6, 6)
        subjective_notes_layout.setSpacing(6)
        subjective_notes_panel.setLayout(subjective_notes_layout)
        subjective_notes_layout.addWidget(self.sentiment_relation_row_widget)
        subjective_notes_layout.addWidget(self.sentiment_metrics_widget)
        subjective_notes_layout.addStretch(1)
        chart_right_panel = build_chart_right_panel_stack(
            analytics_content_widget=metrics_content,
            subjective_notes_content_widget=subjective_notes_panel,
            on_show_analytics=lambda: self._set_chart_right_panel("analytics"),
            on_show_subjective_notes=lambda: self._set_chart_right_panel("subjective_notes"),
            scrollbar_style=RIGHT_PANEL_SCROLLBAR_STYLE,
        )
        self.metrics_panel = chart_right_panel.container
        self.chart_analytics_panel_button = chart_right_panel.analytics_button
        self.subjective_notes_panel_button = chart_right_panel.subjective_notes_button
        self.chart_right_panel_stack = chart_right_panel.stack
        self.chart_analytics_panel_scroll = chart_right_panel.analytics_scroll
        self.subjective_notes_panel_scroll = chart_right_panel.subjective_notes_scroll

        self._main_splitter.addWidget(self.metrics_panel)
        self.metrics_scroll = self.chart_analytics_panel_scroll
        self._register_metric_scroll_widget(self.chart_analytics_panel_scroll)
        self._register_metric_scroll_widget(metrics_content)

        self._chart_analysis_sections_controller = ChartAnalysisSectionsController(
            owner=self,
            on_dropdown_changed=self._on_chart_analysis_dropdown_changed,
            on_export_chart_csv=self._export_chart_analysis_chart_csv,
            get_share_icon_path=_get_share_icon_path,
            on_section_toggled=self._set_chart_analysis_section_expanded,
        )

        self._chart_analysis_section_visible["planet_dynamics"] = self._visibility.get(
            "chart_analytics.planet_dynamics"
        )
        self._chart_analysis_section_visible["anagrams"] = self._visibility.get(
            "chart_analytics.anagrams"
        )

        self._create_chart_analysis_sections(metrics_content)
        self._create_similar_charts_section(metrics_content)
        anagrams_section = build_anagrams_section(
            panel=metrics_content,
            layout=self.metrics_layout,
            add_collapsible_section=self._add_chart_analysis_collapsible_section,
            on_toggled=lambda checked: self._set_chart_analysis_section_expanded(
                "anagrams",
                checked,
            ),
            on_export_clicked=self._export_anagrams_share,
            on_word_clicked=self._on_anagram_link_activated,
            on_source_changed=self._on_anagram_source_changed,
            get_share_icon_path=_get_share_icon_path,
        )
        self._chart_analysis_section_expanded["anagrams"] = False
        self._anagrams_summary_label = anagrams_section.summary_label
        self._anagrams_list_label = anagrams_section.list_label
        self._anagrams_export_button = anagrams_section.export_button
        self._anagrams_source_dropdown = anagrams_section.source_dropdown
        self._sync_chart_analysis_section_visibility()
        self.metrics_layout.addStretch(1)
        self._active_chart_right_panel = "subjective_notes"
        self._set_chart_right_panel("subjective_notes")

        # Shortcuts
        self._shortcut_quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        self._shortcut_quit.activated.connect(self._quit_app)

        # Close window: Ctrl+W and Cmd+W
        self._shortcut_close_ctrl = QShortcut(QKeySequence("Ctrl+W"), self)
        self._shortcut_close_ctrl.activated.connect(self._on_close_requested)
        self._shortcut_close_cmd = QShortcut(QKeySequence("Meta+W"), self)
        self._shortcut_close_cmd.activated.connect(self._on_close_requested)
        self._shortcut_fullscreen_toggle = QShortcut(QKeySequence("F12"), self)
        self._shortcut_fullscreen_toggle.activated.connect(self._toggle_fullscreen)

        self.chart_canvas = None
        self.sign_chart_canvas = None
        self.planet_chart_canvas = None
        self.house_chart_canvas = None
        self.element_chart_canvas = None
        self._position_info_map = {}
        self._aspect_info_map = {}
        self._species_info_map = {}
        self.nakshatra_wordcloud_canvas = None
        self.modal_distribution_canvas = None
        self.gender_guesser_canvas = None
        self.planet_dynamics_canvas = None
        self._update_chart_ruler_footer(None)
        self._manage_charts_dialog = None
        self._handle_database_health()
        self._configure_main_splitter()
        self._restore_window_settings()
        self._decrease_chart_view_label_font_sizes()
        self._set_chart_right_panel_container_visible(False)
        apply_default_text_tooltips(self)
        self._suppress_lucygoosey = False
        self._set_lucygoosey(False)

    def _decrease_chart_view_label_font_sizes(self) -> None:
        for label in self.findChildren(QLabel):
            font = QFont(label.font())
            size = font.pointSizeF()
            if size <= 0:
                continue
            font.setPointSizeF(max(1.0, size - 1.5))
            label.setFont(font)

    def _mark_lucygoosey(self, *args, **kwargs) -> None:
        if self._suppress_lucygoosey:
            return
        self._set_lucygoosey(True)

    def _create_chart_analysis_header(
        self,
        layout: QVBoxLayout,
        title_text: str,
        chart_key: str,
        default_filename: str,
        dropdown_options: list[tuple[str, str]] | None = None,
    ) -> None:
        self._chart_analysis_sections_controller.create_header(
            layout=layout,
            title_text=title_text,
            chart_key=chart_key,
            default_filename=default_filename,
            dropdown_options=dropdown_options,
        )

    def _update_chart_analysis_subtitle(self, chart_key: str) -> None:
        self._chart_analysis_sections_controller.update_subtitle(chart_key)

    def _set_chart_analysis_section_expanded(self, section_key: str, expanded: bool) -> None:
        self._chart_analysis_sections_controller.set_section_expanded(section_key, expanded)
        if not expanded or self._latest_chart is None:
            return
        render_key = self._chart_analysis_render_key_for_section(section_key)
        if render_key is None:
            return
        self._schedule_chart_render(
            self._latest_chart,
            sections={render_key},
            prioritize_sections=True,
        )

    def _is_chart_analysis_section_visible(self, section_key: str) -> bool:
        return self._chart_analysis_section_visible.get(section_key, True)

    def _set_chart_analysis_section_visible(self, section_key: str, visible: bool) -> None:
        self._chart_analysis_section_visible[section_key] = visible
        self._visibility.set(f"chart_analytics.{section_key}", visible)
        self._sync_chart_analysis_section_visibility()
        if section_key == "anagrams" and visible and self._latest_chart is not None:
            self._mark_chart_analytics_sections_dirty({"anagrams"})
            self._schedule_chart_render(self._latest_chart, sections={"anagrams"})

    def _sync_chart_analysis_section_visibility(self) -> None:
        for section_key, section_widget in self._chart_analysis_section_widgets.items():
            section_widget.setVisible(self._is_chart_analysis_section_visible(section_key))

    def _add_chart_analysis_collapsible_section(
        self,
        panel: QWidget,
        layout: QVBoxLayout,
        title: str,
        *,
        expanded: bool = False,
        on_toggled: Callable[[bool], None] | None = None,
        section_key: str | None = None,
    ) -> QVBoxLayout:
        return self._chart_analysis_sections_controller.add_collapsible_section(
            panel=panel,
            layout=layout,
            title=title,
            expanded=expanded,
            on_toggled=on_toggled,
            section_key=section_key,
        )

    def _add_chart_analysis_section(
        self,
        panel: QWidget,
        *,
        section_key: str,
        section_title: str,
        header_title: str,
        subtitle_text: str,
        default_filename: str,
        chart_container_attr: str,
        chart_layout_attr: str,
        dropdown_options: list[tuple[str, str]] | None = None,
        subtitle_by_mode: dict[str, str] | None = None,
        expanded: bool = True,
    ) -> None:
        self._chart_analysis_sections_controller.add_section(
            panel=panel,
            section_key=section_key,
            section_title=section_title,
            header_title=header_title,
            subtitle_text=subtitle_text,
            default_filename=default_filename,
            chart_container_attr=chart_container_attr,
            chart_layout_attr=chart_layout_attr,
            dropdown_options=dropdown_options,
            subtitle_by_mode=subtitle_by_mode,
            expanded=expanded,
        )

    def _create_chart_analysis_sections(self, panel: QWidget) -> None:
        self._chart_analysis_sections_controller.create_sections(panel)

    def _create_similar_charts_section(self, panel: QWidget) -> None:
        section_layout = self._add_chart_analysis_collapsible_section(
            panel=panel,
            layout=self.metrics_layout,
            title="Similar Charts",
            expanded=False,
            on_toggled=lambda checked: self._set_chart_analysis_section_expanded(
                "similar_charts",
                checked,
            ),
        )
        self._chart_analysis_section_expanded["similar_charts"] = False

        summary_label = QLabel(
            "Finds the top 3 closest matches from saved database charts."
        )
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
        section_layout.addWidget(summary_label)
        self._similar_charts_summary_label = summary_label

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header_layout.addStretch(1)
        dropdown = QComboBox()
        dropdown_font = QFont(dropdown.font())
        dropdown_font.setCapitalization(QFont.AllUppercase)
        if dropdown_font.pointSize() > 0:
            dropdown_font.setPointSize(max(7, dropdown_font.pointSize() - 2))
        dropdown.setFont(dropdown_font)
        dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dropdown.setMinimumContentsLength(14)
        dropdown.setStyleSheet(DATABASE_ANALYTICS_DROPDOWN_STYLE)
        dropdown.addItem("Most Similar", "most_similar")
        dropdown.addItem("Least Similar", "least_similar")
        dropdown.currentIndexChanged.connect(
            lambda _index: self._on_chart_analysis_dropdown_changed("similar_charts")
        )
        header_layout.addWidget(dropdown, 0, Qt.AlignRight)
        self._chart_analysis_chart_dropdowns["similar_charts"] = dropdown
        self._similar_charts_mode_dropdown = dropdown
        export_button = QToolButton()
        share_icon_path = _get_share_icon_path()
        if share_icon_path:
            export_button.setIcon(QIcon(share_icon_path))
            export_button.setIconSize(QSize(14, 14))
        else:
            export_button.setText("↗")
        export_button.setAutoRaise(True)
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.setToolTip("Export similar charts as TXT or Markdown")
        export_button.clicked.connect(self._export_similar_charts_share)
        header_layout.addWidget(export_button, 0, Qt.AlignRight)
        section_layout.addWidget(header_row)
        self._similar_charts_export_button = export_button
        self._similar_charts_export_button.setEnabled(False)

        list_label = QLabel("Generate or load a chart to search for matches.")
        list_label.setWordWrap(True)
        list_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        list_label.setOpenExternalLinks(False)
        list_label.linkActivated.connect(self._on_similar_chart_link_activated)
        section_layout.addWidget(list_label)
        self._similar_charts_list_label = list_label

    def _on_similar_chart_link_activated(self, target: str) -> None:
        try:
            chart_id = int(target)
        except (TypeError, ValueError):
            return
        current_chart_id = self.current_chart_id
        if current_chart_id is None or current_chart_id == chart_id:
            return
        previous_history = list(self._chart_view_history)
        previous_index = self._chart_view_history_index
        if not self._chart_view_history:
            self._chart_view_history = [current_chart_id]
            self._chart_view_history_index = 0
        else:
            self._chart_view_history = self._chart_view_history[: self._chart_view_history_index + 1]
        self._chart_view_history.append(chart_id)
        self._chart_view_history_index = len(self._chart_view_history) - 1
        loaded = self.load_chart_by_id(chart_id, from_chart_link=True)
        if not loaded:
            self._chart_view_history = previous_history
            self._chart_view_history_index = previous_index

    def _on_chart_analysis_dropdown_changed(self, chart_key: str) -> None:
        self._update_chart_analysis_subtitle(chart_key)
        if self._latest_chart is None:
            return
        render_key = self._chart_analysis_render_key_for_section(chart_key)
        if chart_key == "dominant_signs":
            self._render_sign_tally(self._latest_chart)
        elif chart_key == "dominant_planets":
            self._render_planet_tally(self._latest_chart)
        elif chart_key == "dominant_houses":
            self._render_house_tally(self._latest_chart)
        elif chart_key == "dominant_elements":
            self._render_element_tally(self._latest_chart)
        elif chart_key == "nakshatra_prevalence":
            self._render_nakshatra_wordcloud(self._latest_chart)
        elif chart_key == "modal_distribution":
            self._render_modal_distribution(self._latest_chart)
        elif chart_key == "gender_guesser":
            self._render_gender_guesser(self._latest_chart)
        elif chart_key == "planet_dynamics":
            self._render_planet_dynamics(self._latest_chart)
        elif chart_key == "similar_charts":
            self._render_similar_charts(self._latest_chart)
        if render_key is not None:
            self._mark_chart_analytics_sections_clean({render_key}, self._latest_chart)

    def _render_similar_charts(self, chart: Chart) -> None:
        if self._similar_charts_list_label is None:
            return
        if getattr(chart, "is_placeholder", False):
            self._similar_charts_export_rows = []
            self._similar_charts_subject_name = ""
            if self._similar_charts_export_button is not None:
                self._similar_charts_export_button.setEnabled(False)
            self._similar_charts_list_label.setText(
                "Similar chart matching is disabled for placeholder charts."
            )
            return

        try:
            rows = list_charts()
        except Exception as exc:
            self._similar_charts_export_rows = []
            self._similar_charts_subject_name = ""
            if self._similar_charts_export_button is not None:
                self._similar_charts_export_button.setEnabled(False)
            self._similar_charts_list_label.setText(
                f"Could not read saved charts for twin matching:\n{exc}"
            )
            return

        candidates: list[tuple[int, Chart]] = []
        for row in rows:
            chart_id = int(row[0])
            is_placeholder = bool(row[15]) if len(row) > 15 else False
            if self.current_chart_id is not None and chart_id == self.current_chart_id:
                continue
            if is_placeholder:
                continue
            try:
                candidate = load_chart(chart_id)
            except Exception:
                continue
            candidates.append((chart_id, candidate))

        if not candidates:
            self._similar_charts_export_rows = []
            self._similar_charts_subject_name = ""
            if self._similar_charts_export_button is not None:
                self._similar_charts_export_button.setEnabled(False)
            self._similar_charts_list_label.setText(
                "Need at least one additional non-placeholder saved chart in the database."
            )
            return

        matches = find_astro_twins(
            chart,
            candidates,
            top_k=3,
            exclude_chart_id=self.current_chart_id,
            least_similar=(self._chart_analysis_selected_mode("similar_charts", "most_similar") == "least_similar"),
        )
        if not matches:
            self._similar_charts_export_rows = []
            self._similar_charts_subject_name = ""
            if self._similar_charts_export_button is not None:
                self._similar_charts_export_button.setEnabled(False)
            self._similar_charts_list_label.setText("No similar charts found.")
            return

        self._similar_charts_subject_name = str(getattr(chart, "name", "") or "Current chart").strip()
        self._similar_charts_export_rows = []
        if self._similar_charts_export_button is not None:
            self._similar_charts_export_button.setEnabled(True)
        match_blocks: list[str] = []
        for rank, match in enumerate(matches, start=1):
            safe_name = html.escape(match.chart_name)
            similarity_percent = match.score * 100.0
            band_label, band_color = self._similarity_band_for_percent(similarity_percent)
            rank_label = (
                f'<span style="font-weight: bold; color: {CHART_DATA_HIGHLIGHT_COLOR};">'
                f"{rank}."
                "</span>"
            )
            match_blocks.append(
                (
                    f'{rank_label} #{match.chart_id} — <a href="{match.chart_id}">{safe_name}</a><br>'
                    f'Similarity <span style="color: {band_color}; font-weight: 600;">'
                    f"{similarity_percent:.1f}% ({band_label})"
                    f"</span>"
                    f" (placements {match.placement_score * 100.0:.0f}%,"
                    f" aspects {match.aspect_score * 100.0:.0f}%,"
                    f" distribution {match.distribution_score * 100.0:.0f}%)"
                )
            )
            self._similar_charts_export_rows.append(
                {
                    "rank": rank,
                    "chart_id": match.chart_id,
                    "chart_name": match.chart_name,
                    "similarity_percent": round(similarity_percent, 1),
                    "similarity_band": band_label,
                    "placement_percent": round(match.placement_score * 100.0, 1),
                    "aspect_percent": round(match.aspect_score * 100.0, 1),
                    "distribution_percent": round(match.distribution_score * 100.0, 1),
                }
            )
        self._similar_charts_list_label.setText("<br><br>".join(match_blocks))

    def _similarity_band_for_percent(self, similarity_percent: float) -> tuple[str, str]:
        thresholds = load_similarity_thresholds(self._settings)
        band = classify_similarity(similarity_percent, thresholds)
        return band.label, band.color

    def _export_similar_charts_share(self) -> None:
        if not self._similar_charts_export_rows:
            QMessageBox.information(
                self,
                "Export similar charts",
                "Generate or load a chart first.",
            )
            return
        export_date = datetime.date.today().isoformat()
        subject_token = self._sanitize_export_token(self._similar_charts_subject_name or "chart")
        file_path = _get_text_export_path(
            self,
            self._settings,
            dialog_title="Export similar charts",
            default_stem=f"similar-charts-{subject_token}-{export_date}",
            preference_key=SIMILAR_CHARTS_EXPORT_FORMAT_KEY,
            default_extension=".txt",
        )
        if not file_path:
            return

        is_markdown = file_path.lower().endswith(".md")
        lines: list[str] = []
        if is_markdown:
            lines.append(f"# Similar Charts for {self._similar_charts_subject_name or 'Current chart'}")
            lines.append("")
            lines.append(
                "| Rank | Chart ID | Chart | Similarity | Band | Placement | Aspects | Distribution |"
            )
            lines.append("|---:|---:|---|---:|---|---:|---:|---:|")
            for row in self._similar_charts_export_rows:
                lines.append(
                    f"| {row['rank']} | {row['chart_id']} | {row['chart_name']} | "
                    f"{row['similarity_percent']:.1f}% | {row.get('similarity_band', '')} | {row['placement_percent']:.1f}% | "
                    f"{row['aspect_percent']:.1f}% | {row['distribution_percent']:.1f}% |"
                )
        else:
            lines.append(f"Similar Charts for {self._similar_charts_subject_name or 'Current chart'}")
            lines.append("")
            for row in self._similar_charts_export_rows:
                lines.append(
                    f"{row['rank']}. #{row['chart_id']} — {row['chart_name']}: "
                    f"Similarity {row['similarity_percent']:.1f}% "
                    f"[{row.get('similarity_band', 'unclassified')}] "
                    f"(placements {row['placement_percent']:.1f}%, "
                    f"aspects {row['aspect_percent']:.1f}%, "
                    f"distribution {row['distribution_percent']:.1f}%)"
                )
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines).rstrip() + "\n")
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", f"Could not save export:\n{exc}")
            return
        QMessageBox.information(self, "Export complete", f"Saved similar charts export to:\n{file_path}")

    def _render_anagrams(self, chart: Chart) -> None:
        if self._anagrams_list_label is None:
            return
        source = self._anagrams_selected_source if self._anagrams_selected_source in {"name", "alias"} else "name"
        subject_label = ANAGRAM_SOURCE_LABELS.get(source, "Chart name")
        chart_text = str(getattr(chart, source, "") or "")
        self._anagrams_current_chart_text = chart_text.strip()
        self._anagrams_current_subject_label = subject_label
        if not self._anagrams_current_chart_text:
            self._anagrams_current_words = []
            self._anagrams_clicked_definitions.clear()
            self._anagrams_list_label.setText(
                render_anagrams_text(chart_text, subject_label=subject_label)
            )
            return
        words = collect_anagram_words(self._anagrams_current_chart_text, max_results=30)
        self._anagrams_current_words = words
        self._anagrams_clicked_definitions = {
            word: definition
            for word, definition in self._anagrams_clicked_definitions.items()
            if word in set(words)
        }
        if not words:
            self._anagrams_list_label.setText(
                render_anagrams_text(chart_text, subject_label=subject_label)
            )
            return
        self._anagrams_list_label.setText(
            render_anagrams_html(
                self._anagrams_current_chart_text,
                words,
                self._anagrams_clicked_definitions,
                subject_label=subject_label,
            )
        )

    def _on_anagram_source_changed(self, source_value: str) -> None:
        self._anagrams_selected_source = source_value if source_value in {"name", "alias"} else "name"
        if self._latest_chart is not None:
            self._render_anagrams(self._latest_chart)
        elif self._anagrams_list_label is not None:
            source_label = ANAGRAM_SOURCE_LABELS.get(self._anagrams_selected_source, "Chart name")
            self._anagrams_list_label.setText(
                f"Generate or load a chart to scan {source_label.lower()} letters."
            )

    def _on_anagram_link_activated(self, target: str) -> None:
        if not target.startswith("define:"):
            return
        encoded_word = target.split("define:", 1)[1].strip()
        word = urllib.parse.unquote(encoded_word).strip().casefold()
        if not word or word not in self._anagrams_current_words:
            return
        definition = fetch_word_definition(word)
        self._anagrams_clicked_definitions[word] = definition
        if self._anagrams_list_label is not None:
            self._anagrams_list_label.setText(
                render_anagrams_html(
                    self._anagrams_current_chart_text,
                    self._anagrams_current_words,
                    self._anagrams_clicked_definitions,
                    subject_label=self._anagrams_current_subject_label,
                )
            )

    def _sanitize_export_token(self, value: str, fallback: str = "chart") -> str:
        return _sanitize_export_token(value, fallback)

    def _export_anagrams_share(self) -> None:
        if not self._anagrams_current_chart_text:
            QMessageBox.information(
                self,
                "Export anagrams",
                "Load or generate a chart first.",
            )
            return
        export_date = datetime.datetime.now().strftime("%Y%m%d")
        default_name_token = self._sanitize_export_token(self._anagrams_current_chart_text) or "chart"
        default_filename = f"anagrams-{default_name_token}-{export_date}.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export anagrams",
            default_filename,
            "Markdown (*.md);;Text files (*.txt);;All files (*)",
        )
        if not file_path:
            return
        lines = [
            f"# Anagrams for {self._anagrams_current_subject_label}: {self._anagrams_current_chart_text}",
            "",
            f"- Source: {self._anagrams_current_subject_label}",
            "",
            "## Words",
        ]
        if self._anagrams_current_words:
            lines.extend([f"- {word}" for word in self._anagrams_current_words])
        else:
            lines.append("- (No matches)")
        lines.extend(["", "## Clicked definitions"])
        if self._anagrams_clicked_definitions:
            for word in self._anagrams_current_words:
                definition = self._anagrams_clicked_definitions.get(word)
                if definition:
                    lines.append(f"- **{word}**: {definition}")
        else:
            lines.append("- (No definitions looked up)")
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines).rstrip() + "\n")
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", f"Could not save export:\n{exc}")

    def _chart_analysis_rows_for_key(self, chart_key: str, chart: Chart) -> list[list[Any]]:
        if chart_key == "dominant_signs":
            mode = self._chart_analysis_selected_mode(chart_key, "dominant_signs")
            if mode == "sign_prevalence":
                counts = _calculate_sign_prevalence_counts(chart)
            else:
                counts = _calculate_dominant_sign_weights(chart)
            return [[sign, counts.get(sign, 0)] for sign in ZODIAC_NAMES]
        if chart_key == "dominant_planets":
            mode = self._chart_analysis_selected_mode(chart_key, "dominant_planets")
            if mode == "sidereal_planet_prevalence":
                counts = _calculate_sidereal_planet_prevalence_counts(chart)
                planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
            else:
                counts = _calculate_dominant_planet_weights(chart)
                planets = _dominant_planet_keys(chart)
            return [[planet, counts.get(planet, 0)] for planet in planets]
        if chart_key == "dominant_houses":
            mode = self._chart_analysis_selected_mode(chart_key, "dominant_houses")
            if mode == "house_prevalence":
                counts = _calculate_house_prevalence_counts(chart)
            else:
                counts = _calculate_dominant_house_weights(chart)
            return [[str(house_num), counts.get(house_num, 0)] for house_num in range(1, 13)]
        if chart_key == "dominant_elements":
            mode = self._chart_analysis_selected_mode(chart_key, "dominant_elements")
            counts = (
                _calculate_element_prevalence_counts(chart)
                if mode == "elemental_prevalence"
                else _calculate_dominant_element_weights(chart)
            )
            return [[element, counts.get(element, 0)] for element in ("Fire", "Earth", "Air", "Water")]
        if chart_key == "nakshatra_prevalence":
            mode = self._chart_analysis_selected_mode(chart_key, "nakshatra_prevalence")
            counts = (
                _calculate_nakshatra_prevalence_counts(chart)
                if mode == "nakshatra_prevalence"
                else _calculate_dominant_nakshatra_weights(chart)
            )
            return [[name, counts.get(name, 0)] for name, *_ in NAKSHATRA_RANGES]
        if chart_key == "modal_distribution":
            counts = _calculate_modal_distribution_counts(chart)
            return [[mode.capitalize(), counts.get(mode, 0)] for mode in ("cardinal", "mutable", "fixed")]
        if chart_key == "gender_guesser":
            return [
                ["Gender Prevalence", round(_calculate_gender_prevalence_score(chart), 2)],
                ["Gender Weights", round(_calculate_gender_weight_score(chart), 2)],
            ]
        if chart_key == "planet_dynamics":
            selected_planet = self._chart_analysis_selected_mode(chart_key, "")
            scores = getattr(chart, "planet_dynamics_scores", None) or _calculate_planet_dynamics_scores(chart)
            if not selected_planet or selected_planet not in scores:
                selected_planet = next(iter(scores), "")
            if not selected_planet:
                return []
            metric_scores = scores.get(selected_planet, {})
            metric_label_map = {
                "stability": "Groundedness",
                "constructiveness": "Productivity",
                "volatility": "Reactivity",
                "fragility": "Fragility",
                "adaptability": "Resilience",
            }
            metric_order = (
                "stability",
                "constructiveness",
                "volatility",
                "fragility",
                "adaptability",
            )
            return [["planet", selected_planet]] + [
                [metric_label_map.get(metric, metric), metric_scores.get(metric, 0.0)]
                for metric in metric_order
            ]
        return []

    def _export_chart_analysis_chart_csv(self, chart_key: str, chart_title: str) -> None:
        chart = self._latest_chart
        if chart is None:
            QMessageBox.information(self, "No chart", "Generate or load a chart first.")
            return
        rows = self._chart_analysis_rows_for_key(chart_key, chart)
        if not rows:
            QMessageBox.information(self, "Nothing to export", f"No data available for {chart_title}.")
            return

        default_stem = self._chart_analysis_chart_filenames.get(
            chart_key,
            f"ephemeraldaddy_chart_{chart_key}",
        )
        export_date = datetime.datetime.now().strftime("%Y-%m-%d")
        default_filename = f"{default_stem}-{export_date}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {chart_title} as CSV",
            default_filename,
            "CSV Files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["Metric", "Value"])
                writer.writerows(rows)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", f"Could not write CSV file.\n\n{exc}")
            return
        QMessageBox.information(self, "Export complete", f"Exported {chart_title} CSV to:\n{file_path}")

    def _chart_analysis_selected_mode(self, chart_key: str, fallback: str) -> str:
        dropdown = self._chart_analysis_chart_dropdowns.get(chart_key)
        selected_mode = dropdown.currentData() if dropdown is not None else None
        return selected_mode if isinstance(selected_mode, str) else fallback

    @staticmethod
    def _apply_metric_chart_sizing(canvas: FigureCanvas) -> None:
        figure = canvas.figure
        height = int(round(figure.get_size_inches()[1] * figure.get_dpi()))
        if height > 0:
            canvas.setMinimumHeight(height)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        canvas.updateGeometry()

    def _register_metric_scroll_widget(self, widget: QWidget | None) -> None:
        if widget is None:
            return
        self._metric_scroll_widgets.add(widget)
        widget.installEventFilter(self)

    def _register_metric_chart(self, canvas: FigureCanvas, title: str) -> None:
        self._metric_chart_titles[canvas] = title
        self._register_metric_scroll_widget(canvas)

    def _handle_metrics_wheel(self, event) -> bool:
        if self.metrics_scroll is None:
            return False
        scrollbar = self.metrics_scroll.verticalScrollBar()
        pixel_delta = event.pixelDelta().y()
        angle_delta = event.angleDelta().y()
        if pixel_delta:
            scrollbar.setValue(scrollbar.value() - pixel_delta)
        elif angle_delta:
            scroll_amount = int(angle_delta / 120) * scrollbar.singleStep() * 3
            scrollbar.setValue(scrollbar.value() - scroll_amount)
        return True

    def _handle_metrics_keypress(self, event) -> bool:
        if self.metrics_scroll is None:
            return False
        scrollbar = self.metrics_scroll.verticalScrollBar()
        key = event.key()
        if key == Qt.Key_Up:
            scrollbar.setValue(scrollbar.value() - scrollbar.singleStep())
            return True
        if key == Qt.Key_Down:
            scrollbar.setValue(scrollbar.value() + scrollbar.singleStep())
            return True
        if key == Qt.Key_PageUp:
            scrollbar.setValue(scrollbar.value() - scrollbar.pageStep())
            return True
        if key == Qt.Key_PageDown:
            scrollbar.setValue(scrollbar.value() + scrollbar.pageStep())
            return True
        if key == Qt.Key_Home:
            scrollbar.setValue(scrollbar.minimum())
            return True
        if key == Qt.Key_End:
            scrollbar.setValue(scrollbar.maximum())
            return True
        return False

    def _show_metric_canvas_popout(self, canvas: FigureCanvas, title: str) -> None:
        if self._latest_chart is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(*STANDARD_NCV_POPOUT_LAYOUT["window_min_size"]) #dialog.setMinimumSize(720, 540)
        layout = QVBoxLayout()
        layout.setContentsMargins(*STANDARD_NCV_POPOUT_LAYOUT["content_margins"]) #layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)
        figure = self._build_metric_popout_figure(title, self._latest_chart)
        popout_canvas = FigureCanvas(figure)
        popout_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        info_panel = QPlainTextEdit()
        info_panel.setReadOnly(True)
        info_panel.setPlaceholderText(STANDARD_NCV_POPOUT_LAYOUT["info_placeholder"])
        info_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(popout_canvas, STANDARD_NCV_POPOUT_LAYOUT["chart_stretch"])
        layout.addWidget(info_panel, STANDARD_NCV_POPOUT_LAYOUT["info_stretch"])

        if title == "Nakshatra Prevalence":
            # info_panel = QPlainTextEdit()
            # info_panel.setReadOnly(True)
            info_panel.setPlaceholderText(
                "Click a nakshatra ⓘ label to view its description."
            )
            # info_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # layout.addWidget(popout_canvas, 2)
            # layout.addWidget(info_panel, 1)

            def _on_pick(event) -> None:
                artist = getattr(event, "artist", None)
                nakshatra_name = artist.get_gid() if artist is not None else None
                if not isinstance(nakshatra_name, str) or not nakshatra_name:
                    return
                info_panel.setPlainText(_format_nakshatra_description_text(nakshatra_name))

            popout_canvas.mpl_connect("pick_event", _on_pick)
        elif title == "Gender Guesser":
            info_panel.setPlainText(_build_gender_guesser_breakdown_text(self._latest_chart))
        # else:
        #     layout.addWidget(popout_canvas, 1)

        dialog.resize(
            max(900, int(figure.get_figwidth() * figure.get_dpi()) + 80),
            max(650, int(figure.get_figheight() * figure.get_dpi()) + 80),
        )
        self._register_popout_shortcuts(dialog)
        dialog.show()
        self._metric_popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._metric_popout_dialogs.remove(dialog)
            if dialog in self._metric_popout_dialogs
            else None
        )

    def _register_popout_shortcuts(self, dialog: QDialog) -> None:
        dialog._shortcut_close_ctrl = QShortcut(QKeySequence("Ctrl+W"), dialog)
        dialog._shortcut_close_ctrl.activated.connect(dialog.close)
        dialog._shortcut_close_cmd = QShortcut(QKeySequence("Meta+W"), dialog)
        dialog._shortcut_close_cmd.activated.connect(dialog.close)

    def _build_metric_popout_figure(self, title: str, chart: Chart) -> Figure:
        size_by_title = {
            "Signs": (8.5, 4.2),
            "Bodies": (8.5, 4.2),
            "Houses": (8.5, 4.2),
            "Dominant Elements": (8.0, 5.4),
            "Nakshatra Prevalence": (9.0, 6.6),
            "Modes": (8.0, 5.4),
            "Gender Guesser": (8.0, 4.2),
            "Body Dynamics": (8.5, 5.0),
        }
        figsize = size_by_title.get(title, (8.5, 4.6))
        figure = Figure(figsize=figsize)
        figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(CHART_THEME_COLORS["background"])
        if title == "Signs":
            self._draw_sign_tally(ax, chart)
        elif title == "Bodies":
            self._draw_planet_tally(ax, chart)
        elif title == "Houses":
            self._draw_house_tally(ax, chart)
        elif title == "Elements":
            self._draw_element_tally(ax, chart)
        elif title == "Nakshatra Prevalence":
            self._draw_nakshatra_wordcloud(ax, chart)
        elif title == "Modes":
            self._draw_modal_distribution(ax, chart)
        elif title == "Gender Guesser":
            self._draw_gender_guesser(ax, chart)
        elif title == "Body Dynamics":
            self._draw_planet_dynamics(ax, chart)
        return figure

    def _draw_sign_tally(self, ax, chart: Chart) -> None:
        mode = self._chart_analysis_selected_mode("dominant_signs", "dominant_signs")
        weighted_counts = (
            _calculate_sign_prevalence_counts(chart)
            if mode == "sign_prevalence"
            else _calculate_dominant_sign_weights(chart)
        )
        signs = list(ZODIAC_NAMES)
        values = [weighted_counts[sign] for sign in signs]
        colors = [SIGN_COLORS.get(sign, "#6fa8dc") for sign in signs]
        max_value = max(values) if values else 0

        bars = ax.bar(signs, values, color=colors)

        self._apply_standard_ncv_bar_chart_axes(ax, signs)
        ax.tick_params(axis="x", colors=CHART_THEME_COLORS["text"])
        ax.set_ylim(0, max(1, max_value + 1))
        # ax.margins(x=0.03)
        # ax.tick_params(axis="x", labelbottom=False, bottom=False)
        # ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")
        ax.set_anchor("W")
        glyph_offset = max(0.15, (max_value * 0.02) if max_value else 0.15)
        for index, bar in enumerate(bars):
            glyph = ZODIAC_SIGNS[index]
            height = bar.get_height()
            label_height = max(height, 0)
            ax.text(
                bar.get_x() + (bar.get_width() / 2),
                label_height + glyph_offset,
                glyph,
                ha="center",
                va="bottom",
                color=CHART_THEME_COLORS["text"],
                fontsize=7.5,
            )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        ax.figure.tight_layout()
        # ax.figure.subplots_adjust(left=0.18, bottom=0.12, top=0.92, right=0.98)
        ax.figure.subplots_adjust(
            left=STANDARD_NCV_HORIZONTAL_BAR_CHART["left"],
            bottom=STANDARD_NCV_HORIZONTAL_BAR_CHART["bottom"],
            top=STANDARD_NCV_HORIZONTAL_BAR_CHART["top"],
            right=STANDARD_NCV_HORIZONTAL_BAR_CHART["right"],
        )

    def _draw_planet_tally(self, ax, chart: Chart) -> None:
        mode = self._chart_analysis_selected_mode("dominant_planets", "dominant_planets")
        if mode == "sidereal_planet_prevalence":
            planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
            weighted_counts = _calculate_sidereal_planet_prevalence_counts(chart)
        else:
            planets = _dominant_planet_keys(chart)
            weighted_counts = _calculate_dominant_planet_weights(chart)
        values = [weighted_counts[body] for body in planets]
        colors = [PLANET_COLORS.get(body, "#6fa8dc") for body in planets]
        max_value = max(values) if values else 0

        edge_colors = ["#9933ff" if body in OUTLINED_PLANET_KEYS else "none" for body in planets]
        line_widths = [.1 if body in OUTLINED_PLANET_KEYS else 0 for body in planets]
        bars = ax.bar(
            planets,
            values,
            color=colors,
            edgecolor=edge_colors,
            linewidth=line_widths,
        )
        x_labels = [_display_body_name(body) for body in planets]
        self._apply_standard_ncv_bar_chart_axes(ax, x_labels)
        ax.set_ylim(0, max(1, max_value + 1))
        # ax.margins(x=0.03)
        # ax.tick_params(axis="x", labelbottom=False, bottom=False)
        # ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")
        ax.set_anchor("W")
        label_offset = max(0.15, (max_value * 0.02) if max_value else 0.15)
        for bar, label in zip(bars, planets, strict=True):
            height = bar.get_height()
            label_height = max(height, 0)
            ax.text(
                bar.get_x() + (bar.get_width() / 2),
                label_height + label_offset,
                PLANET_GLYPHS.get(label, label),
                ha="center",
                va="bottom",
                color=CHART_THEME_COLORS["text"],
                fontsize=9,
            )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        ax.figure.tight_layout()
        # ax.figure.subplots_adjust(left=0.18, bottom=0.24, top=0.92, right=0.98)
        ax.figure.subplots_adjust(
            left=STANDARD_NCV_HORIZONTAL_BAR_CHART["left"],
            bottom=STANDARD_NCV_HORIZONTAL_BAR_CHART["bottom"],
            top=STANDARD_NCV_HORIZONTAL_BAR_CHART["top"],
            right=STANDARD_NCV_HORIZONTAL_BAR_CHART["right"],
        )

    def _draw_house_tally(self, ax, chart: Chart) -> None:
        use_houses = _chart_uses_houses(chart)
        houses = getattr(chart, "houses", None) if use_houses else None
        house_numbers = list(range(1, 13))
        house_counts = {house_num: 0 for house_num in house_numbers}

        mode = self._chart_analysis_selected_mode("dominant_houses", "dominant_houses")

        if use_houses and houses:
            #planets = [body for body in PLANET_ORDER if body in NATAL_WEIGHT]
            planets = (
                list(PLANET_ORDER)
                if mode == "house_prevalence"
                else [body for body in PLANET_ORDER if body in NATAL_WEIGHT]
            )
            for body in planets:
                if body not in chart.positions:
                    continue
                lon = chart.positions[body]
                house_num = _house_for_longitude(houses, lon)
                if house_num is None:
                    continue
                #house_counts[house_num] += NATAL_WEIGHT.get(body, 1)
                house_counts[house_num] += 1 if mode == "house_prevalence" else NATAL_WEIGHT.get(body, 1)

        values = [house_counts[house_num] for house_num in house_numbers]
        max_value = max(values) if values else 0

        if not use_houses or not houses:
            ax.text(
                0.5,
                0.5,
                "Houses unavailable",
                ha="center",
                va="center",
                color=CHART_THEME_COLORS["text"],
                fontsize=10,
            )
            ax.set_axis_off()
            return

        house_labels = [str(num) for num in house_numbers]
        house_colors = [HOUSE_COLORS.get(label, "#6fa8dc") for label in house_labels]
        bars = ax.bar(house_labels, values, color=house_colors)
        ax.set_ylim(0, max(1, max_value + 1))
        ax.margins(x=0.03)
        ax.tick_params(axis="x", labelsize=9, colors="#f5f5f5")
        ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")
        ax.set_anchor("W")
        label_offset = max(0.15, (max_value * 0.02) if max_value else 0.15)
        for bar, label in zip(bars, house_numbers, strict=True):
            height = bar.get_height()
            label_height = max(height, 0)
            ax.text(
                bar.get_x() + (bar.get_width() / 2),
                label_height + label_offset,
                str(label),
                ha="center",
                va="bottom",
                color=CHART_THEME_COLORS["text"],
                fontsize=8,
            )
        for spine in ax.spines.values():
            spine.set_color("#444444")
        ax.figure.tight_layout()
        ax.figure.subplots_adjust(left=0.18, bottom=0.24, top=0.92, right=0.98)

    def _draw_element_tally(self, ax, chart: Chart) -> None:
        elements = ["Fire", "Earth", "Air", "Water"]
        mode = self._chart_analysis_selected_mode("dominant_elements", "dominant_elements")
        element_counts = (
            _calculate_element_prevalence_counts(chart)
            if mode == "elemental_prevalence"
            else _calculate_dominant_element_weights(chart)
        )

        values = [element_counts[element] for element in elements]
        total = sum(values)
        if total <= 0:
            ax.text(
                0.5,
                0.5,
                "No element data",
                ha="center",
                va="center",
                color=CHART_THEME_COLORS["text"],
                fontsize=10,
            )
            ax.set_axis_off()
            return

        colors = [ELEMENT_COLORS.get(element, "#6fa8dc") for element in elements]
        ax.pie(
            values,
            colors=colors,
            startangle=STANDARD_NCV_PIE_CHART["start_angle"], # startangle=90,
            wedgeprops={"edgecolor": STANDARD_NCV_PIE_CHART["wedge_edge_color"]}, # wedgeprops={"edgecolor": "#111111"},
        )
        legend_label_format = STANDARD_NCV_PIE_CHART["legend_label_format"]
        legend_labels = [
            legend_label_format.format(percent=(value / total) * 100, label=element)
            for element, value in zip(elements, values, strict=True)
        ]
        legend_handles = [
            Patch(facecolor=color, label=label)
            for label, color in zip(legend_labels, colors, strict=True)
        ]
        ax.legend(
            handles=legend_handles,
            loc=STANDARD_NCV_PIE_CHART["legend_loc"], # loc="upper center",
            bbox_to_anchor=STANDARD_NCV_PIE_CHART["legend_anchor"], # bbox_to_anchor=(0.5, -0.08),
            frameon=False,
            labelcolor=STANDARD_NCV_PIE_CHART["legend_label_color"], # labelcolor="#f5f5f5",
            fontsize=STANDARD_NCV_PIE_CHART["legend_font_size"], # fontsize=10,
            ncol=STANDARD_NCV_PIE_CHART["legend_ncol"], # ncol=2,
        )
        # Use explicit subplot bounds so repeated redraws do not keep shrinking
        # the pie plot area when controls (like retcon) trigger chart refreshes.
        ax.figure.subplots_adjust(**STANDARD_NCV_PIE_CHART["subplots_adjust"]) #ax.figure.subplots_adjust(left=0.12, right=0.88, bottom=0.26, top=0.92)

    def _draw_nakshatra_wordcloud(self, ax, chart: Chart) -> None:
        nakshatras = [name for name, *_ in NAKSHATRA_RANGES]
        mode = self._chart_analysis_selected_mode("nakshatra_prevalence", "nakshatra_prevalence")
        counts = (
            _calculate_nakshatra_prevalence_counts(chart)
            if mode == "nakshatra_prevalence"
            else _calculate_dominant_nakshatra_weights(chart)
        )

        values = [counts[name] for name in nakshatras]
        max_value = max(values) if values else 0

        if max_value <= 0:
            ax.text(
                0.5,
                0.5,
                "No nakshatra data",
                ha="center",
                va="center",
                color=CHART_THEME_COLORS["text"],
                fontsize=10,
            )
            ax.set_axis_off()
            return

        bar_colors = [ #nice elegant patch that names according to the color key code
            NAKSHATRA_PLANET_COLOR.get(name, (None, "#6fa8dc"))[1]
            for name in nakshatras
        ]
        ax.bar(nakshatras, values, color=bar_colors)
        _apply_nakshatra_tick_info_markers(ax, nakshatras)

        ax.set_ylim(0, max(1, max_value + 1))
        ax.margins(x=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_margin"]) #ax.margins(x=0.01)
        ax.tick_params(
            axis="x",
            # labelrotation=90,
            # labelsize=7,
            # colors="#f5f5f5",
            # pad=2,
            labelrotation=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_label_rotation"],
            labelsize=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_label_size"],
            colors=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_color"],
            pad=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_pad"],
        )
        ax.tick_params(
            axis="y",
            labelsize=STANDARD_NCV_HORIZONTAL_BAR_CHART["y_tick_label_size"],
            colors=STANDARD_NCV_HORIZONTAL_BAR_CHART["y_tick_color"],
        )
        #ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")
        ax.set_anchor("W")
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        ax.figure.tight_layout()
        # ax.figure.subplots_adjust(left=0.18, bottom=0.46, top=0.92, right=0.98)
        ax.figure.subplots_adjust(
            left=STANDARD_NCV_HORIZONTAL_BAR_CHART["left"],
            bottom=0.46,
            top=STANDARD_NCV_HORIZONTAL_BAR_CHART["top"],
            right=STANDARD_NCV_HORIZONTAL_BAR_CHART["right"],
        )

    def _draw_modal_distribution(self, ax, chart: Chart) -> None:
        modal_order = ["cardinal", "mutable", "fixed"]
        mode_counts = {mode: 0 for mode in modal_order}
        use_houses = _chart_uses_houses(chart)
        mode_colors = {
            "cardinal": "#993333", #burnt orange
            "mutable": "#6699ff", #blue
            "fixed": "#336600", #olive
        }

        for body in PLANET_ORDER:
            if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                continue
            lon = chart.positions.get(body)
            if lon is None:
                continue
            sign = _sign_for_longitude(lon)
            weight = NATAL_WEIGHT.get(body, 1)
            for mode in modal_order:
                if sign in MODES.get(mode, set()):
                    mode_counts[mode] += weight
                    break

        values = [mode_counts[mode] for mode in modal_order]
        total = sum(values)
        if total <= 0:
            ax.text(
                0.5,
                0.5,
                "No modal data",
                ha="center",
                va="center",
                color=CHART_THEME_COLORS["text"],
                fontsize=10,
            )
            ax.set_axis_off()
            return

        colors = [mode_colors.get(mode, "#6fa8dc") for mode in modal_order]
        ax.pie(
            values,
            colors=colors,
            startangle=STANDARD_NCV_PIE_CHART["start_angle"], #startangle=90,
            wedgeprops={"edgecolor": STANDARD_NCV_PIE_CHART["wedge_edge_color"]}, #wedgeprops={"edgecolor": "#111111"},
        )
        legend_label_format = STANDARD_NCV_PIE_CHART["legend_label_format"]
        legend_labels = [
            legend_label_format.format(percent=(value / total) * 100, label=mode.capitalize())
            for mode, value in zip(modal_order, values, strict=True)
        ]
        legend_handles = [
            Patch(facecolor=color, label=label)
            for label, color in zip(legend_labels, colors, strict=True)
        ]
        ax.legend(
            handles=legend_handles,
            # loc="upper center",
            # bbox_to_anchor=(0.5, -0.08),
            loc=STANDARD_NCV_PIE_CHART["legend_loc"],
            bbox_to_anchor=STANDARD_NCV_PIE_CHART["legend_anchor"],
            frameon=False,
            # labelcolor="#f5f5f5",
            # fontsize=10,
            # ncol=2,
            labelcolor=STANDARD_NCV_PIE_CHART["legend_label_color"],
            fontsize=STANDARD_NCV_PIE_CHART["legend_font_size"],
            ncol=STANDARD_NCV_PIE_CHART["legend_ncol"],
        )
        # Use explicit subplot bounds so repeated redraws do not keep shrinking
        # the pie plot area when controls (like retcon) trigger chart refreshes.
        # ax.figure.subplots_adjust(left=0.12, right=0.88, bottom=0.26, top=0.92)
        ax.figure.subplots_adjust(**STANDARD_NCV_PIE_CHART["subplots_adjust"])

    def _apply_standard_ncv_bar_chart_axes(self, ax, labels: list[str]) -> None:
        ax.margins(x=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_margin"])
        ax.set_xticks(range(len(labels)), labels)
        ax.tick_params(
            axis="x",
            labelrotation=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_label_rotation"],
            labelsize=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_label_size"],
            colors=CHART_AXES_STYLE["x_tick"]["colors"],
            pad=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_pad"],
        )
        ax.tick_params(
            axis="y",
            labelsize=STANDARD_NCV_HORIZONTAL_BAR_CHART["y_tick_label_size"],
            colors=CHART_AXES_STYLE["y_tick"]["colors"],
        )

    def _draw_gender_guesser(self, ax, chart: Chart) -> None:
        prevalence_score = _calculate_gender_prevalence_score(chart)
        weighted_score = _calculate_gender_weight_score(chart)

        def _format_gender_delta(score: float, *, mode_label: str) -> str:
            delta_pct = (abs(float(score) - 5.0) / 5.0) * 100.0
            if math.isclose(delta_pct, 0.0, abs_tol=1e-9):
                return f"0.0% androgynous by {mode_label}"
            polarity = "♀" if score > 5.0 else "♂"
            return f"{delta_pct:.1f}% more {polarity} by {mode_label}"

        prevalence_label = _format_gender_delta(prevalence_score, mode_label="prevalence")
        weighted_label = _format_gender_delta(weighted_score, mode_label="weight")

        def _gender_label_color(score: float) -> str:
            if score < 5.0:
                return GENDER_GUESSER_COLORS["masculine"]
            if score > 5.0:
                return GENDER_GUESSER_COLORS["feminine"]
            return CHART_THEME_COLORS["text"]

        prevalence_label_color = _gender_label_color(prevalence_score)
        weighted_label_color = _gender_label_color(weighted_score)

        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(
            gradient,
            extent=(0, 10, -0.08, 0.08),
            cmap="RdYlGn",
            aspect="auto",
            zorder=1,
        )

        ax.scatter(
            prevalence_score,
            0,
            s=82,
            facecolors="#ffffff",
            edgecolors="#111111",
            linewidths=1.3,
            zorder=3,
        )
        ax.scatter(
            weighted_score,
            0,
            s=82,
            facecolors="none",
            edgecolors="#ffffff",
            linewidths=1.7,
            zorder=4,
        )

        ax.text(0, -0.18, "♂", color=GENDER_GUESSER_COLORS["masculine"], ha="left", va="top", fontsize=8) #"Masculine"
        ax.text(10, -0.18, "♀", color=GENDER_GUESSER_COLORS["feminine"], ha="right", va="top", fontsize=8) #"Feminine"
        ax.text(
            0.015,
            1.05,
            f"● {prevalence_label}",
            color=prevalence_label_color,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
        )
        ax.text(
            0.015,
            0.95,
            f"○ {weighted_label}",
            color=weighted_label_color,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
        )

        ax.set_xlim(0, 10)
        ax.set_ylim(-0.35, 0.35)
        ax.set_xticks([0, 2.5, 7.5, 10], labels=["0%", "25%", "75%", "100%"])
        ax.tick_params(axis="x", labelsize=8, colors="#f5f5f5")
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(False)
        ax.figure.tight_layout()
        ax.figure.subplots_adjust(left=0.09, bottom=0.34, top=0.83, right=0.97)

    def _draw_planet_dynamics(self, ax, chart: Chart) -> None:
        scores = getattr(chart, "planet_dynamics_scores", None) or _calculate_planet_dynamics_scores(chart)
        selected_planet = self._chart_analysis_selected_mode("planet_dynamics", "")
        if not selected_planet or selected_planet not in scores:
            selected_planet = next(iter(scores), "")

        if not selected_planet:
            ax.text(0.5, 0.5, "No planet dynamics data", ha="center", va="center", color="#f5f5f5", fontsize=10)
            ax.set_axis_off()
            return

        metric_order = [
            "stability",
            "constructiveness",
            "volatility",
            "fragility",
            "adaptability",
        ]
        metric_labels = ["Groundedness", "Productivity", "Reactivity", "Fragility", "Resilience"]
        values = [float(scores[selected_planet].get(metric, 0.0)) for metric in metric_order]
        bar_colors = [PLANET_DYNAMICS_BAR_COLORS.get(metric, "#6fa8dc") for metric in metric_order]

        bars = ax.bar(metric_labels, values, color=bar_colors)
        self._apply_standard_ncv_bar_chart_axes(ax, metric_labels)
        ax.tick_params(axis="x", colors=CHART_THEME_COLORS["text"])
        max_value = max(values) if values else 0.0
        ax.set_ylim(0, max(10.0, max_value + 0.8))
        ax.set_anchor("W")

        label_offset = max(0.12, (max_value * 0.02) if max_value else 0.12)
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + (bar.get_width() / 2),
                value + label_offset,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                color="#f5f5f5",
                fontsize=8,
            )

        for spine in ax.spines.values():
            spine.set_color(STANDARD_NCV_HORIZONTAL_BAR_CHART["spine_color"])
        ax.set_title(f"{_display_body_name(selected_planet)} Dynamics", color="#f5f5f5", fontsize=10, pad=8)
        ax.figure.tight_layout()
        ax.figure.subplots_adjust(
            left=STANDARD_NCV_HORIZONTAL_BAR_CHART["left"],
            bottom=STANDARD_NCV_HORIZONTAL_BAR_CHART["bottom"],
            top=STANDARD_NCV_HORIZONTAL_BAR_CHART["top"],
            right=STANDARD_NCV_HORIZONTAL_BAR_CHART["right"],
        )

    def _set_lucygoosey(self, is_lucygoosey: bool) -> None:
        self._lucygoosey = is_lucygoosey

    def _current_aspect_sort(self) -> str:
        if hasattr(self, "aspects_sort_combo"):
            return self.aspects_sort_combo.currentText()
        return "Priority"

    def _chart_data_visibility_options(self) -> dict[str, bool]:
        return {
            "show_cursedness": self._visibility.get("chart_data.cursedness"),
            "show_dnd_species": self._visibility.get("chart_data.dnd_species"),
        }

    def _refresh_chart_summary(self, chart: Chart | None = None) -> None:
        if chart is None:
            chart = self._latest_chart
        if chart is None:
            return
        summary, position_info_map, aspect_info_map, species_info_map = format_chart_text(
            chart,
            aspect_sort=self._current_aspect_sort(),
            **self._chart_data_visibility_options(),
        )
        self.output_text.setPlainText(summary)
        self._position_info_map = position_info_map
        self._aspect_info_map = aspect_info_map
        self._species_info_map = species_info_map

    def _build_chart_export_markdown(self, chart: Chart) -> str:
        date_label = chart.dt.strftime("%Y-%m-%d") if chart.dt else "Unknown"
        time_label = (
            "Unknown"
            if getattr(chart, "birthtime_unknown", False)
            else chart.dt.strftime("%H:%M %Z")
        )
        alias = getattr(chart, "alias", None) or ""
        birth_place = getattr(chart, "birth_place", None) or "Unknown"
        use_houses = _chart_uses_houses(chart)
        houses = getattr(chart, "houses", None) if use_houses else None

        lines = [
            f"# Chart Export: {chart.name or 'Unnamed'}",
            "",
            "## Metadata",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Name | {chart.name or 'Unnamed'} |",
            f"| Alias | {alias or '—'} |",
            f"| Birth date | {date_label} |",
            f"| Birth time | {time_label} |",
            f"| Birthplace | {birth_place} |",
            f"| Latitude / Longitude | {chart.lat:.4f} / {chart.lon:.4f} |",
            f"| Birth time unknown | {getattr(chart, 'birthtime_unknown', False)} |",
            f"| Rectified time used | {getattr(chart, 'retcon_time_used', False)} |",
            f"| UTC fallback used | {getattr(chart, 'used_utc_fallback', False)} |",
        ]

        lines.extend([
            "",
            "## Positions",
            "",
            "| Body | Position | Sign | House |",
            "| --- | --- | --- | --- |",
        ])

        ordered_bodies = [body for body in PLANET_ORDER if body in chart.positions]
        extras = sorted(set(chart.positions).difference(ordered_bodies))
        ordered_bodies.extend(extras)
        for body in ordered_bodies:
            lon = chart.positions.get(body)
            if lon is None:
                lines.append(f"| {body} | Unknown | Unknown | — |")
                continue
            if not use_houses and body in {"AS", "MC", "DS", "IC"}:
                lines.append(f"| {body} | Unknown (birth time unknown) | Unknown | — |")
                continue
            sign = _sign_for_longitude(lon)
            pretty_position = _format_longitude(lon)
            house_num = _house_for_longitude(houses, lon) if use_houses else None
            house_label = str(house_num) if house_num else "—"
            lines.append(f"| {body} | {pretty_position} | {sign} | {house_label} |")

        if use_houses and houses:
            lines.extend([
                "",
                "## House Cusps",
                "",
                "| House | Cusp |",
                "| --- | --- |",
            ])
            for idx, cusp in enumerate(houses[:12], start=1):
                lines.append(f"| {idx} | {_format_longitude(cusp)} |")

        lines.extend([
            "",
            "## Aspects",
            "",
            "| Body A | Aspect | Body B | Exact Angle | Orb (Δ) | Score |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ])
        aspects = getattr(chart, "aspects", None) or []
        filtered_aspects = [asp for asp in aspects if not _is_structural_tautology(asp)]
        if not use_houses:
            angular_bodies = {"AS", "MC", "DS", "IC"}
            filtered_aspects = [
                asp
                for asp in filtered_aspects
                if asp.get("p1") not in angular_bodies and asp.get("p2") not in angular_bodies
            ]
        dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not dominant_planet_weights:
            dominant_planet_weights = _calculate_dominant_planet_weights(chart)
        filtered_aspects.sort(
            key=lambda asp: _aspect_score(asp, planet_weights=dominant_planet_weights),
            reverse=True,
        )
        if not filtered_aspects:
            lines.append("| — | — | — | — | — | — |")
        for asp in filtered_aspects:
            lines.append(
                "| "
                f"{asp.get('p1', '?')} | {_aspect_label(asp.get('type', ''))} | {asp.get('p2', '?')} | "
                f"{_format_degree_minutes(float(asp.get('angle', 0.0)), include_sign=False)} | {_format_degree_minutes(float(asp.get('delta', 0.0)))} | "
                f"{_aspect_score(asp, planet_weights=dominant_planet_weights):.2f} |"
            )

        lines.extend([
            "",
            "## Raw Chart Data (JSON)",
            "",
            "```json",
            json.dumps(chart.as_dict(), indent=2, ensure_ascii=False),
            "```",
            "",
        ])
        return "\n".join(lines)

    def _export_chart(self, chart: Chart | None) -> None:
        if chart is None:
            QMessageBox.information(
                self,
                "incomplete birthdate",
                "Generate or load a chart before exporting.",
            )
            return

        chart_title = (chart.name or "chart").strip() or "chart"
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", chart_title).strip("_") or "birthchart"
        export_date = datetime.date.today().isoformat()
        default_filename = f"ephemeraldaddy_{safe_title}_chart-{export_date}.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export chart as Markdown",
            default_filename,
            "Markdown Files (*.md)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".md"):
            file_path = f"{file_path}.md"

        markdown_text = self._build_chart_export_markdown(chart)
        try:
            with open(file_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_text)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export chart markdown:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved chart markdown to:\n{file_path}",
        )

    def on_export_chart(self) -> None:
        self._export_chart(self._latest_chart)

    def _selected_chart_id_from_manage_view(self) -> int | None:
        manage_dialog = self._manage_charts_dialog
        if manage_dialog is None or not hasattr(manage_dialog, "list_widget"):
            return None
        item = manage_dialog.list_widget.currentItem()
        if item is None:
            selected_items = manage_dialog.list_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
        if item is None:
            return None
        raw_chart_id = item.data(Qt.UserRole)
        if raw_chart_id is None:
            return None
        try:
            return int(raw_chart_id)
        except (TypeError, ValueError):
            return None

    def _resolve_chart_for_active_action(
        self,
        requester: QWidget | None = None,
    ) -> tuple[Chart | None, int | None]:
        """Get Active Chart Rule for cross-window chart actions.

        - If Natal Chart View is active: use the currently selected/open chart there.
        - If Database View is active: use the selected chart in the middle chart list.
        - If no chart is selected in the active context: return (None, None).
        """
        manage_dialog = self._manage_charts_dialog
        chart_view_active = requester is self or self.isActiveWindow()
        database_view_active = (
            requester is manage_dialog
            or (
                manage_dialog is not None
                and manage_dialog.isVisible()
                and manage_dialog.isActiveWindow()
            )
        )
        if chart_view_active and self._latest_chart is not None:
            return self._latest_chart, self.current_chart_id

        if database_view_active:
            chart_id = self._selected_chart_id_from_manage_view()
            if chart_id is None:
                return None, None
            try:
                return load_chart(chart_id), chart_id
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Chart action",
                    f"Could not load the selected chart:\n{exc}",
                )
                return None, None

        if self._latest_chart is not None:
            return self._latest_chart, self.current_chart_id

        chart_id = self._selected_chart_id_from_manage_view()
        if chart_id is None:
            return None, None
        try:
            return load_chart(chart_id), chart_id
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Chart action",
                f"Could not load the selected chart:\n{exc}",
            )
            return None, None

    def _run_chart_action_from_active_context(
        self,
        action_name: str,
        requester: QWidget | None = None,
    ) -> None:
        chart, chart_id = self._resolve_chart_for_active_action(requester=requester)
        if chart is None:
            QMessageBox.information(self, "No chart selected", "Please select a chart first.")
            return

        if action_name == "interpret_astro_age":
            self._interpret_astro_age(chart)
        elif action_name == "create_gemstone_chartwheel":
            self._create_gemstone_chartwheel(chart)
        elif action_name == "get_personal_transit":
            self._generate_current_transits_for_chart(chart, chart_id)
        elif action_name == "export_chart":
            self._export_chart(chart)
        elif action_name == "open_bazi_window":
            self._open_bazi_window(chart)
        elif action_name == "get_human_design_info":
            self._latest_chart = chart
            self.on_get_human_design_info()
        else:
            QMessageBox.warning(self, "Chart action", f"Unknown chart action: {action_name}")





    def _show_gemstone_chartwheel_popout(self, image_path: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Gemstone Chartwheel Preview")
        dialog.resize(720, 760)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(640, 640)

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            image_label.setText("Could not load generated chartwheel image preview.")
        else:
            image_label.setPixmap(
                pixmap.scaled(
                    680,
                    680,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        path_label = QLabel(f"Saved to: {image_path}")
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(image_label, 1)
        layout.addWidget(path_label, 0)

        self._register_popout_shortcuts(dialog)
        self._gemstone_chartwheel_popouts.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, d=dialog: self._gemstone_chartwheel_popouts.remove(d)
            if d in self._gemstone_chartwheel_popouts
            else None
        )

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _interpret_astro_age(self, chart: Chart | None) -> None:
        if chart is None:
            QMessageBox.information(
                self,
                "No chart loaded",
                "Generate or load a chart before interpreting astro age.",
            )
            return

        planet_weights = (
            getattr(chart, "dominant_planet_weights", None)
            or _calculate_dominant_planet_weights(chart)
        )
        astro_age = chart_age_from_positions(
            getattr(chart, "positions", {}),
            _sign_for_longitude,
            planet_strengths=planet_weights,
        )
        breakdown = astro_age.get("breakdown", [])
        if not breakdown:
            QMessageBox.information(
                self,
                "Astro age unavailable",
                "No supported planetary placements were found for astro age interpretation.",
            )
            return

        dialog = QDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        chart_name = (getattr(chart, "name", None) or "Chart").strip() or "Chart"
        dialog.setWindowTitle(f"Astro Age Interpretation • {chart_name}")
        dialog.resize(640, 760)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        summary_label = QLabel(
            "\n".join(
                [
                    f"Chart: {chart_name}",
                    f"Weighted mean age: {round(astro_age['mean_age'])}",
                    f"Weighted median age: {round(astro_age['median_age'])}",
                ]
            )
        )
        summary_label.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        summary_font = summary_label.font()
        summary_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        summary_label.setFont(summary_font)
        layout.addWidget(summary_label, 0)

        breakdown_output = QPlainTextEdit()
        breakdown_output.setReadOnly(True)
        breakdown_font = breakdown_output.font()
        breakdown_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        breakdown_output.setFont(breakdown_font)
        breakdown_output.setPlaceholderText("Astro age breakdown unavailable.")

        planet_label_overrides = {
            "Sun": "Identity:",
            "Moon": "Emotionally:",
            "Rising": "1st Impression Given:",
            "Mercury":"Mentally:",
            "Venus":"Romantically:",
            "Mars":"Energetically/Confrontationally:",
            "Jupiter":"Luckwise:",
            "Saturn":"Responsibilities:",
            "Uranus":"Rebellion (Generational):",
            "Neptune":"Ideals (Generational):",
            "Pluto":"Power & crises (Generational):",
            "Rahu":"Becoming:",
            "Ketu":"Leaving behind behavior that's:",
        }

        lines = [
            "POSITION-LEVEL ASTRO AGE BREAKDOWN",
            "",
            f"{'Planet Key':<34} {'Sign':<12} {'Age':>6} {'Band':<20} {'Weight':>7} {'Contribution':>13}",
            "-" * 98,
        ]
        for entry in breakdown:
            label = planet_label_overrides.get(entry["planet"], entry["planet"])
            lines.append(
                f"{label:<34} {entry['sign']:<12} "
                f"{round(entry['placement_age']):>6} {entry['age_band']:<20} "
                f"{round(entry['weight']):>7} {round(entry['weighted_contribution']):>13}"
            )
        breakdown_output.setPlainText("\n".join(lines))
        layout.addWidget(breakdown_output, 1)

        self._register_popout_shortcuts(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def on_interpret_astro_age(self) -> None:
        self._interpret_astro_age(self._latest_chart)

    def _open_bazi_window(self, chart: Chart | None) -> None:
        validation_error = validate_chart_for_bazi(chart)
        if validation_error is not None:
            title = "No chart loaded" if chart is None else "BaZi unavailable"
            message = (
                BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
                if chart is not None and validation_error != "Please select a chart first."
                else validation_error
            )
            QMessageBox.information(self, title, message)
            return

        assert chart is not None
        try:
            dialog = create_bazi_window_dialog(
                self,
                chart,
                header_style=CHART_DATA_POPOUT_HEADER_STYLE,
                monospace_font_family=CHART_DATA_MONOSPACE_FONT_FAMILY,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "BaZi error",
                f"Unable to calculate BaZi chart:\n{exc}",
            )
            return

        self._register_popout_shortcuts(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def on_open_bazi_window(self) -> None:
        self._open_bazi_window(self._latest_chart)

    def on_show_chart_analytics_panel(self) -> None:
        if not self.chart_analytics_panel_button.isEnabled():
            return
        self._set_chart_right_panel("analytics")
        self._set_chart_right_panel_container_visible(True)

    def _create_gemstone_chartwheel(self, chart: Chart | None) -> None:
        if chart is None:
            QMessageBox.information(
                self,
                "No chart loaded",
                "Generate or load a chart before creating a gemstone chartwheel.",
            )
            return

        chart_name = (getattr(chart, "name", None) or "chart").strip() or "chart"
        default_filename = f"{chart_name}-natal_chart-wheel_by-ephemeraldaddy.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Gemstone Chartwheel",
            default_filename,
            "PNG Files (*.png)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".png"):
            file_path = f"{file_path}.png"

        try:
            draw_chartwheel(Path(file_path), chart_positions=chart.positions)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Gemstone chartwheel export failed",
                f"Could not create gemstone chartwheel:\n{exc}",
            )
            return

        self._show_gemstone_chartwheel_popout(file_path)
        QMessageBox.information(
            self,
            "Gemstone chartwheel exported",
            f"Saved gemstone chartwheel to:\n{file_path}",
        )

    def on_create_gemstone_chartwheel(self) -> None:
        self._create_gemstone_chartwheel(self._latest_chart)

    def _on_aspects_sort_changed(self, _value: str) -> None:
        self._refresh_chart_summary()

    def _position_output_share_button(self) -> None:
        if not hasattr(self, "output_share_button") or not hasattr(self, "output_text"):
            return
        viewport = self.output_text.viewport()
        button = self.output_share_button
        margin = 6
        button.move(
            max(margin, viewport.width() - button.width() - margin),
            margin,
        )

    def _set_chart_info_panel_mode(self, mode: str) -> None:
        if mode not in {"chart_info", "comments", "source"}:
            return
        self._chart_info_panel_mode = mode
        if hasattr(self, "chart_info_content_stack"):
            mode_to_index = {"chart_info": 0, "comments": 1, "source": 2}
            self.chart_info_content_stack.setCurrentIndex(mode_to_index[mode])
        self._refresh_chart_info_panel_toggle_buttons()

    def _refresh_chart_info_panel_toggle_buttons(self) -> None:
        active_mode = getattr(self, "_chart_info_panel_mode", "comments")
        chart_info_active = active_mode == "chart_info"
        comments_active = active_mode == "comments"
        source_active = active_mode == "source"
        active_style = (
            "QPushButton { font-weight: 700; padding: 2px 8px; }"
            "QPushButton:checked { background-color: #2f3a5a; border: 1px solid #6f7fb4; }"
        )
        inactive_style = "QPushButton { font-weight: 400; padding: 2px 8px; }"
        if hasattr(self, "chart_info_toggle_button"):
            self.chart_info_toggle_button.blockSignals(True)
            self.chart_info_toggle_button.setChecked(chart_info_active)
            self.chart_info_toggle_button.blockSignals(False)
            self.chart_info_toggle_button.setStyleSheet(
                active_style if chart_info_active else inactive_style
            )
        if hasattr(self, "chart_comments_toggle_button"):
            self.chart_comments_toggle_button.blockSignals(True)
            self.chart_comments_toggle_button.setChecked(comments_active)
            self.chart_comments_toggle_button.blockSignals(False)
            self.chart_comments_toggle_button.setStyleSheet(
                active_style if comments_active else inactive_style
            )
        if hasattr(self, "chart_source_toggle_button"):
            self.chart_source_toggle_button.blockSignals(True)
            self.chart_source_toggle_button.setChecked(source_active)
            self.chart_source_toggle_button.blockSignals(False)
            self.chart_source_toggle_button.setStyleSheet(
                active_style if source_active else inactive_style
            )

    def _export_chart_data_output(self) -> None:
        summary_text = self.output_text.toPlainText().strip()
        if not summary_text:
            QMessageBox.information(
                self,
                "Nothing to export",
                "Generate or load a chart before exporting chart data output.",
            )
            return

        export_date = datetime.date.today().isoformat()
        default_filename = f"chart-data-output-{export_date}.md"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Chart Data Output",
            default_filename,
            "Markdown Files (*.md);;Text Files (*.txt)",
        )
        if not file_path:
            return

        selected_extension = ".txt" if "*.txt" in selected_filter else ".md"
        if not file_path.lower().endswith((".md", ".txt")):
            file_path = f"{file_path}{selected_extension}"

        try:
            with open(file_path, "w", encoding="utf-8") as output_file:
                output_file.write(summary_text)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export chart data output:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved chart data output to:\n{file_path}",
        )

    def _handle_summary_info_click(
        self,
        output_widget: QPlainTextEdit,
        cursor,
        position_info_map: dict[int, list[dict[str, object]]],
        aspect_info_map: dict[int, dict[str, object]],
        species_info_map: dict[int, list[dict[str, object]]],
        target_info_widget: QPlainTextEdit,
        block_offset: int = 0,
    ) -> bool:
        block = cursor.block()
        block_number = block.blockNumber() + block_offset
        block_text = block.text()
        info_index = block_text.rfind("ⓘ")
        if info_index == -1:
            return False

        cursor_pos = cursor.positionInBlock()
        original_chart_info_output = self.chart_info_output
        self.chart_info_output = target_info_widget
        try:
            if target_info_widget is original_chart_info_output:
                self._set_chart_info_panel_mode("chart_info")
            species_entries = species_info_map.get(block_number, [])
            if species_entries:
                selected_species = None
                for entry in sorted(species_entries, key=lambda item: item["icon_index"]):
                    if cursor_pos >= entry["icon_index"]:
                        selected_species = entry
                if selected_species:
                    self._show_species_info(
                        selected_species["family"],
                        selected_species["subtype"],
                        selected_species["score"],
                        selected_species["evidence"],
                    )
                    return True

            info_entries = position_info_map.get(block_number, [])
            if info_entries:
                selected_entry = None
                for entry in sorted(info_entries, key=lambda item: item["icon_index"]):
                    if cursor_pos >= entry["icon_index"]:
                        selected_entry = entry
                if selected_entry:
                    if selected_entry.get("kind") == "nakshatra":
                        self._show_nakshatra_info(selected_entry["nakshatra"])
                        return True
                    if selected_entry.get("kind") == "hd_gate_line":
                        self._show_human_design_gate_line_info(
                            int(selected_entry.get("gate", 0)),
                            selected_entry.get("line"),
                        )
                        return True
                    if selected_entry.get("kind") == "hd_property":
                        self._show_human_design_property_info(str(selected_entry.get("property_key", "")))
                        return True
                    self._show_position_info(
                        selected_entry["body"],
                        selected_entry["sign"],
                        selected_entry["house"],
                    )
                    return True

            if cursor.positionInBlock() >= info_index:
                aspect_info = aspect_info_map.get(block_number)
                if aspect_info:
                    self._show_aspect_info(
                        aspect_info["p1"],
                        aspect_info["p2"],
                        aspect_info["type"],
                        aspect_info["angle"],
                        aspect_info["delta"],
                        sign1=aspect_info.get("sign1"),
                        sign2=aspect_info.get("sign2"),
                        house1=aspect_info.get("house1"),
                        house2=aspect_info.get("house2"),
                    )
                    return True
            return False
        finally:
            self.chart_info_output = original_chart_info_output

    def eventFilter(self, obj, event) -> bool:
        popout_context = self._popout_summary_contexts.get(obj)
        output_text = getattr(self, "output_text", None)
        chart_canvas = getattr(self, "chart_canvas", None)
        if popout_context is not None:
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                output_widget = popout_context["output_widget"]
                cursor = output_widget.cursorForPosition(event.position().toPoint())
                return self._handle_summary_info_click(
                    output_widget,
                    cursor,
                    popout_context["position_info_map"],
                    popout_context["aspect_info_map"],
                    popout_context["species_info_map"],
                    popout_context["chart_info_output"],
                    popout_context.get("summary_block_offset", 0),
                )
            return False
        if obj is self.output_text.viewport():
            if event.type() == QEvent.Resize:
                self._position_output_share_button()
        if output_text is not None and obj is output_text.viewport():
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                cursor = output_text.cursorForPosition(event.position().toPoint())
                return self._handle_summary_info_click(
                    output_text,
                    cursor,
                    self._position_info_map,
                    self._aspect_info_map,
                    self._species_info_map,
                    self.chart_info_output,
                )
        if obj in self._metric_scroll_widgets:
            if event.type() in (QEvent.Enter, QEvent.MouseButtonPress):
                if self.metrics_scroll is not None:
                    self.metrics_scroll.setFocus(Qt.MouseFocusReason)
            if event.type() == QEvent.Wheel:
                return self._handle_metrics_wheel(event)
            if event.type() == QEvent.KeyPress:
                return self._handle_metrics_keypress(event)
        if obj in self._metric_chart_titles:
            if (
                event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton
            ):
                self._show_metric_canvas_popout(obj, self._metric_chart_titles[obj])
                return True
        if chart_canvas is not None and obj is chart_canvas:
            if event.type() == QEvent.Enter:
                obj.setCursor(Qt.PointingHandCursor)
            if (
                event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton
            ):
                self.on_popout_chart()
                return True
        return super().eventFilter(obj, event)

    def _show_position_info(self, body: str, sign: str, house_num: int | None) -> None:
        sign_key = sign.lower()
        sign_keywords = SIGN_KEYWORDS.get(sign_key, {})
        adverbs = sign_keywords.get("best_adverbs", []) + sign_keywords.get(
            "worst_adverbs", []
        )
        planet_keywords = PLANET_KEYWORDS.get(body, {})
        verbs = planet_keywords.get("verbs", [])
        verbs_only = planet_keywords.get("verbsonly", [])
        planet_nouns = planet_keywords.get("nouns", [])
        if house_num is None:
            verb_choices = verbs_only or verbs
            if not (adverbs and verb_choices):
                self.chart_info_output.setPlainText(
                    f"No interpretation data available for {body} in {sign}."
                )
                return
        else:
            sign_verbs = sign_keywords.get("verbs", [])
            house_keywords = HOUSE_KEYWORDS.get(house_num, [])
            if not (adverbs and verbs and house_keywords and sign_verbs and planet_nouns):
                self.chart_info_output.setPlainText(
                    f"No interpretation data available for {body} in {sign}, house {house_num}."
                )
                return
        
        unique_lines: list[str] = []
        seen: set[tuple[str, str, str]] = set()
        
        def add_unique_lines(
            target_count: int,
            verb_options: list[str],
            noun_options: list[str],
            adverb_options: list[str],
            max_attempts: int = 200,
        ) -> None:
            attempts = 0
            while len(unique_lines) < target_count and attempts < max_attempts:
                noun = random.choice(noun_options)
                verb = random.choice(verb_options)
                adverb = random.choice(adverb_options)
                combo = (noun, verb, adverb)
                if combo in seen:
                    attempts += 1
                    continue
                seen.add(combo)
                unique_lines.append(f"• {verb} {noun} {adverb}")
                attempts += 1
        if house_num is None:
            verb_choices = verbs_only or verbs
            add_unique_lines(6, verb_choices, [""], adverbs)
            unique_lines = [line.replace("  ", " ").rstrip() for line in unique_lines]
            header = f"{body} in {sign}"
        else:
            house_of_keywords = [f"of {house}" for house in house_keywords]
            add_unique_lines(3, verbs, house_keywords, adverbs)
            add_unique_lines(6, sign_verbs, planet_nouns, house_of_keywords)
            header = f"{body} in {sign} • House {house_num}"
        self.chart_info_output.setPlainText("\n".join([header, ""] + unique_lines))

    def _show_nakshatra_info(self, nakshatra: str) -> None:
        formatted_text = _format_nakshatra_description_text(nakshatra)
        lines = formatted_text.splitlines()
        if len(lines) <= 1:
            self.chart_info_output.setPlainText(formatted_text)
            return

        title = lines[0]
        bullet_lines = [f"• {line}" for line in lines[1:] if line.strip()]
        self.chart_info_output.setPlainText("\n".join([title, "", *bullet_lines]))

    def _show_human_design_gate_line_info(self, gate: int, line: int | None) -> None:
        line_number = int(line) if isinstance(line, int) else None
        self.chart_info_output.setPlainText(format_gate_line_info(gate, line_number))

    def _show_human_design_property_info(self, property_key: str) -> None:
        info_map = {
            "type": (
                "Type\n\n"
                "• Mechanical category derived from center and channel definition.\n"
                "• Reflector: no defined centers.\n"
                "• Generator / Manifesting Generator: Sacral defined.\n"
                "• Manifestor: no Sacral, but motor connected to Throat.\n"
                "• Projector: no Sacral and no motor-to-Throat connection."
            ),
            "authority": (
                "Authority\n\n"
                "• Inner Authority is prioritized from center configuration.\n"
                "• Emotional > Sacral > Splenic > Ego variants > Self-Projected/Mental > Lunar."
            ),
            "profile": (
                "Profile\n\n"
                "• Profile is derived from Personality Sun line / Design Sun line.\n"
                "• Display format: PersonalityLine/DesignLine (for example, 1/3)."
            ),
        }
        self.chart_info_output.setPlainText(info_map.get(property_key, "No details available for this Human Design property."))

    def _show_species_info(
        self,
        family: str,
        subtype: str,
        score: float,
        evidence: list[str],
    ) -> None:
        header = f"{family} ({subtype}) • {score:.2f}"
        if evidence:
            lines = [f"• {line}" for line in evidence]
            self.chart_info_output.setPlainText("\n".join([header, "", "Evidence:"] + lines))
            return
        self.chart_info_output.setPlainText(
            "\n".join([header, "", "• Evidence is unavailable for this species assignment."])
        )

    def _show_aspect_info(
        self,
        p1: str,
        p2: str,
        atype: str,
        angle: float,
        delta: float,
        *,
        sign1: str | None = None,
        sign2: str | None = None,
        house1: int | None = None,
        house2: int | None = None,
    ) -> None:
        aspect_keywords = ASPECT_KEYWORDS.get(atype, [])
        p1_nouns = PLANET_KEYWORDS.get(p1, {}).get("nouns", [])
        p2_nouns = PLANET_KEYWORDS.get(p2, {}).get("nouns", [])
        if not (aspect_keywords and p1_nouns and p2_nouns):
            self.chart_info_output.setPlainText(
                f"No interpretation data available for {p1} {atype} {p2}."
            )
            return

        unique_lines = _build_aspect_interpretation_lines(
            p1_nouns=p1_nouns,
            p2_nouns=p2_nouns,
            aspect_keywords=aspect_keywords,
            sign1=sign1,
            sign2=sign2,
            house1=house1,
            house2=house2,
        )

        header = f"{p1} {atype} {p2} • {angle:.2f}° (orb {delta:+.2f}°)"
        bullet_lines = [f"• {line}" for line in unique_lines]
        self.chart_info_output.setPlainText("\n".join([header, ""] + bullet_lines))

    def _confirm_discard_or_save(self) -> bool:
        if not self._lucygoosey:
            return True

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Unsaved changes")
        dialog.setText(
            "You have unsaved changes. Save them before loading another chart?"
        )
        save_button = dialog.addButton("Save", QMessageBox.AcceptRole)
        discard_button = dialog.addButton("Discard", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() == save_button:
            self.on_update_chart(show_dialog=True)
        elif dialog.clickedButton() == discard_button:
            self._set_lucygoosey(False)
        return not self._lucygoosey

    def _should_auto_update_sentiments(self) -> bool:
        return self.current_chart_id is not None

    def _ensure_current_chart_still_exists(self) -> bool:
        chart_id = self.current_chart_id
        if chart_id is None:
            return False
        try:
            load_chart(chart_id)
        except ValueError:
            self._orphan_current_chart_reference()
            return False
        return True

    def _orphan_current_chart_reference(self) -> None:
        self.current_chart_id = None
        set_current_chart(None)
        self.update_button.setText("Save Chart")
        self._set_lucygoosey(False)

    def _autosave_checkbox_state(self) -> None:
        if self._suppress_lucygoosey or self.current_chart_id is None:
            return
        if not self._lucygoosey:
            return
        if not self._ensure_current_chart_still_exists():
            return
        self.on_update_chart(show_dialog=False, recalculate_chart=False)
        self._set_lucygoosey(False)

    def _on_sentiment_toggled(self, checked: bool) -> None:
        if self._suppress_lucygoosey:
            return
        self._set_lucygoosey(True)
        if self._should_auto_update_sentiments():
            self._metadata_autosave_timer.start(2000)

    def _on_relationship_type_toggled(self, checked: bool) -> None:
        if self._suppress_lucygoosey:
            return
        self._set_lucygoosey(True)
        if self._should_auto_update_sentiments():
            self._metadata_autosave_timer.start(2000)

    def _flush_pending_metadata_save(self) -> None:
        had_pending_metadata_save = self._metadata_autosave_timer.isActive()
        if had_pending_metadata_save:
            self._metadata_autosave_timer.stop()
        if not had_pending_metadata_save and not self._lucygoosey:
            return
        self._autosave_checkbox_state()

    def _open_chart_familiarity_calculator(self) -> None:
        selected_labels = list(getattr(self, "_chart_familiarity_factors", []))
        dialog = FamiliarityCalculatorDialog(selected_labels, self)

        def _apply_changes() -> None:
            familiarity_factors = dialog.selected_labels()
            familiarity_value = dialog.calculated_score()
            self._chart_familiarity_factors = familiarity_factors
            self.familiarity_spin.setValue(familiarity_value)
            self.familiarity_spin.setToolTip(
                ", ".join(familiarity_factors) if familiarity_factors else ""
            )

        dialog.accepted.connect(_apply_changes)
        dialog.exec()

    def _on_sentiment_metric_changed(self, _value: int) -> None:
        if self._suppress_lucygoosey:
            return
        self._set_lucygoosey(True)
        if not self._should_auto_update_sentiments():
            return
        self._sentiment_metrics_autosave_timer.start(2000)

    def _update_alignment_score_label(self, value: int) -> None:
        if getattr(self, "_alignment_score_assigned", False):
            self.alignment_score_label.setText(f"Alignment score: {int(value)}")
        else:
            self.alignment_score_label.setText("Alignment score: blank")

    def _on_alignment_changed(self, value: int) -> None:
        if not getattr(self, "_alignment_programmatic_update", False):
            self._alignment_score_assigned = True
        self._update_alignment_score_label(value)
        self._on_sentiment_metric_changed(value)

    def _set_alignment_score_state(self, value: int, *, assigned: bool) -> None:
        self._alignment_programmatic_update = True
        self._alignment_score_assigned = bool(assigned)
        self.alignment_slider.setValue(int(value))
        self._alignment_programmatic_update = False
        self._update_alignment_score_label(self.alignment_slider.value())

    def _flush_pending_sentiment_metrics_save(self) -> None:
        had_pending_metric_save = self._sentiment_metrics_autosave_timer.isActive()
        if had_pending_metric_save:
            self._sentiment_metrics_autosave_timer.stop()
        if not had_pending_metric_save and not self._lucygoosey:
            return
        if not self._should_auto_update_sentiments():
            return
        if not self._ensure_current_chart_still_exists():
            return
        self.on_update_chart(show_dialog=False, recalculate_chart=False)
        self._set_lucygoosey(False)

    def _clear_event_metadata_fields(self) -> None:
        # Event chart type intentionally removes sentiment/relationship metadata.
        self._set_sentiment_selection([])
        self._set_relationship_type_selection([])
        self.chart_tags_input.setText("")
        self.positive_sentiment_intensity_spin.setValue(1)
        self.negative_sentiment_intensity_spin.setValue(1)
        self.familiarity_spin.setValue(1)
        self._set_alignment_score_state(0, assigned=False)
        self.familiarity_spin.setToolTip("")
        self._chart_familiarity_factors = []
        self.year_first_encountered_edit.setText("")

    def _apply_chart_type_ui_state(self, chart_type: str | None) -> None:
        is_event_chart = chart_type == SOURCE_EVENT

        # Metadata group: sentiment + relationship panels.
        self.sentiment_relation_row_widget.setVisible(not is_event_chart)

        # Metadata group: sentiment intensity controls.
        self.sentiment_metrics_widget.setVisible(not is_event_chart)

    def _set_chart_type_selection(self, chart_type: str | None) -> None:
        chart_type_value = _normalize_gui_source(chart_type)
        chart_type_index = self.chart_source_combo.findData(chart_type_value)
        if chart_type_index < 0:
            chart_type_index = self.chart_source_combo.findData(SOURCE_PERSONAL)
        self.chart_source_combo.blockSignals(True)
        self.chart_source_combo.setCurrentIndex(max(0, chart_type_index))
        self.chart_source_combo.blockSignals(False)
        self._chart_type_previous_index = self.chart_source_combo.currentIndex()
        self._apply_chart_type_ui_state(self.chart_source_combo.currentData())

    def _on_chart_type_changed(self, index: int) -> None:
        if self._suppress_lucygoosey:
            self._chart_type_previous_index = index
            self._apply_chart_type_ui_state(self.chart_source_combo.currentData())
            return

        chart_type_value = self.chart_source_combo.itemData(index)
        previous_value = self.chart_source_combo.itemData(self._chart_type_previous_index)
        switched_to_event = chart_type_value == SOURCE_EVENT and previous_value != SOURCE_EVENT
        if switched_to_event:
            prompt = (
                "Changing Chart Type to ‘Event’ chart will erase all metadata. Accept? Y/N."
            )
            choice = QMessageBox.question(
                self,
                "Change Chart Type",
                prompt,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if choice == QMessageBox.No:
                self.chart_source_combo.blockSignals(True)
                self.chart_source_combo.setCurrentIndex(self._chart_type_previous_index)
                self.chart_source_combo.blockSignals(False)
                self._apply_chart_type_ui_state(previous_value)
                return
            self._clear_event_metadata_fields()

        self._chart_type_previous_index = index
        self._apply_chart_type_ui_state(chart_type_value)
        self._mark_lucygoosey()

    def _configure_main_splitter(self) -> None:
        base_left = 366
        base_middle = 750
        base_right = 316
        self._main_splitter.setSizes([base_left, base_middle, base_right])
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 2)
        self._main_splitter.setStretchFactor(2, 1)

    def _reset_interface_layout_to_defaults(self) -> None:
        self._settings.remove("main_window")
        self._settings.setValue("main_window/layout_customized", 0)
        self._window_layout_customized = False
        geometry = _available_screen_geometry()
        if geometry is not None:
            self.setGeometry(geometry)
        self.setWindowState(
            (self.windowState() & ~Qt.WindowFullScreen) | Qt.WindowMaximized
        )
        self._configure_main_splitter()

    def _set_chart_right_panel_container_visible(self, visible: bool) -> None:
        """Show/hide Chart View's entire right-hand panel container.

        This controls the whole right-side column (toggle buttons + panel stack),
        not just the Chart Analytics sub-panel.
        """
        panel = getattr(self, "metrics_panel", None)
        if panel is None:
            return
        panel.setVisible(visible)
        if visible:
            sizes = self._main_splitter.sizes()
            if len(sizes) >= 3 and sizes[2] == 0:
                self._configure_main_splitter()

    def _set_chart_analysis_panel_visible(self, visible: bool) -> None:
        """Backward-compatible alias for _set_chart_right_panel_container_visible."""
        self._set_chart_right_panel_container_visible(visible)

    def _set_chart_right_panel(self, panel_key: str) -> None:
        panel_stack = getattr(self, "chart_right_panel_stack", None)
        if panel_stack is None:
            return
        analytics_enabled = bool(
            getattr(self, "chart_analytics_panel_button", None)
            and self.chart_analytics_panel_button.isEnabled()
        )
        if panel_key == "analytics" and not analytics_enabled:
            panel_key = "subjective_notes"
        if panel_key == "subjective_notes":
            panel_stack.setCurrentWidget(self.subjective_notes_panel_scroll)
        else:
            panel_key = "analytics"
            panel_stack.setCurrentWidget(self.chart_analytics_panel_scroll)
        self._active_chart_right_panel = panel_key
        self.chart_analytics_panel_button.setChecked(panel_key == "analytics")
        self.subjective_notes_panel_button.setChecked(panel_key == "subjective_notes")
        if panel_key == "analytics" and self._latest_chart is not None:
            self._schedule_chart_render(self._latest_chart)

    def _sync_chart_right_panel_placeholder_state(self, chart: Chart | None) -> None:
        analytics_button = getattr(self, "chart_analytics_panel_button", None)
        if analytics_button is None:
            return
        is_placeholder = bool(chart is not None and getattr(chart, "is_placeholder", False))
        analytics_button.setEnabled(not is_placeholder)
        if is_placeholder:
            self._set_chart_right_panel("subjective_notes")

    def _restore_window_settings(self) -> None:
        splitter_key = "main_window/splitter_sizes"
        customized_key = "main_window/layout_customized"
        geometry_key = "main_window/geometry"
        maximized_key = "main_window/maximized"
        restored_customized = str(self._settings.value(customized_key, "0")).lower() in {
            "1",
            "true",
            "yes",
        }
        restored_maximized = str(self._settings.value(maximized_key, "1")).lower() in {
            "1",
            "true",
            "yes",
        }
        self._window_layout_customized = restored_customized
        default_geometry = _available_screen_geometry()
        restored_geometry = self._settings.value(geometry_key)
        self._restoring_window_layout = True

        if restored_customized and restored_geometry:
            self.restoreGeometry(restored_geometry)
        elif default_geometry is not None:
            self.setGeometry(default_geometry)

        base_state = (self.windowState() & ~Qt.WindowFullScreen) & ~Qt.WindowMinimized
        if restored_maximized:
            self.setWindowState(base_state | Qt.WindowMaximized)
        else:
            self.setWindowState(base_state & ~Qt.WindowMaximized)
            self.showNormal()

        sizes = self._settings.value(splitter_key)
        if restored_customized and sizes:
            self._main_splitter.setSizes([int(size) for size in sizes])
        else:
            self._main_splitter.setSizes([366, 750, 316])
        self._restoring_window_layout = False

    def _on_main_splitter_moved(self, *_args) -> None:
        if self._restoring_window_layout:
            return
        self._window_layout_customized = True

    def _raise_manage_charts_dialog(self) -> None:
        dialog = self._manage_charts_dialog
        if dialog is None:
            return
        dialog.raise_()
        dialog.activateWindow()
        dialog.setFocus(Qt.ActiveWindowFocusReason)

    def _show_chart_view_maximized(
        self,
        *,
        maximize: bool | None = None,
        source_window: QWidget | None = None,
    ) -> None:
        placement: WindowPlacement | None = None
        if source_window is not None:
            placement = capture_window_placement(source_window)
            if maximize is None:
                maximize = placement.maximized

        if maximize is None:
            maximize = True

        self.show()
        apply_window_placement(
            self,
            WindowPlacement(
                geometry=placement.geometry if placement is not None else None,
                maximized=maximize,
            ),
        )
        self.raise_()
        self.activateWindow()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.setWindowState(
                (self.windowState() & ~Qt.WindowFullScreen) | Qt.WindowMaximized
            )
            return
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111111;
            }
            QWidget {
                color: #f5f5f5;
                background-color: #111111;
                font-size: 13px;
            }
            QLineEdit, QDateEdit, QTimeEdit {
                background-color: #222222;
                border: 1px solid #444444;
                padding: 4px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPlainTextEdit {
                background-color: #181818;
                border: 1px solid #444444;
            }
        """)

    def _handle_database_health(self) -> None:
        ok, message = check_database_health()
        if ok:
            return
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Critical)
        dialog.setWindowTitle("Database error")
        dialog.setText(
            "The database appears to be corrupted or unreadable.\n"
            "You can restore a previous backup to continue."
        )
        if message:
            dialog.setDetailedText(message)
        restore_button = dialog.addButton(
            "Restore Backup", QMessageBox.ActionRole
        )
        continue_button = dialog.addButton(
            "Continue Anyway", QMessageBox.RejectRole
        )
        dialog.exec()
        if dialog.clickedButton() == restore_button:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Restore database",
                "",
                "Database Files (*.db)",
            )
            if not file_path:
                return
            try:
                restore_database(Path(file_path))
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Restore error",
                    f"Could not restore the database:\n{e}",
                )
                return
            QMessageBox.information(
                self,
                "Restore complete",
                "Database restored. You may continue.",
            )
        elif dialog.clickedButton() == continue_button:
            return

    def _clear_searched_birth_place(self) -> None:
        self._searched_birth_place = None
        self._searched_lat = None
        self._searched_lon = None

    def _on_place_text_changed(self, _text: str) -> None:
        self._clear_searched_birth_place()
        self._mark_lucygoosey()

    def on_search_place(self):
        """Search for location candidates and let the user pick one."""
        query = self.place_edit.text().strip()
        if not query:
            QMessageBox.information(
                self,
                "Search",
                "Type at least a city name before searching.",
            )
            return

        try:
            candidates = search_locations(query, limit=7)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Search error",
                f"Could not search locations:\n{e}",
            )
            return

        if not candidates:
            QMessageBox.information(
                self,
                "No matches",
                "No locations found. Try adding state/region/country.",
            )
            return

        labels = [c[0] for c in candidates]

        choice, ok = QInputDialog.getItem(
            self,
            "Select location",
            "Matches:",
            labels,
            0,
            False,  # editable = False
        )
        if ok and choice:
            selected_lat = None
            selected_lon = None
            for label, lat, lon in candidates:
                if label == choice:
                    selected_lat = float(lat)
                    selected_lon = float(lon)
                    break
            self.place_edit.setText(choice)
            if selected_lat is not None and selected_lon is not None:
                self._searched_birth_place = choice
                self._searched_lat = selected_lat
                self._searched_lon = selected_lon

    def _quit_app(self):
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def allow_close_for_app_exit(self) -> None:
        self._allow_app_exit_close = True

    def keyPressEvent(self, event):
        # Hitting Enter/Return updates the current chart, or generates a new one.
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            focus_widget = QApplication.focusWidget()
            callback_owner = focus_widget
            while callback_owner is not None:
                callback = getattr(callback_owner, "_batch_enter_apply_callback", None)
                if not callable(callback):
                    callback = getattr(callback_owner, "_enter_update_callback", None)
                if callable(callback):
                    callback()
                    return
                callback_owner = callback_owner.parentWidget()
            if isinstance(focus_widget, QAbstractButton):
                focus_widget.click()
                return
            if isinstance(focus_widget, (QTextEdit, QPlainTextEdit)):
                super().keyPressEvent(event)
                return
            if self.current_chart_id is not None:
                self.on_update_chart()
            else:
                self.on_generate()
        else:
            super().keyPressEvent(event)

    def _selected_sentiments(self) -> list[str]:
        return [
            name
            for name, checkbox in self.sentiment_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _selected_relationship_types(self) -> list[str]:
        return [
            name
            for name, checkbox in self.relationship_type_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _set_sentiment_selection(self, sentiments: list[str]) -> None:
        sentiment_set = set(sentiments or [])
        for name, checkbox in self.sentiment_checkboxes.items():
            checkbox.setChecked(name in sentiment_set)

    def _set_relationship_type_selection(self, relationship_types: list[str]) -> None:
        relationship_set = set(relationship_types or [])
        for name, checkbox in self.relationship_type_checkboxes.items():
            checkbox.setChecked(name in relationship_set)

    def _confirm_self_reassignment(self, current_chart_id: int | None) -> bool:
        existing_self = find_self_tagged_chart(exclude_chart_id=current_chart_id)
        if existing_self is None:
            return True

        _former_chart_id, former_chart_name = existing_self
        choice = QMessageBox.question(
            self,
            "There's only one you, baby. ('Self' relationship already assigned)",
            f"Remove 'self' from {former_chart_name}? y/n",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return False

        removed_ids = clear_self_tag_from_other_charts(
            current_chart_id if current_chart_id is not None else -1
        )
        for removed_id in removed_ids:
            self._chart_cache.pop(removed_id, None)
        return True

    def _resolve_location(self, place: str):
        if (
            self._searched_birth_place
            and place == self._searched_birth_place
            and self._searched_lat is not None
            and self._searched_lon is not None
        ):
            location_msg = (
                f"Using selected coordinates for {place} "
                f"({self._searched_lat:.4f}, {self._searched_lon:.4f})"
            )
            return self._searched_lat, self._searched_lon, location_msg, None, True
        if (
            self._loaded_birth_place
            and place == self._loaded_birth_place
            and self._loaded_lat is not None
            and self._loaded_lon is not None
        ):
            location_msg = (
                f"Using saved coordinates for {place} "
                f"({self._loaded_lat:.4f}, {self._loaded_lon:.4f})"
            )
            return self._loaded_lat, self._loaded_lon, location_msg, None, True
        return None, None, None, None, False


    def _on_placeholder_toggled(self, checked: bool) -> None:
        if checked:
            self._clear_required_field_highlights()
            if self.current_chart_id is not None and self.placeholder_chart_checkbox.hasFocus():
                revert_choice = QMessageBox.question(
                    self,
                    "Revert to placeholder chart?",
                    "Revert this saved chart to a placeholder chart?\n\n"
                    "Any existing partial birth date values will be preserved on save. "
                    "Chart drawing will be removed.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if revert_choice == QMessageBox.No:
                    blocker = QSignalBlocker(self.placeholder_chart_checkbox)
                    self.placeholder_chart_checkbox.setChecked(False)
                    del blocker
                    return
                # self.birth_month_edit.clear()
                # self.birth_day_edit.clear()
                # self.birth_year_edit.clear()

    def _clear_required_field_highlights(self) -> None:
        for widget in (
            self.birth_month_edit,
            self.birth_day_edit,
            self.birth_year_edit,
            self.place_edit,
        ):
            widget.setStyleSheet("")

    def _highlight_required_fields(self) -> None:
        self._clear_required_field_highlights()
        missing_widgets = []
        if not self.birth_month_edit.text().strip():
            missing_widgets.append(self.birth_month_edit)
        if not self.birth_day_edit.text().strip():
            missing_widgets.append(self.birth_day_edit)
        if not self.birth_year_edit.text().strip():
            missing_widgets.append(self.birth_year_edit)
        if not self.place_edit.text().strip():
            missing_widgets.append(self.place_edit)
        for widget in missing_widgets:
            widget.setStyleSheet("border: 1px solid #d26969;")

    def _build_placeholder_chart(self):
        month_text = self.birth_month_edit.text().strip()
        day_text = self.birth_day_edit.text().strip()
        year_text = self.birth_year_edit.text().strip()
        month = int(month_text) if month_text.isdigit() else None
        day = int(day_text) if day_text.isdigit() else None
        year = int(year_text) if year_text.isdigit() else None

        dt_year = year or 1990
        dt_month = month if month and 1 <= month <= 12 else 1
        dt_day = day if day and 1 <= day <= 31 else 1
        try:
            qdate = QDate(dt_year, dt_month, dt_day)
            if not qdate.isValid():
                qdate = QDate(1990, 1, 1)
            dt_year, dt_month, dt_day = qdate.year(), qdate.month(), qdate.day()
        except Exception:
            dt_year, dt_month, dt_day = 1990, 1, 1

        retcon_qtime = self.retcon_time_edit.time()
        qtime = retcon_qtime if self.retcon_time_checkbox.isChecked() else QTime(12, 0)
        dt_local = datetime.datetime(dt_year, dt_month, dt_day, qtime.hour(), qtime.minute())
        placeholder = SimpleNamespace()
        placeholder.name = self.name_edit.text().strip() or "Anonymous"
        placeholder.alias = self.alias_edit.text().strip() or None
        placeholder.gender = self.gender_combo.currentData() or None
        placeholder.dt = dt_local.replace(tzinfo=ZoneInfo("UTC"))
        placeholder.lat = 0.0
        placeholder.lon = 0.0
        placeholder.used_utc_fallback = False
        placeholder.birthtime_unknown = True
        placeholder.retcon_time_used = self.retcon_time_checkbox.isChecked()
        placeholder.retcon_hour = retcon_qtime.hour()
        placeholder.retcon_minute = retcon_qtime.minute()
        placeholder.birth_place = self.place_edit.text().strip() or ""
        placeholder.sentiments = list(self._selected_sentiments()) if hasattr(self, "_selected_sentiments") else []
        placeholder.relationship_types = list(self._selected_relationship_types()) if hasattr(self, "_selected_relationship_types") else []
        placeholder.tags = parse_tag_text(self.chart_tags_input.text())
        placeholder.comments = self.comments_edit.toPlainText().strip()
        placeholder.chart_data_source = self.source_edit.toPlainText().strip()
        placeholder.positive_sentiment_intensity = self.positive_sentiment_intensity_spin.value()
        placeholder.negative_sentiment_intensity = self.negative_sentiment_intensity_spin.value()
        placeholder.familiarity = self.familiarity_spin.value()
        placeholder.alignment_score = self.alignment_slider.value()
        placeholder.familiarity_factors = list(getattr(self, "_chart_familiarity_factors", []))
        placeholder.year_first_encountered = self._parse_year_first_encountered_text(self.year_first_encountered_edit.text())
        placeholder.age_when_first_met = 0
        placeholder.sentiment_confidence = placeholder.familiarity
        placeholder.chart_type = _normalize_gui_source(self.chart_source_combo.currentData())
        placeholder.source = placeholder.chart_type
        placeholder.dominant_sign_weights = {}
        placeholder.dominant_planet_weights = {}
        placeholder.is_placeholder = True
        placeholder.is_deceased = self.deceased_checkbox.isChecked()
        placeholder.birth_month = month
        placeholder.birth_day = day
        placeholder.birth_year = year
        placeholder.positions = {}
        placeholder.retrogrades = {}
        placeholder.houses = []
        placeholder.aspects = []
        placeholder.modal_distribution = {}
        return placeholder


    def _build_chart_from_inputs(self, show_feedback: bool = True):
        self._clear_required_field_highlights()
        name = self.name_edit.text().strip() or "Anonymous"
        alias = self.alias_edit.text().strip() or None
        gender = self.gender_combo.currentData() or None
        place = self.place_edit.text().strip() or "Chicago, IL, USA"

        qdate = self._birth_date_from_fields()
        if qdate is None:
            if show_feedback:
                QMessageBox.warning(
                    self,
                    "Invalid birth date",
                    f"Birth date must be a real calendar date in MM. DD. YYYY format, and the year must be between {NATAL_CHART_MIN_YEAR} and {NATAL_CHART_MAX_YEAR}.",
                )
            return
        if self.retcon_time_checkbox.isChecked():
            qtime = self.retcon_time_edit.time()
        elif self.time_unknown_checkbox.isChecked():
            qtime = QTime(12, 0)
        else:
            qtime = self.time_edit.time()
        dt_local = datetime.datetime(
            qdate.year(),
            qdate.month(),
            qdate.day(),
            qtime.hour(),
            qtime.minute(),
        )

        # Geocode
        (
            lat,
            lon,
            location_msg,
            tz_override,
            used_saved_coordinates,
        ) = self._resolve_location(place)
        if not used_saved_coordinates:
            try:
                lat, lon, label = geocode_location(place)
                tz_override = None  # let Chart infer timezone from lat/lon
                location_msg = f"Using: {label} ({lat:.4f}, {lon:.4f})"
                if label and label != place:
                    place = label
                    self.place_edit.setText(label)
            except LocationLookupError:
                if not show_feedback:
                    return
                # Ask user: default to UTC, or try again?
                choice = QMessageBox.question(
                    self,
                    "Location not found",
                    (
                        "Birth location could not be found.\n\n"
                        "Do you want to default to UTC at (0.0, 0.0)?\n"
                        "Click 'No' to edit the location and try again."
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )

                if choice == QMessageBox.No:
                    # Let them correct the field; do not generate a chart yet.
                    self.place_edit.setFocus()
                    self.place_edit.selectAll()
                    return

                # User accepted UTC fallback
                lat, lon = 0.0, 0.0
                tz_override = ZoneInfo("UTC")
                location_msg = (
                    "Birth location not found.\n"
                    "Defaulting to UTC at (0.0, 0.0)."
                )

        # Build chart
        try:
            chart = Chart(name, dt_local, lat, lon, tz=tz_override, alias=alias)
            chart.gender = gender
            print("DEBUG houses:", chart.houses)
            print("Asc ~", chart.houses[0])
            print("MC  ~", chart.houses[9])
        except Exception as e:
            if show_feedback:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not compute chart:\n{e}",
                )
            return  # only bail on error
        chart_type_value = _normalize_gui_source(self.chart_source_combo.currentData())
        is_event_chart = chart_type_value == SOURCE_EVENT
        if hasattr(chart, "sentiments"):
            if is_event_chart:
                chart.sentiments = []
            elif hasattr(self, "_selected_sentiments"):
                chart.sentiments = list(self._selected_sentiments())
            else:
                chart.sentiments = []
        if hasattr(chart, "relationship_types"):
            if is_event_chart:
                chart.relationship_types = []
            elif hasattr(self, "_selected_relationship_types"):
                chart.relationship_types = list(self._selected_relationship_types())
            else:
                chart.relationship_types = []
        if hasattr(chart, "comments"):
            chart.comments = self.comments_edit.toPlainText().strip()
        if hasattr(chart, "chart_data_source"):
            chart.chart_data_source = self.source_edit.toPlainText().strip()
        if hasattr(chart, "tags"):
            chart.tags = [] if is_event_chart else parse_tag_text(self.chart_tags_input.text())
        if hasattr(chart, "positive_sentiment_intensity"):
            chart.positive_sentiment_intensity = 1 if is_event_chart else self.positive_sentiment_intensity_spin.value()
        if hasattr(chart, "negative_sentiment_intensity"):
            chart.negative_sentiment_intensity = 1 if is_event_chart else self.negative_sentiment_intensity_spin.value()
        if hasattr(chart, "familiarity"):
            chart.familiarity = 1 if is_event_chart else self.familiarity_spin.value()
            chart.familiarity_factors = [] if is_event_chart else list(getattr(self, "_chart_familiarity_factors", []))
        if hasattr(chart, "alignment_score"):
            chart.alignment_score = (
                0
                if is_event_chart
                else (
                    self.alignment_slider.value()
                    if self._alignment_score_assigned
                    else None
                )
            )
        if hasattr(chart, "age_when_first_met"):
            chart.year_first_encountered = None if is_event_chart else self._parse_year_first_encountered_text(self.year_first_encountered_edit.text())
            chart.age_when_first_met = 0
        if hasattr(chart, "source"):
            chart.source = chart_type_value

        chart.birthtime_unknown = self.time_unknown_checkbox.isChecked()
        chart.retcon_time_used = self.retcon_time_checkbox.isChecked()
        chart.retcon_hour = self.retcon_time_edit.time().hour()
        chart.retcon_minute = self.retcon_time_edit.time().minute()
        chart.birth_place = place
        chart.birth_month = qdate.month()
        chart.birth_day = qdate.day()
        chart.birth_year = qdate.year()
        chart.is_placeholder = False
        chart.is_deceased = self.deceased_checkbox.isChecked()
        return chart, place, location_msg, tz_override

    def on_generate(self):
        chart_result = self._build_chart_from_inputs()
        if chart_result is None:
            return

        chart, place, location_msg, tz_override = chart_result

        # Persist to local DB
        self._loaded_birth_place = place
        self._loaded_lat = chart.lat
        self._loaded_lon = chart.lon

        # Update the text summary
        self._latest_chart = chart
        self._set_chart_right_panel_container_visible(True)
        self._schedule_chart_render(chart, sections={
            "summary",
            "signs",
            "planets",
            "houses",
            "elements",
            "nakshatra",
            "modal",
            "gender",
            "wheel",
        })

        # Inform about fallbacks
        extra_lines = [location_msg]
        if chart.used_utc_fallback and tz_override is None:
            extra_lines.append("Timezone inference failed; UTC was used.")
        extra_lines.append("Use Save Chart to store this chart.")

        QMessageBox.information(
            self,
            "Chart generated",
            "\n".join(extra_lines),
        )

    @staticmethod
    def _bind_enter_update(widget: QWidget, callback: Callable[[], None]) -> None:
        shortcut = QShortcut(QKeySequence("Return"), widget)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(callback)
        widget._enter_update_shortcut = shortcut

        shortcut2 = QShortcut(QKeySequence("Enter"), widget)
        shortcut2.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut2.activated.connect(callback)
        widget._enter_update_shortcut2 = shortcut2

        widget._enter_update_callback = callback

        if isinstance(widget, QLineEdit):
            widget.returnPressed.connect(callback)

        line_edit_getter = getattr(widget, "lineEdit", None)
        if callable(line_edit_getter):
            inner_line_edit = line_edit_getter()
            if isinstance(inner_line_edit, QLineEdit):
                inner_line_edit.returnPressed.connect(callback)

    @staticmethod
    def _parse_year_first_encountered_text(raw_value: str | None) -> int | None:
        value = (raw_value or "").strip()
        if value == "":
            return None
        if value.isdigit():
            return int(value)
        return None

    def _refresh_search_tags_list(self, known_tags: list[str]) -> None:
        if not hasattr(self, "search_tags_list_widget"):
            return
        selected_tags = {
            tag.casefold()
            for tag in parse_tag_text(
                self.search_tags_input.text() if hasattr(self, "search_tags_input") else ""
            )
        }
        self.search_tags_list_widget.clear()
        for tag in known_tags:
            label = f"✓ {tag}" if tag.casefold() in selected_tags else tag
            self.search_tags_list_widget.addItem(label)

    def _on_search_tag_item_clicked(self, item: QListWidgetItem) -> None:
        tag_value = item.text().lstrip("✓").strip()
        if not tag_value:
            return
        self.search_tags_input.setText(tag_value)

    def _update_tag_completers(self) -> None:
        sorted_tags = list_recognized_tags()
        self._known_chart_tags = sorted_tags
        if hasattr(self, "chart_tags_input"):
            apply_tag_completer(self.chart_tags_input, sorted_tags)
        if hasattr(self, "search_tags_input"):
            apply_tag_completer(self.search_tags_input, sorted_tags)
        if hasattr(self, "batch_tags_input"):
            apply_tag_completer(self.batch_tags_input, sorted_tags)
        refresh_search_tags_list = getattr(self, "_refresh_search_tags_list", None)
        if callable(refresh_search_tags_list):
            refresh_search_tags_list(sorted_tags)

    def _on_chart_tags_changed(self, *_: object) -> None:
        tags = parse_tag_text(self.chart_tags_input.text())
        render_tag_chip_preview(self.chart_tags_preview_label, tags)
        self._mark_lucygoosey()

    def _confirm_birth_day_duplicate_save(self, chart: Chart) -> bool:
        month = getattr(chart, "birth_month", None)
        day = getattr(chart, "birth_day", None)
        if month is None or day is None:
            dt = getattr(chart, "dt", None)
            month = getattr(dt, "month", None)
            day = getattr(dt, "day", None)
        if month is None or day is None:
            return True

        matches = find_chart_name_matches_by_birth_day(month, day)
        if not matches:
            return True

        preview_limit = 12
        preview_names = matches[:preview_limit]
        extra_count = max(0, len(matches) - len(preview_names))
        lines = [f"Found {len(matches)} chart(s) with this birthday ({int(month):02d}/{int(day):02d}):", ""]
        lines.extend(f"• {name}" for name in preview_names)
        if extra_count:
            lines.append(f"• ...and {extra_count} more")
        lines.extend(["", "Continue and save this chart anyway?"])

        choice = QMessageBox.question(
            self,
            "Possible duplicate birthdays",
            "\n".join(lines),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return choice == QMessageBox.Yes

    def on_update_chart(self, show_dialog: bool = True, recalculate_chart: bool = True):
        chart_id = self.current_chart_id
        is_placeholder = self.placeholder_chart_checkbox.isChecked()
        chart = None
        place = self.place_edit.text().strip()
        location_msg = "Saved as placeholder chart."
        tz_override = None

        if not recalculate_chart and chart_id is not None:
            try:
                chart = load_chart(chart_id)
            except ValueError:
                # Chart was deleted while editor remained open; continue in
                # "new chart" mode so autosave/update cannot target a stale id.
                chart_id = None
                self._orphan_current_chart_reference()
                chart = None
            except Exception:
                chart = None
            if chart is not None:
                chart_type_value = _normalize_gui_source(self.chart_source_combo.currentData())
                is_event_chart = chart_type_value == SOURCE_EVENT
                chart.sentiments = [] if is_event_chart else list(self._selected_sentiments())
                chart.relationship_types = [] if is_event_chart else list(self._selected_relationship_types())
                chart.tags = [] if is_event_chart else parse_tag_text(self.chart_tags_input.text())
                chart.comments = self.comments_edit.toPlainText().strip()
                chart.chart_data_source = self.source_edit.toPlainText().strip()
                chart.positive_sentiment_intensity = 1 if is_event_chart else self.positive_sentiment_intensity_spin.value()
                chart.negative_sentiment_intensity = 1 if is_event_chart else self.negative_sentiment_intensity_spin.value()
                chart.familiarity = 1 if is_event_chart else self.familiarity_spin.value()
                chart.alignment_score = (
                    0
                    if is_event_chart
                    else (
                        self.alignment_slider.value()
                        if self._alignment_score_assigned
                        else None
                    )
                )
                chart.familiarity_factors = [] if is_event_chart else list(getattr(self, "_chart_familiarity_factors", []))
                chart.year_first_encountered = None if is_event_chart else self._parse_year_first_encountered_text(self.year_first_encountered_edit.text())
                chart.age_when_first_met = 0
                chart.source = chart_type_value
                chart.gender = self.gender_combo.currentData() or None
                chart.birthtime_unknown = self.time_unknown_checkbox.isChecked()
                chart.retcon_time_used = self.retcon_time_checkbox.isChecked()
                chart.retcon_hour = self.retcon_time_edit.time().hour()
                chart.retcon_minute = self.retcon_time_edit.time().minute()
                chart.is_placeholder = self.placeholder_chart_checkbox.isChecked()
                chart.is_deceased = self.deceased_checkbox.isChecked()
                is_placeholder = chart.is_placeholder
                chart.birth_month = getattr(chart, "birth_month", None)
                chart.birth_day = getattr(chart, "birth_day", None)
                chart.birth_year = getattr(chart, "birth_year", None)
                if is_placeholder:
                    month_text = self.birth_month_edit.text().strip()
                    day_text = self.birth_day_edit.text().strip()
                    year_text = self.birth_year_edit.text().strip()
                    chart.birth_month = int(month_text) if month_text.isdigit() else None
                    chart.birth_day = int(day_text) if day_text.isdigit() else None
                    chart.birth_year = int(year_text) if year_text.isdigit() else None
                place = self.place_edit.text().strip() or chart.birth_place or place
                chart.birth_place = place
                location_msg = "Chart metadata saved."

        if chart is None and not is_placeholder:
            calculate_choice = QMessageBox.question(
                self,
                "Calculate chart?",
                "Calculate chart?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if calculate_choice == QMessageBox.No:
                self.placeholder_chart_checkbox.setChecked(True)
                is_placeholder = True
            else:
                self._clear_required_field_highlights()
                if (
                    not self.birth_month_edit.text().strip()
                    or not self.birth_day_edit.text().strip()
                    or not self.birth_year_edit.text().strip()
                    or not self.place_edit.text().strip()
                ):
                    self._highlight_required_fields()
                    self.placeholder_chart_checkbox.setChecked(True)
                    QMessageBox.warning(
                        self,
                        "Incomplete chart data",
                        "Missing required data for calculation. The chart was flagged as a placeholder.",
                    )
                    is_placeholder = True

        if chart is None and is_placeholder:
            chart = self._build_placeholder_chart()
            place = chart.birth_place
        elif chart is None:
            chart_result = self._build_chart_from_inputs()
            if chart_result is None:
                self._highlight_required_fields()
                self.placeholder_chart_checkbox.setChecked(True)
                return
            chart, place, location_msg, tz_override = chart_result
            chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
            chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
            chart.is_placeholder = False

        #chart, place, location_msg, tz_override = chart_result
        if chart_id is not None and recalculate_chart:
            try:
                load_chart(chart_id)
            except ValueError:
                chart_id = None
                self._orphan_current_chart_reference()

        is_new_chart = chart_id is None

        relationship_types = list(getattr(chart, "relationship_types", []) or [])
        if any(value.lower() == "self" for value in relationship_types):
            if not self._confirm_self_reassignment(chart_id):
                relationship_types = [
                    value for value in relationship_types if value.lower() != "self"
                ]
                chart.relationship_types = relationship_types
                self._set_relationship_type_selection(relationship_types)

        #chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
        #chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
        save_kwargs = dict(
            birth_place=place,
            retcon_time_used=getattr(chart, "retcon_time_used", False),
            retcon_hour=self.retcon_time_edit.time().hour(),
            retcon_minute=self.retcon_time_edit.time().minute(),
            is_placeholder=is_placeholder,
            is_deceased=getattr(chart, "is_deceased", False),
            birth_month=getattr(chart, "birth_month", None),
            birth_day=getattr(chart, "birth_day", None),
            birth_year=getattr(chart, "birth_year", None),
        )

        if is_new_chart:
            if not self._confirm_birth_day_duplicate_save(chart):
                return
            chart_id = save_chart(chart, **save_kwargs)
            set_current_chart(chart_id)
        else:
            update_chart(chart_id, chart, **save_kwargs)
            set_current_chart(chart_id)
            self._invalidate_chart_view_navigation_cache({chart_id})

        self.current_chart_id = chart_id
        self._cache_chart_view_navigation_entry(chart_id, chart)
        self._mark_chart_analytics_sections_dirty()
        self._manage_charts_pending_changed_ids.add(chart_id)
        self._refresh_manage_charts_in_background({chart_id})
        self._loaded_birth_place = place
        self._loaded_lat = chart.lat
        self._loaded_lon = chart.lon
        self._set_lucygoosey(False)
        if is_new_chart:
            self.update_button.setText("Update Chart")

        self._latest_chart = chart
        self._update_tag_completers()
        self._sync_chart_right_panel_placeholder_state(chart)
        if is_placeholder:
            self._set_chart_right_panel_container_visible(True)
            self._clear_chart_displays()
        else:
            self._set_chart_right_panel_container_visible(True)
            self._schedule_chart_render(chart, sections={
                "summary",
                "signs",
                "planets",
                "houses",
                "elements",
                "nakshatra",
                "modal",
                "gender",
                "similar_charts",
            })

        if show_dialog:
            if is_new_chart:
                extra_lines = [location_msg, f"Saved locally as chart #{chart_id}."]
                dialog_title = "Chart saved"
            else:
                extra_lines = [location_msg, f"Updated chart #{chart_id}."]
                dialog_title = "Chart updated"
            if not is_placeholder and chart.used_utc_fallback and tz_override is None:
                extra_lines.insert(1, "Timezone inference failed; UTC was used.")
            QMessageBox.information(self, dialog_title, "\n".join(extra_lines))

        if not is_placeholder:
            self._schedule_chart_render(chart, sections={"wheel"})

    def _reset_new_chart_form(self) -> None:
        self._chart_view_history.clear()
        self._chart_view_history_index = -1
        self.current_chart_id = None
        set_current_chart(None)
        self._loaded_birth_place = None
        self._loaded_lat = None
        self._loaded_lon = None
        self._latest_chart = None
        for button in (
            self.export_chart_button,
            self.current_transits_button,
            self.gemstone_chartwheel_button,
            self.interpret_astro_age_button,
            self.open_bazi_window_button,
        ):
            if button is not None:
                button.setEnabled(False)

        self._suppress_lucygoosey = True
        self.name_edit.clear()
        self.alias_edit.clear()
        self.gender_combo.setCurrentIndex(0)
        self.place_edit.clear()
        self.placeholder_chart_checkbox.setChecked(False)
        self._set_sentiment_selection([])
        self._set_relationship_type_selection([])
        self.chart_tags_input.clear()
        self.comments_edit.clear()
        self.source_edit.clear()
        self._set_birth_date_fields_from_qdate(QDate(1990, 1, 1))
        self.time_edit.setTime(QTime(12, 0))
        self.time_unknown_checkbox.setChecked(False)
        self.retcon_time_checkbox.setChecked(False)
        self.deceased_checkbox.setChecked(False)
        self.retcon_time_edit.setTime(QTime(12, 0))
        self._birth_time_user_overridden = False
        self._retcon_time_user_overridden = False
        self._update_time_input_text_colors()
        self.positive_sentiment_intensity_spin.setValue(1)
        self.negative_sentiment_intensity_spin.setValue(1)
        self.familiarity_spin.setValue(1)
        self._set_alignment_score_state(0, assigned=False)
        self.familiarity_spin.setToolTip("")
        self._chart_familiarity_factors = []
        self.year_first_encountered_edit.setText("")
        self._set_chart_type_selection(SOURCE_PERSONAL)
        self._suppress_lucygoosey = False
        self._set_lucygoosey(False)

        self.update_button.setText("Save Chart")
        self.output_text.clear()
        self._clear_chart_displays()
        self._set_chart_right_panel_container_visible(False)

    def _on_delete_this_chart(self) -> None:
        chart_id = self.current_chart_id
        if chart_id is None:
            QMessageBox.information(
                self,
                "Delete this chart",
                "No saved chart is currently open.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            "Delete this chart and return to Database View?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_charts([chart_id])
        except Exception as e:
            QMessageBox.critical(
                self,
                "Delete error",
                f"Could not delete chart #{chart_id}:\n{e}",
            )
            return

        self._on_charts_deleted({chart_id})
        self._manage_charts_pending_changed_ids.add(chart_id)
        manage_dialog = self._get_or_create_manage_charts_dialog()
        manage_dialog._refresh_charts(changed_ids={chart_id})
        self.on_manage_charts()


    def _start_swiss_ephemeris_prefetch(self) -> None:
        self._ephemeris_prefetch_controller.start()

    def _on_swiss_ephemeris_prefetch_error(self, message: str) -> None:
        print(f"Swiss Ephemeris prefetch failed: {message}")


    def on_new_chart(self) -> None:
        if not self._confirm_discard_or_save():
            return
        self._reset_new_chart_form()

    def open_chart_from_retcon_match(
        self,
        match: dict,
        place_label: str,
        lat: float | None,
        lon: float | None,
    ) -> None:
        if not self._confirm_discard_or_save():
            return

        self._reset_new_chart_form()
        match_dt = match.get("datetime")
        if not isinstance(match_dt, datetime.datetime):
            QMessageBox.warning(self, "Rectification Engine", "Selected match has invalid date/time.")
            return

        self._show_chart_view_maximized()

        self.place_edit.setText(place_label)
        if lat is not None and lon is not None:
            self._loaded_birth_place = place_label
            self._loaded_lat = lat
            self._loaded_lon = lon

        if not self.name_edit.text().strip():
            self.name_edit.setText(f"Rectified Candidate {match_dt.strftime('%Y-%m-%d %H:%M')}")

        self._set_birth_date_fields_from_qdate(QDate(match_dt.year, match_dt.month, match_dt.day))
        self.time_edit.setTime(QTime(match_dt.hour, match_dt.minute))
        self.retcon_time_edit.setTime(QTime(match_dt.hour, match_dt.minute))
        self.time_unknown_checkbox.setChecked(False)
        self.retcon_time_checkbox.setChecked(True)
        self._birth_time_user_overridden = True
        self._retcon_time_user_overridden = True
        self._update_time_input_text_colors()

        self.on_generate()

    def on_load_chart(self):
        """Let the user pick a saved chart from the DB and display it."""
        try:
            rows = list_charts()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load error",
                f"Could not load saved charts:\n{e}",
            )
            return

        if not rows:
            QMessageBox.information(
                self,
                "No charts",
                "No saved charts found yet.",
            )
            return

        # rows: List[Tuple[id, name, alias, datetime_iso, birth_place, created_at, used_utc_fallback, birthtime_unknown, retcon_time_used, familiarity, age_when_first_met, social_score, source, is_placeholder]]
        labels = []
        for (
            cid,
            name,
            _alias,
            _gender,
            dt_iso,
            birth_place,
            _created_at,
            _used_fallback,
            _birthtime_unknown,
            _retcon_time_used,
            _familiarity,
            _age_when_first_met,
            _year_first_encountered,
            _social_score,
            _source,
            is_placeholder,
            is_deceased,
            _birth_month,
            _birth_day,
            _birth_year,
        ) in rows:
            name = name or "Unnamed"
            dt_iso = dt_iso or "?"
            place = birth_place or ""
            labels.append(f"#{cid}  {name}  {dt_iso}  {place}")

        choice, ok = QInputDialog.getItem(
            self,
            "Load saved chart",
            "Select a chart:",
            labels,
            0,
            False,  # not editable
        )
        if not ok or not choice:
            return

        # Extract id from label "#12  ..."
        try:
            first_token = choice.split()[0]  # "#12"
            chart_id = int(first_token.lstrip("#"))
        except Exception:
            QMessageBox.warning(
                self,
                "Parse error",
                f"Could not parse chart id from selection:\n{choice}",
            )
            return
        self.load_chart_by_id(chart_id)

    def _cache_chart_view_navigation_entry(self, chart_id: int, chart: Chart | None) -> None:
        if chart is None:
            return
        normalized_chart_id = int(chart_id)
        self._chart_view_navigation_cache[normalized_chart_id] = chart
        self._chart_view_navigation_cache.move_to_end(normalized_chart_id)
        while len(self._chart_view_navigation_cache) > CHART_VIEW_NAV_CACHE_LIMIT:
            self._chart_view_navigation_cache.popitem(last=False)

    def _invalidate_chart_view_navigation_cache(
        self,
        chart_ids: set[int] | list[int] | tuple[int, ...] | None = None,
    ) -> None:
        if not chart_ids:
            self._chart_view_navigation_cache.clear()
            return
        for chart_id in chart_ids:
            self._chart_view_navigation_cache.pop(int(chart_id), None)

    def load_chart_by_id(self, chart_id: int, *, from_chart_link: bool = False) -> bool:
        if not self._confirm_discard_or_save():
            return False
        is_same_chart_request = self.current_chart_id == chart_id
        if not from_chart_link and not is_same_chart_request:
            self._chart_view_history.clear()
            self._chart_view_history_index = -1
        cached_chart = self._chart_view_navigation_cache.get(int(chart_id))
        use_fast_navigation_swap = (
            from_chart_link
            and not is_same_chart_request
            and cached_chart is not None
        )
        if not is_same_chart_request and not use_fast_navigation_swap:
            self._clear_chart_displays()
            self._sync_chart_right_panel_placeholder_state(None)
            self._show_chart_loading_overlay()
            QApplication.processEvents()
        if cached_chart is not None:
            chart = cached_chart
            self._chart_view_navigation_cache.move_to_end(int(chart_id))
        else:
            try:
                chart = load_chart(chart_id)
            except Exception as e:
                self._hide_chart_loading_overlay()
                QMessageBox.critical(
                    self,
                    "Load error",
                    f"Could not load chart #{chart_id}:\n{e}",
                )
                return False
            self._cache_chart_view_navigation_entry(chart_id, chart)

        set_current_chart(chart_id)
        self._pending_render_chart = None
        self._pending_render_sections.clear()
        self._pending_render_queue.clear()
        if self._render_flush_timer.isActive():
            self._render_flush_timer.stop()
        self.chart_info_output.clear()
        self._position_info_map = {}
        self._aspect_info_map = {}
        self._species_info_map = {}

        # Chart Edit Window: an "existing chart" is a saved DB entry with a chart_id.
        self.current_chart_id = chart_id

        # Update input fields from loaded chart
        self._suppress_lucygoosey = True
        self.name_edit.setText(chart.name or "")
        self.alias_edit.setText(getattr(chart, "alias", "") or "")
        gender_value = getattr(chart, "gender", None) or ""
        gender_index = self.gender_combo.findData(gender_value)
        self.gender_combo.setCurrentIndex(max(0, gender_index))
        self.place_edit.setText(chart.birth_place or "")
        placeholder_checked = bool(getattr(chart, "is_placeholder", False))
        placeholder_blocker = QSignalBlocker(self.placeholder_chart_checkbox)
        self.placeholder_chart_checkbox.setChecked(placeholder_checked)
        del placeholder_blocker
        self._set_sentiment_selection(getattr(chart, "sentiments", []))
        self._set_relationship_type_selection(
            getattr(chart, "relationship_types", []),
        )
        self.chart_tags_input.setText(
            ", ".join(normalize_tag_list(getattr(chart, "tags", [])))
        )
        self.comments_edit.setPlainText(getattr(chart, "comments", "") or "")
        self.source_edit.setPlainText(getattr(chart, "chart_data_source", "") or "")
        self.positive_sentiment_intensity_spin.setValue(
            getattr(chart, "positive_sentiment_intensity", 1) or 1
        )
        self.negative_sentiment_intensity_spin.setValue(
            getattr(chart, "negative_sentiment_intensity", 1) or 1
        )
        self.familiarity_spin.setValue(
            getattr(chart, "familiarity", 1) or 1
        )
        loaded_alignment = getattr(chart, "alignment_score", None)
        self._set_alignment_score_state(
            int(loaded_alignment or 0),
            assigned=isinstance(loaded_alignment, int),
        )
        self._chart_familiarity_factors = list(
            getattr(chart, "familiarity_factors", []) or []
        )
        self.familiarity_spin.setToolTip(
            ", ".join(self._chart_familiarity_factors) if self._chart_familiarity_factors else ""
        )
        self.year_first_encountered_edit.setText(
            "" if getattr(chart, "year_first_encountered", None) is None else str(getattr(chart, "year_first_encountered"))
        )
        source_value = _normalize_gui_source(getattr(chart, "source", SOURCE_PERSONAL) or SOURCE_PERSONAL)
        source_index = self.chart_source_combo.findData(source_value)
        if source_index < 0:
            source_index = self.chart_source_combo.findData(SOURCE_PERSONAL)
        self._set_chart_type_selection(self.chart_source_combo.itemData(max(0, source_index)))

        # dt is tz-aware; use stored partial date for placeholders when available.
        placeholder_month = getattr(chart, "birth_month", None)
        placeholder_day = getattr(chart, "birth_day", None)
        placeholder_year = getattr(chart, "birth_year", None)
        qdate = QDate(chart.dt.year, chart.dt.month, chart.dt.day)
        qtime = QTime(chart.dt.hour, chart.dt.minute)
        if getattr(chart, "is_placeholder", False):
            self.birth_month_edit.setText(f"{int(placeholder_month):02d}" if placeholder_month else "")
            self.birth_day_edit.setText(f"{int(placeholder_day):02d}" if placeholder_day else "")
            self.birth_year_edit.setText(f"{int(placeholder_year):04d}" if placeholder_year else "")
        else:
            self._set_birth_date_fields_from_qdate(qdate)
        qdate = QDate(chart.dt.year, chart.dt.month, chart.dt.day)
        qtime = QTime(chart.dt.hour, chart.dt.minute)
        default_noon = QTime(12, 0)
        self.time_edit.setTime(qtime)
        self.time_unknown_checkbox.setChecked(chart.birthtime_unknown)
        if chart.birthtime_unknown:
            self.time_edit.setTime(default_noon)
        self.retcon_time_checkbox.setChecked(chart.retcon_time_used)
        self.deceased_checkbox.setChecked(bool(getattr(chart, "is_deceased", False)))
        stored_retcon_hour = getattr(chart, "retcon_hour", None)
        stored_retcon_minute = getattr(chart, "retcon_minute", None)
        if stored_retcon_hour is not None and stored_retcon_minute is not None:
            self.retcon_time_edit.setTime(QTime(int(stored_retcon_hour), int(stored_retcon_minute)))
        elif chart.retcon_time_used:
            self.retcon_time_edit.setTime(qtime)
        else:
            self.retcon_time_edit.setTime(default_noon)
        self._birth_time_user_overridden = (
            not chart.birthtime_unknown and qtime != default_noon
        )
        self._retcon_time_user_overridden = self.retcon_time_edit.time() != default_noon
        self._update_time_input_text_colors()
        self._suppress_lucygoosey = False
        self._set_lucygoosey(False)
        self._loaded_birth_place = chart.birth_place
        self._loaded_lat = chart.lat
        self._loaded_lon = chart.lon
        self.update_button.setText("Update Chart")

        # Update the text summary
        self._latest_chart = chart
        self._cache_chart_view_navigation_entry(chart_id, chart)
        self._sync_chart_right_panel_placeholder_state(chart)
        if getattr(chart, "is_placeholder", False):
            self._set_chart_right_panel_container_visible(True)
            self._clear_chart_displays()
            self._hide_chart_loading_overlay()
        else:
            self._set_chart_right_panel_container_visible(True)
            self._schedule_chart_render(chart)
        return True

    def _on_chart_view_back_requested(self) -> None:
        if not self._chart_view_history:
            self.on_manage_charts()
            return
        if self._chart_view_history_index <= 0:
            self.on_manage_charts()
            return
        previous_index = self._chart_view_history_index - 1
        previous_chart_id = self._chart_view_history[previous_index]
        if self.load_chart_by_id(previous_chart_id, from_chart_link=True):
            self._chart_view_history_index = previous_index
            return
        self.on_manage_charts()

    def _get_or_create_manage_charts_dialog(self) -> ManageChartsDialog:
        if self._manage_charts_dialog is None:
            self._manage_charts_dialog = ManageChartsDialog(self)
            self._manage_charts_dialog.setWindowModality(Qt.NonModal)
        return self._manage_charts_dialog

    def _refresh_manage_charts_in_background(self, changed_ids: set[int]) -> None:
        if not changed_ids:
            return
        manage_dialog = self._manage_charts_dialog
        if manage_dialog is None:
            return
        if not manage_dialog.isVisible():
            return
        if not getattr(manage_dialog, "_chart_rows", None):
            return
        manage_dialog._refresh_charts(
            refresh_metrics=True,
            changed_ids=set(changed_ids),
        )
        self._manage_charts_pending_changed_ids.difference_update(changed_ids)

    def on_manage_charts(self):
        self._chart_view_history.clear()
        self._chart_view_history_index = -1
        self._flush_pending_sentiment_metrics_save()
        self._settings.setValue("app/last_view", "database")
        manage_dialog = self._get_or_create_manage_charts_dialog()
        manage_dialog.adopt_window_placement(self)
        opened = self._charts_controller.open_manage_charts()
        if not opened:
            return
        QTimer.singleShot(0, self._raise_manage_charts_dialog)
        self._retarget_size_checker_to_database_view()
        self.hide()

    def _on_close_requested(self) -> None:
        self.close()

    def _retarget_size_checker_to_main_view(self) -> None:
        if self._size_checker_popup is None or not self._size_checker_popup.isVisible():
            return
        self._size_checker_popup.set_target(
            parent_window=self,
            splitter=self._main_splitter,
            title="Size Checker • Natal Chart View",
        )

    def _retarget_size_checker_to_database_view(self) -> None:
        manage_dialog = self._manage_charts_dialog
        if (
            self._size_checker_popup is None
            or not self._size_checker_popup.isVisible()
            or manage_dialog is None
        ):
            return
        self._size_checker_popup.set_target(
            parent_window=manage_dialog,
            splitter=manage_dialog._content_splitter,
            title="Size Checker • Database View",
        )
        manage_dialog._size_checker_popup = self._size_checker_popup

    def _on_charts_deleted(self, chart_ids: set[int]) -> None:
        self._invalidate_chart_view_navigation_cache(chart_ids)
        if self.current_chart_id is None or self.current_chart_id not in chart_ids:
            return
        self._orphan_current_chart_reference()
        self._latest_chart = None
        for button in (
            self.export_chart_button,
            self.current_transits_button,
            self.gemstone_chartwheel_button,
            self.interpret_astro_age_button,
            self.open_bazi_window_button,
        ):
            if button is not None:
                button.setEnabled(False)

    def _create_retcon_dialog(self, parent: QWidget) -> RetconEngineDialog:
        dialog = RetconEngineDialog(parent)
        dialog.setWindowModality(Qt.NonModal)
        return dialog

    def on_retcon_engine(self) -> None:
        self._retcon_dialog_controller.show(self)

    def _on_unknown_time_toggled(self, checked: bool) -> None:
        if checked:
            self._birth_time_user_overridden = False
            self.time_edit.setTime(QTime(12, 0))
        self._update_time_input_text_colors()
        self._refresh_chart_preview()
        self._autosave_checkbox_state()

    def _toggle_chart_panel_content(
        self,
        toggle: QToolButton,
        content_widget: QWidget,
        expanded: bool,
    ) -> None:
        content_widget.setVisible(expanded)
        toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

    def _on_birth_date_field_changed(self, _value: str) -> None:
        # Avoid validating/computing on every keystroke in birth-date fields.
        # Date compliance is checked when the user saves/updates.
        return

    def _set_birth_date_fields_from_qdate(self, qdate: QDate) -> None:
        self.birth_month_edit.setText(f"{qdate.month():02d}")
        self.birth_day_edit.setText(f"{qdate.day():02d}")
        self.birth_year_edit.setText(f"{qdate.year():04d}")

    def _birth_date_from_fields(self) -> QDate | None:
        month_text = self.birth_month_edit.text().strip()
        day_text = self.birth_day_edit.text().strip()
        year_text = self.birth_year_edit.text().strip()
        if not month_text or not day_text or not year_text:
            return None

        try:
            month = int(month_text)
            day = int(day_text)
            year = int(year_text)
        except ValueError:
            return None

        if not (1 <= month <= 12):
            return None
        if not (NATAL_CHART_MIN_YEAR <= year <= NATAL_CHART_MAX_YEAR):
            return None

        max_day = calendar.monthrange(year, month)[1]
        if not (1 <= day <= max_day):
            return None

        qdate = QDate(year, month, day)
        if not qdate.isValid():
            return None

        min_birth_qdate = QDate(
            NATAL_CHART_MIN_DATE.year,
            NATAL_CHART_MIN_DATE.month,
            NATAL_CHART_MIN_DATE.day,
        )
        max_birth_qdate = QDate(
            NATAL_CHART_MAX_DATE.year,
            NATAL_CHART_MAX_DATE.month,
            NATAL_CHART_MAX_DATE.day,
        )
        if qdate < min_birth_qdate or qdate > max_birth_qdate:
            return None
        return qdate

    def _on_retcon_time_toggled(self, _checked: bool) -> None:
        self._update_time_input_text_colors()
        self._refresh_chart_preview()
        self._autosave_checkbox_state()

    def _on_birth_time_changed(self, _time: QTime) -> None:
        if (
            not self._suppress_lucygoosey
            and not self.time_unknown_checkbox.isChecked()
        ):
            self._birth_time_user_overridden = True
        self._update_time_input_text_colors()

    def _on_retcon_time_changed(self, _time: QTime) -> None:
        if not self._suppress_lucygoosey:
            self._retcon_time_user_overridden = True
        self._update_time_input_text_colors()

    def _update_time_input_text_colors(self) -> None:
        birth_time_color = (
            "#f5f5f5"
            if (
                not self.time_unknown_checkbox.isChecked()
                and self._birth_time_user_overridden
            )
            else "#8a8a8a"
        )
        retcon_time_color = (
            "#f5f5f5" if self._retcon_time_user_overridden else "#8a8a8a"
        )
        self.time_edit.setStyleSheet(f"color: {birth_time_color};")
        self.retcon_time_edit.setStyleSheet(f"color: {retcon_time_color};")

    def _refresh_chart_preview(self) -> None:
        if self._suppress_lucygoosey or self._latest_chart is None:
            return
        if self.placeholder_chart_checkbox.isChecked():
            return
        chart_result = self._build_chart_from_inputs(show_feedback=False)
        if chart_result is None:
            return
        chart, _place, _location_msg, _tz_override = chart_result
        chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)
        chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)
        self._schedule_chart_render(chart)

    def _clear_layout_widgets(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _show_chart_loading_overlay(self) -> None:
        # Temporarily disabled per UX request: Chart View loading overlay is not
        # reliable enough for production behavior.
        return

    def _hide_chart_loading_overlay(self, *, defer_ms: int = 0) -> None:
        # Keep as a no-op while overlay is disabled.
        return

    def _schedule_passive_chart_analysis_preload_if_current(self, chart: Chart) -> None:
        if self._latest_chart is not chart:
            return
        self._schedule_passive_chart_analysis_preload(chart)

    def _schedule_passive_chart_analysis_preload_if_current(self, chart: Chart) -> None:
        if self._latest_chart is not chart:
            return
        self._schedule_passive_chart_analysis_preload(chart)

    def _schedule_chart_render(
        self,
        chart: Chart,
        sections: set[str] | None = None,
        *,
        allow_collapsed_sections: bool = False,
        prioritize_sections: bool = False,
    ) -> None:
        self._latest_chart = chart
        if self._pending_render_chart is not None and self._pending_render_chart is not chart:
            self._pending_render_sections.clear()
            self._pending_render_queue.clear()
        self._pending_render_chart = chart
        if sections is None:
            sections = {
                "summary",
                "signs",
                "planets",
                "houses",
                "elements",
                "nakshatra",
                "modal",
                "gender",
                "planet_dynamics",
                "similar_charts",
                "wheel",
            }
            if self._is_chart_analysis_section_visible("anagrams"):
                sections.add("anagrams")
        sections = self._filter_chart_render_sections_for_visibility_and_cache(
            chart,
            sections,
            allow_collapsed_sections=allow_collapsed_sections,
        )
        if "planet_dynamics" in sections:
            chart.planet_dynamics_scores = _calculate_planet_dynamics_scores(chart)
        self._pending_render_sections.update(sections)
        render_order = (
            "summary",
            "signs",
            "planets",
            "houses",
            "elements",
            "nakshatra",
            "modal",
            "gender",
            "planet_dynamics",
            "wheel",
            "similar_charts",
            "anagrams",
        )
        queued = set(self._pending_render_queue)
        prioritized_queue: list[str] = []
        if prioritize_sections:
            for section_name in render_order:
                if section_name in sections and section_name in self._pending_render_queue:
                    self._pending_render_queue.remove(section_name)
                    prioritized_queue.append(section_name)
                    queued.discard(section_name)
        for section_name in render_order:
            if section_name in self._pending_render_sections and section_name not in queued:
                if prioritize_sections:
                    prioritized_queue.append(section_name)
                else:
                    self._pending_render_queue.append(section_name)
                queued.add(section_name)
        if prioritized_queue:
            self._pending_render_queue = prioritized_queue + self._pending_render_queue
        if not self._render_flush_timer.isActive():
            self._render_flush_timer.start(0)

    def _flush_scheduled_chart_render(self) -> None:
        chart = self._pending_render_chart
        if chart is None:
            self._pending_render_sections.clear()
            self._pending_render_queue.clear()
            self._hide_chart_loading_overlay()
            return

        section = self._pending_render_queue.pop(0) if self._pending_render_queue else None
        if section is None:
            if not self._pending_render_sections:
                self._pending_render_chart = None
                self._hide_chart_loading_overlay()
            return

        if section == "summary":
            self._refresh_chart_summary(chart)
        elif section == "signs":
            self._render_sign_tally(chart)
        elif section == "planets":
            self._render_planet_tally(chart)
        elif section == "houses":
            self._render_house_tally(chart)
        elif section == "elements":
            self._render_element_tally(chart)
        elif section == "nakshatra":
            self._render_nakshatra_wordcloud(chart)
        elif section == "modal":
            self._render_modal_distribution(chart)
        elif section == "gender":
            self._render_gender_guesser(chart)
        elif section == "planet_dynamics":
            self._render_planet_dynamics(chart)
        elif section == "wheel":
            self._render_chart(chart)
        elif section == "similar_charts":
            self._render_similar_charts(chart)
        elif section == "anagrams":
            self._render_anagrams(chart)
        self._pending_render_sections.discard(section)
        self._mark_chart_analytics_sections_clean({section}, chart)

        if self._pending_render_queue:
            self._render_flush_timer.start(0)
            return
        if self._pending_render_sections:
            self._render_flush_timer.start(0)
            return

        self._pending_render_chart = None
        # draw() is synchronous for chart/metric canvases, so overlay shutdown can
        # be tied to actual completion of the final render pass here.
        self._hide_chart_loading_overlay()
        QTimer.singleShot(
            0,
            lambda chart_snapshot=chart: self._schedule_passive_chart_analysis_preload_if_current(
                chart_snapshot
            ),
        )

    def _chart_analysis_render_key_for_section(self, section_key: str) -> str | None:
        return {
            "dominant_signs": "signs",
            "dominant_planets": "planets",
            "dominant_houses": "houses",
            "dominant_elements": "elements",
            "nakshatra_prevalence": "nakshatra",
            "modal_distribution": "modal",
            "gender_guesser": "gender",
            "planet_dynamics": "planet_dynamics",
            "similar_charts": "similar_charts",
            "anagrams": "anagrams",
        }.get(section_key)

    def _chart_analysis_section_key_for_render(self, render_key: str) -> str | None:
        return {
            "signs": "dominant_signs",
            "planets": "dominant_planets",
            "houses": "dominant_houses",
            "elements": "dominant_elements",
            "nakshatra": "nakshatra_prevalence",
            "modal": "modal_distribution",
            "gender": "gender_guesser",
            "planet_dynamics": "planet_dynamics",
            "similar_charts": "similar_charts",
            "anagrams": "anagrams",
        }.get(render_key)

    @staticmethod
    def _is_chart_analytics_render_key(render_key: str) -> bool:
        return render_key in {
            "signs",
            "planets",
            "houses",
            "elements",
            "nakshatra",
            "modal",
            "gender",
            "planet_dynamics",
            "similar_charts",
            "anagrams",
        }

    def _chart_analytics_cache_token(self, chart: Chart) -> str:
        chart_id = self.current_chart_id
        if chart_id is not None:
            return f"id:{int(chart_id)}"
        dt_value = getattr(chart, "dt", None)
        dt_token = dt_value.isoformat() if dt_value is not None else "nodt"
        return (
            f"draft:{getattr(chart, 'name', '')}|{dt_token}|"
            f"{getattr(chart, 'lat', 0.0):.6f}|{getattr(chart, 'lon', 0.0):.6f}"
        )

    def _mark_chart_analytics_sections_dirty(self, sections: set[str] | None = None) -> None:
        if sections is None:
            sections = {
                "signs",
                "planets",
                "houses",
                "elements",
                "nakshatra",
                "modal",
                "gender",
                "planet_dynamics",
                "similar_charts",
                "anagrams",
            }
        for section in sections:
            if self._is_chart_analytics_render_key(section):
                self._chart_analytics_dirty_sections.add(section)

    def _mark_chart_analytics_sections_clean(self, sections: set[str], chart: Chart) -> None:
        token = self._chart_analytics_cache_token(chart)
        for section in sections:
            if not self._is_chart_analytics_render_key(section):
                continue
            self._chart_analytics_dirty_sections.discard(section)
            self._chart_analytics_render_tokens[section] = token

    def _is_chart_analytics_section_renderable(
        self,
        render_key: str,
        *,
        allow_collapsed: bool = False,
    ) -> bool:
        section_key = self._chart_analysis_section_key_for_render(render_key)
        if section_key is None:
            return False
        if not self.metrics_panel.isVisible():
            return False
        if getattr(self, "_active_chart_right_panel", "analytics") != "analytics":
            return False
        if not allow_collapsed and not self._chart_analysis_section_expanded.get(section_key, True):
            return False
        if section_key in {"planet_dynamics", "anagrams"} and not self._is_chart_analysis_section_visible(section_key):
            return False
        return True

    def _filter_chart_render_sections_for_visibility_and_cache(
        self,
        chart: Chart,
        sections: set[str],
        *,
        allow_collapsed_sections: bool = False,
    ) -> set[str]:
        filtered: set[str] = set()
        token = self._chart_analytics_cache_token(chart)
        for section in sections:
            if not self._is_chart_analytics_render_key(section):
                filtered.add(section)
                continue
            if not self._is_chart_analytics_section_renderable(
                section,
                allow_collapsed=allow_collapsed_sections,
            ):
                continue
            if (
                section not in self._chart_analytics_dirty_sections
                and self._chart_analytics_render_tokens.get(section) == token
            ):
                continue
            filtered.add(section)
        return filtered

    def _schedule_passive_chart_analysis_preload(self, chart: Chart) -> None:
        if not self.metrics_panel.isVisible():
            return
        if getattr(self, "_active_chart_right_panel", "analytics") != "analytics":
            return
        passive_sections = {
            "signs",
            "planets",
            "houses",
            "elements",
            "nakshatra",
            "modal",
            "gender",
            "planet_dynamics",
            "similar_charts",
        }
        if self._is_chart_analysis_section_visible("anagrams"):
            passive_sections.add("anagrams")
        self._schedule_chart_render(
            chart,
            sections=passive_sections,
            allow_collapsed_sections=True,
        )

    def _render_metric_panel(
        self,
        *,
        canvas_attr: str,
        container_layout: QLayout,
        figsize: tuple[float, float],
        title: str,
        draw_fn: Callable[[Any, Chart], None],
        chart: Chart,
    ) -> None:
        canvas = getattr(self, canvas_attr)
        if canvas is None:
            figure = Figure(figsize=figsize)
            figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
            ax = figure.add_subplot(111)
            ax.set_facecolor(CHART_THEME_COLORS["background"])
            canvas = FigureCanvas(figure)
            self._apply_metric_chart_sizing(canvas)
            setattr(self, canvas_attr, canvas)
            self._register_metric_chart(canvas, title)
            self._clear_layout_widgets(container_layout)
            container_layout.addWidget(canvas)
        else:
            figure = canvas.figure
            ax = figure.gca()
            ax.clear()
            figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
            ax.set_facecolor(CHART_THEME_COLORS["background"])

        draw_fn(ax, chart)
        canvas.draw()

    def _render_chart(self, chart: Chart) -> None:
        self._latest_chart = chart
        for button in (
            self.export_chart_button,
            self.current_transits_button,
            self.gemstone_chartwheel_button,
            self.interpret_astro_age_button,
            self.open_bazi_window_button,
        ):
            if button is not None:
                button.setEnabled(True)

        if self.chart_canvas is None:
            figure = Figure(figsize=(5.5, 5.5))
            canvas = FigureCanvas(figure)
            canvas.installEventFilter(self)
            self._clear_layout_widgets(self.chart_canvas_container_layout)
            self.chart_canvas_container_layout.addWidget(canvas)
            self.chart_canvas = canvas
        else:
            canvas = self.chart_canvas
            figure = canvas.figure
            figure.clear()

        draw_chart_wheel(
            figure,
            chart,
            canvas=canvas,
            symbol_scale=0.7,
            wheel_scale=1.3,
        )
        canvas.draw()
        
        self.chart_canvas = canvas

    def _clear_chart_displays(self) -> None:
        for layout in (
            self.chart_canvas_container_layout,
            self.sign_chart_container_layout,
            self.planet_chart_container_layout,
            self.house_chart_container_layout,
            self.element_chart_container_layout,
            self.nakshatra_wordcloud_container_layout,
            self.modal_distribution_container_layout,
            self.gender_guesser_container_layout,
            self.planet_dynamics_container_layout,
        ):
            self._clear_layout_widgets(layout)
        self._pending_render_chart = None
        self._pending_render_sections.clear()
        self._pending_render_queue.clear()
        if self._render_flush_timer.isActive():
            self._render_flush_timer.stop()
        self.chart_info_output.clear()
        self._position_info_map = {}
        self._aspect_info_map = {}
        self._species_info_map = {}
        self.chart_canvas = None
        self.sign_chart_canvas = None
        self.planet_chart_canvas = None
        self.house_chart_canvas = None
        self.element_chart_canvas = None
        self.nakshatra_wordcloud_canvas = None
        self.modal_distribution_canvas = None
        self.gender_guesser_canvas = None
        self.planet_dynamics_canvas = None
        if self._similar_charts_list_label is not None:
            self._similar_charts_list_label.setText(
                "Generate or load a chart to search for matches."
            )
        self._similar_charts_export_rows = []
        self._similar_charts_subject_name = ""
        if self._similar_charts_export_button is not None:
            self._similar_charts_export_button.setEnabled(False)
        if self._anagrams_list_label is not None:
            source_label = ANAGRAM_SOURCE_LABELS.get(self._anagrams_selected_source, "Chart name")
            self._anagrams_list_label.setText(
                f"Generate or load a chart to scan {source_label.lower()} letters."
            )
        self._anagrams_current_words = []
        self._anagrams_clicked_definitions.clear()
        self._anagrams_current_chart_text = ""
        self._anagrams_current_subject_label = ANAGRAM_SOURCE_LABELS.get(
            self._anagrams_selected_source,
            "Chart name",
        )
        self._hide_chart_loading_overlay()

    def _render_sign_tally(self, chart: Chart) -> None:

        self._render_metric_panel(
            canvas_attr="sign_chart_canvas",
            container_layout=self.sign_chart_container_layout,
            figsize=(5.5, 3.2),
            title="Signs",
            draw_fn=self._draw_sign_tally,
            chart=chart,
        )

    def _render_planet_tally(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="planet_chart_canvas",
            container_layout=self.planet_chart_container_layout,
            figsize=(5.5, 3.2),
            title="Bodies",
            draw_fn=self._draw_planet_tally,
            chart=chart,
        )
        self._update_chart_ruler_footer(chart)

    def _chart_ruler_planets(self, chart: Chart) -> list[str]:
        if bool(getattr(chart, "birthtime_unknown", False)):
            return []
        asc_longitude = None
        positions = getattr(chart, "positions", None) or {}
        if "AS" in positions:
            asc_longitude = positions.get("AS")
        if asc_longitude is None:
            houses = getattr(chart, "houses", None)
            if houses and len(houses) >= 1:
                asc_longitude = houses[0]
        if asc_longitude is None:
            return []

        ascendant_sign = _sign_for_longitude(float(asc_longitude))
        rulers = [
            planet
            for planet, ruled_signs in PLANET_RULERSHIP.items()
            if ascendant_sign in ruled_signs
        ]
        return rulers

    def _update_chart_ruler_footer(self, chart: Chart | None) -> None:
        chart_ruler_label = self._chart_analysis_footer_labels.get("dominant_planets")
        if chart_ruler_label is None:
            return
        if chart is None:
            chart_ruler_label.setText("Chart Ruler: Unknown")
            return
        rulers = self._chart_ruler_planets(chart)
        if not rulers:
            chart_ruler_label.setText("Chart Ruler: Unknown")
            return
        chart_ruler_label.setText(f"Chart Ruler: {' & '.join(rulers)}")

    def _render_house_tally(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="house_chart_canvas",
            container_layout=self.house_chart_container_layout,
            figsize=(5.5, 3.2),
            title="Houses",
            draw_fn=self._draw_house_tally,
            chart=chart,
        )

    def _render_element_tally(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="element_chart_canvas",
            container_layout=self.element_chart_container_layout,
            figsize=(5.5, 3.2),
            title="Elements",
            draw_fn=self._draw_element_tally,
            chart=chart,
        )

    def _render_nakshatra_wordcloud(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="nakshatra_wordcloud_canvas",
            container_layout=self.nakshatra_wordcloud_container_layout,
            figsize=(5.5, 5.1),
            title="Nakshatra Prevalence",
            draw_fn=self._draw_nakshatra_wordcloud,
            chart=chart,
        )

    def _render_modal_distribution(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="modal_distribution_canvas",
            container_layout=self.modal_distribution_container_layout,
            figsize=(5.5, 3.2),
            title="Modes",
            draw_fn=self._draw_modal_distribution,
            chart=chart,
        )

    def _render_gender_guesser(self, chart: Chart) -> None:
        self._render_metric_panel(
            canvas_attr="gender_guesser_canvas",
            container_layout=self.gender_guesser_container_layout,
            figsize=(5.5, 2.8),
            title="Gender Guesser",
            draw_fn=self._draw_gender_guesser,
            chart=chart,
        )

    def _render_planet_dynamics(self, chart: Chart) -> None:
        dropdown = self._chart_analysis_chart_dropdowns.get("planet_dynamics")
        scores = getattr(chart, "planet_dynamics_scores", None) or _calculate_planet_dynamics_scores(chart)
        if dropdown is not None:
            current = dropdown.currentData()
            dropdown.blockSignals(True)
            dropdown.clear()
            for body in _dominant_planet_keys(chart):
                if body in scores:
                    dropdown.addItem(_display_body_name(body).upper(), body)
            if dropdown.count() > 0:
                current_index = dropdown.findData(current)
                dropdown.setCurrentIndex(current_index if current_index >= 0 else 0)
            dropdown.blockSignals(False)

        self._render_metric_panel(
            canvas_attr="planet_dynamics_canvas",
            container_layout=self.planet_dynamics_container_layout,
            figsize=(5.5, 3.4), #width & height of "Body Dynamics" graph
            title="Body Dynamics",
            draw_fn=self._draw_planet_dynamics,
            chart=chart,
        )

    def _normalize_aspect_type(self, raw_aspect: Any) -> str:
        return _normalize_aspect_type(raw_aspect)

    def _extract_aspect_weight(self, aspect_entry: Any) -> float:
        return _extract_aspect_weight(aspect_entry)

    def _collect_aspect_type_counts(
        self,
        aspect_entries: list[Any],
        *,
        weighted: bool = False,
        weighted_score_for_entry: Callable[[Any], float] | None = None,
    ) -> OrderedDict[str, float]:
        return _collect_aspect_type_counts(
            aspect_entries,
            weighted=weighted,
            weighted_score_for_entry=weighted_score_for_entry,
        )

    def _collect_aspect_category_totals(
        self,
        aspect_counts: OrderedDict[str, float],
        *,
        categories: dict[str, dict[str, Any]],
    ) -> OrderedDict[str, float]:
        return _collect_aspect_category_totals(aspect_counts, categories=categories)

    def _draw_popout_aspect_distribution_chart(
        self,
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

    def _build_popout_left_panel(
        self,
        layout: QHBoxLayout,
        *,
        chart_info_placeholder: str,
        aspect_entries: list[Any],
        export_file_stem: str,
        weighted_score_for_entry: Callable[[Any], float] | None = None,
        aspect_subheader: str | None = None,
        show_aspect_distribution: bool = True,
        awareness_stream_entries: list[dict[str, Any]] | None = None,
    ) -> QPlainTextEdit:
        return _build_popout_left_panel_widget(
            layout,
            chart_info_placeholder=chart_info_placeholder,
            aspect_entries=aspect_entries,
            export_file_stem=export_file_stem,
            weighted_score_for_entry=weighted_score_for_entry,
            aspect_subheader=aspect_subheader,
            parent=self,
            chart_summary_highlighter_cls=ChartSummaryHighlighter,
            export_aspect_distribution_csv_dialog=_export_aspect_distribution_csv_dialog,
            get_share_icon_path=_get_share_icon_path,
            chart_data_info_label_style=CHART_DATA_INFO_LABEL_STYLE,
            database_analytics_dropdown_style=DATABASE_ANALYTICS_DROPDOWN_STYLE,
            chart_theme_colors=CHART_THEME_COLORS,
            show_aspect_distribution=show_aspect_distribution,
            awareness_stream_entries=awareness_stream_entries,
        )

    def on_popout_chart(self) -> None:
        if self._latest_chart is None:
            QMessageBox.information(
                self,
                "No chart",
                "Generate or load a chart to pop it out.",
            )
            return
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle("Natal Chart View")
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)

        natal_planet_weights = getattr(self._latest_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(self._latest_chart)

        def _weighted_natal_score(entry: Any) -> float:
            if isinstance(entry, dict):
                return max(0.0, float(_aspect_score(entry, planet_weights=natal_planet_weights)))
            if hasattr(entry, "exactness") and hasattr(entry, "weight"):
                return max(0.0, float(entry.exactness) * float(entry.weight))
            return 0.0

        chart_info_output = self._build_popout_left_panel(
            layout,
            chart_info_placeholder="Click the ⓘ next to a position or aspect to see details/interpretation.",
            aspect_entries=list(getattr(self._latest_chart, "aspects", []) or []),
            export_file_stem=f"{_sanitize_export_token(self._latest_chart.name)}-natal_aspect_distribution",
            weighted_score_for_entry=_weighted_natal_score,
        )

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout, 3)

        date_label = self._latest_chart.dt.strftime("%m.%d.%Y") if self._latest_chart.dt else "??.??.????"
        time_label = (
            "unknown"
            if getattr(self._latest_chart, "birthtime_unknown", False)
            else self._latest_chart.dt.strftime("%H:%M")
        )
        birth_place = getattr(self._latest_chart, "birth_place", None) or "Unknown"
        popout_header_layout = QHBoxLayout()
        popout_header_layout.setContentsMargins(0, 0, 0, 0)
        popout_header_layout.setSpacing(12)

        popout_header_left = QLabel(
            "\n".join(
                [
                    f"Name:       {self._latest_chart.name}",
                    f"Birth date: {date_label}",
                    f"Birth time: {time_label}",
                    f"Birthplace: {birth_place}, {self._latest_chart.lat:.4f}, {self._latest_chart.lon:.4f}",
                ]
            )
        )
        popout_header_left.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        popout_header_left_font = popout_header_left.font()
        popout_header_left_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        popout_header_left.setFont(popout_header_left_font)
        popout_header_layout.addWidget(popout_header_left, 0, Qt.AlignLeft | Qt.AlignTop)
        popout_header_layout.addStretch(1)

        popout_export_button = QPushButton("Export Chart")
        popout_export_button.clicked.connect(self.on_export_chart)
        popout_header_layout.addWidget(popout_export_button, 0, Qt.AlignTop | Qt.AlignRight)

        right_layout.addLayout(popout_header_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        draw_chart_wheel(
            figure,
            self._latest_chart,
            canvas=canvas,
            wheel_padding=0.03,
            show_title=False,
            symbol_scale=0.7,
        )
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.draw_idle()
        right_layout.addWidget(canvas, 7)

        summary_controls = QHBoxLayout()
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        right_layout.addLayout(summary_controls)

        summary_output = QPlainTextEdit()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        summary_output._summary_highlighter = ChartSummaryHighlighter(summary_output.document())
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self)
        right_layout.addWidget(summary_output, 3)

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
        }
        self._popout_summary_contexts[popout_context_key] = popout_context
        dialog.destroyed.connect(
            lambda _=None, key=popout_context_key: self._popout_summary_contexts.pop(key, None)
        )

        def _refresh_summary() -> None:
            sort_mode = summary_sort_combo.currentText()
            chart_summary_text, position_info_map, aspect_info_map, species_info_map = format_chart_text(
                self._latest_chart,
                aspect_sort=sort_mode,
            )
            summary_lines_local = chart_summary_text.splitlines()
            positions_start_index = next(
                (idx for idx, line in enumerate(summary_lines_local) if line.strip() == "POSITIONS"),
                0,
            )
            visible_summary_lines = summary_lines_local[positions_start_index:]
            summary_output.setPlainText("\n".join(visible_summary_lines))
            popout_context["position_info_map"] = position_info_map
            popout_context["aspect_info_map"] = aspect_info_map
            popout_context["species_info_map"] = species_info_map
            popout_context["summary_block_offset"] = positions_start_index

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        _refresh_summary()

        dialog.resize(1320, 1080)
        self._register_popout_shortcuts(dialog)
        dialog.show()

    def on_get_human_design_info(self) -> None:
        if self._latest_chart is None:
            QMessageBox.information(
                self,
                "No chart",
                "Generate or load a chart to view Human Design info.",
            )
            return
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle("Human Design")
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)

        natal_planet_weights = getattr(self._latest_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(self._latest_chart)

        def _weighted_natal_score(entry: Any) -> float:
            if isinstance(entry, dict):
                return max(0.0, float(_aspect_score(entry, planet_weights=natal_planet_weights)))
            if hasattr(entry, "exactness") and hasattr(entry, "weight"):
                return max(0.0, float(entry.exactness) * float(entry.weight))
            return 0.0
        hd_result = build_human_design_result(self._latest_chart)
        awareness_stream_entries = build_awareness_stream_completion(set(hd_result.active_gates))

        chart_info_output = self._build_popout_left_panel(
            layout,
            chart_info_placeholder="Click the ⓘ next to a position to see details/interpretation.",
            aspect_entries=list(getattr(self._latest_chart, "aspects", []) or []),
            export_file_stem=f"{_sanitize_export_token(self._latest_chart.name)}-natal_aspect_distribution",
            weighted_score_for_entry=_weighted_natal_score,
            show_aspect_distribution=False,
            awareness_stream_entries=awareness_stream_entries,
        )

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout, 3)

        date_label = self._latest_chart.dt.strftime("%m.%d.%Y") if self._latest_chart.dt else "??.??.????"
        time_label = (
            "unknown"
            if getattr(self._latest_chart, "birthtime_unknown", False)
            else self._latest_chart.dt.strftime("%H:%M")
        )
        birth_place = getattr(self._latest_chart, "birth_place", None) or "Unknown"
        header_label = QLabel(
            "\n".join(
                [
                    "Human Design",
                    f"Name:       {self._latest_chart.name}",
                    f"Birth date: {date_label}",
                    f"Birth time: {time_label}",
                    f"Birthplace: {birth_place}, {self._latest_chart.lat:.4f}, {self._latest_chart.lon:.4f}",
                ]
            )
        )
        header_label.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        header_font = header_label.font()
        header_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        header_font.setBold(True)
        header_label.setFont(header_font)
        right_layout.addWidget(header_label, 0, Qt.AlignLeft | Qt.AlignTop)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        draw_human_design_chart(
            figure,
            hd_result,
            chart_theme_colors=CHART_THEME_COLORS,
        )
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.draw_idle()
        right_layout.addWidget(canvas, 7)

        summary_output = QPlainTextEdit()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        summary_output._summary_highlighter = ChartSummaryHighlighter(summary_output.document())
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self)
        right_layout.addWidget(summary_output, 3)

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
        }
        self._popout_summary_contexts[popout_context_key] = popout_context
        dialog.destroyed.connect(
            lambda _=None, key=popout_context_key: self._popout_summary_contexts.pop(key, None)
        )

        chart_data_text, position_info_map, aspect_info_map, species_info_map, summary_block_offset = build_human_design_chart_data_output(
            self._latest_chart,
            aspect_sort="Priority",
        )
        summary_output.setPlainText(chart_data_text)
        popout_context["position_info_map"] = position_info_map
        popout_context["aspect_info_map"] = aspect_info_map
        popout_context["species_info_map"] = species_info_map
        popout_context["summary_block_offset"] = summary_block_offset

        dialog.resize(1320, 1080)
        self._register_popout_shortcuts(dialog)
        dialog.show()

    def _resolve_current_transit_location(
        self,
        raw_location: str,
    ) -> tuple[float, float, str]:
        location_value = raw_location.strip()
        if not location_value:
            raise ValueError("Location is required.")

        if "," in location_value:
            maybe_lat, maybe_lon = location_value.split(",", 1)
            try:
                lat = float(maybe_lat.strip())
                lon = float(maybe_lon.strip())
            except ValueError:
                lat = None
                lon = None
            if lat is not None and lon is not None:
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    raise ValueError(
                        "Latitude must be between -90 and 90, and longitude between -180 and 180."
                    )
                return lat, lon, f"{lat:.4f}, {lon:.4f}"

        lat, lon, resolved_label = geocode_location(location_value)
        return float(lat), float(lon), resolved_label

    def _generate_current_transits_for_chart(
        self,
        chart: Chart | None,
        chart_id: int | None,
    ) -> None:
        if chart is None:
            QMessageBox.information(
                self,
                "No chart",
                "Generate or load a chart first.",
            )
            return

        default_location = self._settings.value("main_window/transit_last_location", "")
        if not isinstance(default_location, str):
            default_location = ""
        prompt_value = default_location.strip()
        while True:
            raw_location, accepted = QInputDialog.getText(
                self,
                "Get Current Transits",
                "Transit location (city or lat,lon):",
                text=prompt_value,
            )
            if not accepted:
                return
            prompt_value = raw_location.strip()
            try:
                transit_lat, transit_lon, location_label = self._resolve_current_transit_location(
                    raw_location
                )
                break
            except (LocationLookupError, ValueError) as exc:
                QMessageBox.warning(
                    self,
                    "Get Current Transits",
                    f"{exc}\n\nPlease try another location.",
                )

        self._settings.setValue("main_window/transit_last_location", raw_location.strip())

        transit_datetime_utc = datetime.datetime.now(datetime.timezone.utc)
        local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        timestamp_label = transit_datetime_utc.astimezone(local_tz).strftime("%Y-%m-%d %H:%M %Z")
        natal_chart = copy.deepcopy(chart)
        personal_transit_name = (
            f"Personal Transit Chart for {natal_chart.name} on {timestamp_label} @ {location_label}"
        )
        transit_chart = Chart(
            personal_transit_name,
            transit_datetime_utc,
            transit_lat,
            transit_lon,
            tz=datetime.timezone.utc,
        )
        transit_chart.birthtime_unknown = False
        transit_chart.retcon_time_used = False

        natal_kwargs: dict[str, Any] = {"chart_type": "natal"}
        if chart_id is not None:
            natal_kwargs["chart_id"] = chart_id
        natal_normalized = normalize_chart(natal_chart, **natal_kwargs)
        transit_normalized = normalize_chart(transit_chart, chart_type="transit")
        transit_in_natal = assign_houses(
            transit_normalized.bodies,
            natal_normalized.houses,
            layer="TRANSIT",
        )
        natal_targets = assign_houses(
            natal_normalized.bodies,
            natal_normalized.houses,
            layer="NATAL",
        )
        life_forecast_hits = compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
        )
        daily_vibe_hits = compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        )

        manage_dialog = self._get_or_create_manage_charts_dialog()
        manage_dialog._transit_location_label = location_label
        manage_dialog._show_personal_transit_chart_popout(
            natal_chart,
            transit_chart,
            transit_in_natal,
            {
                PERSONAL_TRANSIT_MODE_LIFE_FORECAST: life_forecast_hits,
                PERSONAL_TRANSIT_MODE_DAILY_VIBE: daily_vibe_hits,
            },
            include_time=True,
        )

    def on_get_current_transits(self) -> None:
        self._generate_current_transits_for_chart(self._latest_chart, self.current_chart_id)

    def on_get_synastry_chart(self) -> None:
        manage_dialog = self._get_or_create_manage_charts_dialog()
        chart_ids = manage_dialog._prompt_composite_chart_selection(
            default_first_chart_id=self.current_chart_id,
            focus_second_input=True,
        )
        if chart_ids is None:
            return
        manage_dialog._generate_composite_chart_for_ids(*chart_ids)

    def closeEvent(self, event) -> None:
        if not self._allow_app_exit_close:
            self.on_manage_charts()
            event.ignore()
            return

        self._flush_pending_sentiment_metrics_save()
        if not self._confirm_discard_or_save():
            event.ignore()
            return
        if self._size_checker_popup is not None:
            self._size_checker_popup.close()
            self._size_checker_popup = None
        if self._manage_charts_dialog is not None:
            self._manage_charts_dialog._size_checker_popup = None
        if self.isVisible():
            if not self.isMaximized() and not self.isFullScreen():
                self._window_layout_customized = True
            self._settings.setValue("main_window/maximized", int(self.isMaximized()))
            if self._window_layout_customized:
                self._settings.setValue("main_window/geometry", self.saveGeometry())
                self._settings.setValue("main_window/splitter_sizes", self._main_splitter.sizes())
                self._settings.setValue("main_window/layout_customized", 1)
            else:
                self._settings.remove("main_window/geometry")
                self._settings.remove("main_window/splitter_sizes")
                self._settings.setValue("main_window/layout_customized", 0)
            # Startup is intentionally Database View-first; persist that contract
            # so older installs carrying `app/last_view=chart` do not regress.
            self._settings.setValue("app/last_view", "database")
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_help_scrim"):
            self._help_resize_overlay()
        # if self._help_overlay_active:
        #     self._rebuild_help_markers()

    def _ensure_help_overlay_widgets(self) -> None:
        if hasattr(self, "_help_scrim"):
            return

        central = self.centralWidget()
        if central is None:
            return

        self._help_scrim = QWidget(central)
        self._help_scrim.hide()
        self._help_scrim.setStyleSheet("background-color: rgba(0, 0, 0, 26);")

        self._help_side_panel = QFrame(self._help_scrim)
        self._help_side_panel.setStyleSheet(
            "QFrame {"
            "background-color: #616161;"
            "border-right: 1px solid #f2c94c;"
            "}"
            "QLabel { color: #ffffff; }"
            "QLineEdit {"
            "background-color: #737373;"
            "border: 1px solid #f2c94c;"
            "color: #ffffff;"
            "padding: 6px;"
            "border-radius: 4px;"
            "}"
            "QListWidget {"
            "background-color: #6a6a6a;"
            "border: 1px solid #f2c94c;"
            "color: #ffffff;"
            "}"
        )
        panel_layout = QVBoxLayout(self._help_side_panel)
        panel_layout.setContentsMargins(14, 12, 14, 14)
        panel_layout.setSpacing(10)

        panel_title = QLabel("❓") #"Help"
        panel_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f2c94c;")
        panel_layout.addWidget(panel_title)

        panel_hint = QLabel("Search feature explanations and developer notes.")
        panel_hint.setWordWrap(True)
        panel_layout.addWidget(panel_hint)

        self._help_search_edit = QLineEdit()
        self._help_search_edit.setPlaceholderText("Search help notes…")
        self._help_search_edit.textChanged.connect(self._refresh_help_search_results)
        panel_layout.addWidget(self._help_search_edit)

        self._help_results_list = QListWidget()
        self._help_results_list.currentRowChanged.connect(self._show_selected_help_entry)
        panel_layout.addWidget(self._help_results_list, 1)

        self._help_entry_detail = QLabel()
        self._help_entry_detail.setWordWrap(True)
        self._help_entry_detail.setContentsMargins(10, 10, 10, 10)
        self._help_entry_detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._help_entry_detail.setStyleSheet(
            "background-color: #5a5a5a; border: 1px solid #f2c94c; border-radius: 4px; padding: 12px;"
        )
        self._help_entry_detail_scroll = QScrollArea()
        self._help_entry_detail_scroll.setWidgetResizable(True)
        self._help_entry_detail_scroll.setFrameShape(QScrollArea.NoFrame)
        self._help_entry_detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._help_entry_detail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._help_entry_detail_scroll.setMinimumHeight(240)
        self._help_entry_detail_scroll.setWidget(self._help_entry_detail)
        panel_layout.addWidget(self._help_entry_detail_scroll, 2)

        self._help_icon_button = QToolButton(self._help_side_panel)
        self._help_icon_button.setText("?")
        self._help_icon_button.setToolTip("Open the Help panel.")
        self._help_icon_button.clicked.connect(self._open_help_side_panel)
        self._help_icon_button.setStyleSheet(
            "QToolButton {"
            "background-color: #f2c94c;"
            "color: #14213d;"
            "border: 1px solid #14213d;"
            "border-radius: 10px;"
            "font-weight: 700;"
            "font-size: 16px;"
            "padding: 0px;"
            "}"
        )
        self._help_icon_button.setFixedSize(20, 20)

        self._help_icon_close = QPushButton("×", self._help_side_panel)
        self._help_icon_close.setToolTip("Close Help overlay")
        self._help_icon_close.clicked.connect(self._disable_help_overlay)
        self._help_icon_close.setFixedSize(18, 18)
        self._help_icon_close.setStyleSheet(
            "QPushButton {"
            "background-color: #9a9a9a;"
            "color: #2f2f2f;"
            "border: 1px solid #4f4f4f;"
            "border-radius: 9px;"
            "font-size: 16px;"
            "padding: 0px;"
            "}"
        )

        self._help_resize_overlay()
        self._refresh_help_search_results()

    def _help_resize_overlay(self) -> None:
        central = self.centralWidget()
        if central is None or not hasattr(self, "_help_scrim"):
            return
        self._help_scrim.setGeometry(0, 0, central.width(), central.height())
        self._help_side_panel.setGeometry(0, 0, 320, self._help_scrim.height())
        right_edge = self._help_side_panel.width() - 12
        self._help_icon_close.move(right_edge - self._help_icon_close.width(), 12)
        self._help_icon_button.move(
            self._help_icon_close.x() - 8 - self._help_icon_button.width(),
            12,
        )

    def _toggle_help_overlay(self) -> None:
        if self._help_overlay_active:
            self._disable_help_overlay()
        else:
            self._enable_help_overlay()

    def _enable_help_overlay(self) -> None:
        self._ensure_help_overlay_widgets()
        self._help_overlay_active = True
        self._help_scrim.show()
        self._help_scrim.raise_()
        self._help_side_panel.show()
        #self._rebuild_help_markers()

    def _disable_help_overlay(self) -> None:
        self._help_overlay_active = False
        self._clear_help_markers()
        if hasattr(self, "_help_scrim"):
            self._help_scrim.hide()

    def _open_help_side_panel(self) -> None:
        if not self._help_overlay_active:
            return
        self._help_side_panel.show()
        self._help_side_panel.raise_()
        self._help_search_edit.setFocus()

    def _clear_help_markers(self) -> None:
        for marker in self._help_marker_buttons:
            marker.deleteLater()
        self._help_marker_buttons.clear()

    def _rebuild_help_markers(self) -> None:
        if not self._help_overlay_active:
            return
        self._clear_help_markers()
        if not hasattr(self, "_help_scrim"):
            return

        for widget in self._iter_help_target_widgets():
            marker = QToolButton(self._help_scrim)
            marker.setText("?")
            marker.setFixedSize(14, 14)
            marker.setStyleSheet(
                "QToolButton {"
                "background-color: #f2c94c;"
                "color: #14213d;"
                "border: 1px solid #14213d;"
                "border-radius: 7px;"
                "font-size: 10px;"
                "font-weight: 700;"
                "padding: 0px;"
                "}"
            )
            widget_label = self._help_widget_label(widget)
            marker.setToolTip(help_notes.tooltip_for_widget(widget.objectName(), widget_label))
            top_right = widget.mapTo(self._help_scrim, QPoint(widget.width() - 2, 2))
            marker.move(top_right.x() - marker.width() // 2, top_right.y() - marker.height() // 2)
            marker.show()
            marker.raise_()
            self._help_marker_buttons.append(marker)

        self._help_side_panel.raise_()
        self._help_icon_button.raise_()
        self._help_icon_close.raise_()

    def _help_widget_label(self, widget: QWidget) -> str:
        if isinstance(widget, (QAbstractButton, QLabel)):
            return widget.text().strip()
        return ""

    def _iter_help_target_widgets(self) -> list[QAbstractButton | QLabel]:
        central = self.centralWidget()
        if central is None:
            return []

        targets: list[QAbstractButton | QLabel] = []
        button_targets = central.findChildren(QAbstractButton)
        label_targets = central.findChildren(QLabel)
        for widget in [*button_targets, *label_targets]:
            if widget in {
                getattr(self, "_help_icon_button", None),
                getattr(self, "_help_icon_close", None),
                self.help_overlay_button,
            }:
                continue
            if not widget.isVisible() or not widget.text().strip():
                continue
            if widget.width() < 24 or widget.height() < 10:
                continue
            targets.append(widget)
        return targets

    def _refresh_help_search_results(self) -> None:
        if not hasattr(self, "_help_results_list"):
            return
        self._help_results_list.clear()
        self._help_search_results_cache = tuple(
            help_notes.search_help_entries(self._help_search_edit.text())
        )
        for entry in self._help_search_results_cache:
            self._help_results_list.addItem(entry.title)
        if self._help_search_results_cache:
            self._help_results_list.setCurrentRow(0)
        else:
            self._help_entry_detail.setText("No help entries matched your search.")
            self._help_entry_detail_scroll.verticalScrollBar().setValue(0)

    def _show_selected_help_entry(self, row: int) -> None:
        if not hasattr(self, "_help_search_results_cache"):
            return
        if row < 0 or row >= len(self._help_search_results_cache):
            self._help_entry_detail.setText("Select an entry to view details.")
            self._help_entry_detail_scroll.verticalScrollBar().setValue(0)
            return
        entry = self._help_search_results_cache[row]
        keywords = ", ".join(entry.keywords)
        suffix = f"\n\nKeywords: {keywords}" if keywords else ""
        self._help_entry_detail.setText(f"{entry.description}{suffix}")
        self._help_entry_detail_scroll.verticalScrollBar().setValue(0)

def main(startup_loading: _StartupLoadingWidget | QWidget | None = None):
    _maybe_reexec_with_macos_app_name()
    _register_packaged_symbol_fonts()
    _configure_matplotlib_info_marker_font()

    app = _get_qapp()
    if startup_loading is None:
        startup_loading = _StartupLoadingWidget()
        startup_loading.show()
        startup_loading.raise_()
        startup_loading.activateWindow()
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    if _should_run_startup_dependency_check(settings):
        startup_loading.update_status("Checking required dependencies…", 15)
        try:
            ensure_all_deps(verbose=False)
        except Exception as exc:
            startup_loading.close()
            QMessageBox.critical(
                None,
                "Startup dependency error",
                (
                    "The app could not start because required Python dependencies "
                    "were unavailable and automatic installation failed.\n\n"
                    f"Details: {exc}"
                ),
            )
            raise SystemExit(1) from exc
        _mark_startup_dependency_check_complete(settings)
    else:
        startup_loading.update_status("Using cached dependency readiness…", 15)
    startup_loading.update_status("Loading main window…", 45)
    window = MainWindow()
    startup_loading.update_status("Applying startup settings…", 75)
    icon_path = _get_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
        window.setWindowIcon(QIcon(icon_path))

    # Always launch into Database View. Persisted "last_view" state previously
    # allowed cold-start entry into Chart View, which can present a blank chart
    # canvas while heavy initialization catches up (more pronounced on Windows).
    # Keeping launch deterministic avoids that startup race without changing
    # intended user-facing behavior (Database View first, Chart View on demand).
    window.on_manage_charts()
    window.hide()
    startup_loading.update_status("Startup complete.", 100)
    QTimer.singleShot(250, startup_loading.close)

    if not getattr(app, "_edd_running", False):
        app._edd_running = True
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
