from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_predictability_optional_module_defaults_hidden_and_has_distinct_copy():
    visibility = (REPO_ROOT / "ephemeraldaddy/gui/visibility.py").read_text()
    display_preferences = (
        REPO_ROOT / "ephemeraldaddy/gui/settings/modules/display_preferences.py"
    ).read_text()

    assert '"chart_view.predictability": False' in visibility
    assert '"Show Predictability"' in display_preferences
    assert "This is not the " in display_preferences
    assert "Predictions module." in display_preferences


def test_predictability_visibility_sync_covers_dbv_and_chart_editor_sections():
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    search_panel = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text()
    chart_view_window = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert "self.batch_predictability_section = predictability_section" in app
    assert 'predictability_section.setVisible(self._visibility.get("chart_view.predictability"))' in app
    assert "window.search_predictability_section = predictability_section" in search_panel
    assert 'predictability_section.setVisible(visibility_store.get("chart_view.predictability"))' in search_panel
    assert "self.predictability_section_box = predictability_box" in app
    assert 'predictability_box.setVisible(self._visibility.get("chart_view.predictability"))' in app
    assert (
        'for section_attr in ("batch_predictability_section", "predictability_section_box", "search_predictability_section")'
        in chart_view_window
    )


def test_settings_optional_module_toggle_updates_predictability_targets():
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    display_preferences = (
        REPO_ROOT / "ephemeraldaddy/gui/settings/modules/display_preferences.py"
    ).read_text()

    assert "set_predictability_visibility: BoolCallback" in display_preferences
    assert "config.set_predictability_visibility" in display_preferences
    assert "set_predictability_visibility=self._set_predictability_visibility_from_settings" in app
    assert 'self._visibility.set("chart_view.predictability", checked)' in app
    assert 'for section_attr in ("batch_predictability_section", "search_predictability_section")' in app
    assert 'sync_predictability = getattr(parent, "_sync_predictability_visibility", None)' in app
