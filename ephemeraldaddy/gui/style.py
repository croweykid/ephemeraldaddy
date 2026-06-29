"""Shared GUI styling and interface constants."""
from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    #QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QSize,
    QTimer,
    Qt,
    #QVariantAnimation,
)
from PySide6.QtGui import QFont, QIcon#, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QComboBox,
    #QGraphicsOpacityEffect,
    #QLabel,
    QListView,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)


# Shared cursor policy. Keep these constants and helpers as the single source of
# truth for clickable UI affordances across Chart View, Database View, popouts,
# and utility panels.
APP_CHART_INFO_LINK_CURSOR = Qt.WhatsThisCursor
APP_POPOUT_CURSOR = Qt.PointingHandCursor
APP_BUTTON_CURSOR = Qt.PointingHandCursor


def apply_chart_info_link_cursor(widget: QWidget) -> None:
    """Use the appwide question cursor for links that open Chart Info details."""
    widget.setCursor(APP_CHART_INFO_LINK_CURSOR)


def apply_popout_cursor(widget: QWidget) -> None:
    """Use the appwide pointing-hand cursor for clickable charts/popout targets."""
    widget.setCursor(APP_POPOUT_CURSOR)


def apply_button_cursor(button: QAbstractButton) -> None:
    """Use the appwide pointing-hand cursor for clickable buttons."""
    button.setCursor(APP_BUTTON_CURSOR)


class _AppwideCursorDefaultsFilter(QObject):
    """Apply shared cursor defaults to widgets created after QApplication setup."""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() in (QEvent.ChildAdded, QEvent.Show):
            self._apply_to_object(watched)
        return super().eventFilter(watched, event)

    def _apply_to_object(self, obj: QObject) -> None:
        if isinstance(obj, QAbstractButton):
            apply_button_cursor(obj)
        for child in obj.findChildren(QAbstractButton):
            apply_button_cursor(child)


def install_appwide_cursor_defaults(app: QApplication) -> None:
    """Install appwide cursor defaults for standard interactive widgets."""
    if getattr(app, "_edd_appwide_cursor_defaults_installed", False):
        return
    cursor_filter = _AppwideCursorDefaultsFilter(app)
    app.installEventFilter(cursor_filter)
    app._edd_appwide_cursor_defaults_filter = cursor_filter  # type: ignore[attr-defined]
    app._edd_appwide_cursor_defaults_installed = True  # type: ignore[attr-defined]
    cursor_filter._apply_to_object(app)


# Appwide widget styling shared by Chart View, Database View, and utility panels.
# Keep text-entry controls charcoal instead of pure black so field boundaries stay
# visible against the dark application background.
APPWIDE_TEXT_INPUT_BACKGROUND_COLOR = "#222222"
APPWIDE_TEXT_INPUT_BORDER_COLOR = "#444444"
APPWIDE_BUTTON_BACKGROUND_COLOR = "#333333"
APPWIDE_BUTTON_HOVER_BACKGROUND_COLOR = "#444444"
APPWIDE_BUTTON_BORDER_COLOR = "#555555"
APPWIDE_PLAIN_TEXT_INPUT_BACKGROUND_COLOR = "#181818"

APPWIDE_DARK_THEME_STYLESHEET = f"""
QMainWindow {{
    background-color: #111111;
}}
QWidget {{
    color: #f5f5f5;
    background-color: #111111;
    font-size: 13px;
}}
QLineEdit, QDateEdit, QTimeEdit, QTextEdit, QPlainTextEdit {{
    background-color: {APPWIDE_TEXT_INPUT_BACKGROUND_COLOR};
    border: 1px solid {APPWIDE_TEXT_INPUT_BORDER_COLOR};
    padding: 4px;
}}
QPushButton {{
    background-color: {APPWIDE_BUTTON_BACKGROUND_COLOR};
    border: 1px solid {APPWIDE_BUTTON_BORDER_COLOR};
    padding: 6px 10px;
}}
QPushButton:hover {{
    background-color: {APPWIDE_BUTTON_HOVER_BACKGROUND_COLOR};
}}
QPlainTextEdit {{
    background-color: {APPWIDE_PLAIN_TEXT_INPUT_BACKGROUND_COLOR};
}}
"""

DARK_THEME = {
    "background": "#111111",
    "foreground": "#f5f5f5",
    "wheel_circle": "#444444",
    "house_line": "#333333",
    "planet": "#f1d28f",
}

