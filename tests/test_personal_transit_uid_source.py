import ast
from pathlib import Path


CONTROLLER_PATH = Path("ephemeraldaddy/gui/features/transits/controller.py")
CONTROLLER_SOURCE = CONTROLLER_PATH.read_text(encoding="utf-8")
CONTROLLER_TREE = ast.parse(CONTROLLER_SOURCE)
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def _method_source(tree: ast.AST, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_personal_transit_controller_public_identity_is_uid_only():
    assert "chart_id" not in CONTROLLER_SOURCE
    assert "resolve_personal_transit_chart_uid" in CONTROLLER_SOURCE
    assert "resolve_personal_transit_chart_id" not in CONTROLLER_SOURCE


def test_personal_transit_options_batch_resolve_and_store_uids():
    method = _method_source(
        CONTROLLER_TREE,
        CONTROLLER_SOURCE,
        "refresh_personal_transit_chart_options",
    )

    assert "get_chart_uid_map(row[0] for row in rows)" in method
    assert "_personal_transit_chart_lookup[key] = chart_uid" in method
    assert "[UID {chart_uid}]" in method
    assert "[#{" not in method


def test_personal_transit_generation_loads_by_uid():
    method = _method_source(
        CONTROLLER_TREE,
        CONTROLLER_SOURCE,
        "generate_personal_transit",
    )

    assert "load_chart_by_uid(chart_uid)" in method
    assert "normalize_chart(natal_chart, chart_type=\"natal\")" in method


def test_database_selection_routes_item_uid_to_personal_transit():
    method = _method_source(
        APP_TREE, APP_SOURCE, "_on_generate_personal_transit_for_selected_chart"
    )

    assert "self._normalized_item_chart_uid(item)" in method
    assert "self._item_local_row_id(item)" not in method
    assert "candidate_uid == chart_uid" in method
