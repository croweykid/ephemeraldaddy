"""Pure anagram calculation helpers for Chart View."""

from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache

_FALLBACK_DICTIONARY_WORDS: frozenset[str] = frozenset(
    {
        "about",
        "above",
        "ace",
        "act",
        "actor",
        "age",
        "air",
        "alert",
        "alien",
        "alter",
        "angel",
        "anger",
        "angle",
        "ant",
        "arc",
        "arch",
        "are",
        "area",
        "art",
        "artist",
        "ash",
        "ask",
        "ate",
        "aunt",
        "aura",
        "bar",
        "bare",
        "bear",
        "beat",
        "being",
        "below",
        "belt",
        "best",
        "beta",
        "binary",
        "bird",
        "birth",
        "bite",
        "blue",
        "bone",
        "born",
        "brain",
        "brave",
        "bread",
        "break",
        "bring",
        "broad",
        "care",
        "caret",
        "car",
        "cart",
        "cater",
        "cat",
        "chart",
        "cheat",
        "clear",
        "cone",
        "core",
        "crate",
        "date",
        "deal",
        "dear",
        "demon",
        "dine",
        "dream",
        "dust",
        "earth",
        "east",
        "eat",
        "elan",
        "end",
        "era",
        "evil",
        "faith",
        "fate",
        "fire",
        "flow",
        "form",
        "gain",
        "gate",
        "gear",
        "ghost",
        "gold",
        "grace",
        "great",
        "hair",
        "hate",
        "hater",
        "heart",
        "heat",
        "hero",
        "hope",
        "idea",
        "iron",
        "karma",
        "kind",
        "king",
        "lane",
        "late",
        "lead",
        "lean",
        "learn",
        "least",
        "line",
        "listen",
        "live",
        "lone",
        "love",
        "lover",
        "maker",
        "mars",
        "mean",
        "mind",
        "moon",
        "moral",
        "more",
        "muse",
        "name",
        "near",
        "night",
        "note",
        "ocean",
        "omen",
        "one",
        "open",
        "oracle",
        "planet",
        "poet",
        "power",
        "quiet",
        "race",
        "rat",
        "react",
        "read",
        "realm",
        "rise",
        "road",
        "rose",
        "sacred",
        "sage",
        "said",
        "sale",
        "sat",
        "scale",
        "seal",
        "seat",
        "shine",
        "sign",
        "silent",
        "singer",
        "solar",
        "soul",
        "star",
        "stone",
        "story",
        "sun",
        "tar",
        "tea",
        "tone",
        "trace",
        "trade",
        "trial",
        "true",
        "user",
        "veil",
        "venus",
        "vision",
        "water",
        "wise",
        "word",
        "world",
        "writer",
    }
)


@lru_cache(maxsize=1)
def anagram_dictionary_words() -> frozenset[str]:
    """Return dictionary words from the host OS, with a bundled fallback."""
    paths = (
        "/usr/share/dict/words",
        "/usr/dict/words",
    )
    words: set[str] = set()
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    raw_word = raw_line.strip().casefold()
                    if not raw_word.isalpha():
                        continue
                    if len(raw_word) < 3:
                        continue
                    words.add(raw_word)
        except OSError:
            continue
    if words:
        return frozenset(words)
    return _FALLBACK_DICTIONARY_WORDS


def collect_chart_name_anagrams(
    chart_name: str,
    *,
    max_results: int = 30,
) -> list[str]:
    letters = [ch for ch in chart_name.casefold() if ch.isalpha()]
    if len(letters) < 3:
        return []
    letters_counter = Counter(letters)
    dictionary_words = anagram_dictionary_words()
    candidate_words: list[str] = []
    for word in dictionary_words:
        if len(word) > len(letters):
            continue
        word_counts = Counter(word)
        if all(word_counts[char] <= letters_counter.get(char, 0) for char in word_counts):
            candidate_words.append(word)
    candidate_words.sort(key=lambda word: (-len(word), word))
    return candidate_words[:max_results]


def render_anagrams_text(chart_text: str, *, subject_label: str = "Chart name") -> str:
    """Build display text for chart-name/chart-alias anagrams."""
    clean_name = str(chart_text or "").strip()
    if not clean_name:
        return f"{subject_label} is empty; no anagrams available."
    letters = [ch for ch in clean_name.casefold() if ch.isalpha()]
    if len(letters) < 3:
        return f"Need at least 3 letters in {subject_label.lower()} for anagrams."

    max_permutations_to_scan = 250_000
    permutation_count = math.factorial(len(letters))
    matches = collect_chart_name_anagrams(clean_name, max_results=30)
    if permutation_count > max_permutations_to_scan:
        unique_letters = len(set(letters))
        return "\n".join(
            [
                f'{subject_label}: "{clean_name}"',
                f"Letters: {len(letters)} (unique: {unique_letters})",
                f"Raw permutation space: {permutation_count:,} (too large to brute force in UI).",
                "Showing dictionary-matched options from available letters instead:",
                "",
                "\n".join(matches) or "(No matches found.)",
            ]
        )

    return "\n".join(
        [
            f'{subject_label}: "{clean_name}"',
            f"Letters: {len(letters)}",
            "",
            "Single-word anagrams/sub-anagrams from available letters:",
            ", ".join(matches) if matches else "(None found.)",
        ]
    )


def collect_anagram_words(chart_text: str, *, max_results: int = 30) -> list[str]:
    """Return capped dictionary matches for the provided text."""
    clean_name = str(chart_text or "").strip()
    if not clean_name:
        return []
    return collect_chart_name_anagrams(clean_name, max_results=max_results)
