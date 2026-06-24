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
