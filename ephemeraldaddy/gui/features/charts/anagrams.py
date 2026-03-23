"""Chart-name anagram helpers for Chart View analytics."""

from __future__ import annotations

import math
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget
from PySide6.QtWidgets import QHBoxLayout, QToolButton

from ephemeraldaddy.gui.style import (
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
)


ANAGRAM_SOURCE_OPTIONS: list[tuple[str, str]] = [
    ("Chart Name", "name"),
    ("Chart Alias", "alias"),
]
ANAGRAM_SOURCE_LABELS: dict[str, str] = {
    source_value: source_label for source_label, source_value in ANAGRAM_SOURCE_OPTIONS
}
DEFINITION_HTTP_HEADERS = {
    "User-Agent": "ephemeraldaddy/1.0 (+https://github.com/ephemeraldaddy/ephemeraldaddy)",
    "Accept": "application/json",
}
DEFINITION_CONNECTIVITY_ERROR_CODES = {401, 403, 407, 429, 500, 502, 503, 504}
_DEFINITION_HTTP_SESSION = requests.Session()


@dataclass(frozen=True)
class AnagramsSectionWidgets:
    """References to labels used by the chart-name anagrams analytics section."""

    summary_label: QLabel
    list_label: QLabel
    export_button: QToolButton
    source_dropdown: QComboBox


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
    matches = _collect_chart_name_anagrams(clean_name, max_results=30)
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
    return _collect_chart_name_anagrams(clean_name, max_results=max_results)


def render_anagrams_html(
    chart_text: str,
    words: list[str],
    definitions: dict[str, str],
    *,
    subject_label: str = "Chart name",
) -> str:
    """Build rich HTML view with clickable words and optional definition snippets."""
    clean_name = str(chart_text or "").strip()
    if not clean_name:
        return f"{subject_label} is empty; no anagrams available."
    letters = [ch for ch in clean_name.casefold() if ch.isalpha()]
    if len(letters) < 3:
        return f"Need at least 3 letters in {subject_label.lower()} for anagrams."
    if not words:
        return (
            f"{subject_label}: \"{clean_name}\"<br>"
            f"Letters: {len(letters)}<br><br>"
            "No dictionary matches found."
        )
    rendered: list[str] = []
    for word in words:
        word_link = (
            f'<a href="define:{urllib.parse.quote(word)}" '
            f'style="color: #9dd8ff; text-decoration: none;">{word}</a>'
        )
        definition = definitions.get(word, "").strip()
        if definition:
            rendered.append(f"{word_link} — {definition}")
        else:
            rendered.append(word_link)
    return (
        f"{subject_label}: \"{clean_name}\"<br>"
        f"Letters: {len(letters)}<br><br>"
        "Click a word to fetch a definition:<br>"
        + "<br>".join(rendered)
    )


