from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")
SEARCH_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text(encoding="utf-8")


def test_shared_dropdown_style_disables_popup_elision_and_sizes_to_contents():
    assert "dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)" in STYLE_SOURCE
    assert "popup_view.setTextElideMode(Qt.ElideNone)" in STYLE_SOURCE
    assert "popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in STYLE_SOURCE


def test_database_search_human_design_dropdowns_have_non_eliding_widths():
    assert 'set_dropdown_width_chars(channel_combo, 7)' in SEARCH_PANEL_SOURCE
    assert 'set_dropdown_width_chars(window._human_design_profile_filter_combo, 6)' in SEARCH_PANEL_SOURCE
    assert 'width_px = (metrics.horizontalAdvance("0") * int(chars)) + 46' in SEARCH_PANEL_SOURCE
