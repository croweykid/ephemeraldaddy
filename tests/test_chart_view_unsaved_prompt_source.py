from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_unsaved_prompt_has_deterministic_leave_buttons_without_changing_save_path():
    method = _method_source("_confirm_discard_or_save")
    assert "dialog.setStandardButtons(" in method
    assert "QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel" in method
    assert "dialog.setDefaultButton(QMessageBox.Save)" in method
    assert "dialog.setEscapeButton(QMessageBox.Cancel)" in method
    assert "self.on_update_chart(show_dialog=True)" in method
    assert 'if not self._lucygoosey:' in method
    assert 'self._metadata_autosave_requires_recalculation = False' in method
    assert "recalculate_chart=recalculate_chart" not in method
    assert "return self.on_update_chart" not in method
    assert "self._set_lucygoosey(False)" in method
    assert "return not self._lucygoosey" in method


def test_unsaved_prompt_marks_modal_state_only_while_prompt_is_open():
    method = _method_source("_confirm_discard_or_save")
    assert "self._leaving_chart_view_prompt_open = True" in method
    assert "dialog.exec()" in method
    assert "finally:" in method
    assert "self._leaving_chart_view_prompt_open = False" in method
    assert method.index("self._leaving_chart_view_prompt_open = True") < method.index("dialog.exec()")
    assert method.index("dialog.exec()") < method.index("self._leaving_chart_view_prompt_open = False")


def test_timed_autosaves_only_clear_dirty_state_after_a_successful_save():
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "self.on_update_chart(show_dialog=False, recalculate_chart=recalculate_chart)" in autosave_method
    assert "self._set_lucygoosey(False)" not in autosave_method
    assert "if self._lucygoosey and recalculate_chart:" in autosave_method
    assert "self._metadata_autosave_requires_recalculation = True" in autosave_method
    assert "subjective_notes_autosave=True" in metric_method
    assert "self._set_lucygoosey(False)" not in metric_method
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" not in autosave_method
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" not in metric_method


def test_prompt_open_defers_but_does_not_disable_timed_autosaves():
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "if self._leaving_chart_view_prompt_open:" in autosave_method
    assert "self._metadata_autosave_timer.start(delay_ms)" in autosave_method
    assert "if self._leaving_chart_view_prompt_open:" in metric_method
    assert "self._sentiment_metrics_autosave_timer.start(2000)" in metric_method


def test_metric_flush_does_not_save_after_discard_clears_dirty_flag():
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "if had_pending_metric_save:" in metric_method
    assert "self._sentiment_metrics_autosave_timer.stop()" in metric_method
    assert "if not self._lucygoosey:" in metric_method
    assert "if not had_pending_metric_save and not self._lucygoosey:" not in metric_method
    assert metric_method.index("if not self._lucygoosey:") < metric_method.index("subjective_notes_autosave=True")


def test_lucygoosey_timed_autosaves_are_update_only_for_saved_charts():
    should_auto_method = _method_source("_should_auto_update_sentiments")
    can_autosave_method = _method_source("_can_autosave_current_chart")
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "return self._can_autosave_current_chart()" in should_auto_method
    assert "return self._current_local_row_id() is not None" in can_autosave_method
    assert "Lucygoosey autosaves are update-only" in can_autosave_method
    assert "not self._can_autosave_current_chart()" in autosave_method
    assert "if not self._should_auto_update_sentiments():" in metric_method


def test_chart_save_signature_remains_void_for_existing_callers():
    method = _method_source("on_update_chart")
    assert "-> bool" not in method.splitlines()[0]
    assert not method.rstrip().endswith("return True")


def test_retcon_toggle_marks_dirty_before_deferred_autosave():
    method = _method_source("_on_retcon_time_toggled")
    assert "self._mark_lucygoosey()" in method
    assert "self._metadata_autosave_timer.start(2500)" in method
    assert "self._autosave_checkbox_state()" not in method
    assert method.index("self._mark_lucygoosey()") < method.index("self._metadata_autosave_timer.start(2500)")


