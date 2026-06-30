from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text()


def test_tag_manager_category_drop_treats_payload_as_command_not_model_move():
    hierarchy_drop = DEV_TOOLS_SOURCE.split("class _TagHierarchyTree", 1)[1].split(
        "class ManageMetadataLabelsDialog", 1
    )[0]
    assert "self._on_drop_labels(category_prefix, labels)" in hierarchy_drop
    assert "event.setDropAction(Qt.CopyAction)" in hierarchy_drop
    assert "event.accept()" in hierarchy_drop
    assert "event.acceptProposedAction()" not in hierarchy_drop.split(
        "def dropEvent", 1
    )[1]


def test_tag_manager_category_list_drop_treats_payload_as_command_not_model_move():
    category_list_drop = DEV_TOOLS_SOURCE.split("class _TagCategoryDropList", 1)[1].split(
        "class _TagHierarchyTree", 1
    )[0]
    assert "self._on_drop_labels(category_prefix, labels)" in category_list_drop
    assert "event.setDropAction(Qt.CopyAction)" in category_list_drop
    assert "event.accept()" in category_list_drop
