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


def test_metric_graphs_delegate_to_single_viewport_layout_owner():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    controller = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py"
    ).read_text()

    assert "MetricCanvasLayoutController(" in source
    assert "viewport_width = scroll_area.viewport().width()" in controller
    assert "ancestor_width" not in controller
    assert "_horizontal_insets_to_viewport" in controller
    assert "delays_ms: tuple[int, ...] = (0, 50, 150, 300)" not in source


def test_tab_switch_reasserts_visible_canvas_layout_without_rerendering():
    source = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/chart_editor/right_panel_controller.py"
    ).read_text()
    method_start = source.index("    def set_active_panel(")
    method = source[
        method_start : source.index("    def set_section_visible(", method_start)
    ]

    assert "QTimer.singleShot(0, self._request_visible_canvas_layouts)" in method
    assert 'getattr(self._owner, "_request_visible_metric_canvas_layouts"' not in source


def test_canvas_layout_dependency_is_explicit_and_chart_editor_owned():
    controller = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/chart_editor/right_panel_controller.py"
    ).read_text()
    builder = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()
    legacy_stack = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py"
    ).read_text()

    assert "request_visible_canvas_layouts: Callable[[], None]" in controller
    assert "self._request_visible_canvas_layouts = request_visible_canvas_layouts" in controller
    assert (
        "request_visible_canvas_layouts=owner._request_visible_metric_canvas_layouts"
        in builder
    )
    legacy_navigation = legacy_stack[
        legacy_stack.index("def set_chart_right_panel(") : legacy_stack.index(
            "def _predictions_panel_render_is_current"
        )
    ]
    assert 'getattr(owner, "_request_visible_metric_canvas_layouts"' not in legacy_navigation


def test_hidden_metric_canvas_width_is_not_guessed_from_stale_geometry():
    source = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py"
    ).read_text()

    assert "if not self._is_authoritative_geometry_visible(canvas):" in source
    assert "self._dirty_canvases.add(canvas)" in source
    assert "visible viewport resize event" in source
    assert "event.type() == QEvent.Show" in source
    assert "and watched in self._scroll_by_canvas" in source
    assert "event.type() == QEvent.Resize\n            and isinstance(watched, FigureCanvas)" not in source


def test_rectified_time_canvas_reset_invalidates_layouts_before_preview_rebuild():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _reset_metric_canvases_for_retcon_timing_update")
    method = source[method_start : source.index("    def _refresh_chart_preview", method_start)]

    assert "touched_layouts: list[QLayout] = []" in method
    assert "touched_layouts.append(layout)" in method
    assert "layout.invalidate()" in method
    assert "parent.adjustSize()" in method
    assert "self._request_visible_metric_canvas_layouts()" in method
