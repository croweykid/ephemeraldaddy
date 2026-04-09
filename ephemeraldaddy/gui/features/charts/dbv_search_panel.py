"""Database View right-hand search panel mixin methods."""

from __future__ import annotations


def _ensure_dbv_search_panel_symbols() -> None:
    """Populate globals from app module so extracted methods keep behavior unchanged."""
    from ephemeraldaddy.gui import app as app_module

    symbol_names = [
        "ASPECT_DEFS",
        "COLLAPSIBLE_SECTION_CONTENT_STYLE",
        "DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE",
        "DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS",
        "DATABASE_ANALYTICS_SUBHEADER_STYLE",
        "DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE",
        "DATABASE_VIEW_PANEL_HEADER_STYLE",
        "DEFAULT_DROPDOWN_STYLE",
        "DND_CLASS_ALIASES",
        "DND_CLASS_FILTER_OPTIONS",
        "DND_SPECIES_LIST",
        "EmojiTiledPanel",
        "GENERATION_FILTER_OPTIONS",
        "GEN_POP_UNSUPPORTED_SIGN_DISTRIBUTION_MODES",
        "GENDER_DROPDOWN_OPTIONS",
        "LILITH_CALCULATION_TRUE",
        "MainWindow",
        "QApplication",
        "QButtonGroup",
        "QCheckBox",
        "QComboBox",
        "QDate",
        "QFrame",
        "QFormLayout",
        "QGridLayout",
        "QHBoxLayout",
        "QIntValidator",
        "QLabel",
        "QLineEdit",
        "QListWidget",
        "QListWidgetItem",
        "QCompleter",
        "QMessageBox",
        "QPushButton",
        "QRadioButton",
        "QSizePolicy",
        "QToolButton",
        "QTime",
        "QVBoxLayout",
        "QWidget",
        "Qt",
        "QuadStateSlider",
        "RIGHT_PANEL_SCROLLBAR_STYLE",
        "RODDEN_RATING",
        "SEARCH_GENDER_GUESSED_OPTIONS",
        "SEARCH_GENDER_OPTIONS",
        "SOURCE_OPTIONS",
        "SOURCE_PUBLIC_DB",
        "SOURCE_VISIBILITY_ALL",
        "SOURCE_VISIBILITY_EVENT_ONLY",
        "SOURCE_VISIBILITY_NO_EVENTS",
        "ZODIAC_NAMES",
        "_calculate_dominant_planet_weights",
        "_calculate_dominant_sign_weights",
        "_new_debug_action_id",
        "configure_collapsible_header_toggle",
        "logger",
        "parse_astrotheme_profile",
        "parse_tag_text",
        "render_tag_chip_preview",
        "save_chart",
        "search_astrotheme_profile_url",
        "set_current_chart",
        "set_lilith_calculation_mode",
    ]

    g = globals()
    for name in symbol_names:
        if name in g:
            continue
        g[name] = getattr(app_module, name)


