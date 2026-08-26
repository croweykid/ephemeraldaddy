from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
WORKER_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/similar_charts_worker.py"
).read_text(encoding="utf-8")


def _class_source(name: str, next_name: str | None = None) -> str:
    start = APP_SOURCE.index(f"class {name}")
    end = APP_SOURCE.index(f"class {next_name}", start) if next_name else len(APP_SOURCE)
    return APP_SOURCE[start:end]


def test_database_view_hidden_and_visible_state_is_uid_owned():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "self._hidden_chart_uids" in source
    assert "self._hidden_local_row_ids =" not in source
    assert "self._visible_local_row_ids" not in source
    assert "def _hidden_local_row_ids_for_persistence" in source


def test_chart_editor_hidden_state_is_uid_owned():
    source = _class_source("MainWindow")

    assert "self._hidden_chart_uids" in source
    assert "self._hidden_local_row_ids =" not in source
    assert "self._hidden_local_row_ids.add" not in source
    assert "self._hidden_local_row_ids.discard" not in source
    assert "def _refresh_database_view_after_chart_hidden_toggle(self, changed_chart_uid: str)" in source


def test_batch_refresh_does_not_retain_parallel_local_ids():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_pending_batch_refresh_uids" in source
    assert "_pending_batch_refresh_ids" not in source
    assert "changed_ids = set(self._local_row_ids_for_uids(changed_uids))" in source


def test_similar_charts_worker_owns_uid_identity_only():
    assert "current_chart_uid: str | None" in WORKER_SOURCE
    assert "hidden_chart_uids: set[str] | None" in WORKER_SOURCE
    assert "self._current_chart_uid" in WORKER_SOURCE
    assert "self._hidden_chart_uids" in WORKER_SOURCE
    assert "self._current_chart_id" not in WORKER_SOURCE
    assert "self._hidden_chart_ids" not in WORKER_SOURCE
    assert "get_chart_ids_by_uid(self._hidden_chart_uids)" in WORKER_SOURCE


def test_inline_rename_identity_is_uid_owned():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_inline_rename_chart_uid" in source
    assert "_inline_rename_chart_id" not in source
    assert "self._apply_batch_nonastral_patch({chart_uid}" in source
    assert "self._refresh_filters_after_batch_edit(chart_uids={chart_uid})" in source


def test_possible_duplicate_controller_state_is_uid_keyed():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_possible_duplicate_chart_uids" in source
    assert "_possible_duplicate_related_names_by_uid" in source
    assert "_possible_duplicate_likelihoods_by_uid" in source
    assert "_possible_duplicate_sort_keys_by_uid" in source
    assert "_possible_duplicate_group_by_uid" in source
    assert "_possible_duplicate_chart_ids" not in source
    assert "_excluded_duplicate_pairs" not in source


def test_trait_ranking_selection_state_is_uid_owned():
    source = Path(
        "ephemeraldaddy/gui/features/charts/database_analytics.py"
    ).read_text(encoding="utf-8")

    assert "_traits_distribution_manual_rank_chart_uids" in source
    assert "_traits_distribution_latest_selected_chart_uids" in source
    assert "_traits_distribution_manual_rank_chart_ids" not in source
    assert "_traits_distribution_latest_selected_local_row_ids" not in source
    assert "hidden_chart_uids: set[str]" in source


def test_database_metrics_dirty_and_snapshot_state_is_uid_keyed():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_database_metric_snapshots_by_uid: dict[str" in source
    assert "_database_metrics_lucy_goosey_uids: set[str]" in source
    assert "_database_metric_snapshots:" not in source
    assert "_database_metrics_lucy_goosey_ids" not in source
    assert "DATABASE_METRICS_PERSISTENT_CACHE_VERSION = 3" in APP_SOURCE


def test_active_and_displayed_row_caches_are_uid_keyed():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_active_chart_rows_by_uid: dict[str" in source
    assert "_displayed_chart_rows_by_uid: dict[str" in source
    assert "_active_chart_rows_by_id" not in source
    assert "_displayed_chart_rows_by_id" not in source


def test_displayed_row_uid_is_normalized_before_cache_insertion():
    source = _class_source("DatabaseViewWindow", "MainWindow")
    populate_source = source[source.index("    def _populate_list(") :]

    normalize_uid = populate_source.index(
        'item_chart_uid = str(_chart_uid or "").strip().upper()'
    )
    cache_row = populate_source.index(
        "self._displayed_chart_rows_by_uid[item_chart_uid] = ("
    )
    create_item = populate_source.index("item = QListWidgetItem(label)")

    assert normalize_uid < cache_row < create_item


def test_similar_chart_candidate_exclusions_are_uid_owned():
    source = _class_source("MainWindow")

    assert "_similar_charts_candidate_excluded_chart_uids" in source
    assert "_similar_charts_candidate_excluded_chart_ids" not in source
    assert "get_chart_ids_by_uid" in source


def test_charts_controller_has_no_legacy_pending_id_callbacks():
    source = Path(
        "ephemeraldaddy/gui/features/controllers/main_window.py"
    ).read_text(encoding="utf-8")
    controller = source[source.index("class ChartsController"):]

    assert "get_pending_changed_refreshes" in controller
    assert "clear_pending_changed_refreshes" in controller
    assert "get_pending_changed_ids" not in controller
    assert "clear_pending_changed_ids" not in controller


def test_high_similarity_and_worker_callers_pass_hidden_uids():
    app_source = _class_source("MainWindow")
    similarities_source = Path(
        "ephemeraldaddy/gui/features/charts/similarities_analysis.py"
    ).read_text(encoding="utf-8")

    high_similarity_call = APP_SOURCE[
        APP_SOURCE.index("    def _show_high_similarity_chart_pairs"):
        APP_SOURCE.index("    def _open_high_similarity_chart_uid")
    ]
    worker_call = app_source[
        app_source.index("    def _start_similar_charts_worker"):
        app_source.index("    def _forget_similar_charts_worker_job")
    ]
    high_similarity_function = similarities_source[
        similarities_source.index("def show_high_similarity_chart_pairs("):
    ]

    assert "hidden_chart_uids=set(self._hidden_chart_uids)" in high_similarity_call
    assert "hidden_chart_uids=set(self._hidden_chart_uids)" in worker_call
    assert "hidden_chart_ids=" not in worker_call
    assert "hidden_chart_uids: set[str] | None" in high_similarity_function
    assert "get_chart_ids_by_uid(hidden_chart_uids or set())" in high_similarity_function


def test_weirdness_metadata_cache_is_uid_keyed():
    source = _class_source("DatabaseViewWindow", "MainWindow")

    assert "_weirdness_cache_metadata_by_uid" in source
    assert "_weirdness_cache_metadata_by_id" not in source
    assert "metadata[normalized_chart_uid]" in source
