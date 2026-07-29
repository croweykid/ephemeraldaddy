from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_chart_view_has_metadata_only_save_guard():
    assert "def _saved_chart_birth_inputs_match_form" in APP_SOURCE
    assert "def _chart_astro_data_recalculation_token" in APP_SOURCE
    assert "descriptive metadata such as alias" in APP_SOURCE
    assert "persisted_chart_for_change is not None" in APP_SOURCE
    assert "self._saved_chart_birth_inputs_match_form(persisted_chart_for_change)" in APP_SOURCE
    assert "recalculate_chart = False" in APP_SOURCE


def test_metadata_only_guard_tracks_birth_calculation_inputs():
    helper_start = APP_SOURCE.index("def _saved_chart_birth_inputs_match_form")
    helper_end = APP_SOURCE.index("def on_update_chart", helper_start)
    helper_source = APP_SOURCE[helper_start:helper_end]
    for token in (
        "placeholder_checked = self.placeholder_chart_checkbox.isChecked()",
        "_birth_date_from_fields",
        "retcon_time_checkbox",
        "_rectification_range_effective_from_inputs",
        "time_unknown_checkbox",
        "place_edit",
        "_searched_birth_place",
        "_searched_lat",
        "_searched_lon",
        "birthtime_unknown",
        "retcon_time_used",
        "rectification_range_start_minute",
        "rectification_range_end_minute",
    ):
        assert token in helper_source


def test_metadata_only_branch_persists_reminds_me_of_and_avoids_render_spinner():
    update_start = APP_SOURCE.index("def on_update_chart")
    update_end = APP_SOURCE.index("def _reset_new_chart_form", update_start)
    update_source = APP_SOURCE[update_start:update_end]
    assert "persisted_chart_for_change = None" in update_source
    assert "chart.reminds_me_of = (" in update_source
    assert "serialize_reminds_me_of_uids" in update_source
    assert "if not is_placeholder and chart_recalculated:" in update_source
    assert "self._refresh_chart_summary(chart)" in update_source
    assert "self._hide_chart_loading_overlay()" in update_source


def test_placeholder_charts_do_not_short_circuit_birth_input_comparison():
    helper_start = APP_SOURCE.index("def _saved_chart_birth_inputs_match_form")
    helper_end = APP_SOURCE.index("def on_update_chart", helper_start)
    helper_source = APP_SOURCE[helper_start:helper_end]
    assert "if self.placeholder_chart_checkbox.isChecked():\n            return True" not in helper_source
    assert "placeholder_checked or self.time_unknown_checkbox.isChecked()" in helper_source


def test_coordinate_search_selection_for_same_place_label_forces_recalculation():
    helper_start = APP_SOURCE.index("def _saved_chart_birth_inputs_match_form")
    helper_end = APP_SOURCE.index("def on_update_chart", helper_start)
    helper_source = APP_SOURCE[helper_start:helper_end]
    assert "_searched_birth_place" in helper_source
    assert "_searched_lat" in helper_source
    assert "_searched_lon" in helper_source
    assert "saved_lat" in helper_source
    assert "saved_lon" in helper_source
    assert "return False" in helper_source[helper_source.index("searched_lat"):helper_source.rindex("retcon_time")]


def test_chart_save_change_detection_uses_persisted_chart_not_preview_baseline():
    update_start = APP_SOURCE.index("def on_update_chart")
    update_end = APP_SOURCE.index("def _reset_new_chart_form", update_start)
    update_source = APP_SOURCE[update_start:update_end]
    assert "persisted_chart_for_change = None" in update_source
    assert "persisted_chart_for_change = load_chart(chart_id)" in update_source
    previous_refresh_index = update_source.index("previous_chart_for_refresh = (")
    changed_fields_index = update_source.index("changed_fields = self._chart_metadata_changed_fields(")
    refresh_block = update_source[previous_refresh_index:changed_fields_index]
    assert "persisted_chart_for_change" in refresh_block
    assert "self._latest_chart" not in refresh_block
    previous_token_index = update_source.index("previous_recalculation_token = (")
    cache_entry_index = update_source.index("self._cache_chart_view_navigation_entry", previous_token_index)
    token_block = update_source[previous_token_index:cache_entry_index]
    assert "self._chart_analytics_cache_token(persisted_chart_for_change)" in token_block
    assert "self._chart_analytics_cache_token(self._latest_chart)" not in token_block


def test_metadata_only_saves_use_lightweight_db_update_path():
    update_start = APP_SOURCE.index("def on_update_chart")
    update_end = APP_SOURCE.index("def _reset_new_chart_form", update_start)
    update_source = APP_SOURCE[update_start:update_end]
    assert "update_chart_lightweight_metadata" in APP_SOURCE
    assert "if recalculate_chart:\n                update_chart(chart_id, chart, **save_kwargs)" in update_source
    assert "else:\n                update_chart_lightweight_metadata(chart_id, chart)" in update_source
