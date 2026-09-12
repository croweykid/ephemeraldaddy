"""Pure randomized sentence models for aspect Chart Information."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence

from ephemeraldaddy.core.house_definitions import HOUSE_DEFINITIONS
from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    HOUSE_COLORS,
    PLANET_COLORS,
    SIGN_COLORS,
    SIGN_KEYWORDS,
)

ColoredSegment = tuple[str, str | None]
Choice = Callable[[Sequence[str]], str]

DEFAULT_TEXT_COLOR = "#f5f5f5"


def build_aspect_sentence_segments(
    *,
    first_body: str,
    second_body: str,
    aspect_type: str,
    first_body_nouns: Sequence[str],
    second_body_nouns: Sequence[str],
    aspect_keywords: Sequence[str],
    first_sign: str | None,
    second_sign: str | None,
    first_house: int | None,
    second_house: int | None,
    line_count: int = 6,
    max_attempts: int = 300,
    choose: Choice = random.choice,
    default_text_color: str = DEFAULT_TEXT_COLOR,
) -> list[list[ColoredSegment]]:
    """Build unique colorized aspect sentences without reading window state."""
    first_sign_key = str(first_sign or "").strip().title()
    second_sign_key = str(second_sign or "").strip().title()
    first_sign_keywords = SIGN_KEYWORDS.get(first_sign_key, {})
    second_sign_keywords = SIGN_KEYWORDS.get(second_sign_key, {})
    first_sign_adjectives = _nonempty_strings(
        [
            *first_sign_keywords.get("best", []),
            *first_sign_keywords.get("worst", []),
        ]
    )
    second_sign_adjectives = _nonempty_strings(
        [
            *second_sign_keywords.get("best", []),
            *second_sign_keywords.get("worst", []),
        ]
    )
    first_house_nouns = _house_domains(first_house)
    second_house_nouns = _house_domains(second_house)

    first_body_color = PLANET_COLORS.get(first_body, default_text_color)
    second_body_color = PLANET_COLORS.get(second_body, default_text_color)
    first_sign_color = SIGN_COLORS.get(first_sign_key, default_text_color)
    second_sign_color = SIGN_COLORS.get(second_sign_key, default_text_color)
    first_house_color = HOUSE_COLORS.get(str(first_house), default_text_color)
    second_house_color = HOUSE_COLORS.get(str(second_house), default_text_color)
    aspect_color = ASPECT_COLORS.get(aspect_type, default_text_color)

    lines: list[list[ColoredSegment]] = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    attempts = 0
    while len(lines) < max(0, line_count) and attempts < max(0, max_attempts):
        first_noun = str(choose(first_body_nouns)).strip()
        second_noun = str(choose(second_body_nouns)).strip()
        keyword = str(choose(aspect_keywords)).strip()
        first_adjective = _optional_choice(first_sign_adjectives, choose)
        second_adjective = _optional_choice(second_sign_adjectives, choose)
        first_house_noun = _optional_choice(first_house_nouns, choose)
        second_house_noun = _optional_choice(second_house_nouns, choose)
        combination = (
            first_adjective,
            first_noun,
            keyword,
            second_adjective,
            second_noun,
            first_house_noun,
            second_house_noun,
        )
        attempts += 1
        if combination in seen:
            continue
        seen.add(combination)

        segments: list[ColoredSegment] = [("• ", None)]
        if first_house_noun and second_house_noun:
            segments.extend(
                [
                    ("(", None),
                    (first_house_noun, first_house_color),
                    (" & ", None),
                    (second_house_noun, second_house_color),
                    ("): ", None),
                ]
            )
        tokens = [
            (first_adjective, first_sign_color),
            (first_noun, first_body_color),
            (keyword, aspect_color),
            (second_adjective, second_sign_color),
            (second_noun, second_body_color),
        ]
        for index, token in enumerate((token for token in tokens if token[0])):
            if index:
                segments.append((" ", None))
            segments.append(token)
        lines.append(segments)
    return lines


def _nonempty_strings(values: Sequence[object]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _house_domains(house_number: int | None) -> tuple[str, ...]:
    if house_number is None:
        return ()
    return _nonempty_strings(
        HOUSE_DEFINITIONS.get(house_number, {}).get("core_domains", [])
    )


def _optional_choice(values: Sequence[str], choose: Choice) -> str:
    return str(choose(values)).strip() if values else ""
