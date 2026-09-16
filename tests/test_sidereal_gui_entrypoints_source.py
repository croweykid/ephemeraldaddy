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


def test_time_sensitivity_refresh_token_includes_coordinate_context():
    schedule_method = APP_SOURCE.split("    def _schedule_chart_render(", 1)[1].split(
        "    def ", 1
    )[0]

    assert 'getattr(chart, "zodiac", "tropical")' in schedule_method
    assert 'getattr(chart, "ayanamsha", "")' in schedule_method


def test_sidereal_chart_info_uses_canonical_sign_keywords_and_contextual_plugins():
    sign_method = APP_SOURCE.split("    def _show_sign_keyword_info(", 1)[1].split(
        "    def _show_element_keyword_info(", 1
    )[0]
    click_handler = APP_SOURCE.split("    def _handle_summary_info_click(", 1)[1].split(
        "    def _run_with_chart_info_output(", 1
    )[0]
    position_method = APP_SOURCE.split("    def _show_position_info(", 1)[1].split(
        "    def _show_decan_info(", 1
    )[0]

    assert "SIGN_KEYWORDS_CANONICAL.get(sign_key.casefold(), {})" in sign_method
    assert 'getattr(chart, "zodiac", "tropical")' in sign_method
    assert "if body_key and not is_sidereal" in sign_method
    assert "self._show_sign_keyword_info(sign, body_name=body)" in position_method
    assert 'zodiac=str(getattr(chart, "zodiac", "tropical") or "tropical")' in click_handler
