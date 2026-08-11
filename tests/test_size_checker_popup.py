import ast
from pathlib import Path


def test_size_checker_popup_imports_shared_button_cursor_helper():
    source = Path("ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")
    module = ast.parse(source)

    style_imports = {
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "ephemeraldaddy.gui.style"
        for alias in node.names
    }

    assert "apply_button_cursor" in style_imports