class DatabaseViewSearchPanelMixin:
    def _build_search_panel(self) -> QWidget:
        _ensure_dbv_search_panel_symbols()
        # Search panel (right sidebar).
        panel = EmojiTiledPanel("🔎", font_size=100, opacity=0.12) #Search panel background
        panel.setMinimumWidth(260)
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
        self.incomplete_birthdate_checkbox = QuadStateSlider("incomplete birthdate (placeholder chart)")
        self.incomplete_birthdate_checkbox.modeChanged.connect(self._on_filter_changed)
        incomplete_birthdate_row.addWidget(self.incomplete_birthdate_checkbox)
        incomplete_birthdate_row.addStretch(1)
        birth_info_status_layout.addLayout(incomplete_birthdate_row)

        birth_status_mode_row = QHBoxLayout()
        birth_status_mode_row.addWidget(QLabel("🐣Time:"))
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
        self.birthtime_unknown_checkbox = QuadStateSlider("unknown")
        self.birthtime_unknown_checkbox.modeChanged.connect(self._on_filter_changed)
        self.retconned_checkbox = QuadStateSlider("rectified")
        self.retconned_checkbox.modeChanged.connect(self._on_filter_changed)
        birth_filters_row.addWidget(self.birthtime_unknown_checkbox)
        birth_filters_row.addWidget(self.retconned_checkbox)
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
        self.data_rating_filter_checkboxes = {}
        rodden_rows = (len(RODDEN_RATING) + 1) // 2
        for idx, rating in enumerate(RODDEN_RATING):
            grade = str(rating.get("grade", "")).strip()
            if not grade:
                continue
            checkbox = QuadStateSlider(grade)
            checkbox.modeChanged.connect(self._on_filter_changed)
            self.data_rating_filter_checkboxes[grade] = checkbox
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

    #Search: Aspects section
        aspect_section, aspect_group_layout = add_collapsible_section("🪐Aspect") #astrological aspect

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

    #Search: Dominant Modes section
        dominant_mode_section, dominant_mode_group_layout = add_collapsible_section(
            "🪐Dominant Modes" #dominant astrological modes
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
            element_combo.addItem("Any", "Any")
            for element in ("Fire", "Earth", "Air", "Water"):
                element_combo.addItem(element, element)
            element_combo.currentIndexChanged.connect(self._on_astrological_filter_changed)

            filter_and = QRadioButton("AND")
            filter_or = QRadioButton("OR")
            filter_group = QButtonGroup(dominant_element_row)
            filter_group.setExclusive(True)
            filter_group.addButton(filter_and)
            filter_group.addButton(filter_or)
            filter_and.setChecked(True)
            filter_group.buttonClicked.connect(self._on_filter_changed)

            dominant_element_row_layout.addWidget(QLabel("🧪"))
            dominant_element_row_layout.addWidget(element_combo, 1)
            dominant_element_row_layout.addWidget(filter_and)
            dominant_element_row_layout.addWidget(filter_or)

            self._dominant_element_filters.append({
                "element": element_combo,
                "and": filter_and,
                "or": filter_or,
            })
            dominant_element_layout.addRow(dominant_element_row)

        layout.addWidget(dominant_element_section)

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
            channel_combo.currentIndexChanged.connect(self._on_filter_changed)
            self._human_design_channel_filters.append(channel_combo)
            hd_channels_row.addWidget(channel_combo, 1)
        self._human_design_channel_filter_and = QRadioButton("AND")
        self._human_design_channel_filter_or = QRadioButton("OR")
        hd_channel_group = QButtonGroup(self)
        hd_channel_group.setExclusive(True)
        hd_channel_group.addButton(self._human_design_channel_filter_and)
        hd_channel_group.addButton(self._human_design_channel_filter_or)
        self._human_design_channel_filter_and.setChecked(True)
        hd_channel_group.buttonClicked.connect(self._on_filter_changed)
        hd_channels_row.addWidget(self._human_design_channel_filter_and)
        hd_channels_row.addWidget(self._human_design_channel_filter_or)
        human_design_group_layout.addLayout(hd_channels_row)

        hd_gates_row = QHBoxLayout()
        hd_gates_row.addWidget(QLabel("Gates"))
        for _ in range(3):
            gate_combo = QComboBox()
            apply_default_dropdown_style(gate_combo)
            gate_combo.addItem("Any", "Any")
            for gate_value in range(1, 65):
                gate_combo.addItem(str(gate_value), gate_value)
            gate_combo.currentIndexChanged.connect(self._on_filter_changed)
            self._human_design_gate_filters.append(gate_combo)
            hd_gates_row.addWidget(gate_combo, 1)
        self._human_design_gate_filter_and = QRadioButton("AND")
        self._human_design_gate_filter_or = QRadioButton("OR")
        hd_gate_group = QButtonGroup(self)
        hd_gate_group.setExclusive(True)
        hd_gate_group.addButton(self._human_design_gate_filter_and)
        hd_gate_group.addButton(self._human_design_gate_filter_or)
        self._human_design_gate_filter_and.setChecked(True)
        hd_gate_group.buttonClicked.connect(self._on_filter_changed)
        hd_gates_row.addWidget(self._human_design_gate_filter_and)
        hd_gates_row.addWidget(self._human_design_gate_filter_or)
        human_design_group_layout.addLayout(hd_gates_row)

        hd_type_row = QHBoxLayout()
        hd_type_row.addWidget(QLabel("Type"))
        self._human_design_type_filter_combo = QComboBox()
        apply_default_dropdown_style(self._human_design_type_filter_combo)
        self._human_design_type_filter_combo.addItem("Any", "Any")
        self._human_design_type_filter_combo.addItem("Manifestor", "Manifestor")
        self._human_design_type_filter_combo.addItem("Generator", "Generator")
        self._human_design_type_filter_combo.addItem("Manifesting Generator", "Manifesting Generator")
        self._human_design_type_filter_combo.addItem("Projector", "Projector")
        self._human_design_type_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        hd_type_row.addWidget(self._human_design_type_filter_combo, 1)
        human_design_group_layout.addLayout(hd_type_row)
        layout.addWidget(human_design_section)

    #Search: year first encountered
        year_first_encountered_section, year_first_encountered_group_layout = add_collapsible_section(
            "💭Year 1st Encountered" #year user first encountered
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

        sentiment_section, sentiment_group_layout = add_collapsible_section("💭Sentiment")

    #Search: Sentiments section
        sentiment_mode_layout = QHBoxLayout()
        sentiment_mode_layout.addWidget(QLabel("Sentiments"))
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

    #Search: Alignment section
        alignment_section, alignment_group_layout = add_collapsible_section("💭Alignment")
        alignment_range_row = QHBoxLayout()
        alignment_range_row.addWidget(QLabel("💭Alignment"))
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

    #Search: relationship types section
        relationship_section, relationship_group_layout = add_collapsible_section(
            "💭Relationships"
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

    #Search: D&D section
        dnd_species_section, dnd_species_group_layout = add_collapsible_section(
            "⚔️D&&D-ification"
        )
        class_filter_row = QHBoxLayout()
        class_filter_row.addWidget(QLabel("Top 3 Classes"))
        self.dnd_class_filter_combo = QComboBox()
        apply_default_dropdown_style(self.dnd_class_filter_combo)
        self.dnd_class_filter_combo.addItem("Any", "Any")
        for class_definition in DND_CLASSES.values():
            self.dnd_class_filter_combo.addItem(class_definition.display_name, class_definition.display_name)
        self.dnd_class_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        class_filter_row.addWidget(self.dnd_class_filter_combo, 1)
        dnd_species_group_layout.addLayout(class_filter_row)

        species_filter_row = QHBoxLayout()
        species_filter_row.addWidget(QLabel("Top 3 Species"))
        self.species_filter_combo = QComboBox()
        apply_default_dropdown_style(self.species_filter_combo)
        self.species_filter_combo.addItem("Any", "Any")
        for species in SPECIES_FAMILIES:
            self.species_filter_combo.addItem(species, species)
        self.species_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        species_filter_row.addWidget(self.species_filter_combo, 1)
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
            min_input.setValidator(QIntValidator(1, 30, self))
            min_input.setPlaceholderText("min")
            min_input.textChanged.connect(self._on_filter_changed)
            row_layout.addWidget(min_input)
            row_layout.addWidget(QLabel("max:"))
            max_input = QLineEdit()
            max_input.setFixedWidth(40)
            max_input.setMaxLength(2)
            max_input.setValidator(QIntValidator(1, 30, self))
            max_input.setPlaceholderText("max")
            max_input.textChanged.connect(self._on_filter_changed)
            row_layout.addWidget(max_input)
            row_layout.addStretch(1)
            self._dnd_stat_filter_min_inputs[stat_key] = min_input
            self._dnd_stat_filter_max_inputs[stat_key] = max_input
            row = idx % 3
            col = idx // 3
            dnd_stat_grid.addLayout(row_layout, row, col)
        dnd_species_group_layout.addLayout(dnd_stat_grid)
        layout.addWidget(dnd_species_section)

    #Search: Mortality section
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

    #Search: gender section
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

    #Search: Locations section
        locations_section, locations_group_layout = add_collapsible_section("Locations")

        country_row = QHBoxLayout()
        country_row.addWidget(QLabel("Country"))
        self._search_location_country_input = QLineEdit()
        self._search_location_country_input.setPlaceholderText("e.g. USA, UK, Italy")
        self._search_location_country_input.textChanged.connect(self._on_filter_changed)
        self._search_location_country_input.returnPressed.connect(self._on_filter_changed)
        country_row.addWidget(self._search_location_country_input, 1)
        locations_group_layout.addLayout(country_row)

        city_row = QHBoxLayout()
        city_row.addWidget(QLabel("City"))
        self._search_location_city_input = QLineEdit()
        self._search_location_city_input.setPlaceholderText("e.g. London")
        self._search_location_city_input.textChanged.connect(self._on_filter_changed)
        self._search_location_city_input.returnPressed.connect(self._on_filter_changed)
        city_row.addWidget(self._search_location_city_input, 1)
        locations_group_layout.addLayout(city_row)

        state_row = QHBoxLayout()
        state_row.addWidget(QLabel("State"))
        self._search_location_state_input = QLineEdit()
        self._search_location_state_input.setPlaceholderText("e.g. CA, NY, PR")
        self._search_location_state_input.textChanged.connect(self._on_filter_changed)
        self._search_location_state_input.returnPressed.connect(self._on_filter_changed)
        state_row.addWidget(self._search_location_state_input, 1)
        locations_group_layout.addLayout(state_row)
        layout.addWidget(locations_section)

    #Search: chart type section
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

    #Search: Notes section
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

    def _on_import_astrotheme_from_search_panel(self) -> None:
        _ensure_dbv_search_panel_symbols()
        raw_query = self.astrotheme_search_input.text().strip()
        debug_id = _new_debug_action_id("astrotheme_import")
        if not raw_query:
            QMessageBox.information(self, "Astrotheme import", "Enter a name or Astrotheme profile URL.")
            return
        logger.info("Astrotheme import started (id=%s query=%r).", debug_id, raw_query)

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
            logger.exception(
                "Astrotheme import failed during lookup/parse (id=%s query=%r): %s",
                debug_id,
                raw_query,
                exc,
            )
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
        parent_data_rating = str(profile_data.get("data_rating", "blank") or "blank")
        data_rating_index = parent.data_rating_combo.findData(parent_data_rating)
        parent.data_rating_combo.setCurrentIndex(max(0, data_rating_index))
        parent.source_edit.setPlainText(profile_data["profile_url"])
        parent.biography_edit.setPlainText(str(profile_data.get("biography", "") or ""))
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
        chart.data_rating = str(profile_data.get("data_rating", "blank") or "blank")
        chart.biography = str(profile_data.get("biography", "") or "")
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
            logger.exception(
                "Astrotheme import failed while saving chart (id=%s profile_url=%r): %s",
                debug_id,
                profile_data.get("profile_url"),
                exc,
            )
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
        logger.info("Astrotheme import completed (id=%s chart_id=%s).", debug_id, chart_id)

    def _apply_location_completer(self, line_edit: QLineEdit | None, choices: list[str]) -> None:
        _ensure_dbv_search_panel_symbols()
        if not isinstance(line_edit, QLineEdit):
            return
        completer = QCompleter(choices, line_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        line_edit.setCompleter(completer)

    def _update_location_completers(self) -> None:
        _ensure_dbv_search_panel_symbols()
        countries: set[str] = set()
        cities: set[str] = set()
        states: set[str] = set()
        chart_rows = getattr(self, "_chart_rows", [])
        for chart_row in chart_rows:
            birth_place = str(chart_row[5] if len(chart_row) > 5 else "" or "").strip()
            if not birth_place:
                continue
            country, city, state = self._normalized_location_components(birth_place)
            if country:
                countries.add(country)
            if city:
                cities.add(city)
            if state:
                states.add(state)

        self._apply_location_completer(
            getattr(self, "_search_location_country_input", None),
            sorted(countries),
        )
        self._apply_location_completer(
            getattr(self, "_search_location_city_input", None),
            sorted(cities),
        )
        self._apply_location_completer(
            getattr(self, "_search_location_state_input", None),
            sorted(states),
        )

    def _on_search_tags_changed(self, *_: object) -> None:
        _ensure_dbv_search_panel_symbols()
        tags = parse_tag_text(self.search_tags_input.text())
        render_tag_chip_preview(self.search_tags_preview_label, tags)
        self._refresh_search_tags_list(getattr(self, "_known_chart_tags", []))
        self._on_filter_changed()

    def _refresh_search_tags_list(self, known_tags: list[str]) -> None:
        _ensure_dbv_search_panel_symbols()
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
        _ensure_dbv_search_panel_symbols()
        tag_value = item.text().lstrip("✓").strip()
        if not tag_value:
            return
        self.search_tags_input.setText(tag_value)

    def _show_search_database_panel(self) -> None:
        _ensure_dbv_search_panel_symbols()
        self._show_right_panel("search")

    def _toggle_search_panel(self) -> None:
        _ensure_dbv_search_panel_symbols()
        if (
            self._right_panel_visible
            and self._active_right_panel == "search"
            and not self._is_right_panel_collapsed()
        ):
            self._set_right_panel_visible(False)
            return
        self._show_right_panel("search")

    def _searchable_bodies(self) -> list[tuple[str, str]]:
        _ensure_dbv_search_panel_symbols()
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
            (_display_body_label("Lilith"), "Lilith"),
            ("Part of Fortune", "Part of Fortune"),
            ("AS", "AS"),
            ("IC", "IC"),
            ("DS", "DS"),
            ("MC", "MC"),
        ]

    def _searchable_body_options(self) -> list[tuple[str, str]]:
        _ensure_dbv_search_panel_symbols()
        return [("Any", "Any"), *self._searchable_bodies()]

    def _on_filter_changed(self, *_: object) -> None:
        _ensure_dbv_search_panel_symbols()
        if self._suppress_filter_refresh:
            return
        self._filter_refresh_pending = True
        self._filter_refresh_timer.start()

    def _on_astrological_filter_changed(self, *_: object) -> None:
        _ensure_dbv_search_panel_symbols()
        self._auto_exclude_placeholders_for_astrological_filters()
        self._on_filter_changed()

    def _clear_filters(self, refresh: bool = True) -> None:
        _ensure_dbv_search_panel_symbols()
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
            if hasattr(self, "dnd_class_filter_combo") and self.dnd_class_filter_combo is not None:
                self.dnd_class_filter_combo.setCurrentIndex(0)
            self.species_filter_combo.setCurrentIndex(0)
            for min_input in self._dnd_stat_filter_min_inputs.values():
                min_input.setText("")
            for max_input in self._dnd_stat_filter_max_inputs.values():
                max_input.setText("")
            self.search_text_input.setText("")
            if self._search_location_country_input is not None:
                self._search_location_country_input.setText("")
            if self._search_location_city_input is not None:
                self._search_location_city_input.setText("")
            if self._search_location_state_input is not None:
                self._search_location_state_input.setText("")
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
            for checkbox in self.data_rating_filter_checkboxes.values():
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
            for channel_combo in self._human_design_channel_filters:
                channel_combo.setCurrentIndex(0)
            for gate_combo in self._human_design_gate_filters:
                gate_combo.setCurrentIndex(0)
            if self._human_design_channel_filter_or is not None:
                self._human_design_channel_filter_or.setChecked(False)
            if self._human_design_channel_filter_and is not None:
                self._human_design_channel_filter_and.setChecked(True)
            if self._human_design_gate_filter_or is not None:
                self._human_design_gate_filter_or.setChecked(False)
            if self._human_design_gate_filter_and is not None:
                self._human_design_gate_filter_and.setChecked(True)
            if self._human_design_type_filter_combo is not None:
                self._human_design_type_filter_combo.setCurrentIndex(0)
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
            for filters in self._dominant_element_filters:
                filters["element"].setCurrentIndex(0)
                filters["or"].setChecked(False)
                filters["and"].setChecked(True)
        finally:
            self._suppress_filter_refresh = False
        if refresh:
            self._on_filter_changed()

    def _reset_filters(self) -> None:
        _ensure_dbv_search_panel_symbols()
        self._clear_filters(refresh=False)
        self._set_sort_mode("alpha")
        self.list_widget.clearSelection()
