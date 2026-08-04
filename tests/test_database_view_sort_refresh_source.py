from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _sort_method_source() -> str:
    return APP_SOURCE.split("    def _set_sort_mode", 1)[1].split(
        "    @staticmethod\n    def _age_sort_key", 1
    )[0]


def test_sort_only_rebuilds_database_rows_without_external_refreshes():
    method = _sort_method_source()

    assert "refresh_metrics=False" in method
    assert "refresh_external_controls=False" in method
    assert "_on_selection_changed" not in method


def test_list_population_can_skip_unrelated_chart_tool_options():
    method = APP_SOURCE.split("    def _populate_list", 1)[1].split(
        "    def _run_database_metrics_refresh", 1
    )[0]

    assert "refresh_external_controls: bool = True" in method
    assert "if refresh_external_controls:" in method
    assert "self._refresh_personal_transit_chart_options()" in method
    assert "self._refresh_similarities_chart_options()" in method
