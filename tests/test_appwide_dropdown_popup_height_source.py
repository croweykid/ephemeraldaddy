from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_appwide_dropdown_popup_max_height_rule():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert "APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX = 400" in source
    assert "max-height: __APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX__px;" in source
    assert "def configure_dropdown_popup_height" in source
    assert "popup_view.setMaximumHeight(APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX)" in source
    assert "popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in source


def test_appwide_widget_defaults_apply_dropdown_popup_height_to_all_combos():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert "if isinstance(obj, QComboBox):" in source
    assert "for child in obj.findChildren(QComboBox):" in source
    assert "configure_dropdown_popup_height(obj)" in source
    assert "configure_dropdown_popup_height(child)" in source


def test_shared_dropdown_style_uses_same_appwide_popup_height_rule():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()
    helper_start = source.index("def apply_shared_dropdown_style")
    helper_source = source[helper_start : source.index("# About dialog", helper_start)]

    assert "popup_view.setMaximumHeight(APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX)" in helper_source
    assert "popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in helper_source
    assert "configure_dropdown_popup_height(dropdown)" in helper_source
