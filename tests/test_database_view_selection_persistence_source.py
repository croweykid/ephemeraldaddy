from ephemeraldaddy.gui.features.charts.selection_header import SelectionSummaryCounts

from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


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

    assert "self._populate_list(selected_ids=selected_ids or None)" in method
    assert "sync_persistent_selection=False" in method


def test_hide_hypothetical_refresh_preserves_hidden_persistent_selection():
    method = _method_source("_on_hide_hypothetical_toggled")

    assert "selected_ids=set(self._selected_chart_ids())" in method
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
    init_section = APP_SOURCE[APP_SOURCE.index("self._selected_chart_id_order: list[int]"):APP_SOURCE.index("self._custom_collections", APP_SOURCE.index("self._selected_chart_id_order: list[int]"))]
    clear_method = _method_source("_clear_persistent_selection")
    selection_method = _method_source("_on_selection_changed")

    assert "self._prior_deselected_selection: list[int] = []" in init_section
    assert "self._remember_single_chart_deselection(previous_selection, [])" in clear_method
    assert "previous_selection = list(getattr(self, \"_selected_chart_id_order\", []))" in selection_method
    assert "self._remember_single_chart_deselection(" in selection_method


def test_ctrl_z_restores_one_prior_deselected_selection():
    restore_method = _method_source("_restore_prior_deselected_selection")
    assert "if len(prior_selection) != 1:" in restore_method
    assert "self._prior_deselected_selection = []" in restore_method
    assert "self._replace_persistent_selection(prior_selection)" in restore_method
    assert "self._sync_visible_selection_from_persistent_selection()" in restore_method
    assert "QKeySequence.StandardKey.Undo" in APP_SOURCE
    assert "self._restore_prior_deselected_selection()" in APP_SOURCE


def test_copy_uses_persistent_selection_for_all_selected_chart_names():
    method = _method_source("_selected_chart_names_for_clipboard")
    copy_method = _method_source("_copy_selected_chart_names_to_clipboard")

    assert "self._reconcile_persistent_selection_with_database()" in method
    assert "_selected_chart_ids_set" in method
    assert "chart_id not in selected_ids" in method
    assert "_selected_chart_id_order" in method
    assert "_similar_charts_popout_chart_names_by_id" in method
    assert "\"\\n\".join(selected_names)" in copy_method