CHART_THEME_COLORS = {
    "background": "#111111",
    "text": "#f5f5f5",
    "muted_text": "#8b8b8b",
    "spine": "#444444",
    "accent": "#6fa8dc",
}

# Shared Chart Data Output separator styling. This is intentionally a visual-only
# ghost for existing whitespace between padded table columns: the underlying
# plain text remains unchanged so fixed-width column positions do not shift.
SEPARATOR_STYLE = {
    "character": ".",
    "color": "#555555",
    "minimum_space_run": 2,
}

GENDER_GUESSER_COLORS = {
    "masculine": "#f16464",
    "feminine": "#7bdb7b",
    "androgynous": "#ffd966",
}

MIDDLE_PANEL_ACCENT_COLOR = "#c8914f"
CHART_DATA_HIGHLIGHT_COLOR = MIDDLE_PANEL_ACCENT_COLOR


EARTH_TONE_COLOR_CYCLE = (
    "#7b5b45",  # clay brown
    "#8f7a5a",  # tan umber
    "#6e7f52",  # muted olive
    "#8d5f4d",  # terracotta
    "#6a6d58",  # moss gray
    "#a07855",  # saddle
    "#7a6a4f",  # bark
    "#8c735d",  # warm taupe
    "#5f6b4f",  # forest dust
)


def get_cycled_earthtone_colors(count: int) -> list[str]:
    """Return `count` colors cycling through the shared 9-color earthtone palette."""
    total = max(0, int(count))
    palette_size = len(EARTH_TONE_COLOR_CYCLE)
    if total == 0 or palette_size == 0:
        return []
    return [EARTH_TONE_COLOR_CYCLE[index % palette_size] for index in range(total)]


CHART_HEADER_TEMPLATES = {
    "name_alias": "Name: {name} | Alias: {alias}",
    "date_times": "Date: {date} | Official Time: {official_time} | Retcon Time: {retcon_time}",
    "place": "Place: {birth_place} | {lat:.4f}, {lon:.4f}",
    "when_where": "When/Where: {date} @ {time} {timezone} | {location}, {lat:.4f}, {lon:.4f}",
    "when_where_compact": "When/Where: {date_time} | {lat:.4f}, {lon:.4f}",
}


CHART_AXES_STYLE = {
    "y_tick": {"labelsize": 7.5, "colors": CHART_THEME_COLORS["text"], "pad": 6},
    "x_tick": {"labelsize": 7, "colors": CHART_THEME_COLORS["muted_text"]},
    "barh_adjust": {"left": 0.36, "bottom": 0.12, "right": 0.97, "top": 0.96},
}

# Alignment-score visualization tuning.
ALIGNMENT_SCORE_RANGE = (-10.0, 10.0)
ALIGNMENT_NEGATIVE_RGB = (100, 0, 0)
ALIGNMENT_POSITIVE_RGB = (0, 0, 100)
ALIGNMENT_CUMULATIVE_SUBTITLE_WRAP_WIDTH = 44
SIMILARITY_GRADIENT_MIN_RED = 140
SIMILARITY_GRADIENT_MAX_GREEN = 255


def _interpolate_rgb_channel(start: int, end: int, ratio: float) -> int:
    return int(round(start + ((end - start) * ratio)))


def alignment_score_to_rgb(value: float) -> tuple[float, float, float]:
    """
    Map alignment scores to an RGB gradient:
    - most negative -> red (100, 0, 0)
    - most positive -> blue (0, 0, 100)
    """
    min_value, max_value = ALIGNMENT_SCORE_RANGE
    clamped = max(min_value, min(max_value, float(value)))
    ratio = (clamped - min_value) / (max_value - min_value) if max_value > min_value else 0.5
    red = _interpolate_rgb_channel(ALIGNMENT_NEGATIVE_RGB[0], ALIGNMENT_POSITIVE_RGB[0], ratio)
    green = _interpolate_rgb_channel(ALIGNMENT_NEGATIVE_RGB[1], ALIGNMENT_POSITIVE_RGB[1], ratio)
    blue = _interpolate_rgb_channel(ALIGNMENT_NEGATIVE_RGB[2], ALIGNMENT_POSITIVE_RGB[2], ratio)
    return (red / 100.0, green / 100.0, blue / 100.0)


