from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_appwide_dropdown_popup_max_height_rule():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert "APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX = 400" in source
    assert "max-height: __APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX__px;" in source
    assert "def configure_dropdown_popup_height" in source
    assert "popup_view.setMaximumHeight(APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX)" in source
    assert "popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in source


def test_appwide_widget_defaults_do_not_mutate_combo_popup_views():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()
    filter_start = source.index("class _AppwideCursorDefaultsFilter")
    filter_source = source[filter_start : source.index("def install_appwide_cursor_defaults", filter_start)]

    assert "Apply shared button defaults" in filter_source
    assert "QComboBox" not in filter_source
    assert "configure_dropdown_popup_height" not in filter_source


def test_shared_dropdown_style_uses_same_appwide_popup_height_rule():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()
    helper_start = source.index("def apply_shared_dropdown_style")
    helper_source = source[helper_start : source.index("# About dialog", helper_start)]

    assert "popup_view.setMaximumHeight(APPWIDE_DROPDOWN_POPUP_MAX_HEIGHT_PX)" in helper_source
    assert "popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in helper_source
    assert "configure_dropdown_popup_height(dropdown)" in helper_source
