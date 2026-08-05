from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    start = APP_SOURCE.index(f"    def {name}(")
    next_start = APP_SOURCE.find("\n    def ", start + 1)
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_rectified_time_preview_only_queues_lightweight_sections():
    method = _method_source("_refresh_chart_preview")

    assert 'sections={"summary", "wheel"}' in method
    assert "refresh_time_sensitivity=False" in method
    assert "_mark_chart_analytics_sections_lucy_goosey()" in method
    assert "_suppress_right_panel_refresh_for_timing_preview = True" in method
    assert "chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)" not in method
    assert "chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)" not in method
    assert "chart.dominant_nakshatra_weights = _calculate_dominant_nakshatra_weights(chart)" not in method


def test_chart_render_can_skip_time_sensitivity_refresh_for_live_timing_preview():
    method = _method_source("_schedule_chart_render")

    assert "refresh_time_sensitivity: bool = True" in method
    assert "refresh_time_sensitivity" in method.split("time_sensitivity_panel.refresh_for_current_chart()", 1)[0]


def test_timing_preview_flush_keeps_live_chart_data_output_rebuild():
    method = _method_source("_flush_timing_preview_update")

    assert "_refresh_chart_preview()" in method
    assert "_reset_metric_canvases_for_retcon_timing_update" not in method


def test_timing_preview_completion_does_not_wake_right_panel_peripherals():
    method = _method_source("_flush_scheduled_chart_render")

    marker = "if not timing_preview_render:"
    assert "timing_preview_render = bool(" in method
    assert marker in method
    gated_block = method[method.index(marker):]
    assert "self._schedule_chart_render_for_active_right_panel()" in gated_block
    assert "self._schedule_passive_chart_analysis_preload_if_current" in gated_block


def test_chart_summary_does_not_wake_predictions_during_timing_preview():
    method = _method_source("_refresh_chart_summary")

    assert "_suppress_right_panel_refresh_for_timing_preview" in method
    assert "_suppress_right_panel_refresh_for_timing_preview = False" in method
    assert "else:" in method
    assert "_schedule_chart_render_for_active_right_panel()" in method
