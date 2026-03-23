"""Chart-name anagram helpers for Chart View analytics."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.gui.style import DATABASE_ANALYTICS_SUBHEADER_STYLE


@dataclass(frozen=True)
class AnagramsSectionWidgets:
    """References to labels used by the chart-name anagrams analytics section."""

    summary_label: QLabel
    list_label: QLabel


@lru_cache(maxsize=1)
def _anagram_dictionary_words() -> frozenset[str]:
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
    return frozenset(
        {
            "art",
            "arc",
            "car",
            "chart",
            "rat",
            "tar",
            "cat",
            "act",
            "trace",
            "crate",
            "react",
            "cater",
            "caret",
            "earth",
            "heart",
            "hater",
            "listen",
            "silent",
        }
    )


def _collect_chart_name_anagrams(
    chart_name: str,
    *,
    max_results: int = 30,
) -> list[str]:
    letters = [ch for ch in chart_name.casefold() if ch.isalpha()]
    if len(letters) < 3:
        return []
    letters_counter = Counter(letters)
    dictionary_words = _anagram_dictionary_words()
    candidate_words: list[str] = []
    for word in dictionary_words:
        if len(word) > len(letters):
            continue
        word_counts = Counter(word)
        if all(word_counts[char] <= letters_counter.get(char, 0) for char in word_counts):
            candidate_words.append(word)
    candidate_words.sort(key=lambda word: (-len(word), word))
    return candidate_words[:max_results]


def render_anagrams_text(chart_name: str) -> str:
    """Build display text for chart-name anagrams."""
    clean_name = str(chart_name or "").strip()
    if not clean_name:
        return "Chart name is empty; no anagrams available."
    letters = [ch for ch in clean_name.casefold() if ch.isalpha()]
    if len(letters) < 3:
        return "Need at least 3 letters in chart name for anagrams."

    max_permutations_to_scan = 250_000
    permutation_count = math.factorial(len(letters))
    matches = _collect_chart_name_anagrams(clean_name, max_results=30)
    if permutation_count > max_permutations_to_scan:
        unique_letters = len(set(letters))
        return "\n".join(
            [
                f'Chart name: "{clean_name}"',
                f"Letters: {len(letters)} (unique: {unique_letters})",
                f"Raw permutation space: {permutation_count:,} (too large to brute force in UI).",
                "Showing dictionary-matched options from available letters instead:",
                "",
                "\n".join(matches) or "(No matches found.)",
            ]
        )

    return "\n".join(
        [
            f'Chart name: "{clean_name}"',
            f"Letters: {len(letters)}",
            "",
            "Single-word anagrams/sub-anagrams from available letters:",
            ", ".join(matches) if matches else "(None found.)",
        ]
    )


def build_anagrams_section(
    *,
    panel: QWidget,
    layout: QVBoxLayout,
    add_collapsible_section: Callable[..., QVBoxLayout],
    on_toggled: Callable[[bool], None],
) -> AnagramsSectionWidgets:
    """Create the Anagrams collapsible analytics section."""
    section_layout = add_collapsible_section(
        panel=panel,
        layout=layout,
        title="Anagrams",
        expanded=False,
        on_toggled=on_toggled,
        section_key="anagrams",
    )

    summary_label = QLabel(
        "Dictionary-based anagrams for the chart name (single words only, capped for speed)."
    )
    summary_label.setWordWrap(True)
    summary_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    section_layout.addWidget(summary_label)

    list_label = QLabel("Generate or load a chart to scan chart-name letters.")
    list_label.setWordWrap(True)
    list_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    section_layout.addWidget(list_label)
    return AnagramsSectionWidgets(
        summary_label=summary_label,
        list_label=list_label,
    )
