from pathlib import Path


def test_command_palette_module_and_shortcuts_are_wired():
    module = Path("ephemeraldaddy/gui/cmd_pallette.py").read_text()
    app = Path("ephemeraldaddy/gui/app.py").read_text()

    assert "class CommandPaletteDialog" in module
    assert "class CommandPaletteAction" in module
    assert 'QKeySequence("Ctrl+K")' in module
    assert 'QKeySequence("Meta+K")' in module
    assert "install_command_palette(self, self._command_palette_actions)" in app


def test_command_palette_includes_core_quick_switcher_commands():
    app = Path("ephemeraldaddy/gui/app.py").read_text()

    for command in [
        '"Search"',
        '"New chart"',
        '"Open Human Design"',
        '"Show Database Analytics"',
        '"Export selected"',
        '"Settings"',
        '"Create Gemstone Chart"',
    ]:
        assert command in app
