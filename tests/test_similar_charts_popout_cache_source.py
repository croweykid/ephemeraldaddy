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
    assert "for changed_chart_id in sorted(changed_chart_ids):" in show_method
    incremental_branch = show_method.split("elif incremental_refresh_supported:", 1)[1].split("else:", 1)[0]
    assert "load_chart(changed_chart_id)" in incremental_branch
    assert "_load_similar_chart_candidates" not in incremental_branch
    assert "top_k=max(1, len(candidates))" in show_method


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