def value_to_red_blue_rgb(
    value: float,
    min_value: float,
    max_value: float,
) -> tuple[float, float, float]:
    """Map any scalar value to the shared red→blue gradient for a numeric range."""
    if max_value > min_value:
        ratio = (float(value) - float(min_value)) / (float(max_value) - float(min_value))
    else:
        ratio = 0.5
    clamped_ratio = max(0.0, min(1.0, ratio))
    red = _interpolate_rgb_channel(
        ALIGNMENT_NEGATIVE_RGB[0],
        ALIGNMENT_POSITIVE_RGB[0],
        clamped_ratio,
    )
    green = _interpolate_rgb_channel(
        ALIGNMENT_NEGATIVE_RGB[1],
        ALIGNMENT_POSITIVE_RGB[1],
        clamped_ratio,
    )
    blue = _interpolate_rgb_channel(
        ALIGNMENT_NEGATIVE_RGB[2],
        ALIGNMENT_POSITIVE_RGB[2],
        clamped_ratio,
    )
    return (red / 100.0, green / 100.0, blue / 100.0)


def similarity_gradient_rgb_from_ratio(ratio: float) -> tuple[int, int, int]:
    """
    Shared dark-red -> bright-green scale used by Similarities UI elements.

    Ratio is clamped into [0.0, 1.0]:
    - 0.0 => medium-dark red floor
    - 1.0 => bright green
    """
    clamped = max(0.0, min(1.0, float(ratio)))
    red = int(round(SIMILARITY_GRADIENT_MIN_RED * (1.0 - clamped)))
    green = int(round(SIMILARITY_GRADIENT_MAX_GREEN * clamped))
    return (red, green, 0)


def similarity_gradient_rgb_for_range(
    value: float,
    minimum: float,
    maximum: float,
) -> tuple[int, int, int]:
    """Map a value in [minimum, maximum] onto the shared similarity red->green scale."""
    if maximum > minimum:
        ratio = (float(value) - float(minimum)) / (float(maximum) - float(minimum))
    else:
        ratio = 0.0
    return similarity_gradient_rgb_from_ratio(ratio)


def format_chart_header(template_key: str, **kwargs: object) -> str:
    """Format a standard chart header line using the shared template catalog."""
    return CHART_HEADER_TEMPLATES[template_key].format(**kwargs)

TRISTATE_SENTIMENT_STYLE = """
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:indeterminate {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16'><rect width='16' height='16' rx='2' ry='2' fill='%23cc0000'/><path d='M4 4 L12 12 M12 4 L4 12' stroke='white' stroke-width='2' stroke-linecap='round'/></svg>");
}
"""

QUAD_STATE_SLIDER_VISUALS = {
    "true": {
        "text": "✓",
        "style": "background: #19391f; color: #4de06c; border: 1px solid #2d6a38;",
        "tooltip": "All selected charts have this property.",
    },
    "false": {
        "text": "✕",
        "style": "background: #3a1717; color: #ff6b6b; border: 1px solid #7b2d2d;",
        "tooltip": "All selected charts are set negative for this property.",
    },
    "mixed": {
        "text": "–",
        "style": "background: #2b2b2b; color: #b0b0b0; border: 1px solid #5a5a5a;",
        "tooltip": "Selection has mixed values for this property.",
    },
    "empty": {
        "text": "",
        "style": "background: #111; color: #ddd; border: 1px solid #444;",
        "tooltip": "No value set.",
    },
}

RIGHT_PANEL_SCROLLBAR_STYLE = """
QScrollArea {
    border: none;
    background: #111111;
}
QScrollArea::viewport {
    background: #111111;
}
QScrollBar:vertical {
    background: #240046;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #3c096c;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #5a189a;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    background: #240046;
    height: 0px;
    width: 0px;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: #240046;
}
QScrollBar:horizontal {
    background: #240046;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #3c096c;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #5a189a;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: #240046;
    height: 0px;
    width: 0px;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: #240046;
}
"""

