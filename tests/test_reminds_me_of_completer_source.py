from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_reminds_me_of_completer_refresh_reuses_existing_model():
    helper = APP_SOURCE.split("def _update_reminds_me_of_completer", 1)[1].split(
        "def _render_reminds_me_of_selection", 1
    )[0]
    assert "QStringListModel" in APP_SOURCE
    assert 'existing_completer = getattr(line_edit, "_reminds_me_of_completer", None)' in helper
    assert "existing_model.setStringList(choices)" in helper
    assert "return" in helper.split("existing_model.setStringList", 1)[1].split(
        "completer = QCompleter", 1
    )[0]
    assert "QCompleter(QStringListModel(choices, line_edit), line_edit)" in helper
