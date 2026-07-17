from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
RIGHT_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()


def test_metric_canvas_width_uses_scroll_container_not_child_geometry():
    viewport_method_start = APP_SOURCE.index("    def _metric_canvas_scroll_viewport_width")
    viewport_method = APP_SOURCE[viewport_method_start : APP_SOURCE.index("    @staticmethod", viewport_method_start + 1)]
    available_method_start = APP_SOURCE.index("    def _metric_canvas_available_layout_width")
    available_method = APP_SOURCE[available_method_start : APP_SOURCE.index("    @staticmethod", available_method_start + 1)]

    assert "ancestors outside the" in viewport_method
    assert "if scroll_area.isVisible():" in viewport_method
    assert "candidate_widths.extend([scroll_area.viewport().width(), scroll_area.width()])" in viewport_method
    assert "ancestor = scroll_area.parentWidget()" in viewport_method
    assert "candidate_widths.append(ancestor_width)" in viewport_method
    assert "do not clamp against" in available_method
    assert "scroll-content child widgets" in available_method
    assert "ancestor = parent" not in available_method


def test_prediction_finish_reschedules_all_metric_canvas_refreshes():
    method_start = RIGHT_PANEL_SOURCE.index("def _finish_background_prediction_render")
    method = RIGHT_PANEL_SOURCE[method_start : RIGHT_PANEL_SOURCE.index("def _retain_background_prediction_job", method_start)]

    assert "_schedule_deferred_all_metric_canvas_layout_refreshes" in method
    assert "_schedule_deferred_visible_metric_canvas_layout_refreshes" in method
    assert "schedule_metric_refreshes((0, 25, 75, 150, 300, 600))" in method


def test_metric_canvas_refresh_can_target_hidden_stacked_tabs():
    assert "def _schedule_all_metric_canvas_layout_refreshes" in APP_SOURCE
    assert "Resize every registered right-panel metric canvas" in APP_SOURCE
    assert "self._schedule_all_metric_canvas_layout_refreshes()" in APP_SOURCE


def test_canvas_resize_events_do_not_fan_out_to_every_metric_canvas():
    event_filter_start = APP_SOURCE.index('metric_chart_titles = getattr(self, "_metric_chart_titles", {})')
    event_filter = APP_SOURCE[event_filter_start : APP_SOURCE.index("        if chart_canvas is not None and obj is chart_canvas", event_filter_start)]

    assert 'metric_chart_titles = getattr(self, "_metric_chart_titles", {})' in event_filter
    assert "if event.type() == QEvent.Resize and obj not in metric_chart_titles:" in event_filter
