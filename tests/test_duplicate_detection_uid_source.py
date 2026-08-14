import ast
from pathlib import Path


SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/duplicate_detection.py"
).read_text(encoding="utf-8")
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(APP_SOURCE, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_duplicate_detection_public_model_is_uid_only():
    assert "chart_id" not in SOURCE
    assert "duplicate_uids: set[str]" in SOURCE
    assert "load_chart_by_uid: Callable[[str]" in SOURCE
    assert "excluded_pairs: set[tuple[str, str]]" in SOURCE


def test_database_view_keeps_duplicate_detection_results_as_uids():
    method = _method_source("_on_check_for_duplicates")

    assert "chart_uids_by_local_row=uid_by_local_row" in method
    assert "load_chart_by_uid=self._get_chart_for_filter_by_uid" in method
    assert "set(duplicate_result.duplicate_uids)" in method
    assert "get_chart_uid_map(duplicate_result" not in method