DEFAULT_DROPDOWN_STYLE = """
QComboBox {
    background-color: #1c1c1c;
    alternate-background-color: #1c1c1c;
    color: __CHART_DATA_HIGHLIGHT_COLOR__;
    border: 1px solid #3f3f3f;
    border-radius: 4px;
    padding: 3px 2px;
    min-height: 24px;
    combobox-popup: 1;
}
QComboBox::drop-down {
    background-color: transparent;
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background-color: #1c1c1c;
    alternate-background-color: #1c1c1c;
    selection-background-color: #4f3f25;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    padding: 3px 2px 3px 2px;
    margin: 0px;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #4f3f25;
    color: __CHART_DATA_HIGHLIGHT_COLOR__;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #6a532d;
    color: #fff2d8;
}
QComboBox QAbstractItemView::item:checked {
    background-color: #4f3f25;
    color: __CHART_DATA_HIGHLIGHT_COLOR__;
}
QComboBox QAbstractItemView::item:checked:hover {
    background-color: #6a532d;
    color: #fff2d8;
}
QComboBox QAbstractItemView::indicator {
    width: 0px;
    height: 0px;
    margin: 0px;
    padding: 0px;
}
""".replace("__CHART_DATA_HIGHLIGHT_COLOR__", CHART_DATA_HIGHLIGHT_COLOR)

WINDOW_CHROME_MENU_STYLE = """
QMenu {
    background-color: #1c1c1c;
    color: #f0f0f0;
    border: 1px solid #2a2a2a;
}
QMenu::item {
    background-color: transparent;
    padding: 4px 12px;
}
QMenu::item:selected {
    background-color: #6a532d;
    color: #fff2d8;
}
QMenu::item:checked {
    background-color: #4f3f25;
    color: #f6ead1;
}
QMenu::item:checked:selected {
    background-color: #6a532d;
    color: #fff2d8;
}
QMenu::indicator {
    width: 0px;
    height: 0px;
}
QMenu::separator {
    background: #2a2a2a;
    height: 1px;
    margin: 4px 10px;
}
"""

INACTIVE_ACTION_BUTTON_STYLE = """
QPushButton {
    background-color: #2b2b2b;
    color: #b8b8b8;
    border: 1px solid #3a3a3a;
}
"""

SIMILARITY_CALCULATE_BUTTON_ACTIVE_STYLE = """
QPushButton {
    background-color: #1f3a1f;
    color: #c6f7c6;
    border: 1px solid #2f6130;
    padding: 4px 10px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #274b27;
}
"""

SIMILARITY_CALCULATE_BUTTON_INACTIVE_STYLE = """
QPushButton {
    background-color: #2a2a2a;
    color: #7d7d7d;
    border: 1px solid #3c3c3c;
    padding: 4px 10px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #303030;
}
"""

DATABASE_ANALYTICS_DROPDOWN_STYLE = DEFAULT_DROPDOWN_STYLE
DATABASE_ANALYTICS_HEADER_SPACING = 6
DATABASE_ANALYTICS_DROPDOWN_TOP_PADDING = 6
DATABASE_ANALYTICS_EXPORT_ICON_SIZE = (14, 14)
DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE = (20, 20)
DATABASE_ANALYTICS_SUBHEADER_STYLE = "margin-bottom: 0px;"
DATABASE_VIEW_SUBHEADER_WORD_WRAP = True
DATABASE_ANALYTICS_CONTENT_MARGINS = (8, 6, 8, 6)
DATABASE_ANALYTICS_CONTENT_SPACING = 2
DATABASE_ANALYTICS_CHART_CONTENT_MARGINS = (0, 0, 0, 0)


# Temporary debug colors for visualizing Database Analytics panel boundaries.
DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS = False
DATABASE_ANALYTICS_PANEL_DEBUG_STYLE = "background-color: #240046;" #black currant/dark purple
DATABASE_ANALYTICS_SECTION_DEBUG_STYLE = "background-color: #3c096c;" #brighter purple
DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE = "background-color: #5a189a;" #even brighter purple
DATABASE_ANALYTICS_SUBTITLE_DEBUG_STYLE = "background-color: #0f4c5c;" #dark teal
DATABASE_ANALYTICS_HEADER_ROW_DEBUG_STYLE = "background-color: #1b4332;" #dark green
DATABASE_ANALYTICS_CHART_CONTAINER_DEBUG_STYLE = "background-color: #ff006e;" #hot pink
DATABASE_ANALYTICS_GRAPH_LABEL_REGION_DEBUG_COLOR = "#33ccff" #cornflower blue
DATABASE_ANALYTICS_GRAPH_AREA_DEBUG_COLOR = "#ff6699" #lighter pink

