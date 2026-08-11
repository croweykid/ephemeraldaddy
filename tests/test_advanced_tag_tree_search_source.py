from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text(encoding="utf-8")


def test_advanced_tag_search_lives_inside_collapsible_section():
    builder = SOURCE.split("def build_dbv_search_panel", 1)[1]
    block = builder.split("layout.addWidget(create_divider())", 1)[0]
    assert 'setPlaceholderText("Find an existing tag…")' in block
    assert "search_tags_content_layout.addWidget(window.advanced_tag_search_input)" in block
    assert "search_tags_content_layout.addWidget(window.search_tags_list_widget)" in block
    assert "search_tags_toggle.toggled.connect(window.search_tags_content.setVisible)" in block


def test_advanced_tag_search_autocomplete_uses_existing_tag_names():
    helper = SOURCE.split("def install_advanced_tag_search_autocomplete", 1)[1].split(
        "def filter_advanced_tag_tree", 1
    )[0]
    assert "QStringListModel(tags, line_edit)" in helper
    assert "Qt.MatchContains" in helper
    assert "setMaxVisibleItems(12)" in helper


def test_clearing_navigation_search_preserves_tag_filter_widgets():
    helper = SOURCE.split("def filter_advanced_tag_tree", 1)[1].split(
        "def refresh_search_tags_list", 1
    )[0]
    assert "setHidden" in helper
    assert "setExpanded(True)" in helper
    assert "search_tag_filter_checkboxes" not in helper
    assert ".clear()" not in helper
    assert "_advanced_tag_search_expanded_state" in helper


def test_nested_dot_tags_build_each_parent_level():
    refresh = SOURCE.split("def refresh_search_tags_list", 1)[1].split(
        "def has_active_chart_filters", 1
    )[0]
    assert 'value.split(".")' in refresh
    assert "category_item_for([prefix, *value_parts[:-1]])" in refresh
