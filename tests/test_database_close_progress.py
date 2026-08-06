from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()
CLOSE_PROGRESS_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "ephemeraldaddy/gui/features/database_view/close_progress.py"
).read_text()


def test_database_close_progress_uses_the_shared_app_loading_bar():
    assert "class DatabaseCloseProgress:" in CLOSE_PROGRESS_SOURCE
    assert "create_app_loading_progress" in CLOSE_PROGRESS_SOURCE
    assert 'title="Closing Ephemeral Daddy"' in CLOSE_PROGRESS_SOURCE
    assert 'message="Preparing to close safely…"' in CLOSE_PROGRESS_SOURCE
    assert "self._update_progress(self._progress, message, percent)" in CLOSE_PROGRESS_SOURCE


def test_database_view_close_reports_work_in_order_before_it_closes():
    start = APP_SOURCE.index("    def closeEvent(self, event) -> None:")
    end = APP_SOURCE.index("\n    def ", start + 1)
    close_event = APP_SOURCE[start:end]

    expected_stages = (
        "Stopping background database work…",
        "Saving Database Analytics cache…",
        "Saving prediction and trait caches…",
        "Closing temporary windows and tools…",
        "Saving your Database View layout…",
        "Saving collections and session state…",
        "Everything is saved. Closing now…",
    )
    positions = [close_event.index(stage) for stage in expected_stages]

    assert positions == sorted(positions)
    assert positions[-1] < close_event.index("super().closeEvent(event)")
