from pathlib import Path


def test_manual_completion_is_only_offered_after_wikipedia_returns_no_birthplace():
    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    start = source.index("def _on_import_astrotheme_from_search_panel")
    end = source.index("def _on_get_bio_for_open_chart", start)
    method = source[start:end]

    astrotheme_lookup = method.index("parse_astrotheme_profile(query)")
    wikipedia_offer = method.index("cannot be found on Astrotheme - trying Wikipedia")
    wikipedia_lookup = method.index("resolve_wikipedia_page_options(raw_query)")
    wikipedia_parse = method.index("parse_wikipedia_birth_data(selected_title)")
    missing_birthplace = method.index('if not birth_place:')
    manual_offer = method.index("confirm_manual_wikipedia_import(self, selected_title)")

    assert (
        astrotheme_lookup
        < wikipedia_offer
        < wikipedia_lookup
        < wikipedia_parse
        < missing_birthplace
        < manual_offer
    )
    assert method.count("confirm_manual_wikipedia_import(") == 1
