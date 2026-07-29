import ast
from pathlib import Path


APP_PATH = Path(__file__).parents[1] / "ephemeraldaddy" / "gui" / "app.py"


def _imported_names(module_name: str) -> set[str]:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == module_name
        for alias in node.names
    }


def test_database_view_collection_filter_imports_every_referenced_collection_constant():
    imported_names = _imported_names("ephemeraldaddy.gui.features.charts.collections")
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    referenced_collection_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id.startswith("DEFAULT_COLLECTION_")
    }

    assert referenced_collection_names <= imported_names


def test_database_view_personal_collection_filter_imports_parasocial_source():
    imported_names = _imported_names("ephemeraldaddy.gui.features.charts.provenance")

    assert "SOURCE_PARASOCIAL" in imported_names
