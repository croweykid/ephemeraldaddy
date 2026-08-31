from pathlib import Path


def test_plugin_can_be_disabled_and_reenabled_without_deleting_it(monkeypatch, tmp_path):
    from ephemeraldaddy.analysis import human_design_plugins as plugins

    plugin_dir = tmp_path / "plugins"
    disabled_dir = plugin_dir / "disabled"
    monkeypatch.setattr(plugins, "PLUGIN_DIR", plugin_dir)
    monkeypatch.setattr(plugins, "DISABLED_PLUGIN_DIR", disabled_dir)
    enabled_path = plugin_dir / plugins.RECOGNIZED_PLUGIN_FILENAMES[0]
    enabled_path.parent.mkdir(parents=True)
    enabled_path.write_text("{}", encoding="utf-8")

    disabled_path = plugins.set_plugin_enabled(enabled_path.name, False)
    assert disabled_path == disabled_dir / enabled_path.name
    assert plugins.plugin_installations() == [
        {"name": enabled_path.name, "enabled": False, "path": disabled_path}
    ]
    assert not enabled_path.exists()

    restored_path = plugins.set_plugin_enabled(enabled_path.name, True)
    assert restored_path == enabled_path
    assert restored_path.exists()
    assert not disabled_path.exists()


def test_settings_places_presets_traits_and_plugin_manager_in_requested_tabs():
    root = Path(__file__).resolve().parents[1]
    app_source = (root / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    plugin_source = (root / "ephemeraldaddy/gui/settings/modules/plugins.py").read_text(encoding="utf-8")

    assert 'astro_twin_tabs.addTab(presets_tab, "Astro Twin Presets Manager")' in app_source
    assert 'property_tabs.addTab(traits_widget, "Traits")' in app_source
    assert 'QGroupBox("Upload Panel")' in app_source
    assert 'heading = QLabel("Plugin Manager")' in plugin_source
    assert '["Plugin", "Status", "File location"]' in plugin_source
    assert '"✓ Enabled" if enabled else "✕ Disabled"' in plugin_source
    assert 'self.toggle_button.setText("Disable" if enabled else "Enable")' in plugin_source
    assert 'f"Open Folder in {_file_browser_name()}"' in plugin_source
