from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_hydrated_rows_build_bidirectional_uid_persistence_indexes():
    method = _method_source("_rebuild_hydrated_chart_identity_indexes")

    assert "self._chart_uid_by_local_row_id =" in method
    assert "self._local_row_id_by_chart_uid =" in method
    assert "get_chart_uid" not in method
    assert "get_chart_ids_by_uid" not in method


def test_filter_and_placeholder_hot_paths_do_not_query_for_uids():
    for method_name in (
        "_chart_matches_filters",
        "_is_placeholder_local_row_id",
        "_is_similarities_placeholder_local_row_id",
    ):
        method = _method_source(method_name)
        assert "self._chart_uid_by_local_row_id.get(int(chart_id))" in method
        assert "get_chart_uid(chart_id)" not in method


def test_uid_to_row_resolution_only_queries_for_unhydrated_uids():
    method = _method_source("_local_row_ids_for_uids")

    assert "self._local_row_id_by_chart_uid" in method
    assert "if missing_uids:" in method
    assert "get_chart_ids_by_uid(missing_uids)" in method


def test_refresh_builds_identity_indexes_at_hydration_boundary():
    method = _method_source("_refresh_charts")

    loaded_rows = method.index("self._chart_rows = list_charts()")
    built_indexes = method.index("self._rebuild_hydrated_chart_identity_indexes()")
    populated_list = method.index("self._populate_list(")
    assert loaded_rows < built_indexes < populated_list


def test_metrics_row_token_reuses_uid_stored_in_hydrated_row():
    method = _method_source("_database_metrics_rows_token")

    assert 'chart_uid = str(row[30] or f"legacy-id:{chart_id}")' in method
    assert "get_chart_uid_map" not in method
