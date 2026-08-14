import ast
from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)
EXPORT_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/batch_total_chart_export.py"
).read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(APP_SOURCE, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_single_chart_prompt_returns_uid_and_never_displays_local_row_id():
    method = _method_source("_prompt_single_chart_selection")

    assert "-> str | None" in method
    assert "get_chart_uid_map(row[0] for row in rows)" in method
    assert "[UID {chart_uid}]" in method
    assert "chart_id" not in method


def test_middle_panel_chart_routing_is_uid_first():
    resolver = _method_source("_resolve_middle_panel_tool_chart_uid")
    router = _method_source("_on_middle_panel_chart_tool")

    assert "self._selected_chart_uids()" in resolver
    assert "load_chart_by_uid(chart_uid)" in router
    assert "_resolve_middle_panel_tool_chart_id" not in APP_SOURCE


def test_total_chart_export_worker_and_flow_are_uid_only():
    assert "chart_id" not in EXPORT_SOURCE
    assert "chart_ids" not in EXPORT_SOURCE
    assert "Sequence[tuple[str, str]]" in EXPORT_SOURCE
    assert "load_chart_by_uid(chart_uid)" in EXPORT_SOURCE


def test_database_view_passes_uids_into_total_chart_export():
    method = _method_source("_on_export_selected_total_chart")

    assert "self._selected_chart_uids()" in method
    assert "load_chart_by_uid=load_chart_by_uid" in method
    assert "self._selected_local_row_ids()" not in method
