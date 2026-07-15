from pathlib import Path


APP_TEXT_SEARCH_SOURCE = Path("ephemeraldaddy/gui/app_text_search.py").read_text()


def test_label_highlight_restore_ignores_dynamically_rewritten_labels():
    clear_method = APP_TEXT_SEARCH_SOURCE.split("def _clear_highlights", 1)[1].split(
        "def _highlight_label_html", 1
    )[0]

    assert "_LabelHighlightState" in APP_TEXT_SEARCH_SOURCE
    assert "highlighted_html" in clear_method
    assert "if label.text() == state.highlighted_html" in clear_method
    assert "label.setText(state.original_html)" in clear_method
