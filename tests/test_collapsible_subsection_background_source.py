from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (ROOT / "ephemeraldaddy/gui/style.py").read_text()
SEARCH_SOURCE = (ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text()
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_subsection_background_has_distinct_dark_purple_style():
    assert 'COLLAPSIBLE_SECTION_BACKGROUND = "#050505"' in STYLE_SOURCE
    assert 'COLLAPSIBLE_SUBSECTION_BACKGROUND = "#16071f"' in STYLE_SOURCE
    assert "COLLAPSIBLE_SUBSECTION_CONTENT_STYLE" in STYLE_SOURCE


def test_database_search_sections_accept_subsection_flag():
    assert "title: str, *, subsection: bool = False" in SEARCH_SOURCE
    assert "COLLAPSIBLE_SUBSECTION_CONTENT_STYLE" in SEARCH_SOURCE
    assert "if subsection" in SEARCH_SOURCE


def test_database_search_top_categories_are_not_subsections():
    for title in ("Astro", "Human Design", "Interactions", "Predictions", "Demographics"):
        assert f'add_collapsible_section("{title}")' in SEARCH_SOURCE
        assert f'add_collapsible_section("{title}", subsection=True)' not in SEARCH_SOURCE


def test_database_search_nested_sections_are_subsections():
    for title in ("🪐Positions", "🪐Decans", "💭Sentiment", "Lifespan", "Notes"):
        assert f'add_collapsible_section("{title}", subsection=True)' in SEARCH_SOURCE
    assert '"Data Quality", #data icon contenders:' in SEARCH_SOURCE
    assert 'subsection=True' in SEARCH_SOURCE


def test_batch_editor_nested_tag_picker_uses_subsection_background():
    assert "self.batch_tags_list_widget.setStyleSheet(COLLAPSIBLE_SUBSECTION_CONTENT_STYLE)" in APP_SOURCE
