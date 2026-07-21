from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_legacy_help_side_panel_chrome_removed() -> None:
    assert "_help_side_panel" not in APP_SOURCE
    assert "_help_icon_close" not in APP_SOURCE
    assert "_help_icon_button" not in APP_SOURCE


def test_legacy_help_search_box_removed() -> None:
    assert "_help_search_edit" not in APP_SOURCE
    assert "_help_results_list" not in APP_SOURCE
    assert "_help_entry_detail" not in APP_SOURCE
