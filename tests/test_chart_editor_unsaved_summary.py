from pathlib import Path

from ephemeraldaddy.gui.features.chart_editor.unsaved_summary import (
    build_unsaved_changes_prompt_details,
    format_unsaved_change_line,
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
    assert "Birth/time calculation fields changed; chart recalculation is required." in summary
    assert "Unknown birth time" in summary
    assert "Use rectified time" in summary
    assert "Use rectified range" in summary
    assert "Rectified range" in summary
