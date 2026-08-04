from pathlib import Path


SOURCE = Path("ephemeraldaddy/gui/features/charts/database_analytics.py").read_text()


def test_tags_uses_parent_section_header_hierarchy():
    branch = SOURCE.split("def _create_tags_database_analytics_section", 1)[1].split(
        "def _create_traits_database_analytics_section", 1
    )[0]

    assert "nested=True" in branch
    assert "hierarchy_level=COLLAPSIBLE_HEADER_LEVEL_PARENT" in branch
