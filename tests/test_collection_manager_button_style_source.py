from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_collection_manager_hover_and_pressed_feedback():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")

    assert 'QPushButton[eddCollectionManagerButton="true"]:hover' in source
    assert 'QPushButton[eddCollectionManagerButton="true"]:pressed' in source
    assert "COLLECTION_MANAGER_BUTTON_HOVER_BORDER_COLOR" in source
    assert "COLLECTION_MANAGER_BUTTON_PRESSED_BORDER_COLOR" in source


def test_collection_manager_configures_each_action_button():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")

    assert "configure_collection_manager_button" in source
    for button_name in (
        "collection_create_button",
        "collection_rename_button",
        "collection_delete_button",
        "collection_search_add_button",
        "collection_add_selected_button",
        "collection_remove_selected_button",
    ):
        assert f"self.{button_name}," in source
