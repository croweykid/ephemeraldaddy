"""Pure sentence models for body, sign, and house Chart Information."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ephemeraldaddy.core.house_definitions import HOUSE_DEFINITIONS
from ephemeraldaddy.core.interpretations import (
    HOUSE_COLORS,
    PLANET_COLORS,
    PLANET_KEYWORDS,
    SIGN_COLORS,
    SIGN_KEYWORDS,
)

ColoredSegment = tuple[str, str | None]
Choice = Callable[[Sequence[str]], str]
DEFAULT_TEXT_COLOR = "#f5f5f5"


@dataclass(frozen=True, slots=True)
class PositionSentenceModel:
    """Display-ready heading and colorized interpretation sentences."""

    header: str
    lines: tuple[tuple[ColoredSegment, ...], ...]


def build_position_sentence_model(
    body: str,
    sign: str,
    house_number: int | None,
    *,
    choose: Choice = random.choice,
    default_text_color: str = DEFAULT_TEXT_COLOR,
    max_attempts: int = 200,
) -> PositionSentenceModel | None:
    """Build a position interpretation, or ``None`` when reference data is absent."""
    sign_key = str(sign or "").strip().title()
    sign_keywords = SIGN_KEYWORDS.get(sign_key, {})
    adverbs = _strings(
        [
            *sign_keywords.get("best_adverbs", []),
            *sign_keywords.get("worst_adverbs", []),
        ]
    )
    planet_keywords = PLANET_KEYWORDS.get(body, {})
    verbs = _strings(planet_keywords.get("verbs", []))
    verbs_only = _strings(planet_keywords.get("verbsonly", []))
    planet_nouns = _strings(planet_keywords.get("nouns", []))

    body_color = PLANET_COLORS.get(body, default_text_color)
    sign_color = SIGN_COLORS.get(sign_key, default_text_color)
    if house_number is None:
        verb_choices = verbs_only or verbs
        if not (adverbs and verb_choices):
            return None
        lines: list[list[ColoredSegment]] = []
        _add_unique_lines(
            lines,
            seen=set(),
            target_count=6,
            verbs=verb_choices,
            nouns=("",),
            adverbs=adverbs,
            colors=(body_color, None, sign_color),
            choose=choose,
            max_attempts=max_attempts,
        )
        return _model(f"{body} in {sign}", lines)

    sign_verbs = _strings(sign_keywords.get("verbs", []))
    house_domains = _strings(
        HOUSE_DEFINITIONS.get(house_number, {}).get("core_domains", [])
    )
    if not (adverbs and verbs and house_domains and sign_verbs and planet_nouns):
        return None

    house_color = HOUSE_COLORS.get(str(house_number), default_text_color)
    lines = []
    seen: set[tuple[str, str, str]] = set()
    _add_unique_lines(
        lines,
        seen=seen,
        target_count=3,
        verbs=verbs,
        nouns=house_domains,
        adverbs=adverbs,
        colors=(body_color, house_color, sign_color),
        choose=choose,
        max_attempts=max_attempts,
    )
    _add_unique_lines(
        lines,
        seen=seen,
        target_count=6,
        verbs=sign_verbs,
        nouns=planet_nouns,
        adverbs=tuple(f"of {domain}" for domain in house_domains),
        colors=(sign_color, body_color, house_color),
        choose=choose,
        max_attempts=max_attempts,
    )
    return _model(f"{body} in {sign} • House {house_number}", lines)


def _strings(values: Sequence[object]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _add_unique_lines(
    lines: list[list[ColoredSegment]],
    *,
    seen: set[tuple[str, str, str]],
    target_count: int,
    verbs: Sequence[str],
    nouns: Sequence[str],
    adverbs: Sequence[str],
    colors: tuple[str | None, str | None, str | None],
    choose: Choice,
    max_attempts: int,
) -> None:
    attempts = 0
    while len(lines) < target_count and attempts < max(0, max_attempts):
        noun = str(choose(nouns)).strip()
        verb = str(choose(verbs)).strip()
        adverb = str(choose(adverbs)).strip()
        combination = (noun, verb, adverb)
        attempts += 1
        if combination in seen:
            continue
        seen.add(combination)
        segments: list[ColoredSegment] = [("• ", None)]
        for text, color in zip((verb, noun, adverb), colors, strict=True):
            if not text:
                continue
            if len(segments) > 1:
                segments.append((" ", None))
            segments.append((text, color))
        lines.append(segments)


def _model(header: str, lines: list[list[ColoredSegment]]) -> PositionSentenceModel:
    return PositionSentenceModel(
        header=header,
        lines=tuple(tuple(segment for segment in line) for line in lines),
    )
