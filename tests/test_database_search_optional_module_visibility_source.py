from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_SOURCE = (ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text()
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_search_prediction_enneagram_uses_optional_module_visibility():
    assert "window.search_enneagram_prediction_section = enneagram_section" in SEARCH_SOURCE
    assert 'enneagram_section.setVisible(visibility_store.get("predictions.enneagram"))' in SEARCH_SOURCE
    assert 'if section_key == "enneagram":' in APP_SOURCE
    assert "search_section.setVisible(bool(checked))" in APP_SOURCE


def test_search_predictability_uses_optional_module_visibility():
    assert "window.search_predictability_section = predictability_section" in SEARCH_SOURCE
    assert 'predictability_section.setVisible(visibility_store.get("chart_view.predictability"))' in SEARCH_SOURCE
    assert 'for section_attr in ("batch_predictability_section", "search_predictability_section")' in APP_SOURCE
