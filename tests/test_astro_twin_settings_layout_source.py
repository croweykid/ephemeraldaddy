from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/dev_tools.py").read_text(
    encoding="utf-8"
)
APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text(
    encoding="utf-8"
)
SECTION = SOURCE.split("def build_similarity_calculator_settings_section", 1)[1].split(
    "def build_predictions_settings_section", 1
)[0]


def test_algorithm_caption_leads_and_demographic_matching_follows_custom_subpanel():
    chooser = SECTION.index('QLabel("Choose how Astro Twins are defined:")')
    custom_attach = SECTION.index("algorithm_layout.addWidget(custom_fields_frame)")
    divider = SECTION.index("demographic_algorithm_divider = QFrame()", custom_attach)
    demographic = SECTION.index('QLabel("Demographic Matching")', divider)
    stretch = SECTION.index("algorithm_layout.addStretch(1)", demographic)

    assert chooser < custom_attach < divider < demographic < stretch
    assert "demographic_match_header.setStyleSheet(subheader_style)" in SECTION
    assert "demographic_algorithm_divider.setFrameShape(QFrame.HLine)" in SECTION
    assert 'QLabel("Scoring Methods")' not in SECTION
    assert '"Choose the metric by which Astro Twins are defined:"' not in SECTION
    assert 'QLabel("Match preference")' not in SECTION
    assert 'QLabel("Astro Twin Calculator")' not in SECTION

def test_demographic_matching_labels_order_and_no_tooltips():
    include_everyone = SECTION.index('("none", "Include everyone (default)")')
    assigned_sex = SECTION.index('("sex", "Match assigned sex")')
    opposite_assigned_sex = SECTION.index('("opposite_sex", "Opposite assigned sex")')
    gender_identity = SECTION.index('("gender", "Match gender identity")')
    opposite_gender_identity = SECTION.index('("opposite_gender", "Opposite gender identity")')
    demographic_loop = SECTION[include_everyone:SECTION.index('demographic_match_buttons["none"]', include_everyone)]

    assert include_everyone < assigned_sex < opposite_assigned_sex < gender_identity < opposite_gender_identity
    assert "setToolTip" not in demographic_loop
    assert '"No preference"' not in SECTION
    assert '"Gender match"' not in SECTION
    assert '"Sex match"' not in SECTION


def test_database_distinction_precedes_custom_as_final_scoring_option():
    database_widget = SECTION.index("algorithm_layout.addWidget(database_distinction_radio)")
    custom_widget = SECTION.index("algorithm_layout.addWidget(custom_radio)")
    custom_fields = SECTION.index("custom_fields_frame = QFrame()")

    assert database_widget < custom_widget < custom_fields


def test_database_distinction_explanation_is_tooltip_only():
    assert "database_distinction_radio.setToolTip(DATABASE_DISTINCTION_SCAN_TOOLTIP)" in SECTION
    assert "database_distinction_help" not in SECTION


def test_custom_subpanel_has_visual_cues_and_preset_button_at_bottom():
    custom_fields = SECTION.index("custom_fields_frame = QFrame()")
    accent = SECTION.index('border-left: 3px solid {CHART_DATA_HIGHLIGHT_COLOR}', custom_fields)
    reset_button = SECTION.index('QPushButton("Reset Weights to Default")', custom_fields)
    save_button = SECTION.index('QPushButton("Save as Preset")', custom_fields)
    attach_to_layout = SECTION.index("algorithm_layout.addWidget(custom_fields_frame)", custom_fields)

    assert custom_fields < accent < reset_button < save_button < attach_to_layout
    assert 'save_custom_preset_button.setToolTip("save current weights as preset")' in SECTION
    assert '"save_custom_preset_button": save_custom_preset_button' in SECTION


def test_custom_weight_grid_uses_centered_renamed_headers_and_compact_columns():
    assert 'criterion_header = QLabel("Criterion")' in SECTION
    assert 'total_header = QLabel("Total")' in SECTION
    assert 'header.setAlignment(Qt.AlignCenter)' in SECTION
    assert 'weight_column_width = character_width * 8' in SECTION
    assert 'total_column_width = character_width * 12' in SECTION
    assert 'calculator_grid.setColumnStretch(1, 1)' in SECTION
    assert 'weight_spinbox.setFixedWidth(weight_column_width)' in SECTION


def test_placement_weight_mode_is_inline_with_placement_criterion_without_label():
    placement_branch = SECTION.index('if key == "placement":')
    criterion = SECTION.index("placement_criterion_row.addWidget(criterion_label)", placement_branch)
    combo = SECTION.index("placement_criterion_row.addWidget(weighting_mode_combo)", placement_branch)
    reset = SECTION.index('QPushButton("Reset Weights to Default")', combo)

    assert placement_branch < criterion < combo < reset
    assert 'QLabel("Placement-weight mode")' not in SECTION

def test_placement_weighting_modes_have_item_and_selected_tooltips():
    assert "PLACEMENT_WEIGHTING_MODE_TOOLTIPS" in SECTION
    assert "weighting_mode_combo.setItemData(" in SECTION
    assert "Qt.ToolTipRole" in SECTION
    assert "weighting_mode_combo.setToolTip(" in SECTION
    assert "weighting_mode_combo.itemData(index, Qt.ToolTipRole)" in SECTION


def test_selected_scoring_method_uses_chart_data_highlight_color():
    assert 'QRadioButton:checked {{ color: {CHART_DATA_HIGHLIGHT_COLOR}; }}' in SECTION
    assert "scoring_method_radio.setStyleSheet(scoring_method_selected_style)" in SECTION


