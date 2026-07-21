from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
SEARCH_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text(encoding="utf-8")


def test_search_panel_does_not_import_gui_app_module():
    assert "from ephemeraldaddy.gui import app" not in SEARCH_PANEL_SOURCE
    assert "app_module." not in SEARCH_PANEL_SOURCE


def test_tag_completer_uses_db_recognized_tags_source():
    helper = SEARCH_PANEL_SOURCE.split("def tag_completer_tags_for_session", 1)[1].split(
        "def update_tag_completers_if_needed", 1
    )[0]
    assert "from ephemeraldaddy.core.db import list_recognized_tags" in helper
    assert "from ephemeraldaddy.gui.features.charts.tagging import list_recognized_tags" not in helper


def test_search_tags_typing_does_not_rebuild_tag_tree_on_each_keystroke():
    handler = APP_SOURCE.split("def _on_search_tags_changed", 1)[1].split(
        "def _refresh_search_tags_list", 1
    )[0]
    assert "sync_search_tags_list_selection(self, set(tags))" in handler
    assert "_refresh_search_tags_list" not in handler


def test_search_tags_selection_sync_respects_collapsed_tag_tree():
    helper = SEARCH_PANEL_SOURCE.split("def sync_search_tags_list_selection", 1)[1].split(
        "def on_search_tag_logic_changed", 1
    )[0]
    assert "search_tags_toggle" in helper
    assert "not search_tags_toggle.isChecked()" in helper
    assert "return" in helper.split("not search_tags_toggle.isChecked()", 1)[1]


def test_search_tags_selection_sync_suppresses_per_checkbox_filter_signals():
    helper = SEARCH_PANEL_SOURCE.split("def sync_search_tags_list_selection", 1)[1].split(
        "def on_search_tag_logic_changed", 1
    )[0]
    assert "emit_signal=False" in helper
    assert "tree.clear()" not in helper


def test_database_view_search_bars_live_above_collection_controls():
    setup_block = APP_SOURCE.split("# Database View - Center list panel", 1)[1].split(
        "# Database View - Content splitter", 1
    )[0]
    search_row_index = setup_block.index("list_layout.addWidget(build_dbv_search_bar_row(self))")
    collection_index = setup_block.index("self.collection_combo = QComboBox()")
    header_row_index = setup_block.index("list_layout.addWidget(list_header_row)")
    assert search_row_index < collection_index < header_row_index


def test_database_view_imports_middle_panel_search_bar_builder():
    import_block = APP_SOURCE.split("from ephemeraldaddy.gui.dbv_search_panel import (", 1)[1].split(
        ")", 1
    )[0]
    assert "build_dbv_search_bar_row" in import_block


def test_right_search_filter_panel_no_longer_owns_top_level_search_inputs():
    panel_builder = SEARCH_PANEL_SOURCE.split("def build_dbv_search_panel", 1)[1]
    panel_prefix = panel_builder.split("def build_trait_search_layout", 1)[0]
    assert "window.search_text_input = QLineEdit()" not in panel_prefix
    assert "window.astrotheme_search_input = QLineEdit()" not in panel_prefix
    assert "window.search_tags_input = QLineEdit()" not in panel_prefix
    assert 'QLabel("Search Filters")' in panel_prefix


def test_middle_panel_search_bar_row_preserves_search_wiring():
    row_builder = SEARCH_PANEL_SOURCE.split("def build_dbv_search_bar_row", 1)[1].split(
        "def build_dbv_search_panel", 1
    )[0]
    assert "window.search_text_input.textChanged.connect(window._on_filter_changed)" in row_builder
    assert "window.astrotheme_search_input.returnPressed.connect(" in row_builder
    assert "window._on_import_astrotheme_from_search_panel" in row_builder
    assert "window.search_tags_input.textChanged.connect(window._on_search_tags_changed)" in row_builder
    assert "window.search_untagged_checkbox.modeChanged.connect(window._on_filter_changed)" in row_builder


def test_middle_panel_search_bar_row_top_aligns_all_search_cells():
    row_builder = SEARCH_PANEL_SOURCE.split("def build_dbv_search_bar_row", 1)[1].split(
        "def build_dbv_search_panel", 1
    )[0]
    assert "row_layout.addWidget(database_cell, 2, Qt.AlignTop)" in row_builder
    assert "row_layout.addWidget(astrotheme_cell, 2, Qt.AlignTop)" in row_builder
    assert "row_layout.addWidget(tag_cell, 2, Qt.AlignTop)" in row_builder


def test_middle_panel_search_bar_row_applies_custom_search_controls():
    row_builder = SEARCH_PANEL_SOURCE.split("def build_dbv_search_bar_row", 1)[1].split(
        "def build_dbv_search_panel", 1
    )[0]
    assert 'QPushButton("🔍")' in row_builder
    assert 'QPushButton("⬇️")' in row_builder
    assert 'background_color="#e6b800"' in row_builder
    assert 'placeholder_color="#b38f00"' in row_builder
    assert 'text_color="#1f1f1f"' in row_builder
    assert 'background_color="#5900b3"' in row_builder
    assert 'placeholder_color="#8000ff"' in row_builder
