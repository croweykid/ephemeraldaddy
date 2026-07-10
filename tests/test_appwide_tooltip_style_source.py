from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLTIPS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/tooltips.py").read_text()
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_universal_tooltip_style_matches_app_tooltip_standard():
    assert 'APP_TOOLTIP_BACKGROUND_COLOR = "#252525"' in TOOLTIPS_SOURCE
    assert 'APP_TOOLTIP_TEXT_COLOR = "#f5f5f5"' in TOOLTIPS_SOURCE
    assert "QToolTip {" in TOOLTIPS_SOURCE
    assert "background-color: {APP_TOOLTIP_BACKGROUND_COLOR}" in TOOLTIPS_SOURCE
    assert "color: {APP_TOOLTIP_TEXT_COLOR}" in TOOLTIPS_SOURCE
    assert "border: 1px solid {CHART_DATA_HIGHLIGHT_COLOR}" in TOOLTIPS_SOURCE


def test_qapplication_installs_universal_tooltip_style():
    assert "install_app_tooltip_style" in TOOLTIPS_SOURCE
    assert "from ephemeraldaddy.gui.tooltips import apply_default_text_tooltips, install_app_tooltip_style" in APP_SOURCE
    assert "install_app_tooltip_style(app)" in APP_SOURCE


def test_tooltip_signifier_does_not_install_legacy_widget_tooltip_styles():
    signifier_block = TOOLTIPS_SOURCE.split("def apply_tooltip_signifier", 1)[1].split(
        "class TooltipHelpLabel", 1
    )[0]

    assert "setStyleSheet" not in signifier_block
    assert "APP_TOOLTIP_STYLE not in existing_style" not in TOOLTIPS_SOURCE
    assert 'style="color: {APP_TOOLTIP_TEXT_COLOR};' in TOOLTIPS_SOURCE


def test_database_view_right_panel_buttons_have_default_tooltip_overrides():
    assert '"manage_settings_button": "Settings"' in TOOLTIPS_SOURCE
    assert '"manage_toggle_search_panel_button": "Search"' in TOOLTIPS_SOURCE
    assert '"manage_toggle_batch_edit_panel_button": "Batch Edit Panel"' in TOOLTIPS_SOURCE
    assert '"manage_database_manager_button": "Database Manager"' in TOOLTIPS_SOURCE
    assert '"manage_toggle_collections_panel_button": "Collections"' in TOOLTIPS_SOURCE


def test_tooltips_wrap_after_42_characters():
    assert "APP_TOOLTIP_WRAP_COLUMN = 42" in TOOLTIPS_SOURCE
    assert "_wrap_plain_tooltip_text" in TOOLTIPS_SOURCE
    assert "width=APP_TOOLTIP_WRAP_COLUMN" in TOOLTIPS_SOURCE
    assert "replace(chr(10), '<br>')" in TOOLTIPS_SOURCE


def test_qwidget_settooltip_is_wrapped_appwide():
    assert "_install_wrapping_set_tooltip()" in TOOLTIPS_SOURCE
    assert "QWidget.setToolTip = set_wrapped_tooltip" in TOOLTIPS_SOURCE
    assert '_wrap_tooltip_text(str(tooltip or ""))' in TOOLTIPS_SOURCE
