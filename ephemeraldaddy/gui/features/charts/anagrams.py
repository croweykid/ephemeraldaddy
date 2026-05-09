"""Chart-name anagram helpers for Chart View analytics."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import requests
from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget
from PySide6.QtWidgets import QHBoxLayout, QToolButton

from ephemeraldaddy.gui.features.charts.anagram_engine import (
    anagram_dictionary_words as _anagram_dictionary_words,
    collect_anagram_words,
    collect_chart_name_anagrams as _collect_chart_name_anagrams,
    render_anagrams_text,
)
from ephemeraldaddy.gui.style import (
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
    DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    configure_collapsible_header_toggle,
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
    """References to labels used by the chart-name anagrams section."""

    summary_label: QLabel
    list_label: QLabel
    definition_label: QLabel
    export_button: QToolButton
    source_dropdown: QComboBox
    container: QWidget


@dataclass
class AnagramsViewState:
    """Mutable display state for Chart View's anagrams panel."""

    selected_source: str = "name"
    current_words: list[str] | None = None
    clicked_definitions: dict[str, str] | None = None
    current_chart_text: str = ""
    current_subject_label: str = "Chart name"

    def __post_init__(self) -> None:
        if self.current_words is None:
            self.current_words = []
        if self.clicked_definitions is None:
            self.clicked_definitions = {}


class AnagramsPresenter:
    """Keep anagram UI state, source options, and render behavior out of app.py."""

    def __init__(self, widgets: AnagramsSectionWidgets) -> None:
        self.widgets = widgets
        self.state = AnagramsViewState()

    @staticmethod
    def chart_has_alias(chart: object | None) -> bool:
        return bool(str(getattr(chart, "alias", "") or "").strip())

    def _clear_definition_detail(self) -> None:
        self.widgets.definition_label.clear()
        self.widgets.definition_label.setVisible(False)

    def sync_source_options(
        self,
        chart: object | None,
        *,
        reset_to_chart_name: bool = False,
    ) -> None:
        alias_available = self.chart_has_alias(chart)
        if reset_to_chart_name or not alias_available:
            self.state.selected_source = "name"

        dropdown = self.widgets.source_dropdown
        blocker = QSignalBlocker(dropdown)
        dropdown.clear()
        dropdown.addItem("Chart Name", "name")
        if alias_available:
            dropdown.addItem("Chart Alias", "alias")
        selected_index = dropdown.findData(self.state.selected_source)
        dropdown.setCurrentIndex(max(0, selected_index))
        dropdown.setMinimumWidth(dropdown.sizeHint().width() + 6)
        del blocker

    def refresh_for_chart(
        self,
        chart: object | None,
        *,
        reset_to_chart_name: bool = False,
    ) -> None:
        self.sync_source_options(chart, reset_to_chart_name=reset_to_chart_name)
        if chart is None:
            source_label = ANAGRAM_SOURCE_LABELS.get(self.state.selected_source, "Chart name")
            self.widgets.list_label.setText(
                f"Generate or load a chart to scan {source_label.lower()} letters."
            )
            self._clear_definition_detail()
            self.state.current_words = []
            self.state.clicked_definitions.clear()
            self.state.current_chart_text = ""
            self.state.current_subject_label = ANAGRAM_SOURCE_LABELS.get(
                self.state.selected_source,
                "Chart name",
            )
            return
        self.render(chart)

    def render(self, chart: object) -> None:
        self.sync_source_options(chart)
        source = self.state.selected_source if self.state.selected_source in {"name", "alias"} else "name"
        if source == "alias" and not self.chart_has_alias(chart):
            source = "name"
            self.state.selected_source = "name"
            self.sync_source_options(chart)

        subject_label = ANAGRAM_SOURCE_LABELS.get(source, "Chart name")
        chart_text = str(getattr(chart, source, "") or "")
        self.state.current_chart_text = chart_text.strip()
        self.state.current_subject_label = subject_label
        if not self.state.current_chart_text:
            self.state.current_words = []
            self.state.clicked_definitions.clear()
            self.widgets.list_label.setText(
                render_anagrams_text(chart_text, subject_label=subject_label)
            )
            self._clear_definition_detail()
            return

        words = collect_anagram_words(self.state.current_chart_text, max_results=30)
        self.state.current_words = words
        word_set = set(words)
        self.state.clicked_definitions = {
            word: definition
            for word, definition in self.state.clicked_definitions.items()
            if word in word_set
        }
        self._clear_definition_detail()
        if not words:
            self.widgets.list_label.setText(
                render_anagrams_text(chart_text, subject_label=subject_label)
            )
            self._clear_definition_detail()
            return
        self.widgets.list_label.setText(
            render_anagrams_html(
                self.state.current_chart_text,
                words,
                subject_label=subject_label,
            )
        )

    def source_changed(self, source_value: str, chart: object | None) -> None:
        requested_source = source_value if source_value in {"name", "alias"} else "name"
        if requested_source == "alias" and not self.chart_has_alias(chart):
            requested_source = "name"
        self.state.selected_source = requested_source
        self.refresh_for_chart(chart)

    def definition_clicked(self, target: str) -> bool:
        if not target.startswith("define:"):
            return False
        encoded_word = target.split("define:", 1)[1].strip()
        word = urllib.parse.unquote(encoded_word).strip().casefold()
        current_words = self.state.current_words or []
        if not word or word not in current_words:
            return False
        definition = fetch_word_definition(word)
        self.state.clicked_definitions[word] = definition
        self.widgets.definition_label.setText(render_definition_detail_html(word, definition))
        self.widgets.definition_label.setVisible(True)
        return True