def test_total_only_shows_green_completion_percentage_at_one():
    assert 'total_weight_value_label = QLabel("0.00/1.00")' in SECTION
    assert 'total_text = f"{checked_total:.2f}/1.00"' in APP_SOURCE
    assert "if abs(checked_total - 1.0) < 0.000_001:" in APP_SOURCE
    assert 'color: {COLOR_ACCENT_SUCCESS};">100%</span>' in APP_SOURCE


def test_custom_preset_selector_and_in_use_state_are_wired():
    assert 'select_preset_label = QLabel("Select Preset")' in SECTION
    assert "resolve_custom_astro_twin_presets_path().is_file()" in SECTION
    assert "select_preset_combo.currentIndexChanged.connect(apply_selected_preset)" in SECTION
    assert "preset_state[\"preset_in_use\"] = True" in SECTION
    assert "preset_state[\"preset_in_use\"] = False" in SECTION
    assert 'f"\'{preset_name}\' preset applied!"' in SECTION
    assert 'f"\'{preset_name}\' in use{suffix}"' in SECTION
    assert 'suffix = " (modified*)" if modified else ""' in SECTION
    assert 'font_style = "font-style: italic;" if modified else ""' in SECTION


def test_saving_loaded_preset_offers_exact_update_or_new_choices():
    assert '"Do you want to update the current preset or save this as new preset?"' in SECTION
    assert 'choice_dialog.addButton(f"Update \'{preset_name}\'", QMessageBox.AcceptRole)' in SECTION
    assert 'choice_dialog.addButton("Save as new", QMessageBox.ActionRole)' in SECTION
    assert "update_custom_astro_twin_preset(preset_name, current_custom_settings())" in SECTION
    save_handler = SECTION.split("def save_current_custom_preset", 1)[1].split(
        "save_custom_preset_button.clicked.connect", 1
    )[0]
    assert "if preset_name:" in save_handler
    assert 'if bool(preset_state["preset_in_use"]) and preset_name:' not in save_handler


def test_manage_presets_button_is_file_gated_and_right_of_selector():
    selector = SECTION.index("preset_action_row.addWidget(select_preset_combo)")
    manager = SECTION.index("preset_action_row.addWidget(manage_presets_button)")

    assert selector < manager
    assert 'manage_presets_button = QPushButton("Manage Presets")' in SECTION
    assert "manage_presets_button.setVisible(is_local_file_available)" in SECTION
    assert "manage_presets_button.clicked.connect(on_manage_presets_clicked)" in SECTION


def test_research_accuracy_ranking_fills_space_below_button_and_divider():
    button = SECTION.index('QPushButton("Show 90-100% similarities")')
    divider = SECTION.index("research_accuracy_divider = QFrame()")
    ranking = SECTION.index("algorithm_accuracy_label = SimilarityAlgorithmAccuracyBrowser(")

    assert button < divider < ranking
    assert "research_accuracy_divider.setFrameShape(QFrame.HLine)" in SECTION
    assert "on_use_row=apply_accuracy_ranking_row" in SECTION
    assert "research_layout.addWidget(algorithm_accuracy_label, 1)" in SECTION
    assert "research_layout.addStretch(1)" not in SECTION
    assert "self.setMaximumHeight(360)" not in SOURCE


def test_research_use_this_applies_mode_custom_snapshot_and_all_or_nothing_criterion():
    assert '"database_distinction": database_distinction_radio' in SECTION
    assert "def apply_accuracy_ranking_row(row: dict[str, object])" in SECTION
    assert 'if mode == "custom":' in SECTION
    assert 'calculator_checkboxes[key].setChecked(bool(factor.get("enabled", False)))' in SECTION
    assert 'calculator_weights[key].setValue(float(factor.get("weight", 0.0)))' in SECTION
    assert 'snapshot.get("placement_weighting_mode")' in SECTION
    assert 'snapshot_settings.get("all_or_nothing_component")' in SECTION
    assert "target_radio.setChecked(True)" in SECTION


def test_research_weight_coloring_uses_shared_zero_based_red_green_scale():
    browser = SOURCE.split("class SimilarityAlgorithmAccuracyBrowser", 1)[1].split(
        "def _build_settings_help_label", 1
    )[0]
    assert "more_readable_color_scale_rgb_for_range(" in browser
    assert "0.0," in browser
    assert "scale_max," in browser
    assert "factor_weight_color=self._factor_weight_color" in browser


def test_ranking_formatter_has_use_action_and_filters_disabled_factors():
    ranking_source = (
        Path(__file__).resolve().parents[1]
        / "ephemeraldaddy/gui/features/charts/similarities_algorithm_log.py"
    ).read_text(encoding="utf-8")
    formatter = ranking_source.split(
        "def format_similarity_algorithm_accuracy_ranking_html", 1
    )[1].split("def _settings_payload", 1)[0]
    assert '<th align=\"center\">Use</th>' in formatter
    assert 'href=\"use:{index - 1}\"' in formatter
    assert "enabled_factors = [" in formatter
    assert 'bool(factor.get(\"enabled\", False))' in formatter
    assert "for factor in enabled_factors:" in formatter
    assert "factor_weight_color(weight, maximum_weight)" in formatter
    assert 'f\"{label}: {weight:g} (on)\"' in formatter
    assert "(off)" not in formatter
