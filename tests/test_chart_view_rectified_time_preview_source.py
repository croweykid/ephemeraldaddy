from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()
RIGHT_PANEL_CONTROLLER_SOURCE = Path(
    "ephemeraldaddy/gui/features/controllers/chart_right_panel.py"
).read_text()
RIGHT_PANEL_STACK_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py"
).read_text()


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


def test_timing_preview_completion_refreshes_only_visible_analytics():
    method = _method_source("_flush_scheduled_chart_render")

    marker = 'if timing_preview_render and active_right_tab == "analytics":'
    assert "timing_preview_render = bool(" in method
    assert marker in method
    timing_block, normal_block = method[method.index(marker):].split(
        "elif not timing_preview_render:", 1
    )
    assert "self._schedule_chart_render_for_active_right_panel(chart)" in timing_block
    assert "self._schedule_passive_chart_analysis_preload_if_current" not in timing_block
    assert "self._schedule_passive_chart_analysis_preload_if_current" in normal_block


def test_chart_summary_does_not_wake_predictions_during_timing_preview():
    method = _method_source("_refresh_chart_summary")

    assert "_suppress_right_panel_refresh_for_timing_preview" in method
    assert "and not bool(" in method
    assert "_schedule_chart_render_for_active_right_panel()" in method


def test_timing_edit_switches_open_predictions_panel_to_analytics():
    method = _method_source("_queue_timing_preview_update")

    assert 'getattr(state, "active_tab", None) == "predictions"' in method
    assert 'self._set_chart_right_panel("analytics", schedule_render=False)' in method
    assert method.index('getattr(state, "active_tab", None) == "predictions"') < method.index('self._timing_preview_update_timer.start')


def test_forced_analytics_switch_can_defer_render_until_preview_finishes():
    assert "schedule_render: bool = True" in RIGHT_PANEL_CONTROLLER_SOURCE
    assert "if not schedule_render:" in RIGHT_PANEL_CONTROLLER_SOURCE
    assert "schedule_render: bool = True" in RIGHT_PANEL_STACK_SOURCE
    assert "if schedule_render\n        else None" in RIGHT_PANEL_STACK_SOURCE
    assert "self.schedule_render(chart=chart)" in RIGHT_PANEL_CONTROLLER_SOURCE
