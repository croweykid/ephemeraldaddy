from pathlib import Path


DEV_TOOLS_SOURCE = Path("ephemeraldaddy/gui/dev_tools.py").read_text()
STYLE_SOURCE = Path("ephemeraldaddy/gui/style.py").read_text()


def test_property_manager_uses_shared_settings_tab_style() -> None:
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]

    assert "SETTINGS_TAB_STYLE" in STYLE_SOURCE
    assert "self._field_tabs = QTabBar(self)" in dialog_source
    assert "self._field_tabs.setStyleSheet(SETTINGS_TAB_STYLE)" in dialog_source
    assert 'tabs.setStyleSheet(SETTINGS_TAB_STYLE)' in DEV_TOOLS_SOURCE


def test_property_manager_tabs_have_requested_order_and_labels() -> None:
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]
    options_source = dialog_source.split("field_options = [", 1)[1].split("]", 1)[0]

    labels = ["Relationships", "Sentiments", "Collections", "Tags"]
    positions = [options_source.index(f'(\"{label}\",') for label in labels]
    assert positions == sorted(positions)
    assert "Manager" not in options_source
