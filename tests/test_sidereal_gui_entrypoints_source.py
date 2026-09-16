from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
CHROME_SOURCE = Path("ephemeraldaddy/gui/window_chrome.py").read_text(encoding="utf-8")


def test_settings_astrology_section_builds_default_mode_controls():
    assert "add_astrology_mode_controls(" in APP_SOURCE
    assert "on_changed=self._on_default_astrology_context_changed" in APP_SOURCE
    assert "save_astrology_context(self._settings, context)" in APP_SOURCE


def test_both_window_chrome_menus_expose_sidereal_chart_editor():
    assert CHROME_SOURCE.count('"Sidereal Chart Editor"') == 2
    assert '"on_open_sidereal_chart"' in CHROME_SOURCE
    assert '"_on_menu_open_sidereal_chart"' in CHROME_SOURCE


def test_database_entrypoint_reuses_standard_single_chart_prompt():
    assert 'self._on_middle_panel_chart_tool("sidereal")' in APP_SOURCE
    assert '"sidereal": "Sidereal Chart Editor"' in APP_SOURCE
    assert "_resolve_middle_panel_tool_chart_id(tool_title)" in APP_SOURCE


def test_loaded_chart_is_projected_without_polluting_tropical_navigation_cache():
    cache_call = "self._cache_chart_view_navigation_entry(normalized_chart_uid, chart)"
    projection_call = "chart = chart_for_astrology_context(chart, self._astrology_context)"
    assert APP_SOURCE.index(cache_call, APP_SOURCE.index("def load_chart_by_uid(")) < APP_SOURCE.index(
        projection_call, APP_SOURCE.index("def load_chart_by_uid(")
    )
