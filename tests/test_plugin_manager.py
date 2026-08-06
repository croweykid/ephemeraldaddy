from pathlib import Path

from ephemeraldaddy.analysis import human_design_plugins as plugins


def test_plugin_can_be_disabled_and_reenabled(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    disabled_dir = plugin_dir / "disabled"
    monkeypatch.setattr(plugins, "PLUGIN_DIR", plugin_dir)
    monkeypatch.setattr(plugins, "DISABLED_PLUGIN_DIR", disabled_dir)

    enabled_path = plugin_dir / plugins.RECOGNIZED_PLUGIN_FILENAMES[0]
    enabled_path.parent.mkdir(parents=True)
    enabled_path.write_text("{}", encoding="utf-8")

    disabled_path = plugins.set_plugin_enabled(enabled_path.name, False)
    assert disabled_path == disabled_dir / enabled_path.name
    assert plugins.plugin_installation_rows() == [
        {"name": enabled_path.name, "enabled": False, "path": disabled_path}
    ]

    restored_path = plugins.set_plugin_enabled(enabled_path.name, True)
    assert restored_path == enabled_path
    assert plugins.plugin_installation_rows() == [
        {"name": enabled_path.name, "enabled": True, "path": enabled_path}
    ]


def test_plugin_settings_has_separate_upload_and_manager_panels():
    source = Path("ephemeraldaddy/gui/features/settings/plugins.py").read_text(encoding="utf-8")

    assert 'QGroupBox("Upload Panel")' in source
    assert 'QGroupBox("Plugin Manager")' in source
    assert '["Plugin Name", "Status", "File Location", "Enable / Disable", "Install Folder"]' in source
    assert '"✓ Enabled" if enabled else "✕ Disabled"' in source
    assert 'return "Open Folder in Finder"' in source
    assert 'return "Open Folder in Explorer"' in source
