"""Helpers for generating aspect interpretation sentences."""

from __future__ import annotations

import random

from ephemeraldaddy.core.interpretations import HOUSE_KEYWORDS, SIGN_KEYWORDS


def _sign_adjective_candidates(sign: str | None) -> list[str]:
    """Return adjective candidates for a sign using SIGN_KEYWORDS best+worst lists."""
    if not sign:
        return []
    sign_entry = SIGN_KEYWORDS.get(str(sign).strip().lower(), {})
    best = sign_entry.get("best", [])
    worst = sign_entry.get("worst", [])
    candidates = [word for word in [*best, *worst] if isinstance(word, str) and word.strip()]
    return [candidate.strip() for candidate in candidates]


def build_aspect_interpretation_lines(
    *,
    p1_nouns: list[str],
    p2_nouns: list[str],
    aspect_keywords: list[str],
    sign1: str | None,
    sign2: str | None,
    house1: int | None,
    house2: int | None,
    line_count: int = 6,
    max_attempts: int = 300,
) -> list[str]:
    """Build unique human-readable aspect interpretation lines."""
    sign1_adjectives = _sign_adjective_candidates(sign1)
    sign2_adjectives = _sign_adjective_candidates(sign2)
    house1_keywords = HOUSE_KEYWORDS.get(house1, []) if house1 else []
    house2_keywords = HOUSE_KEYWORDS.get(house2, []) if house2 else []

    unique_lines: list[str] = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    attempts = 0

    while len(unique_lines) < line_count and attempts < max_attempts:
        noun1 = random.choice(p1_nouns)
        noun2 = random.choice(p2_nouns)
        keyword = random.choice(aspect_keywords)
        sign1_adj = random.choice(sign1_adjectives) if sign1_adjectives else ""
        sign2_adj = random.choice(sign2_adjectives) if sign2_adjectives else ""
        house_noun1 = random.choice(house1_keywords) if house1_keywords else ""
        house_noun2 = random.choice(house2_keywords) if house2_keywords else ""

        combo = (
            sign1_adj,
            noun1,
            keyword,
            sign2_adj,
            noun2,
            house_noun1,
            house_noun2,
        )
        if combo in seen:
            attempts += 1
            continue
        seen.add(combo)

        tokens = [token for token in (sign1_adj, noun1, keyword, sign2_adj, noun2) if token]
        sentence = " ".join(tokens)
        if house_noun1 and house_noun2:
            sentence += f" in regards to {house_noun1} & {house_noun2}"
        unique_lines.append(sentence)
        attempts += 1

    return unique_lines
