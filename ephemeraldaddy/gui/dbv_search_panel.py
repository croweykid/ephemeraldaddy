"""Database View right-hand search panel UI builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ephemeraldaddy.core.interpretations import JONES_PLANETS

BODY_DYNAMICS_ROLE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Enabler", "enabler"),
    ("Antagonist", "antagonist"),
    ("Escalator", "escalator"),
)

def weight_is_at_least_triple_next_highest(
    weights: dict[str, float] | None,
    selected_key: str,
) -> bool:
    """Return whether a selected weight is at least 3x the next-highest peer.

    ``selected_key == "Any"`` means any weighted key may satisfy the isolated
    dominance test. This is the active Isolated Factors wildcard behavior.
    """
    if not weights:
        return False

    def numeric_weight(weight_key: str) -> float | None:
        try:
            return float(weights.get(weight_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return None

    def key_is_isolated(candidate_key: str) -> bool:
        if candidate_key not in weights:
            return False
        selected_weight = numeric_weight(candidate_key)
        if selected_weight is None or selected_weight <= 0.0:
            return False

        next_highest_weight = 0.0
        for weight_key in weights:
            if str(weight_key) == candidate_key:
                continue
            other_weight = numeric_weight(str(weight_key))
            if other_weight is None:
                return False
            next_highest_weight = max(next_highest_weight, other_weight)
        return selected_weight >= (next_highest_weight * 3.0)

    if selected_key == "Any":
        return any(key_is_isolated(str(weight_key)) for weight_key in weights)
    return key_is_isolated(selected_key)


def active_body_dynamics_filters(window) -> list[dict[str, object]]:
    """Return active Body Dynamics filter rows from the Database View search panel."""
    return [
        filters
        for filters in getattr(window, "_body_dynamics_filters", [])
        if str(filters["body"].currentData()) != "Any"
    ]


def body_dynamics_filters_are_active(window) -> bool:
    """Return whether any Body Dynamics filter row is selected."""
    return bool(active_body_dynamics_filters(window))


def reset_body_dynamics_filters(window) -> None:
    """Reset all Body Dynamics filter widgets to their default state."""
    for filters in getattr(window, "_body_dynamics_filters", []):
        filters["body"].setCurrentIndex(0)
        filters["role"].setCurrentIndex(0)
        filters["or"].setChecked(False)
        filters["exclude"].setChecked(False)
        filters["and"].setChecked(True)


def _body_dynamics_filter_matches(chart, filters: dict[str, object]) -> bool:
    body = str(filters["body"].currentData())
    role = str(filters["role"].currentData())
    if body == "Any" or not role:
        return False

    from ephemeraldaddy.core import db

    roles = db._parse_body_dynamics_roles(getattr(chart, "body_dynamics_roles", None))
    if body not in roles:
        roles = db._resolve_body_dynamics_roles(chart)
    return roles.get(body) == role


def chart_matches_body_dynamics_filters(window, chart, filters: list[dict[str, object]] | None = None) -> bool:
    """Apply active Body Dynamics AND/OR/EXCLUDE filters to a chart."""
    active_filters = list(filters if filters is not None else active_body_dynamics_filters(window))
    if not active_filters:
        return True

    and_filters = [filters for filters in active_filters if filters["and"].isChecked()]
    or_filters = [filters for filters in active_filters if filters["or"].isChecked()]
    exclude_filters = [filters for filters in active_filters if filters["exclude"].isChecked()]

    for filters in and_filters:
        if not _body_dynamics_filter_matches(chart, filters):
            return False
    if or_filters and not any(_body_dynamics_filter_matches(chart, filters) for filters in or_filters):
        return False
    for filters in exclude_filters:
        if _body_dynamics_filter_matches(chart, filters):
            return False
    return True


if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def build_dbv_search_panel(window) -> "QWidget":
    """Build the Database View search panel while mutating ``window`` state."""
    from ephemeraldaddy.gui import app as app_module

    # Qt widgets/classes
    QWidget = app_module.QWidget
    EmojiTiledPanel = app_module.EmojiTiledPanel
    QVBoxLayout = app_module.QVBoxLayout
    QComboBox = app_module.QComboBox
    QLabel = app_module.QLabel
    QLineEdit = app_module.QLineEdit
    QHBoxLayout = app_module.QHBoxLayout
    QPushButton = app_module.QPushButton
    QListWidget = app_module.QListWidget
    QCheckBox = app_module.QCheckBox
    QToolButton = app_module.QToolButton
    Qt = app_module.Qt
    QFrame = app_module.QFrame
    QuadStateSlider = app_module.QuadStateSlider
    QRadioButton = app_module.QRadioButton
    QButtonGroup = app_module.QButtonGroup
    QGridLayout = app_module.QGridLayout
    QFormLayout = app_module.QFormLayout
    QIntValidator = app_module.QIntValidator
    QSizePolicy = app_module.QSizePolicy

    # Shared styles/constants/helpers already resolved in app.py.
    DEFAULT_DROPDOWN_STYLE = app_module.DEFAULT_DROPDOWN_STYLE
    DATABASE_VIEW_PANEL_HEADER_STYLE = app_module.DATABASE_VIEW_PANEL_HEADER_STYLE
    DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE = app_module.DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE
    COLLAPSIBLE_SECTION_CONTENT_STYLE = app_module.COLLAPSIBLE_SECTION_CONTENT_STYLE
    DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS = app_module.DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS
    DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE = app_module.DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE
    DATABASE_ANALYTICS_SUBHEADER_STYLE = app_module.DATABASE_ANALYTICS_SUBHEADER_STYLE
    RODDEN_RATING = app_module.RODDEN_RATING
    ZODIAC_NAMES = app_module.ZODIAC_NAMES
    ASPECT_DEFS = app_module.ASPECT_DEFS
    HD_CHANNELS = app_module.HD_CHANNELS
    NAKSHATRA_RANGES = app_module.NAKSHATRA_RANGES
    NATAL_CHART_MIN_YEAR = app_module.NATAL_CHART_MIN_YEAR
    NATAL_CHART_MAX_YEAR = app_module.NATAL_CHART_MAX_YEAR
    SEARCH_SENTIMENT_OPTIONS = app_module.SEARCH_SENTIMENT_OPTIONS
    SEARCH_RELATIONSHIP_TYPE_OPTIONS = app_module.SEARCH_RELATIONSHIP_TYPE_OPTIONS
    DND_CLASSES = app_module.DND_CLASSES
    SPECIES_FAMILIES = app_module.SPECIES_FAMILIES
    GENERATION_FILTER_OPTIONS = app_module.GENERATION_FILTER_OPTIONS
    SEARCH_GENDER_OPTIONS = app_module.SEARCH_GENDER_OPTIONS
    SEARCH_GENDER_GUESSED_OPTIONS = app_module.SEARCH_GENDER_GUESSED_OPTIONS
    SOURCE_OPTIONS = app_module.SOURCE_OPTIONS
    configure_collapsible_header_toggle = app_module.configure_collapsible_header_toggle
    # Search panel (right sidebar).
    panel = EmojiTiledPanel("🔎", font_size=100, opacity=0.12) #Search panel background
    panel.setMinimumWidth(260)
    layout = QVBoxLayout()
    panel.setLayout(layout)

    def apply_default_dropdown_style(dropdown: QComboBox) -> None:
        dropdown.setStyleSheet(DEFAULT_DROPDOWN_STYLE)

    def center_dropdown_items(dropdown: QComboBox) -> None:
        dropdown.setEditable(False)
        for item_index in range(dropdown.count()):
            dropdown.setItemData(item_index, Qt.AlignCenter, Qt.TextAlignmentRole)
        dropdown.setStyleSheet(f"{DEFAULT_DROPDOWN_STYLE} QComboBox {{ text-align: center; }}")

    def narrow_dropdown_for_not_option(dropdown: QComboBox) -> None:
        target_width = max(120, dropdown.sizeHint().width() - 100)
        dropdown.setFixedWidth(target_width)

    def set_dropdown_width_chars(dropdown: QComboBox, chars: int) -> None:
        metrics = dropdown.fontMetrics()
        width_px = (metrics.horizontalAdvance("0") * int(chars)) + 24
        dropdown.setMinimumWidth(width_px)
        dropdown.setMaximumWidth(width_px)
        dropdown.setFixedWidth(width_px)
        dropdown.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def compact_body_label(label: str) -> str:
        return str(label).replace("Part of Fortune", "Fortune")

    def compact_nakshatra_label(label: str) -> str:
        return str(label).replace("Purva", "P.").replace("Uttara", "U.")

    search_title = QLabel("Database search")
    search_title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
    layout.addWidget(search_title)

    window.search_text_input = QLineEdit()
    window.search_text_input.setPlaceholderText(
        "Search names or birthplaces"
    )
    window.search_text_input.textChanged.connect(window._on_filter_changed)
    window.search_text_input.returnPressed.connect(window._on_filter_changed)
    window.search_text_input.installEventFilter(window)
    layout.addWidget(window.search_text_input)

    astrotheme_row = QHBoxLayout()
    window.astrotheme_search_input = QLineEdit()
    window.astrotheme_search_input.setPlaceholderText(
        "Search Astrotheme.com's public 📚"
    )
    window.astrotheme_search_input.returnPressed.connect(
        window._on_import_astrotheme_from_search_panel
    )
    window.astrotheme_search_input.installEventFilter(window)
    astrotheme_row.addWidget(window.astrotheme_search_input, 1)
    astrotheme_import_button = QPushButton("Import")
    astrotheme_import_button.clicked.connect(
        window._on_import_astrotheme_from_search_panel
    )
    astrotheme_row.addWidget(astrotheme_import_button)
    layout.addLayout(astrotheme_row)

    tags_search_row = QVBoxLayout()
    tags_search_row.setContentsMargins(0, 0, 0, 0)
    tags_search_row.setSpacing(4)
    window.search_tags_input = QLineEdit()
    window.search_tags_input.setPlaceholderText(
        "Search by tags (comma-separated)"
    )
    window.search_tags_input.textChanged.connect(window._on_search_tags_changed)
    window.search_tags_input.returnPressed.connect(window._on_filter_changed)
    tags_search_row.addWidget(window.search_tags_input)
    window.search_tags_preview_label = QLabel()
    window.search_tags_preview_label.setWordWrap(True)
    window.search_tags_preview_label.setTextFormat(Qt.RichText)
    tags_search_row.addWidget(window.search_tags_preview_label)
    window.search_untagged_checkbox = QuadStateSlider("untagged")
    window.search_untagged_checkbox.modeChanged.connect(window._on_filter_changed)
    tags_search_row.addWidget(window.search_untagged_checkbox)

    window.search_tags_toggle = QToolButton()
    configure_collapsible_header_toggle(
        window.search_tags_toggle,
        title="Tags",
        expanded=False,
        style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    )
    tags_search_row.addWidget(window.search_tags_toggle)

    window.search_tags_list_widget = QListWidget()
    window.search_tags_list_widget.setSelectionMode(QListWidget.NoSelection)
    window.search_tags_list_widget.setMaximumHeight(180)
    window.search_tags_list_widget.setVisible(False)
    window.search_tags_toggle.toggled.connect(window.search_tags_list_widget.setVisible)
    window.search_tags_toggle.toggled.connect(
        lambda expanded: window._refresh_search_tags_list(
            getattr(window, "_known_chart_tags", [])
        ) if expanded else None
    )
    tags_search_row.addWidget(window.search_tags_list_widget)
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
    #reset_button.clicked.connect(window._reset_filters)
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
        content_style = COLLAPSIBLE_SECTION_CONTENT_STYLE
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            content_style = f"{content_style} {DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE}"
        content.setStyleSheet(content_style)
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

    #Search: data completeness & accuracy
    birth_info_status_section, birth_info_status_layout = add_collapsible_section(
        "🧩 Data Completeness && Accuracy" #data icon contenders: 🧮 🗄️ 🪪 𖦏 🔢 🧩 ℹ️
    )

    incomplete_birthdate_row = QHBoxLayout()
    window.incomplete_birthdate_checkbox = QuadStateSlider("incomplete birthdate (placeholder chart)")
    window.incomplete_birthdate_checkbox.modeChanged.connect(window._on_filter_changed)
    incomplete_birthdate_row.addWidget(window.incomplete_birthdate_checkbox)
    incomplete_birthdate_row.addStretch(1)
    birth_info_status_layout.addLayout(incomplete_birthdate_row)

    birth_status_mode_row = QHBoxLayout()
    birth_status_mode_row.addWidget(QLabel("🐣Time:"))
    birth_status_mode_row.addStretch(1)
    window.birth_status_filter_and = QRadioButton("AND")
    window.birth_status_filter_or = QRadioButton("OR")
    window.birth_status_filter_group = QButtonGroup(window)
    window.birth_status_filter_group.setExclusive(True)
    window.birth_status_filter_group.addButton(window.birth_status_filter_and)
    window.birth_status_filter_group.addButton(window.birth_status_filter_or)
    window.birth_status_filter_and.setChecked(True)
    window.birth_status_filter_and.toggled.connect(window._on_filter_changed)
    window.birth_status_filter_or.toggled.connect(window._on_filter_changed)
    birth_status_mode_row.addWidget(window.birth_status_filter_and)
    birth_status_mode_row.addWidget(window.birth_status_filter_or)
    birth_info_status_layout.addLayout(birth_status_mode_row)

    birth_filters_row = QHBoxLayout()
    window.birthtime_unknown_checkbox = QuadStateSlider("unknown")
    window.birthtime_unknown_checkbox.modeChanged.connect(window._on_filter_changed)
    window.retconned_checkbox = QuadStateSlider("rectified")
    window.retconned_checkbox.modeChanged.connect(window._on_filter_changed)
    birth_filters_row.addWidget(window.birthtime_unknown_checkbox)
    birth_filters_row.addWidget(window.retconned_checkbox)
    birth_filters_row.addStretch(1)
    birth_info_status_layout.addLayout(birth_filters_row)

    rodden_divider = QFrame()
    rodden_divider.setFrameShape(QFrame.HLine)
    rodden_divider.setStyleSheet("color: #2f2f2f;")
    birth_info_status_layout.addWidget(rodden_divider)

    rodden_header = QLabel("Rodden Rating")
    rodden_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    birth_info_status_layout.addWidget(rodden_header)

    rodden_layout = QGridLayout()
    rodden_layout.setContentsMargins(0, 0, 0, 0)
    rodden_layout.setHorizontalSpacing(10)
    rodden_layout.setVerticalSpacing(4)
    window.data_rating_filter_checkboxes = {}
    rodden_rows = (len(RODDEN_RATING) + 1) // 2
    for idx, rating in enumerate(RODDEN_RATING):
        grade = str(rating.get("grade", "")).strip()
        if not grade:
            continue
        checkbox = QuadStateSlider(grade)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.data_rating_filter_checkboxes[grade] = checkbox
        row = idx % rodden_rows
        col = idx // rodden_rows
        rodden_layout.addWidget(checkbox, row, col)
    birth_info_status_layout.addLayout(rodden_layout)
    layout.addWidget(birth_info_status_section)

    #Search: Astrological Positions section
    bodies_section, bodies_group_layout = add_collapsible_section("🪐Positions") #astrological positions

    bodies_layout = QFormLayout()
    bodies_layout.setLabelAlignment(Qt.AlignLeft)
    bodies_group_layout.addLayout(bodies_layout)

    for _ in range(10):
        filter_row = QWidget()
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_row.setLayout(filter_layout)

        body_combo = QComboBox()
        apply_default_dropdown_style(body_combo)
        body_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(body_combo, 10)
        for body_label, body_key in window._searchable_bodies():
            body_combo.addItem(compact_body_label(body_label), body_key)
        body_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        sign_combo = QComboBox()
        apply_default_dropdown_style(sign_combo)
        sign_combo.addItem("Any 🪧", "Any")
        set_dropdown_width_chars(sign_combo, 6)
        for sign in ZODIAC_NAMES:
            sign_combo.addItem(sign, sign)
        sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        house_combo = QComboBox()
        apply_default_dropdown_style(house_combo)
        house_combo.addItem("Any 🏠", "Any")
        set_dropdown_width_chars(house_combo, 6)
        for house_num in range(1, 13):
            house_combo.addItem(str(house_num), str(house_num))
        house_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_layout.addWidget(body_combo)
        filter_layout.addWidget(sign_combo, 1)
        filter_layout.addWidget(house_combo)
        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(filter_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)
        filter_layout.addWidget(filter_and)
        filter_layout.addWidget(filter_or)
        filter_layout.addWidget(filter_not)

        window._search_body_filters.append({
            "body": body_combo,
            "sign": sign_combo,
            "house": house_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        bodies_layout.addRow(filter_row)

    layout.addWidget(bodies_section)

    #Search: Aspects section
    aspect_section, aspect_group_layout = add_collapsible_section("🪐Aspect") #astrological aspect

    aspect_layout = QFormLayout()
    aspect_layout.setLabelAlignment(Qt.AlignLeft)
    aspect_group_layout.addLayout(aspect_layout)

    aspect_options = [("Any 📐", "Any")]
    for aspect_name in sorted(ASPECT_DEFS):
        aspect_options.append((aspect_name.replace("_", " ").title(), aspect_name))

    searchable_planets = list(window._searchable_bodies())

    for _ in range(3):
        aspect_row = QWidget()
        aspect_row_layout = QHBoxLayout()
        aspect_row_layout.setContentsMargins(0, 0, 0, 0)
        aspect_row.setLayout(aspect_row_layout)

        planet_1_combo = QComboBox()
        apply_default_dropdown_style(planet_1_combo)
        planet_1_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(planet_1_combo, 10)
        for label, key in searchable_planets:
            planet_1_combo.addItem(compact_body_label(label), key)
        planet_1_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        aspect_combo = QComboBox()
        apply_default_dropdown_style(aspect_combo)
        for label, key in aspect_options:
            aspect_combo.addItem(label, key)
        set_dropdown_width_chars(aspect_combo, 17)
        aspect_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        planet_2_combo = QComboBox()
        apply_default_dropdown_style(planet_2_combo)
        planet_2_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(planet_2_combo, 10)
        for label, key in searchable_planets:
            planet_2_combo.addItem(compact_body_label(label), key)
        planet_2_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_group = QButtonGroup(aspect_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        aspect_row_layout.addWidget(planet_1_combo, 1)
        aspect_row_layout.addWidget(aspect_combo, 1)
        aspect_row_layout.addWidget(planet_2_combo, 1)
        aspect_row_layout.addWidget(filter_and)
        aspect_row_layout.addWidget(filter_or)

        window._aspect_filters.append(
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

    #Search: Dominant Sign section
    dominant_section, dominant_group_layout = add_collapsible_section(
        "🪐Dominant Sign" #dominant astrological sign
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
        sign_combo.addItem("Any 🪧", "Any")
        set_dropdown_width_chars(sign_combo, 6)
        for sign in ZODIAC_NAMES:
            sign_combo.addItem(sign)
        narrow_dropdown_for_not_option(sign_combo)
        sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(dominant_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        dominant_row_layout.addWidget(sign_combo)
        dominant_row_layout.addWidget(filter_and)
        dominant_row_layout.addWidget(filter_or)
        dominant_row_layout.addWidget(filter_not)
        dominant_row_layout.addStretch(1)

        window._dominant_sign_filters.append({
            "sign": sign_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        dominant_layout.addRow(dominant_row)

    layout.addWidget(dominant_section)

    #Search: Dominant Bodies section
    dominant_planet_section, dominant_planet_group_layout = add_collapsible_section(
        "🪐Dominant Bodies" #dominant astrological bodies
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
        planet_combo.addItem("Any 🪐", "Any")
        for planet_label, planet_key in window._searchable_bodies():
            if planet_key in {"AS", "IC", "DS", "MC"}:
                continue
            planet_combo.addItem(compact_body_label(planet_label), planet_key)
        narrow_dropdown_for_not_option(planet_combo)
        planet_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(dominant_planet_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        dominant_planet_row_layout.addWidget(planet_combo)
        dominant_planet_row_layout.addWidget(filter_and)
        dominant_planet_row_layout.addWidget(filter_or)
        dominant_planet_row_layout.addWidget(filter_not)
        dominant_planet_row_layout.addStretch(1)

        window._dominant_planet_filters.append({
            "planet": planet_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        dominant_planet_layout.addRow(dominant_planet_row)

    layout.addWidget(dominant_planet_section)

    #Search: Body Dynamics section
    body_dynamics_section, body_dynamics_group_layout = add_collapsible_section(
        "🪐Body Dynamics"
    )

    body_dynamics_layout = QFormLayout()
    body_dynamics_layout.setLabelAlignment(Qt.AlignLeft)
    body_dynamics_group_layout.addLayout(body_dynamics_layout)

    for _ in range(3):
        body_dynamics_row = QWidget()
        body_dynamics_row_layout = QHBoxLayout()
        body_dynamics_row_layout.setContentsMargins(0, 0, 0, 0)
        body_dynamics_row.setLayout(body_dynamics_row_layout)

        body_combo = QComboBox()
        apply_default_dropdown_style(body_combo)
        body_combo.addItem("Any 🪐", "Any")
        set_dropdown_width_chars(body_combo, 10)
        for body in JONES_PLANETS:
            body_combo.addItem(compact_body_label(body), body)
        body_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        role_combo = QComboBox()
        apply_default_dropdown_style(role_combo)
        role_combo.addItem("Any ±", "any")
        set_dropdown_width_chars(role_combo, 10)
        for role_label, role_key in BODY_DYNAMICS_ROLE_OPTIONS:
            role_combo.addItem(role_label, role_key)
        role_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_exclude = QRadioButton("🚫")
        filter_group = QButtonGroup(body_dynamics_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_exclude)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        body_dynamics_row_layout.addWidget(body_combo, 1)
        body_dynamics_row_layout.addWidget(role_combo, 1)
        body_dynamics_row_layout.addWidget(filter_and)
        body_dynamics_row_layout.addWidget(filter_or)
        body_dynamics_row_layout.addWidget(filter_exclude)

        window._body_dynamics_filters.append({
            "body": body_combo,
            "role": role_combo,
            "and": filter_and,
            "or": filter_or,
            "exclude": filter_exclude,
        })
        body_dynamics_layout.addRow(body_dynamics_row)

    layout.addWidget(body_dynamics_section)

    #Search: Dominant Mode section
    dominant_mode_section, dominant_mode_group_layout = add_collapsible_section(
        "🪐Dominant Mode" #dominant astrological mode
    )

    dominant_mode_layout = QFormLayout()
    dominant_mode_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_mode_group_layout.addLayout(dominant_mode_layout)

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
    narrow_dropdown_for_not_option(mode_combo)
    mode_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    filter_and = QRadioButton("&&")
    filter_or = QRadioButton("OR")
    filter_not = QRadioButton("🚫")
    filter_group = QButtonGroup(dominant_mode_row)
    filter_group.setExclusive(True)
    filter_group.addButton(filter_and)
    filter_group.addButton(filter_or)
    filter_group.addButton(filter_not)
    filter_and.setChecked(True)
    filter_group.buttonClicked.connect(window._on_filter_changed)

    dominant_mode_row_layout.addWidget(mode_combo)
    dominant_mode_row_layout.addWidget(filter_and)
    dominant_mode_row_layout.addWidget(filter_or)
    dominant_mode_row_layout.addWidget(filter_not)
    dominant_mode_row_layout.addStretch(1)

    window._dominant_mode_filters.append({
        "mode": mode_combo,
        "and": filter_and,
        "or": filter_or,
        "not": filter_not,
    })
    dominant_mode_layout.addRow(dominant_mode_row)

    layout.addWidget(dominant_mode_section)

    # Search: Decans section
    decan_section, decan_group_layout = add_collapsible_section("🪐Decans")
    decan_layout = QFormLayout()
    decan_layout.setLabelAlignment(Qt.AlignLeft)
    decan_group_layout.addLayout(decan_layout)

    decan_row = QWidget()
    decan_row_layout = QHBoxLayout()
    decan_row_layout.setContentsMargins(0, 0, 0, 0)
    decan_row.setLayout(decan_row_layout)

    decan_sign_combo = QComboBox()
    apply_default_dropdown_style(decan_sign_combo)
    decan_sign_combo.addItem("Any", "Any")
    for sign_name in ZODIAC_NAMES:
        decan_sign_combo.addItem(str(sign_name), str(sign_name))
    decan_sign_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    decan_number_combo = QComboBox()
    apply_default_dropdown_style(decan_number_combo)
    decan_number_combo.addItem("Any", "Any")
    decan_number_combo.addItem("1", "1")
    decan_number_combo.addItem("2", "2")
    decan_number_combo.addItem("3", "3")
    decan_number_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

    decan_row_layout.addWidget(QLabel("🔟"))
    decan_row_layout.addWidget(decan_sign_combo, 1)
    decan_row_layout.addWidget(decan_number_combo, 1)
    decan_row_layout.addStretch(1)

    window._decan_sign_filter_combo = decan_sign_combo
    window._decan_number_filter_combo = decan_number_combo
    decan_layout.addRow(decan_row)
    layout.addWidget(decan_section)

    #Search: Dominant Nakshatra section
    dominant_nakshatra_section, dominant_nakshatra_group_layout = add_collapsible_section(
        "🪐Dominant Nakshatra"
    )

    dominant_nakshatra_layout = QFormLayout()
    dominant_nakshatra_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_nakshatra_group_layout.addLayout(dominant_nakshatra_layout)

    for _ in range(3):
        dominant_nakshatra_row = QWidget()
        dominant_nakshatra_row_layout = QHBoxLayout()
        dominant_nakshatra_row_layout.setContentsMargins(0, 0, 0, 0)
        dominant_nakshatra_row.setLayout(dominant_nakshatra_row_layout)

        nakshatra_combo = QComboBox()
        apply_default_dropdown_style(nakshatra_combo)
        nakshatra_combo.addItem("Any", "Any")
        for nakshatra_name, *_ in NAKSHATRA_RANGES:
            nakshatra_combo.addItem(compact_nakshatra_label(str(nakshatra_name)), str(nakshatra_name))
        narrow_dropdown_for_not_option(nakshatra_combo)
        nakshatra_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(dominant_nakshatra_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        dominant_nakshatra_row_layout.addWidget(nakshatra_combo)
        dominant_nakshatra_row_layout.addWidget(filter_and)
        dominant_nakshatra_row_layout.addWidget(filter_or)
        dominant_nakshatra_row_layout.addWidget(filter_not)
        dominant_nakshatra_row_layout.addStretch(1)

        window._dominant_nakshatra_filters.append({
            "nakshatra": nakshatra_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        dominant_nakshatra_layout.addRow(dominant_nakshatra_row)

    layout.addWidget(dominant_nakshatra_section)

    #Search: Dominant Elements section
    dominant_element_section, dominant_element_group_layout = add_collapsible_section(
        "🪐Dominant Elements" #dominatn astrological elements
    )
    dominant_element_layout = QFormLayout()
    dominant_element_layout.setLabelAlignment(Qt.AlignLeft)
    dominant_element_group_layout.addLayout(dominant_element_layout)

    for _ in range(3):
        dominant_element_row = QWidget()
        dominant_element_row_layout = QHBoxLayout()
        dominant_element_row_layout.setContentsMargins(0, 0, 0, 0)
        dominant_element_row.setLayout(dominant_element_row_layout)

        element_combo = QComboBox()
        apply_default_dropdown_style(element_combo)
        element_combo.addItem("🔥🌬️💧🌱", "Any")
        for element in ("Fire", "Earth", "Air", "Water"):
            element_combo.addItem(element, element)
        narrow_dropdown_for_not_option(element_combo)
        element_combo.currentIndexChanged.connect(window._on_astrological_filter_changed)

        filter_and = QRadioButton("&&")
        filter_or = QRadioButton("OR")
        filter_not = QRadioButton("🚫")
        filter_group = QButtonGroup(dominant_element_row)
        filter_group.setExclusive(True)
        filter_group.addButton(filter_and)
        filter_group.addButton(filter_or)
        filter_group.addButton(filter_not)
        filter_and.setChecked(True)
        filter_group.buttonClicked.connect(window._on_filter_changed)

        dominant_element_row_layout.addWidget(QLabel("🧪"))
        dominant_element_row_layout.addWidget(element_combo)
        dominant_element_row_layout.addWidget(filter_and)
        dominant_element_row_layout.addWidget(filter_or)
        dominant_element_row_layout.addWidget(filter_not)
        dominant_element_row_layout.addStretch(1)

        window._dominant_element_filters.append({
            "element": element_combo,
            "and": filter_and,
            "or": filter_or,
            "not": filter_not,
        })
        dominant_element_layout.addRow(dominant_element_row)

    layout.addWidget(dominant_element_section)

    #Search: Isolated Factors section
    isolated_factors_section, isolated_factors_group_layout = add_collapsible_section(
        "🪐Isolated Factors"
    )

    isolated_body_row = QHBoxLayout()
    isolated_body_row.addWidget(QLabel("Isolated dominance of"))
    window._isolated_dominant_body_filter_combo = QComboBox()
    apply_default_dropdown_style(window._isolated_dominant_body_filter_combo)
    window._isolated_dominant_body_filter_combo.addItem("Any 🪐", "Any")
    set_dropdown_width_chars(window._isolated_dominant_body_filter_combo, 10)
    for body_label, body_key in window._searchable_bodies():
        if body_key in {"AS", "IC", "DS", "MC"}:
            continue
        window._isolated_dominant_body_filter_combo.addItem(compact_body_label(body_label), body_key)
    window._isolated_dominant_body_filter_combo.currentIndexChanged.connect(
        window._on_astrological_filter_changed
    )
    isolated_body_row.addWidget(window._isolated_dominant_body_filter_combo, 1)
    isolated_factors_group_layout.addLayout(isolated_body_row)

    isolated_operator_row = QHBoxLayout()
    isolated_operator_row.addStretch(1)
    window._isolated_dominant_filter_and = QRadioButton("&&")
    window._isolated_dominant_filter_or = QRadioButton("OR")
    isolated_operator_group = QButtonGroup(window)
    isolated_operator_group.setExclusive(True)
    isolated_operator_group.addButton(window._isolated_dominant_filter_and)
    isolated_operator_group.addButton(window._isolated_dominant_filter_or)
    window._isolated_dominant_filter_and.setChecked(True)
    isolated_operator_group.buttonClicked.connect(window._on_filter_changed)
    isolated_operator_row.addWidget(window._isolated_dominant_filter_and)
    isolated_operator_row.addWidget(window._isolated_dominant_filter_or)
    isolated_operator_row.addStretch(1)
    isolated_factors_group_layout.addLayout(isolated_operator_row)

    isolated_sign_row = QHBoxLayout()
    isolated_sign_row.addWidget(QLabel("Isolated dominance of"))
    window._isolated_dominant_sign_filter_combo = QComboBox()
    apply_default_dropdown_style(window._isolated_dominant_sign_filter_combo)
    window._isolated_dominant_sign_filter_combo.addItem("Any 🪧", "Any")
    set_dropdown_width_chars(window._isolated_dominant_sign_filter_combo, 6)
    for sign in ZODIAC_NAMES:
        window._isolated_dominant_sign_filter_combo.addItem(sign, sign)
    window._isolated_dominant_sign_filter_combo.currentIndexChanged.connect(
        window._on_astrological_filter_changed
    )
    isolated_sign_row.addWidget(window._isolated_dominant_sign_filter_combo, 1)
    isolated_factors_group_layout.addLayout(isolated_sign_row)

    layout.addWidget(isolated_factors_section)

    #Search: Human Design section
    human_design_section, human_design_group_layout = add_collapsible_section("🪐Human Design")

    hd_channels_row = QHBoxLayout()
    hd_channels_row.addWidget(QLabel("Channels"))
    for _ in range(3):
        channel_combo = QComboBox()
        apply_default_dropdown_style(channel_combo)
        channel_combo.addItem("Any", "Any")
        channel_options = sorted(
            {
                str(channel_key).strip()
                for channel_key in HD_CHANNELS.keys()
                if str(channel_key).strip()
            },
            key=lambda value: (
                int(value.split("-")[0]) if "-" in value and value.split("-")[0].isdigit() else 999,
                int(value.split("-")[1]) if "-" in value and len(value.split("-")) > 1 and value.split("-")[1].isdigit() else 999,
                value,
            ),
        )
        for channel_label in channel_options:
            channel_combo.addItem(channel_label, channel_label)
        set_dropdown_width_chars(channel_combo, 4)
        channel_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_channel_filters.append(channel_combo)
        hd_channels_row.addWidget(channel_combo)
    window._human_design_channel_filter_and = QRadioButton("&&")
    window._human_design_channel_filter_or = QRadioButton("OR")
    hd_channel_group = QButtonGroup(window)
    hd_channel_group.setExclusive(True)
    hd_channel_group.addButton(window._human_design_channel_filter_and)
    hd_channel_group.addButton(window._human_design_channel_filter_or)
    window._human_design_channel_filter_and.setChecked(True)
    hd_channel_group.buttonClicked.connect(window._on_filter_changed)
    hd_channels_row.addWidget(window._human_design_channel_filter_and)
    hd_channels_row.addWidget(window._human_design_channel_filter_or)
    human_design_group_layout.addLayout(hd_channels_row)

    hd_gates_row = QHBoxLayout()
    hd_gates_row.addWidget(QLabel("Gates"))
    for _ in range(3):
        gate_combo = QComboBox()
        apply_default_dropdown_style(gate_combo)
        gate_combo.addItem("Any", "Any")
        for gate_value in range(1, 65):
            gate_combo.addItem(str(gate_value), gate_value)
        center_dropdown_items(gate_combo)
        set_dropdown_width_chars(gate_combo, 3)
        gate_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_gate_filters.append(gate_combo)
        hd_gates_row.addWidget(gate_combo)
    window._human_design_gate_filter_and = QRadioButton("&&")
    window._human_design_gate_filter_or = QRadioButton("OR")
    hd_gate_group = QButtonGroup(window)
    hd_gate_group.setExclusive(True)
    hd_gate_group.addButton(window._human_design_gate_filter_and)
    hd_gate_group.addButton(window._human_design_gate_filter_or)
    window._human_design_gate_filter_and.setChecked(True)
    hd_gate_group.buttonClicked.connect(window._on_filter_changed)
    hd_gates_row.addWidget(window._human_design_gate_filter_and)
    hd_gates_row.addWidget(window._human_design_gate_filter_or)
    human_design_group_layout.addLayout(hd_gates_row)

    hd_type_row = QHBoxLayout()
    hd_type_row.addWidget(QLabel("Type"))
    window._human_design_type_filter_combo = QComboBox()
    apply_default_dropdown_style(window._human_design_type_filter_combo)
    window._human_design_type_filter_combo.addItem("Any", "Any")
    window._human_design_type_filter_combo.addItem("Manifestor", "Manifestor")
    window._human_design_type_filter_combo.addItem("Generator", "Generator")
    window._human_design_type_filter_combo.addItem("Manifesting Generator", "Manifesting Generator")
    window._human_design_type_filter_combo.addItem("Projector", "Projector")
    set_dropdown_width_chars(window._human_design_type_filter_combo, 22)
    window._human_design_type_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    hd_type_row.addWidget(window._human_design_type_filter_combo)
    human_design_group_layout.addLayout(hd_type_row)

    hd_profile_row = QHBoxLayout()
    hd_profile_row.addWidget(QLabel("Profile"))
    window._human_design_profile_filter_combo = QComboBox()
    apply_default_dropdown_style(window._human_design_profile_filter_combo)
    window._human_design_profile_filter_combo.addItem("Any", "Any")
    for profile_label in getattr(window, "HD_STANDARD_PROFILES", ()):
        window._human_design_profile_filter_combo.addItem(profile_label, profile_label)
    set_dropdown_width_chars(window._human_design_profile_filter_combo, 3)
    window._human_design_profile_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    hd_profile_row.addWidget(window._human_design_profile_filter_combo)
    human_design_group_layout.addLayout(hd_profile_row)

    hd_defined_centers_row = QHBoxLayout()
    hd_defined_centers_row.addWidget(QLabel("Defined:"))
    for _ in range(3):
        center_combo = QComboBox()
        apply_default_dropdown_style(center_combo)
        center_combo.addItem("Any", "Any")
        for center_label in getattr(window, "HD_DEFINED_CENTER_ORDER", ()):
            center_combo.addItem(center_label, center_label)
        set_dropdown_width_chars(center_combo, 11)
        center_combo.currentIndexChanged.connect(window._on_filter_changed)
        window._human_design_defined_center_filters.append(center_combo)
        hd_defined_centers_row.addWidget(center_combo)
    window._human_design_defined_center_filter_and = QRadioButton("&&")
    window._human_design_defined_center_filter_or = QRadioButton("OR")
    hd_defined_center_group = QButtonGroup(window)
    hd_defined_center_group.setExclusive(True)
    hd_defined_center_group.addButton(window._human_design_defined_center_filter_and)
    hd_defined_center_group.addButton(window._human_design_defined_center_filter_or)
    window._human_design_defined_center_filter_and.setChecked(True)
    hd_defined_center_group.buttonClicked.connect(window._on_filter_changed)
    hd_defined_centers_row.addWidget(window._human_design_defined_center_filter_and)
    hd_defined_centers_row.addWidget(window._human_design_defined_center_filter_or)
    human_design_group_layout.addLayout(hd_defined_centers_row)
    layout.addWidget(human_design_section)

    #Search: year first encountered
    year_first_encountered_section, year_first_encountered_group_layout = add_collapsible_section(
        "💭Year 1st Encountered" #year user first encountered
    )
    year_first_encountered_range_row = QHBoxLayout()
    year_first_encountered_range_row.addWidget(QLabel("Earliest"))
    window._year_first_encountered_earliest_input = QLineEdit()
    window._year_first_encountered_earliest_input.setMaxLength(4)
    window._year_first_encountered_earliest_input.setFixedWidth(56)
    window._year_first_encountered_earliest_input.setPlaceholderText("YYYY")
    window._year_first_encountered_earliest_input.setValidator(
        QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, window)
    )
    window._year_first_encountered_earliest_input.textChanged.connect(window._on_filter_changed)
    year_first_encountered_range_row.addWidget(window._year_first_encountered_earliest_input)
    year_first_encountered_range_row.addSpacing(10)
    year_first_encountered_range_row.addWidget(QLabel("Latest"))
    window._year_first_encountered_latest_input = QLineEdit()
    window._year_first_encountered_latest_input.setMaxLength(4)
    window._year_first_encountered_latest_input.setFixedWidth(56)
    window._year_first_encountered_latest_input.setPlaceholderText("YYYY")
    window._year_first_encountered_latest_input.setValidator(
        QIntValidator(NATAL_CHART_MIN_YEAR, NATAL_CHART_MAX_YEAR, window)
    )
    window._year_first_encountered_latest_input.textChanged.connect(window._on_filter_changed)
    year_first_encountered_range_row.addWidget(window._year_first_encountered_latest_input)
    year_first_encountered_range_row.addStretch(1)
    year_first_encountered_group_layout.addLayout(year_first_encountered_range_row)

    year_first_encountered_blank_row = QHBoxLayout()
    window._year_first_encountered_blank_checkbox = QuadStateSlider("blank")
    window._year_first_encountered_blank_checkbox.modeChanged.connect(window._on_filter_changed)
    year_first_encountered_blank_row.addWidget(window._year_first_encountered_blank_checkbox)
    year_first_encountered_blank_row.addStretch(1)
    year_first_encountered_group_layout.addLayout(year_first_encountered_blank_row)
    layout.addWidget(year_first_encountered_section)

    sentiment_section, sentiment_group_layout = add_collapsible_section("💭Sentiment")

    #Search: Sentiments section
    sentiment_mode_layout = QHBoxLayout()
    sentiment_mode_layout.addWidget(QLabel("Sentiments"))
    sentiment_mode_layout.addStretch(1)
    window.sentiment_filter_and = QRadioButton("AND")
    window.sentiment_filter_or = QRadioButton("OR")
    window.sentiment_filter_group = QButtonGroup(window)
    window.sentiment_filter_group.setExclusive(True)
    window.sentiment_filter_group.addButton(window.sentiment_filter_and)
    window.sentiment_filter_group.addButton(window.sentiment_filter_or)
    window.sentiment_filter_and.setChecked(True)
    # Use group-level click handling so we only refresh once per selection
    # change and avoid transient states where neither option is checked.
    window.sentiment_filter_group.buttonClicked.connect(window._on_filter_changed)
    sentiment_mode_layout.addWidget(window.sentiment_filter_and)
    sentiment_mode_layout.addWidget(window.sentiment_filter_or)
    sentiment_group_layout.addLayout(sentiment_mode_layout)
    sentiment_layout = QGridLayout()
    sentiment_layout.setContentsMargins(0, 0, 0, 0)
    window.sentiment_filter_checkboxes = {}
    sentiment_rows = (len(SEARCH_SENTIMENT_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_SENTIMENT_OPTIONS):
        checkbox = QuadStateSlider(label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.sentiment_filter_checkboxes[label] = checkbox
        row = idx % sentiment_rows
        col = idx // sentiment_rows
        sentiment_layout.addWidget(checkbox, row, col)
    sentiment_group_layout.addLayout(sentiment_layout)

    sentiment_intensity_row = QHBoxLayout()
    sentiment_intensity_row.addWidget(QLabel("💖"))
    window._positive_sentiment_intensity_min_input = QLineEdit()
    window._positive_sentiment_intensity_min_input.setFixedWidth(44)
    window._positive_sentiment_intensity_min_input.setMaxLength(2)
    window._positive_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, window))
    window._positive_sentiment_intensity_min_input.setPlaceholderText("min")
    window._positive_sentiment_intensity_min_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._positive_sentiment_intensity_min_input)
    sentiment_intensity_row.addWidget(QLabel("max"))
    window._positive_sentiment_intensity_max_input = QLineEdit()
    window._positive_sentiment_intensity_max_input.setFixedWidth(44)
    window._positive_sentiment_intensity_max_input.setMaxLength(2)
    window._positive_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, window))
    window._positive_sentiment_intensity_max_input.setPlaceholderText("max")
    window._positive_sentiment_intensity_max_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._positive_sentiment_intensity_max_input)
    sentiment_intensity_row.addSpacing(10)
    sentiment_intensity_row.addWidget(QLabel("💔"))
    window._negative_sentiment_intensity_min_input = QLineEdit()
    window._negative_sentiment_intensity_min_input.setFixedWidth(44)
    window._negative_sentiment_intensity_min_input.setMaxLength(2)
    window._negative_sentiment_intensity_min_input.setValidator(QIntValidator(1, 10, window))
    window._negative_sentiment_intensity_min_input.setPlaceholderText("min")
    window._negative_sentiment_intensity_min_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._negative_sentiment_intensity_min_input)
    sentiment_intensity_row.addWidget(QLabel("max"))
    window._negative_sentiment_intensity_max_input = QLineEdit()
    window._negative_sentiment_intensity_max_input.setFixedWidth(44)
    window._negative_sentiment_intensity_max_input.setMaxLength(2)
    window._negative_sentiment_intensity_max_input.setValidator(QIntValidator(1, 10, window))
    window._negative_sentiment_intensity_max_input.setPlaceholderText("max")
    window._negative_sentiment_intensity_max_input.textChanged.connect(window._on_filter_changed)
    sentiment_intensity_row.addWidget(window._negative_sentiment_intensity_max_input)
    sentiment_intensity_row.addStretch(1)
    sentiment_group_layout.addLayout(sentiment_intensity_row)

    familiarity_row = QHBoxLayout()
    familiarity_row.addWidget(QLabel("Familiarity"))
    window._familiarity_min_input = QLineEdit()
    window._familiarity_min_input.setFixedWidth(44)
    window._familiarity_min_input.setMaxLength(2)
    window._familiarity_min_input.setValidator(QIntValidator(1, 10, window))
    window._familiarity_min_input.setPlaceholderText("min")
    window._familiarity_min_input.textChanged.connect(window._on_filter_changed)
    familiarity_row.addWidget(window._familiarity_min_input)
    familiarity_row.addWidget(QLabel("max"))
    window._familiarity_max_input = QLineEdit()
    window._familiarity_max_input.setFixedWidth(44)
    window._familiarity_max_input.setMaxLength(2)
    window._familiarity_max_input.setValidator(QIntValidator(1, 10, window))
    window._familiarity_max_input.setPlaceholderText("max")
    window._familiarity_max_input.textChanged.connect(window._on_filter_changed)
    familiarity_row.addWidget(window._familiarity_max_input)
    familiarity_row.addStretch(1)
    sentiment_group_layout.addLayout(familiarity_row)

    layout.addWidget(sentiment_section)

    #Search: Alignment section
    alignment_section, alignment_group_layout = add_collapsible_section("💭Alignment")
    alignment_range_row = QHBoxLayout()
    alignment_range_row.addWidget(QLabel("💭Alignment"))
    window._alignment_score_min_input = QLineEdit()
    window._alignment_score_min_input.setFixedWidth(44)
    window._alignment_score_min_input.setMaxLength(3)
    window._alignment_score_min_input.setValidator(QIntValidator(-10, 10, window))
    window._alignment_score_min_input.setPlaceholderText("min")
    window._alignment_score_min_input.textChanged.connect(window._on_filter_changed)
    alignment_range_row.addWidget(window._alignment_score_min_input)
    alignment_range_row.addWidget(QLabel("max"))
    window._alignment_score_max_input = QLineEdit()
    window._alignment_score_max_input.setFixedWidth(44)
    window._alignment_score_max_input.setMaxLength(3)
    window._alignment_score_max_input.setValidator(QIntValidator(-10, 10, window))
    window._alignment_score_max_input.setPlaceholderText("max")
    window._alignment_score_max_input.textChanged.connect(window._on_filter_changed)
    alignment_range_row.addWidget(window._alignment_score_max_input)
    alignment_range_row.addStretch(1)
    alignment_group_layout.addLayout(alignment_range_row)

    window._alignment_score_blank_checkbox = QCheckBox("no alignment assigned")
    window._alignment_score_blank_checkbox.stateChanged.connect(window._on_filter_changed)
    alignment_group_layout.addWidget(window._alignment_score_blank_checkbox)
    layout.addWidget(alignment_section)

    #Search: relationship types section
    relationship_section, relationship_group_layout = add_collapsible_section(
        "💭Relationships"
    )
    relationship_mode_layout = QHBoxLayout()
    relationship_mode_layout.addWidget(QLabel("Relationship type"))
    relationship_mode_layout.addStretch(1)
    window.relationship_filter_and = QRadioButton("AND")
    window.relationship_filter_or = QRadioButton("OR")
    window.relationship_filter_group = QButtonGroup(window)
    window.relationship_filter_group.setExclusive(True)
    window.relationship_filter_group.addButton(window.relationship_filter_and)
    window.relationship_filter_group.addButton(window.relationship_filter_or)
    window.relationship_filter_and.setChecked(True)
    window.relationship_filter_group.buttonClicked.connect(window._on_filter_changed)
    relationship_mode_layout.addWidget(window.relationship_filter_and)
    relationship_mode_layout.addWidget(window.relationship_filter_or)
    relationship_group_layout.addLayout(relationship_mode_layout)

    relationship_layout = QGridLayout()
    relationship_layout.setContentsMargins(0, 0, 0, 0)
    window.relationship_filter_checkboxes = {}
    relationship_rows = (len(SEARCH_RELATIONSHIP_TYPE_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_RELATIONSHIP_TYPE_OPTIONS):
        checkbox = QuadStateSlider(label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.relationship_filter_checkboxes[label] = checkbox
        row = idx % relationship_rows
        col = idx // relationship_rows
        relationship_layout.addWidget(checkbox, row, col)
    relationship_group_layout.addLayout(relationship_layout)
    layout.addWidget(relationship_section)

    #Search: D&D section
    dnd_species_section, dnd_species_group_layout = add_collapsible_section(
        "⚔️D&&D-ification"
    )
    class_filter_row = QHBoxLayout()
    class_filter_row.addWidget(QLabel("Top 3 Classes"))
    window.dnd_class_filter_combo = QComboBox()
    apply_default_dropdown_style(window.dnd_class_filter_combo)
    window.dnd_class_filter_combo.addItem("Any", "Any")
    for class_definition in DND_CLASSES.values():
        window.dnd_class_filter_combo.addItem(class_definition.display_name, class_definition.display_name)
    window.dnd_class_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    class_filter_row.addWidget(window.dnd_class_filter_combo, 1)
    dnd_species_group_layout.addLayout(class_filter_row)

    species_filter_row = QHBoxLayout()
    species_filter_row.addWidget(QLabel("Top 3 Species"))
    window.species_filter_combo = QComboBox()
    apply_default_dropdown_style(window.species_filter_combo)
    window.species_filter_combo.addItem("Any", "Any")
    for species in SPECIES_FAMILIES:
        window.species_filter_combo.addItem(species, species)
    window.species_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    species_filter_row.addWidget(window.species_filter_combo, 1)
    dnd_species_group_layout.addLayout(species_filter_row)

    dnd_stats_header = QLabel("Stat ranges")
    dnd_stats_header.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    dnd_species_group_layout.addWidget(dnd_stats_header)
    dnd_stat_grid = QGridLayout()
    dnd_stat_grid.setContentsMargins(0, 0, 0, 0)
    dnd_stat_grid.setHorizontalSpacing(14)
    dnd_stat_grid.setVerticalSpacing(4)
    dnd_stat_filter_order = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    for idx, stat_key in enumerate(dnd_stat_filter_order):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        row_layout.addWidget(QLabel(stat_key))
        row_layout.addWidget(QLabel("min:"))
        min_input = QLineEdit()
        min_input.setFixedWidth(40)
        min_input.setMaxLength(2)
        min_input.setValidator(QIntValidator(1, 30, window))
        min_input.setPlaceholderText("min")
        min_input.textChanged.connect(window._on_filter_changed)
        row_layout.addWidget(min_input)
        row_layout.addWidget(QLabel("max:"))
        max_input = QLineEdit()
        max_input.setFixedWidth(40)
        max_input.setMaxLength(2)
        max_input.setValidator(QIntValidator(1, 30, window))
        max_input.setPlaceholderText("max")
        max_input.textChanged.connect(window._on_filter_changed)
        row_layout.addWidget(max_input)
        row_layout.addStretch(1)
        window._dnd_stat_filter_min_inputs[stat_key] = min_input
        window._dnd_stat_filter_max_inputs[stat_key] = max_input
        row = idx % 3
        col = idx // 3
        dnd_stat_grid.addLayout(row_layout, row, col)
    dnd_species_group_layout.addLayout(dnd_stat_grid)
    layout.addWidget(dnd_species_section)

    #Search: Mortality section
    mortality_section, mortality_section_layout = add_collapsible_section("Mortality")
    mortality_row = QHBoxLayout()
    window.living_checkbox = QuadStateSlider("living")
    window.living_checkbox.modeChanged.connect(window._on_filter_changed)
    mortality_row.addWidget(window.living_checkbox)
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
    window.generation_filter_checkboxes = {}
    generation_rows = (len(GENERATION_FILTER_OPTIONS) + 1) // 2
    for idx, generation_name in enumerate(GENERATION_FILTER_OPTIONS):
        checkbox = QuadStateSlider(generation_name)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.generation_filter_checkboxes[generation_name] = checkbox
        row = idx % generation_rows
        col = idx // generation_rows
        generation_layout.addWidget(checkbox, row, col)
    mortality_section_layout.addLayout(generation_layout)

    layout.addWidget(mortality_section)

    #Search: gender section
    gender_section, gender_group_layout = add_collapsible_section("Gender")
    gender_mode_layout = QHBoxLayout()
    gender_mode_layout.addWidget(QLabel("Gender"))
    gender_mode_layout.addStretch(1)
    window.gender_filter_and = QRadioButton("AND")
    window.gender_filter_or = QRadioButton("OR")
    window.gender_filter_group = QButtonGroup(window)
    window.gender_filter_group.setExclusive(True)
    window.gender_filter_group.addButton(window.gender_filter_and)
    window.gender_filter_group.addButton(window.gender_filter_or)
    window.gender_filter_and.setChecked(True)
    window.gender_filter_group.buttonClicked.connect(window._on_filter_changed)
    gender_mode_layout.addWidget(window.gender_filter_and)
    gender_mode_layout.addWidget(window.gender_filter_or)
    gender_group_layout.addLayout(gender_mode_layout)

    gender_layout = QGridLayout()
    gender_layout.setContentsMargins(0, 0, 0, 0)
    window.gender_filter_checkboxes = {}
    gender_rows = (len(SEARCH_GENDER_OPTIONS) + 1) // 2
    for idx, label in enumerate(SEARCH_GENDER_OPTIONS):
        checkbox_label = "blank" if label == "none" else label
        checkbox = QuadStateSlider(checkbox_label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.gender_filter_checkboxes[label] = checkbox
        row = idx % gender_rows
        col = idx // gender_rows
        gender_layout.addWidget(checkbox, row, col)
    gender_group_layout.addLayout(gender_layout)

    gender_guessed_layout = QHBoxLayout()
    gender_guessed_layout.addWidget(QLabel("Gender Guessed"))
    window.gender_guessed_filter_combo = QComboBox()
    apply_default_dropdown_style(window.gender_guessed_filter_combo)
    for label, value in SEARCH_GENDER_GUESSED_OPTIONS:
        window.gender_guessed_filter_combo.addItem(label, value)
    window.gender_guessed_filter_combo.currentIndexChanged.connect(window._on_filter_changed)
    gender_guessed_layout.addWidget(window.gender_guessed_filter_combo)
    gender_group_layout.addLayout(gender_guessed_layout)

    layout.addWidget(gender_section)

    #Search: Locations section
    locations_section, locations_group_layout = add_collapsible_section("Locations")

    country_row = QHBoxLayout()
    country_row.addWidget(QLabel("Country"))
    window._search_location_country_input = QLineEdit()
    window._search_location_country_input.setPlaceholderText("e.g. USA, UK, Italy")
    window._search_location_country_input.textChanged.connect(window._on_filter_changed)
    window._search_location_country_input.returnPressed.connect(window._on_filter_changed)
    country_row.addWidget(window._search_location_country_input, 1)
    locations_group_layout.addLayout(country_row)

    city_row = QHBoxLayout()
    city_row.addWidget(QLabel("City"))
    window._search_location_city_input = QLineEdit()
    window._search_location_city_input.setPlaceholderText("e.g. London")
    window._search_location_city_input.textChanged.connect(window._on_filter_changed)
    window._search_location_city_input.returnPressed.connect(window._on_filter_changed)
    city_row.addWidget(window._search_location_city_input, 1)
    locations_group_layout.addLayout(city_row)

    state_row = QHBoxLayout()
    state_row.addWidget(QLabel("State"))
    window._search_location_state_input = QLineEdit()
    window._search_location_state_input.setPlaceholderText("e.g. CA, NY, PR")
    window._search_location_state_input.textChanged.connect(window._on_filter_changed)
    window._search_location_state_input.returnPressed.connect(window._on_filter_changed)
    state_row.addWidget(window._search_location_state_input, 1)
    locations_group_layout.addLayout(state_row)
    layout.addWidget(locations_section)

    #Search: chart type section
    chart_type_section, chart_type_group_layout = add_collapsible_section(
        "Chart Type"
    )
    chart_type_layout = QGridLayout()
    chart_type_layout.setContentsMargins(0, 0, 0, 0)
    window.chart_type_filter_checkboxes = {}
    chart_type_rows = (len(SOURCE_OPTIONS) + 1) // 2
    for idx, (source_label, source_value) in enumerate(SOURCE_OPTIONS):
        checkbox = QuadStateSlider(source_label)
        checkbox.modeChanged.connect(window._on_filter_changed)
        window.chart_type_filter_checkboxes[source_value] = checkbox
        row = idx % chart_type_rows
        col = idx // chart_type_rows
        chart_type_layout.addWidget(checkbox, row, col)
    chart_type_group_layout.addLayout(chart_type_layout)
    layout.addWidget(chart_type_section)

    predictability_section, predictability_group_layout = add_collapsible_section(
        "💭Predictability"
    )
    predictability_range_layout = QGridLayout()
    predictability_range_layout.setContentsMargins(0, 0, 0, 0)
    predictability_range_layout.addWidget(QLabel("Min"), 0, 0)
    window._matched_expectations_min_input = QLineEdit()
    window._matched_expectations_min_input.setPlaceholderText("0")
    window._matched_expectations_min_input.setValidator(QIntValidator(0, 9, window))
    window._matched_expectations_min_input.textChanged.connect(window._on_filter_changed)
    predictability_range_layout.addWidget(window._matched_expectations_min_input, 0, 1)
    predictability_range_layout.addWidget(QLabel("Max"), 1, 0)
    window._matched_expectations_max_input = QLineEdit()
    window._matched_expectations_max_input.setPlaceholderText("9")
    window._matched_expectations_max_input.setValidator(QIntValidator(0, 9, window))
    window._matched_expectations_max_input.textChanged.connect(window._on_filter_changed)
    predictability_range_layout.addWidget(window._matched_expectations_max_input, 1, 1)
    predictability_group_layout.addLayout(predictability_range_layout)
    window._matched_expectations_blank_checkbox = QCheckBox("include blank")
    window._matched_expectations_blank_checkbox.toggled.connect(window._on_filter_changed)
    predictability_group_layout.addWidget(window._matched_expectations_blank_checkbox)
    layout.addWidget(predictability_section)

    #Search: Notes section
    notes_section, notes_group_layout = add_collapsible_section("Notes")

    comments_row = QHBoxLayout()
    window._notes_comments_filter_checkbox = QuadStateSlider("Comments")
    window._notes_comments_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    comments_row.addWidget(window._notes_comments_filter_checkbox)
    window._notes_comments_filter_input = QLineEdit()
    window._notes_comments_filter_input.setPlaceholderText("contains text")
    window._notes_comments_filter_input.textChanged.connect(window._on_filter_changed)
    comments_row.addWidget(window._notes_comments_filter_input, 1)
    notes_group_layout.addLayout(comments_row)

    bio_row = QHBoxLayout()
    window._notes_bio_filter_checkbox = QuadStateSlider("Bio")
    window._notes_bio_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    bio_row.addWidget(window._notes_bio_filter_checkbox)
    window._notes_bio_filter_input = QLineEdit()
    window._notes_bio_filter_input.setPlaceholderText("contains text")
    window._notes_bio_filter_input.textChanged.connect(window._on_filter_changed)
    bio_row.addWidget(window._notes_bio_filter_input, 1)
    notes_group_layout.addLayout(bio_row)

    rectification_row = QHBoxLayout()
    window._notes_rectification_filter_checkbox = QuadStateSlider("Rectification")
    window._notes_rectification_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    rectification_row.addWidget(window._notes_rectification_filter_checkbox)
    window._notes_rectification_filter_input = QLineEdit()
    window._notes_rectification_filter_input.setPlaceholderText("contains text")
    window._notes_rectification_filter_input.textChanged.connect(window._on_filter_changed)
    rectification_row.addWidget(window._notes_rectification_filter_input, 1)
    notes_group_layout.addLayout(rectification_row)

    source_row = QHBoxLayout()
    window._notes_source_filter_checkbox = QuadStateSlider("Source")
    window._notes_source_filter_checkbox.modeChanged.connect(window._on_filter_changed)
    source_row.addWidget(window._notes_source_filter_checkbox)
    window._notes_source_filter_input = QLineEdit()
    window._notes_source_filter_input.setPlaceholderText("contains text")
    window._notes_source_filter_input.textChanged.connect(window._on_filter_changed)
    source_row.addWidget(window._notes_source_filter_input, 1)
    notes_group_layout.addLayout(source_row)

    layout.addWidget(notes_section)

    button_row = QHBoxLayout()
    button_row.addStretch(1)
    clear_button = QPushButton("Clear filters")
    clear_button.clicked.connect(lambda: window._clear_filters())
    button_row.addWidget(clear_button)
    layout.addLayout(button_row)

    layout.addStretch(1)
    return panel
