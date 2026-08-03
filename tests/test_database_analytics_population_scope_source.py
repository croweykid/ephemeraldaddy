import ast
from pathlib import Path


def test_loaded_chart_count_is_assigned_before_analytics_population_scope_uses_it():
    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_update_sentiment_tally"
    )

    loaded_chart_assignments = [
        node.lineno
        for node in ast.walk(method)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "loaded_charts"
            for target in node.targets
        )
    ]
    analytics_population_reads = [
        node.lineno
        for node in ast.walk(method)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "analytics_population_ids"
            for target in node.targets
        )
    ]

    assert loaded_chart_assignments
    assert analytics_population_reads
    assert min(loaded_chart_assignments) < min(analytics_population_reads)
