from ephemeraldaddy.gui.features.charts.selection_header import SelectionSummaryCounts

from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(method_name: str) -> str:
    start = APP_SOURCE.index(f"    def {method_name}")
    next_method = APP_SOURCE.index("\n    def ", start + 1)
    return APP_SOURCE[start:next_method]


def test_selection_changed_can_skip_persistent_selection_sync_for_programmatic_refreshes():
    method = _method_source("_on_selection_changed")

    assert "sync_persistent_selection: bool = True" in method
    assert "if sync_persistent_selection:" in method
    assert "self._merge_visible_selection_into_persistent_selection" in method


def test_sort_refresh_preserves_hidden_persistent_selection():
    method = _method_source("_set_sort_mode")

    assert "self._populate_list(selected_ids=selected_ids or None)" in method
    assert "sync_persistent_selection=False" in method


def test_hide_hypothetical_refresh_preserves_hidden_persistent_selection():
    method = _method_source("_on_hide_hypothetical_toggled")

    assert "selected_ids=set(self._selected_chart_ids())" in method
    assert "sync_persistent_selection=False" in method
