from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
SEARCH_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text(encoding="utf-8")


def test_search_tags_typing_does_not_rebuild_tag_tree_on_each_keystroke():
    handler = APP_SOURCE.split("def _on_search_tags_changed", 1)[1].split(
        "def _refresh_search_tags_list", 1
    )[0]
    assert "sync_search_tags_list_selection(self, set(tags))" in handler
    assert "_refresh_search_tags_list" not in handler


def test_search_tags_selection_sync_suppresses_per_checkbox_filter_signals():
    helper = SEARCH_PANEL_SOURCE.split("def sync_search_tags_list_selection", 1)[1].split(
        "def on_search_tag_logic_changed", 1
    )[0]
    assert "emit_signal=False" in helper
    assert "tree.clear()" not in helper
