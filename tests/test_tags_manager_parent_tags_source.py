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
    assert "node_chart_memberships.setdefault(path_key, set()).update(chart_memberships)" in refresh
    assert "chart_count = len(node_chart_memberships.get(key, set()))" in refresh


def test_parent_tag_chart_results_distinguish_exact_and_child_matches() -> None:
    assert 'matches.append((chart_name, label.casefold() in tags))' in PROPERTY_MANAGER_SOURCE
    assert "not bool(match[1])" in PROPERTY_MANAGER_SOURCE
    assert "font.setItalic(True)" in DEV_TOOLS_SOURCE
    assert "self._selected_chart_names_heading_text(selected_label)" in DEV_TOOLS_SOURCE


def test_each_property_manager_uses_a_field_specific_chart_heading() -> None:
    assert 'self.FIELD_TAGS: "Charts with selected tag"' in DEV_TOOLS_SOURCE
    assert 'self.FIELD_COLLECTIONS: "Charts in selected collection"' in DEV_TOOLS_SOURCE
    assert 'self.FIELD_RELATIONSHIPS: "Charts with selected relationship"' in DEV_TOOLS_SOURCE
    assert 'self.FIELD_SENTIMENTS: "Charts with selected sentiment"' in DEV_TOOLS_SOURCE


def test_each_selected_property_is_named_in_the_chart_heading() -> None:
    heading = DEV_TOOLS_SOURCE.split(
        "def _selected_chart_names_heading_text", 1
    )[1].split("def _active_rows", 1)[0]

    assert 'return f"Charts in {clean_label}"' in heading
    assert 'return f"Charts with {clean_label}"' in heading
    assert 'clean_label = " > ".join(' in heading


def test_parent_tag_actions_include_the_exact_tag_and_its_children() -> None:
    rename = DEV_TOOLS_SOURCE.split(
        "def _rename_selected_tag_category", 1
    )[1].split("def _create_collection", 1)[0]
    delete = DEV_TOOLS_SOURCE.split("def _delete_selected", 1)[1].split(
        "def _rename_tag_category_display_name", 1
    )[0]
    move = DEV_TOOLS_SOURCE.split("def _assign_tags_to_category", 1)[1].split(
        "def _row_for_key", 1
    )[0]

    assert "if original_casefold == old_prefix_casefold:" in rename
    assert "affected_labels.append((original_label, new_prefix))" in rename
    assert "subtree_labels = self._tag_labels_in_subtree(old_label)" in delete
    assert "for subtree_label in self._tag_labels_in_subtree(label) or [label]:" in move
    assert 'suffix = subtree_label[len(label):]' in move


def test_parent_counts_use_distinct_chart_uids() -> None:
    load_usage = PROPERTY_MANAGER_SOURCE.split("def load_usage", 1)[1].split(
        "def _collection_usage_rows", 1
    )[0]

    assert "uid_by_id = get_chart_uid_map" in load_usage
    assert 'row["chart_uids"] = sorted(tag_chart_uids.get(label, set()))' in load_usage
