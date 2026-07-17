from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAIT_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text(encoding="utf-8")
DND_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text(encoding="utf-8")
ENNEAGRAM_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text(encoding="utf-8")
RIGHT_PANEL_STACK_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text(encoding="utf-8")


def test_trait_chart_signature_uses_only_essential_birth_data_not_derived_payloads():
    helper = TRAIT_SOURCE.split("def _chart_trait_metadata_signature", 1)[1].split(
        "def _database_norm_refresh_threshold", 1
    )[0]

    assert '"birth_date"' in helper
    assert '"birth_time"' in helper
    assert '"birth_place"' in helper
    assert '"retcon_time_used"' in helper
    assert '"retcon_hour"' in helper
    assert '"retcon_minute"' in helper
    assert '"rectification_range_used"' in helper
    assert '"rectification_range_start_minute"' in helper
    assert '"rectification_range_end_minute"' in helper
    assert '"chart_uses_houses"' in helper
    assert '"scoring_payload"' not in helper
    assert '"positions"' not in helper
    assert '"aspects"' not in helper
    assert '"human_design_gates"' not in helper
    assert '"bazi_sign_weights"' not in helper


def test_dnd_cache_tokens_ignore_chart_name_and_include_rectification_range():
    stat_helper = DND_SOURCE.split("def _chart_state_cache_token", 1)[1].split(
        "def _statblock_cache_key", 1
    )[0]
    alignment_helper = DND_SOURCE.split("def _dnd_alignment_cache_key", 1)[1].split(
        "def _dnd_alignment_score_parts", 1
    )[0]

    for helper in (stat_helper, alignment_helper):
        assert '"name"' not in helper
        assert '"birth_date"' in helper
        assert '"birth_time"' in helper
        assert '"datetime_iso"' in helper
        assert '"rectification_range_used"' in helper
        assert '"rectification_range_start_minute"' in helper
        assert '"rectification_range_end_minute"' in helper


def test_enneagram_cache_token_includes_rectification_range_birth_data():
    helper = ENNEAGRAM_SOURCE.split("def _enneagram_chart_state_token", 1)[1].split(
        "def _load_persisted_enneagram_prediction_payload", 1
    )[0]

    assert '"birth_date"' in helper
    assert '"birth_time"' in helper
    assert '"datetime_iso"' in helper
    assert '"rectification_range_used"' in helper
    assert '"rectification_range_start_minute"' in helper
    assert '"rectification_range_end_minute"' in helper


def test_predictions_right_panel_render_token_includes_rectification_range_birth_data():
    helper = RIGHT_PANEL_STACK_SOURCE.split("def _chart_right_panel_prediction_render_token", 1)[1].split(
        "def schedule_chart_render_for_active_right_panel", 1
    )[0]

    assert '"rectification_range_used"' in helper
    assert '"rectification_range_start_minute"' in helper
    assert '"rectification_range_end_minute"' in helper


def test_predictions_manual_recalculation_setting_defaults_to_manual_and_blocks_trait_auto_load():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    dev_tools_source = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")
    trait_render = TRAIT_SOURCE.split("def render_traits_predictions", 1)[1]

    assert 'SETTINGS_KEY_PREDICTIONS_MANUAL_RECALCULATION_ONLY = "predictions/manual_recalculation_only"' in app_source
    assert 'fallback: bool = True' in app_source.split('def _load_predictions_manual_recalculation_only', 1)[1].split('\n\n', 1)[0]
    assert 'manual recalculation/refresh only (vs automatic)' in dev_tools_source
    assert 'manual_checkbox.setChecked(bool(manual_value))' in app_source
    assert 'if _predictions_manual_recalculation_only(owner):' in trait_render
    assert '_traits_calculate_prompt_html()' in trait_render


def test_stale_predictions_show_cached_data_before_optional_auto_refresh():
    dnd_render = DND_SOURCE.split("def render(self, chart", 1)[1]
    enneagram_render = ENNEAGRAM_SOURCE.split("def render(self, chart", 1)[1]
    trait_render = TRAIT_SOURCE.split("def render_traits_predictions", 1)[1]

    assert '_trait_predictions_refresh_message' in trait_render
    assert '_apply_traits_prediction_metadata(' in trait_render
    assert '_start_traits_prediction_calculation(owner)' in trait_render
    assert 'automatic refresh is running in the background' in DND_SOURCE
    assert 'self._show_stale_recalculate_notice(self.chart_layout, chart, "dnd_statblock", refreshing=not manual_only)' in dnd_render
    assert 'self._show_stale_recalculate_notice(self.alignment_layout, chart, "dnd_alignment", refreshing=not manual_only)' in dnd_render
    assert 'auto_refresh_started = True' in dnd_render
    assert 'self.calculate_callback(chart, None)' in dnd_render
    assert 'self._show_stale_recalculate_notice(chart, refreshing=not manual_only)' in enneagram_render
    assert 'self.calculate_callback(chart, "enneagram")' in enneagram_render


