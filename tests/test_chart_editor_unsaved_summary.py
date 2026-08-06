from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from ephemeraldaddy.gui.features.chart_editor.unsaved_summary import (
    ChartEditorDraftSummary,
    RECALCULATION_NOTICE,
    build_unsaved_changes_prompt_details,
    format_unsaved_change_line,
    summarize_chart_editor_draft_changes,
)

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_unsaved_prompt_details_are_bounded_and_user_facing():
    assert format_unsaved_change_line("Birth time", "12:00", "12:05") == "Birth time: 12:00 → 12:05"
    details = build_unsaved_changes_prompt_details(str(index) for index in range(12))
    assert details.startswith("Unsaved changes detected:")
    assert "• 0" in details
    assert "…and 4 more field(s)." in details


def test_unsaved_prompt_includes_change_summary_details():
    prompt = _method_source("_confirm_discard_or_save")
    summary = _method_source("_current_unsaved_change_summary_lines")

    assert "dialog.setInformativeText(" in prompt
    assert "build_unsaved_changes_prompt_details(" in prompt
    assert "self._current_unsaved_change_summary_lines()" in prompt
    assert "ChartEditorDraftSummary(" in summary
    assert "summarize_chart_editor_draft_changes(" in summary
    assert "load_chart_by_uid(self.current_chart_uid)" in summary


def test_draft_comparison_is_owned_outside_app_and_reports_timing_changes():
    saved = SimpleNamespace(
        name="Ada", alias="", from_whence="", birth_month=1, birth_day=2,
        birth_year=2000, birth_place="London", birthtime_unknown=False,
        dt=datetime(2000, 1, 2, 12, 0), retcon_time_used=False,
        retcon_hour=12, retcon_minute=0, rectification_range_used=False,
        rectification_range_start_minute=660,
        rectification_range_end_minute=780, chart_type="Person", gender="",
        tags=[], comments="", rectification_notes="", biography="",
        chart_data_source="", enneagram_type=["9", "8"],
        tritype=[9, 4, 5], mbti=["I", "N", "T", "P"],
    )
    draft = ChartEditorDraftSummary(
        name="Ada", alias="", from_whence="", birth_date="2000-01-02",
        birth_place="London", birthtime_unknown=True, birth_time="12:15",
        retcon_time_used=True, retcon_time="12:15",
        rectification_range_used=True, rectification_range="11:30 to 13:30",
        chart_type="Person", gender="", tags=(), comments="",
        rectification_notes="", biography="", chart_data_source="",
        enneagram_type=("9", "8"), tritype=(9, 4, 5),
        mbti=("I", "N", "T", "P"),
    )

    changes = summarize_chart_editor_draft_changes(
        saved, draft, recalculation_required=True
    )

    assert changes[0] == RECALCULATION_NOTICE
    assert "Unknown birth time: no → yes" in changes
    assert "Use rectified time: no → yes" in changes
    assert "Rectified range: 11:00 to 13:00 → 11:30 to 13:30" in changes


def test_draft_comparison_summarizes_typology_changes():
    saved = SimpleNamespace(
        enneagram_type=["9", "8"], tritype=[9, 4, 5],
        mbti=["I", "N", "T", "P"],
    )
    draft = ChartEditorDraftSummary(
        name="", alias="", from_whence="", birth_date="blank",
        birth_place="", birthtime_unknown=False, birth_time="blank",
        retcon_time_used=False, retcon_time="00:00",
        rectification_range_used=False,
        rectification_range="blank to blank", chart_type="", gender="",
        tags=(), comments="", rectification_notes="", biography="",
        chart_data_source="", enneagram_type=("4", "5"),
        tritype=(4, 6, 9), mbti=("E", "N", "F", "J"),
    )

    changes = summarize_chart_editor_draft_changes(
        saved, draft, recalculation_required=False
    )

    assert "Enneagram: 9w8 → 4w5" in changes
    assert "Tri-Type: 9-4-5 → 4-6-9" in changes
    assert "MBTI: INTP → ENFJ" in changes
