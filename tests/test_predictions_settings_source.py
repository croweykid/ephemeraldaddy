from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text()


def test_predictions_settings_section_uses_module_wide_language():
    assert 'self._add_settings_collapsible_section(content_layout, "Predictions")' in APP_SOURCE
    assert 'label = QLabel("Predictions")' in DEV_TOOLS_SOURCE
    assert "Configure how Predictions criteria are scored" in DEV_TOOLS_SOURCE
    assert "build_predictions_settings_section" in DEV_TOOLS_SOURCE


def test_predictions_settings_expose_dominance_normalization_mode():
    assert "on_score_mode_changed" in DEV_TOOLS_SOURCE
    assert "score_mode_combo" in DEV_TOOLS_SOURCE
    assert '("background_z", "background z-score")' in DEV_TOOLS_SOURCE
    assert '("category_z", "category z-score")' in DEV_TOOLS_SOURCE
    assert "use_mutual_exclusive_bucket_scoring" in DEV_TOOLS_SOURCE
    assert "on_dominance_normalization_mode_changed" in DEV_TOOLS_SOURCE
    assert 'dominance_combo.addItem(title, value)' in DEV_TOOLS_SOURCE
    assert '("range", "range")' in DEV_TOOLS_SOURCE
    assert '("share", "share")' in DEV_TOOLS_SOURCE
    assert 'self._prediction_dominance_normalization_combo = enneagram_controls["dominance_combo"]' in APP_SOURCE
    assert "normalized_dominance_normalization_mode()" in APP_SOURCE
    assert 'self._prediction_score_mode_combo = enneagram_controls["score_mode_combo"]' in APP_SOURCE
    assert "normalized_score_mode()" in APP_SOURCE
    assert 'payload["score_mode"] = str(mode or "opportunity")' in APP_SOURCE
    assert 'payload["dominance_normalization_mode"] = str(mode or "range")' in APP_SOURCE


def test_predictions_settings_apply_shared_weighted_predictor_options():
    assert "set_default_scoring_options as _set_prediction_scoring_options" in APP_SOURCE
    assert "_set_prediction_scoring_options(self._enneagram_scoring_options)" in APP_SOURCE
    assert "_set_prediction_scoring_options(options)" in APP_SOURCE

def test_enneagram_predictions_recompute_when_cached_scores_are_blank():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text()

    assert "def _coerce_cached_enneagram_type_scores" in source
    assert "if not isinstance(cached_scores, dict) or not cached_scores:" in source
    assert "cached_scores = _coerce_cached_enneagram_type_scores(" in source
    assert "if cached_scores is not None:" in source
