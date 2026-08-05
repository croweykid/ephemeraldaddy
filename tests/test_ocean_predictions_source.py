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
