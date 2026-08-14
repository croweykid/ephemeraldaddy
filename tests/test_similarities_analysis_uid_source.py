import ast
from pathlib import Path


SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/similarities_analysis.py"
).read_text(encoding="utf-8")
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)


def _method_source(name: str) -> str:
    for node in ast.walk(APP_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(APP_SOURCE, node) or ""
    raise AssertionError(f"Method {name!r} was not found")


def test_similarity_analysis_protocols_are_uid_first():
    protocol_region = SOURCE[
        SOURCE.index("class SimilaritiesBaselineProvider"):
        SOURCE.index("_DISSIMILARITIES_SECTION_ORDER")
    ]

    assert "chart_id" not in protocol_region
    assert "chart_uids: list[str]" in protocol_region
    assert "_get_chart_for_filter_by_uid" in protocol_region


def test_similarity_baseline_cache_is_uid_keyed():
    cache_region = SOURCE[
        SOURCE.index("class SimilaritiesDbBaselineCache"):
        SOURCE.index("def _match_counts")
    ]

    assert "tuple[str, ...]" in cache_region
    assert "db_chart_uids: list[str]" in cache_region
    assert "tuple(db_chart_uids)" in cache_region
    assert "chart_id" not in cache_region


def test_database_similarity_analysis_builders_load_by_uid():
    for name in (
        "_build_common_position_signs",
        "_build_common_houses_in_positions",
        "_build_common_signs_in_houses",
        "_build_common_aspects",
        "_build_common_human_design_aggregates",
    ):
        method = _method_source(name)
        assert "chart_uids: list[str]" in method
        assert "_get_chart_for_filter_by_uid" in method


def test_high_similarity_public_workflow_accepts_and_returns_uids():
    high_similarity_region = SOURCE[SOURCE.index("HighSimilarityOpenCallback ="):]
    app_method = _method_source("_show_high_similarity_chart_pairs")

    assert "chart_uids: list[str]" in high_similarity_region
    assert "load_charts_by_uids" in high_similarity_region
    assert "pairs: list[tuple[float, str, str]]" in high_similarity_region
    assert "chart_uids=list(getattr(self, \"_active_chart_rows_by_uid\", {}))" in app_method
    assert "load_charts_by_uids=load_charts_by_uids" in app_method
