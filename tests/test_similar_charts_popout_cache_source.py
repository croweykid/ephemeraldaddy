from pathlib import Path


def test_similar_charts_popout_cache_key_allows_incremental_database_refresh():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    key_method = source.split("def _similar_charts_popout_cache_key", 1)[1].split(
        "def _get_cached_similar_charts_popout_payload", 1
    )[0]

    assert "incremental-db-v1" in key_method
    assert "_similar_charts_popout_database_signature(rows)" not in key_method


def test_similar_charts_popout_cache_tracks_row_signatures_and_rescores_changed_rows_only():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    show_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]

    assert "row_signatures = self._similar_charts_popout_database_row_signatures(chart_rows)" in show_method
    assert "changed_chart_ids =" in show_method
    assert "subject_chart_id not in changed_chart_ids" in show_method
    assert "refreshed_candidates =" in show_method
    assert "if int(candidate[0]) in changed_chart_ids" in show_method
    assert "top_k=max(1, len(candidates))" in show_method
