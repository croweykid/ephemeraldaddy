from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chart_analytics_layout_allows_canvases_to_fill_scroll_viewport():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "owner.metrics_layout.setAlignment(Qt.AlignTop)" in source
    assert "owner.metrics_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" not in source


def test_metric_canvas_sizing_uses_expanding_width_not_ignored_zero_width():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "canvas.setMinimumWidth(1)" in source
    assert "canvas.setMaximumWidth(viewport_width)" in source
    assert "canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)" in source
    assert "canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)" not in source


def test_dnd_prediction_summary_is_added_after_metric_panel_render_clears_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _render_dndification_predictions")
    method = source[
        method_start : source.index("    def _normalize_aspect_type", method_start)
    ]

    first_render = method.index("self._render_metric_panel(")
    first_add = method.index("chart_layout.addWidget(summary_label)")

    assert first_render < first_add


def test_dnd_prediction_statblock_uses_horizontal_axis_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    function = source[
        source.index("def draw_dnd_statblock_predictions") : source.index(
            "def draw_dnd_species_predictions"
        )
    ]

    assert "ax.barh(labels, values)" in function
    assert "_ = apply_standard_bar_axes" in function
    assert "apply_standard_bar_axes(ax, labels)" not in function
    assert "ax.figure.subplots_adjust(left=0.16" in function
