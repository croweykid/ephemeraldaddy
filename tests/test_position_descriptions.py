from ephemeraldaddy.core.position_descriptions import get_position_description


def test_position_description_lookup_normalizes_body_and_sign() -> None:
    description = get_position_description(" Moon ", "ARIES")

    assert description is not None
    assert description.startswith("An Aries Moon")


def test_position_description_lookup_allows_generic_fallback() -> None:
    assert get_position_description("Sun", "Aries") is None
    assert get_position_description("Moon", "Not a sign") is None


def test_chart_info_checks_curated_prose_before_generic_keywords() -> None:
    with open("ephemeraldaddy/gui/app.py", encoding="utf-8") as app_file:
        source = app_file.read()

    method_start = source.index("    def _show_sign_keyword_info(")
    method_end = source.index("\n    def _show_element_keyword_info(", method_start)
    method_source = source[method_start:method_end]

    prose_lookup = method_source.index("get_position_description(body_key, sign_key)")
    generic_theme = method_source.index("DOMINANT_BODY_MEANINGS.get(body_key")
    assert prose_lookup < generic_theme
