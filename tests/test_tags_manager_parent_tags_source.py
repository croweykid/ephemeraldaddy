from pathlib import Path


DEV_TOOLS_SOURCE = Path("ephemeraldaddy/gui/dev_tools.py").read_text()
PROPERTY_MANAGER_SOURCE = Path("ephemeraldaddy/gui/property_manager.py").read_text()


def test_parent_tags_are_rendered_as_their_folder_nodes() -> None:
    refresh = DEV_TOOLS_SOURCE.split("def _refresh_list(self)", 1)[1].split(
        "def _selected_label(self)", 1
    )[0]

    assert "if parts and exact_path_key in parent_node_path_keys:" in refresh
    assert "node.setData(0, Qt.UserRole + 2, label)" in refresh
    assert 'node.setText(0, f"{base_label} ({chart_count} {chart_word})")' in refresh
    assert "node_chart_counts[path_key] = node_chart_counts.get(path_key, 0) + count" in refresh


def test_parent_tag_chart_results_distinguish_exact_and_child_matches() -> None:
    assert 'matches.append((chart_name, label.casefold() in tags))' in PROPERTY_MANAGER_SOURCE
    assert "not bool(match[1])" in PROPERTY_MANAGER_SOURCE
    assert "font.setItalic(True)" in DEV_TOOLS_SOURCE
    assert 'self._chart_names_heading.setText(f"Charts with {display_tag}")' in DEV_TOOLS_SOURCE