@lru_cache(maxsize=512)
def fetch_word_definition(word: str, *, timeout_seconds: float = 1.8) -> str:
    """Fetch a short English definition for a word."""
    cleaned = str(word or "").strip().casefold()
    if not cleaned.isalpha():
        return "Definition unavailable."

    dictionary_api_endpoint = (
        f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(cleaned)}"
    )
    datamuse_endpoint = (
        f"https://api.datamuse.com/words?sp={urllib.parse.quote(cleaned)}&md=d&max=1"
    )

    saw_connectivity_error = False

    try:
        response = _DEFINITION_HTTP_SESSION.get(
            dictionary_api_endpoint,
            headers=DEFINITION_HTTP_HEADERS,
            timeout=(0.9, timeout_seconds),
        )
    except requests.RequestException:
        saw_connectivity_error = True
    else:
        if response.status_code in DEFINITION_CONNECTIVITY_ERROR_CODES:
            saw_connectivity_error = True
        elif response.status_code < 400:
            try:
                parsed = response.json()
            except ValueError:
                parsed = None

            if isinstance(parsed, list) and parsed:
                entry = parsed[0]
                meanings = entry.get("meanings") if isinstance(entry, dict) else None
                if isinstance(meanings, list):
                    for meaning in meanings:
                        definitions = meaning.get("definitions") if isinstance(meaning, dict) else None
                        if not isinstance(definitions, list):
                            continue
                        for definition_entry in definitions:
                            definition = (
                                definition_entry.get("definition")
                                if isinstance(definition_entry, dict)
                                else None
                            )
                            if isinstance(definition, str) and definition.strip():
                                compact = " ".join(definition.strip().split())
                                return compact[:220]

    try:
        response = _DEFINITION_HTTP_SESSION.get(
            datamuse_endpoint,
            headers=DEFINITION_HTTP_HEADERS,
            timeout=(0.9, timeout_seconds),
        )
    except requests.RequestException:
        if saw_connectivity_error:
            return "Definition unavailable (dictionary service unreachable)."
        return "Definition unavailable."

    if response.status_code in DEFINITION_CONNECTIVITY_ERROR_CODES:
        saw_connectivity_error = True
    elif response.status_code < 400:
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
        if isinstance(parsed, list) and parsed:
            first = parsed[0]
            defs = first.get("defs") if isinstance(first, dict) else None
            if isinstance(defs, list):
                for item in defs:
                    if not isinstance(item, str):
                        continue
                    _, _, raw_definition = item.partition("\t")
                    definition = raw_definition.strip() or item.strip()
                    if definition:
                        compact = " ".join(definition.split())
                        return compact[:220]

    if saw_connectivity_error:
        return "Definition unavailable (dictionary service unreachable)."
    return "Definition unavailable."


def build_anagrams_section(
    *,
    panel: QWidget,
    layout: QVBoxLayout,
    add_collapsible_section: Callable[..., QVBoxLayout],
    on_toggled: Callable[[bool], None],
    on_export_clicked: Callable[[], None],
    on_word_clicked: Callable[[str], None],
    on_source_changed: Callable[[str], None],
    get_share_icon_path: Callable[[], str | None],
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
        "Dictionary-based anagrams for chart name or alias (single words only, capped for speed)."
    )
    summary_label.setWordWrap(True)
    summary_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
    section_layout.addWidget(summary_label)

    header_row = QWidget()
    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_row.setLayout(header_layout)
    source_dropdown = QComboBox()
    source_dropdown.setStyleSheet(DATABASE_ANALYTICS_DROPDOWN_STYLE)
    for source_label, source_value in ANAGRAM_SOURCE_OPTIONS:
        source_dropdown.addItem(source_label, source_value)
    source_dropdown.currentIndexChanged.connect(
        lambda _index: on_source_changed(str(source_dropdown.currentData() or "name"))
    )
    header_layout.addWidget(source_dropdown, 0, Qt.AlignLeft)
    header_layout.addStretch(1)

    export_button = QToolButton()
    share_icon_path = get_share_icon_path()
    if share_icon_path:
        export_button.setIcon(QIcon(share_icon_path))
    else:
        export_button.setText("↗")
    export_button.setAutoRaise(True)
    export_button.setCursor(Qt.PointingHandCursor)
    export_button.setToolTip("Export anagrams and clicked definitions")
    export_button.clicked.connect(on_export_clicked)
    header_layout.addWidget(export_button, 0, Qt.AlignRight)
    section_layout.addWidget(header_row)

    list_label = QLabel("Generate or load a chart to scan chart name letters.")
    list_label.setWordWrap(True)
    list_label.setTextFormat(Qt.RichText)
    list_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    list_label.setOpenExternalLinks(False)
    list_label.linkActivated.connect(on_word_clicked)
    section_layout.addWidget(list_label)
    return AnagramsSectionWidgets(
        summary_label=summary_label,
        list_label=list_label,
        export_button=export_button,
        source_dropdown=source_dropdown,
    )