SETTINGS_ORG = "EphemeralDaddy"
SETTINGS_APP = "EphemeralDaddy"
FAILSAFE_EXIT_TIMEOUT_MS = 5000
CRASH_MESSAGE = (
    "¡Lo siento! Ephemeral Daddy is experiencing a stellar collision. "
    "✨Deuces for now, cowboy.✨"
)

RELATIVE_YEAR_COLORS = {
    "year before last":"#9966ff",
    "last year":"#6699ff",
    "current":"#66ffff",
    "next":"#99ff99",
    "year after next":"#ffff66",
    "other":"#ffffff"
}

MIDDLE_PANEL_PLACEHOLDER_COLOR_RGBA = "rgba(200, 145, 79, 0.92)"
CHART_VIEW_TIME_INPUT_WIDTH = 78
CHART_VIEW_TIME_INPUT_DISPLAY_FORMAT = "HH:mm"
CHART_VIEW_TIME_OVERWRITE_ENABLED = True
CHART_VIEW_RECTIFIED_GROUP_LEFT_SPACER = 12
CHART_VIEW_RECTIFIED_LABEL_CHECKBOX_SPACING = 4
DATABASE_VIEW_HEADER_COLOR = MIDDLE_PANEL_ACCENT_COLOR
COLLAPSIBLE_SECTION_BACKGROUND = "#050505"  # Top-level collapsible sections stay near-black.
COLLAPSIBLE_SUBSECTION_BACKGROUND = "#16071f"  # Subtle dark purple for nested subsections.
COLLAPSIBLE_SECTION_CONTENT_STYLE = f"background-color: {COLLAPSIBLE_SECTION_BACKGROUND};"
COLLAPSIBLE_SUBSECTION_CONTENT_STYLE = (
    f"background-color: {COLLAPSIBLE_SUBSECTION_BACKGROUND};"
)
DATABASE_VIEW_PANEL_HEADER_STYLE = (
    f"font-weight: bold; font-size: 14.5px; color: {DATABASE_VIEW_HEADER_COLOR};"
)
CHART_DATA_HIGHLIGHT_COLOR = MIDDLE_PANEL_ACCENT_COLOR
COLLAPSIBLE_SECTION_HEADER_WIGGLE_DURATION_MS = 220
COLLAPSIBLE_SECTION_HEADER_WIGGLE_OFFSET_PX = 4


def collapsible_section_header_toggle_style(
    *,
    text_color: str,
    background_color: str = COLLAPSIBLE_SECTION_BACKGROUND,
) -> str:
    """Return the appwide expandable/collapsible section-header text rule."""
    return (
        "QToolButton {"
        "font-weight: bold; font-size: 12px; "
        f"color: {text_color}; "
        "padding: 6px; text-align: left; "
        f"background-color: {background_color};"
        "}"
        "QToolButton:hover {"
        f"color: {CHART_DATA_HIGHLIGHT_COLOR};"
        "}"
    )


DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE = collapsible_section_header_toggle_style(
    text_color="#ffffff",
)
SETTINGS_COLLAPSIBLE_TOGGLE_STYLE = collapsible_section_header_toggle_style(
    text_color=DATABASE_VIEW_HEADER_COLOR,
)
SETTINGS_SECTION_SUBHEADER_STYLE = "font-weight: 700;"
DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE
CHART_DATA_MONOSPACE_FONT_FAMILY = "Courier New"
CHART_DATA_DIVIDER = "---------"
CHART_DATA_SECTION_HEADERS = (
    "CHART INFO",
    "CORE DESIGNATION",
    "POSITIONS",
    "HOUSES",
    "ASPECTS",
    "BODYGRAPH PROPERTIES",
    "DEFINED CENTERS",
    "GATES",
    "LINES",
    "CHANNELS",
    "AWARENESS STREAMS",
    "CURSEDNESS",
    "D&D-ification",
)
CHART_DATA_COLON_LABELS = (
    "CURSEDNESS:",
    "D&D SPECIES/RACE:",
    "Reasoning:",
)

