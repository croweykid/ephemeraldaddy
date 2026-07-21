from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "ephemeraldaddy"
    / "gui"
    / "features"
    / "charts"
    / "dnd_predictions.py"
).read_text(encoding="utf-8")


def test_dnd_species_prediction_labels_prefer_subspecies_names():
    assert "def _species_display_label" in SOURCE
    assert "return subtype_text if subtype_text else str(family)" in SOURCE
    assert "label = _species_display_label(str(family), subtype_text)" in SOURCE
    assert "labels = [_species_display_label(family, subtype)" in SOURCE


def test_dnd_species_prediction_click_uses_formatted_html_info_panel():
    assert "def format_dnd_species_info_html" in SOURCE
    assert "<b>Category:</b>" in SOURCE
    assert "<b>Evidence:</b>" in SOURCE
    assert "CHART_DATA_HIGHLIGHT_COLOR" in SOURCE
    assert "set_chart_info_html(info_panel, html_text)" in SOURCE
    assert "format_dnd_species_info_html(" in SOURCE
    assert "description_text = _species_description_text(family, subtype)" in SOURCE


def test_dnd_species_prediction_cache_version_invalidates_old_labels():
    assert "DND_SPECIES_CLASS_CACHE_VERSION = 4" in SOURCE