def test_predictions_cached_payloads_are_guarded_by_current_chart_uid():
    dnd_stat_restore = DND_SOURCE.split("def _restore_statblock_cache", 1)[1].split(
        "def _statblock_cache_is_stale", 1
    )[0]
    dnd_alignment = DND_SOURCE.split("def _dnd_alignment_score_parts", 1)[1].split(
        "def dnd_alignment_deviations", 1
    )[0]
    enneagram_restore = ENNEAGRAM_SOURCE.split("def _restore_cache", 1)[1].split(
        "def _cache_is_stale", 1
    )[0]

    assert "def _cache_payload_chart_uid_matches" in DND_SOURCE
    assert "def _cache_payload_chart_uid_matches" in ENNEAGRAM_SOURCE
    assert '"chart_uid": _chart_prediction_cache_uid(chart)' in DND_SOURCE
    assert 'serializable["chart_uid"] = chart_uid' in DND_SOURCE
    assert '_cache_payload_chart_uid_matches(chart, cached, require_uid=True)' in dnd_stat_restore
    assert '_cache_payload_chart_uid_matches(chart, restored, require_uid=True)' in dnd_stat_restore
    assert '_cache_payload_chart_uid_matches(chart, cached, require_uid=True)' in dnd_alignment
    assert '_cache_payload_chart_uid_matches(chart, restored, require_uid=True)' in dnd_alignment
    assert '"chart_uid": _chart_prediction_cache_uid(chart)' in ENNEAGRAM_SOURCE
    assert 'serializable["chart_uid"] = chart_uid' in ENNEAGRAM_SOURCE
    assert '_cache_payload_chart_uid_matches(chart, cached, require_uid=True)' in enneagram_restore


def test_dnd_alignment_draw_respects_stale_cache_without_recomputing_in_manual_mode():
    dnd_alignment_parts = DND_SOURCE.split("def _dnd_alignment_score_parts", 1)[1].split(
        "def dnd_alignment_deviations", 1
    )[0]
    dnd_render = DND_SOURCE.split("def render(self, chart", 1)[1].split(
        "def connect_dnd_alignment_popout_pick_handler", 1
    )[0]

    assert "if cached_key == cache_key or allow_stale:" in dnd_alignment_parts
    assert "_cache_payload_chart_uid_matches(chart, alignment_cache, require_uid=True)" in dnd_render
    assert "_cache_payload_chart_uid_matches(chart, restored_alignment, require_uid=True)" in dnd_render
    assert 'restored_alignment["chart_uid"] = _chart_prediction_cache_uid(chart)' in dnd_render


def test_dnd_species_and_class_predictions_are_persisted_by_chart_uid():
    dnd_render_species = DND_SOURCE.split("def _render_species_and_class_summaries", 1)[1].split(
        "label_sections =", 1
    )[0]

    assert "Predictions cache contract" in DND_SOURCE
    assert "Do not silently refresh stale cached sections from render/draw paths." in TRAIT_SOURCE
    assert "def _restore_species_class_cache" in DND_SOURCE
    assert "def _cache_species_class_metadata" in DND_SOURCE
    assert '_persist_dnd_prediction_payload(chart, "species_class", cache_payload)' in DND_SOURCE
    assert '"species": _collect_ranked_species_payloads(chart)' in DND_SOURCE
    assert '"classes": class_payloads' in DND_SOURCE
    assert "self._cache_species_class_metadata(chart)" in DND_SOURCE
    assert "species_class_cache = self._restore_species_class_cache(chart)" in dnd_render_species
    assert "species_class_cache = self._cache_species_class_metadata(chart)" in dnd_render_species
    assert "species_payloads=species_payloads" in DND_SOURCE
    assert "class_payloads=class_payloads" in DND_SOURCE
