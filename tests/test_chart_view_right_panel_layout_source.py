from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chart_analytics_layout_allows_canvases_to_fill_scroll_viewport():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "owner.metrics_layout.setAlignment(Qt.AlignTop)" in source
    assert "owner.metrics_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" not in source


def test_metric_canvas_sizing_uses_expanding_width_not_ignored_zero_width():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "canvas.setMinimumWidth(1)" in source
    assert "available_width = MainWindow._metric_canvas_available_layout_width(canvas)" in source
    assert "CHART_RIGHT_PANEL_GRAPH_HEIGHT_PX = 240" in source
    assert "canvas.setMinimumWidth(available_width)" in source
    assert "canvas.setMaximumWidth(available_width)" in source
    assert "canvas.resize(available_width, current_height)" in source
    assert "canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)" in source
    assert "canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)" not in source


def test_metric_canvas_width_subtracts_scroll_content_margins():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "def _metric_canvas_available_layout_width" in source
    assert "viewport_width = MainWindow._metric_canvas_scroll_viewport_width(canvas)" in source
    assert "margins = parent_layout.contentsMargins()" in source
    assert "available_width -= margins.left() + margins.right()" in source


def test_dnd_prediction_summary_is_added_after_metric_panel_render_clears_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _render_dndification_predictions")
    method = source[
        method_start : source.index("    def _normalize_aspect_type", method_start)
    ]

    first_render = method.index("self._render_metric_panel(")
    first_add = method.index("chart_layout.addWidget(summary_label)")

    assert first_render < first_add


def test_dnd_prediction_statblock_uses_standard_vertical_axis_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    function = source[
        source.index("def draw_dnd_statblock_predictions") : source.index(
            "def draw_dnd_species_predictions"
        )
    ]

    assert "ax.bar(labels, values)" in function
    assert "_style_prediction_bar_chart(" in function
    assert "ax.barh(labels, values)" not in function
    assert "_ = apply_standard_bar_axes" not in function


def test_dnd_stat_popout_evidence_imports_stat_predictors():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    import_block = source[
        source.index("from ephemeraldaddy.analysis.dnd.dnd_definitions import (") : source.index(
            "from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import ("
        )
    ]
    evidence_function = source[
        source.index("def _build_dnd_stat_evidence_html") : source.index(
            "def build_dnd_statblock_popout_info_html"
        )
    ]

    assert "DND_STAT_PREDICTORS" in import_block
    assert "DND_STAT_PREDICTORS.get(stat_key, {})" in evidence_function


def test_prediction_metric_canvases_redraw_after_stacked_panel_layout_settles():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "def _schedule_metric_canvas_layout_refresh" in source
    assert "_pending_metric_canvas_layout_refreshes" in source
    assert "QTimer.singleShot(0, _refresh_once)" in source
    assert "QTimer.singleShot(50" not in source
    assert "self._schedule_metric_canvas_layout_refresh(canvas)" in source


def test_metric_scroll_viewport_resize_refreshes_existing_canvases():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "def _schedule_visible_metric_canvas_layout_refreshes" in source
    assert "if event.type() == QEvent.Resize:" in source
    assert "self._schedule_visible_metric_canvas_layout_refreshes()" in source


def test_clear_chart_displays_resets_dnd_prediction_canvas_and_summary():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _clear_chart_displays")
    method = source[method_start : source.index("    def _render_sign_tally", method_start)]

    assert "self.dnd_predictions_chart_layout" in method
    assert "self.dnd_prediction_statblock_canvas = None" in method
    assert "self.dnd_prediction_top_three_label = None" in method


def test_settings_dialog_section_labels_wrap_to_available_width():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "def _configure_settings_section_text_wrap" in source
    assert "label.setWordWrap(True)" in source
    assert "label.setMinimumWidth(0)" in source
    assert "label.setMinimumHeight(0)" in source
    assert "label.setMaximumHeight(16777215)" in source
    assert "label.setAlignment(label.alignment() | Qt.AlignTop)" in source
    assert "label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)" in source
    assert "label.updateGeometry()" in source
    assert "self._configure_settings_section_text_wrap(content)" in source


