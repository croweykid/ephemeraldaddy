from pathlib import Path


def test_similar_chart_candidates_support_batch_loading_after_filtering():
    source = Path("ephemeraldaddy/gui/features/charts/similar_charts_popout.py").read_text()
    method = source.split("def load_similar_chart_candidates", 1)[1].split(
        "def format_similar_chart_name_parts_html", 1
    )[0]

    assert "load_charts_by_ids: Callable[[list[int]], Mapping[int, Any]] | None = None" in method
    assert "candidate_ids.append(chart_id)" in method
    assert method.index("if chart_row_is_non_aggregable(row):") < method.index("candidate_ids.append(chart_id)")
    assert "charts_by_id = load_charts_by_ids(candidate_ids)" in method
    assert "candidate = charts_by_id.get(chart_id)" in method
    assert method.index("if load_charts_by_ids is not None and candidate_ids:") < method.index(
        "for chart_id in candidate_ids:\n        try:"
    )
