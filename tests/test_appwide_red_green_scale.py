import ast
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_STYLE_PATH = _REPOSITORY_ROOT / "ephemeraldaddy/gui/style.py"
_STYLE_NAMES = {
    "APPWIDE_RED_GREEN_SCALE_LESS_RGB",
    "APPWIDE_RED_GREEN_SCALE_MORE_RGB",
    "_interpolate_rgb_channel",
    "appwide_red_green_rgb_from_ratio",
    "appwide_red_green_rgb_for_range",
}


def _load_scale_namespace() -> dict[str, object]:
    tree = ast.parse(_STYLE_PATH.read_text(encoding="utf-8"))
    selected_nodes = [
        node
        for node in tree.body
        if (
            isinstance(node, (ast.FunctionDef, ast.Assign))
            and any(name in _STYLE_NAMES for name in _defined_names(node))
        )
    ]
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=selected_nodes, type_ignores=[]), str(_STYLE_PATH), "exec"), namespace)
    return namespace


def _defined_names(node: ast.stmt) -> set[str]:
    if isinstance(node, ast.FunctionDef):
        return {node.name}
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    return set()


_SCALE = _load_scale_namespace()
APPWIDE_RED_GREEN_SCALE_LESS_RGB = _SCALE["APPWIDE_RED_GREEN_SCALE_LESS_RGB"]
APPWIDE_RED_GREEN_SCALE_MORE_RGB = _SCALE["APPWIDE_RED_GREEN_SCALE_MORE_RGB"]
appwide_red_green_rgb_from_ratio = _SCALE["appwide_red_green_rgb_from_ratio"]
appwide_red_green_rgb_for_range = _SCALE["appwide_red_green_rgb_for_range"]


def test_appwide_red_green_scale_endpoints_and_clamping() -> None:
    assert appwide_red_green_rgb_from_ratio(0.0) == APPWIDE_RED_GREEN_SCALE_LESS_RGB
    assert appwide_red_green_rgb_from_ratio(1.0) == APPWIDE_RED_GREEN_SCALE_MORE_RGB
    assert appwide_red_green_rgb_from_ratio(-1.0) == APPWIDE_RED_GREEN_SCALE_LESS_RGB
    assert appwide_red_green_rgb_from_ratio(2.0) == APPWIDE_RED_GREEN_SCALE_MORE_RGB


def test_appwide_red_green_scale_maps_ranges() -> None:
    assert appwide_red_green_rgb_for_range(10.0, 10.0, 20.0) == APPWIDE_RED_GREEN_SCALE_LESS_RGB
    assert appwide_red_green_rgb_for_range(20.0, 10.0, 20.0) == APPWIDE_RED_GREEN_SCALE_MORE_RGB
    assert appwide_red_green_rgb_for_range(10.0, 10.0, 10.0) == APPWIDE_RED_GREEN_SCALE_LESS_RGB


def test_quantitative_ui_consumers_use_the_appwide_scale() -> None:
    consumer_paths = (
        "ephemeraldaddy/gui/app.py",
        "ephemeraldaddy/gui/dev_tools.py",
        "ephemeraldaddy/gui/features/charts/trait_predictions.py",
        "ephemeraldaddy/gui/features/controllers/db_info.py",
    )

    for relative_path in consumer_paths:
        source = (_REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert "appwide_red_green_rgb_for_range" in source
        assert "similarity_gradient_rgb_for_range" not in source
