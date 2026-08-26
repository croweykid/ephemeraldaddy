from pathlib import Path


def _controller_source() -> str:
    return Path("ephemeraldaddy/gui/features/controllers/main_window.py").read_text()


def test_startup_database_refresh_runs_before_loading_widget_completes():
    source = _controller_source()
    method = source.split("def open_manage_charts", 1)[1].split("class EphemerisPrefetchController", 1)[0]
    startup_branch = method.split("if refresh_after_show is not None:", 1)[1].split("else:", 1)[0]

    assert 'progress_callback("Loading Database rows…", 89)' in startup_branch
    assert "app.processEvents()" in startup_branch
    assert "refresh_after_show()" in startup_branch
    assert 'progress_callback("Database View is ready.", 99)' in startup_branch
    assert "QTimer.singleShot(350, refresh_after_show)" not in method