def test_subjective_checkbox_autosaves_use_batched_subjective_timer():
    sentiment_method = _method_source("_on_sentiment_toggled")
    relationship_method = _method_source("_on_relationship_type_toggled")
    queue_method = _method_source("_queue_subjective_notes_autosave")
    assert "self._metadata_autosave_timer.start(2000)" not in sentiment_method
    assert "self._metadata_autosave_timer.start(2000)" not in relationship_method
    assert "self._queue_subjective_notes_autosave()" in sentiment_method
    assert "self._queue_subjective_notes_autosave()" in relationship_method
    assert "self._sentiment_metrics_autosave_timer.start(2000)" in queue_method


def test_typology_fields_queue_lightweight_autosaves():
    controller_source = (
        Path(__file__).resolve().parents[1]
        / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()
    typology_start = controller_source.index("def _populate_typology_section")
    typology_end = controller_source.index(
        "def update_chart_view_typology_subheader", typology_start
    )
    typology_source = controller_source[typology_start:typology_end]

    assert typology_source.count(
        "owner._chart_editor_controller.on_lightweight_metadata_changed"
    ) == 2
    assert "connect(owner._mark_lucygoosey)" not in typology_source


def test_flavor_text_fields_queue_lightweight_autosaves():
    for field_name in (
        "comments_edit",
        "rectification_edit",
        "biography_edit",
        "source_edit",
    ):
        assert (
            f"self.{field_name}.textChanged.connect("
            "\n            self._chart_editor_controller.on_lightweight_metadata_changed"
        ) in APP_SOURCE
    assert "def _on_lightweight_metadata_changed" not in APP_SOURCE


def test_leave_check_flushes_lightweight_autosave_before_prompting():
    method = _method_source("_confirm_discard_or_save")
    timer_check = "if self._sentiment_metrics_autosave_timer.isActive():"
    flush = "self._flush_pending_sentiment_metrics_save()"
    dirty_check = "if not self._lucygoosey:"
    assert timer_check in method
    assert flush in method
    assert method.index(timer_check) < method.index(flush) < method.index(dirty_check)
    assert method.index(flush) < method.index("self._flush_pending_metadata_save()")


def test_authoritative_birth_inputs_are_protected_from_lightweight_autosave():
    birth_handler = _method_source("_on_birth_date_field_changed")
    place_handler = _method_source("_on_place_text_changed")
    assert (
        "self._chart_editor_controller.on_authoritative_metadata_changed()"
        in birth_handler
    )
    assert (
        "self._chart_editor_controller.on_authoritative_metadata_changed()"
        in place_handler
    )


def test_failed_timed_autosaves_are_reported_to_terminal():
    metadata_method = _method_source("_autosave_checkbox_state")
    lightweight_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert (
        'self._chart_editor_controller.report_incomplete_autosave("metadata")'
        in metadata_method
    )
    assert (
        "self._chart_editor_controller.report_incomplete_autosave("
        in lightweight_method
    )
    assert '"lightweight metadata"' in lightweight_method


def test_retcon_time_edits_defer_autosave_so_leave_prompt_can_win():
    method = _method_source("_on_retcon_time_changed")
    assert "self._mark_lucygoosey()" in method
    assert "self._metadata_autosave_timer.start(2500)" in method
    assert "self._autosave_checkbox_state()" not in method


def test_save_update_caches_chart_view_entry_by_uid_not_row_id():
    method = _method_source("on_update_chart")
    assert "self._set_current_chart_uid(chart.chart_uid)" in method
    assert "self._cache_chart_view_navigation_entry(self.current_chart_uid, chart)" in method
    assert "self._cache_chart_view_navigation_entry(chart_id, chart)" not in method


def test_current_chart_uid_for_navigation_does_not_round_trip_through_row_id():
    method = _method_source("_current_chart_uid_for_navigation")
    assert "return self._normalized_chart_uid_key(self.current_chart_uid)" in method
    assert "get_chart_uid" not in method
    assert "_current_local_row_id" not in method


def test_delete_flow_invalidates_navigation_cache_with_predelete_uids():
    delete_start = APP_SOURCE.index("    def _on_delete(self) -> None:")
    delete_end = APP_SOURCE.find("\n    def ", delete_start + 1)
    delete_method = APP_SOURCE[delete_start:delete_end]
    deleted_callback = _method_source("_on_charts_deleted")
    assert "deleted_chart_uids = set(chart_uids)" in delete_method
    assert "delete_charts_by_uids(chart_uids)" in delete_method
    assert "parent._on_charts_deleted(set(chart_ids), chart_uids=deleted_chart_uids)" in delete_method
    assert "chart_uids: set[str] | None = None" in deleted_callback
    assert "self._invalidate_chart_view_navigation_cache(normalized_chart_uids)" in deleted_callback
    assert "_invalidate_chart_view_navigation_cache_for_ids" not in APP_SOURCE
    assert 'getattr(cached_chart, "id", 0)' not in deleted_callback


def test_loaded_rectified_time_is_restored_before_checkbox_enabled():
    method = _method_source("load_chart_by_uid")
    stored_hour_index = method.index('stored_retcon_hour = getattr(chart, "retcon_hour", None)')
    set_time_index = method.index("self.retcon_time_edit.setTime", stored_hour_index)
    checkbox_index = method.index("self.retcon_time_checkbox.setChecked(chart.retcon_time_used)")
    assert stored_hour_index < set_time_index < checkbox_index


def test_retcon_controls_do_not_have_duplicate_dirty_signal_connections():
    assert "self.retcon_time_checkbox.toggled.connect(self._mark_lucygoosey)" not in APP_SOURCE
    assert "self.retcon_time_edit.timeChanged.connect(self._mark_lucygoosey)" not in APP_SOURCE
    assert "self.retcon_time_checkbox.toggled.connect(self._on_retcon_time_toggled)" in APP_SOURCE
    assert "self.retcon_time_edit.timeChanged.connect(self._on_retcon_time_changed)" in APP_SOURCE


def test_subjective_autosave_preserves_mixed_changed_fields_for_refresh():
    method = _method_source("on_update_chart")
    changed_fields_index = method.index("changed_fields = self._chart_metadata_changed_fields(")
    update_index = method.index("self._update_sentiment_tally(", changed_fields_index)
    refresh_block = method[changed_fields_index:update_index]
    assert "changed_fields &= " not in refresh_block
    update_call = method[update_index:method.index("self._record_manage_charts_pending_change", update_index)]
    assert "update_similarities=bool(" in update_call
    assert '"birth_data" in changed_fields' in update_call


def test_subjective_autosave_defers_to_pending_recalculation_autosave():
    method = _method_source("_flush_pending_sentiment_metrics_save")
    recalc_guard = method.index("if self._metadata_autosave_requires_recalculation:")
    subjective_save = method.index("subjective_notes_autosave=True")
    assert recalc_guard < subjective_save
    recalc_branch = method[recalc_guard:subjective_save]
    assert "self._metadata_autosave_timer.isActive()" in recalc_branch
    assert "self._metadata_autosave_timer.start(2500)" in recalc_branch
    assert "return" in recalc_branch
    assert "self._set_lucygoosey(False)" not in recalc_branch


def test_subjective_autosave_still_saves_material_facts_sidecar():
    method = _method_source("on_update_chart")
    subjective_guard = method.index("if not subjective_notes_autosave:")
    material_save = method.index("self._save_material_facts_for_chart(chart_id)")
    previous_token = method.index("previous_recalculation_token =", material_save)
    assert subjective_guard < material_save < previous_token

def test_material_facts_load_preserves_outer_lucygoosey_suppression():
    method = _method_source("_load_material_facts_for_chart")
    assert "previous_suppress_lucygoosey = self._suppress_lucygoosey" in method
    assert "self._suppress_lucygoosey = True" in method
    assert "self._suppress_lucygoosey = previous_suppress_lucygoosey" in method
    assert "self._suppress_lucygoosey = False" not in method


def test_material_facts_load_uses_legacy_aware_loader():
    method = _method_source("_load_material_facts_for_chart")
    assert "identifiers = load_personal_identifiers(chart_id)" in method
    assert "load_personal_identifiers_by_uid(get_chart_uid(chart_id))" not in method


def test_chart_editor_retains_only_uid_current_chart_identity():
    class_source = APP_SOURCE[APP_SOURCE.index("class MainWindow"):]
    init_start = class_source.index("    def __init__")
    init_end = class_source.index("\n    def ", init_start + 1)
    init_source = class_source[init_start:init_end]
    identity_source = _method_source("_set_current_chart_uid")
    adapter_start = class_source.index("    def _current_local_row_id")
    adapter_end = class_source.index("\n    def ", adapter_start + 1)
    adapter_source = class_source[adapter_start:adapter_end]

    assert "self.current_chart_uid: str | None = None" in init_source
    assert "self.current_chart_id" not in class_source
    assert "chart_id" not in identity_source
    assert "chart:" not in identity_source
    assert "normalized_uid = self._normalized_chart_uid_key(chart_uid)" in identity_source
    assert "if normalized_uid is None:" in identity_source
    assert "self.current_chart_uid = normalized_uid" in identity_source
    assert "def _clear_current_chart_uid" in class_source
    assert "latest_uid == current_uid" in adapter_source
    assert "return get_chart_id_by_uid(current_uid)" in adapter_source


def test_pending_database_refresh_state_is_uid_owned():
    class_source = APP_SOURCE[APP_SOURCE.index("class MainWindow"):]
    pending_method = _method_source("_pending_manage_chart_refreshes")

    assert "_manage_charts_pending_changed_ids" not in class_source
    assert "_manage_charts_pending_changed_uids" in class_source
    assert "tuple[set[str], set[str], bool]" in pending_method
    assert "metric_uids.add(chart_uid)" in pending_method
    assert "lightweight_uids.add(chart_uid)" in pending_method
    assert "get_chart_id_by_uid" not in pending_method


def test_saved_chart_right_panel_consumers_use_uid_identity():
    controller_source = Path("ephemeraldaddy/gui/features/controllers/chart_right_panel.py").read_text()
    fallback_source = Path("ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert 'getattr(self._owner, "current_chart_uid", None) is not None' in controller_source
    assert 'getattr(owner, "current_chart_uid", None) is not None' in fallback_source
    assert "current_chart_id" not in controller_source
    assert "current_chart_id" not in fallback_source


def test_deleted_chart_uid_is_queued_as_full_refresh_tombstone():
    delete_method = _method_source("_on_delete_this_chart")
    discard_branch = _method_source("on_update_chart")
    record_method = _method_source("_record_manage_charts_pending_change")
    pending_method = _method_source("_pending_manage_chart_refreshes")
    clear_method = _method_source("_clear_pending_manage_chart_refreshes")
    coordinator_source = Path(
        "ephemeraldaddy/gui/features/windowing/appwide_window_coordinator.py"
    ).read_text()

    assert "chart_uid = self._current_chart_uid_for_navigation()" in delete_method
    assert "delete_charts_by_uids([chart_uid])" in delete_method
    assert "self._record_manage_charts_pending_change(chart_uid, refresh_metrics=True, deleted=True)" in delete_method
    assert "self._record_manage_charts_pending_change(chart_uid, refresh_metrics=True, deleted=True)" in discard_branch
    assert "get_chart_uid" not in record_method
    assert "if deleted:" in record_method
    assert "self._manage_charts_full_refresh_pending = True" in record_method
    assert "bool(self._manage_charts_full_refresh_pending)" in pending_method
    assert "self._manage_charts_full_refresh_pending = False" in clear_method
    assert "if force_full_refresh:" in coordinator_source
    assert 'refresh_reason = "deleted_chart"' in coordinator_source


def test_persisted_chart_object_caches_local_row_id_before_hot_path_use():
    method = _method_source("on_update_chart")
    assign_index = method.index("chart.id = int(chart_id)")

    assert method.index("chart_id = save_chart(") < assign_index
    assert method.index("self._set_current_chart_uid(chart.chart_uid)") > assign_index
    assert method.index("self._cache_chart_view_navigation_entry(self.current_chart_uid, chart)") > assign_index
    assert method.index("self._latest_chart = chart") > assign_index