def test_property_managers_button_sits_below_settings_sections_with_padding():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _ensure_settings_dialog")
    method = source[method_start : source.index("    def _set_lilith_calculation_method", method_start)]

    data_visualization_index = method.index('"Data Visualization"')
    developer_tools_index = method.index('"Developer Tools"')
    database_stats_index = method.index("add_database_info_settings_section(self, content_layout)")
    similar_charts_index = method.index('"Similar Charts Calculator"')
    enneagram_index = method.index('"Enneagram Predictor"')
    user_profile_index = method.index('"User Profile"')
    reset_index = method.index('"Reset All to Defaults"')
    property_managers_index = method.index('"Property Managers"')
    stretch_index = method.index("content_layout.addStretch(1)")

    assert data_visualization_index < developer_tools_index < database_stats_index
    assert database_stats_index < similar_charts_index < enneagram_index < user_profile_index < reset_index
    assert reset_index < property_managers_index < stretch_index
    assert "top_spacing=18" in method
    assert "parent_layout.addSpacing(top_spacing)" in source
    assert "button = QPushButton(title)" in source
    assert "button = QToolButton()" not in source[
        source.index("    def _add_settings_action_section") : source.index("    def _build_settings_subheader_label")
    ]


def test_prediction_panel_graph_layouts_are_left_aligned():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source
    assert "owner.enneagram_prediction_chart_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source
    assert "owner.dnd_predictions_chart_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source


def test_right_panel_scroll_areas_pin_content_to_left_edge():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert "analytics_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source
    assert "predictions_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source
    assert "subjective_notes_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source


def test_predictions_refresh_uses_token_gated_right_panel_scheduler():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _refresh_chart_summary")
    method = source[method_start : source.index("    def _build_chart_export_markdown", method_start)]

    assert "self._schedule_chart_render_for_active_right_panel()" in method
    assert "self._render_enneagram_predictions(chart)" not in method
    assert "self._render_dndification_predictions(chart)" not in method


def test_saved_chart_metadata_updates_do_not_dirty_right_panel_sections():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    save_start = source.index("    def on_update_chart")
    save_method = source[save_start : source.index("    def _reset_new_chart_form", save_start)]

    assert "previous_recalculation_token =" in save_method
    assert "new_recalculation_token = self._chart_analytics_cache_token(chart)" in save_method
    assert "chart_recalculated = bool(" in save_method
    dirty_index = save_method.index("self._mark_chart_analytics_sections_lucy_goosey()")
    recalculated_index = save_method.index("if chart_recalculated:")
    assert recalculated_index < dirty_index


def test_batch_metadata_refresh_does_not_dirty_right_panel_sections():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _refresh_filters_after_batch_edit")
    method = source[method_start : source.index("        def _refresh_and_restore_selection", method_start)]

    assert "sections={\"summary\"}" in method
    assert "_mark_chart_analytics_sections_lucy_goosey" not in method

def test_photo_gallery_button_activates_photo_gallery_panel():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert "photo_gallery_button.clicked.connect(on_show_photo_gallery)" in source
    assert "photo_gallery_button.clicked.connect(lambda: None)" not in source


def test_photo_gallery_preview_is_full_screen_without_upscaling_small_images():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "dialog.showFullScreen()" in source
    assert "if pixmap.width() > max_width or pixmap.height() > max_height:" in source
    assert (
        "display_pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)"
        in source
    )
    assert "display_pixmap = pixmap" in source
    assert "pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)" in source


def test_photo_gallery_max_storage_dimensions_are_1920_by_1080():
    source = (REPO_ROOT / "ephemeraldaddy/core/photo_gallery.py").read_text()
    panel_source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "MAX_PHOTO_WIDTH = 1920" in source
    assert "MAX_PHOTO_HEIGHT = 1080" in source
    assert "image.thumbnail((MAX_PHOTO_WIDTH, MAX_PHOTO_HEIGHT), Image.Resampling.LANCZOS)" in source
    assert "MAX_PHOTO_DIMENSION = 600" not in source
    assert "maximum dimensions of 1920×1080 px" in panel_source