def render_anagrams_html(
    chart_text: str,
    words: list[str],
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
        rendered.append(word_link)
    return (
        f"{subject_label}: \"{clean_name}\"<br>"
        f"Letters: {len(letters)}<br><br>"
        "Click a word to fetch its definition:<br>"
        + "<br>".join(rendered)
    )


def render_definition_detail_html(word: str, definition: str) -> str:
    """Build the stable definition detail shown below the clickable anagram list."""
    clean_word = str(word or "").strip()
    clean_definition = str(definition or "").strip() or "Definition unavailable."
    return (
        f'<span style="color: #9dd8ff; font-weight: 700;">{clean_word}</span>'
        f'<span style="color: #f5f5f5;"> — {clean_definition}</span>'
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
    on_toggled: Callable[[bool], None],
    on_export_clicked: Callable[[], None],
    on_word_clicked: Callable[[str], None],
    on_source_changed: Callable[[str], None],
    get_share_icon_path: Callable[[], str | None],
) -> AnagramsSectionWidgets:
    """Create the Anagrams collapsible Subjective Notes section."""
    anagrams_box = QFrame()
    anagrams_box.setStyleSheet(
        "QFrame {"
        "background-color: #1c1c1c;"
        "border: 1px solid #2b2b2b;"
        "border-radius: 6px;"
        "}"
    )
    anagrams_box_layout = QVBoxLayout()
    anagrams_box_layout.setContentsMargins(8, 4, 8, 8)
    anagrams_box_layout.setSpacing(0)
    anagrams_box.setLayout(anagrams_box_layout)
    anagrams_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    
    toggle = QToolButton()
    configure_collapsible_header_toggle(
        toggle,
        title="Anagrams",
        expanded=False,
        style_sheet=DATABASE_VIEW_COLLAPSIBLE_TOGGLE_STYLE,
    )
    anagrams_box_layout.addWidget(toggle)

    content_widget = QWidget()
    section_layout = QVBoxLayout()
    section_layout.setContentsMargins(0, 2, 0, 0)
    section_layout.setSpacing(4)
    content_widget.setLayout(section_layout)
    content_widget.setVisible(False)

    def toggle_content(checked: bool) -> None:
        content_widget.setVisible(checked)
        toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        on_toggled(checked)
        anagrams_box.adjustSize()
        panel.adjustSize()
        panel.updateGeometry()

    toggle.toggled.connect(toggle_content)
    anagrams_box_layout.addWidget(content_widget)
    layout.addWidget(anagrams_box)

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
    source_dropdown.addItem("Chart Name", "name")
    source_dropdown.setMinimumWidth(source_dropdown.sizeHint().width() + 6)
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

    definition_label = QLabel()
    definition_label.setWordWrap(True)
    definition_label.setTextFormat(Qt.RichText)
    definition_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    definition_label.setStyleSheet("color: #f5f5f5; padding-top: 2px;")
    definition_label.setVisible(False)
    section_layout.addWidget(definition_label)
    return AnagramsSectionWidgets(
        summary_label=summary_label,
        list_label=list_label,
        definition_label=definition_label,
        export_button=export_button,
        source_dropdown=source_dropdown,
        container=anagrams_box,
    )
