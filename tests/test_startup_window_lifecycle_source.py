from pathlib import Path


def _lifecycle_source() -> str:
    return Path("ephemeraldaddy/gui/features/controllers/window_lifecycle.py").read_text()


def _app_source() -> str:
    return Path("ephemeraldaddy/gui/app.py").read_text()


def test_startup_keeps_owner_window_visible_if_database_view_is_not_visible():
    source = _lifecycle_source()
    method = source.split("def configure_initial_window_state", 1)[1]

    assert "default_view_opened = bool(show_default_view())" in method
    assert "QApplication.topLevelWidgets()" in method
    assert "if default_view_opened and visible_windows:" in method
    assert "window.hide()" in method
    assert "window.show()" in method


def test_app_does_not_quit_when_last_startup_widget_closes():
    source = _app_source()
    main = source.split("def main(", 1)[1]

    assert "app.setQuitOnLastWindowClosed(False)" in main
