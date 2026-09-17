from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path(__file__).parents[1] / "ephemeraldaddy" / "gui" / "app.py"
APP_TREE = ast.parse(APP_PATH.read_text(encoding="utf-8"))


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(APP_PATH.read_text(encoding="utf-8"), node) or ""
    raise AssertionError(f"method not found: {name}")


def test_batch_tag_finalize_uses_scoped_roster_refresh() -> None:
    source = _method_source("_finalize_batch_tag_updates")
    assert "_refresh_roster_after_tag_change" in source
    assert "_refresh_filters_after_batch_edit" not in source
    assert "_refresh_charts" not in source


def test_scoped_tag_refresh_does_not_reread_database() -> None:
    source = _method_source("_refresh_roster_after_tag_change")
    assert "_populate_list" in source
    assert "list_charts" not in source
    assert "_refresh_charts" not in source


def test_tag_row_patch_updates_lightweight_projection() -> None:
    source = _method_source("_patch_chart_row_tags")
    assert "self._chart_rows[row_index] = patched_row" in source
    assert "self._active_chart_rows_by_uid[chart_uid] = patched_row" in source
    assert "self._displayed_chart_rows_by_uid[chart_uid] = patched_row" in source
