"""Static regression contract for Chart View save/autosave integrity.

These checks intentionally keep the PR #1890/#1893 save-path guarantees together
so later GUI refactors cannot silently turn subjective edits into full chart
recalculations or make the two autosave timers race each other.

This module reads Python source as text; it does *not* launch Qt, wait for real
timers, or reopen a chart from a real database.  See
``docs/chart_view_save_integrity_regressions.md`` for the exact guarantees,
limitations, command-line usage, and complementary manual GUI procedure.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
DB_SOURCE = (REPO_ROOT / "ephemeraldaddy/core/db.py").read_text()
RIGHT_PANEL_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py"
).read_text()


def _method(source: str, name: str) -> str:
    marker = f"    def {name}"
    start = source.index(marker)
    end = source.find("\n    def ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def _function(source: str, name: str) -> str:
    marker = f"def {name}"
    start = source.index(marker)
    end = source.find("\ndef ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_subjective_only_save_uses_lightweight_update_and_preserves_calculated_payloads():
    save = _method(APP_SOURCE, "on_update_chart")
    lightweight = _function(DB_SOURCE, "update_chart_lightweight_metadata")
    update_sql = lightweight.split("UPDATE charts", 1)[1].split("WHERE id = ?", 1)[0]

    assert "if recalculate_chart:\n                update_chart(chart_id, chart, **save_kwargs)" in save
    assert "else:\n                update_chart_lightweight_metadata(chart_id, chart)" in save
    assert "positions" not in update_sql
    assert "houses" not in update_sql
    assert "_persist_chart_derived_cache" not in lightweight


def test_rapid_subjective_edits_share_one_debounced_lightweight_timer():
    sentiment = _method(APP_SOURCE, "_on_sentiment_toggled")
    relationship = _method(APP_SOURCE, "_on_relationship_type_toggled")
    score = _method(APP_SOURCE, "_on_sentiment_metric_changed")
    queue = _method(APP_SOURCE, "_queue_subjective_notes_autosave")
    flush = _method(APP_SOURCE, "_flush_pending_sentiment_metrics_save")

    for handler in (sentiment, relationship, score):
        assert "self._queue_subjective_notes_autosave()" in handler
    assert "self._sentiment_metrics_autosave_timer.start(2000)" in queue
    assert "recalculate_chart=False" in flush
    assert "subjective_notes_autosave=True" in flush


def test_all_timing_inputs_request_a_full_recalculation():
    timing_handlers = (
        "_on_birth_time_changed",
        "_on_retcon_time_toggled",
        "_on_retcon_time_changed",
        "_on_rectification_range_toggled",
        "_on_rectification_range_changed",
    )
    for name in timing_handlers:
        assert "self._queue_timing_preview_update()" in _method(APP_SOURCE, name)

    queue = _method(APP_SOURCE, "_queue_timing_preview_update")
    assert "self._metadata_autosave_requires_recalculation = True" in queue
    assert "self._metadata_autosave_timer.start(2500)" not in queue


def test_subjective_flush_defers_to_pending_birth_recalculation_without_losing_dirty_state():
    flush = _method(APP_SOURCE, "_flush_pending_sentiment_metrics_save")
    guard = flush.index("if self._metadata_autosave_requires_recalculation:")
    subjective_save = flush.index("subjective_notes_autosave=True")
    branch = flush[guard:subjective_save]

    assert guard < subjective_save
    assert "self._metadata_autosave_timer.start(2500)" in branch
    assert "return" in branch
    assert "self._set_lucygoosey(False)" not in branch


def test_subjective_autosave_also_persists_material_facts_before_clearing_dirty_state():
    save = _method(APP_SOURCE, "on_update_chart")
    material_save = save.index("self._save_material_facts_for_chart(chart_id)")
    clear_dirty = save.index("self._set_lucygoosey(False)", material_save)

    assert material_save < clear_dirty


def test_pending_autosaves_are_deferred_during_leave_prompt_and_save_remains_available():
    prompt = _method(APP_SOURCE, "_confirm_discard_or_save")
    metadata_flush = _method(APP_SOURCE, "_autosave_checkbox_state")
    subjective_flush = _method(APP_SOURCE, "_flush_pending_sentiment_metrics_save")

    assert "QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel" in prompt
    assert "self.on_update_chart(show_dialog=True)" in prompt
    assert "if self._leaving_chart_view_prompt_open:" in metadata_flush
    assert "self._metadata_autosave_timer.start(delay_ms)" in metadata_flush
    assert "if self._leaving_chart_view_prompt_open:" in subjective_flush
    assert "self._sentiment_metrics_autosave_timer.start(2000)" in subjective_flush


def test_subjective_notes_activation_never_schedules_anagrams():
    schedule = _function(RIGHT_PANEL_SOURCE, "schedule_chart_render_for_active_right_panel")

    assert 'active_panel == "abc"' in schedule
    assert 'active_panel in {"subjective_notes", "abc"}' not in schedule
