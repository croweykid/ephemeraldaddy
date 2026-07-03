from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (ROOT / "ephemeraldaddy/gui/style.py").read_text()
SEARCH_SOURCE = (ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text()
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_nested_section_background_has_distinct_dark_purple_style():
    assert 'COLLAPSIBLE_SECTION_BACKGROUND = "#050505"' in STYLE_SOURCE
    assert 'COLLAPSIBLE_NESTED_SECTION_BACKGROUND = "#16071f"' in STYLE_SOURCE
    assert "COLLAPSIBLE_NESTED_SECTION_CONTENT_STYLE" in STYLE_SOURCE


def test_collapsible_headers_use_appwide_charcoal_background():
    assert 'COLLAPSIBLE_HEADER_BACKGROUND = "#222222"' in STYLE_SOURCE
    assert "background_color: str = COLLAPSIBLE_HEADER_BACKGROUND" in STYLE_SOURCE


def test_database_search_sections_accept_nested_flag():
    assert "title: str, *, nested: bool = False" in SEARCH_SOURCE
    assert "COLLAPSIBLE_NESTED_SECTION_CONTENT_STYLE" in SEARCH_SOURCE
    assert "if nested" in SEARCH_SOURCE


def test_database_search_top_categories_are_nested_sections():
    for title in ("Astro", "Human Design", "Interactions", "Predictions", "Demographics"):
        assert f'add_collapsible_section("{title}", nested=True)' in SEARCH_SOURCE


def test_database_search_subsections_use_standard_section_background():
    for title in ("🪐Positions", "🪐Decans", "💭Sentiment", "Lifespan", "Notes"):
        assert f'add_collapsible_section("{title}", nested=True)' not in SEARCH_SOURCE
        assert f'add_collapsible_section("{title}")' in SEARCH_SOURCE
    assert 'nested=True' in SEARCH_SOURCE


def test_batch_editor_nested_tag_picker_keeps_subsection_list_standard_black():
    assert 'add_collapsible_section("🏷️Tagging", nested=True)' in APP_SOURCE
    assert "self.batch_tags_list_widget.setStyleSheet(COLLAPSIBLE_SECTION_CONTENT_STYLE)" in APP_SOURCE
