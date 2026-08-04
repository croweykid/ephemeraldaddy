from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_database_view_collection_save_notifies_chart_editor_predictions():
    database_view = APP_SOURCE.split("class ManageChartsDialog", 1)[1].split("class MainWindow", 1)[0]
    save_method = database_view.split("def _save_custom_collections_to_settings", 1)[1].split(
        "@staticmethod", 1
    )[0]

    assert "refresh_hd_electrochemistry_collections(owner)" in save_method


def test_chart_editor_collection_save_refreshes_its_predictions():
    chart_editor = APP_SOURCE.split("class MainWindow", 1)[1]
    save_method = chart_editor.split("def _save_custom_collections_to_settings", 1)[1].split(
        "@staticmethod", 1
    )[0]

    assert "refresh_hd_electrochemistry_collections(self)" in save_method
