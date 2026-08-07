from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def _function_source(source: str, name: str) -> str:
    marker = f"def {name}"
    start = source.index(marker)
    next_start = source.find("\ndef ", start + len(marker))
    return source[start:] if next_start == -1 else source[start:next_start]


def test_chart_analytics_layout_allows_canvases_to_fill_scroll_viewport():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "owner.metrics_layout.setAlignment(Qt.AlignTop)" in source
    assert "owner.metrics_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)" not in source


def test_metric_canvas_sizing_uses_expanding_width_not_ignored_zero_width():
    source = _source("ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py")

    assert "canvas.setMinimumWidth(available_width)" in source
    assert "canvas.setMaximumWidth(available_width)" in source
    assert "canvas.resize(available_width, display_height)" in source
    assert "canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)" in source
    assert "ancestor_width" not in _function_source(source, "apply_now")


def test_metric_canvas_width_subtracts_scroll_content_margins():
    source = _source("ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py")

    assert "viewport_width = scroll_area.viewport().width()" in source
    assert "margins = layout.contentsMargins()" in source
    assert "while widget is not None:" in source
    assert "total += margins.left() + margins.right()" in source


def test_prediction_graph_sections_use_extra_axis_label_height():
    enneagram_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text()
    dnd_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()

    assert "ENNEAGRAM_PREDICTION_GRAPH_HEIGHT_PX = ENNEAGRAM_PREDICTION_GRAPH_BASE_HEIGHT_PX + 10" in enneagram_source
    assert "display_height=ENNEAGRAM_PREDICTION_GRAPH_HEIGHT_PX" in enneagram_source
    assert "DND_ALIGNMENT_GRAPH_HEIGHT_PX = DND_ALIGNMENT_GRAPH_BASE_HEIGHT_PX + 6" in dnd_source
    assert "display_height=DND_ALIGNMENT_GRAPH_HEIGHT_PX" in dnd_source


def test_dnd_prediction_summary_is_added_after_metric_panel_render_clears_layout():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _render_dndification_predictions")
    method = source[
        method_start : source.index("    def _normalize_aspect_type", method_start)
    ]

    render_call = method.index("self._dnd_prediction_adapter().render(chart, self._render_metric_panel)")
    summary_assign = method.index("self.dnd_prediction_top_three_label = summary_label")

    assert render_call < summary_assign


def test_chart_right_panel_controller_delegates_predictions_to_background_scheduler():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/chart_editor/right_panel_controller.py").read_text()
    branch_start = source.index('        if active_panel == "predictions":')
    branch = source[
        branch_start : source.index('        if active_panel in {"abc", "anagrams"}', branch_start)
    ]

    assert "schedule_chart_render_for_active_right_panel(self._owner)" in branch
    assert "_render_enneagram_predictions" not in branch
    assert "_render_dndification_predictions" not in branch


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
    controller = _source("ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py")

    assert "def _request_metric_canvas_layout" in source
    assert "self._metric_canvas_layout_controller.request(canvas)" in source
    assert "QTimer.singleShot(0, self._flush)" in controller
    assert "QTimer.singleShot(50" not in controller


def test_metric_scroll_viewport_resize_refreshes_existing_canvases():
    source = _source("ephemeraldaddy/gui/features/chart_editor/metric_canvas_layout.py")

    assert "event.type() in (QEvent.Resize, QEvent.Show)" in source
    assert "watched is scroll_area.viewport()" in source
    assert "self.request(canvas)" in source


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



def test_settings_collapsible_headers_match_appwide_style_centered():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    style_source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert "SETTINGS_COLLAPSIBLE_TOGGLE_STYLE = DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE" in style_source
    settings_method = source[source.index("    def _add_settings_collapsible_section") : source.index("    def _add_settings_action_section")]
    assert "style_sheet=SETTINGS_COLLAPSIBLE_TOGGLE_STYLE" in settings_method
    assert "title_alignment=Qt.AlignCenter" in settings_method
    assert "QToolButton:hover" in style_source
    assert "padding: 6px; text-align: left;" in style_source

def test_property_managers_button_sits_below_settings_sections_with_padding():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _ensure_settings_dialog")
    method = source[method_start : source.index("    def _set_lilith_calculation_method", method_start)]

    data_visualization_index = method.index('"Data Visualization"')
    developer_tools_index = method.index('"Developer Tools"')
    database_stats_index = method.index("add_database_info_settings_section(self, content_layout)")
    similar_charts_index = method.index('"Astro Twin Calculator"')
    predictions_index = method.index('"Predictions"')
    user_profile_index = method.index('"User Profile"')
    reset_index = method.index('"Reset All to Defaults"')
    property_manager_index = method.index('"Property Manager"')
    stretch_index = method.index("content_layout.addStretch(1)")

    assert data_visualization_index < developer_tools_index < database_stats_index
    assert database_stats_index < similar_charts_index < predictions_index < user_profile_index < reset_index
    assert reset_index < property_manager_index < stretch_index
    assert "Property Manager" in method
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

    assert "scroll_area.setAlignment(Qt.AlignLeft | Qt.AlignTop)" in source


