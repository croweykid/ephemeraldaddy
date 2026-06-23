from pathlib import Path


def _app_source() -> str:
    return Path("ephemeraldaddy/gui/app.py").read_text()


def test_similar_charts_popout_cache_key_allows_incremental_database_refresh():
    source = _app_source()
    key_method = source.split("def _similar_charts_popout_cache_key", 1)[1].split(
        "def _get_cached_similar_charts_popout_payload", 1
    )[0]

    assert "incremental-db-v1" in key_method
    assert "_similar_charts_popout_database_signature(rows)" not in key_method


def test_similar_charts_popout_cache_tracks_row_signatures_and_rescores_changed_rows_only():
    source = _app_source()
    show_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]

    assert "row_signatures = self._similar_charts_popout_database_row_signatures(chart_rows)" in show_method
    assert "changed_chart_ids =" in show_method
    assert "subject_chart_id not in changed_chart_ids" in show_method
    assert "refreshed_chart_ids = [" in show_method
    incremental_branch = show_method.split("elif incremental_refresh_supported:", 1)[1].split("else:", 1)[0]
    assert "load_charts(refreshed_chart_ids)" in incremental_branch
    assert "_load_similar_chart_candidates" not in incremental_branch
    assert "top_k=max(1, len(candidates))" in show_method



def test_similar_charts_popout_exact_cache_hit_skips_full_recompute_progress():
    source = _app_source()
    show_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]
    exact_hit_branch = show_method.split(
        "if cached_payload is not None and not changed_chart_ids and not deleted_chart_ids:", 1
    )[1].split("elif incremental_refresh_supported:", 1)[0]

    assert 'self._similar_charts_popout_last_cache_status = "hit"' in exact_hit_branch
    assert "find_astro_twins(" not in exact_hit_branch
    assert "show_similar_charts_loading_progress" not in exact_hit_branch

def test_similar_charts_popout_perceived_accuracy_uses_cached_rankings_when_available():
    source = _app_source()
    accuracy_method = source.split("def _similar_charts_perceived_accuracy_entries_for_states", 1)[1].split(
        "def _show_similar_charts_popout", 1
    )[0]
    show_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]

    assert "ranked_matches: list[Any] | None = None" in accuracy_method
    assert "match_by_id[int(match.chart_id)] = match" in accuracy_method
    assert "ranked_matches=most_similar_matches" in show_method
    perceived_controls = show_method.split("if show_perceived_accuracy_controls:", 1)[1].split("else:", 1)[0]
    assert "_load_similar_chart_candidates" not in perceived_controls


def test_developer_tools_exposes_manual_similar_charts_cache_refresh():
    source = _app_source()
    dev_tools_section = source.split('self._add_settings_collapsible_section(content_layout, "Developer Tools")', 1)[1].split(
        '#should this be here or no?', 1
    )[0]
    clear_method = source.split("def _clear_similar_charts_popout_cache", 1)[1].split(
        "def _on_refresh_similar_charts_popout_cache_requested", 1
    )[0]
    refresh_method = source.split("def _on_refresh_similar_charts_popout_cache_requested", 1)[1].split(
        "def _on_similarity_calculator_checkbox_toggled", 1
    )[0]

    assert 'QPushButton("Refresh Similar Charts cache")' in dev_tools_section
    assert "_on_refresh_similar_charts_popout_cache_requested" in dev_tools_section
    assert "cache.clear()" in clear_method
    assert "The next Similar Charts popout will recalculate on demand." in refresh_method


def test_full_recompute_refreshes_existing_similar_charts_cache_payload():
    source = _app_source()
    show_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]
    full_recompute_store = show_method.split("if performed_full_recompute:", 1)[1].split(
        "subject_name =", 1
    )[0]

    assert "performed_full_recompute = False" in show_method
    assert "performed_full_recompute = True" in show_method
    assert "cached_payload is None" not in full_recompute_store
    assert "row_signatures=row_signatures" in full_recompute_store
