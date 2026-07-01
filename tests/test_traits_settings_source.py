from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_traits_settings_ui_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )

    assert "add_traits_settings_section(self, content_layout)" in app_source
    assert "def _on_trait_upload_clicked" not in app_source
    assert "def add_traits_settings_section" in settings_source
    assert "def on_trait_upload_clicked" in settings_source
    assert "Edit JSON…" in settings_source
    assert "def on_trait_edit_clicked" in settings_source
    assert "parse_trait_file(temp_path)" in settings_source
    assert "_mark_trait_definitions_changed(owner)" in settings_source
    assert "clear_likelihoods=False" in settings_source
    assert "_warm_trait_definitions(owner, {clean_name})" in settings_source


def test_trait_prediction_rendering_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")

    assert "def _render_traits_predictions" in app_source
    assert "_render_traits_predictions(self, chart)" in app_source
    assert "def render_traits_predictions" in predictions_source
    assert "calculate_trait_scores" in predictions_source
    assert "TRAIT_DB_NORMS_CACHE_PATH" in predictions_source
    assert "def warm_trait_database_norms" in predictions_source
    assert "def clear_trait_norm_cache" in predictions_source
    assert "_load_trait_norm_cache()" in predictions_source


def test_prediction_norm_rows_use_full_database_not_displayed_filter_scope():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    method = app_source[
        app_source.index("    def _prediction_norm_rows")
        : app_source.index("    def _prediction_norms_render_token")
    ]

    assert 'chart_rows = getattr(self, "_chart_rows", None)' in method
    assert 'getattr(manage_dialog, "_chart_rows", None)' in method
    assert "_displayed_chart_rows_by_id" not in method


def test_database_view_traits_search_lives_in_search_panel_and_uses_metadata():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    search_source = (ROOT / "ephemeraldaddy" / "gui" / "dbv_search_panel.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")

    assert 'add_collapsible_section("🧬Traits")' in search_source
    assert "def collect_search_trait_filter_sets" in search_source
    assert "def chart_matches_trait_filters" in search_source
    assert "collect_search_trait_filter_sets(self)" in app_source
    assert "chart_matches_trait_filters(" in app_source
    assert "def trait_metadata_for_chart" in predictions_source
    assert "predicted_traits_above_avg" in predictions_source
    assert "predicted_traits_below_avg" in predictions_source
