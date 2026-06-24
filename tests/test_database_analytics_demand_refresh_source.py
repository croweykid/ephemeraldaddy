from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_database_analytics_does_not_preload_at_startup():
    assert "QTimer.singleShot(0, self._start_database_metrics_cache_preload)" not in APP_SOURCE
    assert "self._database_metrics_preload_enabled = False" in APP_SOURCE


def test_section_refresh_accumulates_snapshot_coverage_for_requested_sections():
    assert "computed_sections = None" in APP_SOURCE
    assert "frozenset(sections_to_refresh) | self._database_metrics_snapshot_sections" in APP_SOURCE
    assert "computed_sections=computed_sections," in APP_SOURCE


def test_database_analytics_does_not_persist_cross_session_cache_on_close():
    close_event_start = APP_SOURCE.index("    def closeEvent(self, event) -> None:")
    close_event_end = APP_SOURCE.index("    def _on_hide_hypothetical_toggled", close_event_start)
    close_event_source = APP_SOURCE[close_event_start:close_event_end]
    assert "_save_database_metrics_persistent_cache" not in close_event_source