CHART_DATA_COMMON_LABELS = (
    "Name:",
    "Alias:",
    "Date:",
    "Birth date:",
    "Time:",
    "Birth time:",
    "Official Time:",
    "Retcon Time:",
    "Place:",
    "Chart ID:",
    "Birthplace:",
    "Location:",
    "When/Where:",
    "Personal Transit (Transit → Natal)",
    "Daily Vibe",
    "(Short-term 1-3 day personal transits)",
    "Life Forecast",
    "(Longer-term and structural transits)",
)
CHART_DATA_INFO_LABEL_STYLE = f"font-weight: bold; color: {CHART_DATA_HIGHLIGHT_COLOR};"
CHART_DATA_POPOUT_HEADER_STYLE = "font-weight: 600;"
CHART_DATA_DND_SUBHEADER_BOLD = True
CHART_DATA_DND_SUBHEADER_NOTE_ITALIC = True
CHART_DATA_DND_SUBHEADER_NOTE_BOLD = False
DND_STAT_EARTHTONE_COLORS = {
    "STR": "#7b5b45",
    "DEX": "#8f7a5a",
    "CON": "#6e7f52",
    "INT": "#6a6d58",
    "WIS": "#7a6a4f",
    "CHA": "#8d5f4d",
}
CHART_INFO_SPECIES_HEADER_COLOR = CHART_DATA_HIGHLIGHT_COLOR
CHART_INFO_SPECIES_DESCRIPTION_ITALIC = True
CHART_INFO_EVIDENCE_LABEL_BOLD = True


class _CollapsibleHeaderHoverFilter(QObject):
    """Keep section-header hover color consistent for stylesheets without QSS hover blocks."""

    def __init__(self, toggle: QToolButton, base_style_sheet: str) -> None:
        super().__init__(toggle)
        self._toggle = toggle
        self._base_style_sheet = base_style_sheet

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if watched is self._toggle:
            if event.type() == QEvent.Enter:
                self._toggle.setStyleSheet(
                    f"{self._base_style_sheet} "
                    f"QToolButton {{ color: {CHART_DATA_HIGHLIGHT_COLOR}; }}"
                )
            elif event.type() in (QEvent.Leave, QEvent.Hide, QEvent.EnabledChange):
                self._toggle.setStyleSheet(self._base_style_sheet)
        return super().eventFilter(watched, event)


