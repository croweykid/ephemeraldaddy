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
    source = _class_source("ManageChartsDialog", "MainWindow")

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
    source = _class_source("ManageChartsDialog", "MainWindow")

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
    source = _class_source("ManageChartsDialog", "MainWindow")

    assert "_inline_rename_chart_uid" in source
    assert "_inline_rename_chart_id" not in source
    assert "self._apply_batch_nonastral_patch({chart_uid}" in source
    assert "self._refresh_filters_after_batch_edit(chart_uids={chart_uid})" in source
