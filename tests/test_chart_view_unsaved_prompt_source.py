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


def test_timed_autosaves_keep_existing_save_and_dirty_state_defaults():
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "self.on_update_chart(show_dialog=False, recalculate_chart=recalculate_chart)" in autosave_method
    assert "self._set_lucygoosey(False)" in autosave_method
    assert "subjective_notes_autosave=True" in metric_method
    assert "self._set_lucygoosey(False)" in metric_method
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
    assert "return self.current_chart_id is not None" in can_autosave_method
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


def test_retcon_time_edits_defer_autosave_so_leave_prompt_can_win():
    method = _method_source("_on_retcon_time_changed")
    assert "self._mark_lucygoosey()" in method
    assert "self._metadata_autosave_timer.start(2500)" in method
    assert "self._autosave_checkbox_state()" not in method


def test_save_update_caches_chart_view_entry_by_uid_not_row_id():
    method = _method_source("on_update_chart")
    assert "self._set_current_chart_identity(chart_id, chart)" in method
    assert "self._cache_chart_view_navigation_entry(self.current_chart_uid, chart)" in method
    assert "self._cache_chart_view_navigation_entry(chart_id, chart)" not in method


def test_current_chart_uid_for_navigation_repairs_stale_uid_state():
    method = _method_source("_current_chart_uid_for_navigation")
    assert "latest_chart_uid" in method
    assert "current_chart_id is not None" in method
    assert "latest_chart_id == current_chart_id" in method
    assert "current_chart_id is None" not in method
    assert "stored_chart_uid != latest_chart_uid" in method
    assert "self.current_chart_uid = latest_chart_uid" in method
    assert "resolved_chart_uid = self._normalized_chart_uid_key(get_chart_uid(current_chart_id))" in method
    assert "return stored_chart_uid" in method


def test_delete_flow_invalidates_navigation_cache_with_predelete_uids():
    delete_start = APP_SOURCE.index("    def _on_delete(self) -> None:")
    delete_end = APP_SOURCE.find("\n    def ", delete_start + 1)
    delete_method = APP_SOURCE[delete_start:delete_end]
    deleted_callback = _method_source("_on_charts_deleted")
    id_adapter = _method_source("_invalidate_chart_view_navigation_cache_for_ids")

    assert "deleted_chart_uids = set(get_chart_uid_map(chart_ids).values())" in delete_method
    assert "parent._on_charts_deleted(set(chart_ids), chart_uids=deleted_chart_uids)" in delete_method
    assert "chart_uids: set[str] | None = None" in deleted_callback
    assert "self._invalidate_chart_view_navigation_cache(normalized_chart_uids)" in deleted_callback
    assert "self._invalidate_chart_view_navigation_cache_for_ids(chart_ids)" in deleted_callback
    assert 'getattr(cached_chart, "id", 0)' not in id_adapter


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
    update_call = method[update_index:method.index("self._manage_charts_pending_changed_ids.add", update_index)]
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
