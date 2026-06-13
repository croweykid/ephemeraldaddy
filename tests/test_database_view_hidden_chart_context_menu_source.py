from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(method_name: str) -> str:
    start = APP_SOURCE.index(f"    def {method_name}")
    next_method = APP_SOURCE.index("\n    def ", start + 1)
    return APP_SOURCE[start:next_method]


def test_show_hidden_setting_names_charts_explicitly():
    assert 'QCheckBox("Show Hidden Charts")' in APP_SOURCE
    assert 'QCheckBox("Show Hidden")' not in APP_SOURCE


def test_context_menu_offers_unhide_only_when_hidden_charts_are_shown():
    method = _method_source("_show_chart_list_context_menu")

    assert 'getattr(self, "_show_hidden_charts", False)' in method
    assert 'selected_hidden_ids' in method
    assert '"Unhide selected chart"' in method
    assert 'self._unhide_selected_charts(selected_hidden_ids)' in method


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