def test_predictions_refresh_uses_token_gated_right_panel_scheduler():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _refresh_chart_summary")
    method = source[method_start : source.index("    def _build_chart_export_markdown", method_start)]

    assert "self._schedule_chart_render_for_active_right_panel()" in method
    assert "self._render_enneagram_predictions(chart)" not in method
    assert "self._render_dndification_predictions(chart)" not in method


def test_predictions_scheduler_queues_expanded_gender_guesser_graph():
    source = _source("ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py")
    scheduler = _function_source(source, "schedule_chart_render_for_active_right_panel")
    content_check = _function_source(source, "_predictions_panel_has_rendered_content")

    assert '"gender_guesser_canvas"' in content_check
    assert 'is_chart_analytics_section_renderable("gender")' in scheduler
    assert 'sections={"gender"}' in scheduler


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


def test_photo_gallery_preview_is_full_screen():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "dialog.showFullScreen()" in source
    assert "_PhotoPreviewDialog" in source


def test_photo_gallery_max_storage_dimensions_are_1920_by_1080():
    source = (REPO_ROOT / "ephemeraldaddy/core/photo_gallery.py").read_text()
    panel_source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "MAX_PHOTO_WIDTH = 1920" in source
    assert "MAX_PHOTO_HEIGHT = 1080" in source
    assert "image.thumbnail((MAX_PHOTO_WIDTH, MAX_PHOTO_HEIGHT), Image.Resampling.LANCZOS)" in source
    assert "MAX_PHOTO_DIMENSION = 600" not in source
    assert "maximum dimensions of 1920×1080 px" in panel_source


def test_dnd_alignment_popout_is_registered_and_configured():
    registry_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/metric_popout_registry.py").read_text()
    dnd_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'key="dnd_alignment"' in registry_source
    assert 'title="Fantasy RPG Alignment"' in registry_source
    assert '_draw_dnd_alignment_predictions' in registry_source
    assert 'connect_dnd_alignment_popout_pick_handler' in registry_source
    assert 'def _draw_dnd_alignment_predictions' in app_source
    assert 'def _build_dnd_alignment_popout_info' in app_source
    assert 'build_dnd_alignment_breakdown_html' in dnd_source
    assert 'build_dnd_alignment_description_html' in dnd_source
    assert 'point.set_gid(f"dnd_alignment:{alignment_key}")' in dnd_source
    assert 'font-style:italic' in dnd_source
    assert 'def resolve_dnd_official_alignment' in dnd_source
    assert 'Official Fantasy RPG alignment:' in dnd_source
    assert 'return "True Neutral"' in dnd_source


def test_predictions_background_warmup_updates_loading_progress():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert "progress = Signal(str, int)" in source
    assert "create_app_loading_progress(" in source
    assert "worker.progress.connect(receiver.handle_progress, Qt.QueuedConnection)" in source
    assert "update_app_loading_progress(progress, message, percent)" in source
    assert "close_app_loading_progress(progress)" in source


def test_predictions_sections_show_calculate_prompt_instead_of_auto_calculating():
    enneagram_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text()
    dnd_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text()
    stack_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()
    controller_source = (REPO_ROOT / "ephemeraldaddy/gui/features/chart_editor/right_panel_controller.py").read_text()
    view_source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
    loading_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/prediction_loading_labels.py").read_text()
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "No prior data. Calculate (can take awhile)?" in enneagram_source
    assert "No prior data. Calculate (can take awhile)?" in dnd_source
    assert 'QPushButton("Calculate!")' in enneagram_source
    assert 'QPushButton("Calculate!")' in dnd_source
    active_branch = stack_source[
        stack_source.index('    if active_panel == "predictions":') : stack_source.index('    if active_panel == "abc"')
    ]
    assert "_start_background_prediction_render(owner, chart, render_token)" not in active_branch
    assert "owner._render_enneagram_predictions(chart)" in active_branch
    assert "owner._render_dndification_predictions(chart)" in active_branch
    assert "def _predictions_panel_has_rendered_content" in stack_source
    assert "Loading trait predictions" in stack_source  #for this UID
    assert "No traits uploaded. Add traits in Settings > Traits." not in stack_source
    assert "and _predictions_panel_has_rendered_content(owner)" in stack_source
    assert "and _predictions_panel_has_rendered_content(self._owner)" in controller_source
    assert "render_traits(chart)" in stack_source
    assert "sections: set[str] | None = None" in stack_source
    assert "self._sections = set(sections or" in stack_source
    assert "if \"dnd_statblock\" in self._sections" in stack_source
    assert "if \"dnd_alignment\" in self._sections" in stack_source
    assert "calculate_callback(chart, \"enneagram\")" in enneagram_source
    assert "calculate_callback(chart, section)" in dnd_source
    assert 'reset_canvas_callback("enneagram_prediction_canvas")' in enneagram_source
    assert "reset_canvas_callback(canvas_attr)" in dnd_source
    assert "def _dnd_alignment_cache_key" in dnd_source
    assert 'cached.get("key") == cache_key' in dnd_source
    assert "_prediction_norms_render_token" in dnd_source
    assert "def _stable_traits_metadata_hash" in app_source
    assert "self._stable_traits_metadata_hash(payload)" in app_source
    assert "start_prediction_loading_blink(label)" in view_source
    assert "def stop_prediction_loading_blink" in loading_source
    assert "if \"Loading\" not in label_text:" in loading_source
    assert "stop_prediction_loading_blink(self.tritype_label)" in enneagram_source
    assert "stop_prediction_loading_blink(label)" in dnd_source


