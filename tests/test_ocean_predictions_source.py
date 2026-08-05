from pathlib import Path


def test_ocean_predictions_respect_chart_uses_houses_and_axes():
    source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert "chart_uses_houses(chart)" in source
    assert "calculate_dominant_house_weights(chart)" in source
    assert "calculate_dominant_nakshatra_weights(chart)" in source
    assert "OCEAN_NAKSHATRAS" in source
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
    source = Path("ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert 'title="OCEAN Personality"' in source
    assert 'register_prediction_section("ocean"' in source
    assert "ocean_prediction_chart_layout" in source
    assert "ocean_prediction_label" in source


def test_ocean_predictions_are_visible_and_rendered_with_predictions_panel():
    visibility_source = Path("ephemeraldaddy/gui/visibility.py").read_text()
    right_panel_source = Path("ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

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


def test_ocean_metric_popout_registry_is_wired():
    registry_source = Path("ephemeraldaddy/gui/features/charts/metric_popout_registry.py").read_text()
    app_source = Path("ephemeraldaddy/gui/app.py").read_text()
    ocean_source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert 'title="OCEAN Personality Predictor"' in registry_source
    assert 'draw=_call_draw("_draw_ocean_predictions")' in registry_source
    assert "configure_info=_configure_ocean" in registry_source
    assert "connect_ocean_popout_pick_handler" in registry_source
    assert "def _draw_ocean_predictions" in app_source
    assert "def build_ocean_popout_info_html" in ocean_source
    assert "def connect_ocean_popout_pick_handler" in ocean_source
    assert 'bar.set_gid(f"ocean:{trait}")' in ocean_source
    assert 'tick_label.set_gid(f"ocean:{trait}")' in ocean_source


def test_clear_chart_displays_clears_ocean_layout_and_label():
    source = Path("ephemeraldaddy/gui/app.py").read_text()

    clear_start = source.index("def _clear_chart_displays")
    clear_end = source.index("def _render_chart", clear_start)
    clear_source = source[clear_start:clear_end]

    assert "self.ocean_prediction_chart_layout" in clear_source
    assert "self.ocean_prediction_canvas = None" in clear_source
    assert "self.ocean_prediction_label.setText" in clear_source
    assert "Loading OCEAN predictions" in clear_source
