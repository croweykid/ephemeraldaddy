"""Shared GUI styling and interface constants."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QSizePolicy

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

GENDER_GUESSER_COLORS = {
    "masculine": "#f16464",
    "feminine": "#7bdb7b",
    "androgynous": "#ffd966",
}

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
    background: #1a1a1a;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #0b0b0b;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #111111;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}
"""

DEFAULT_DROPDOWN_STYLE = """
QComboBox {
    background-color: #242424;
    border: 1px solid #3f3f3f;
    border-radius: 4px;
    color: #f0f0f0;
    padding: 3px 6px;
    min-height: 24px;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background-color: #242424;
    color: #f0f0f0;
    selection-background-color: #3b3b3b;
}
"""

WINDOW_CHROME_MENU_STYLE = """
QMenu {
    background-color: #000000;
    color: #f0f0f0;
    border: 1px solid #2a2a2a;
}
QMenu::item {
    background-color: transparent;
    padding: 4px 22px;
}
QMenu::item:selected {
    background-color: #2f2f2f;
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

MIDDLE_PANEL_ACCENT_COLOR = "#c8914f"
MIDDLE_PANEL_PLACEHOLDER_COLOR_RGBA = "rgba(200, 145, 79, 0.92)"
CHART_VIEW_TIME_INPUT_WIDTH = 78
CHART_VIEW_TIME_INPUT_DISPLAY_FORMAT = "HH:mm"
CHART_VIEW_TIME_OVERWRITE_ENABLED = True
CHART_VIEW_RECTIFIED_GROUP_LEFT_SPACER = 12
CHART_VIEW_RECTIFIED_LABEL_CHECKBOX_SPACING = 4
DATABASE_VIEW_HEADER_COLOR = MIDDLE_PANEL_ACCENT_COLOR
COLLAPSIBLE_SECTION_BACKGROUND = "#0f0515" #362b3d
COLLAPSIBLE_SECTION_CONTENT_STYLE = f"background-color: {COLLAPSIBLE_SECTION_BACKGROUND};"
DATABASE_VIEW_PANEL_HEADER_STYLE = (
    f"font-weight: bold; font-size: 14.5px; color: {DATABASE_VIEW_HEADER_COLOR};"
)
DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE = (
    f"font-weight: bold; font-size: 12px; color: #ffffff; padding: 6px; text-align: left; "
    f"background-color: {COLLAPSIBLE_SECTION_BACKGROUND};"
)
SETTINGS_COLLAPSIBLE_TOGGLE_STYLE = (
    f"font-weight: bold; font-size: 12px; color: {DATABASE_VIEW_HEADER_COLOR}; padding: 6px; text-align: left; "
    f"background-color: {COLLAPSIBLE_SECTION_BACKGROUND};"
)
SETTINGS_SECTION_SUBHEADER_STYLE = "font-weight: 700;"
DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE
CHART_DATA_HIGHLIGHT_COLOR = MIDDLE_PANEL_ACCENT_COLOR
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

# About dialog typography/color hierarchy (aligned to Database View middle panel palette).
ABOUT_DIALOG_INTRO_STYLE = f"font-weight: 700; color: {MIDDLE_PANEL_ACCENT_COLOR};"
ABOUT_DIALOG_MARKDOWN_STYLESHEET = f"""
h1 {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 700;
}}
h2 {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 650;
}}
h3, h4, h5, h6 {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 600;
}}
.about-question {{
    color: {MIDDLE_PANEL_ACCENT_COLOR};
    font-weight: 650;
}}
.about-answer {{
    color: {MIDDLE_PANEL_PLACEHOLDER_COLOR_RGBA};
    font-weight: 600;
}}
"""

# Standardized Natal Chart View chart layout/style references.
STANDARD_NCV_HORIZONTAL_BAR_CHART = {
    "background": "#111111",
    "spine_color": "#444444",
    "x_tick_color": "#f5f5f5",
    "y_tick_color": "#f5f5f5",
    "x_tick_label_rotation": 90,
    "x_tick_label_size": 7,
    "y_tick_label_size": 8,
    "x_tick_pad": 2,
    "x_margin": 0.03,
    "left": 0.10, #padding
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
    "legend_label_color": "#f5f5f5",
    "legend_font_size": 8,
    "legend_label_format": "{percent:.0f}% {label}",
    "legend_ncol": 2,
    "subplots_adjust": {"left": 0.12, "right": 0.88, "bottom": 0.26, "top": 0.92},
}

PLANET_DYNAMICS_BAR_COLORS = {
    "stability": "#6aa84f",      # green
    "constructiveness": "#a94442", # brick red
    "volatility": "#7fff00",     # chartreuse
    "fragility": "#6fa8dc",      # blue
    "adaptability": "#f4c542",   # saffron
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


#COLOR SPECTRUM GENERATOR:
def get_blended_color(color1, color2, color3, color4, totalsteps, getstep):
    # accepts 4 anchor colors; blends in totalsteps; returns color at getstep

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def lerp(a, b, t):
        return round(a + (b - a) * t)

    if totalsteps <= 0:
        raise ValueError("totalsteps must be > 0")

    anchors = [hex_to_rgb(c) for c in (color1, color2, color3, color4)]

    # wrap getstep so any integer works
    t = (getstep % totalsteps) / totalsteps * 4
    segment = int(t) % 4
    frac = t - segment

    a = anchors[segment]
    b = anchors[(segment + 1) % 4]

    rgb = tuple(lerp(a[i], b[i], frac) for i in range(3))
    return rgb_to_hex(rgb)


def build_spectrum(color1, color2, color3, color4, totalsteps):
    return [
        get_blended_color(color1, color2, color3, color4, totalsteps, getstep)
        for getstep in range(totalsteps)
    ]


# example
palette = build_spectrum("#ccffcc", "#ffff00", "#cc3300", "#ccccff", 12)
print(palette)
print(get_blended_color("#ccffcc", "#ffff00", "#cc3300", "#ccccff", 12, 7))