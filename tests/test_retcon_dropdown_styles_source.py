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
    assert "apply_shared_dropdown_style(dropdown)" in loud_helper
    assert 'dropdown.setProperty("loudSelection", is_loud)' in loud_helper
    assert 'default_value: str = "Any"' in loud_helper


def test_rectification_engine_uses_shared_dropdown_helpers():
    assert "apply_shared_dropdown_style(self.step_combo)" in DIALOGUES_SOURCE
    assert "apply_loud_selection_dropdown_menu(sign_combo)" in DIALOGUES_SOURCE
    assert "apply_loud_selection_dropdown_menu(house_combo)" in DIALOGUES_SOURCE
    assert "_DEFINED_POSITION_STYLE" not in DIALOGUES_SOURCE


def test_rectification_house_headers_are_limited_to_one_text_line():
    assert "header.setMaximumHeight(header.fontMetrics().height())" in DIALOGUES_SOURCE
