"""Source checks for the compact Database View header spacing."""

from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_database_view_menu_to_toolbar_margin_is_four_pixels() -> None:
    layout_setup = APP_SOURCE.index("layout = QVBoxLayout()", APP_SOURCE.index("class DatabaseViewWindow"))
    chrome_setup = APP_SOURCE.index("configure_manage_dialog_chrome(self, layout", layout_setup)

    assert "layout.setContentsMargins(0, 4, 0, 0)" in APP_SOURCE[layout_setup:chrome_setup]


def test_database_view_search_to_filter_row_spacing_is_four_pixels() -> None:
    list_layout_setup = APP_SOURCE.index("list_layout = QVBoxLayout()")
    search_row = APP_SOURCE.index("list_layout.addWidget(build_dbv_search_bar_row(self))", list_layout_setup)
    filter_row = APP_SOURCE.index("list_layout.addWidget(list_header_row)", search_row)

    assert "list_layout.setSpacing(4)" in APP_SOURCE[list_layout_setup:search_row]
    assert search_row < filter_row
