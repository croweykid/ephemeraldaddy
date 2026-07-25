from ephemeraldaddy.gui.tag_categories import TAG_CATEGORY_OPTIONS, tag_category_display_name


def test_every_configured_tag_category_uses_shared_display_name() -> None:
    for display_name, prefix in TAG_CATEGORY_OPTIONS:
        assert tag_category_display_name(prefix) == display_name


def test_legacy_prefixes_use_canonical_display_names() -> None:
    assert tag_category_display_name("characters") == "Characters Played"
    assert tag_category_display_name("personality") == "Typology"
    assert tag_category_display_name("places") == "Place"


def test_unknown_prefix_gets_readable_fallback() -> None:
    assert tag_category_display_name("custom_category") == "Custom Category"
