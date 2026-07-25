from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/ranking_panel.py").read_text(
    encoding="utf-8"
)
STYLE_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/style.py").read_text(
    encoding="utf-8"
)


def test_ranking_traits_are_alphabetized_without_grouping_bundled_traits_first():
    sync_method = SOURCE.split("def _sync_rankings_trait_combo", 1)[1].split(
        "def _rankings_trait_likelihood_cache_complete", 1
    )[0]

    assert "active_traits.sort" in sync_method
    assert ".casefold()" in sync_method
    assert sync_method.index("active_traits.sort") < sync_method.index("for trait in active_traits")


def test_ranking_traits_distinguish_default_and_add_on_names_by_color():
    sync_method = SOURCE.split("def _sync_rankings_trait_combo", 1)[1].split(
        "def _rankings_trait_likelihood_cache_complete", 1
    )[0]

    assert 'DROPDOWN_MUTED_ITEM_TEXT_COLOR = "#cfcfcf"' in STYLE_SOURCE
    assert 'DROPDOWN_ACCENT_ITEM_TEXT_COLOR = "#ff9f1c"' in STYLE_SOURCE
    assert "def set_dropdown_item_text_color" in STYLE_SOURCE
    assert 'trait.get("bundled", False)' in sync_method
    assert "set_dropdown_item_text_color(combo, combo.count() - 1, name_color)" in sync_method
