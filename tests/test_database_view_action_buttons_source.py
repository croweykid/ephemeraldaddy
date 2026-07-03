from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "ephemeraldaddy/gui/app.py"


def _update_batch_edit_action_buttons_source() -> str:
    source = SOURCE_PATH.read_text()
    start = source.index("    def _update_batch_edit_action_buttons(self) -> None:")
    end = source.index("    def _on_import_csv(self) -> None:", start)
    return source[start:end]


def test_database_view_action_buttons_skip_redundant_state_updates():
    source = SOURCE_PATH.read_text()
    method_source = _update_batch_edit_action_buttons_source()

    assert "def _set_button_text_if_changed" in source
    assert "def _set_button_enabled_if_changed" in source
    assert "self._set_button_text_if_changed(" in method_source
    assert "self._set_button_enabled_if_changed(" in method_source
    assert "batch_delete_chart_button.setText" not in method_source
    assert "total_chart_export_button.setText" not in method_source
    assert "batch_rename_chart_button.setEnabled" not in method_source
    assert "total_chart_export_button.setEnabled" not in method_source
