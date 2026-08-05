from pathlib import Path


def test_ocean_predictions_respect_chart_uses_houses_and_axes():
    source = Path("ephemeraldaddy/gui/features/predictions/ocean.py").read_text()

    assert "chart_uses_houses(chart)" in source
    assert "calculate_dominant_house_weights(chart)" in source
    assert "calculate_dominant_nakshatra_weights(chart)" in source
    assert "OCEAN_NAKSHATRAS" in source
    assert '"O", "C", "E", "A", "N"' in source
    assert "Open" in source and "Conservative" in source
    assert "Conscientious" in source and "Slack" in source
    assert "Extraverted" in source and "Introverted" in source
    assert "Agreeable" in source and "Disagreeable" in source
    assert "Neurotic" in source and "Stable" in source


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
