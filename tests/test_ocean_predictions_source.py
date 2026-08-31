from pathlib import Path

from ephemeraldaddy.gui.features.predictions.ocean_settings import (
    OceanPredictorWeights,
    ocean_predictor_weights_from_payload,
)


def test_ocean_predictions_respect_chart_uses_houses_and_axes():
    source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert "chart_uses_houses(chart)" in source
    assert "calculate_dominant_house_weights(chart)" in source
    assert "calculate_dominant_nakshatra_weights(chart)" in source
    assert "OCEAN_NAKSHATRAS_THEORY" in source
    assert '"O", "C", "E", "A", "N"' in source
    assert "OCEAN_MIN_SCORE = -10.0" in source
    assert "OCEAN_MAX_SCORE = 10.0" in source
    assert "barh" in source
    assert "axvline(0" in source
    assert "Openness" in source and "Conventionality" in source
    assert "Conscientiousness" in source and "Casualness" in source
    assert "Extraversion" in source and "Introversion" in source
    assert "Agreeableness" in source and "Abrasiveness" in source
    assert "Neuroticism" in source and "Stability" in source


def test_chart_editor_predictions_panel_registers_ocean_section():
    source = Path(
        "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert 'title="OCEAN Personality"' in source
    assert 'register_prediction_section("ocean"' in source
    assert "ocean_prediction_chart_layout" in source
    assert "ocean_prediction_label" in source


def test_ocean_predictions_are_visible_and_rendered_with_predictions_panel():
    visibility_source = Path("ephemeraldaddy/gui/visibility.py").read_text()
    right_panel_source = Path(
        "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py"
    ).read_text()

    assert '"predictions.ocean": True' in visibility_source
    assert 'getattr(owner, "_render_ocean_predictions", None)' in right_panel_source


def test_ocean_scores_to_mbti_rules_are_encoded():
    source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert "def ocean_scores_to_mbti" in source
    assert '("E", "E", "I")' in source
    assert '("O", "N", "S")' in source
    assert '("A", "F", "T")' in source
    assert '("C", "J", "P")' in source
    assert 'letters.append("x")' in source
    assert "abs(score) <= 3.0" in source
    assert "letter.lower()" in source
    assert "MBTI:" in source


def test_ocean_metric_popout_is_registered_and_pickable():
    ocean_source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()
    registry_source = Path(
        "ephemeraldaddy/gui/features/charts/metric_popout_registry.py"
    ).read_text()
    app_source = Path("ephemeraldaddy/gui/app.py").read_text()

    assert "OCEAN_POP_OUT_TITLE" in ocean_source
    assert 'set_gid(f"ocean:{trait}")' in ocean_source
    assert "build_ocean_trait_popout_info" in ocean_source
    assert 'title="OCEAN Personality Predictor"' in registry_source
    assert 'draw=_call_draw("_draw_ocean_predictions")' in registry_source
    assert "configure_info=_configure_ocean" in registry_source
    assert "def _draw_ocean_predictions" in app_source
    assert "def _build_ocean_popout_info" in app_source


def test_ocean_layout_is_cleared_with_chart_displays():
    source = Path("ephemeraldaddy/gui/app.py").read_text()

    assert "self.ocean_prediction_chart_layout" in source
    assert "self.ocean_prediction_canvas = None" in source
    assert "Generate or load a chart to view OCEAN predictions." in source


def test_ocean_predictor_weight_defaults_match_settings_percentages():
    config = OceanPredictorWeights()

    assert config.sign_weight == 45.0
    assert config.body_weight == 25.0
    assert config.nakshatra_weight == 10.0
    assert config.elemental_weight == 10.0
    assert config.house_weight == 10.0
    assert all(
        getattr(config, name)
        for name in (
            "use_sign_weights",
            "use_body_weights",
            "use_nakshatra_weights",
            "use_elemental_weights",
            "use_house_weights",
        )
    )


def test_ocean_predictor_payload_clamps_percentages_and_preserves_switches():
    config = ocean_predictor_weights_from_payload(
        {
            "use_sign_weights": "false",
            "use_body_weights": "true",
            "sign_weight": 150,
            "body_weight": -2,
        }
    )

    assert config.use_sign_weights is False
    assert config.use_body_weights is True
    assert config.sign_weight == 100.0
    assert config.body_weight == 0.0


def test_ocean_scores_include_configurable_elemental_and_weighted_categories():
    source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert "OCEAN_ELEMENTS_THEORY" in source
    assert "calculate_dominant_element_weights(chart)" in source
    assert "config.use_elemental_weights" in source
    assert "config.use_house_weights" in source
    assert "total_category_weight" in source


def test_ocean_settings_orchestration_stays_outside_app_window():
    app_source = Path("ephemeraldaddy/gui/app.py").read_text()
    controller_source = Path(
        "ephemeraldaddy/gui/settings/modules/ocean_predictor.py"
    ).read_text()

    assert "OceanPredictorSettingsController" in controller_source
    assert "class SettingsAdapter(Protocol)" in controller_source
    assert "def _update_ocean_predictor_setting" not in app_source
    assert "ocean_settings_controller.bind_controls" in app_source


def test_ocean_settings_refresh_current_prediction_without_database_cache_invalidation():
    app_source = Path("ephemeraldaddy/gui/app.py").read_text()
    settings_block = app_source.split(
        'enneagram_section = self._add_settings_collapsible_section(content_layout, "Predictions")',
        1,
    )[1].split(
        "property_manager_section = self._add_settings_collapsible_section",
        1,
    )[0]

    assert "owner._refresh_ocean_predictions_after_settings_change" in settings_block
    assert "self._invalidate_database_metrics_cache" not in settings_block
    assert "def _refresh_ocean_predictions_after_settings_change" in app_source
    assert "self._render_ocean_predictions(chart)" in app_source
