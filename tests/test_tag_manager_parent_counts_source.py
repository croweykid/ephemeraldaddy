from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text()


def test_tag_manager_parent_node_counts_include_exact_parent_tag_rows():
    refresh_list = DEV_TOOLS_SOURCE.split("def _refresh_list", 1)[1].split(
        "def _selected_label", 1
    )[0]
    assert "parent_node_path_keys: set[str] = set()" in refresh_list
    assert "if exact_path_key in parent_node_path_keys:" in refresh_list
    assert "node_chart_counts[exact_path_key] = node_chart_counts.get(exact_path_key, 0) + count" in refresh_list
