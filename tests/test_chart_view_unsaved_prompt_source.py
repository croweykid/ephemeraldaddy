from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_unsaved_prompt_stops_pending_autosaves_while_user_decides():
    method = _method_source("_confirm_discard_or_save")
    assert "pending_metadata_autosave = self._metadata_autosave_timer.isActive()" in method
    assert "pending_metric_autosave = self._sentiment_metrics_autosave_timer.isActive()" in method
    assert "self._metadata_autosave_timer.stop()" in method
    assert "self._sentiment_metrics_autosave_timer.stop()" in method
    assert "dialog.exec()" in method
    assert method.index("self._metadata_autosave_timer.stop()") < method.index("dialog.exec()")
    assert method.index("self._sentiment_metrics_autosave_timer.stop()") < method.index("dialog.exec()")


def test_unsaved_prompt_buttons_have_deterministic_outcomes():
    method = _method_source("_confirm_discard_or_save")
    assert 'save_button = dialog.addButton("Save", QMessageBox.AcceptRole)' in method
    assert 'discard_button = dialog.addButton("Discard", QMessageBox.DestructiveRole)' in method
    assert 'cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)' in method
    assert "dialog.setEscapeButton(cancel_button)" in method
    assert "return self.on_update_chart(show_dialog=True)" in method
    assert "if clicked_button == discard_button:" in method
    assert "self._set_lucygoosey(False)" in method
    assert "return False" in method


def test_autosave_only_clears_dirty_flag_after_successful_save():
    autosave_method = _method_source("_autosave_checkbox_state")
    metric_method = _method_source("_flush_pending_sentiment_metrics_save")
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" in autosave_method
    assert "if self.on_update_chart(show_dialog=False, recalculate_chart=False):" in metric_method


def test_chart_save_reports_success_to_unsaved_prompt():
    method = _method_source("on_update_chart")
    assert "-> bool" in method.splitlines()[0]
    assert "return False" in method
    assert method.rstrip().endswith("return True")
