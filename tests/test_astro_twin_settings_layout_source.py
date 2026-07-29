from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/dev_tools.py").read_text(
    encoding="utf-8"
)
SECTION = SOURCE.split("def build_similarity_calculator_settings_section", 1)[1].split(
    "def build_predictions_settings_section", 1
)[0]


def test_demographic_matching_precedes_scoring_methods_and_has_divider():
    demographic = SECTION.index('QLabel("Demographic Matching")')
    divider = SECTION.index("demographic_algorithm_divider = QFrame()")
    scoring = SECTION.index('QLabel("Scoring Methods")')
    chooser = SECTION.index('"Choose which matching algorithm powers Similar Charts results."')

    assert demographic < divider < scoring < chooser
    assert "demographic_match_header.setStyleSheet(subheader_style)" in SECTION
    assert "scoring_methods_header.setStyleSheet(subheader_style)" in SECTION
    assert "demographic_algorithm_divider.setFrameShape(QFrame.HLine)" in SECTION
    assert 'QLabel("Match preference")' not in SECTION
    assert 'QLabel("Astro Twin Calculator")' not in SECTION


def test_demographic_matching_labels_order_and_no_tooltips():
    include_everyone = SECTION.index('("none", "Include everyone (default)")')
    assigned_sex = SECTION.index('("sex", "Match assigned sex")')
    gender_identity = SECTION.index('("gender", "Match gender identity")')
    demographic_loop = SECTION[include_everyone:SECTION.index('demographic_match_buttons["none"]', include_everyone)]

    assert include_everyone < assigned_sex < gender_identity
    assert "setToolTip" not in demographic_loop
    assert '"No preference"' not in SECTION
    assert '"Gender match"' not in SECTION
    assert '"Sex match"' not in SECTION


def test_database_distinction_precedes_custom_as_final_scoring_option():
    database_widget = SECTION.index("algorithm_layout.addWidget(database_distinction_radio)")
    custom_widget = SECTION.index("algorithm_layout.addWidget(custom_radio)")
    custom_fields = SECTION.index("custom_fields_frame = QFrame()")

    assert database_widget < custom_widget < custom_fields


def test_custom_subpanel_has_visual_cues_and_preset_button_at_bottom():
    custom_fields = SECTION.index("custom_fields_frame = QFrame()")
    accent = SECTION.index('border-left: 3px solid {CHART_DATA_HIGHLIGHT_COLOR}', custom_fields)
    reset_button = SECTION.index('QPushButton("Reset Weights to Defaults")', custom_fields)
    save_button = SECTION.index('QPushButton("Save as Preset")', custom_fields)
    attach_to_layout = SECTION.index("algorithm_layout.addWidget(custom_fields_frame)", custom_fields)

    assert custom_fields < accent < reset_button < save_button < attach_to_layout
    assert 'save_custom_preset_button.setToolTip("save current weights as preset")' in SECTION
    assert '"save_custom_preset_button": save_custom_preset_button' in SECTION


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
