from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = SOURCE.index(marker)
    next_start = SOURCE.find("\n    def ", start + len(marker))
    if next_start == -1:
        return SOURCE[start:]
    return SOURCE[start:next_start]


def test_database_metrics_startup_restores_persistent_cache_without_preloading_full_refresh():
    method = _method_source("_start_database_metrics_cache_preload")
    assert "_load_database_metrics_persistent_cache()" in method
    assert "_refresh_database_metrics_cache(force_full_refresh=True)" not in method


def test_database_metrics_cache_is_saved_on_close():
    method = _method_source("closeEvent")
    assert "self._save_database_metrics_persistent_cache()" in method


def test_incremental_refresh_preserves_warmer_snapshot_sections():
    method = _method_source("_refresh_database_metrics_cache")
    assert "computed_sections.issubset(self._database_metrics_snapshot_sections)" in method
    assert "snapshot_sections = self._database_metrics_snapshot_sections" in method
    assert "computed_sections=snapshot_sections" in method
