from __future__ import annotations

import datetime
import re
from collections import Counter

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QWidget

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASS_AXIS_EARTHTONE_COLORS,
    DND_CLASS_THRESHOLD_COLOR,
    DND_CLASSES,
    DND_CLASS_SUBCLASS_EXPLAINERS,
    format_class_axis_label,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SPECIES_FAMILIES
from ephemeraldaddy.analysis.human_design import HD_GATE_OCCURRENCE_COLORS
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    SIGN_COLORS,
)
from ephemeraldaddy.gui.style import (
    CHART_DATA_COLON_LABELS,
    CHART_DATA_COMMON_LABELS,
    CHART_DATA_DND_SUBHEADER_BOLD,
    CHART_DATA_DND_SUBHEADER_NOTE_BOLD,
    CHART_DATA_DND_SUBHEADER_NOTE_ITALIC,
    CHART_DATA_HIGHLIGHT_COLOR,
    CHART_DATA_SECTION_HEADERS,
    CHART_INFO_EVIDENCE_LABEL_BOLD,
    CHART_INFO_SPECIES_DESCRIPTION_ITALIC,
    CHART_INFO_SPECIES_HEADER_COLOR,
    DND_STAT_EARTHTONE_COLORS,
    RELATIVE_YEAR_COLORS,
    CHART_DATA_MONOSPACE_FONT_FAMILY,
)


