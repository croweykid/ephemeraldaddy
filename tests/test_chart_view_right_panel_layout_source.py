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


def test_predictions_panel_keeps_dnd_summary_outside_metric_canvas_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
    builder_start = source.index("def _build_predictions_panel")
    builder = source[builder_start : source.index("def build_chart_view_right_panel", builder_start)]

    assert "dnd_section_layout.addWidget(owner.dnd_predictions_chart_panel)" in builder
    assert "owner.dnd_prediction_top_three_label = QLabel" in builder
    assert "dnd_section_layout.addWidget(owner.dnd_prediction_top_three_label)" in builder

    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = app_source.index("    def _render_dndification_predictions")
    method = app_source[
        method_start : app_source.index("    def _normalize_aspect_type", method_start)
    ]

    assert "chart_layout.addWidget(summary_label)" not in method
    assert "section_layout.addWidget(summary_label)" in method


def test_dnd_prediction_statblock_uses_chart_analytics_vertical_bar_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    function = source[
        source.index("def draw_dnd_statblock_predictions") : source.index(
            "def draw_dnd_species_predictions"
        )
    ]

    assert "ax.bar(labels, values)" in function
    assert "ax.barh(labels, values)" not in source
    assert "apply_standard_bar_axes(ax, labels)" in function
    assert "ax.figure.subplots_adjust(left=0.18, bottom=0.20, top=0.92, right=0.96)" in function
