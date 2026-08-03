from pathlib import Path


DEV_TOOLS = Path("ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")
PROPERTY_MANAGER = Path("ephemeraldaddy/gui/property_manager.py").read_text(encoding="utf-8")


def test_property_manager_exposes_name_manager_with_name_and_frequency_columns():
    assert '("Names", self.FIELD_NAMES)' in DEV_TOOLS
    assert 'setHeaderLabels(["Name", "Frequency"])' in DEV_TOOLS
    assert 'self.FIELD_NAMES: "Charts with selected name or alias"' in DEV_TOOLS


def test_name_manager_suppresses_tokens_without_rewriting_chart_metadata():
    assert "suppress_name_tokens([old_label])" in PROPERTY_MANAGER
    assert 'field != ManageMetadataLabelsDialog.FIELD_NAMES' in PROPERTY_MANAGER
    assert "Chart names and aliases will not be edited." in DEV_TOOLS
