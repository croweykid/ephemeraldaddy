from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_database_analytics_does_not_preload_at_startup():
    assert "QTimer.singleShot(0, self._start_database_metrics_cache_preload)" not in APP_SOURCE
    assert "self._database_metrics_preload_enabled = False" in APP_SOURCE


def test_section_refresh_accumulates_snapshot_coverage_for_requested_sections():
    assert "computed_sections = None" in APP_SOURCE
    assert "frozenset(sections_to_refresh) | self._database_metrics_snapshot_sections" in APP_SOURCE
    assert "computed_sections=computed_sections," in APP_SOURCE


def test_database_analytics_persists_cross_session_cache_on_close_without_recompute():
    close_event_start = APP_SOURCE.index("    def closeEvent(self, event) -> None:")
    close_event_end = APP_SOURCE.index("    def _on_hide_hypothetical_toggled", close_event_start)
    close_event_source = APP_SOURCE[close_event_start:close_event_end]
    save_method_start = APP_SOURCE.index("    def _save_database_metrics_persistent_cache")
    save_method_end = APP_SOURCE.index("    def _load_custom_collections_from_settings", save_method_start)
    save_method_source = APP_SOURCE[save_method_start:save_method_end]

    assert "self._save_database_metrics_persistent_cache()" in close_event_source
    assert "if self._database_metrics_cache is None:" in save_method_source
    assert "force_full_refresh=True" not in save_method_source


def test_database_analytics_flushes_pending_metrics_before_close_cache_save():
    flush_start = APP_SOURCE.index("    def _flush_pending_database_metrics_before_close")
    flush_end = APP_SOURCE.index("    def closeEvent", flush_start)
    flush_source = APP_SOURCE[flush_start:flush_end]
    close_event_start = APP_SOURCE.index("    def closeEvent(self, event) -> None:")
    close_event_end = APP_SOURCE.index("    def _on_hide_hypothetical_toggled", close_event_start)
    close_event_source = APP_SOURCE[close_event_start:close_event_end]

    assert "self._run_deferred_database_metrics_refresh()" in flush_source
    assert "while self._incremental_metrics_refresh_scheduled:" in flush_source
    assert "self._run_incremental_metrics_refresh_step()" in flush_source
    assert close_event_source.index("self._flush_pending_database_metrics_before_close()") < close_event_source.index("self._is_closing = True")
    assert close_event_source.index("self._flush_pending_database_metrics_before_close()") < close_event_source.index("self._save_database_metrics_persistent_cache()")
