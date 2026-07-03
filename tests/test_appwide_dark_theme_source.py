from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_appwide_chart_view_text_input_and_button_standard():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert 'APPWIDE_TEXT_INPUT_BACKGROUND_COLOR = "#222222"' in source
    assert 'APPWIDE_BUTTON_BACKGROUND_COLOR = "#333333"' in source
    assert 'APPWIDE_DARK_THEME_STYLESHEET' in source
    assert 'QLineEdit, QDateEdit, QTimeEdit, QTextEdit, QPlainTextEdit' in source
    assert 'background-color: {APPWIDE_TEXT_INPUT_BACKGROUND_COLOR}' in source
    assert 'QPushButton {' in source
    assert 'background-color: {APPWIDE_BUTTON_BACKGROUND_COLOR}' in source


def test_application_uses_shared_appwide_dark_theme_stylesheet():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "APPWIDE_DARK_THEME_STYLESHEET" in source
    assert "self.setStyleSheet(APPWIDE_DARK_THEME_STYLESHEET)" in source
    assert "f\"{APPWIDE_DARK_THEME_STYLESHEET}\\n\"" in source
    assert "QLineEdit, QDateEdit, QTimeEdit {" not in source
