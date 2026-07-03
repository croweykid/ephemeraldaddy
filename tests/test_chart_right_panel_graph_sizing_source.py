from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chart_view_right_panel_scroll_areas_disallow_horizontal_overflow():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py"
    ).read_text()

    assert "def _configure_chart_right_panel_scroll_area" in source
    assert "scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in source
    assert (
        "content_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)"
        in source
    )


def test_metric_graphs_get_deferred_width_refreshes_after_render():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "def _schedule_deferred_metric_canvas_layout_refresh" in source
    assert "delays_ms: tuple[int, ...] = (0, 50, 150, 300)" in source
    assert "self._schedule_deferred_metric_canvas_layout_refresh(canvas)" in source


def test_metric_canvas_width_clamps_to_live_scroll_area_during_retcon_rebuilds():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "scroll_area_width = scroll_area.width()" in source
    assert "viewport_width = min(viewport_width, scroll_area_width)" in source
    assert "stale viewport width" in source


def test_rectified_time_canvas_reset_invalidates_layouts_before_preview_rebuild():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _reset_metric_canvases_for_retcon_timing_update")
    method = source[method_start : source.index("    def _refresh_chart_preview", method_start)]

    assert "touched_layouts: list[QLayout] = []" in method
    assert "touched_layouts.append(layout)" in method
    assert "layout.invalidate()" in method
    assert "parent.adjustSize()" in method
    assert "self._schedule_deferred_visible_metric_canvas_layout_refreshes()" in method