def test_predictions_timeout_does_not_terminate_qthread_from_gui_thread():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()
    assert "Predictions warmup did not stop after timeout; leaving worker in background" in source
    assert "retaining references and not terminating from GUI thread" in source
    assert "owner._predictions_background_jobs[:] = retained_jobs" in source
    assert "thread.terminate()" not in source


def test_traits_predictions_default_to_manual_recalculation_with_cached_stale_display():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text()
    assert "No prior data. Calculate (can take awhile)?" in source
    assert "trait-predictions:calculate" in source
    assert "cached_only: bool = False" in source
    assert "trait_metadata_for_chart(owner, chart, cached_only=True)" in source
    assert '"trait_display_signature": trait_display_signature' in source
    assert "_traits_recalculate_prompt_html" in source
    assert "Cached trait predictions shown" in source
    assert "_trait_predictions_refresh_message(str(cached.get" not in source
    no_cache_branch = source[source.index("owner._traits_prediction_pending_chart = chart"):]
    assert "if _predictions_manual_recalculation_only(owner):" in no_cache_branch
    assert "_traits_calculate_prompt_html()" in no_cache_branch
    assert "Loading fresh trait predictions" in no_cache_branch  #for this UID
    assert "start_prediction_loading_blink(label)" in no_cache_branch
    assert "QTimer.singleShot(0, lambda owner=owner: _start_traits_prediction_calculation(owner))" in no_cache_branch
    assert "_start_traits_prediction_refresh_worker(owner, chart, traits" not in no_cache_branch
    assert '"positions": getattr(chart, "positions", None)' not in source
    assert '"aspects": getattr(chart, "aspects", None)' not in source
    assert 'scoring_payload["houses"] = getattr(chart, "houses", None)' not in source
    assert '"rectification_range_used": bool(getattr(chart, "rectification_range_used", False))' in source




def test_traits_prediction_prompt_label_is_reshown_after_table_results():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text()
    apply_view = source.split("def _apply_traits_prediction_view", 1)[1].split("def _apply_traits_prediction_metadata", 1)[0]

    assert "label.setVisible(True)" in apply_view
    assert "A later chart may have no cached metadata yet" in apply_view

def test_predictions_panel_rerenders_traits_for_each_chart_even_when_content_exists():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()
    predictions_branch = source.split('if active_panel == "predictions":', 1)[1].split('if active_panel == "abc"', 1)[0]

    assert 'traits_render_token = str(getattr(owner, "_traits_prediction_last_render_chart_token", "") or "")' in predictions_branch
    assert 'traits_ready_for_chart = traits_ready and traits_render_token == render_token' in predictions_branch
    assert 'and traits_ready_for_chart' in predictions_branch
    assert 'and traits_ready\n' not in predictions_branch
    assert 'render_traits = getattr(owner, "_render_traits_predictions", None)' in predictions_branch
    assert 'if callable(render_traits):\n            render_traits(chart)' in predictions_branch
    assert 'setattr(owner, "_traits_prediction_last_render_chart_token", render_token)' in predictions_branch
    assert 'if callable(render_traits) and not traits_ready' not in predictions_branch
    assert predictions_branch.index('render_traits(chart)') < predictions_branch.index('owner._render_enneagram_predictions(chart)')


def test_prediction_calculate_prompts_expand_and_center_contents():
    for relative_path in (
        "ephemeraldaddy/gui/features/charts/dnd_predictions.py",
        "ephemeraldaddy/gui/features/charts/enneagram_predictions.py",
    ):
        source = (REPO_ROOT / relative_path).read_text()
        assert "QSizePolicy.Expanding, QSizePolicy.MinimumExpanding" in source
        assert "label.setMinimumHeight(label.sizeHint().height())" in source
        assert "panel_layout.setAlignment(Qt.AlignCenter)" in source
        assert ".addWidget(panel)" in source
    traits_source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text()
    assert "min-height:120px" in traits_source
    assert "text-align:center" in traits_source
    assert "white-space:normal" in traits_source


def test_right_panel_expand_autoscroll_ignores_plain_checkboxes():
    source = _source("ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py")
    method = _function_source(source, "_install_expand_autoscroll")
    assert "findChildren(QToolButton)" in method
    assert "findChildren(QAbstractButton)" not in method
    assert 'property("collapsible_header_autoscroll_installed")' in method


def test_subjective_notes_does_not_schedule_anagrams():
    source = _source("ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py")
    method = _function_source(source, "schedule_chart_render_for_active_right_panel")
    assert 'active_panel == "abc"' in method
    assert 'active_panel in {"subjective_notes", "abc"}' not in method
