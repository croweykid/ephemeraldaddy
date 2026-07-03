from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_appwide_chart_view_text_input_and_button_standard():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert 'COLOR_BG_APP = "#0f1014"' in source
    assert 'COLOR_BG_PANEL = "#15161c"' in source
    assert 'COLOR_BG_SURFACE = "#1c1e26"' in source
    assert 'COLOR_BG_ELEVATED = "#242734"' in source
    assert 'COLOR_BG_INPUT = "#20232d"' in source
    assert "APPWIDE_TEXT_INPUT_BACKGROUND_COLOR = COLOR_BG_INPUT" in source
    assert "APPWIDE_BUTTON_BACKGROUND_COLOR = COLOR_BG_ELEVATED" in source
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


def test_database_view_uses_shared_surface_and_toolbar_styles():
    style_source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "DATABASE_VIEW_PANEL_BACKGROUND = COLOR_BG_PANEL" in style_source
    assert "DATABASE_VIEW_TOOLBAR_BUTTON_STYLE" in style_source
    assert "DATABASE_VIEW_CHART_LIST_STYLE" in style_source
    assert "DATABASE_VIEW_TOOLBAR_BUTTON_STYLE" in app_source
    assert "DATABASE_VIEW_CHART_LIST_STYLE" in app_source
    assert 'database_view_header_button_style = (' not in app_source
