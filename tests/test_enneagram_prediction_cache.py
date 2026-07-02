import ast
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py"


def _load_cache_helpers():
    source = SOURCE_PATH.read_text()
    module_ast = ast.parse(source)
    wanted = {
        "_coerce_complete_enneagram_type_scores",
        "cache_enneagram_prediction_metadata",
    }
    selected = [node for node in module_ast.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"Any": object, "math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace


def test_complete_enneagram_cache_validation_requires_all_nine_finite_scores():
    helpers = _load_cache_helpers()
    coerce = helpers["_coerce_complete_enneagram_type_scores"]

    complete = {str(num): num * 1.5 for num in range(1, 10)}
    assert coerce(complete) == {num: num * 1.5 for num in range(1, 10)}
    assert coerce({}) is None
    assert coerce({1: 1.0}) is None
    assert coerce({**{num: float(num) for num in range(1, 10)}, 4: float("nan")}) is None


def test_enneagram_metadata_cache_preserves_computed_all_zero_scores():
    helpers = _load_cache_helpers()
    cache_metadata = helpers["cache_enneagram_prediction_metadata"]

    class Chart:
        pass

    chart = Chart()
    scores = cache_metadata(chart, {})

    assert scores == {num: 0.0 for num in range(1, 10)}
    assert chart.enneagram_type_weights == {num: 0.0 for num in range(1, 10)}
    assert chart.dominant_enneagram_type is None
    assert chart.top_three_enneagram_types == []


def test_enneagram_draw_and_adapter_use_complete_cache_validator():
    source = SOURCE_PATH.read_text()
    draw_start = source.index("def draw_enneagram_predictions")
    draw_source = source[draw_start : source.index("def build_enneagram_popout_info_html", draw_start)]
    cache_start = source.index("    def cache_metadata")
    cache_source = source[cache_start : source.index("    def render", cache_start)]

    assert "_coerce_complete_enneagram_type_scores" in draw_source
    assert "type_scores = calculate_type_weights(chart)" in draw_source
    assert "_coerce_complete_enneagram_type_scores" in cache_source
    assert "scores = self.calculate_type_weights(chart)" in cache_source
