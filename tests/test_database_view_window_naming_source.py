import ast
from pathlib import Path


APP_PATH = Path("ephemeraldaddy/gui/app.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")


def test_database_view_uses_its_canonical_window_class_name():
    module = ast.parse(APP_SOURCE)

    assert any(
        isinstance(node, ast.ClassDef) and node.name == "DatabaseViewWindow"
        for node in module.body
    )
    assert not any(
        isinstance(node, ast.ClassDef) and node.name == "ManageChartsDialog"
        for node in module.body
    )


def test_legacy_database_window_name_is_only_a_compatibility_alias():
    module = ast.parse(APP_SOURCE)
    legacy_name_nodes = [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Name) and node.id == "ManageChartsDialog"
    ]

    assert len(legacy_name_nodes) == 1
    alias = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "ManageChartsDialog"
            for target in node.targets
        )
    )
    assert isinstance(alias.value, ast.Name)
    assert alias.value.id == "DatabaseViewWindow"
