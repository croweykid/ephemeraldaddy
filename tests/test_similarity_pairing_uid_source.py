import ast
from pathlib import Path


PAIRING_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/similarity_pairing.py"
).read_text(encoding="utf-8")
BATCH_SOURCE = Path("ephemeraldaddy/gui/dbv_batch_similarity.py").read_text(
    encoding="utf-8"
)
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(APP_SOURCE, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_pairing_value_objects_and_lookup_are_uid_only():
    assert "chart_id" not in PAIRING_SOURCE
    assert "selected_chart_uids: list[str]" in PAIRING_SOURCE
    assert "first_chart_uid: str | None" in PAIRING_SOURCE
    assert "second_chart_uid: str | None" in PAIRING_SOURCE
    assert "dict[str, str]" in PAIRING_SOURCE


def test_database_pair_calculation_loads_and_routes_by_uid():
    similarity = _method_source("_calculate_pair_similarity_from_selection")
    dissimilarity = _method_source("_calculate_pair_dissimilarity_from_selection")

    for method in (similarity, dissimilarity):
        assert "self._selected_chart_uids()" in method
        assert "load_chart_by_uid(resolution.first_chart_uid)" in method
        assert "load_chart_by_uid(resolution.second_chart_uid)" in method
        assert "similarity_breakdown_chart_uids(resolution)" in method


def test_batch_similarity_keeps_ids_at_relationship_persistence_boundary():
    assert "owner._selected_chart_uids()" in BATCH_SOURCE
    assert "resolve_chart_uid(" in BATCH_SOURCE
    assert "load_chart_by_uid(chart_uid)" in BATCH_SOURCE
    assert "get_chart_ids_by_uid" in BATCH_SOURCE
    assert "chart_1_id=local_row_id" in BATCH_SOURCE
    assert "chart_2_id=target_local_row_id" in BATCH_SOURCE
