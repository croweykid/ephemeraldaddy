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


def test_chart_uid_change_invalidates_traits_before_cached_navigation_branch():
    app_source = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    load_body = app_source.split("    def load_chart_by_uid(", 1)[1].split(
        "    def ", 1
    )[0]

    different_chart_check = load_body.index("if not is_same_chart_request:")
    invalidation = load_body.index("_invalidate_traits_prediction_view(self)")
    cached_lookup = load_body.index("cached_chart =")
    clear_displays = load_body.index("self._clear_chart_displays()")

    assert different_chart_check < invalidation < cached_lookup < clear_displays