def _run_collapsible_header_wiggle(toggle: QToolButton) -> None:
    """Animate a compact up/down wiggle on a clicked collapsible header."""
    origin = toggle.pos()
    previous_animation = getattr(toggle, "_collapsible_header_wiggle_animation", None)
    if previous_animation is not None:
        previous_animation.stop()
        previous_origin = getattr(toggle, "_collapsible_header_wiggle_origin", None)
        if isinstance(previous_origin, QPoint):
            toggle.move(previous_origin)
            origin = toggle.pos()
    toggle._collapsible_header_wiggle_origin = origin  # type: ignore[attr-defined]
    wiggle_offset = COLLAPSIBLE_SECTION_HEADER_WIGGLE_OFFSET_PX

    animation = QPropertyAnimation(toggle, b"pos", toggle)
    animation.setDuration(COLLAPSIBLE_SECTION_HEADER_WIGGLE_DURATION_MS)
    animation.setEasingCurve(QEasingCurve.InOutSine)
    animation.setStartValue(origin)
    half_wiggle_offset = max(1, abs(wiggle_offset) // 2)
    animation.setKeyValueAt(0.25, origin + QPoint(0, -wiggle_offset))
    animation.setKeyValueAt(0.50, origin + QPoint(0, wiggle_offset))
    animation.setKeyValueAt(0.75, origin + QPoint(0, -half_wiggle_offset))
    animation.setEndValue(origin)
    animation.finished.connect(
        lambda header_toggle=toggle, start_pos=origin: header_toggle.move(start_pos)
    )
    toggle._collapsible_header_wiggle_animation = animation  # type: ignore[attr-defined]
    animation.start()


def _install_collapsible_header_interactions(toggle: QToolButton, style_sheet: str) -> None:
    """Install the shared hover and click-wiggle behavior on a collapsible header."""
    if not toggle.property("collapsible_header_hover_filter_installed"):
        hover_filter = _CollapsibleHeaderHoverFilter(toggle, style_sheet)
        toggle.installEventFilter(hover_filter)
        toggle._collapsible_header_hover_filter = hover_filter  # type: ignore[attr-defined]
        toggle.setProperty("collapsible_header_hover_filter_installed", True)
    if not toggle.property("collapsible_header_wiggle_installed"):
        toggle.clicked.connect(
            lambda _checked=False, header_toggle=toggle: _run_collapsible_header_wiggle(
                header_toggle
            )
        )
        toggle.setProperty("collapsible_header_wiggle_installed", True)
    if not toggle.property("collapsible_header_autoscroll_installed"):
        toggle.toggled.connect(
            lambda checked=False, header_toggle=toggle: (
                _schedule_collapsible_section_autoscroll(header_toggle) if checked else None
            )
        )
        toggle.setProperty("collapsible_header_autoscroll_installed", True)


def _nearest_scroll_area(widget: QWidget) -> QScrollArea | None:
    """Return the nearest ancestor scroll area containing ``widget``."""
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            return parent
        parent = parent.parentWidget()
    return None


def _collapsible_section_for_toggle(toggle: QToolButton) -> QWidget | None:
    """Return the section widget controlled by a collapsible header toggle."""
    section = toggle.parentWidget()
    while section is not None and section.layout() is None:
        section = section.parentWidget()
    return section


def _scroll_collapsible_section_bottom_into_view(toggle: QToolButton) -> None:
    """Scroll a containing panel down until the expanded section bottom is visible."""
    if not toggle.isChecked():
        return

    section = _collapsible_section_for_toggle(toggle)
    if section is None:
        return

    scroll_area = _nearest_scroll_area(section)
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


def _schedule_collapsible_section_autoscroll(toggle: QToolButton) -> None:
    """Defer autoscroll until expansion layouts and lazy content refreshes settle."""
    QTimer.singleShot(
        0,
        lambda header_toggle=toggle: _scroll_collapsible_section_bottom_into_view(
            header_toggle
        ),
    )
    QTimer.singleShot(
        50,
        lambda header_toggle=toggle: _scroll_collapsible_section_bottom_into_view(
            header_toggle
        ),
    )


def configure_share_export_icon_button(
    button: QAbstractButton,
    *,
    share_icon_path: str | None,
    tooltip: str,
    fallback_text: str = "↗",
) -> None:
    """Apply shared visual behavior for compact share/export icon buttons."""
    if share_icon_path:
        button.setIcon(QIcon(share_icon_path))
        button.setIconSize(QSize(*DATABASE_ANALYTICS_EXPORT_ICON_SIZE))
    else:
        button.setText(fallback_text)

    if hasattr(button, "setFlat"):
        button.setFlat(True)
    if isinstance(button, QToolButton):
        button.setAutoRaise(True)

    button.setFixedSize(*DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE)
    apply_button_cursor(button)
    button.setToolTip(tooltip)


def configure_collapsible_header_toggle(
    toggle: QToolButton,
    *,
    title: str,
    expanded: bool,
    style_sheet: str,
) -> None:
    """Apply default shared behavior for collapsible/expandable section headers."""
    toggle.setText(title)
    toggle.setCheckable(True)
    toggle.setChecked(expanded)
    toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
    toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    toggle.setStyleSheet(style_sheet)
    _install_collapsible_header_interactions(toggle, style_sheet)


def apply_shared_dropdown_style(dropdown: QComboBox) -> None:
    """Force shared dropdown styling on a combo and its popup view.

    Dropdowns should expose their full option labels instead of replacing
    meaningful text with ellipses.  Let the closed combo and popup size to
    their contents, and disable item eliding in the popup view so short
    values such as Human Design profiles/channels remain readable.
    """
    dropdown.setStyleSheet(DEFAULT_DROPDOWN_STYLE)
    dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    dropdown.setMinimumContentsLength(max(dropdown.minimumContentsLength(), 3))
    popup_view = QListView(dropdown)
    popup_view.setTextElideMode(Qt.ElideNone)
    popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    popup_view.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
    popup_view.setStyleSheet(
        """
QListView {
    background-color: #1c1c1c;
    alternate-background-color: #1c1c1c;
    outline: 0;
}
QListView::viewport {
    background-color: #1c1c1c;
}
QListView::item {
    background-color: #1c1c1c;
    padding: 3px 2px;
    margin: 0px;
}
QListView::item:selected {
    background-color: #4f3f25;
    color: __CHART_DATA_HIGHLIGHT_COLOR__;
}
QListView::item:hover {
    background-color: #6a532d;
    color: #fff2d8;
}
QListView::item:checked {
    background-color: #4f3f25;
    color: __CHART_DATA_HIGHLIGHT_COLOR__;
}
QListView::item:checked:hover {
    background-color: #6a532d;
    color: #fff2d8;
}
QListView::indicator {
    width: 0px;
    height: 0px;
    margin: 0px;
    padding: 0px;
}
""".replace("__CHART_DATA_HIGHLIGHT_COLOR__", CHART_DATA_HIGHLIGHT_COLOR)
    )
    dropdown.setView(popup_view)

# About dialog typography/color hierarchy (aligned to Database View middle panel palette).
ABOUT_DIALOG_INTRO_STYLE = f"font-weight: 700; color: {MIDDLE_PANEL_ACCENT_COLOR};"
ABOUT_DIALOG_SUBHEADER_COLOR = CHART_DATA_HIGHLIGHT_COLOR
ABOUT_DIALOG_ACCENT_BUTTON_COLOR = "#7a4cd6"
ABOUT_DIALOG_QUESTION_COLOR = "#d6b15a"
ABOUT_DIALOG_MARKDOWN_STYLESHEET = f"""
h1 {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 700;
}}
h2 {{
    color: {ABOUT_DIALOG_ACCENT_BUTTON_COLOR};
    font-weight: 650;
}}
h3, h4, h5, h6 {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 600;
}}
.about-question {{
    color: {ABOUT_DIALOG_QUESTION_COLOR};
    font-weight: 650;
}}
.about-answer {{
    color: #ffffff;
    font-weight: 600;
}}
.about-major-header {{
    color: {ABOUT_DIALOG_ACCENT_BUTTON_COLOR};
    font-weight: 650;
}}
.about-subheader {{
    color: {ABOUT_DIALOG_SUBHEADER_COLOR};
    font-weight: 650;
}}
"""

# Standardized Natal Chart View chart layout/style references.
STANDARD_NCV_HORIZONTAL_BAR_CHART = {
    "background": "#111111",
    "spine_color": "#444444",
    "x_tick_color": "#f5f5f5", #white-ish
    "y_tick_color": "#f5f5f5", #white-ish
    "x_tick_label_rotation": 90,
    "x_tick_label_size": 7,
    "y_tick_label_size": 8,
    "x_tick_pad": 2,
    "x_margin": 0.03,
    "left": 0.18, #padding; keeps 5+ character y-axis tick labels inside the matplotlib canvas
    "bottom": 0.20, #padding
    "top": 0.92, #padding
    "right": 0.96, #padding
    "show_vertical_tick_labels": True,
    "show_info_icon": False,
}

STANDARD_NCV_PIE_CHART = {
    "start_angle": 90,
    "wedge_edge_color": "#111111",
    "legend_loc": "upper center",
    "legend_anchor": (0.5, -0.08),
    "legend_label_color": "#f5f5f5", #white-ish
    "legend_font_size": 8,
    "legend_label_format": "{percent:.0f}% {label}",
    "legend_ncol": 2,
    "subplots_adjust": {"left": 0.12, "right": 0.88, "bottom": 0.26, "top": 0.92},
}

PLANET_DYNAMICS_BAR_COLORS = {
    "antagonizing": "#b30000",  # stress/friction red
    "enabling": "#6666ff",      # chill vibes violet/blue
    "escalating": "#ffff00",    # amplifying yellow
}

STANDARD_NCV_POPOUT_LAYOUT = {
    "window_min_size": (720, 540),
    "content_margins": (12, 12, 12, 12),
    "chart_stretch": 2,
    "info_stretch": 1,
    "info_placeholder": "ⓘ Click a label to view detailed information.",
}

RELATIVE_YEAR_COLORS = {
    "current":"#66ffff",
    "next":"#99ff99",
    "year after next":"#ffff66",
    "other":"#ffffff"
}

#hex color blender
def blend_hex_colors(hex_a, hex_b, weight_a=0.5):
    """
    Blend two hex colors.
    weight_a = share of first color.
    """
    hex_a = hex_a.lstrip("#")
    hex_b = hex_b.lstrip("#")

    rgb_a = tuple(int(hex_a[i:i+2], 16) for i in (0, 2, 4))
    rgb_b = tuple(int(hex_b[i:i+2], 16) for i in (0, 2, 4))

    rgb = tuple(
        round(a * weight_a + b * (1 - weight_a))
        for a, b in zip(rgb_a, rgb_b)
    )

    return "#{:02x}{:02x}{:02x}".format(*rgb)
