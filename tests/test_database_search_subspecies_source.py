from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
SEARCH_PANEL_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "dbv_search_panel.py").read_text(encoding="utf-8")


def test_species_filter_exposes_dependent_subspecies_dropdown() -> None:
    assert "FAMILY_SUBTYPES = app_module.FAMILY_SUBTYPES" in SEARCH_PANEL_SOURCE
    assert "window.subspecies_filter_combo = QComboBox()" in SEARCH_PANEL_SOURCE
    assert "def refresh_subspecies_filter_options()" in SEARCH_PANEL_SOURCE
    assert "FAMILY_SUBTYPES.get(selected_species, [])" in SEARCH_PANEL_SOURCE
    assert "row_visible = selected_species != \"Any\" and bool(subtypes)" in SEARCH_PANEL_SOURCE
    assert "window.species_filter_combo.currentIndexChanged.connect(on_species_filter_changed)" in SEARCH_PANEL_SOURCE
    assert "window.subspecies_filter_combo.currentIndexChanged.connect(window._on_filter_changed)" in SEARCH_PANEL_SOURCE


def test_search_filters_apply_selected_subspecies_to_top_three_species() -> None:
    assert "FAMILY_SUBTYPES" in APP_SOURCE
    assert "selected_subspecies = (" in APP_SOURCE
    assert "if selected_species != \"Any\" or selected_subspecies != \"Any\":" in APP_SOURCE
    assert "top_three_subspecies = {" in APP_SOURCE
    assert "if selected_species == \"Any\" or species_name == selected_species" in APP_SOURCE
    assert "if selected_subspecies not in top_three_subspecies:" in APP_SOURCE
    assert "species_top_three = self._cached_top_three_species_for_filter(chart)" in APP_SOURCE
    species_filter_block = APP_SOURCE.split("if selected_species != \"Any\" or selected_subspecies != \"Any\":", 1)[1].split("if selected_dnd_class != \"Any\":", 1)[0]
    assert "assign_top_three_species(chart)" not in species_filter_block


def test_subspecies_filter_uses_bulk_cached_prediction_metadata() -> None:
    assert "def _cached_top_three_species_for_filter" in APP_SOURCE
    assert "get_all_chart_dnd_prediction_metadata()" in APP_SOURCE
    assert "search must not run that scorer synchronously" in APP_SOURCE


def test_clear_and_active_filter_state_include_subspecies() -> None:
    assert "self.subspecies_filter_combo.currentData() == \"Any\"" in APP_SOURCE
    assert "self.subspecies_filter_combo.setCurrentIndex(0)" in APP_SOURCE
