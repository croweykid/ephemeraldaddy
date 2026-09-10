from ephemeraldaddy.core.theme_reference import (
    DEFAULT_THEME_ITEM_WEIGHT,
    THEME_ENTRY_KEYS,
    THEME_FAMILIES,
    THEMES,
    WEIGHTED_THEME_PROPERTIES,
    theme_item_weight,
    themes_in_family,
    validate_theme_reference,
)


def test_theme_reference_schema_is_uniform():
    validate_theme_reference()
    assert THEMES
    for theme in THEMES.values():
        assert frozenset(theme) == THEME_ENTRY_KEYS
        assert theme["family"] in THEME_FAMILIES


def test_imagination_family_uses_expanded_perspective_label():
    assert (
        THEME_FAMILIES["imagination_expanded_perspective"]["label"]
        == "Imagination & Expanded Perspective"
    )


def test_listed_items_default_to_weight_one():
    assert DEFAULT_THEME_ITEM_WEIGHT == 1.0
    assert theme_item_weight("confinement_escape", "houses", 12) == 1.0
    assert theme_item_weight("dogma_faith", "bodies", "Jupiter") == 1.0


def test_unlisted_items_have_zero_theme_membership():
    assert theme_item_weight("confinement_escape", "houses", 10) == 0.0
    assert theme_item_weight("dogma_faith", "bodies", "Mars") == 0.0


def test_aspects_are_not_theme_membership_properties():
    assert "aspects" not in WEIGHTED_THEME_PROPERTIES
    for theme in THEMES.values():
        assert "aspects" not in theme


def test_family_grouping_is_data_driven():
    grouped = themes_in_family("change_boundaries_disappearance")
    assert "confinement_escape" in grouped
    assert grouped["confinement_escape"]["label"] == "Confinement & Escape"
