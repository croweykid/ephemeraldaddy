from __future__ import annotations

import weakref
from pathlib import Path
from typing import Callable

import shiboken6
from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTabBar,
    QTabWidget,
    #QSizePolicy,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItemIterator,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ephemeraldaddy.gui.settings_widgets import SettingsHelpLabel
from ephemeraldaddy.gui.tooltips import (
    DATABASE_DISTINCTION_SCAN_TOOLTIP,
    PLACEMENT_WEIGHTING_MODE_TOOLTIPS,
    TooltipHelpLabel,
)
from ephemeraldaddy.gui.tag_categories import TAG_CATEGORY_OPTIONS, TAG_CATEGORY_PREFIXES
from ephemeraldaddy.gui.style import (
    apply_button_cursor,
    apply_shared_dropdown_style,
    CHART_DATA_INFO_LABEL_STYLE,
    CHART_DATA_HIGHLIGHT_COLOR,
    COLOR_ACCENT_SUCCESS,
    COLOR_BG_ELEVATED,
    INACTIVE_ACTION_BUTTON_STYLE,
    SETTINGS_TAB_STYLE,
    more_readable_color_scale_rgb_for_range,
)
from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    aggregate_similarity_algorithm_accuracy,
    format_similarity_algorithm_accuracy_ranking_html,
)
from ephemeraldaddy.gui.features.charts.similarity_custom_presets import (
    load_custom_astro_twin_presets,
    next_custom_astro_twin_preset_name,
    resolve_custom_astro_twin_presets_path,
    save_custom_astro_twin_preset,
    update_custom_astro_twin_preset,
)
from ephemeraldaddy.gui.features.predictions.ocean_settings import OCEAN_WEIGHT_ROWS
from ephemeraldaddy.gui.settings.percentage_weights import update_percentage_weight_constraints
from ephemeraldaddy.core.diagnostics import (
    DEFAULT_ERROR_REPORTING_MODE,
    ErrorReportingMode,
    normalize_error_reporting_mode,
)

SETTINGS_KEY_BATCH_TAGGING_TERMINAL_DEBUG = "dev_tools/batch_tagging_terminal_debug"
SETTINGS_KEY_ERROR_REPORTING_MODE = "dev_tools/error_reporting_mode"
BATCH_TAGGING_TERMINAL_DEBUG_DEFAULT = False
SETTINGS_KEY_ENNEAGRAM_PREDICTIONS_DEBUG = "dev_tools/enneagram_predictions_debug"
ENNEAGRAM_PREDICTIONS_DEBUG_DEFAULT = False
SETTINGS_KEY_PREDICTIONS_THREAD_DEBUG = "dev_tools/predictions_thread_debug"
PREDICTIONS_THREAD_DEBUG_DEFAULT = False
SETTINGS_KEY_DISTINGUISHING_FACTORS_SCORING_DEBUG = "dev_tools/distinguishing_factors_scoring_debug"
DISTINGUISHING_FACTORS_SCORING_DEBUG_DEFAULT = False
SETTINGS_KEY_SIMILARITY_PERCEIVED_ACCURACY_CONTROLS = "dev_tools/similarity_perceived_accuracy_controls"
SIMILARITY_PERCEIVED_ACCURACY_CONTROLS_DEFAULT = False
SETTINGS_KEY_DEMO_MODE = "dev_tools/demo_mode"
DEMO_MODE_DEFAULT = False
SETTINGS_KEY_PERFORMANCE_METRICS_LOGGING = "dev_tools/performance_metrics_logging"
PERFORMANCE_METRICS_LOGGING_DEFAULT = False
SETTINGS_KEY_PROPERTY_MANAGER_SPLITTER_SIZES = "property_manager/column_widths"
SETTINGS_KEY_PROPERTY_MANAGER_PRESET_COLUMN_SIZES = "property_manager/preset_column_widths"


