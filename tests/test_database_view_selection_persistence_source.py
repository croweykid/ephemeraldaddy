from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
SELECTION_SOURCE = Path(
    "ephemeraldaddy/gui/features/database_view/selection.py"
).read_text(encoding="utf-8")


def _method_source(method_name: str) -> str:
    start = APP_SOURCE.index(f"    def {method_name}")
    next_method = APP_SOURCE.index("\n    def ", start + 1)
    return APP_SOURCE[start:next_method]


def test_selection_changed_can_skip_persistent_selection_sync_for_programmatic_refreshes():
    method = _method_source("_on_selection_changed")

    assert "sync_persistent_selection: bool = True" in method
    assert "if sync_persistent_selection:" in method
    assert "self._merge_visible_selection_into_persistent_selection" in method


def test_sort_refresh_preserves_hidden_persistent_selection():
    method = _method_source("_set_sort_mode")

    assert "selected_ids=selected_ids or None" in method
    assert "refresh_metrics=False" in method
    assert "_on_selection_changed" not in method
    assert method.index("self._cancel_inline_chart_rename()") < method.index(
        "self._populate_list("
    )


def test_hide_hypothetical_refresh_preserves_hidden_persistent_selection():
    method = _method_source("_on_hide_hypothetical_toggled")

    assert "self._populate_list(refresh_metrics=False)" in method
    assert "sync_persistent_selection=False" in method


def test_auto_placeholder_exclusion_does_not_persist_user_preference():
    method = _method_source("_auto_exclude_placeholders_for_astrological_filters")

    assert "QSignalBlocker(self.incomplete_birthdate_checkbox)" in method
    assert "setMode(QuadStateSlider.MODE_FALSE)" in method
    assert "SETTINGS_KEY_HIDE_PLACEHOLDER_CHARTS_FILTER" not in method


def test_close_event_does_not_persist_transient_placeholder_filter_state():
    method = _method_source("closeEvent")

    assert "SETTINGS_KEY_HIDE_PLACEHOLDER_CHARTS_FILTER" not in method


def test_single_chart_deselection_is_remembered_for_undo():
    clear_method = _method_source("_clear_persistent_selection")

    assert "DatabaseSelectionController(DatabaseSelectionModel())" in APP_SOURCE
    assert (
        "self._replace_persistent_selection_by_uids([], remember_deselection=True)"
        in clear_method
    )
    assert (
        "if remember_deselection and len(self.selected_uids) == 1 and not replacement:"
        in SELECTION_SOURCE
    )
    assert "self.prior_single_selection = self.selected_uids[0]" in SELECTION_SOURCE


def test_ctrl_z_restores_one_prior_deselected_selection():
    restore_method = _method_source("_restore_prior_deselected_selection")
    assert "restore_prior_single_selection()" in restore_method
    assert "if prior_selection is None:" in restore_method
    assert "self._sync_visible_selection_from_persistent_selection()" in restore_method
    assert "QKeySequence.StandardKey.Undo" in APP_SOURCE
    assert "self._restore_prior_deselected_selection()" in APP_SOURCE


def test_copy_uses_persistent_selection_for_all_selected_chart_names():
    method = _method_source("_selected_chart_names_for_clipboard")
    copy_method = _method_source("_copy_selected_chart_names_to_clipboard")

    assert "self._reconcile_persistent_selection_with_database()" in method
    assert "_database_selection.model.selected_uids" in method
    assert "chart_uid in copied_uids" in method
    assert "self._local_row_id_by_chart_uid.get(chart_uid)" in method
    assert "_similar_charts_popout_chart_names_by_id" in method
    assert '"\\n".join(selected_names)' in copy_method


def test_database_view_has_local_uid_normalizer_for_persistent_selection():
    assert "class ManageChartsDialog" in APP_SOURCE
    class_source = APP_SOURCE[
        APP_SOURCE.index("class ManageChartsDialog") : APP_SOURCE.index(
            "class MainWindow"
        )
    ]
    assert "def _normalized_chart_uid_key" in class_source
    assert (
        "return ManageChartsDialog._normalized_chart_uid_key(raw_chart_uid)"
        in class_source
    )


def test_database_view_does_not_retain_parallel_integer_selection_state():
    class_source = APP_SOURCE[
        APP_SOURCE.index("class ManageChartsDialog") : APP_SOURCE.index(
            "class MainWindow"
        )
    ]

    assert "_selected_local_row_id_order" not in class_source
    assert "_selected_local_row_ids_set" not in class_source
    assert "DatabaseSelectionController(DatabaseSelectionModel())" in class_source
    assert "selected_uids: list[str]" in SELECTION_SOURCE
    assert (
        "return self._local_row_ids_for_uids(self._database_selection.model.selected_uids)"
        in class_source
    )


def test_navigation_anchor_does_not_retain_parallel_integer_identity():
    class_source = APP_SOURCE[
        APP_SOURCE.index("class ManageChartsDialog") : APP_SOURCE.index(
            "class MainWindow"
        )
    ]

    assert "_filter_navigation_anchor_local_row_id" not in class_source
    assert "anchor_uid: str | None" in SELECTION_SOURCE
    assert "self._database_selection.model.anchor_uid" in class_source
