from ephemeraldaddy.gui.tag_categories import (
    TAG_CATEGORY_OPTIONS,
    TAG_DISTRIBUTION_CATEGORY_ALIASES,
    TAG_DISTRIBUTION_CATEGORY_ORDER,
    tag_category_display_name,
)


def test_property_manager_retains_its_original_category_labels() -> None:
    assert ("🧬 Trait", "trait") in TAG_CATEGORY_OPTIONS
    assert ("Characters Played", "character") in TAG_CATEGORY_OPTIONS
    assert ("Typology", "personality_types") in TAG_CATEGORY_OPTIONS


def test_search_retains_its_original_category_labels() -> None:
    assert tag_category_display_name("trait") == "Trait"
    assert tag_category_display_name("character") == "Characters Played"
    assert tag_category_display_name("personality_types") == "Typology"


def test_database_analytics_retains_original_labels_and_aliases() -> None:
    assert "Characters" in TAG_DISTRIBUTION_CATEGORY_ORDER
    assert "Personality" in TAG_DISTRIBUTION_CATEGORY_ORDER
    assert "Places" in TAG_DISTRIBUTION_CATEGORY_ORDER
    assert TAG_DISTRIBUTION_CATEGORY_ALIASES["unknown"] == "Uncategorized"
    assert TAG_DISTRIBUTION_CATEGORY_ALIASES["uncategorized"] == "Uncategorized"


def test_unknown_prefix_gets_readable_fallback() -> None:
    assert tag_category_display_name("custom_category") == "Custom Category"
