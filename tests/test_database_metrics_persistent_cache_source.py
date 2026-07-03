from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()
DB_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/core/db.py").read_text()
DB_ANALYTICS_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/features/charts/database_analytics.py").read_text()


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


def test_database_metrics_cache_is_saved_on_close_without_blocking_recompute():
    method = _method_source(APP_SOURCE, "closeEvent")
    save_method = _method_source(APP_SOURCE, "_save_database_metrics_persistent_cache")
    assert "self._save_database_metrics_persistent_cache()" in method
    assert "self._database_metrics_preload_enabled = False" in method
    assert "if self._database_metrics_cache is None:" in save_method
    assert "computed_sections=frozenset(DATABASE_METRICS_SECTION_ORDER)" not in save_method


def test_database_metrics_panel_open_and_section_expand_defer_heavy_refresh():
    show_method = _method_source(APP_SOURCE, "_show_left_panel")
    panel_show_method = _method_source(APP_SOURCE, "_refresh_database_metrics_panel_on_show")
    refresh_needed_method = _method_source(
        APP_SOURCE, "_database_metrics_refresh_needed_on_panel_show"
    )
    expand_method = _method_source(APP_SOURCE, "_set_database_metrics_section_expanded")
    database_panel_branch = show_method.split('if panel_name == "database_metrics":', 1)[1].split(
        'elif panel_name == "gen_pop_norms":', 1
    )[0]
    assert "baseline_changed=previous_database_metrics_baseline_mode != self._database_metrics_baseline_mode" in database_panel_branch
    assert "self._update_sentiment_tally(" not in database_panel_branch
    assert "baseline_changed: bool = False" in panel_show_method
    assert "expanded_sections = frozenset(self._expanded_database_metric_sections())" in panel_show_method
    assert "and expanded_sections.issubset(self._database_metrics_snapshot_sections)" in panel_show_method
    assert "sections_to_refresh=set(expanded_sections)" in panel_show_method
    assert "if not self._database_metrics_refresh_needed_on_panel_show():" in panel_show_method
    assert "self._show_database_analytics_pending_indicator(False)" in panel_show_method
    assert "self._schedule_database_metrics_background_preload()" in panel_show_method
    assert "self._schedule_deferred_database_metrics_refresh()" in panel_show_method
    assert refresh_needed_method.index("expanded_sections =") < refresh_needed_method.index("self._database_metrics_cache is None")
    assert "if not expanded_sections:" in refresh_needed_method
    assert "self._database_metrics_lucy_goosey_ids" in refresh_needed_method
    assert "expanded_sections.issubset(self._database_metrics_snapshot_sections)" in refresh_needed_method
    assert "QTimer.singleShot(" in expand_method
    assert "self._refresh_expanded_database_metric_section(key)" in expand_method



def test_database_metrics_section_refresh_protocols_are_field_scoped():
    assert "DATABASE_METRICS_BIRTH_DATA_SECTIONS" in DB_ANALYTICS_SOURCE
    assert '"birth_data"' in DB_ANALYTICS_SOURCE
    assert '"tags": frozenset({"tag_distribution"})' in DB_ANALYTICS_SOURCE
    assert '"sentiments": frozenset({"sentiment_prevalence"})' in DB_ANALYTICS_SOURCE
    assert '"gender": frozenset({"gender"})' in DB_ANALYTICS_SOURCE
    birth_scope = DB_ANALYTICS_SOURCE.split("DATABASE_METRICS_BIRTH_DATA_SECTIONS", 1)[1].split("DATABASE_METRICS_SUBJECTIVE_SECTION_DEPENDENCIES", 1)[0]
    assert '"gender"' in birth_scope
    assert "def database_metrics_sections_for_changed_fields" in DB_ANALYTICS_SOURCE
    assert "if changed_fields is None:" in DB_ANALYTICS_SOURCE
    assert "return frozenset()" in DB_ANALYTICS_SOURCE
    update_method = _method_source(APP_SOURCE, "_update_sentiment_tally")
    assert "changed_fields" in update_method
    assert "database_metrics_sections_for_changed_fields" in update_method
    assert "if scoped_database_refresh_requested and not sections_to_refresh:" in update_method
    assert "update_database_metrics = False" in update_method
    assert "self._database_metrics_preloaded_sections.difference_update(sections_to_refresh)" in update_method
    incremental_method = _method_source(APP_SOURCE, "_schedule_incremental_metrics_refresh")
    assert "sections_to_refresh" in incremental_method
    assert "if section_key in allowed_sections" in incremental_method

def test_incremental_refresh_reuses_same_changed_ids_for_every_section_step():
    method = _method_source(APP_SOURCE, "_run_incremental_metrics_refresh_step")
    assert "self._incremental_metrics_refresh_changed_ids.clear()" in method.split(
        "if not self._incremental_metrics_refresh_sections:", 1
    )[1].split("section_key =", 1)[0]
    per_section_body = method.split("section_key =", 1)[1]
    assert "changed_ids = (" in per_section_body
    assert "self._incremental_metrics_refresh_changed_ids.clear()" not in per_section_body


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


def test_persistent_cache_rows_token_uses_chart_uids_not_legacy_ids():
    token_method = _method_source(APP_SOURCE, "_database_metrics_rows_token")
    assert "get_chart_uid_map(row_ids)" in token_method
    assert "legacy-id:" in token_method
    assert "repr(tuple(row[1:]))" in token_method


def test_persistent_cache_validates_analytics_configuration():
    token_method = _method_source(APP_SOURCE, "_database_metrics_config_token")
    load_method = _method_source(APP_SOURCE, "_load_database_metrics_persistent_cache")
    save_method = _method_source(APP_SOURCE, "_save_database_metrics_persistent_cache")
    assert "_enneagram_scoring_options" in token_method
    assert 'payload.get("config_token")' in load_method
    apply_method = _method_source(APP_SOURCE, "_apply_enneagram_predictor_weights")
    assert '"config_token": self._database_metrics_config_token()' in save_method
    assert "self._invalidate_database_metrics_cache()" in apply_method


def test_append_database_reports_imported_uids_and_refreshes_incrementally():
    append_method = _method_source(DB_SOURCE, "append_database", indented=False)
    gui_method = _method_source(APP_SOURCE, "_on_append_database_placeholder")
    assert "imported_uids.append(new_chart_uid)" in append_method
    assert '"imported_uids": imported_uids' in append_method
    assert 'result.get("imported_uids", [])' in gui_method
    assert "get_chart_uid_map().items()" in gui_method
    assert "changed_ids=changed_ids or None" in gui_method
