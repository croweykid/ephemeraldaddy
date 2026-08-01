from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
LAYOUT_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py").read_text()
RIGHT_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()


def test_metric_canvas_width_uses_scroll_container_not_child_geometry():
    assert "viewport_width = scroll_area.viewport().width()" in LAYOUT_SOURCE
    assert "ancestor_width" not in LAYOUT_SOURCE
    assert "hidden ancestors" in LAYOUT_SOURCE


def test_prediction_finish_reschedules_all_metric_canvas_refreshes():
    method_start = RIGHT_PANEL_SOURCE.index("def _finish_background_prediction_render")
    method = RIGHT_PANEL_SOURCE[method_start : RIGHT_PANEL_SOURCE.index("def _retain_background_prediction_job", method_start)]

    assert "_request_all_metric_canvas_layouts" in method
    assert "_request_visible_metric_canvas_layouts" in method
    assert "request_metric_layouts()" in method
    assert "timer ladders" in method


def test_metric_canvas_refresh_defers_hidden_stacked_tabs():
    assert "def _request_all_metric_canvas_layouts" in APP_SOURCE
    assert "if not self._is_authoritative_geometry_visible(canvas):" in LAYOUT_SOURCE
    assert "self._dirty_canvases.add(canvas)" in LAYOUT_SOURCE
    assert "self._request_all_metric_canvas_layouts()" not in APP_SOURCE


def test_metric_chart_registration_tracks_scroll_area_and_viewport():
    register_start = APP_SOURCE.index("    def _register_metric_chart")
    register_source = APP_SOURCE[register_start : APP_SOURCE.index("    def _request_metric_canvas_layout", register_start)]

    assert "def _register_metric_chart_scroll_area" in register_source
    assert "scroll_area = self._metric_canvas_scroll_area(canvas)" in register_source
    assert "self._register_metric_scroll_widget(scroll_area)" in register_source
    assert "QTimer.singleShot(0" in register_source


def test_canvas_resize_events_do_not_fan_out_to_every_metric_canvas():
    event_filter_start = APP_SOURCE.index('metric_chart_titles = getattr(self, "_metric_chart_titles", {})')
    event_filter = APP_SOURCE[event_filter_start : APP_SOURCE.index("        if chart_canvas is not None and obj is chart_canvas", event_filter_start)]

    assert 'metric_chart_titles = getattr(self, "_metric_chart_titles", {})' in event_filter
    assert "if event.type() == QEvent.Resize and obj not in metric_chart_titles:" not in event_filter
    assert "resize -> redraw -> resize feedback loop" in event_filter
