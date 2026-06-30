from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO_ROOT / "ephemeraldaddy/gui/app.py"


def test_database_view_chart_list_copy_shortcut_copies_raw_names_to_clipboard():
    source = APP_SOURCE.read_text()

    assert "def _chart_list_item_raw_name" in source
    assert 'metadata.get("raw_name")' in source
    assert "def _selected_chart_list_item_names" in source
    assert "for row in range(list_widget.count()):" in source
    assert "event.matches(QKeySequence.StandardKey.Copy)" in source
    assert "_copy_selected_chart_names_to_clipboard" in source
    assert 'QApplication.clipboard().setText("\\n".join(selected_names))' in source
