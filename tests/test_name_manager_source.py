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


def test_name_manager_resolves_name_rows_and_matches_through_chart_uids():
    chart_names_source = PROPERTY_MANAGER.split("def chart_names", 1)[1]
    names_branch = chart_names_source.split(
        "if field == ManageMetadataLabelsDialog.FIELD_NAMES:", 1
    )[1].split("for row in rows:", 1)[0]
    assert "get_chart_uid_map" in names_branch
    assert "_get_chart_for_filter_by_uid" in names_branch
