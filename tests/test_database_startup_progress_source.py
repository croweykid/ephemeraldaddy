from pathlib import Path


def _controller_source() -> str:
    return Path("ephemeraldaddy/gui/features/windowing/appwide_window_coordinator.py").read_text()


def test_startup_database_refresh_runs_before_loading_widget_completes():
    source = _controller_source()
    method = source.split("def open_database_view", 1)[1].split("return True", 1)[0]
    startup_branch = method.split("if refresh_after_show is not None:", 1)[1].split("else:", 1)[0]

    assert 'progress_callback("Loading Database rows…", 89)' in startup_branch
    assert "self._process_application_events()" in startup_branch
    assert "refresh_after_show()" in startup_branch
    assert 'progress_callback("Database View is ready.", 99)' in startup_branch
    assert "self._schedule_once(350, refresh_after_show)" not in method
