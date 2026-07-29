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
