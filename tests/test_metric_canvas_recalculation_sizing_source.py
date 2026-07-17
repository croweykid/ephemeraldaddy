from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
RIGHT_PANEL_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()


def test_metric_canvas_width_clamps_to_live_ancestor_geometry():
    method_start = APP_SOURCE.index("    def _metric_canvas_available_layout_width")
    method = APP_SOURCE[method_start : APP_SOURCE.index("    @staticmethod", method_start + 1)]

    assert "narrowest live ancestor width" in method
    assert "ancestor_width = ancestor.width()" in method
    assert "available_width = min(available_width, ancestor_width)" in method
    assert "if isinstance(ancestor, QScrollArea):" in method


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