class ChartDataTableOutput(QPlainTextEdit):
    """Read-only chart output widget using shared chart-data rendering settings."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        emphasize_dnd_class_headers: bool = False,
        emphasize_species_info_headers: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFrameShape(QFrame.NoFrame)

        output_font = QFont(self.font())
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        output_font.setFixedPitch(True)
        if CHART_DATA_MONOSPACE_FONT_FAMILY:
            output_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        self.setFont(output_font)

        # Ensure every chart-data output panel gets the shared visual formatter by default.
        # This keeps in-view and popout chart-data styling aligned app-wide.
        apply_chart_data_highlighter(
            self,
            emphasize_dnd_class_headers=emphasize_dnd_class_headers,
            emphasize_species_info_headers=emphasize_species_info_headers,
        )


class ChartSummaryHighlighter(QSyntaxHighlighter):
    """Shared formatter for every chart-data output panel."""

    _NAKSHATRA_INFO_FIELD_LABELS = (
        "Symbol:",
        "Shakti:",
        "Essence:",
        "Quality:",
        "Favorable Activities:",
        "Sidereal Sign:",
        "Archetypes:",
        "Deity:",
        "Ruler:",
        "Body Associations:",
        "Notes A:",
        "Notes B:",
    )
    _HD_SUBHEADER_PREFIXES = (
        "Head",
        "Ajna",
        "Throat",
        "G",
        "Ego",
        "Spleen",
        "Solar Plexus",
        "Sacral",
        "Root",
        "Type",
        "Authority",
        "Strategy",
        "Profile",
        "Definition",
        "Incarnation Cross",
        "Channel",
        "Body",
        "Sign",
        "Longitude",
        "G/L",
        "C",
        "T",
        "B",
    )

    def __init__(
        self,
        document,
        *,
        emphasize_dnd_class_headers: bool = False,
        emphasize_species_info_headers: bool = False,
    ) -> None:
        super().__init__(document)
        self._emphasize_dnd_class_headers = bool(emphasize_dnd_class_headers)
        self._emphasize_species_info_headers = bool(emphasize_species_info_headers)
        self._unknown_format = QTextCharFormat()
        self._unknown_format.setForeground(QColor("#666666"))
        self._unknown_format.setFontItalic(True)
        self._unknown_needles = (
            "unknown (birth time unknown)",
            "unknown (🐣time unknown)",
            "unknown (birthtime unknown)",
        )
        self._label_format = QTextCharFormat()
        self._label_format.setFontWeight(QFont.Bold)
        self._label_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        self._nakshatra_header_formats = {}
        for nakshatra, (_planet, color) in NAKSHATRA_PLANET_COLOR.items():
            header_format = QTextCharFormat(self._label_format)
            header_format.setForeground(QColor(color or CHART_DATA_HIGHLIGHT_COLOR))
            self._nakshatra_header_formats[nakshatra] = header_format
        self._nakshatra_formats = {
            nakshatra: self._make_format(color or CHART_DATA_HIGHLIGHT_COLOR)
            for nakshatra, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()
        }
        self._section_format = QTextCharFormat()
        self._section_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        self._section_format.setFontWeight(QFont.Bold)
        self._plain_bold_format = QTextCharFormat()
        self._plain_bold_format.setFontWeight(QFont.Bold)
        self._copper_header_format = QTextCharFormat(self._plain_bold_format)
        self._copper_header_format.setForeground(QColor("#c8914f"))
        self._plain_italic_format = QTextCharFormat()
        self._plain_italic_format.setFontItalic(True)
        self._class_header_format = QTextCharFormat(self._plain_bold_format)
        self._class_header_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
        self._class_subheader_format = QTextCharFormat()
        self._class_subheader_format.setFontItalic(True)
        self._species_header_format = QTextCharFormat(self._plain_bold_format)
        self._species_header_format.setForeground(QColor(CHART_INFO_SPECIES_HEADER_COLOR))
        self._species_subheader_format = QTextCharFormat()
        self._species_subheader_format.setFontItalic(CHART_INFO_SPECIES_DESCRIPTION_ITALIC)
        self._dnd_subheader_format = QTextCharFormat()
        if CHART_DATA_DND_SUBHEADER_BOLD:
            self._dnd_subheader_format.setFontWeight(QFont.Bold)
        self._dnd_subheader_note_format = QTextCharFormat()
        self._dnd_subheader_note_format.setFontItalic(CHART_DATA_DND_SUBHEADER_NOTE_ITALIC)
        if CHART_DATA_DND_SUBHEADER_NOTE_BOLD:
            self._dnd_subheader_note_format.setFontWeight(QFont.Bold)
        self._dnd_threshold_format = self._make_format(DND_CLASS_THRESHOLD_COLOR)
        self._dnd_axis_line_formats = {
            format_class_axis_label(axis_name): self._make_format(color)
            for axis_name, color in DND_CLASS_AXIS_EARTHTONE_COLORS.items()
        }
        self._dnd_stat_line_formats = {
            stat_key: self._make_format(color)
            for stat_key, color in DND_STAT_EARTHTONE_COLORS.items()
        }
        self._time_variant_format = QTextCharFormat()
        self._time_variant_format.setFontItalic(True)
        self._time_variant_dawn_format = self._make_format("#d1863a", italic=True)
        self._time_variant_dusk_format = self._make_format("#4a7bd1", italic=True)
        self._aspect_formats = {
            "conjunction": self._make_format("#c7a56a"),
            "sextile": self._make_format("#6b8ba4"),
            "square": self._make_format("#8d6e63"),
            "trine": self._make_format("#6b705c"),
            "opposition": self._make_format("#c26d3a"),
        }
        self._planet_formats = {
            planet: self._make_format(color)
            for planet, color in PLANET_COLORS.items()
            if color
        }
        self._planet_aliases = {
            "Black Moon Lilith": "Lilith",
            "Part of Fortune": "Fortune",
            "Ascendant": "AS",
            "Descendant": "DS",
            "Medium Coeli": "MC",
            "Imum Coeli": "IC",
        }
        self._planet_alias_formats = {
            alias: self._planet_formats[target]
            for alias, target in self._planet_aliases.items()
            if target in self._planet_formats
        }
        self._sign_formats = {
            sign: self._make_format(color)
            for sign, color in SIGN_COLORS.items()
            if color
        }
        self._element_formats = {
            element.lower(): self._make_format(color)
            for element, color in ELEMENT_COLORS.items()
            if isinstance(element, str)
            and element.lower() in {"fire", "earth", "air", "water"}
            and color
        }
        self._house_formats = {
            str(house): self._make_format(color)
            for house, color in HOUSE_COLORS.items()
            if isinstance(house, (str, int)) and str(house).isdigit() and color
        }
        self._house_token_pattern = re.compile(r"\bH(1[0-2]|[1-9])\b")
        self._house_label_patterns = tuple(
            re.compile(pattern, flags=re.IGNORECASE)
            for pattern in (
                r"\bHouse\s+(1[0-2]|[1-9])\b",
                r"\b(1[0-2]|[1-9])(st|nd|rd|th)\s+House\b",
            )
        )
        self._relative_year_formats = {
            label: self._make_format(color)
            for label, color in RELATIVE_YEAR_COLORS.items()
            if isinstance(color, str) and color
        }
        self._transit_range_date_pattern = re.compile(r"\d{2}-\d{2}-(\d{4})(?:\s+\d{2}:\d{2})?\*?")
        self._awareness_completion_formats = {
            100: self._make_format("#2f9e44"),
            75: self._make_format("#8ea63b"),
            50: self._make_format("#d98e2f"),
            25: self._make_format("#c24a4a"),
            0: self._make_format("#777777"),
        }
        self._awareness_completion_pattern = re.compile(r"^\s*[A-Za-z ]+:\s+.+-\s+(\d{1,3})%\.\s+.*$")
        self._defined_center_formats = self._build_defined_center_formats()
        self._hd_gate_count_formats = {
            bucket: self._make_format(color)
            for bucket, color in HD_GATE_OCCURRENCE_COLORS.items()
        }
        self._hd_gate_count_cache_revision = -1
        self._hd_gate_count_cache: Counter[int] = Counter()

    @staticmethod
    def _make_format(color: str, *, italic: bool = False) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if italic:
            text_format.setFontItalic(True)
        return text_format

    @staticmethod
    def _qt_len(text: str) -> int:
        return len(text.encode("utf-16-le")) // 2

    @staticmethod
    def _build_defined_center_formats() -> dict[str, QTextCharFormat]:
        center_formats: dict[str, QTextCharFormat] = {}
        for center_entry in HD_CENTERS.values():
            center_name = str(center_entry.get("center", "")).strip()
            center_color = str(center_entry.get("color", "")).strip()
            if not center_name or not center_color:
                continue
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(center_color))
            center_formats[center_name] = text_format
        return center_formats

    @classmethod
    def _qt_index(cls, text: str, index: int) -> int:
        return cls._qt_len(text[:index])

    def _get_hd_gate_occurrence_counts(self) -> Counter[int]:
        document = self.document()
        revision = int(document.revision())
        if revision == self._hd_gate_count_cache_revision:
            return self._hd_gate_count_cache
        all_text = document.toPlainText()
        counts: Counter[int] = Counter()
        for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])\.[1-6]\b", all_text):
            gate = int(match.group(1))
            counts[gate] += 1
        self._hd_gate_count_cache_revision = revision
        self._hd_gate_count_cache = counts
        return counts

    def _apply_hd_gate_heatmap(self, text: str, stripped_text: str) -> None:
        if not stripped_text or "," not in stripped_text:
            return
        if not re.fullmatch(r"(?:\d{1,2}(?:\.[1-6])?)(?:,\s*\d{1,2}(?:\.[1-6])?)*", stripped_text):
            return
        counts = self._get_hd_gate_occurrence_counts()
        for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])(?:\.[1-6])?\b", text):
            gate = int(match.group(1))
            occurrence_count = counts.get(gate, 0)
            if occurrence_count <= 0:
                continue
            bucket = 5 if occurrence_count > 4 else occurrence_count
            text_format = self._hd_gate_count_formats.get(bucket)
            if text_format:
                self.setFormat(
                    self._qt_index(text, match.start(1)),
                    self._qt_len(match.group(1)),
                    text_format,
                )

    def highlightBlock(self, text: str) -> None:
        if self.previousBlockState() == 1:
            self.setFormat(0, self._qt_len(text), self._species_subheader_format)
            self.setCurrentBlockState(0)
            return

        lowered = text.lower()
        for needle in self._unknown_needles:
            start = 0
            while True:
                index = lowered.find(needle, start)
                if index == -1:
                    break
                self.setFormat(index, len(needle), self._unknown_format)
                start = index + len(needle)
        stripped_text = text.strip()
        lowered_stripped = stripped_text.lower()
        for header in CHART_DATA_SECTION_HEADERS:
            if stripped_text.upper() == header:
                self.setFormat(0, self._qt_len(text), self._section_format)
                break
        if (
            stripped_text
            and stripped_text == stripped_text.upper()
            and any(char.isalpha() for char in stripped_text)
            and all(char.isupper() or not char.isalpha() for char in stripped_text)
        ):
            self.setFormat(0, self._qt_len(text), self._section_format)
        for prefix in self._HD_SUBHEADER_PREFIXES:
            if (
                stripped_text == prefix
                or stripped_text.startswith(f"{prefix}:")
                or stripped_text.startswith(f"{prefix} ")
            ):
                self.setFormat(0, self._qt_len(prefix), self._plain_bold_format)
                break
        if stripped_text.startswith("Defined Centers:"):
            label = "Defined Centers:"
            self.setFormat(0, self._qt_len(label), self._plain_bold_format)
            centers_text = stripped_text[len(label):].strip()
            if centers_text and centers_text.lower() != "none":
                for raw_center in [segment.strip() for segment in centers_text.split(",") if segment.strip()]:
                    center_key = "G" if raw_center == "G" else raw_center
                    center_format = self._defined_center_formats.get(center_key)
                    if center_format is None:
                        continue
                    center_start = text.find(raw_center)
                    if center_start != -1:
                        self.setFormat(
                            self._qt_index(text, center_start),
                            self._qt_len(raw_center),
                            center_format,
                        )
        if lowered_stripped in {"defined", "undefined"}:
            self.setFormat(0, self._qt_len(text), self._copper_header_format)
        if (
            len(stripped_text) >= 2
            and stripped_text.startswith("*")
            and stripped_text.endswith("*")
        ):
            line_start = text.find("*")
            line_end = text.rfind("*")
            if line_start != -1 and line_end > line_start:
                self.setFormat(
                    self._qt_index(text, line_start),
                    self._qt_len("*"),
                    self._unknown_format,
                )
                self.setFormat(
                    self._qt_index(text, line_start + 1),
                    self._qt_len(text[line_start + 1:line_end]),
                    self._plain_italic_format,
                )
                self.setFormat(
                    self._qt_index(text, line_end),
                    self._qt_len("*"),
                    self._unknown_format,
                )
        if self._emphasize_dnd_class_headers:
            if stripped_text in DND_CLASSES:
                self.setFormat(0, self._qt_len(text), self._class_header_format)
            elif stripped_text and stripped_text in DND_CLASS_SUBCLASS_EXPLAINERS.values():
                self.setFormat(0, self._qt_len(text), self._class_subheader_format)
            elif stripped_text.startswith("‣ "):
                bullet_body = stripped_text[2:].lstrip()
                axis_label_text, separator, _rest = bullet_body.partition(":")
                normalized_axis_label = axis_label_text.strip()
                applied_dnd_line_format = False
                for axis_label, axis_format in self._dnd_axis_line_formats.items():
                    if separator and normalized_axis_label == axis_label:
                        self.setFormat(0, self._qt_len(text), axis_format)
                        marker_index = text.find("│")
                        if marker_index != -1:
                            self.setFormat(
                                self._qt_index(text, marker_index),
                                self._qt_len("│"),
                                self._dnd_threshold_format,
                            )
                        applied_dnd_line_format = True
                        break
                if not applied_dnd_line_format and separator:
                    stat_key = normalized_axis_label.split(" ", 1)[0].strip()
                    stat_format = self._dnd_stat_line_formats.get(stat_key)
                    if stat_format is not None:
                        self.setFormat(0, self._qt_len(text), stat_format)
        if self._emphasize_species_info_headers:
            if stripped_text == "Evidence:" and CHART_INFO_EVIDENCE_LABEL_BOLD:
                self.setFormat(0, self._qt_len(text), self._plain_bold_format)
            elif " • " in stripped_text and re.search(r" • -?\d+(?:\.\d+)?$", stripped_text):
                header_part, _, _score_part = stripped_text.partition(" • ")
                if any(
                    header_part == species or header_part.startswith(f"{species} (")
                    for species in SPECIES_FAMILIES
                ):
                    header_len = len(header_part)
                    self.setFormat(
                        self._qt_index(text, 0),
                        self._qt_len(text[:header_len]),
                        self._species_header_format,
                    )
                    self.setCurrentBlockState(1)
        if stripped_text in {"Statblock", "Statblock ⓘ", "D&D Statblock", "D&D Statblock ⓘ"}:
            self.setFormat(0, self._qt_len(text), self._dnd_subheader_format)
        elif stripped_text == "Top 3 Species":
            self.setFormat(0, self._qt_len(text), self._dnd_subheader_format)
        elif stripped_text.startswith("Top 3 Classes*"):
            classes_header_prefix = "Top 3 Classes*"
            self.setFormat(
                self._qt_index(text, 0),
                self._qt_len(classes_header_prefix),
                self._dnd_subheader_format,
            )
            note_index = text.find("(")
            if note_index != -1:
                self.setFormat(
                    self._qt_index(text, note_index),
                    self._qt_len(text[note_index:]),
                    self._dnd_subheader_note_format,
                )

        if re.match(r"^Channel\s+\d{1,2}-\d{1,2}(?::.*)?$", stripped_text):
            self.setFormat(0, self._qt_len(text), self._class_header_format)

        activation_match = re.match(r"^\s*(Personality|Design)\s+([A-Za-z]+)", text)
        if activation_match:
            body_name = activation_match.group(2)
            body_format = self._planet_formats.get(body_name)
            if body_format:
                span_start = activation_match.start(1)
                span_end = activation_match.end(2)
                self.setFormat(
                    self._qt_index(text, span_start),
                    self._qt_len(text[span_start:span_end]),
                    body_format,
                )

        awareness_match = self._awareness_completion_pattern.match(stripped_text)
        if awareness_match:
            completion_raw = int(awareness_match.group(1))
            completion = min(100, max(0, completion_raw))
            completion_bucket = min((0, 25, 50, 75, 100), key=lambda bucket: abs(bucket - completion))
            awareness_format = self._awareness_completion_formats.get(completion_bucket)
            if awareness_format:
                self.setFormat(0, self._qt_len(text), awareness_format)
        if lowered_stripped.startswith("synastry chart for "):
            self.setFormat(0, self._qt_len(text), self._section_format)
        if lowered_stripped.startswith("personal transit chart for "):
            self.setFormat(0, self._qt_len(text), self._section_format)
        if lowered_stripped.endswith(":") and " aspects to " in lowered_stripped:
            self.setFormat(0, self._qt_len(text), self._section_format)
        for label in (
            *CHART_DATA_COMMON_LABELS,
            *CHART_DATA_COLON_LABELS,
            *CHART_DATA_SECTION_HEADERS,
            *self._NAKSHATRA_INFO_FIELD_LABELS,
            "|",
        ):
            self._highlight_phrase(text, label, self._label_format)
        for nakshatra, header_format in self._nakshatra_header_formats.items():
            if stripped_text == nakshatra:
                self.setFormat(0, self._qt_len(text), header_format)
                break
        if "🌅" in text or "🌌" in text:
            self.setFormat(0, self._qt_len(text), self._time_variant_format)
            dawn_index = text.find("🌅")
            if dawn_index != -1:
                start = dawn_index + len("🌅")
                if start < len(text) and text[start] == " ":
                    start += 1
                if start < len(text):
                    start_qt = self._qt_index(text, start)
                    self.setFormat(
                        start_qt,
                        self._qt_len(text) - start_qt,
                        self._time_variant_dawn_format,
                    )
            dusk_index = text.find("🌌")
            if dusk_index != -1:
                start = dusk_index + len("🌌")
                if start < len(text) and text[start] == " ":
                    start += 1
                if start < len(text):
                    start_qt = self._qt_index(text, start)
                    self.setFormat(
                        start_qt,
                        self._qt_len(text) - start_qt,
                        self._time_variant_dusk_format,
                    )
        leading_token = text.split()[0] if text.split() else ""
        if leading_token in self._planet_formats:
            self.setFormat(0, self._qt_len(text), self._planet_formats[leading_token])
        else:
            for body, fmt in self._planet_formats.items():
                self._highlight_phrase(text, body, fmt)
            for alias, fmt in self._planet_alias_formats.items():
                self._highlight_phrase(text, alias, fmt)
        for aspect, fmt in self._aspect_formats.items():
            self._highlight_phrase(lowered, aspect, fmt)
        for sign, fmt in self._sign_formats.items():
            self._highlight_phrase(text, sign, fmt)
        for element, fmt in self._element_formats.items():
            self._highlight_phrase(lowered, element, fmt)
        for nakshatra, fmt in self._nakshatra_formats.items():
            self._highlight_phrase(text, nakshatra, fmt)
        house_match = re.match(r"^\s*(\d{1,2})\s*:\s+([^\d\s][^\d]*)\s+\d{2}°\d{2}'", text)
        if house_match:
            house_num = house_match.group(1)
            sign_name = house_match.group(2).strip()
            house_fmt = self._house_formats.get(house_num)
            if house_fmt:
                prefix_end = text.find(":") + 1
                if prefix_end > 0:
                    self.setFormat(0, prefix_end, house_fmt)
            sign_fmt = self._make_format(SIGN_COLORS.get(sign_name, CHART_DATA_HIGHLIGHT_COLOR))
            sign_start = text.find(sign_name)
            if sign_start != -1:
                self.setFormat(sign_start, len(sign_name), sign_fmt)
        for match in self._house_token_pattern.finditer(text):
            house_num = match.group(1)
            house_fmt = self._house_formats.get(house_num)
            if house_fmt:
                self.setFormat(match.start(), len(match.group(0)), house_fmt)
        for pattern in self._house_label_patterns:
            for match in pattern.finditer(text):
                house_num = match.group(1)
                house_fmt = self._house_formats.get(house_num)
                if house_fmt:
                    self.setFormat(
                        self._qt_index(text, match.start()),
                        self._qt_len(match.group(0)),
                        house_fmt,
                    )
        current_year = datetime.datetime.now(datetime.timezone.utc).year
        for match in self._transit_range_date_pattern.finditer(text):
            year = int(match.group(1))
            year_delta = year - current_year
            if year_delta == -2:
                year_label = "year before last"
            elif year_delta == -1:
                year_label = "last year"
            elif year_delta == 0:
                year_label = "current"
            elif year_delta == 1:
                year_label = "next"
            elif year_delta == 2:
                year_label = "year after next"
            else:
                year_label = "other"
            text_format = self._relative_year_formats.get(year_label)
            if text_format:
                start_qt = self._qt_index(text, match.start())
                length_qt = self._qt_len(match.group(0))
                self.setFormat(start_qt, length_qt, text_format)

        self._apply_hd_gate_heatmap(text, stripped_text)

    def _highlight_phrase(self, text: str, phrase: str, text_format: QTextCharFormat) -> None:
        start = 0
        phrase_len = len(phrase)
        text_len = len(text)
        while True:
            index = text.find(phrase, start)
            if index == -1:
                break
            before_ok = index == 0 or not text[index - 1].isalnum()
            after_index = index + phrase_len
            after_ok = after_index >= text_len or not text[after_index].isalnum()
            if before_ok and after_ok:
                self.setFormat(
                    self._qt_index(text, index),
                    self._qt_len(phrase),
                    text_format,
                )
            start = index + phrase_len


def apply_chart_data_highlighter(
    output_widget: QPlainTextEdit,
    *,
    emphasize_dnd_class_headers: bool = False,
    emphasize_species_info_headers: bool = False,
) -> ChartSummaryHighlighter:
    """Attach the shared chart-data highlighter to an output widget."""
    highlighter = ChartSummaryHighlighter(
        output_widget.document(),
        emphasize_dnd_class_headers=emphasize_dnd_class_headers,
        emphasize_species_info_headers=emphasize_species_info_headers,
    )
    output_widget._summary_highlighter = highlighter
    return highlighter
