from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _sort_method_source() -> str:
    return APP_SOURCE.split("    def _set_sort_mode", 1)[1].split(
        "    @staticmethod\n    def _age_sort_key", 1
    )[0]


def test_sort_only_rebuilds_database_rows_without_external_refreshes():
    method = _sort_method_source()

    assert "refresh_metrics=False" in method
    assert "_on_selection_changed" not in method
    assert method.index("self._cancel_inline_chart_rename()") < method.index(
        "self._populate_list("
    )


def test_list_population_does_not_refresh_unrelated_chart_tool_options():
    method = APP_SOURCE.split("    def _populate_list", 1)[1].split(
        "    def _run_database_metrics_refresh", 1
    )[0]

    assert "_refresh_personal_transit_chart_options" not in method
    assert "_refresh_similarities_chart_options" not in method


def test_database_hydration_refreshes_chart_tool_options():
    method = APP_SOURCE.split("    def _refresh_charts", 1)[1].split(
        "    def _normalize_chart_row", 1
    )[0]

    list_rows = method.index("self._chart_rows = list_charts()")
    transit_options = method.index("self._refresh_personal_transit_chart_options()")
    similarities_options = method.index("self._refresh_similarities_chart_options()")
    populate_list = method.index("self._populate_list(")
    assert list_rows < transit_options < populate_list
    assert list_rows < similarities_options < populate_list
