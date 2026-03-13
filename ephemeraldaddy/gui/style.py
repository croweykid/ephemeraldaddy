"""Shared GUI styling and interface constants."""

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

DATABASE_ANALYTICS_DROPDOWN_STYLE = DEFAULT_DROPDOWN_STYLE
DATABASE_ANALYTICS_HEADER_SPACING = 6
DATABASE_ANALYTICS_DROPDOWN_TOP_PADDING = 6
DATABASE_ANALYTICS_EXPORT_ICON_SIZE = (14, 14)
DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE = (20, 20)
DATABASE_ANALYTICS_SUBHEADER_STYLE = "margin-bottom: 0px;"
DATABASE_ANALYTICS_CONTENT_MARGINS = (8, 6, 8, 6)
DATABASE_ANALYTICS_CONTENT_SPACING = 2
DATABASE_ANALYTICS_CHART_CONTENT_MARGINS = (0, 0, 0, 0)

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
DATABASE_VIEW_HEADER_COLOR = MIDDLE_PANEL_ACCENT_COLOR
DATABASE_VIEW_PANEL_HEADER_STYLE = (
    f"font-weight: bold; font-size: 14.5px; color: {DATABASE_VIEW_HEADER_COLOR};"
)
DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE = (
    f"font-weight: bold; font-size: 12px; color: #ffffff; padding: 6px; text-align: left;"
)
DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE
CHART_DATA_HIGHLIGHT_COLOR = MIDDLE_PANEL_ACCENT_COLOR
CHART_DATA_MONOSPACE_FONT_FAMILY = "Courier New"
CHART_DATA_DIVIDER = "---------"
CHART_DATA_SECTION_HEADERS = (
    "CHART INFO",
    "POSITIONS",
    "HOUSES",
    "ASPECTS",
    "CURSEDNESS",
    "D&D SPECIES/RACE",
)
CHART_DATA_COLON_LABELS = (
    "CURSEDNESS:",
    "D&D SPECIES/RACE:",
)

CHART_DATA_COMMON_LABELS = (
    "Name:",
    "Alias:",
    "Date:",
    "Official Time:",
    "Retcon Time:",
    "Place:",
    "When/Where:",
    "Personal Transit (Transit → Natal)",
    "Daily Vibe",
    "(Short-term 1-3 day personal transits)",
    "Life Forecast",
    "(Longer-term and structural transits)",
)
CHART_DATA_INFO_LABEL_STYLE = f"font-weight: bold; color: {CHART_DATA_HIGHLIGHT_COLOR};"
CHART_DATA_POPOUT_HEADER_STYLE = "font-weight: 600;"

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
