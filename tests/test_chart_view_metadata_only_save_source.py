from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_chart_view_has_metadata_only_save_guard():
    assert "def _saved_chart_birth_inputs_match_form" in APP_SOURCE
    assert "descriptive metadata such as alias" in APP_SOURCE
    assert "saved_chart is not None and self._saved_chart_birth_inputs_match_form(saved_chart)" in APP_SOURCE
    assert "recalculate_chart = False" in APP_SOURCE


def test_metadata_only_guard_tracks_birth_calculation_inputs():
    helper_start = APP_SOURCE.index("def _saved_chart_birth_inputs_match_form")
    helper_end = APP_SOURCE.index("def on_update_chart", helper_start)
    helper_source = APP_SOURCE[helper_start:helper_end]
    for token in (
        "placeholder_chart_checkbox",
        "_birth_date_from_fields",
        "retcon_time_checkbox",
        "_rectification_range_effective_from_inputs",
        "time_unknown_checkbox",
        "place_edit",
        "birthtime_unknown",
        "retcon_time_used",
        "rectification_range_start_minute",
        "rectification_range_end_minute",
    ):
        assert token in helper_source
