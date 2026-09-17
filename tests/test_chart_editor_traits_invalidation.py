from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_traits_invalidation_clears_presentation_and_pending_state_without_loading():
    source = (
        ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions_core.py"
    ).read_text(encoding="utf-8")
    helper = source.split("def invalidate_traits_prediction_view", 1)[1].split(
        "\ndef ", 1
    )[0]

    assert "owner._traits_prediction_render_token = object()" in helper
    assert 'owner._traits_prediction_last_render_chart_token = ""' in helper
    assert "_cancel_traits_prediction_worker_jobs(owner)" in helper
    assert '_set_traits_header_action(owner, "calculate")' in helper
    assert "_set_traits_prediction_rows(owner, [])" in helper
    assert "table.setVisible(False)" in helper
    assert 'label.setText("")' in helper
    assert "label.setVisible(False)" in helper
    assert 'owner._traits_prediction_above_avg_html = ""' in helper
    assert 'owner._traits_prediction_below_avg_html = ""' in helper
    assert "owner._traits_prediction_pending_chart = None" in helper
    assert "owner._traits_prediction_pending_traits = None" in helper
    assert "owner._traits_prediction_pending_signatures = None" in helper
    assert "owner._traits_prediction_pending_metadata = None" in helper
    assert 'owner._traits_prediction_pending_cache_key = ""' in helper
    assert 'owner._traits_prediction_pending_metadata_cache_key = ""' in helper
    assert "list_traits(" not in helper
    assert "trait_metadata_for_chart(" not in helper
    assert "calculate_trait_likelihoods(" not in helper


def test_chart_uid_change_invalidates_lazy_predictions_only_after_target_validation():
    app_source = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    load_body = app_source.split("    def load_chart_by_uid(", 1)[1].split(
        "    def ", 1
    )[0]

    invalidation = load_body.index("_invalidate_traits_prediction_view(self)")
    record_load = load_body.index("chart = load_chart_by_uid(normalized_chart_uid)")
    local_row_failure = load_body.index(
        'f"Could not resolve local row for chart UID {normalized_chart_uid}."'
    )
    adopt_chart = load_body.index("set_current_chart_by_uid(normalized_chart_uid)")

    assert record_load < local_row_failure < invalidation < adopt_chart


def test_themes_invalidation_is_installed_with_traits_and_remains_lazy():
    source = (
        ROOT / "ephemeraldaddy/gui/features/charts/theme_predictions.py"
    ).read_text(encoding="utf-8")
    helper = source.split("def invalidate_theme_prediction_view", 1)[1].split(
        "\ndef ", 1
    )[0]
    install = source.split("def install_theme_predictions", 1)[1]

    assert 'owner._theme_prediction_last_render_chart_token = ""' in helper
    assert "owner._themes_prediction_chart = None" in helper
    assert "model.set_rows([])" in helper
    assert "table.setVisible(False)" in helper
    assert '_set_theme_status(owner, "")' in helper
    assert "load_prediction_norms_snapshot(" not in helper
    assert "calculate_theme_subtheme_scores(" not in helper
    assert "calculate_theme_family_scores(" not in helper
    assert "original_invalidate(owner)" in install
    assert "invalidate_theme_prediction_view(owner)" in install
    assert (
        "trait_core.invalidate_traits_prediction_view = invalidate_traits_prediction_view"
        in install
    )
