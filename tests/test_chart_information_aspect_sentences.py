import random

from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    HOUSE_COLORS,
    PLANET_COLORS,
    SIGN_COLORS,
)
from ephemeraldaddy.gui.features.chart_information.aspect_sentences import (
    build_aspect_sentence_segments,
)


def test_aspect_sentences_include_colorized_body_sign_house_and_aspect_tokens():
    lines = build_aspect_sentence_segments(
        first_body="Sun",
        second_body="Moon",
        aspect_type="conjunction",
        first_body_nouns=["identity"],
        second_body_nouns=["emotion"],
        aspect_keywords=["fuses"],
        first_sign="Aries",
        second_sign="Cancer",
        first_house=1,
        second_house=4,
        line_count=1,
        choose=lambda values: values[0],
    )

    assert len(lines) == 1
    segments = lines[0]
    assert segments[0] == ("• ", None)
    assert any(color == PLANET_COLORS["Sun"] for _text, color in segments)
    assert any(color == PLANET_COLORS["Moon"] for _text, color in segments)
    assert any(color == SIGN_COLORS["Aries"] for _text, color in segments)
    assert any(color == SIGN_COLORS["Cancer"] for _text, color in segments)
    assert any(color == HOUSE_COLORS["1"] for _text, color in segments)
    assert any(color == HOUSE_COLORS["4"] for _text, color in segments)
    assert any(color == ASPECT_COLORS["conjunction"] for _text, color in segments)


def test_aspect_sentences_are_unique_and_bounded_by_requested_count():
    chooser = random.Random(42).choice

    lines = build_aspect_sentence_segments(
        first_body="Sun",
        second_body="Moon",
        aspect_type="trine",
        first_body_nouns=["identity", "purpose"],
        second_body_nouns=["emotion", "instinct"],
        aspect_keywords=["supports", "harmonizes"],
        first_sign=None,
        second_sign=None,
        first_house=None,
        second_house=None,
        line_count=6,
        choose=chooser,
    )

    assert len(lines) == 6
    assert len({tuple(line) for line in lines}) == 6
    assert all(line[0] == ("• ", None) for line in lines)


def test_aspect_sentences_stop_when_only_one_combination_exists():
    lines = build_aspect_sentence_segments(
        first_body="Unknown A",
        second_body="Unknown B",
        aspect_type="unknown",
        first_body_nouns=["one"],
        second_body_nouns=["two"],
        aspect_keywords=["meets"],
        first_sign=None,
        second_sign=None,
        first_house=None,
        second_house=None,
        line_count=6,
        max_attempts=10,
        choose=lambda values: values[0],
        default_text_color="#abcdef",
    )

    assert len(lines) == 1
    assert [segment for segment in lines[0] if segment[1] == "#abcdef"] == [
        ("one", "#abcdef"),
        ("meets", "#abcdef"),
        ("two", "#abcdef"),
    ]
