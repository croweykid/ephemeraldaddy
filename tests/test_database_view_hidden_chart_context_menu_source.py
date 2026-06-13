from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(method_name: str) -> str:
    start = APP_SOURCE.index(f"    def {method_name}")
    next_method = APP_SOURCE.index("\n    def ", start + 1)
    return APP_SOURCE[start:next_method]


def test_show_hidden_setting_names_charts_explicitly():
    assert 'QCheckBox("Show Hidden Charts")' in APP_SOURCE
    assert 'QCheckBox("Show Hidden")' not in APP_SOURCE


def test_context_menu_offers_rename_delete_and_unhide_actions():
    method = _method_source("_show_chart_list_context_menu")

    assert 'menu.addAction("Rename")' in method
    assert 'menu.addAction("Delete")' in method
    assert "self._on_rename_selected_chart()" in method
    assert "self._on_delete()" in method
    assert 'getattr(self, "_show_hidden_charts", False)' in method
    assert 'selected_hidden_ids' in method
    assert '"Unhide selected chart"' in method
    assert 'self._unhide_selected_charts(selected_hidden_ids)' in method


def test_context_menu_offers_single_chart_tool_actions():
    method = _method_source("_show_chart_list_context_menu")

    assert 'if len(selected_ids) == 1:' in method
    assert '("bazi", "See BaZi Chart")' in method
    assert '("human_design", "See Human Design Chart")' in method
    assert '("personal_transit", "See Transit Chart")' in method
    assert '("similar_charts", "See Similar Charts")' in method
    assert "self._on_middle_panel_chart_tool(tool_actions[chosen_action])" in method


def test_unhide_selected_charts_removes_ids_and_preserves_selection():
    method = _method_source("_unhide_selected_charts")

    assert "self._hidden_chart_ids.difference_update(normalized_ids)" in method
    assert "self._save_hidden_chart_ids_to_settings()" in method
    assert "set(self._selected_chart_ids()) | normalized_ids" in method
    assert "sync_persistent_selection=False" in method


def test_distinguishing_metric_cache_keeps_filtered_out_payloads():
    method = _method_source("_prediction_norm_metric_payloads")

    assert "stale_ids = set(chart_cache) - active_ids" not in method
    assert "Keep cached metric payloads for charts outside" in method
