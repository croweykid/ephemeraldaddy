from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()
DIALOGUES_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/dialogues.py").read_text()


def test_loud_dropdown_extends_appwide_dropdown_standard():
    loud_style = STYLE_SOURCE.split(
        "LOUD_SELECTION_DROPDOWN_MENU_STYLE =", 1
    )[1].split("WINDOW_CHROME_MENU_STYLE", 1)[0]
    loud_helper = STYLE_SOURCE.split(
        "def apply_loud_selection_dropdown_menu", 1
    )[1].split("def set_dropdown_item_text_color", 1)[0]

    assert 'DEFAULT_DROPDOWN_STYLE + """' in loud_style
    assert 'QComboBox[loudSelection="true"]' in loud_style
    assert "background-color: __MIDDLE_PANEL_ACCENT_COLOR__" in loud_style
    assert 'QComboBox[loudSelection="true"]:disabled' in loud_style
    assert "background: #444444" in loud_style
    assert "color: #aaaaaa" in loud_style
    assert "apply_shared_dropdown_style(dropdown)" in loud_helper
    assert 'dropdown.setProperty("loudSelection", is_loud)' in loud_helper
    assert 'default_value: str = "Any"' in loud_helper


def test_shared_dropdown_preserves_disabled_state_styling():
    default_style = STYLE_SOURCE.split(
        'DEFAULT_DROPDOWN_STYLE = """', 1
    )[1].split('""".replace', 1)[0]

    assert "QComboBox:disabled" in default_style
    assert "color: #aaaaaa" in default_style
    assert "background: #444444" in default_style


def test_rectification_engine_uses_shared_dropdown_helpers():
    assert "apply_shared_dropdown_style(self.step_combo)" in DIALOGUES_SOURCE
    assert "apply_loud_selection_dropdown_menu(sign_combo)" in DIALOGUES_SOURCE
    assert "apply_loud_selection_dropdown_menu(house_combo)" in DIALOGUES_SOURCE
    assert "_DEFINED_POSITION_STYLE" not in DIALOGUES_SOURCE


def test_rectification_house_headers_are_limited_to_one_text_line():
    assert "header.setMaximumHeight(header.fontMetrics().height())" in DIALOGUES_SOURCE


def test_refinement_state_survives_results_view_and_stays_out_of_broad_searches():
    assert "def _remove_refinement_angle_widgets" not in DIALOGUES_SOURCE
    assert "if not self._refinement_candidate_matches:" in DIALOGUES_SOURCE
    assert "for match in self._refinement_candidate_matches:" in DIALOGUES_SOURCE
    assert "self._refinement_candidate_matches = list(matches)" in DIALOGUES_SOURCE
    criteria_method = DIALOGUES_SOURCE.split("def _criteria", 1)[1].split(
        "def _house_criteria", 1
    )[0]
    assert 'body in {"Ascendant", "MC"}' in criteria_method
    assert "self._view is not RectificationView.REFINEMENT" in criteria_method
