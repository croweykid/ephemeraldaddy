import ast
from pathlib import Path


STYLE_SOURCE = Path("ephemeraldaddy/gui/style.py")


def _wiggle_function() -> ast.FunctionDef:
    module = ast.parse(STYLE_SOURCE.read_text())
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_run_collapsible_header_wiggle":
            return node
    raise AssertionError("_run_collapsible_header_wiggle was not found")


def test_collapsible_header_wiggle_initializes_origin_before_reuse_branch():
    function = _wiggle_function()

    assert isinstance(function.body[1], ast.Assign)
    assert any(
        isinstance(target, ast.Name) and target.id == "origin"
        for target in function.body[1].targets
    )


def test_collapsible_header_wiggle_animation_runs_for_all_layout_directions():
    function = _wiggle_function()
    animation_assignment_index = next(
        index
        for index, node in enumerate(function.body)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "animation"
            for target in node.targets
        )
    )

    for node in ast.walk(function):
        if isinstance(node, ast.If):
            assert function.body[animation_assignment_index] not in node.body