class SimilarityAlgorithmAccuracyBrowser(QTextBrowser):
    """Collapsible algorithm ranking used by the Astro Twin Research settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded_rows: set[int] = set()
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("QTextBrowser { background: transparent; border: none; }")
        self.setMinimumHeight(100)
        self.anchorClicked.connect(self._toggle_algorithm_details)
        self.refresh_ranking()

    def refresh_ranking(self) -> None:
        rows = aggregate_similarity_algorithm_accuracy(include_v2=True)
        self._expanded_rows.intersection_update(range(len(rows)))
        self.setHtml(
            format_similarity_algorithm_accuracy_ranking_html(
                rows,
                expanded_rows=self._expanded_rows,
                highlight_color=CHART_DATA_HIGHLIGHT_COLOR,
            )
        )

    def _toggle_algorithm_details(self, url) -> None:
        if url.scheme() != "algorithm":
            return
        try:
            row_index = int(url.path())
        except ValueError:
            return
        if row_index in self._expanded_rows:
            self._expanded_rows.remove(row_index)
        else:
            self._expanded_rows.add(row_index)
        self.refresh_ranking()


def _build_settings_help_label(text: str) -> QLabel:
    return SettingsHelpLabel(text)


def load_error_reporting_mode(settings) -> ErrorReportingMode:
    return normalize_error_reporting_mode(
        settings.value(SETTINGS_KEY_ERROR_REPORTING_MODE, DEFAULT_ERROR_REPORTING_MODE.value)
    )


def add_error_reporting_mode_setting(
    *,
    section_layout: QVBoxLayout,
    mode: ErrorReportingMode | str,
    on_changed: Callable[[str], None],
) -> QComboBox:
    label = QLabel("Error reporting mode")
    combo = QComboBox()
    combo.addItem("Just make it work", ErrorReportingMode.QUIET.value)
    combo.addItem("Debug", ErrorReportingMode.DEBUG.value)
    normalized = normalize_error_reporting_mode(mode)
    combo.setCurrentIndex(max(0, combo.findData(normalized.value)))
    combo.setToolTip(
        "Both modes invalidate corrupt cached data and record unexpected failures to the local "
        "diagnostics log. Debug also prints structured errors and tracebacks to the Terminal."
    )
    combo.currentIndexChanged.connect(
        lambda _index: on_changed(str(combo.currentData() or ErrorReportingMode.QUIET.value))
    )
    section_layout.addWidget(label)
    section_layout.addWidget(combo)
    return combo

def load_demo_mode_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_DEMO_MODE, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_demo_mode_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("Private Mode: hide subjective/private notes") #formerly "demo mode"
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, hides Chart Editor Observations, Chart Info Notes, and subjective "
        "ratings in Search and Batch Editor so the app can be shown without private notes."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_batch_tagging_terminal_debug_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_BATCH_TAGGING_TERMINAL_DEBUG, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_batch_tagging_terminal_debug_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("Batch tagging: terminal debug logging")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, batch-tagging phase logs are emitted to the terminal to help debug post-update crashes."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_performance_metrics_logging_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_PERFORMANCE_METRICS_LOGGING, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_performance_metrics_logging_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("Enable Performance Metrics Logging")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, 'performance_metrics_log.txt' file will appear locally and in "
        "~/.ephemeraldaddy/ and track app performance for debugging."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_similarity_perceived_accuracy_controls_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_SIMILARITY_PERCEIVED_ACCURACY_CONTROLS, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_similarity_perceived_accuracy_controls_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("Astro Twin: show perceived-accuracy inputs")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, the Top/Bottom 25 Astro Twin popout shows temporary beta controls "
        "for logging perceived match accuracy to the Similarities Algorithm log."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_distinguishing_factors_scoring_debug_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_DISTINGUISHING_FACTORS_SCORING_DEBUG, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_distinguishing_factors_scoring_debug_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("debug Distinguishing Factors scoring")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, Chart Analytics > Most Distinguishing Astrological Factors shows raw weights, "
        "database means, z-scores, and share details. When disabled, it shows only the concise DB-average comparison."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_predictions_thread_debug_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_PREDICTIONS_THREAD_DEBUG, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_predictions_thread_debug_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("Predictions panel: terminal step debug logging")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, Chart Editor Predictions section steps, cache decisions, and background-thread lifecycle "
        "events are printed to the terminal."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


def load_enneagram_predictions_debug_enabled(settings, *, fallback: bool = False) -> bool:
    value = settings.value(SETTINGS_KEY_ENNEAGRAM_PREDICTIONS_DEBUG, int(fallback))
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(fallback)


def add_enneagram_predictions_debug_setting(
    *,
    section_layout: QVBoxLayout,
    is_enabled: bool,
    on_toggled: Callable[[bool], None],
) -> QCheckBox:
    checkbox = QCheckBox("debug Enneagram Predictions calculator")
    checkbox.setChecked(bool(is_enabled))
    checkbox.setToolTip(
        "When enabled, Enneagram popout Info shows a full criterion-by-criterion math breakdown."
    )
    checkbox.toggled.connect(on_toggled)
    section_layout.addWidget(checkbox)
    return checkbox


FILESYSTEM_INFOGRAPHIC_ITEMS: tuple[dict[str, object], ...] = (
    {
        "path": "ephemeraldaddy/",
        "plain": "The app itself. Think of this as the house where the application lives.",
        "dev": "Importable Python package root; code normally imports from ephemeraldaddy.*.",
        "children": (
            ("gui/", "Screens, windows, buttons, popups, and user-facing interactions.", "PySide6 GUI layer; app.py remains the shell while feature widgets should live in focused modules."),
            ("core/", "The astrology engine and shared rules: charts, aspects, houses, interpretations, databases, backups, photos, and time helpers.", "Domain logic used by GUI and analysis modules; keep calculations here when they are not view-specific."),
            ("analysis/", "Special calculators and reference libraries: Astro Twin matching, Human Design, BaZi, Enneagram, traits, cycles, Fantasy RPG analysis, and time sensitivity.", "Higher-level derived analytics; many files consume core chart data and cached metadata."),
            ("graphics/", "Drawing tools and visual assets, including chart wheels and emoji rendering support.", "Matplotlib/graphics helpers plus packaged image assets."),
            ("data/", "Reference datasets and generated population data the app reads from.", "Static/generated data inputs; compiled/ contains preprocessed artifacts."),
            ("io/", "Import, export, and place lookup plumbing.", "CSV/JSON/gazetteer/geocode boundaries."),
            ("ui/", "Command-line entry points for running the project outside the full desktop app.", "CLI package surface."),
            ("help/", "Help/reference materials shown or used by the app.", "User assistance content."),
        ),
    },
    {"path": "ephemeraldaddy/gui/app.py", "plain": "The main control room: it assembles the big windows, switches between Database View and Chart Editor, and wires buttons to features.", "dev": "Central legacy GUI orchestrator; new work should be pushed into smaller gui modules when practical."},
    {"path": "ephemeraldaddy/gui/dev_tools.py", "plain": "Developer tools and maintenance popups, including this file-system infographic.", "dev": "Settings > Developer Tools helpers and dialogs."},
    {"path": "ephemeraldaddy/gui/style.py", "plain": "The app-wide visual wardrobe: colors, spacing, button styling, and reusable look-and-feel helpers.", "dev": "Shared stylesheet constants and widget styling helpers."},
    {"path": "ephemeraldaddy/gui/dbv_search_panel.py", "plain": "The Database View search panel: helps users find and filter charts.", "dev": "Right-side DBV search UI and query controls."},
    {"path": "ephemeraldaddy/gui/features/", "plain": "Feature-specific panels and popout windows that keep app.py from becoming even larger.", "dev": "Nested feature modules, especially chart panels and analytics widgets."},
    {"path": "ephemeraldaddy/core/chart.py", "plain": "Builds the actual astrology chart data from birth information.", "dev": "Core chart calculation model and helpers."},
    {"path": "ephemeraldaddy/core/interpretations.py", "plain": "The encyclopedia of astrology meanings, labels, color coding, and descriptions.", "dev": "Primary interpretation/reference text source used throughout UI explanations."},
    {"path": "ephemeraldaddy/core/db.py", "plain": "The database doorway: saving, loading, and updating chart records.", "dev": "Persistence layer; prefer UID-based references for chart identity."},
    {"path": "ephemeraldaddy/analysis/get_astro_twin.py", "plain": "Finds similar charts and explains why two charts are alike or different.", "dev": "Similarity scoring settings, algorithms, caching, and relationship logging."},
    {"path": "ephemeraldaddy/analysis/human_design.py", "plain": "Calculates Human Design details from chart data.", "dev": "HD computation pipeline plus reference lookups."},
    {"path": "tests/", "plain": "Automated checks that protect important behavior from accidental breakage.", "dev": "Pytest suite; many tests are source-level guards for GUI wiring."},
    {"path": "docs/ and *.md notes", "plain": "Project notes, dev logs, summaries, and planning documents.", "dev": "Documentation outside the importable package."},
)


class FileSystemInfographicDialog(QDialog):
    """Animated, interactive dark-theme map of the repository for non-developers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ephemeral Daddy File-System Infographic")
        self.setModal(False)
        self.setMinimumSize(980, 680)
        self.resize(1180, 760)
        self._cards: list[QFrame] = []
        self._animations: list[QPropertyAnimation] = []
        self.setStyleSheet("""
            QDialog { background: #090b12; color: #f4f7ff; }
            QLabel { color: #f4f7ff; }
            QPushButton { background: #202a44; color: #f4f7ff; border: 1px solid #5268ff; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #2f3d64; border-color: #8ed8ff; }
            QTreeWidget, QTextBrowser { background: #101525; color: #edf4ff; border: 1px solid #26365f; border-radius: 12px; padding: 8px; }
            QTreeWidget::item:selected { background: #3146a8; color: #ffffff; }
            QLineEdit { background: #111827; color: #ffffff; border: 1px solid #3b4e83; border-radius: 8px; padding: 8px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self._title = QLabel("🗺️ Ephemeral Daddy: app file-system tour")
        self._title.setStyleSheet("font-size: 28px; font-weight: 800; color: #9ee8ff;")
        root.addWidget(self._title)
        subtitle = QLabel("Click a folder or file to see its plain-English job. Use the search box to highlight anything you are curious about. The pulsing cards below show how data flows through the app.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #c7d2fe; font-size: 13px;")
        root.addWidget(subtitle)

        body = QHBoxLayout()
        root.addLayout(body, 1)
        left = QVBoxLayout()
        body.addLayout(left, 2)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search folders, files, or concepts…")
        self._search.textChanged.connect(self._filter_tree)
        left.addWidget(self._search)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["File / folder", "Plain-English purpose"])
        self._tree.itemSelectionChanged.connect(self._show_selected_item)
        left.addWidget(self._tree, 1)

        right = QVBoxLayout()
        body.addLayout(right, 3)
        flow = QHBoxLayout()
        right.addLayout(flow)
        for label, caption in (
            ("Input", "birth data, notes, photos, tags"),
            ("Core", "chart math + shared rules"),
            ("Analysis", "meaning, matching, predictions"),
            ("GUI", "what the user sees and clicks"),
        ):
            card = QFrame()
            card.setStyleSheet("QFrame { background: #131a2e; border: 1px solid #334475; border-radius: 14px; padding: 10px; }")
            lay = QVBoxLayout(card)
            top = QLabel(label)
            top.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffd166;")
            bot = QLabel(caption)
            bot.setWordWrap(True)
            bot.setStyleSheet("color: #dbeafe;")
            lay.addWidget(top)
            lay.addWidget(bot)
            flow.addWidget(card)
            self._cards.append(card)
        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        right.addWidget(self._details, 1)

        buttons = QHBoxLayout()
        root.addLayout(buttons)
        expand = QPushButton("Expand all")
        collapse = QPushButton("Collapse all")
        expand.clicked.connect(self._tree.expandAll)
        collapse.clicked.connect(self._tree.collapseAll)
        buttons.addWidget(expand)
        buttons.addWidget(collapse)
        buttons.addStretch(1)

        self._populate_tree()
        self._start_animation()

    def _populate_tree(self) -> None:
        self._tree.clear()
        for entry in FILESYSTEM_INFOGRAPHIC_ITEMS:
            item = QTreeWidgetItem([str(entry["path"]), str(entry["plain"])])
            item.setData(0, Qt.UserRole, entry)
            self._tree.addTopLevelItem(item)
            for child in entry.get("children", ()):
                path, plain, dev = child
                child_item = QTreeWidgetItem([path, plain])
                child_item.setData(0, Qt.UserRole, {"path": path, "plain": plain, "dev": dev})
                item.addChild(child_item)
        self._tree.expandToDepth(0)
        self._tree.resizeColumnToContents(0)
        if self._tree.topLevelItemCount():
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def _show_selected_item(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole) or {}
        child_rows = "".join(
            f"<li><b>{path}</b>: {plain}<br><small>Dev footnote: {dev}</small></li>"
            for path, plain, dev in data.get("children", ())
        )
        if child_rows:
            child_rows = f"<h3>What lives inside</h3><ul>{child_rows}</ul>"
        self._details.setHtml(f"""
            <style>
              body {{ background: #101525; color: #edf4ff; font-family: Arial, sans-serif; line-height: 1.45; }}
              h2 {{ color: #9ee8ff; }} h3 {{ color: #ffd166; }} small {{ color: #b7c4e8; }}
              .note {{ border-left: 4px solid #8b5cf6; padding: 8px 12px; background: #151d33; border-radius: 8px; }}
              code {{ color: #a7f3d0; }}
            </style>
            <h2>{data.get('path', '')}</h2>
            <p class="note"><b>Plain English:</b> {data.get('plain', '')}</p>
            <p><b>Dev footnote:</b> <code>{data.get('dev', 'Top-level map node; expand it for implementation-specific notes.')}</code></p>
            {child_rows}
            <h3>How to read this map</h3>
            <p><b>Folders</b> are neighborhoods. <b>Files</b> are individual workbenches. The GUI asks for things, core calculates reliable chart facts, analysis turns those facts into higher-level insight, and data/io keep outside information organized.</p>
        """)

    def _filter_tree(self, text: str) -> None:
        needle = text.strip().lower()
        def visit(item: QTreeWidgetItem) -> bool:
            own = needle in " ".join(item.text(i).lower() for i in range(2))
            child_match = False
            for i in range(item.childCount()):
                child_match = visit(item.child(i)) or child_match
            item.setHidden(bool(needle) and not own and not child_match)
            if child_match:
                item.setExpanded(True)
            return own or child_match
        for row in range(self._tree.topLevelItemCount()):
            visit(self._tree.topLevelItem(row))

    def _start_animation(self) -> None:
        for index, card in enumerate(self._cards):
            animation = QPropertyAnimation(card, b"maximumHeight", self)
            animation.setStartValue(86)
            animation.setEndValue(116)
            animation.setDuration(1200 + index * 180)
            animation.setEasingCurve(QEasingCurve.InOutSine)
            animation.setLoopCount(-1)
            animation.start()
            self._animations.append(animation)


SIMILARITY_CALCULATOR_FACTOR_ROWS: tuple[tuple[str, str], ...] = (
    ("placement", "Placement by weight"),
    ("aspect", "Aspect score"),
    ("distribution", "Distribution score"),
    ("dominant_bodies", "Dominant Bodies"),
    ("dominant_houses", "Dominant Houses"),
    ("dominant_signs", "Dominant Signs"),
    ("dominant_nakshatras", "Dominant Nakshatras"),
    ("nakshatra_placement", "Nakshatra placement score"),
    ("nakshatra_dominance", "Nakshatra dominance score"),
    ("defined_centers", "Defined centers score"),
    ("human_design_gates", "Human Design gates score"),
    ("human_design_channels", "Human Design channels score"),
    ("inner_planet_placement", "Inner planet placement"),
    ("outer_planet_placement", "Outer planet placement"),
    ("big_3", "Big 3"),
)


SIMILARITY_CALCULATOR_CHECKBOX_STYLE = f"""
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #777777;
    border-radius: 3px;
    background-color: #202020;
}}
QCheckBox::indicator:hover {{
    border: 1px solid {CHART_DATA_HIGHLIGHT_COLOR};
}}
QCheckBox::indicator:checked {{
    background-color: {CHART_DATA_HIGHLIGHT_COLOR};
    border: 1px solid {CHART_DATA_HIGHLIGHT_COLOR};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16'><path d='M3.4 8.3 L6.5 11.4 L12.8 4.7' fill='none' stroke='%23111111' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}}
"""


SIMILARITY_CALCULATOR_CRITERION_EXPLAINERS: dict[str, str] = {
    "placement": (
        "Compares where each core body lands (sign, and house when houses are available) "
        "between the two charts, weighting each body by its selected chart/body weight."
    ),
    "aspect": (
        "Compares inter-body aspect patterns (planet pair + aspect type), and rewards close "
        "orb agreement while penalizing one-sided/extra-only aspect sets."
    ),
    "distribution": (
        "Compares elemental (fire/earth/air/water) and modality (cardinal/fixed/mutable) "
        "balance across core-body placements in both charts."
    ),
    "dominant_bodies": (
        "Compares body/planet dominance profiles between the two charts as its own separately weighted factor."
    ),
    "dominant_houses": (
        "Compares house dominance profiles between the two charts as its own separately weighted factor."
    ),
    "dominant_signs": (
        "Compares sign dominance profiles between the two charts as its own separately weighted factor."
    ),
    "dominant_nakshatras": (
        "Compares dominant nakshatra emphasis between the two charts as its own separately weighted factor."
    ),
    "nakshatra_placement": (
        "Compares the body-weighted nakshatra distribution profile (27 nakshatras) between charts; "
        "it measures profile-shape overlap, not strict body-to-body nakshatra matches."
    ),
    "nakshatra_dominance": (
        "Compares dominant nakshatra emphasis (weighted key nakshatras and top-nakshatra overlap) "
        "between the two charts."
    ),
    "defined_centers": (
        "Compares Human Design defined centers by set overlap (shared centers vs total unique centers)."
    ),
    "human_design_gates": (
        "Compares Human Design active gates by set overlap (shared gates vs total unique gates)."
    ),
    "human_design_channels": (
        "Compares Human Design defined channels by set overlap (shared channels vs total unique channels)."
    ),
    "inner_planet_placement": (
        "Compares Sun, Moon, Mercury, Venus, and Mars placements only, using the same weighted sign/house placement logic."
    ),
    "outer_planet_placement": (
        "Compares Jupiter, Saturn, Uranus, Neptune, and Pluto placements only, using the same weighted sign/house placement logic."
    ),
    "big_3": (
        "Compares the classic Big 3: Sun sign, Moon sign, and Rising sign when both charts have usable houses."
    ),
}

def build_similarity_calculator_settings_section(
    *,
    dialog: QDialog,
    section_layout: QVBoxLayout,
    subheader_style: str,
    on_mode_default_toggled: Callable[[bool], None],
    on_mode_generic_astro_toggled: Callable[[bool], None],
    on_mode_comprehensive_toggled: Callable[[bool], None],
    on_mode_all_or_nothing_toggled: Callable[[bool], None],
    on_mode_big_3_toggled: Callable[[bool], None],
    on_mode_custom_toggled: Callable[[bool], None],
    on_mode_database_distinction_toggled: Callable[[bool], None],
    on_checkbox_toggled: Callable[[str, bool], None],
    on_weight_changed: Callable[[str, float], None],
    on_placement_weighting_mode_changed: Callable[[str], None],
    on_all_or_nothing_criterion_changed: Callable[[str], None],
    on_demographic_match_mode_changed: Callable[[str], None],
    on_reset_weights_clicked: Callable[[], None],
    on_calibrate_clicked: Callable[[], None],
    on_save_thresholds_clicked: Callable[[], None],
    on_reset_thresholds_clicked: Callable[[], None],
    perceived_accuracy_controls_enabled: bool,
    on_perceived_accuracy_controls_toggled: Callable[[bool], None],
    on_show_high_similarity_clicked: Callable[[], None],
    on_manage_presets_clicked: Callable[[], None],
    threshold_rows: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    tabs = QTabWidget()
    tabs.setStyleSheet(SETTINGS_TAB_STYLE)
    algorithm_tab = QWidget()
    algorithm_layout = QVBoxLayout(algorithm_tab)
    algorithm_layout.setContentsMargins(8, 8, 8, 8)
    calibration_tab = QWidget()
    calibration_layout = QVBoxLayout(calibration_tab)
    calibration_layout.setContentsMargins(8, 8, 8, 8)
    research_tab = QWidget()
    research_layout = QVBoxLayout(research_tab)
    research_layout.setContentsMargins(8, 8, 8, 8)
    tabs.addTab(algorithm_tab, "Algorithm")
    tabs.addTab(calibration_tab, "Calibration")
    tabs.addTab(research_tab, "Research")
    tabs.setCurrentIndex(0)
    section_layout.addWidget(tabs)

    demographic_match_header = QLabel("Demographic Matching")
    demographic_match_header.setStyleSheet(subheader_style)
    algorithm_layout.addWidget(demographic_match_header)

    demographic_match_group = QButtonGroup(dialog)
    demographic_match_group.setExclusive(True)
    demographic_match_buttons: dict[str, QRadioButton] = {}
    for mode, label_text in (
        ("none", "Include everyone (default)"),
        ("sex", "Match assigned sex"),
        ("opposite_sex", "Opposite assigned sex"),
        ("gender", "Match gender identity"),
        ("opposite_gender", "Opposite gender identity"),
    ):
        button = QRadioButton(label_text)
        demographic_match_group.addButton(button)
        button.toggled.connect(
            lambda checked, selected_mode=mode: checked and on_demographic_match_mode_changed(selected_mode)
        )
        algorithm_layout.addWidget(button)
        demographic_match_buttons[mode] = button
    demographic_match_buttons["none"].setChecked(True)

    demographic_algorithm_divider = QFrame()
    demographic_algorithm_divider.setFrameShape(QFrame.HLine)
    demographic_algorithm_divider.setFrameShadow(QFrame.Sunken)
    algorithm_layout.addWidget(demographic_algorithm_divider)

    scoring_methods_header = QLabel("Scoring Methods")
    scoring_methods_header.setStyleSheet(subheader_style)
    algorithm_layout.addWidget(scoring_methods_header)
    algorithm_layout.addWidget(
        QLabel(
            "Choose the metric by which Astro Twins are defined:"
        )
    )

    default_radio = QRadioButton("use default")
    generic_astro_radio = QRadioButton("use generic astro")
    comprehensive_radio = QRadioButton("use comprehensive")
    all_or_nothing_radio = QRadioButton("use all or nothing")
    big_3_radio = QRadioButton("use Big 3")
    custom_radio = QRadioButton("use custom")
    database_distinction_radio = QRadioButton("use database distinction scan")
    database_distinction_radio.setToolTip(DATABASE_DISTINCTION_SCAN_TOOLTIP)
    scoring_method_selected_style = (
        f"QRadioButton:checked {{ color: {CHART_DATA_HIGHLIGHT_COLOR}; }}"
    )
    for scoring_method_radio in (
        default_radio,
        generic_astro_radio,
        comprehensive_radio,
        all_or_nothing_radio,
        big_3_radio,
        custom_radio,
        database_distinction_radio,
    ):
        scoring_method_radio.setStyleSheet(scoring_method_selected_style)
    similar_charts_algo_group = QButtonGroup(dialog)
    similar_charts_algo_group.setExclusive(True)
    similar_charts_algo_group.addButton(default_radio)
    similar_charts_algo_group.addButton(generic_astro_radio)
    similar_charts_algo_group.addButton(comprehensive_radio)
    similar_charts_algo_group.addButton(all_or_nothing_radio)
    similar_charts_algo_group.addButton(big_3_radio)
    similar_charts_algo_group.addButton(custom_radio)
    similar_charts_algo_group.addButton(database_distinction_radio)
    default_radio.toggled.connect(on_mode_default_toggled)
    generic_astro_radio.toggled.connect(on_mode_generic_astro_toggled)
    comprehensive_radio.toggled.connect(on_mode_comprehensive_toggled)
    all_or_nothing_radio.toggled.connect(on_mode_all_or_nothing_toggled)
    big_3_radio.toggled.connect(on_mode_big_3_toggled)
    custom_radio.toggled.connect(on_mode_custom_toggled)
    database_distinction_radio.toggled.connect(on_mode_database_distinction_toggled)
    algorithm_layout.addWidget(default_radio)
    algorithm_layout.addWidget(generic_astro_radio)
    algorithm_layout.addWidget(comprehensive_radio)
    algorithm_layout.addWidget(all_or_nothing_radio)

    all_or_nothing_fields_frame = QFrame()
    all_or_nothing_fields_frame.setFrameShape(QFrame.StyledPanel)
    all_or_nothing_fields_frame.setFrameShadow(QFrame.Plain)
    all_or_nothing_fields_frame.setStyleSheet(
        "QFrame { border: 1px solid rgba(128, 128, 128, 50); border-radius: 6px; }"
    )
    all_or_nothing_fields_layout = QVBoxLayout(all_or_nothing_fields_frame)
    all_or_nothing_fields_layout.setContentsMargins(20, 8, 8, 8)
    all_or_nothing_fields_layout.setSpacing(6)
    all_or_nothing_fields_frame.setVisible(False)
    all_or_nothing_radio.toggled.connect(all_or_nothing_fields_frame.setVisible)

    all_or_nothing_criterion_combo = QComboBox()
    all_or_nothing_criterion_combo.setToolTip(
        "Choose the one criterion that will exclusively rank charts when all-or-nothing mode is selected."
    )
    for key, label_text in SIMILARITY_CALCULATOR_FACTOR_ROWS:
        if key in {"defined_centers", "outer_planet_placement"}:
            continue
        all_or_nothing_criterion_combo.addItem(label_text, key)
    all_or_nothing_criterion_combo.currentIndexChanged.connect(
        lambda _index: on_all_or_nothing_criterion_changed(
            str(all_or_nothing_criterion_combo.currentData() or "inner_planet_placement")
        )
    )
    apply_shared_dropdown_style(all_or_nothing_criterion_combo)
    all_or_nothing_fields_layout.addWidget(all_or_nothing_criterion_combo)
    algorithm_layout.addWidget(all_or_nothing_fields_frame)
    algorithm_layout.addWidget(big_3_radio)
    algorithm_layout.addWidget(database_distinction_radio)
    algorithm_layout.addWidget(custom_radio)

    custom_fields_frame = QFrame()
    custom_fields_frame.setObjectName("customAstroTwinSubpanel")
    custom_fields_frame.setFrameShape(QFrame.StyledPanel)
    custom_fields_frame.setFrameShadow(QFrame.Plain)
    custom_fields_frame.setStyleSheet(
        "#customAstroTwinSubpanel {"
        f" background-color: {COLOR_BG_ELEVATED};"
        " border: 1px solid rgba(150, 150, 150, 85);"
        f" border-left: 3px solid {CHART_DATA_HIGHLIGHT_COLOR};"
        " border-radius: 6px;"
        " }"
    )
    custom_fields_layout = QVBoxLayout(custom_fields_frame)
    custom_fields_layout.setContentsMargins(20, 8, 8, 8)
    custom_fields_layout.setSpacing(8)
    custom_fields_frame.setVisible(False)
    custom_radio.toggled.connect(custom_fields_frame.setVisible)

    preset_status_label = QLabel()
    preset_status_label.setVisible(False)
    custom_fields_layout.addWidget(preset_status_label)
    preset_state: dict[str, object] = {
        "name": None,
        "preset_in_use": False,
        "applying": False,
    }

    calculator_checkboxes: dict[str, QCheckBox] = {}
    calculator_weights: dict[str, QDoubleSpinBox] = {}
    calculator_grid = QGridLayout()
    calculator_grid.setContentsMargins(0, 0, 0, 0)
    calculator_grid.setHorizontalSpacing(8)
    calculator_grid.setVerticalSpacing(6)
    criterion_header = QLabel("Criterion")
    weight_header = QLabel("Weight")
    total_header = QLabel("Total")
    for header in (criterion_header, weight_header, total_header):
        header.setAlignment(Qt.AlignCenter)
    calculator_grid.addWidget(criterion_header, 0, 1)
    calculator_grid.addWidget(weight_header, 0, 2)
    calculator_grid.addWidget(total_header, 0, 3)
    character_width = weight_header.fontMetrics().horizontalAdvance("0")
    weight_column_width = character_width * 8
    total_column_width = character_width * 12
    calculator_grid.setColumnStretch(1, 1)
    calculator_grid.setColumnMinimumWidth(2, weight_column_width)
    calculator_grid.setColumnMinimumWidth(3, total_column_width)
    total_weight_value_label = QLabel("0.00/1.00")
    total_weight_value_label.setFixedWidth(total_column_width)
    total_weight_value_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
    calculator_grid.addWidget(
        total_weight_value_label,
        1,
        3,
        len(SIMILARITY_CALCULATOR_FACTOR_ROWS),
        1,
        alignment=Qt.AlignRight | Qt.AlignTop,
    )
    for row_index, (key, label_text) in enumerate(SIMILARITY_CALCULATOR_FACTOR_ROWS, start=1):
        criterion_tooltip = SIMILARITY_CALCULATOR_CRITERION_EXPLAINERS.get(
            key,
            "Explains what this similarity criterion measures between two charts.",
        )
        criterion_label = TooltipHelpLabel(f"{label_text} Ⓘ", criterion_tooltip)
        calculator_grid.addWidget(criterion_label, row_index, 1)
        enabled_checkbox = QCheckBox()
        enabled_checkbox.setStyleSheet(SIMILARITY_CALCULATOR_CHECKBOX_STYLE)
        enabled_checkbox.setChecked(True)
        enabled_checkbox.stateChanged.connect(
            lambda _state, row_key=key, checkbox=enabled_checkbox: on_checkbox_toggled(
                row_key,
                checkbox.isChecked(),
            )
        )
        calculator_grid.addWidget(enabled_checkbox, row_index, 0, alignment=Qt.AlignCenter)
        weight_spinbox = QDoubleSpinBox()
        weight_spinbox.setDecimals(2)
        weight_spinbox.setRange(0.0, 1.0)
        weight_spinbox.setSingleStep(0.01)
        weight_spinbox.setFixedWidth(weight_column_width)
        weight_spinbox.setAlignment(Qt.AlignRight)
        weight_spinbox.valueChanged.connect(
            lambda _value, row_key=key, spinbox=weight_spinbox: on_weight_changed(
                row_key,
                float(spinbox.value()),
            )
        )
        calculator_grid.addWidget(weight_spinbox, row_index, 2)
        calculator_checkboxes[key] = enabled_checkbox
        calculator_weights[key] = weight_spinbox
    custom_fields_layout.addLayout(calculator_grid)

    weighting_mode_row = QHBoxLayout()
    weighting_mode_label = QLabel("Placement-weight mode")
    weighting_mode_combo = QComboBox()
    weighting_mode_combo.addItem("Chart-defined weights", "chart_defined")
    weighting_mode_combo.addItem("Generic base weights", "generic")
    weighting_mode_combo.addItem("Hybrid (generic + dominant body bonuses)", "hybrid")
    weighting_mode_combo.currentIndexChanged.connect(
        lambda _index: on_placement_weighting_mode_changed(
            str(weighting_mode_combo.currentData() or "chart_defined")
        )
    )
    apply_shared_dropdown_style(weighting_mode_combo)
    weighting_mode_row.addWidget(weighting_mode_label)
    weighting_mode_row.addWidget(weighting_mode_combo)
    reset_similarity_weights_button = QPushButton("Reset Weights to Default")
    reset_similarity_weights_button.clicked.connect(on_reset_weights_clicked)
    weighting_mode_row.addWidget(reset_similarity_weights_button)
    weighting_mode_row.addStretch(1)
    custom_fields_layout.addLayout(weighting_mode_row)

    def current_custom_settings() -> dict[str, object]:
        settings: dict[str, object] = {
            "placement_weighting_mode": str(weighting_mode_combo.currentData() or "chart_defined")
        }
        for key, checkbox in calculator_checkboxes.items():
            settings[f"use_{key}"] = checkbox.isChecked()
            settings[f"weight_{key}"] = float(calculator_weights[key].value())
        return settings

    def show_preset_status(*, modified: bool = False) -> None:
        preset_name = str(preset_state.get("name") or "")
        if not preset_name:
            preset_status_label.setVisible(False)
            return
        suffix = " (modified*)" if modified else ""
        preset_status_label.setText(f"'{preset_name}' in use{suffix}")
        font_style = "font-style: italic;" if modified else ""
        preset_status_label.setStyleSheet(f"color: {COLOR_ACCENT_SUCCESS}; {font_style}")
        preset_status_label.setVisible(True)

    def mark_loaded_preset_modified(*_args) -> None:
        if bool(preset_state["applying"]) or not bool(preset_state["preset_in_use"]):
            return
        preset_state["preset_in_use"] = False
        show_preset_status(modified=True)

    for checkbox in calculator_checkboxes.values():
        checkbox.toggled.connect(mark_loaded_preset_modified)
    for spinbox in calculator_weights.values():
        spinbox.valueChanged.connect(mark_loaded_preset_modified)
    weighting_mode_combo.currentIndexChanged.connect(mark_loaded_preset_modified)

    save_custom_preset_button = QPushButton("Save as Preset")
    save_custom_preset_button.setToolTip("save current weights as preset")
    select_preset_label = QLabel("Select Preset")
    select_preset_combo = QComboBox()
    apply_shared_dropdown_style(select_preset_combo)
    manage_presets_button = QPushButton("Manage Presets")
    manage_presets_button.clicked.connect(on_manage_presets_clicked)

    def refresh_preset_dropdown() -> None:
        preset_state["applying"] = True
        select_preset_combo.clear()
        for preset in load_custom_astro_twin_presets():
            select_preset_combo.addItem(str(preset["name"]), dict(preset["settings"]))
        select_preset_combo.setCurrentIndex(-1)
        preset_state["applying"] = False
        is_local_file_available = resolve_custom_astro_twin_presets_path().is_file()
        select_preset_label.setVisible(is_local_file_available)
        select_preset_combo.setVisible(is_local_file_available)
        manage_presets_button.setVisible(is_local_file_available)

    def apply_selected_preset(index: int) -> None:
        if index < 0 or bool(preset_state["applying"]):
            return
        settings = select_preset_combo.itemData(index)
        if not isinstance(settings, dict):
            return
        preset_state["applying"] = True
        for key, checkbox in calculator_checkboxes.items():
            enabled_key = f"use_{key}"
            weight_key = f"weight_{key}"
            if enabled_key in settings:
                checkbox.setChecked(bool(settings[enabled_key]))
            if weight_key in settings:
                calculator_weights[key].setValue(float(settings[weight_key]))
        placement_index = weighting_mode_combo.findData(settings.get("placement_weighting_mode"))
        if placement_index >= 0:
            weighting_mode_combo.setCurrentIndex(placement_index)
        preset_state["applying"] = False
        preset_name = select_preset_combo.itemText(index)
        preset_state["name"] = preset_name
        preset_state["preset_in_use"] = True
        show_preset_status()
        QMessageBox.information(dialog, "Select Preset", f"'{preset_name}' preset applied!")

    select_preset_combo.currentIndexChanged.connect(apply_selected_preset)
    refresh_preset_dropdown()

    def prompt_for_new_preset_name() -> str | None:
        default_name = next_custom_astro_twin_preset_name(load_custom_astro_twin_presets())
        preset_name, accepted = QInputDialog.getText(
            dialog,
            "Save as Preset",
            "Preset name:",
            text=default_name,
        )
        return preset_name.strip() if accepted and preset_name.strip() else None

    def save_current_custom_preset() -> None:
        preset_name = str(preset_state.get("name") or "")
        update_current = False
        # Keep the loaded preset identity even after its controls become dirty,
        # so edited presets can still update their source record.
        if preset_name:
            choice_dialog = QMessageBox(dialog)
            choice_dialog.setWindowTitle("Save as Preset")
            choice_dialog.setText("Do you want to update the current preset or save this as new preset?")
            update_button = choice_dialog.addButton(f"Update '{preset_name}'", QMessageBox.AcceptRole)
            save_new_button = choice_dialog.addButton("Save as new", QMessageBox.ActionRole)
            choice_dialog.exec()
            clicked_button = choice_dialog.clickedButton()
            if clicked_button is update_button:
                update_current = True
            elif clicked_button is save_new_button:
                preset_name = prompt_for_new_preset_name() or ""
            else:
                return
        else:
            preset_name = prompt_for_new_preset_name() or ""
        if not preset_name:
            return
        try:
            if update_current:
                update_custom_astro_twin_preset(preset_name, current_custom_settings())
            else:
                save_custom_astro_twin_preset(preset_name, current_custom_settings())
        except (KeyError, OSError) as exc:
            QMessageBox.warning(dialog, "Save as Preset", f"Could not save preset: {exc}")
            return
        preset_state["name"] = preset_name
        preset_state["preset_in_use"] = True
        show_preset_status()
        refresh_preset_dropdown()

    save_custom_preset_button.clicked.connect(save_current_custom_preset)
    preset_action_row = QHBoxLayout()
    preset_action_row.addWidget(save_custom_preset_button)
    preset_action_row.addWidget(select_preset_label)
    preset_action_row.addWidget(select_preset_combo)
    preset_action_row.addWidget(manage_presets_button)
    preset_action_row.addStretch(1)
    custom_fields_layout.addLayout(preset_action_row)

    #reset_granular_row = QHBoxLayout()
    #reset_granular_row.addWidget(reset_similarity_weights_button, alignment=Qt.AlignLeft)
    #reset_granular_row.addStretch(1)
    #reset_granular_row.addWidget(granular_explanations_checkbox, alignment=Qt.AlignRight)
    #custom_fields_layout.addLayout(reset_granular_row)
    algorithm_layout.addWidget(custom_fields_frame)
    algorithm_layout.addStretch(1)

    calibrate_similarity_button = QPushButton("Calibrate Similarity Norms")
    calibrate_similarity_button.setToolTip(
        "Compute min/max/avg/median/mode/standard-deviation similarity across saved chart pairs and save thresholds."
    )
    calibrate_similarity_button.clicked.connect(on_calibrate_clicked)
    calibration_layout.addWidget(calibrate_similarity_button)

    similarity_thresholds_label = QLabel("Similarity Thresholds (%)")
    similarity_thresholds_label.setStyleSheet(subheader_style)
    calibration_layout.addWidget(similarity_thresholds_label)
    calibration_layout.addWidget(
        QLabel(
            "Manual override for band cutoffs (q20/q40/q60/q80). "
            "Values are auto-sorted and saved systemwide."
        )
    )

    thresholds_grid = QGridLayout()
    thresholds_grid.setContentsMargins(0, 0, 0, 0)
    thresholds_grid.setHorizontalSpacing(8)
    thresholds_grid.setVerticalSpacing(6)
    threshold_spinboxes: dict[str, QDoubleSpinBox] = {}
    for row_index, (key, label_text) in enumerate(threshold_rows):
        label = QLabel(label_text)
        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(1)
        spinbox.setRange(0.0, 100.0)
        spinbox.setSingleStep(0.5)
        spinbox.setSuffix("%")
        spinbox.setAlignment(Qt.AlignRight)
        thresholds_grid.addWidget(label, row_index, 0)
        thresholds_grid.addWidget(spinbox, row_index, 1)
        threshold_spinboxes[key] = spinbox
    calibration_layout.addLayout(thresholds_grid)

    thresholds_button_row = QHBoxLayout()
    thresholds_save_button = QPushButton("Save Threshold Overrides")
    thresholds_save_button.clicked.connect(on_save_thresholds_clicked)
    thresholds_reset_button = QPushButton("Reset Thresholds to Defaults")
    thresholds_reset_button.clicked.connect(on_reset_thresholds_clicked)
    thresholds_button_row.addWidget(thresholds_save_button)
    thresholds_button_row.addWidget(thresholds_reset_button)
    thresholds_button_row.addStretch(1)
    calibration_layout.addLayout(thresholds_button_row)
    calibration_layout.addStretch(1)

    show_high_similarity_button = QPushButton("Show 90-100% similarities")
    show_high_similarity_button.setToolTip(
        "Calculate database-wide Astro Twin scores with the current calculator mode and list chart pairs "
        "whose similarity is between 90% and 100%. Each listed chart name opens in Chart Editor."
    )
    show_high_similarity_button.clicked.connect(on_show_high_similarity_clicked)
    research_layout.addWidget(show_high_similarity_button, alignment=Qt.AlignLeft)

    research_accuracy_divider = QFrame()
    research_accuracy_divider.setFrameShape(QFrame.HLine)
    research_accuracy_divider.setFrameShadow(QFrame.Sunken)
    research_layout.addWidget(research_accuracy_divider)

    algorithm_accuracy_label = SimilarityAlgorithmAccuracyBrowser()
    algorithm_accuracy_label.setVisible(perceived_accuracy_controls_enabled)
    research_layout.addWidget(algorithm_accuracy_label, 1)

    return {
        "default_radio": default_radio,
        "generic_astro_radio": generic_astro_radio,
        "comprehensive_radio": comprehensive_radio,
        "all_or_nothing_radio": all_or_nothing_radio,
        "big_3_radio": big_3_radio,
        "custom_radio": custom_radio,
        "database_distinction_radio": database_distinction_radio,
        "all_or_nothing_fields_frame": all_or_nothing_fields_frame,
        "custom_fields_frame": custom_fields_frame,
        "calculator_checkboxes": calculator_checkboxes,
        "calculator_weights": calculator_weights,
        "calculator_total_label": total_weight_value_label,
        "save_custom_preset_button": save_custom_preset_button,
        "select_preset_combo": select_preset_combo,
        "preset_status_label": preset_status_label,
        "preset_state": preset_state,
        "manage_presets_button": manage_presets_button,
        "placement_weighting_mode_combo": weighting_mode_combo,
        "all_or_nothing_criterion_combo": all_or_nothing_criterion_combo,
        "demographic_match_buttons": demographic_match_buttons,
        "threshold_spinboxes": threshold_spinboxes,
        "perceived_accuracy_checkbox": None,
        "algorithm_accuracy_label": algorithm_accuracy_label,
        "tabs": tabs,
    }


class SizeCheckerPopup(QDialog):
    """Non-modal developer popup that reports current window/panel dimensions."""

    def __init__(
        self,
        parent_window: QWidget,
        splitter: QSplitter,
        panel_labels: tuple[str, str, str] = ("Left", "Middle", "Right"),
        title: str = "Size Checker",
    ) -> None:
        super().__init__(None)
        self._parent_window: QWidget | None = None
        self._splitter: QSplitter | None = None
        self._panel_labels = panel_labels

        self.setWindowTitle(title)
        self.setModal(False)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        self._copy_button = QPushButton(self)
        self._copy_button.setToolTip("Copy size readout")
        apply_button_cursor(self._copy_button)
        self._copy_button.clicked.connect(self._copy_readout)

        copy_icon_path = Path(__file__).resolve().parents[1] / "graphics" / "copy_icon.png"
        if copy_icon_path.exists():
            self._copy_button.setIcon(QIcon(str(copy_icon_path)))
            self._copy_button.setText("")
        else:
            self._copy_button.setText("Copy")

        self._readout = QTextEdit(self)
        self._readout.setReadOnly(True)
        self._readout.setStyleSheet(
            "QTextEdit {"
            "background-color: rgba(20, 20, 20, 0.9);"
            "color: #f5f5f5;"
            "padding: 8px;"
            "border: 1px solid #777777;"
            "font-family: 'Courier New', monospace;"
            "font-size: 11px;"
            "}"
        )

        header_layout = QHBoxLayout()
        header_layout.addStretch(1)
        header_layout.addWidget(self._copy_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(header_layout)
        layout.addWidget(self._readout)

        self.resize(360, 170)

        self.set_target(
            parent_window=parent_window,
            splitter=splitter,
            panel_labels=panel_labels,
            title=title,
        )

    def set_target(
        self,
        parent_window: QWidget,
        splitter: QSplitter,
        panel_labels: tuple[str, str, str] | None = None,
        title: str | None = None,
    ) -> None:
        if self._parent_window is not None:
            self._parent_window.removeEventFilter(self)
        if self._splitter is not None:
            try:
                self._splitter.splitterMoved.disconnect(self.refresh)
            except (RuntimeError, TypeError):
                pass
            self._splitter.removeEventFilter(self)

        self._parent_window = parent_window
        self._splitter = splitter
        if panel_labels is not None:
            self._panel_labels = panel_labels
        if title is not None:
            self.setWindowTitle(title)

        self._parent_window.installEventFilter(self)
        self._splitter.installEventFilter(self)
        self._splitter.splitterMoved.connect(self.refresh)

        self.refresh()

    def closeEvent(self, event) -> None:
        if self._splitter is not None:
            try:
                self._splitter.splitterMoved.disconnect(self.refresh)
            except (RuntimeError, TypeError):
                pass
            self._splitter.removeEventFilter(self)
        if self._parent_window is not None:
            self._parent_window.removeEventFilter(self)
        self._splitter = None
        self._parent_window = None
        super().closeEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self.refresh()
        return super().eventFilter(watched, event)

    def refresh(self) -> None:
        if self._parent_window is None or self._splitter is None:
            return
        splitter_sizes = self._splitter.sizes()
        if len(splitter_sizes) < 3:
            return

        total = sum(max(0, value) for value in splitter_sizes)
        if total <= 0:
            ratios = (0.0, 0.0, 0.0)
        else:
            ratios = tuple((size / total) for size in splitter_sizes[:3])

        window_size = self._parent_window.size()
        lines = [
            f"Window: {window_size.width()}w × {window_size.height()}h",
            f"{self._panel_labels[0]} panel: {splitter_sizes[0]}w",
            f"{self._panel_labels[1]} panel: {splitter_sizes[1]}w",
            f"{self._panel_labels[2]} panel: {splitter_sizes[2]}w",
            "Ratio (L:M:R): "
            f"{ratios[0]:.3f} : {ratios[1]:.3f} : {ratios[2]:.3f}",
        ]
        self._readout.setPlainText("\n".join(lines))

        anchor = self._parent_window.mapToGlobal(QPoint(0, self._parent_window.height()))
        self.move(anchor.x() + 14, anchor.y() - self.height() - 14)

    def _copy_readout(self) -> None:
        QApplication.clipboard().setText(self._readout.toPlainText())


class MetadataMigrationPanel(QDialog):
    """Floating metadata migration utility that stays above other app windows."""

    def __init__(
        self,
        *,
        parent: QWidget,
        on_alias_to_from_clicked: Callable[[], None],
        on_comments_to_source_clicked: Callable[[], None],
        on_clean_biography_clicked: Callable[[], None],
        on_get_bio_clicked: Callable[[], None],
        on_clean_birthplace_clicked: Callable[[], None],
    ) -> None:
        super().__init__(None)
        self.setWindowTitle("Metadata Cleanup Panel")
        self.setModal(False)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.Tool, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(300, 600)
        self.setMinimumSize(200, 400)
        self.setStyleSheet(
            "QDialog { background-color: #26004d; }"
            "QLabel { color: #f5f5f5; }"
            "QPushButton {"
            "background-color: #1e6bd6;"
            "color: #ffffff;"
            "border: 1px solid #0f4eab;"
            "border-radius: 4px;"
            "padding: 6px 8px;"
            "}"
            "QPushButton:hover { background-color: #2a7be8; }"
            "QPushButton:pressed { background-color: #1559ba; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "Runs metadata cleanup scripts against currently selected charts. Yw."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        alias_button = QPushButton("Alias -> From")
        alias_button.clicked.connect(on_alias_to_from_clicked)
        layout.addWidget(alias_button)

        alias_caption = QLabel(
            "Takes the 'alias' property's value for each selected chart and moves it to each "
            "respective chart's 'from_whence' property"
        )
        alias_caption.setWordWrap(True)
        alias_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(alias_caption)

        comments_button = QPushButton("Comments -> Source")
        comments_button.clicked.connect(on_comments_to_source_clicked)
        layout.addWidget(comments_button)

        comments_caption = QLabel(
            "Finds all instances of URLs in these charts' Comments property and migrates "
            "them to the Source property"
        )
        comments_caption.setWordWrap(True)
        comments_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(comments_caption)

        biography_button = QPushButton("Clean up Biography Text")
        biography_button.clicked.connect(on_clean_biography_clicked)
        layout.addWidget(biography_button)

        biography_caption = QLabel(
            "For selected charts, keep biography text up to (but not including) "
            "'Astrological Profile of', and remove everything from that phrase onward"
        )
        biography_caption.setWordWrap(True)
        biography_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(biography_caption)

        get_bio_button = QPushButton("Get Bio")
        get_bio_button.clicked.connect(on_get_bio_clicked)
        layout.addWidget(get_bio_button)

        get_bio_caption = QLabel(
            "Imports biography from Wikipedia for selected chart(s). "
            "When multiple charts are selected, requests are delayed 1–6 seconds each."
        )
        get_bio_caption.setWordWrap(True)
        get_bio_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(get_bio_caption)

        birthplace_button = QPushButton("Clean up Birthplace")
        birthplace_button.clicked.connect(on_clean_birthplace_clicked)
        layout.addWidget(birthplace_button)

        birthplace_caption = QLabel(
            "Converts verbose imported birthplace metadata to concise Gazetteer-friendly "
            "city/region/country labels (removes street addresses, ZIP/postal codes, counties, and landmarks)."
        )
        birthplace_caption.setWordWrap(True)
        birthplace_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(birthplace_caption)
        layout.addStretch(1)

        if isinstance(parent, QWidget):
            self._anchor_near_parent(parent)

    def _anchor_near_parent(self, parent: QWidget) -> None:
        anchor = parent.mapToGlobal(QPoint(0, 0))
        self.move(anchor.x() + 36, anchor.y() + 84)


class _RenameLabelDialog(QDialog):
    def __init__(self, *, parent: QWidget, title: str, old_label: str, max_length: int) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(360, 130)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Rename '{old_label}' to:"))

        self._line_edit = QLineEdit(self)
        self._line_edit.setMaxLength(max_length)
        self._line_edit.setPlaceholderText(f"Max {max_length} characters")
        self._line_edit.setText(old_label)
        self._line_edit.selectAll()
        layout.addWidget(self._line_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self._line_edit.text().strip()


class _MergeLabelsDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget,
        title: str,
        choices: list[tuple[str, int]],
        default_consolidate: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Consolidate tag:"))
        self._consolidate_combo = QComboBox(self)
        for label, count in choices:
            self._consolidate_combo.addItem(f"{label} ({count})", label)
        apply_shared_dropdown_style(self._consolidate_combo)
        layout.addWidget(self._consolidate_combo)

        layout.addWidget(QLabel("Into tag:"))
        self._into_combo = QComboBox(self)
        for label, count in choices:
            self._into_combo.addItem(f"{label} ({count})", label)
        apply_shared_dropdown_style(self._into_combo)
        layout.addWidget(self._into_combo)

        if default_consolidate:
            consolidate_index = self._consolidate_combo.findData(default_consolidate)
            if consolidate_index >= 0:
                self._consolidate_combo.setCurrentIndex(consolidate_index)
                into_index = 0 if consolidate_index != 0 else 1
                if 0 <= into_index < self._into_combo.count():
                    self._into_combo.setCurrentIndex(into_index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        consolidate = str(self._consolidate_combo.currentData() or "").strip()
        into = str(self._into_combo.currentData() or "").strip()
        return consolidate, into


SETTINGS_KEY_TAG_CATEGORY_DISPLAY_NAMES = "property_manager/tag_category_display_names"


def _split_tag_category(value: str, allowed_prefixes: set[str] | None = None) -> tuple[str, str]:
    normalized = str(value or "").strip()
    if "." not in normalized:
        return "", normalized
    prefix, tag_name = normalized.split(".", 1)
    if not prefix.strip() or not tag_name.strip():
        return "", normalized
    return prefix.strip(), tag_name.strip()


def _compose_tag_category(prefix: str, tag_name: str) -> str:
    clean_tag = str(tag_name or "").strip()
    clean_prefix = str(prefix or "").strip()
    if not clean_tag:
        return ""
    if clean_prefix:
        return f"{clean_prefix}.{clean_tag}"
    return clean_tag


def _defer_tag_category_assignment(
    receiver: QWidget,
    category_prefix: str,
    labels: list[str],
) -> None:
    """Run a Tag Manager drop assignment after Qt completes DnD cleanup."""
    receiver_ref = weakref.ref(receiver)
    deferred_prefix = str(category_prefix or "").strip()
    deferred_labels = tuple(labels)

    def assign_after_drop_cleanup() -> None:
        target = receiver_ref()
        if target is None or not shiboken6.isValid(target):
            return
        on_drop_labels = getattr(target, "_on_drop_labels", None)
        if callable(on_drop_labels):
            on_drop_labels(deferred_prefix, list(deferred_labels))

    QTimer.singleShot(0, assign_after_drop_cleanup)


class _TagCategoryDropList(QListWidget):
    def __init__(self, parent: QWidget, on_drop_labels: Callable[[str, list[str]], None]) -> None:
        super().__init__(parent)
        self._on_drop_labels = on_drop_labels
        self._current_drop_target_row = -1
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(False)

    def _set_drop_target_item(self, target_item: QListWidgetItem | None) -> None:
        target_row = self.row(target_item) if target_item is not None else -1
        if target_row == self._current_drop_target_row:
            return
        self._current_drop_target_row = target_row
        default_color = self.palette().text().color()
        for index in range(self.count()):
            item = self.item(index)
            if item is None:
                continue
            item.setForeground(QColor("#9B59FF") if index == target_row else default_color)

    def _clear_drop_target_highlight(self) -> None:
        self._set_drop_target_item(None)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        source = event.source()
        if isinstance(source, QListWidget):
            event.acceptProposedAction()
            return
        self._clear_drop_target_highlight()
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        source = event.source()
        if isinstance(source, QListWidget):
            self._set_drop_target_item(self.itemAt(event.position().toPoint()))
            event.acceptProposedAction()
            return
        self._clear_drop_target_highlight()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._clear_drop_target_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        target_item = self.itemAt(event.position().toPoint())
        self._set_drop_target_item(target_item)
        if target_item is None:
            self._clear_drop_target_highlight()
            event.ignore()
            return
        source = event.source()
        labels: list[str] = []
        if isinstance(source, QListWidget):
            for item in source.selectedItems():
                label = str(item.data(Qt.UserRole + 2) or item.data(Qt.UserRole) or "").strip()
                if label:
                    labels.append(label)
        labels = list(dict.fromkeys(labels))
        if not labels:
            self._clear_drop_target_highlight()
            event.ignore()
            return
        category_prefix = str(target_item.data(Qt.UserRole) or "").strip()
        if category_prefix:
            self._clear_drop_target_highlight()
            # Treat the DnD payload as a command, not a Qt item move.  Defer the
            # database rename/reload until after Qt finishes drop cleanup so the
            # source model is not rebuilt while Qt still holds dragged indexes.
            _defer_tag_category_assignment(self, category_prefix, labels)
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        self._clear_drop_target_highlight()
        event.ignore()


class _TagHierarchyTree(QTreeWidget):
    def __init__(
        self,
        parent: QWidget,
        get_active_field: Callable[[], str],
        on_drop_labels: Callable[[str, list[str]], None],
    ) -> None:
        super().__init__(parent)
        self._get_active_field = get_active_field
        self._on_drop_labels = on_drop_labels
        self._highlighted_category_item: QTreeWidgetItem | None = None
        self.setHeaderHidden(True)
        # The tree is reused by managers with both one and several columns.
        # Never retain a narrow first-column width from the presets table when
        # returning to a single-column property list.
        self.setTextElideMode(Qt.ElideNone)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def _is_tags_mode(self) -> bool:
        return self._get_active_field() == ManageMetadataLabelsDialog.FIELD_TAGS

    def _is_category_node(self, item: QTreeWidgetItem | None) -> bool:
        if item is None:
            return False
        return item.childCount() > 0 and bool(str(item.data(0, Qt.UserRole + 10) or "").strip())

    def _set_category_highlight(self, item: QTreeWidgetItem | None) -> None:
        highlighted_item = item if self._is_category_node(item) else None
        if highlighted_item is self._highlighted_category_item:
            return
        default_color = self.palette().text().color()
        if self._highlighted_category_item is not None:
            self._highlighted_category_item.setForeground(0, default_color)
        if highlighted_item is not None:
            highlighted_item.setForeground(0, QColor("#9B59FF"))
        self._highlighted_category_item = highlighted_item

    def _clear_category_highlight(self) -> None:
        self._set_category_highlight(None)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._is_tags_mode():
            self._set_category_highlight(self.itemAt(event.position().toPoint()))
            event.acceptProposedAction()
            return
        self._clear_category_highlight()
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._is_tags_mode():
            target_item = self.itemAt(event.position().toPoint())
            self._set_category_highlight(target_item)
            if self._is_category_node(target_item):
                event.acceptProposedAction()
                return
            self._clear_category_highlight()
            event.ignore()
            return
        self._clear_category_highlight()
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._clear_category_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        self._clear_category_highlight()
        if not self._is_tags_mode():
            event.ignore()
            return
        target_item = self.itemAt(event.position().toPoint())
        if not self._is_category_node(target_item):
            event.ignore()
            return
        category_prefix = str(target_item.data(0, Qt.UserRole + 10) or "").strip()
        if not category_prefix:
            event.ignore()
            return
        source = event.source()
        source_items = source.selectedItems() if isinstance(source, QTreeWidget) else self.selectedItems()
        labels: list[str] = []
        for item in source_items:
            label = str(
                item.data(0, Qt.UserRole + 2)
                or item.data(0, Qt.UserRole + 10)
                or item.data(0, Qt.UserRole)
                or ""
            ).strip()
            if label:
                labels.append(label)
        labels = list(dict.fromkeys(labels))
        if not labels:
            event.ignore()
            return
        # Treat the DnD payload as a command, not a Qt item move.  Defer the
        # database rename/reload until after Qt finishes drop cleanup so the
        # source model is not rebuilt while Qt still holds dragged indexes.
        _defer_tag_category_assignment(self, category_prefix, labels)
        event.setDropAction(Qt.CopyAction)
        event.accept()


class ManageMetadataLabelsDialog(QDialog):
    FIELD_TAGS = "tags"
    FIELD_COLLECTIONS = "collections"
    FIELD_RELATIONSHIPS = "relationship_types"
    FIELD_SENTIMENTS = "sentiments"
    FIELD_ASTRO_TWIN_PRESETS = "astro_twin_presets"
    FIELD_NAMES = "names"

    SORT_FREQUENCY = "frequency"
    SORT_ALPHABETICAL = "alphabetical"

    def __init__(
        self,
        *,
        parent: QWidget,
        load_usage,
        apply_change,
        label_limit: int,
        load_chart_names=None,
        refresh_chart_context: Callable[[], None] | None = None,
        collection_actions: dict[str, object] | None = None,
        settings=None,
        initial_field: str | None = None,
        lock_field: bool = False,
        window_title: str = "Property Manager",
        intro_text: str = "Current + legacy labels found in database (including unused/orphaned).",
        show_close_button: bool = True,
        window_flags: Qt.WindowType = Qt.Dialog,
    ) -> None:
        super().__init__(parent, window_flags)
        self.setWindowTitle(window_title)
        self.resize(860, 620)
        self._load_usage = load_usage
        self._apply_change = apply_change
        self._load_chart_names = load_chart_names
        self._refresh_chart_context = refresh_chart_context
        self._collection_actions = collection_actions or {}
        self._settings = settings
        self._label_limit = max(1, label_limit)
        self._usage_data: dict[str, list[dict[str, object]]] = {}
        self._refreshing_label_views = False
        self._pending_usage_reload: tuple[bool, str] | None = None
        self._usage_reload_timer = QTimer(self)
        self._usage_reload_timer.setSingleShot(True)
        self._usage_reload_timer.timeout.connect(self._run_queued_usage_reload)
        self._tag_category_display_names: dict[str, str] = {
            prefix.casefold(): name for name, prefix in TAG_CATEGORY_OPTIONS
        }
        self._load_tag_category_display_names()

        layout = QVBoxLayout(self)

        self._field_selector = QComboBox(self)
        field_options = [
            ("Relationships", self.FIELD_RELATIONSHIPS),
            ("Sentiments", self.FIELD_SENTIMENTS),
            ("Collections", self.FIELD_COLLECTIONS),
            ("Tags", self.FIELD_TAGS),
            ("Names", self.FIELD_NAMES),
            ("Astro Twin Presets", self.FIELD_ASTRO_TWIN_PRESETS),
        ]
        for label, field_value in field_options:
            self._field_selector.addItem(label, field_value)
        self._field_selector.currentIndexChanged.connect(self._refresh_list)
        self._field_selector.currentIndexChanged.connect(self._sync_field_button_selection)
        self._field_selector.setVisible(False)

        if not lock_field:
            self._field_tabs = QTabBar(self)
            self._field_tabs.setStyleSheet(SETTINGS_TAB_STYLE)
            self._field_tabs.setDrawBase(False)
            self._field_tabs.setExpanding(False)
            for label, _field_value in field_options:
                self._field_tabs.addTab(label)
            self._field_tabs.currentChanged.connect(self._field_selector.setCurrentIndex)
            layout.addWidget(self._field_tabs)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        intro_label = QLabel(intro_text)
        intro_label.setStyleSheet("font-style: italic;")
        header_row.addWidget(intro_label, 1)
        header_row.addWidget(QLabel("Sort:"))
        self._sort_selector = QComboBox(self)
        sort_options = sorted(
            [("Alphabetical", self.SORT_ALPHABETICAL), ("Frequency", self.SORT_FREQUENCY)],
            key=lambda option: option[0].casefold(),
        )
        for label, sort_value in sort_options:
            self._sort_selector.addItem(label, sort_value)
        apply_shared_dropdown_style(self._sort_selector)
        self._sort_selector.currentIndexChanged.connect(self._refresh_list)
        header_row.addWidget(self._sort_selector)
        layout.addLayout(header_row)

        # A splitter, rather than a layout with fixed stretch factors, lets the
        # user resize every visible Property Manager column.
        self._column_splitter = QSplitter(Qt.Horizontal, self)
        self._column_splitter.setChildrenCollapsible(False)
        self._unsorted_panel_widget = QWidget(self)
        self._unsorted_panel = QVBoxLayout(self._unsorted_panel_widget)
        self._unsorted_panel.setContentsMargins(0, 0, 0, 0)
        self._unsorted_panel.addWidget(QLabel("Uncategorized tags"))
        self._unsorted_list_widget = _TagHierarchyTree(
            self,
            self._active_field,
            self._assign_tags_to_category,
        )
        self._unsorted_list_widget.itemSelectionChanged.connect(
            lambda: self._on_selection_changed(self._unsorted_list_widget)
        )
        self._unsorted_list_widget.currentItemChanged.connect(
            lambda _current, _previous: self._on_selection_changed(self._unsorted_list_widget)
        )
        self._unsorted_panel.addWidget(self._unsorted_list_widget, 1)
        self._column_splitter.addWidget(self._unsorted_panel_widget)

        middle_panel_widget = QWidget(self)
        middle_panel = QVBoxLayout(middle_panel_widget)
        middle_panel.setContentsMargins(0, 0, 0, 0)
        self._astro_twin_presets_header = QLabel("Astro Twin Presets Manager")
        self._astro_twin_presets_header.setStyleSheet(CHART_DATA_INFO_LABEL_STYLE)
        self._astro_twin_presets_header.setVisible(False)
        middle_panel.addWidget(self._astro_twin_presets_header)
        self._astro_twin_algorithm_placeholder = QLabel(
            "select a preset to see its algorithmic weights"
        )
        self._astro_twin_algorithm_placeholder.setStyleSheet("font-style: italic;")
        self._astro_twin_algorithm_placeholder.setVisible(False)
        middle_panel.addWidget(self._astro_twin_algorithm_placeholder)
        self._list_widget = _TagHierarchyTree(
            self,
            self._active_field,
            self._assign_tags_to_category,
        )
        self._list_widget.itemSelectionChanged.connect(lambda: self._on_selection_changed(self._list_widget))
        self._list_widget.currentItemChanged.connect(
            lambda _current, _previous: self._on_selection_changed(self._list_widget)
        )
        self._list_widget.itemDoubleClicked.connect(self._rename_tag_category_display_name)
        middle_panel.addWidget(self._list_widget, 1)
        self._column_splitter.addWidget(middle_panel_widget)

        self._right_panel_widget = QWidget(self)
        right_panel = QVBoxLayout(self._right_panel_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)
        self._chart_names_heading = QLabel(self._chart_names_heading_text())
        right_panel.addWidget(self._chart_names_heading)
        self._chart_names_list = QListWidget(self)
        self._chart_names_list.setSelectionMode(QAbstractItemView.NoSelection)
        right_panel.addWidget(self._chart_names_list, 1)
        self._column_splitter.addWidget(self._right_panel_widget)
        self._column_splitter.setStretchFactor(0, 1)
        self._column_splitter.setStretchFactor(1, 2)
        self._column_splitter.setStretchFactor(2, 1)
        self._column_splitter.splitterMoved.connect(self._save_column_widths)
        layout.addWidget(self._column_splitter, 1)

        if initial_field in {
            self.FIELD_SENTIMENTS,
            self.FIELD_RELATIONSHIPS,
            self.FIELD_TAGS,
            self.FIELD_COLLECTIONS,
            self.FIELD_ASTRO_TWIN_PRESETS,
            self.FIELD_NAMES,
        }:
            index = self._field_selector.findData(initial_field)
            if index >= 0:
                self._field_selector.setCurrentIndex(index)
        self._sync_field_button_selection()

        button_row = QHBoxLayout()
        self._rename_button = QPushButton("Rename")
        self._rename_button.clicked.connect(self._rename_selected)
        self._delete_button = QPushButton("❌Delete")
        self._delete_button.clicked.connect(self._delete_selected)
        self._merge_button = QPushButton("Merge tags")
        self._merge_button.clicked.connect(self._merge_selected_tags)
        self._new_button = QPushButton("New")
        self._new_button.clicked.connect(self._create_collection)
        self._add_selected_button = QPushButton("Add Selected Charts")
        self._add_selected_button.clicked.connect(self._add_selected_to_collection)
        self._remove_selected_button = QPushButton("Remove Selected Charts")
        self._remove_selected_button.clicked.connect(self._remove_selected_from_collection)
        # refresh_button = QPushButton("Refresh")
        # refresh_button.clicked.connect(self._reload_usage)
        close_button = QPushButton("Close") if show_close_button else None
        if close_button is not None:
            close_button.clicked.connect(self.accept)

        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._merge_button)
        button_row.addWidget(self._new_button)
        button_row.addWidget(self._add_selected_button)
        button_row.addWidget(self._remove_selected_button)
        button_row.addStretch(1)
        #button_row.addWidget(refresh_button)
        if close_button is not None:
            button_row.addWidget(close_button)
        layout.addLayout(button_row)

        # Defer loading so the dialog can render immediately before DB work runs.
        QTimer.singleShot(0, self._reload_usage)

    def _sync_field_button_selection(self) -> None:
        if not hasattr(self, "_field_tabs"):
            return
        self._field_tabs.setCurrentIndex(self._field_selector.currentIndex())

    def refresh_usage(self) -> None:
        self._reload_usage()

    def select_field(self, field: str) -> None:
        """Switch the manager to a specific property subpanel."""
        index = self._field_selector.findData(field)
        if index >= 0:
            self._field_selector.setCurrentIndex(index)
            self._sync_field_button_selection()

    def _queue_usage_reload(
        self,
        *,
        refresh_chart_context: bool = False,
        keep_selection_label: str = "",
    ) -> None:
        """Reload tree models after the current Qt item-view signal unwinds.

        Parent-tag operations replace several tree items at once.  Rebuilding
        either tree directly from a clicked/double-clicked/drop callback can
        invalidate indexes that Qt still uses while finishing that callback,
        which can cause a native (non-Python) crash.  Coalesce requests and let
        the event loop finish the active item-view operation first.
        """
        pending_refresh, pending_selection = self._pending_usage_reload or (False, "")
        self._pending_usage_reload = (
            pending_refresh or refresh_chart_context,
            keep_selection_label or pending_selection,
        )
        if self._usage_reload_timer.isActive():
            return
        self._usage_reload_timer.start(0)

    def _run_queued_usage_reload(self) -> None:
        pending = self._pending_usage_reload
        self._pending_usage_reload = None
        if pending is None:
            return
        refresh_chart_context, keep_selection_label = pending
        self._reload_usage(
            refresh_chart_context=refresh_chart_context,
            keep_selection_label=keep_selection_label,
        )

    def _load_tag_category_display_names(self) -> None:
        settings = getattr(self, "_settings", None)
        if settings is None:
            return
        payload = settings.value(SETTINGS_KEY_TAG_CATEGORY_DISPLAY_NAMES, {})
        if not isinstance(payload, dict):
            return
        for prefix, display_name in payload.items():
            clean_prefix = str(prefix or "").strip().casefold()
            clean_name = str(display_name or "").strip()
            if clean_prefix and clean_name:
                self._tag_category_display_names[clean_prefix] = clean_name

    def _save_tag_category_display_names(self) -> None:
        settings = getattr(self, "_settings", None)
        if settings is None:
            return
        settings.setValue(
            SETTINGS_KEY_TAG_CATEGORY_DISPLAY_NAMES,
            dict(sorted(self._tag_category_display_names.items())),
        )

    def _column_widths_key(self) -> str:
        """Return a key per layout, since Tags has an additional column."""
        return f"{SETTINGS_KEY_PROPERTY_MANAGER_SPLITTER_SIZES}/{self._active_field()}"

    def _save_column_widths(self, *_args) -> None:
        settings = getattr(self, "_settings", None)
        splitter = getattr(self, "_column_splitter", None)
        if settings is None or splitter is None:
            return
        settings.setValue(self._column_widths_key(), splitter.sizes())

    def _restore_column_widths(self) -> None:
        settings = getattr(self, "_settings", None)
        if settings is None:
            return
        raw_sizes = settings.value(self._column_widths_key())
        if not isinstance(raw_sizes, (list, tuple)) or len(raw_sizes) != 3:
            return
        try:
            sizes = [max(0, int(size)) for size in raw_sizes]
        except (TypeError, ValueError):
            return
        if any(sizes):
            self._column_splitter.setSizes(sizes)

    def _save_preset_column_widths(self, *_args) -> None:
        if self._active_field() != self.FIELD_ASTRO_TWIN_PRESETS:
            return
        settings = getattr(self, "_settings", None)
        if settings is not None:
            settings.setValue(
                SETTINGS_KEY_PROPERTY_MANAGER_PRESET_COLUMN_SIZES,
                [self._list_widget.columnWidth(index) for index in range(3)],
            )

    def _on_preset_column_resized(self, *_args) -> None:
        self._save_preset_column_widths()
        QTimer.singleShot(0, self._fit_preset_columns_to_viewport)

    def _restore_preset_column_widths(self) -> bool:
        settings = getattr(self, "_settings", None)
        if settings is None:
            return False
        raw_sizes = settings.value(SETTINGS_KEY_PROPERTY_MANAGER_PRESET_COLUMN_SIZES)
        if not isinstance(raw_sizes, (list, tuple)) or len(raw_sizes) != 3:
            return False
        try:
            sizes = [max(1, int(size)) for size in raw_sizes]
        except (TypeError, ValueError):
            return False
        for index, size in enumerate(sizes):
            self._list_widget.setColumnWidth(index, size)
        return True

    def _fit_preset_columns_to_viewport(self) -> None:
        """Keep the final presets column inside the tree's visible viewport."""
        if self._active_field() != self.FIELD_ASTRO_TWIN_PRESETS:
            return
        header = self._list_widget.header()
        viewport_width = self._list_widget.viewport().width()
        if viewport_width <= 0:
            return
        data_points_width = max(header.sectionSizeHint(2), 90)
        available_for_first_two = max(2, viewport_width - data_points_width)
        first_two = [self._list_widget.columnWidth(index) for index in range(2)]
        requested_width = sum(first_two)
        if requested_width > available_for_first_two:
            scale = available_for_first_two / requested_width
            first_two = [max(1, round(width * scale)) for width in first_two]
        self._list_widget.setColumnWidth(0, first_two[0])
        self._list_widget.setColumnWidth(1, max(1, available_for_first_two - first_two[0]))

    def _active_field(self) -> str:
        value = self._field_selector.currentData()
        return str(value or self.FIELD_SENTIMENTS)

    def _chart_names_heading_text(self) -> str:
        return {
            self.FIELD_TAGS: "Charts with selected tag",
            self.FIELD_COLLECTIONS: "Charts in selected collection",
            self.FIELD_RELATIONSHIPS: "Charts with selected relationship",
            self.FIELD_SENTIMENTS: "Charts with selected sentiment",
            self.FIELD_ASTRO_TWIN_PRESETS: "Algorithm",
            self.FIELD_NAMES: "Charts with selected name or alias",
        }.get(self._active_field(), "Charts")

    def _selected_chart_names_heading_text(self, selected_label: str) -> str:
        clean_label = str(selected_label or "").strip()
        if not clean_label:
            return self._chart_names_heading_text()
        if self._active_field() == self.FIELD_TAGS:
            clean_label = " > ".join(
                part.replace("_", " ").replace("-", " ").title()
                for part in clean_label.split(".")
                if part
            )
        if self._active_field() == self.FIELD_COLLECTIONS:
            return f"Charts in {clean_label}"
        return f"Charts with {clean_label}"

    def _active_rows(self) -> list[dict[str, object]]:
        rows = list(self._usage_data.get(self._active_field(), []))
        sort_mode = self.SORT_FREQUENCY
        if hasattr(self, "_sort_selector"):
            sort_mode = str(self._sort_selector.currentData() or self.SORT_FREQUENCY)
        if sort_mode == self.SORT_ALPHABETICAL:
            rows.sort(key=lambda row: str(row.get("label", "")).casefold())
            return rows
        rows.sort(
            key=lambda row: (
                -int(row.get("count", 0) or 0),
                str(row.get("label", "")).casefold(),
            )
        )
        return rows

    def _known_tag_category_prefixes(self) -> set[str]:
        prefixes = {prefix.casefold() for _name, prefix in TAG_CATEGORY_OPTIONS}
        prefixes.update(self._tag_category_display_names.keys())
        return prefixes

    def _selected_category_prefix(self) -> str:
        if self._active_field() != self.FIELD_TAGS:
            return ""
        item = self._current_selection_item()
        if item is None or item.childCount() <= 0:
            return ""
        return str(item.data(0, Qt.UserRole + 10) or "").strip()

    def _selected_tag_node_kind(self) -> str:
        if self._active_field() != self.FIELD_TAGS:
            return ""
        item = self._current_selection_item()
        if item is None or item.childCount() <= 0:
            return ""
        return str(item.data(0, Qt.UserRole + 11) or "").strip()

    @staticmethod
    def _sanitize_category_prefix(raw_value: str) -> str:
        cleaned = "".join(ch for ch in str(raw_value or "").strip() if ch.isalnum() or ch in {"_", "-"})
        return cleaned

    @classmethod
    def _sanitize_tag_path(cls, raw_value: str) -> str:
        parts = [cls._sanitize_category_prefix(part) for part in str(raw_value or "").strip().split(".")]
        return ".".join(part for part in parts if part)

    def _sync_action_buttons(self) -> None:
        if not hasattr(self, "_rename_button") or not hasattr(self, "_delete_button"):
            return
        selected_count = len(self._selected_labels())
        is_collections = self._active_field() == self.FIELD_COLLECTIONS
        is_astro_twin_presets = self._active_field() == self.FIELD_ASTRO_TWIN_PRESETS
        is_names = self._active_field() == self.FIELD_NAMES
        selected_key = self._selected_key()
        selected_row = self._row_for_key(selected_key)
        can_edit_selected = selected_row is not None and bool(selected_row.get("editable", True))
        tag_category_selected = bool(self._selected_category_prefix())
        rename_enabled = (selected_count == 1 and can_edit_selected) or tag_category_selected
        if is_names:
            rename_enabled = False
        delete_enabled = selected_count >= 1
        if selected_count == 1 and not can_edit_selected:
            delete_enabled = False
        if is_collections:
            delete_enabled = selected_count == 1 and can_edit_selected
        if self._active_field() == self.FIELD_TAGS and tag_category_selected:
            self._rename_button.setText("Rename subcategory" if self._selected_tag_node_kind() == "subcategory" else "Rename category")
        elif self._active_field() == self.FIELD_TAGS and selected_count == 1:
            selected_label = self._selected_label()
            self._rename_button.setText("Rename subcategory" if selected_label.count(".") >= 2 else "Rename tag")
        else:
            self._rename_button.setText("Rename")
        self._rename_button.setEnabled(rename_enabled)
        self._delete_button.setEnabled(delete_enabled)
        self._rename_button.setStyleSheet("" if rename_enabled else INACTIVE_ACTION_BUTTON_STYLE)
        self._delete_button.setStyleSheet("" if delete_enabled else INACTIVE_ACTION_BUTTON_STYLE)
        self._rename_button.setVisible(not is_astro_twin_presets)
        self._delete_button.setVisible(not is_astro_twin_presets)

        if not hasattr(self, "_merge_button"):
            return
        is_tags = self._active_field() == self.FIELD_TAGS
        self._merge_button.setVisible(is_tags)
        self._merge_button.setEnabled(is_tags and len(self._active_rows()) >= 2)
        self._new_button.setVisible(is_collections)
        self._add_selected_button.setVisible(is_collections)
        self._remove_selected_button.setVisible(is_collections)
        can_modify_collection = is_collections and selected_count == 1 and can_edit_selected
        self._add_selected_button.setEnabled(can_modify_collection)
        self._remove_selected_button.setEnabled(can_modify_collection)
        self._add_selected_button.setStyleSheet("" if can_modify_collection else INACTIVE_ACTION_BUTTON_STYLE)
        self._remove_selected_button.setStyleSheet("" if can_modify_collection else INACTIVE_ACTION_BUTTON_STYLE)

    def _reload_usage(
        self,
        *,
        refresh_chart_context: bool = False,
        keep_selection_label: str = "",
    ) -> None:
        if refresh_chart_context and callable(self._refresh_chart_context):
            try:
                self._refresh_chart_context()
            except Exception:
                pass
        try:
            self._usage_data = self._load_usage()
        except Exception as exc:
            QMessageBox.critical(self, "Manage metadata", f"Could not load labels:\n{exc}")
            self._usage_data = {
                self.FIELD_SENTIMENTS: [],
                self.FIELD_RELATIONSHIPS: [],
                self.FIELD_TAGS: [],
                self.FIELD_COLLECTIONS: [],
                self.FIELD_ASTRO_TWIN_PRESETS: [],
                self.FIELD_NAMES: [],
            }
        self._refresh_list()
        if keep_selection_label:
            self._select_label_by_value(keep_selection_label)

    def _select_label_by_value(self, label: str) -> None:
        target_label = str(label or "").strip()
        if not target_label:
            return
        for tree in self._selection_trees():
            iterator = QTreeWidgetItemIterator(tree)
            while iterator.value() is not None:
                item = iterator.value()
                if item is not None and item.childCount() == 0:
                    item_values = (
                        item.data(0, Qt.UserRole + 2),
                        item.data(0, Qt.UserRole + 1),
                        item.data(0, Qt.UserRole),
                    )
                    if target_label in {str(value or "").strip() for value in item_values}:
                        for other_tree in self._selection_trees():
                            if other_tree is not tree:
                                other_tree.clearSelection()
                        tree.clearSelection()
                        tree.setCurrentItem(item)
                        item.setSelected(True)
                        tree.scrollToItem(item)
                        return
                iterator += 1

    def _selection_trees(self) -> list[QTreeWidget]:
        trees = [self._list_widget]
        unsorted_tree = getattr(self, "_unsorted_list_widget", None)
        if isinstance(unsorted_tree, QTreeWidget):
            trees.insert(0, unsorted_tree)
        return trees

    def _refresh_list(self) -> None:
        rows = self._active_rows()
        expanded_state: dict[str, bool] = {}
        if self._active_field() == self.FIELD_TAGS:
            for index in range(self._list_widget.topLevelItemCount()):
                top_level = self._list_widget.topLevelItem(index)
                if top_level is None:
                    continue
                key = str(top_level.data(0, Qt.UserRole + 10) or "").strip()
                if key:
                    expanded_state[key] = top_level.isExpanded()
        self._refreshing_label_views = True
        for tree in self._selection_trees():
            tree.blockSignals(True)
            tree.setCurrentItem(None)
            tree.clearSelection()
            tree.clear()
        if hasattr(self, "_chart_names_list"):
            self._chart_names_list.clear()
        if hasattr(self, "_chart_names_heading"):
            self._chart_names_heading.setText(self._chart_names_heading_text())
        minimum_count = 0
        maximum_count = 0
        if rows:
            counts = [int(row.get("count", 0) or 0) for row in rows]
            minimum_count = min(counts)
            maximum_count = max(counts)
        if self._active_field() == self.FIELD_TAGS:
            node_by_path: dict[str, QTreeWidgetItem] = {}
            node_base_labels: dict[str, str] = {}
            node_chart_memberships: dict[str, set[str]] = {}
            parent_node_path_keys: set[str] = set()
            for row in rows:
                label = str(row.get("label", "")).strip()
                parts = [part.strip() for part in label.split(".") if part.strip()]
                for depth in range(max(len(parts) - 1, 0)):
                    parent_node_path_keys.add(".".join(parts[: depth + 1]).casefold())
            uncategorized_items: list[QTreeWidgetItem] = []

            def node_label_for_path(path: str, part: str, depth: int) -> str:
                if depth == 0:
                    key = path.casefold()
                    display_name = self._tag_category_display_names.get(key)
                    if display_name is None:
                        display_name = next(
                            (name for name, option_prefix in TAG_CATEGORY_OPTIONS if option_prefix.casefold() == key),
                            part.replace("_", " ").replace("-", " ").title(),
                        )
                        self._tag_category_display_names[key] = display_name
                    return display_name
                return part.replace("_", " ").replace("-", " ").title()

            def ensure_node(parts: list[str], depth: int) -> QTreeWidgetItem:
                path = ".".join(parts[: depth + 1])
                key = path.casefold()
                existing = node_by_path.get(key)
                if existing is not None:
                    return existing
                node = QTreeWidgetItem([node_label_for_path(path, parts[depth], depth)])
                node.setData(0, Qt.UserRole + 10, path)
                node.setData(0, Qt.UserRole + 11, "category" if depth == 0 else "subcategory")
                node_by_path[key] = node
                node_base_labels[key] = str(node.text(0))
                if depth == 0:
                    self._list_widget.addTopLevelItem(node)
                else:
                    ensure_node(parts, depth - 1).addChild(node)
                return node

            for row in rows:
                label = str(row.get("label", "")).strip()
                count = int(row.get("count", 0) or 0)
                parts = [part.strip() for part in label.split(".") if part.strip()]
                exact_path_key = ".".join(parts).casefold()
                raw_chart_uids = row.get("chart_uids")
                if isinstance(raw_chart_uids, (list, tuple, set)):
                    chart_memberships = {
                        str(chart_uid).strip().upper()
                        for chart_uid in raw_chart_uids
                        if str(chart_uid).strip()
                    }
                else:
                    # Compatibility for alternate usage providers that only
                    # supply aggregate counts; production rows carry UIDs.
                    chart_memberships = {
                        f"{exact_path_key}:{index}" for index in range(count)
                    }
                if parts and exact_path_key in parent_node_path_keys:
                    # A tag can also be a folder.  Represent it with the folder
                    # node itself rather than adding a second, identically named
                    # leaf beside that node (for example ``Conservative`` and
                    # ``Conservative.Republican``).
                    node = ensure_node(parts, len(parts) - 1)
                    node.setData(0, Qt.UserRole, node_base_labels[exact_path_key])
                    node.setData(0, Qt.UserRole + 1, str(row.get("key", label)))
                    node.setData(0, Qt.UserRole + 2, label)
                    for depth in range(len(parts)):
                        path_key = ".".join(parts[: depth + 1]).casefold()
                        node_chart_memberships.setdefault(path_key, set()).update(chart_memberships)
                    continue
                leaf_value = parts[-1] if parts else label
                display_label = leaf_value.replace("_", " ").replace("-", " ").title()
                item = QTreeWidgetItem([f"{display_label}  ({count} charts)"])
                item.setData(0, Qt.UserRole, display_label)
                item.setData(0, Qt.UserRole + 1, str(row.get("key", label)))
                item.setData(0, Qt.UserRole + 2, label)
                red, green, blue = more_readable_color_scale_rgb_for_range(
                    count,
                    minimum_count,
                    maximum_count,
                )
                item.setForeground(0, QColor(red, green, blue))
                if len(parts) >= 2:
                    parent_parts = parts[:-1]
                    for depth in range(len(parent_parts)):
                        path_key = ".".join(parent_parts[: depth + 1]).casefold()
                        node_chart_memberships.setdefault(path_key, set()).update(chart_memberships)
                    ensure_node(parent_parts, len(parent_parts) - 1).addChild(item)
                else:
                    uncategorized_items.append(item)

            for key, node in node_by_path.items():
                base_label = node_base_labels.get(key, str(node.text(0)))
                chart_count = len(node_chart_memberships.get(key, set()))
                chart_word = "chart" if chart_count == 1 else "charts"
                node.setText(0, f"{base_label} ({chart_count} {chart_word})")
                node.setExpanded(expanded_state.get(str(node.data(0, Qt.UserRole + 10) or ""), False))
            for item in uncategorized_items:
                self._unsorted_list_widget.addTopLevelItem(item.clone())
                self._list_widget.addTopLevelItem(item)
        elif self._active_field() == self.FIELD_ASTRO_TWIN_PRESETS:
            self._list_widget.setColumnCount(3)
            self._list_widget.setHeaderLabels(["Preset Name", "Algorithm", "Data Points"])
            self._list_widget.setHeaderHidden(False)
            for row in rows:
                label = str(row.get("label", "")).strip()
                count = int(row.get("count", 0) or 0)
                item = QTreeWidgetItem([label, "", str(count)])
                item.setData(0, Qt.UserRole, label)
                item.setData(0, Qt.UserRole + 1, str(row.get("key", label)))
                item.setData(0, Qt.UserRole + 2, label)
                item.setData(1, Qt.UserRole, str(row.get("algorithm", "")))
                self._list_widget.addTopLevelItem(item)
            self._list_widget.header().setStretchLastSection(False)
            self._list_widget.header().setSectionResizeMode(QHeaderView.Interactive)
            # The last column stretches into the remaining viewport instead of
            # extending beyond it when the saved/manual widths are too large.
            self._list_widget.header().setSectionResizeMode(2, QHeaderView.Stretch)
            if not self._restore_preset_column_widths():
                self._list_widget.setColumnWidth(0, 180)
                self._list_widget.setColumnWidth(1, 430)
                self._list_widget.setColumnWidth(2, 90)
            try:
                self._list_widget.header().sectionResized.disconnect(
                    self._on_preset_column_resized
                )
            except (RuntimeError, TypeError):
                pass
            self._list_widget.header().sectionResized.connect(
                self._on_preset_column_resized
            )
            QTimer.singleShot(0, self._fit_preset_columns_to_viewport)
        elif self._active_field() == self.FIELD_NAMES:
            self._list_widget.setColumnCount(2)
            self._list_widget.setHeaderLabels(["Name", "Frequency"])
            self._list_widget.setHeaderHidden(False)
            for row in rows:
                label = str(row.get("label", "")).strip()
                count = int(row.get("count", 0) or 0)
                item = QTreeWidgetItem([label, str(count)])
                item.setData(0, Qt.UserRole, label)
                item.setData(0, Qt.UserRole + 1, str(row.get("key", label)))
                item.setData(0, Qt.UserRole + 2, label)
                red, green, blue = more_readable_color_scale_rgb_for_range(
                    count, minimum_count, maximum_count
                )
                item.setForeground(0, QColor(red, green, blue))
                item.setForeground(1, QColor(red, green, blue))
                self._list_widget.addTopLevelItem(item)
            self._list_widget.header().setStretchLastSection(False)
            self._list_widget.header().setSectionResizeMode(0, QHeaderView.Stretch)
            self._list_widget.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        else:
            self._list_widget.setColumnCount(1)
            self._list_widget.setHeaderHidden(True)
            for row in rows:
                label = str(row.get("label", "")).strip()
                count = int(row.get("count", 0) or 0)
                item = QTreeWidgetItem([f"{label}  ({count} charts)"])
                item.setData(0, Qt.UserRole, label)
                item.setData(0, Qt.UserRole + 1, str(row.get("key", label)))
                item.setData(0, Qt.UserRole + 2, label)
                red, green, blue = more_readable_color_scale_rgb_for_range(
                    count,
                    minimum_count,
                    maximum_count,
                )
                item.setForeground(0, QColor(red, green, blue))
                self._list_widget.addTopLevelItem(item)
        tags_mode = self._active_field() == self.FIELD_TAGS
        presets_mode = self._active_field() == self.FIELD_ASTRO_TWIN_PRESETS
        names_mode = self._active_field() == self.FIELD_NAMES
        if not presets_mode and not names_mode:
            self._list_widget.setColumnCount(1)
            self._list_widget.setHeaderHidden(True)
            self._list_widget.header().setStretchLastSection(True)
            self._list_widget.header().setSectionResizeMode(0, QHeaderView.Stretch)
            self._unsorted_list_widget.header().setStretchLastSection(True)
            self._unsorted_list_widget.header().setSectionResizeMode(
                0, QHeaderView.Stretch
            )
        if hasattr(self, "_unsorted_panel_widget"):
            # Only Tags has an uncategorized column. Hiding its containing
            # widget removes that column from the layout entirely, allowing
            # both remaining columns to use the full width in the other
            # managers while preserving Tags' 1:2:1 column proportions.
            self._unsorted_panel_widget.setVisible(tags_mode)
        self._right_panel_widget.setVisible(not presets_mode)
        # Visibility changes affect splitter geometry, so restore on the next
        # event-loop pass after Qt has laid out the active manager columns.
        QTimer.singleShot(0, self._restore_column_widths)
        self._astro_twin_presets_header.setVisible(presets_mode)
        self._astro_twin_algorithm_placeholder.setVisible(presets_mode)
        for tree in self._selection_trees():
            tree.blockSignals(False)
        self._refreshing_label_views = False
        self._on_selection_changed()

    def _selected_label(self) -> str:
        labels = self._selected_labels()
        return labels[0] if labels else ""

    def _selected_labels(self) -> list[str]:
        labels: list[str] = []
        for tree in self._selection_trees():
            for item in tree.selectedItems():
                if item.childCount() > 0:
                    label = str(item.data(0, Qt.UserRole + 10) or "").strip()
                else:
                    label = str(item.data(0, Qt.UserRole + 2) or item.data(0, Qt.UserRole) or "").strip()
                if label:
                    labels.append(label)
        return list(dict.fromkeys(labels))

    def _current_selection_item(self) -> QTreeWidgetItem | None:
        for tree in self._selection_trees():
            if tree.selectedItems():
                return tree.currentItem() or tree.selectedItems()[0]
        return self._list_widget.currentItem()

    def _selected_key(self) -> str:
        item = self._current_selection_item()
        if item is None:
            return ""
        if item.childCount() > 0:
            return str(item.data(0, Qt.UserRole + 10) or "").strip()
        return str(item.data(0, Qt.UserRole + 1) or "").strip()

    def _assign_tags_to_category(self, category_prefix: str, labels: list[str]) -> None:
        if self._active_field() != self.FIELD_TAGS:
            return
        cleaned_prefix = str(category_prefix or "").strip()
        if cleaned_prefix == "__uncategorized__":
            cleaned_prefix = ""
        cleaned_labels = [str(label or "").strip() for label in labels if str(label or "").strip()]
        if not cleaned_labels:
            return

        category_name = next(
            (name for name, prefix in TAG_CATEGORY_OPTIONS if prefix == cleaned_prefix),
            self._tag_category_display_names.get(cleaned_prefix.casefold(), cleaned_prefix or "Uncategorized"),
        )
        if len(cleaned_labels) == 1:
            label = cleaned_labels[0]
            trait_name = label.rsplit(".", 1)[-1]
            subtree = set(self._tag_labels_in_subtree(label))
            entry_count = sum(
                int(row.get("count", 0) or 0)
                for row in self._active_rows()
                if str(row.get("label", "")).strip() in subtree
            )
            prompt = (
                f"Move tag '{trait_name}' and its child tags into '{category_name}' "
                f"({entry_count} {'entry' if entry_count == 1 else 'entries'})?"
            )
        else:
            prompt = f"Assign category '{category_name}' to {len(cleaned_labels)} traits?"
        confirm = QMessageBox.question(
            self,
            "Assign tag category",
            prompt,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        total_occurrences = 0
        total_rows = 0
        changed_count = 0
        label_changes: list[tuple[str, str]] = []
        move_roots = [
            label
            for label in cleaned_labels
            if not any(
                label.casefold().startswith(f"{other.casefold()}.")
                for other in cleaned_labels
                if other != label
            )
        ]
        for label in move_roots:
            if cleaned_prefix.casefold() == label.casefold() or cleaned_prefix.casefold().startswith(
                f"{label.casefold()}."
            ):
                continue
            new_root = _compose_tag_category(cleaned_prefix, label.rsplit(".", 1)[-1])
            for subtree_label in self._tag_labels_in_subtree(label) or [label]:
                suffix = subtree_label[len(label):]
                label_changes.append((subtree_label, f"{new_root}{suffix}"))
        label_changes = list(dict.fromkeys(label_changes))
        for index, (label, updated_label) in enumerate(label_changes):
            if updated_label == label:
                continue
            summary = self._apply_change(
                field=self.FIELD_TAGS,
                old_label=label,
                new_label=updated_label,
                create_backup=index == 0,
            )
            changed_count += 1
            total_occurrences += int(summary.get("occurrences_updated", 0) or 0)
            total_rows += int(summary.get("rows_updated", 0) or 0)
        if changed_count == 0:
            QMessageBox.information(
                self,
                "Assign tag category",
                "No tag category changes were needed.",
            )
            return
        QMessageBox.information(
            self,
            "Assign tag category",
            f"Updated {changed_count} tags across {total_rows} chart(s), "
            f"touching {total_occurrences} tag occurrence(s).",
        )
        self._queue_usage_reload(refresh_chart_context=True)

    def _row_for_key(self, key: str) -> dict[str, object] | None:
        for row in self._active_rows():
            row_key = str(row.get("key", row.get("label", ""))).strip()
            if row_key == key:
                return row
        return None

    def _tag_labels_in_subtree(self, prefix: str) -> list[str]:
        clean_prefix = str(prefix or "").strip()
        prefix_casefold = clean_prefix.casefold()
        if not clean_prefix:
            return []
        return [
            label
            for row in self._active_rows()
            if (label := str(row.get("label", "")).strip())
            and (
                label.casefold() == prefix_casefold
                or label.casefold().startswith(f"{prefix_casefold}.")
            )
        ]

    def _on_selection_changed(self, source_tree: QTreeWidget | None = None) -> None:
        if getattr(self, "_refreshing_label_views", False):
            return
        if source_tree is not None and source_tree.selectedItems():
            for tree in self._selection_trees():
                if tree is not source_tree:
                    tree.blockSignals(True)
                    tree.clearSelection()
                    tree.setCurrentItem(None)
                    tree.blockSignals(False)
        self._sync_action_buttons()
        if self._active_field() == self.FIELD_ASTRO_TWIN_PRESETS:
            for row_index in range(self._list_widget.topLevelItemCount()):
                row_item = self._list_widget.topLevelItem(row_index)
                if row_item is not None:
                    row_item.setText(1, "")
            item = self._current_selection_item()
            if item is not None:
                item.setText(1, str(item.data(1, Qt.UserRole) or ""))
                self._astro_twin_algorithm_placeholder.setVisible(False)
            else:
                self._astro_twin_algorithm_placeholder.setVisible(True)
            return
        self._refresh_chart_names()

    def _refresh_chart_names(self) -> None:
        if getattr(self, "_refreshing_label_views", False):
            return
        self._chart_names_list.clear()
        if not callable(self._load_chart_names):
            return
        selected_label = self._selected_label()
        selected_key = self._selected_key()
        if not selected_label:
            return
        self._chart_names_heading.setText(
            self._selected_chart_names_heading_text(selected_label)
        )
        try:
            chart_names = self._load_chart_names(self._active_field(), selected_label, selected_key)
        except Exception:
            chart_names = []
        for chart_result in chart_names:
            is_direct_tag_match = False
            if isinstance(chart_result, tuple):
                chart_name, is_direct_tag_match = chart_result
            else:
                chart_name = chart_result
            clean_name = str(chart_name).strip()
            if clean_name:
                item = QListWidgetItem(clean_name)
                if self._active_field() == self.FIELD_TAGS and is_direct_tag_match:
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)
                self._chart_names_list.addItem(item)

    def _delete_selected(self) -> None:
        if self._active_field() == self.FIELD_COLLECTIONS:
            self._delete_selected_collection()
            return
        old_labels = self._selected_labels()
        if self._active_field() == self.FIELD_TAGS:
            expanded_labels: list[str] = []
            for old_label in old_labels:
                subtree_labels = self._tag_labels_in_subtree(old_label)
                expanded_labels.extend(subtree_labels or [old_label])
            old_labels = list(dict.fromkeys(expanded_labels))
        if not old_labels:
            QMessageBox.information(self, "Manage metadata", "Select one or more labels to delete.")
            return
        if self._active_field() == self.FIELD_NAMES:
            preview = ", ".join(old_labels[:6])
            if len(old_labels) > 6:
                preview += f", +{len(old_labels) - 6} more"
            confirm = QMessageBox.question(
                self,
                "Suppress names",
                "Stop treating the selected value(s) as names?\n\n"
                f"{preview}\n\nChart names and aliases will not be edited.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if confirm != QMessageBox.Yes:
                return
            suppressed = 0
            for old_label in old_labels:
                summary = self._apply_change(
                    field=self.FIELD_NAMES,
                    old_label=old_label,
                    new_label="",
                    create_backup=False,
                )
                suppressed += int(summary.get("occurrences_updated", 0) or 0)
            QMessageBox.information(
                self,
                "Names suppressed",
                f"Suppressed {suppressed} name {'value' if suppressed == 1 else 'values'}. "
                "Chart metadata was not changed.",
            )
            self._queue_usage_reload(refresh_chart_context=True)
            return
        if len(old_labels) == 1:
            confirm_message = (
                f"Delete '{old_labels[0]}' from all charts?\n\n"
                "This cannot be undone except by restoring a backup."
            )
            confirm_title = "Delete label"
        else:
            preview = ", ".join(old_labels[:6])
            if len(old_labels) > 6:
                preview += f", +{len(old_labels) - 6} more"
            confirm_message = (
                f"Delete {len(old_labels)} labels from all charts?\n\n"
                f"{preview}\n\n"
                "This cannot be undone except by restoring a backup."
            )
            confirm_title = "Delete labels"
        confirm = QMessageBox.question(
            self,
            confirm_title,
            confirm_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        total_occurrences = 0
        total_rows = 0
        for index, old_label in enumerate(old_labels):
            summary = self._apply_change(
                field=self._active_field(),
                old_label=old_label,
                new_label="",
                create_backup=index == 0,
            )
            total_occurrences += int(summary.get("occurrences_updated", 0) or 0)
            total_rows += int(summary.get("rows_updated", 0) or 0)

        QMessageBox.information(
            self,
            "Delete complete",
            f"Removed {total_occurrences} occurrences across {total_rows} chart updates.",
        )
        self._queue_usage_reload(refresh_chart_context=True)

    def _rename_tag_category_display_name(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._active_field() != self.FIELD_TAGS or item is None or item.childCount() <= 0:
            return
        prefix = str(item.data(0, Qt.UserRole + 10) or "").strip()
        if not prefix or prefix == "__uncategorized__":
            return
        if str(item.data(0, Qt.UserRole + 11) or "") != "category":
            return
        current_name = self._tag_category_display_names.get(prefix.casefold(), prefix)
        editor = _RenameLabelDialog(
            parent=self,
            title="Rename category display name",
            old_label=current_name,
            max_length=self._label_limit,
        )
        if editor.exec() != QDialog.Accepted:
            return
        new_name = editor.value()
        if new_name:
            self._tag_category_display_names[prefix.casefold()] = new_name
            self._save_tag_category_display_names()
            self._queue_usage_reload()

    def _rename_selected(self) -> None:
        if self._active_field() == self.FIELD_COLLECTIONS:
            self._rename_selected_collection()
            return
        category_prefix = self._selected_category_prefix()
        if category_prefix:
            self._rename_selected_tag_category(category_prefix)
            return
        item = self._current_selection_item()
        old_label = (
            str(item.data(0, Qt.UserRole + 2) or item.data(0, Qt.UserRole) or "").strip()
            if item is not None
            else self._selected_label()
        )
        if not old_label:
            QMessageBox.information(self, "Manage metadata", "Select a label to rename.")
            return

        editor = _RenameLabelDialog(
            parent=self,
            title="Rename label",
            old_label=old_label,
            max_length=self._label_limit,
        )
        if editor.exec() != QDialog.Accepted:
            return

        new_label = editor.value()
        if not new_label:
            QMessageBox.warning(self, "Manage metadata", "New label cannot be empty.")
            return
        if new_label == old_label:
            return

        summary = self._apply_change(
            field=self._active_field(),
            old_label=old_label,
            new_label=new_label,
        )
        QMessageBox.information(
            self,
            "Rename complete",
            f"Updated {summary.get('occurrences_updated', 0)} occurrences across "
            f"{summary.get('rows_updated', 0)} chart(s).",
        )
        self._queue_usage_reload(
            refresh_chart_context=True,
            keep_selection_label=new_label,
        )

    def _rename_selected_tag_category(self, old_prefix: str) -> None:
        cleaned_old_prefix = str(old_prefix or "").strip().strip(".")
        if not cleaned_old_prefix:
            return
        is_subcategory = "." in cleaned_old_prefix
        title = "Rename tag subcategory" if is_subcategory else "Rename tag category"
        editor = _RenameLabelDialog(
            parent=self,
            title=title,
            old_label=cleaned_old_prefix,
            max_length=self._label_limit,
        )
        if editor.exec() != QDialog.Accepted:
            return
        new_prefix = self._sanitize_tag_path(editor.value())
        if not new_prefix:
            QMessageBox.warning(
                self,
                "Manage metadata",
                "Tag category paths must contain letters, numbers, underscores, dashes, and optional periods.",
            )
            return
        if new_prefix.casefold() == cleaned_old_prefix.casefold():
            return
        if new_prefix.casefold().startswith(f"{cleaned_old_prefix.casefold()}."):
            QMessageBox.warning(
                self,
                title,
                "A tag category cannot be renamed into one of its own child paths.",
            )
            return

        affected_labels: list[tuple[str, str]] = []
        old_prefix_casefold = cleaned_old_prefix.casefold()
        for row in self._active_rows():
            original_label = str(row.get("label", "")).strip()
            original_casefold = original_label.casefold()
            if original_casefold == old_prefix_casefold:
                affected_labels.append((original_label, new_prefix))
            elif original_casefold.startswith(f"{old_prefix_casefold}."):
                suffix = original_label[len(cleaned_old_prefix):].lstrip(".")
                if suffix:
                    affected_labels.append((original_label, f"{new_prefix}.{suffix}"))
        if not affected_labels:
            QMessageBox.information(self, title, "No tags found in that category path.")
            return
        confirm = QMessageBox.question(
            self,
            title,
            f"Rename '{cleaned_old_prefix}.[…]' to '{new_prefix}.[…]' for {len(affected_labels)} tags?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return
        total_occurrences = 0
        total_rows = 0
        for index, (old_label, new_label) in enumerate(affected_labels):
            summary = self._apply_change(
                field=self.FIELD_TAGS,
                old_label=old_label,
                new_label=new_label,
                create_backup=index == 0,
            )
            total_occurrences += int(summary.get("occurrences_updated", 0) or 0)
            total_rows += int(summary.get("rows_updated", 0) or 0)
        if not is_subcategory:
            old_display_name = self._tag_category_display_names.pop(cleaned_old_prefix.casefold(), None)
            if old_display_name:
                self._tag_category_display_names[new_prefix.casefold()] = old_display_name
            self._save_tag_category_display_names()
        QMessageBox.information(
            self,
            "Rename complete",
            f"Updated {len(affected_labels)} tags across {total_rows} chart(s), "
            f"touching {total_occurrences} tag occurrence(s).",
        )
        self._queue_usage_reload(refresh_chart_context=True)

    def _create_collection(self) -> None:
        action = self._collection_actions.get("create")
        if not callable(action):
            return
        action()
        self._queue_usage_reload(refresh_chart_context=True)

    def _rename_selected_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("rename")
        if not key or not callable(action):
            return
        action(key)
        self._queue_usage_reload(refresh_chart_context=True, keep_selection_label=key)

    def _delete_selected_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("delete")
        if not key or not callable(action):
            return
        action(key)
        self._queue_usage_reload(refresh_chart_context=True)

    def _add_selected_to_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("add_selected")
        if not key or not callable(action):
            return
        action(key)
        self._queue_usage_reload(refresh_chart_context=True, keep_selection_label=key)

    def _remove_selected_from_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("remove_selected")
        if not key or not callable(action):
            return
        action(key)
        self._queue_usage_reload(refresh_chart_context=True, keep_selection_label=key)

    # def _delete_selected(self) -> None:
    #     old_label = self._selected_label()
    #     if not old_label:
    #         QMessageBox.information(self, "Manage metadata", "Select a label to delete.")
    #         return
    #     confirm = QMessageBox.question(
    #         self,
    #         "Delete label",
    #         f"Delete '{old_label}' from all charts?\n\nThis cannot be undone except by restoring a backup.",
    #         QMessageBox.Yes | QMessageBox.No,
    #         QMessageBox.Yes,
    #     )
    #     if confirm != QMessageBox.Yes:
    #         return

    #     summary = self._apply_change(
    #         field=self._active_field(),
    #         old_label=old_label,
    #         new_label="",
    #     )
    #     QMessageBox.information(
    #         self,
    #         "Delete complete",
    #         f"Removed {summary.get('occurrences_updated', 0)} occurrences across "
    #         f"{summary.get('rows_updated', 0)} chart(s).",
    #     )
    #     self._reload_usage()

    def _merge_selected_tags(self) -> None:
        if self._active_field() != self.FIELD_TAGS:
            return

        rows = self._active_rows()
        choices: list[tuple[str, int]] = []
        for row in rows:
            label = str(row.get("label", "")).strip()
            if not label:
                continue
            count = int(row.get("count", 0) or 0)
            choices.append((label, count))
        if len(choices) < 2:
            QMessageBox.information(
                self,
                "Merge tags",
                "Need at least two tags to merge.",
            )
            return

        picker = _MergeLabelsDialog(
            parent=self,
            title="Merge tags",
            choices=choices,
            default_consolidate=self._selected_label(),
        )
        if picker.exec() != QDialog.Accepted:
            return

        consolidate_label, into_label = picker.values()
        if not consolidate_label or not into_label:
            QMessageBox.warning(self, "Merge tags", "Select both tags before merging.")
            return
        if consolidate_label == into_label:
            QMessageBox.warning(self, "Merge tags", "Consolidate and Into tags must be different.")
            return

        summary = self._apply_change(
            field=self.FIELD_TAGS,
            old_label=consolidate_label,
            new_label=into_label,
        )
        QMessageBox.information(
            self,
            "Merge complete",
            f"Merged '{consolidate_label}' into '{into_label}'.\n\n"
            f"Updated {summary.get('occurrences_updated', 0)} occurrences across "
            f"{summary.get('rows_updated', 0)} chart(s).",
        )
        self._queue_usage_reload(
            refresh_chart_context=True,
            keep_selection_label=into_label,
        )

ENNEAGRAM_CATEGORY_FACTOR_ROWS: tuple[tuple[str, str], ...] = (
    ("signs", "Signs"),
    ("bodies", "Bodies"),
    ("nakshatras", "Nakshatras"),
    ("houses", "Houses"),
    ("gates", "HD Gates"),
    ("hdtypes", "HD Types"),
    ("centers", "HD Centers"),
    ("profiles", "HD Profiles"),
    ("authorities", "HD Authorities"),
    ("bazisigns", "BaZi Signs"),
    ("positions", "Positions"),
    ("aspects", "Aspects"),
)

def build_predictions_settings_section(
    *,
    dialog: QDialog,
    section_layout: QVBoxLayout,
    subheader_style: str,
    on_option_toggled: Callable[[str, bool], None],
    on_score_mode_changed: Callable[[str], None],
    on_scale_mode_changed: Callable[[str], None],
    on_dominance_normalization_mode_changed: Callable[[str], None],
    on_manual_recalculation_toggled: Callable[[bool], None] | None = None,
    on_ocean_enabled_toggled: Callable[[str, bool], None] | None = None,
    on_ocean_weight_changed: Callable[[str, float], None] | None = None,
) -> dict[str, object]:
    label = QLabel("Predictions")
    label.setStyleSheet(subheader_style)
    section_layout.addWidget(label)
    description = _build_settings_help_label(
        "Configure how Predictions criteria are scored. Property categories are used only "
        "to parse criteria, not as independent score multipliers."
    )
    #description.setWordWrap(True)
    section_layout.addWidget(description)

    behavior_label = QLabel("Scoring behavior")
    behavior_label.setStyleSheet(subheader_style)
    section_layout.addWidget(behavior_label)

    checkbox_rows = (
        (
            "use_direct_dominance_activation",
            "Use dominance activation for direct dominance criteria",
            "When enabled, sign/body/house/nakshatra criteria are multiplied by the chart's normalized dominance weight.",
        ),
        (
            "use_position_dominance_weighting",
            "Use dominance weighting for position criteria",
            "When enabled, matching positions are multiplied by relevant body/sign/house dominance modifiers.",
        ),
        (
            "use_aspect_dominance_weighting",
            "Use dominance/base weighting for aspect criteria",
            "When enabled, matching aspects use body dominance plus the existing aspect base weight; disabled uses orb quality.",
        ),
        (
            "simplify_anti_factor_handling",
            "Simplify anti-factor handling",
            "When enabled, positive evidence adds directly and anti evidence subtracts directly after anti-factor scaling.",
        ),
        (
            "average_scores_by_criterion_count",
            "Average scores by criterion count",
            "Experimental: divide each category's evidence by its criterion count. Disabled by default.",
        ),
        (
            "use_mutual_exclusive_bucket_scoring",
            "Use mutual-exclusive bucket scoring",
            "Treat singleton fields such as body sign/house, HD type, profile, and authority as one bucket instead of many independent opportunities.",
        ),
    )
    checkboxes: dict[str, QCheckBox] = {}
    for key, title, tooltip in checkbox_rows:
        checkbox = QCheckBox(title)
        checkbox.setToolTip(tooltip)
        checkbox.toggled.connect(lambda checked, option_key=key: on_option_toggled(option_key, bool(checked)))
        section_layout.addWidget(checkbox)
        checkboxes[key] = checkbox

    manual_recalculation_checkbox = QCheckBox("manual recalculation/refresh only (vs automatic)")
    manual_recalculation_checkbox.setToolTip(
        "When enabled, Chart Editor Predictions always show the most recent saved results for the chart UID "
        "and only refresh after you click Calculate/Recalculate."
    )
    if on_manual_recalculation_toggled is not None:
        manual_recalculation_checkbox.toggled.connect(
            lambda checked: on_manual_recalculation_toggled(bool(checked))
        )
    section_layout.addWidget(manual_recalculation_checkbox)

    ocean_label = QLabel("OCEAN Predictor")
    ocean_label.setStyleSheet(subheader_style)
    section_layout.addWidget(ocean_label)
    section_layout.addWidget(
        _build_settings_help_label(
            "Choose which astrological evidence contributes to OCEAN Prediction and adjust "
            "each category's percentage weighting. Available enabled weights are normalized at calculation time."
        )
    )
    ocean_grid = QGridLayout()
    ocean_grid.addWidget(QLabel("Use"), 0, 0, alignment=Qt.AlignCenter)
    ocean_grid.addWidget(QLabel("Scoring category"), 0, 1)
    ocean_grid.addWidget(QLabel("Contribution"), 0, 2)
    ocean_grid.addWidget(QLabel("Total"), 0, 3, alignment=Qt.AlignCenter)
    ocean_checkboxes: dict[str, QCheckBox] = {}
    ocean_weight_spinboxes: dict[str, QDoubleSpinBox] = {}
    ocean_total_label = QLabel("0.0%/100.0%")
    ocean_total_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
    ocean_grid.addWidget(
        ocean_total_label,
        1,
        3,
        len(OCEAN_WEIGHT_ROWS),
        1,
        alignment=Qt.AlignCenter | Qt.AlignTop,
    )
    for row, (key, title, default_weight) in enumerate(OCEAN_WEIGHT_ROWS, start=1):
        checkbox = QCheckBox()
        checkbox.setAccessibleName(title)
        checkbox.setChecked(True)
        checkbox.setStyleSheet(SIMILARITY_CALCULATOR_CHECKBOX_STYLE)
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.0, 100.0)
        spinbox.setDecimals(1)
        spinbox.setSingleStep(1.0)
        spinbox.setSuffix("%")
        spinbox.setValue(default_weight)
        if on_ocean_enabled_toggled is not None:
            checkbox.toggled.connect(
                lambda checked, category=key: on_ocean_enabled_toggled(category, bool(checked))
            )
        if on_ocean_weight_changed is not None:
            spinbox.valueChanged.connect(
                lambda value, category=key: on_ocean_weight_changed(category, float(value))
            )
        ocean_grid.addWidget(checkbox, row, 0, alignment=Qt.AlignCenter)
        ocean_grid.addWidget(QLabel(title), row, 1)
        ocean_grid.addWidget(spinbox, row, 2)
        ocean_checkboxes[key] = checkbox
        ocean_weight_spinboxes[key] = spinbox

    def update_ocean_weight_constraints(*_args) -> None:
        update_percentage_weight_constraints(
            ocean_checkboxes, ocean_weight_spinboxes, ocean_total_label
        )

    for checkbox in ocean_checkboxes.values():
        checkbox.toggled.connect(update_ocean_weight_constraints)
    for spinbox in ocean_weight_spinboxes.values():
        spinbox.valueChanged.connect(update_ocean_weight_constraints)
    update_ocean_weight_constraints()
    section_layout.addLayout(ocean_grid)

    advanced_label = QLabel("Advanced")
    advanced_label.setStyleSheet(subheader_style)
    section_layout.addWidget(advanced_label)

    score_mode_row = QHBoxLayout()
    score_mode_row.addWidget(QLabel("Prediction score mode:"))
    score_mode_combo = QComboBox()
    for value, title in (
        ("raw", "raw weighted"),
        ("opportunity", "type opportunity"),
        ("background_z", "background z-score"),
        ("category_z", "category z-score"),
    ):
        score_mode_combo.addItem(title, value)
    score_mode_combo.setToolTip(
        "Select raw scores, opportunity-scaled scores, database background z-scores, or category z-score combination when background stats are available."
    )
    score_mode_combo.currentIndexChanged.connect(
        lambda _idx: on_score_mode_changed(str(score_mode_combo.currentData() or "opportunity"))
    )
    apply_shared_dropdown_style(score_mode_combo)
    score_mode_row.addWidget(score_mode_combo)
    score_mode_row.addStretch(1)
    section_layout.addLayout(score_mode_row)

    scale_row = QHBoxLayout()
    scale_row.addWidget(QLabel("Type signature scale adjustment:"))
    scale_combo = QComboBox()
    for value, title in (
        ("none", "none"),
        ("log", "log"),
        ("sqrt", "sqrt"),
        ("full", "full"),
    ):
        scale_combo.addItem(title, value)
    scale_combo.currentIndexChanged.connect(lambda _idx: on_scale_mode_changed(str(scale_combo.currentData() or "none")))
    apply_shared_dropdown_style(scale_combo)
    scale_row.addWidget(scale_combo)
    scale_row.addStretch(1)
    section_layout.addLayout(scale_row)

    dominance_row = QHBoxLayout()
    dominance_row.addWidget(QLabel("Dominance normalization:"))
    dominance_combo = QComboBox()
    for value, title in (
        ("range", "range"),
        ("share", "share"),
    ):
        dominance_combo.addItem(title, value)
    dominance_combo.setToolTip(
        "range normalizes each dominance map to 0..1; share treats active dominance values as shares of the total."
    )
    dominance_combo.currentIndexChanged.connect(
        lambda _idx: on_dominance_normalization_mode_changed(str(dominance_combo.currentData() or "range"))
    )
    apply_shared_dropdown_style(dominance_combo)
    dominance_row.addWidget(dominance_combo)
    dominance_row.addStretch(1)
    section_layout.addLayout(dominance_row)

    return {
        "checkboxes": checkboxes,
        "manual_recalculation_checkbox": manual_recalculation_checkbox,
        "score_mode_combo": score_mode_combo,
        "scale_combo": scale_combo,
        "dominance_combo": dominance_combo,
        "weight_spinboxes": {},
        "total_label": QLabel("disabled"),
        "ocean_checkboxes": ocean_checkboxes,
        "ocean_weight_spinboxes": ocean_weight_spinboxes,
        "ocean_total_label": ocean_total_label,
        "update_ocean_weight_constraints": update_ocean_weight_constraints,
    }


# Backward-compatible alias for callers/tests that still use the old Enneagram-specific name.
build_enneagram_predictor_settings_section = build_predictions_settings_section
