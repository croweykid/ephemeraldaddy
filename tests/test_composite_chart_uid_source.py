import ast
from pathlib import Path


APP_PATH = Path("ephemeraldaddy/gui/app.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(APP_SOURCE, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_composite_chart_public_workflow_is_uid_only():
    prompt = _method_source("_prompt_composite_chart_selection")
    generate = _method_source("_generate_composite_chart_for_uids")

    assert "chart_id" not in prompt
    assert "chart_id" not in generate
    assert "tuple[str, str]" in prompt
    assert "load_chart_by_uid(base_chart_uid)" in generate
    assert "load_chart_by_uid(overlay_chart_uid)" in generate
    assert "_generate_composite_chart_for_ids" not in APP_SOURCE


def test_composite_chart_choices_display_stable_uid_not_local_row_id():
    prompt = _method_source("_prompt_composite_chart_selection")

    assert "[UID {chart_uid}]" in prompt
    assert "[#{" not in prompt


def test_chart_editor_synastry_routes_current_uid_without_id_round_trip():
    synastry = _method_source("on_get_synastry_chart")
    human_design = _method_source("_open_human_design_synastry_for_chart_uid")

    assert "default_first_chart_uid=self.current_chart_uid" in synastry
    assert "_generate_composite_chart_for_uids(*chart_uids)" in synastry
    assert "get_chart_id_by_uid" not in human_design
    assert "load_chart_by_uid(chart_uids[0])" in human_design
    assert "load_chart_by_uid(chart_uids[1])" in human_design
