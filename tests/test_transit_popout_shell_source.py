from pathlib import Path


def test_shared_transit_popout_shell_owns_requested_tabs_and_defaults() -> None:
    source = Path(
        "ephemeraldaddy/gui/features/transits/popout_shell.py"
    ).read_text(encoding="utf-8")

    assert 'left_tabs.addTab(chart_page, "Chart Drawing")' in source
    assert 'left_tabs.addTab(aspects_page, "Aspects")' in source
    assert "left_tabs.setCurrentWidget(aspects_page)" in source

    assert "main_tabs.setTabPosition(QTabWidget.TabPosition.West)" in source
    assert 'main_tabs.addTab(table_page, "Table View")' in source
    assert 'main_tabs.addTab(theme_page, "Theme View")' in source
    assert "main_tabs.setCurrentWidget(table_page)" in source


def test_shared_transit_popout_shell_is_owned_by_transits_feature_package() -> None:
    source = Path(
        "ephemeraldaddy/gui/features/transits/popout_shell.py"
    ).read_text(encoding="utf-8")

    assert "Personal Transit" in source
    assert "Global Transit" in source
    assert "gui.features.charts" not in source
