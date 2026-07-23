from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROPERTY_MANAGER_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/property_manager.py").read_text(
    encoding="utf-8"
)
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text(
    encoding="utf-8"
)


def test_property_manager_dialog_does_not_refresh_visible_tag_pickers_mid_rename():
    launch_body = PROPERTY_MANAGER_SOURCE.split("def launch", 1)[1].split(
        "def load_usage", 1
    )[0]
    assert "refresh_tag_completers=False" in launch_body
    assert "self._host._update_tag_completers()" in launch_body


def test_property_manager_rebuilds_tag_trees_with_selection_signals_blocked():
    refresh_body = DEV_TOOLS_SOURCE.split("def _refresh_list", 1)[1].split(
        "def _selected_label", 1
    )[0]
    assert "self._refreshing_label_views = True" in refresh_body
    assert "tree.blockSignals(True)" in refresh_body
    assert "tree.setCurrentItem(None)" in refresh_body
    assert "tree.clearSelection()" in refresh_body
    assert "tree.clear()" in refresh_body
    assert "self._chart_names_list.clear()" in refresh_body
    assert "tree.blockSignals(False)" in refresh_body
    assert "self._refreshing_label_views = False" in refresh_body


def test_property_manager_ignores_selection_refresh_during_tag_tree_rebuild():
    selection_body = DEV_TOOLS_SOURCE.split("def _on_selection_changed", 1)[1].split(
        "def _refresh_chart_names", 1
    )[0]
    chart_names_body = DEV_TOOLS_SOURCE.split("def _refresh_chart_names", 1)[1].split(
        "def _delete_selected", 1
    )[0]
    assert 'getattr(self, "_refreshing_label_views", False)' in selection_body
    assert 'getattr(self, "_refreshing_label_views", False)' in chart_names_body
