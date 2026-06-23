from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()
DB_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/core/db.py").read_text()


def _method_source(source: str, name: str, *, indented: bool = True) -> str:
    indent = "    " if indented else ""
    marker = f"{indent}def {name}"
    start = source.index(marker)
    next_start = source.find(f"\n{indent}def ", start + len(marker))
    if next_start == -1:
        return source[start:]
    return source[start:next_start]


def test_database_metrics_startup_restores_persistent_cache_without_preloading_full_refresh():
    method = _method_source(APP_SOURCE, "_start_database_metrics_cache_preload")
    assert "_load_database_metrics_persistent_cache()" in method
    assert "_refresh_database_metrics_cache(force_full_refresh=True)" not in method


def test_database_metrics_cache_is_saved_on_close():
    method = _method_source(APP_SOURCE, "closeEvent")
    assert "self._save_database_metrics_persistent_cache()" in method


def test_incremental_refresh_preserves_warmer_snapshot_sections():
    method = _method_source(APP_SOURCE, "_refresh_database_metrics_cache")
    assert "computed_sections.issubset(self._database_metrics_snapshot_sections)" in method
    assert "snapshot_sections = self._database_metrics_snapshot_sections" in method
    assert "computed_sections=snapshot_sections" in method


def test_persistent_cache_uses_json_not_pickle_and_writes_atomically():
    assert 'DATABASE_METRICS_PERSISTENT_CACHE_FILENAME = ".database_metrics_cache.json"' in APP_SOURCE
    assert "import pickle" not in APP_SOURCE
    save_method = _method_source(APP_SOURCE, "_save_database_metrics_persistent_cache")
    assert "json.dump" in save_method
    assert "temp_path.replace(path)" in save_method


def test_persistent_cache_validates_analytics_configuration():
    token_method = _method_source(APP_SOURCE, "_database_metrics_config_token")
    load_method = _method_source(APP_SOURCE, "_load_database_metrics_persistent_cache")
    save_method = _method_source(APP_SOURCE, "_save_database_metrics_persistent_cache")
    assert "_enneagram_scoring_options" in token_method
    assert 'payload.get("config_token")' in load_method
    apply_method = _method_source(APP_SOURCE, "_apply_enneagram_predictor_weights")
    assert '"config_token": self._database_metrics_config_token()' in save_method
    assert "self._invalidate_database_metrics_cache()" in apply_method


def test_append_database_reports_imported_ids_and_refreshes_incrementally():
    append_method = _method_source(DB_SOURCE, "append_database", indented=False)
    gui_method = _method_source(APP_SOURCE, "_on_append_database_placeholder")
    assert "imported_ids.append(new_chart_id)" in append_method
    assert '"imported_ids": imported_ids' in append_method
    assert "changed_ids=imported_ids or None" in gui_method
    assert "force_full_analysis_refresh=not bool(imported_ids)" in gui_method
