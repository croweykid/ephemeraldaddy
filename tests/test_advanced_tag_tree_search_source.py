import os
from pathlib import Path
from types import SimpleNamespace

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
    assert "_advanced_tag_search_scroll_value" in helper


def test_nested_dot_tags_build_each_parent_level():
    refresh = SOURCE.split("def refresh_search_tags_list", 1)[1].split(
        "def has_active_chart_filters", 1
    )[0]
    assert 'value.split(".")' in refresh
    assert "category_item_for([prefix, *value_parts[:-1]])" in refresh
    assert "category_items[tag.casefold()] = tag_item" in refresh


@pytest.fixture(scope="module")
def qt_app():
    qt_widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

    return qt_widgets.QApplication.instance() or qt_widgets.QApplication([])


def test_navigation_filter_keeps_matching_tag_and_all_ancestors(qt_app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

    from ephemeraldaddy.gui.dbv_search_panel import filter_advanced_tag_tree

    tree = QTreeWidget()
    occupation = QTreeWidgetItem(tree, ["Occupation"])
    writer = QTreeWidgetItem(occupation, ["Writer"])
    novelist = QTreeWidgetItem(writer, ["Novelist"])
    novelist.setData(0, Qt.UserRole + 1, "occupation.writer.novelist")
    reputation = QTreeWidgetItem(tree, ["Reputation"])
    socialite = QTreeWidgetItem(reputation, ["Socialite"])
    socialite.setData(0, Qt.UserRole + 1, "reputation.socialite")
    window = SimpleNamespace(search_tags_list_widget=tree)

    filter_advanced_tag_tree(window, "novel")

    assert not occupation.isHidden()
    assert not writer.isHidden()
    assert not novelist.isHidden()
    assert occupation.isExpanded()
    assert writer.isExpanded()
    assert reputation.isHidden()


def test_clearing_navigation_filter_retains_controls_and_restores_view(qt_app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

    from ephemeraldaddy.gui.dbv_search_panel import filter_advanced_tag_tree

    tree = QTreeWidget()
    occupation = QTreeWidgetItem(tree, ["Occupation"])
    novelist = QTreeWidgetItem(occupation, ["Novelist"])
    novelist.setData(0, Qt.UserRole + 1, "occupation.writer.novelist")
    reputation = QTreeWidgetItem(tree, ["Reputation"])
    socialite = QTreeWidgetItem(reputation, ["Socialite"])
    socialite.setData(0, Qt.UserRole + 1, "reputation.socialite")
    occupation.setExpanded(False)
    reputation.setExpanded(True)
    checkbox = object()
    logic = {"checked": "or"}
    window = SimpleNamespace(
        search_tags_list_widget=tree,
        search_tag_filter_checkboxes={"occupation.writer.novelist": checkbox},
        search_tag_filter_logic_buttons={"occupation.writer.novelist": logic},
    )

    filter_advanced_tag_tree(window, "novelist")
    filter_advanced_tag_tree(window, "")

    assert not occupation.isHidden()
    assert not reputation.isHidden()
    assert not occupation.isExpanded()
    assert reputation.isExpanded()
    assert window.search_tag_filter_checkboxes["occupation.writer.novelist"] is checkbox
    assert window.search_tag_filter_logic_buttons["occupation.writer.novelist"] is logic
