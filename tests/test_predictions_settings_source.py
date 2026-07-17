from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text()
RIGHT_PANEL_STACK_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()


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


def test_predictions_traits_placeholder_prevents_whole_panel_skip():
    assert "def _traits_predictions_have_rendered_content" in RIGHT_PANEL_STACK_SOURCE
    assert "traits_has_default_placeholder = not _traits_predictions_have_rendered_content(owner)" in RIGHT_PANEL_STACK_SOURCE
    assert "and traits_ready" in RIGHT_PANEL_STACK_SOURCE
    assert "if callable(render_traits) and not traits_ready" in RIGHT_PANEL_STACK_SOURCE


def test_predictions_warmup_sections_fail_independently():
    assert "section_errors: list[str] = []" in RIGHT_PANEL_STACK_SOURCE
    assert "Enneagram prediction cache failed" in RIGHT_PANEL_STACK_SOURCE
    assert "D&D statblock prediction cache failed" in RIGHT_PANEL_STACK_SOURCE
    assert "D&D alignment prediction cache failed" in RIGHT_PANEL_STACK_SOURCE
    assert "Some Predictions sections failed; showing available cached sections" in RIGHT_PANEL_STACK_SOURCE


def test_gender_guesser_render_routes_through_predictions_panel():
    assert '"gender": "predictions"' in APP_SOURCE
    assert '"gender_guesser"} and not self._is_chart_analysis_section_visible(section_key)' in APP_SOURCE
    assert 'parent_layout=layout' in (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

def test_predictions_visibility_can_skip_hidden_section_work():
    visibility_source = (REPO_ROOT / "ephemeraldaddy/gui/visibility.py").read_text()
    chart_view_source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
    default_visible_sections = ("traits", "dnd_species", "dnd_class", "dnd_alignment")
    default_hidden_sections = ("enneagram", "dnd_statblock")
    for section_key in default_visible_sections:
        assert f'"predictions.{section_key}": True' in visibility_source
        assert f'section_key="predictions.{section_key}"' in chart_view_source
    for section_key in default_hidden_sections:
        assert f'"predictions.{section_key}": False' in visibility_source
        assert f'section_key="predictions.{section_key}"' in chart_view_source
    assert "def sync_prediction_section_visibility" in RIGHT_PANEL_STACK_SOURCE
    assert "sections = (set(sections) & visible_sections)" in RIGHT_PANEL_STACK_SOURCE
    assert "All Predictions sections are hidden; nothing to calculate." in RIGHT_PANEL_STACK_SOURCE
    assert "if self._visibility.get(\"predictions.enneagram\")" in APP_SOURCE
    assert "adapter.cache_alignment_metadata(chart)" in APP_SOURCE
