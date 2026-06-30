from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_unsaved_prompt_has_deterministic_leave_buttons_without_changing_save_path():
    method = _method_source("_confirm_discard_or_save")
    assert 'save_button = dialog.addButton("Save", QMessageBox.AcceptRole)' in method
    assert 'discard_button = dialog.addButton("Discard", QMessageBox.DestructiveRole)' in method
    assert 'cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)' in method
    assert "dialog.setDefaultButton(save_button)" in method
    assert "dialog.setEscapeButton(cancel_button)" in method
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
    assert "self.on_update_chart(show_dialog=False, recalculate_chart=False)" in autosave_method
    assert "self._set_lucygoosey(False)" in autosave_method
    assert "self.on_update_chart(show_dialog=False, recalculate_chart=False)" in metric_method
    assert "self._set_lucygoosey(False)" in metric_method
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" not in autosave_method
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" not in metric_method


def test_prompt_open_defers_but_does_not_disable_timed_autosaves():
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "if self._leaving_chart_view_prompt_open:" in autosave_method
    assert "self._metadata_autosave_timer.start(2000)" in autosave_method
    assert "if self._leaving_chart_view_prompt_open:" in metric_method
    assert "self._sentiment_metrics_autosave_timer.start(2000)" in metric_method


def test_metric_flush_does_not_save_after_discard_clears_dirty_flag():
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "if had_pending_metric_save:" in metric_method
    assert "self._sentiment_metrics_autosave_timer.stop()" in metric_method
    assert "if not self._lucygoosey:" in metric_method
    assert "if not had_pending_metric_save and not self._lucygoosey:" not in metric_method
    assert metric_method.index("if not self._lucygoosey:") < metric_method.index("self.on_update_chart(show_dialog=False, recalculate_chart=False)")


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
    assert "self._metadata_autosave_timer.start(2000)" in method
    assert "self._autosave_checkbox_state()" not in method
    assert method.index("self._mark_lucygoosey()") < method.index("self._metadata_autosave_timer.start(2000)")


def test_retcon_time_edits_defer_autosave_so_leave_prompt_can_win():
    method = _method_source("_on_retcon_time_changed")
    assert "self._mark_lucygoosey()" in method
    assert "self._metadata_autosave_timer.start(2000)" in method
    assert "self._autosave_checkbox_state()" not in method


def test_loaded_rectified_time_is_restored_before_checkbox_enabled():
    method = _method_source("load_chart_by_id")
    stored_hour_index = method.index('stored_retcon_hour = getattr(chart, "retcon_hour", None)')
    set_time_index = method.index("self.retcon_time_edit.setTime", stored_hour_index)
    checkbox_index = method.index("self.retcon_time_checkbox.setChecked(chart.retcon_time_used)")
    assert stored_hour_index < set_time_index < checkbox_index
