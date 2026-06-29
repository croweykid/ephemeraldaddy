from __future__ import annotations

import datetime
import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QToolTip, QWidget

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASS_AXIS_EARTHTONE_COLORS,
    DND_CLASS_THRESHOLD_COLOR,
    DND_CLASSES,
    DND_CLASS_SUBCLASS_EXPLAINERS,
    format_class_axis_label,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SPECIES_FAMILIES
from ephemeraldaddy.analysis.hd_line_fixings import get_hd_line_fixings
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS, HD_COLORS
from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    ASPECT_GLYPHS,
    BODY_RELATIONAL_GLYPHS,
    ELEMENT_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    PLANET_GLYPHS,
    SIGN_COLORS,
    ZODIAC_NAMES,
    ZODIAC_SIGNS,
)
from ephemeraldaddy.gui.style import (
    CHART_DATA_COLON_LABELS,
    CHART_DATA_COMMON_LABELS,
    CHART_DATA_DIVIDER,
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


class ChartDataTooltipOutput(QPlainTextEdit):
    """Read-only plain-text chart output with per-token hover tooltips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tooltip_spans: dict[int, list[dict[str, object]]] = {}
        self.setMouseTracking(True)

    def set_tooltip_spans(self, spans: dict[int, list[dict[str, object]]] | None) -> None:
        self._tooltip_spans = spans or {}

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001 - Qt event type varies by binding version.
        cursor = self.cursorForPosition(event.pos())
        block_number = cursor.blockNumber()
        column = cursor.positionInBlock()
        tooltip_text = ""
        for span in self._tooltip_spans.get(block_number, []):
            try:
                start = int(span.get("span_start", -1))
                end = int(span.get("span_end", -1))
            except (TypeError, ValueError):
                continue
            if start <= column < end:
                tooltip_text = str(span.get("tooltip", "")).strip()
                break
        if tooltip_text:
            QToolTip.showText(event.globalPos(), tooltip_text, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001 - Qt event type varies by binding version.
        QToolTip.hideText()
        super().leaveEvent(event)


class ChartDataTableOutput(QPlainTextEdit):
    """Read-only chart output widget using shared chart-data rendering settings."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        emphasize_dnd_class_headers: bool = False,
        emphasize_species_info_headers: bool = False,
        human_design_synastry_mode: bool = False,
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
            human_design_synastry_mode=human_design_synastry_mode,
        )


class ChartSummaryHighlighter(QSyntaxHighlighter):
    """Shared formatter for every chart-data output panel."""

    _HD_PERSONALITY_GATE_COLOR = "#2f9e44"
    _HD_DESIGN_GATE_COLOR = "#c24a4a"
    _HD_SYNASTRY_CHART_A_COLOR = "#ff9f1c"
    _HD_SYNASTRY_CHART_B_COLOR = "#4ea5ff"

    _HD_COLOR_NAME_TO_HEX = {
        "red": "#ff4d4d",
        "orange": "#ff9f1c",
        "yellow": "#ffd60a",
        "green": "#5dc26a",
        "blue": "#4f8cff",
        "violet": "#b388ff",
    }
    
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
        "Environment",
        "Perspective",
        "Motivation",
        "Digestion",
        "Combined Type",
        "Combined Authority",
        "Combined Definition",
        "Combined Strategy",
        "Combined Defined Centers",
        "Combined Incarnation Cross(es)",
        "Channel",
        "Body",
        "Sign",
        "Degree",
        "G/L",
        "C",
        "T",
        "B",
    )
    HD_HEADERS = (
        "Gate",
        "Type",
        "Authority",
        "Defined Centers",
        "Combined Defined Centers",
        "Profile",
        "Definition",
        "Incarnation Cross",
        "Environment",
        "Perspective",
        "Motivation",
        "Digestion",
        "Combined Type",
        "Combined Authority",
        "Combined Definition",
        "Combined Strategy",
        "Combined Incarnation Cross(es)",
        "Strategy",
    )

    def __init__(
        self,
        document,
        *,
        emphasize_dnd_class_headers: bool = False,
        emphasize_species_info_headers: bool = False,
        human_design_synastry_mode: bool = False,
    ) -> None:
        super().__init__(document)
        self._emphasize_dnd_class_headers = bool(emphasize_dnd_class_headers)
        self._emphasize_species_info_headers = bool(emphasize_species_info_headers)
        self._human_design_synastry_mode = bool(human_design_synastry_mode)
        self._section_header_names = {header.upper() for header in CHART_DATA_SECTION_HEADERS}
        self._unknown_format = QTextCharFormat()
        self._section_header_names.update({"GATES & LINES"})
        self._column_separator_format = QTextCharFormat()
        self._column_separator_format.setForeground(QColor("#555555"))
        self._unknown_format.setForeground(QColor("#666666"))
        self._unknown_format.setFontItalic(True)
        self._default_body_format = QTextCharFormat()
        # Keep body text non-bold/non-italic by default, but do not force foreground color.
        # This preserves intentional per-token coloring (including cursor-inserted formats)
        # while preventing header-style bold inheritance.
        self._default_body_format.setFontWeight(QFont.Normal)
        self._default_body_format.setFontItalic(False)
        if self._human_design_synastry_mode:
            self._default_body_format.setForeground(QColor("#ffffff"))
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
        self._copper_header_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
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
        # Human Design time variants use the same start/end colors as the
        # chart-data sign time variants above, plus yellow for explicit noon.
        self._hd_midnight_variant_format = self._make_format("#d1863a")
        self._hd_noon_variant_format = self._make_format("#ffd60a")
        self._hd_late_variant_format = self._make_format("#4a7bd1")
        self._aspect_formats = {
            aspect: self._make_format(color)
            for aspect, color in ASPECT_COLORS.items()
            if color
        }
        self._planet_formats = {
            planet: self._make_format(color)
            for planet, color in PLANET_COLORS.items()
            if color
        }
        self._planet_aliases = {
            "Black Moon Lilith": "Lilith",
            "Black☽ Lilith": "Lilith",
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
        self._planet_glyph_formats = {
            glyph: self._planet_formats[planet]
            for planet, glyph in PLANET_GLYPHS.items()
            if planet in self._planet_formats and glyph
        }
        self._sign_formats = {
            sign: self._make_format(color)
            for sign, color in SIGN_COLORS.items()
            if color
        }
        self._sign_glyph_formats = {
            glyph: self._sign_formats[sign]
            for sign, glyph in zip(ZODIAC_NAMES, ZODIAC_SIGNS, strict=False)
            if sign in self._sign_formats and glyph
        }
        self._aspect_glyph_formats = {
            glyph: self._aspect_formats[aspect]
            for aspect, glyph in ASPECT_GLYPHS.items()
            if aspect in self._aspect_formats and glyph
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
        relational_glyphs = sorted(
            {glyph for glyph in BODY_RELATIONAL_GLYPHS.values() if glyph},
            key=len,
            reverse=True,
        )
        self._body_relational_glyph_pattern = re.compile("|".join(re.escape(glyph) for glyph in relational_glyphs))
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
        self._hd_center_header_names = set(self._defined_center_formats)
        self._hd_center_header_names.update(
            {f"{center_name} Center" for center_name in self._defined_center_formats}
        )
        self._hd_personality_gate_format = self._make_format(self._HD_PERSONALITY_GATE_COLOR)
        self._hd_design_gate_format = self._make_format(self._HD_DESIGN_GATE_COLOR)
        self._hd_personality_fixed_gate_format = self._make_format(
            self._HD_PERSONALITY_GATE_COLOR, bold=True, underline=True
        )
        self._hd_design_fixed_gate_format = self._make_format(
            self._HD_DESIGN_GATE_COLOR, bold=True, underline=True
        )
        self._hd_synastry_chart_a_format = self._make_format(self._HD_SYNASTRY_CHART_A_COLOR)
        self._hd_synastry_chart_b_format = self._make_format(self._HD_SYNASTRY_CHART_B_COLOR)
        hd_color_entries = (
            HD_COLORS.values()
            if isinstance(HD_COLORS, dict)
            else HD_COLORS
            if isinstance(HD_COLORS, (list, tuple))
            else ()
        )
        self._hd_environment_color_formats = {
            str(entry.get("name", "")).strip().title(): self._make_format(
                self._HD_COLOR_NAME_TO_HEX.get(str(entry.get("color", "")).strip().lower(), CHART_DATA_HIGHLIGHT_COLOR)
            )
            for entry in hd_color_entries
            if isinstance(entry, dict)
        }
        self._hd_gate_side_cache_revision = -1
        self._hd_gate_side_cache: dict[tuple[int, int], set[str]] = {}
        self._hd_gate_only_side_cache: dict[int, set[str]] = {}
        self._hd_gate_line_fixing_cache: dict[tuple[int, int], str] = {}
        self._hd_synastry_gate_owners: dict[int, set[str]] = {}
        self._hd_synastry_gate_line_owners: dict[tuple[int, int], set[str]] = {}

    def set_human_design_synastry_ownership(
        self,
        *,
        gate_owners: dict[int, set[str]],
        gate_line_owners: dict[tuple[int, int], set[str]],
    ) -> None:
        """Provide per-chart ownership metadata for synastry gate highlighting."""
        self._hd_synastry_gate_owners = {int(gate): set(owners) for gate, owners in gate_owners.items()}
        self._hd_synastry_gate_line_owners = {
            (int(gate), int(line)): set(owners)
            for (gate, line), owners in gate_line_owners.items()
        }
        self.rehighlight()

    @staticmethod
    def _make_format(
        color: str,
        *,
        italic: bool = False,
        bold: bool = False,
        underline: bool = False,
    ) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if italic:
            text_format.setFontItalic(True)
        if bold:
            text_format.setFontWeight(QFont.Bold)
        if underline:
            text_format.setFontUnderline(True)
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

    def _get_hd_gate_line_sides(self) -> dict[tuple[int, int], set[str]]:
        document = self.document()
        revision = int(document.revision())
        if revision == self._hd_gate_side_cache_revision:
            return self._hd_gate_side_cache
        all_text = document.toPlainText()
        gate_line_sides: dict[tuple[int, int], set[str]] = {}
        gate_sides: dict[int, set[str]] = {}
        gate_line_fixings: dict[tuple[int, int], str] = {}
        for text_line in all_text.splitlines():
            side_match = re.match(r"^\s*(?:(Personality|Design)|([PD])\.)\s+", text_line)
            if not side_match:
                continue
            side_token = (side_match.group(1) or side_match.group(2) or "").strip().lower()
            side_key = {"p": "personality", "d": "design"}.get(side_token.rstrip("."), side_token)
            if side_key not in {"personality", "design"}:
                continue
            for activation_match in re.finditer(
                r"\b([1-9]|[1-5][0-9]|6[0-4])\.([1-6])\b",
                text_line,
            ):
                gate = int(activation_match.group(1))
                line = int(activation_match.group(2))
                gate_line_key = (gate, line)
                gate_line_sides.setdefault(gate_line_key, set()).add(side_key)
                gate_sides.setdefault(gate, set()).add(side_key)
                line_prefix = text_line[:activation_match.start()]
                fixing_record = get_hd_line_fixings(gate, line)
                for fixing_name in ("exaltation", "detriment"):
                    if gate_line_key in gate_line_fixings:
                        break
                    for body_name in fixing_record.get(fixing_name, ()):
                        body_text = str(body_name).strip()
                        body_glyph = PLANET_GLYPHS.get(body_text, "")
                        if body_text and (body_text in line_prefix or (body_glyph and body_glyph in line_prefix)):
                            gate_line_fixings[gate_line_key] = fixing_name
                            break
        self._hd_gate_side_cache_revision = revision
        self._hd_gate_side_cache = gate_line_sides
        self._hd_gate_only_side_cache = gate_sides
        self._hd_gate_line_fixing_cache = gate_line_fixings
        return gate_line_sides

    def _get_hd_gate_sides(self) -> dict[int, set[str]]:
        self._get_hd_gate_line_sides()
        return self._hd_gate_only_side_cache

    def _format_for_hd_sides(self, sides: set[str], *, fixed: bool = False) -> QTextCharFormat | None:
        if "personality" in sides:
            return self._hd_personality_fixed_gate_format if fixed else self._hd_personality_gate_format
        if "design" in sides:
            return self._hd_design_fixed_gate_format if fixed else self._hd_design_gate_format
        return None

    def _hd_time_variant_segment_formats(
        self,
        segment_count: int,
        *,
        row_has_three_way_variant: bool,
    ) -> tuple[QTextCharFormat, ...] | None:
        if segment_count == 3:
            return (
                self._hd_midnight_variant_format,
                self._hd_noon_variant_format,
                self._hd_late_variant_format,
            )
        if segment_count == 2:
            if row_has_three_way_variant:
                return (self._hd_midnight_variant_format, self._hd_noon_variant_format)
            return (self._hd_midnight_variant_format, self._hd_late_variant_format)
        return None

    def _apply_hd_time_variant_colors(self, text: str, stripped_text: str) -> None:
        if "->" not in stripped_text or self._current_chart_data_section() != "POSITIONS":
            return
        columns = self._split_padded_columns(text.rstrip())
        if len(columns) < 4:
            return
        has_info_icon = columns[-1][0].strip() == "ⓘ"
        data_columns = columns[:-1] if has_info_icon else columns
        if len(data_columns) < 4:
            return
        body_text = data_columns[0][0].strip()
        if not re.match(r"^[PD]\.\s+", body_text):
            return
        degree_value = data_columns[2][0].strip()
        if not re.fullmatch(r"\d{1,3}(?:\.\d+)?°", degree_value):
            return

        variant_columns = [data_columns[1], *data_columns[3:7]]
        parsed_variant_fields: list[tuple[int, re.Match[str], list[str]]] = []
        row_has_three_way_variant = False
        for value_text, value_start, _value_end in variant_columns:
            value_match = re.search(r"\S+(?:->\S+)*", value_text)
            if value_match is None or "->" not in value_match.group(0):
                continue
            segments = value_match.group(0).split("->")
            if len(segments) == 3:
                row_has_three_way_variant = True
            parsed_variant_fields.append((value_start, value_match, segments))

        for value_start, value_match, segments in parsed_variant_fields:
            segment_formats = self._hd_time_variant_segment_formats(
                len(segments),
                row_has_three_way_variant=row_has_three_way_variant,
            )
            if segment_formats is None:
                continue
            cursor = value_start + value_match.start()
            for segment, text_format in zip(segments, segment_formats):
                if segment and segment != "?":
                    self.setFormat(
                        self._qt_index(text, cursor),
                        self._qt_len(segment),
                        text_format,
                    )
                cursor += len(segment) + len("->")

    def _apply_hd_gate_side_color(self, text: str, stripped_text: str) -> None:
        if not stripped_text:
            return
        current_section = self._current_chart_data_section()
        if current_section not in {"GATES & LINES", "CHANNELS"}:
            return
        if current_section == "GATES & LINES":
            gate_line_sides = self._get_hd_gate_line_sides()
            for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])\.([1-6])\b", text):
                gate = int(match.group(1))
                line = int(match.group(2))
                gate_line_key = (gate, line)
                is_fixed = gate_line_key in self._hd_gate_line_fixing_cache
                text_format = self._format_for_hd_sides(
                    gate_line_sides.get(gate_line_key, set()),
                    fixed=is_fixed,
                )
                if text_format is None:
                    continue
                token_start = match.start()
                if is_fixed:
                    prefix = BODY_RELATIONAL_GLYPHS.get("Exaltation", "")
                    if prefix and text[max(0, match.start() - len(prefix)):match.start()] == prefix:
                        token_start = match.start() - len(prefix)
                self.setFormat(
                    self._qt_index(text, token_start),
                    self._qt_len(text[token_start:match.end()]),
                    text_format,
                )
            return
        gate_sides = self._get_hd_gate_sides()
        for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])-([1-9]|[1-5][0-9]|6[0-4])\b", text):
            for group_index in (1, 2):
                text_format = self._format_for_hd_sides(gate_sides.get(int(match.group(group_index)), set()))
                if text_format is None:
                    continue
                self.setFormat(
                    self._qt_index(text, match.start(group_index)),
                    self._qt_len(match.group(group_index)),
                    text_format,
                )

    def _format_for_hd_synastry_owners(self, owners: set[str]) -> QTextCharFormat | None:
        if "chart_1" in owners:
            return self._hd_synastry_chart_a_format
        if "chart_2" in owners:
            return self._hd_synastry_chart_b_format
        return None

    def _current_synastry_section(self) -> str:
        block = self.currentBlock()
        while block.isValid():
            block_text = block.text().strip()
            if block_text in {"GATES & LINES", "CHANNELS", "AWARENESS STREAMS", "CORE DESIGNATION"}:
                return block_text
            block = block.previous()
        return ""

    def _apply_hd_synastry_gate_line_ownership_color(self, text: str) -> None:
        for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])\.([1-6])\b", text):
            gate = int(match.group(1))
            line = int(match.group(2))
            owners = self._hd_synastry_gate_line_owners.get((gate, line))
            if owners is None:
                owners = self._hd_synastry_gate_owners.get(gate, set())
            text_format = self._format_for_hd_synastry_owners(owners)
            if text_format is None:
                continue
            self.setFormat(
                self._qt_index(text, match.start()),
                self._qt_len(match.group(0)),
                text_format,
            )

    def _apply_hd_synastry_channel_gate_ownership_color(self, text: str) -> None:
        for match in re.finditer(r"\b([1-9]|[1-5][0-9]|6[0-4])-([1-9]|[1-5][0-9]|6[0-4])\b", text):
            for group_index in (1, 2):
                gate = int(match.group(group_index))
                text_format = self._format_for_hd_synastry_owners(
                    self._hd_synastry_gate_owners.get(gate, set())
                )
                if text_format is None:
                    continue
                self.setFormat(
                    self._qt_index(text, match.start(group_index)),
                    self._qt_len(match.group(group_index)),
                    text_format,
                )

    def _apply_defined_centers_format(self, text: str, stripped_text: str) -> None:
        label = ""
        if stripped_text.startswith("Combined Defined Centers:"):
            label = "Combined Defined Centers:"
        elif stripped_text.startswith("Defined Centers:"):
            label = "Defined Centers:"
        if not label:
            return

        self.setFormat(0, self._qt_len(label), self._copper_header_format)
        centers_text = stripped_text[len(label):].strip()
        if not centers_text or centers_text.lower() == "none":
            return
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

    def highlightBlock(self, text: str) -> None:
        self.setFormat(0, self._qt_len(text), self._default_body_format)
        if self.previousBlockState() == 1:
            self.setFormat(0, self._qt_len(text), self._species_subheader_format)
            self.setCurrentBlockState(0)
            return

        for separator in re.finditer(r"…", text):
            self.setFormat(
                self._qt_index(text, separator.start()),
                self._qt_len(separator.group(0)),
                self._column_separator_format,
            )

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
        if self._human_design_synastry_mode:
            if (
                stripped_text
                and stripped_text == stripped_text.upper()
                and any(char.isalpha() for char in stripped_text)
                and all(char.isupper() or not char.isalpha() for char in stripped_text)
            ):
                self.setFormat(0, self._qt_len(text), self._section_format)
                return
            active_synastry_line = re.match(
                r"^.+?'s active gates:", stripped_text, flags=re.IGNORECASE
            ) or re.match(
                r"^.+?'s active channel\(s\):", stripped_text, flags=re.IGNORECASE
            )
            if active_synastry_line:
                previous_active_count = 0
                previous_block = self.currentBlock().previous()
                while previous_block.isValid():
                    previous_text = previous_block.text().strip()
                    if re.match(r"^.+?'s active gates:", previous_text, flags=re.IGNORECASE) or re.match(
                        r"^.+?'s active channel\(s\):", previous_text, flags=re.IGNORECASE
                    ):
                        previous_active_count += 1
                    previous_block = previous_block.previous()
                active_format = (
                    self._hd_synastry_chart_a_format
                    if previous_active_count % 2 == 0
                    else self._hd_synastry_chart_b_format
                )
                self.setFormat(0, self._qt_len(text), active_format)
                return

        if self._human_design_synastry_mode:
            current_section = self._current_synastry_section()
            if current_section == "GATES & LINES":
                self._apply_hd_synastry_gate_line_ownership_color(text)
            elif current_section == "CHANNELS":
                self._apply_hd_synastry_channel_gate_ownership_color(text)

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
                header_format = (
                    self._copper_header_format
                    if prefix in self.HD_HEADERS
                    else self._plain_bold_format
                )
                label_text = f"{prefix}:" if stripped_text.startswith(f"{prefix}:") else prefix
                self.setFormat(0, self._qt_len(label_text), header_format)
                break
        for prefix in self.HD_HEADERS:
            if stripped_text.startswith(f"{prefix} "):
                self.setFormat(0, self._qt_len(prefix), self._copper_header_format)
                break
        if stripped_text in self._hd_center_header_names:
            self.setFormat(0, self._qt_len(stripped_text), self._copper_header_format)
        self._apply_defined_centers_format(text, stripped_text)
        for label in ("Defined Centers:", "Combined Defined Centers:"):
            if not stripped_text.startswith(label):
                continue
            self.setFormat(0, self._qt_len(label), self._copper_header_format)
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
            break
        if re.search(r"\bBody\b", stripped_text) and re.search(r"\bSign\b", stripped_text) and "G/L" in stripped_text:
            for header_token in ("Body", "Sign", "Degree", "Longitude", "G/L", "C", "T", "B"):
                token_start = 0
                while True:
                    token_start = text.find(header_token, token_start)
                    if token_start == -1:
                        break
                    token_end = token_start + len(header_token)
                    left_ok = token_start == 0 or text[token_start - 1].isspace()
                    right_ok = token_end == len(text) or text[token_end].isspace()
                    if left_ok and right_ok:
                        self.setFormat(
                            self._qt_index(text, token_start),
                            self._qt_len(header_token),
                            self._plain_bold_format,
                        )
                    token_start = token_end
        if all(token in stripped_text for token in ("Body", "Sign", "Degree", "Nakshatra", "House", "G.L.")):
            for header_token in ("Body", "Sign", "Degree", "Nakshatra", "House", "G.L."):
                token_start = 0
                while True:
                    token_start = text.find(header_token, token_start)
                    if token_start == -1:
                        break
                    self.setFormat(
                        self._qt_index(text, token_start),
                        self._qt_len(header_token),
                        self._plain_bold_format,
                    )
                    token_start += len(header_token)
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
        self._highlight_planet_glyphs(text)
        for aspect, fmt in self._aspect_formats.items():
            self._highlight_phrase(lowered, aspect, fmt)
        self._highlight_glyphs(text, self._aspect_glyph_formats)
        for sign, fmt in self._sign_formats.items():
            self._highlight_phrase(text, sign, fmt)
        self._highlight_glyphs(text, self._sign_glyph_formats)
        self._highlight_attached_body_relational_glyphs(text)
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
                self._highlight_preceding_body_relational_glyph(text, house_match.start(1), house_fmt)
            sign_fmt = self._make_format(SIGN_COLORS.get(sign_name, CHART_DATA_HIGHLIGHT_COLOR))
            sign_start = text.find(sign_name)
            if sign_start != -1:
                self.setFormat(sign_start, len(sign_name), sign_fmt)
        for match in self._house_token_pattern.finditer(text):
            house_num = match.group(1)
            house_fmt = self._house_formats.get(house_num)
            if house_fmt:
                self.setFormat(match.start(), len(match.group(0)), house_fmt)
                self._highlight_preceding_body_relational_glyph(text, match.start(), house_fmt)
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
                    self._highlight_preceding_body_relational_glyph(text, match.start(), house_fmt)
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

        self._apply_hd_gate_side_color(text, stripped_text)
        self._apply_positions_row_colors(text, stripped_text)
        self._apply_hd_time_variant_colors(text, stripped_text)
        if stripped_text.startswith("Environment:"):
            environment_value = stripped_text.partition(":")[2].strip().removesuffix("ⓘ").strip()
            environment_color_key = environment_value.split("(", 1)[0].strip().title()
            environment_fmt = self._hd_environment_color_formats.get(environment_color_key)
            if environment_fmt and environment_value:
                name_start = text.find(environment_value)
                if name_start >= 0:
                    self.setFormat(self._qt_index(text, name_start), self._qt_len(environment_value), environment_fmt)


    def _current_chart_data_section(self) -> str:
        block = self.currentBlock()
        while block.isValid():
            block_text = block.text().strip()
            normalized_block_text = block_text.upper()
            if normalized_block_text in self._section_header_names:
                return normalized_block_text
            block = block.previous()
        return ""

    def _format_for_sign_cell(self, sign_cell: str) -> QTextCharFormat | None:
        sign_text = sign_cell.strip()
        if not sign_text:
            return None
        sign_format = self._sign_formats.get(sign_text)
        if sign_format is not None:
            return sign_format
        return self._sign_glyph_formats.get(sign_text)

    def _planet_format_for_body_cell(self, body_cell: str) -> QTextCharFormat | None:
        normalized_body_cell = body_cell.strip()
        if not normalized_body_cell:
            return None
        for body, text_format in sorted(
            self._planet_formats.items(), key=lambda item: len(item[0]), reverse=True
        ):
            glyph = PLANET_GLYPHS.get(body)
            if body in normalized_body_cell or (glyph and glyph in normalized_body_cell):
                return text_format
        for alias, text_format in sorted(
            self._planet_alias_formats.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if alias in normalized_body_cell:
                return text_format
        return None

    @staticmethod
    def _split_padded_columns(text: str) -> list[tuple[str, int, int]]:
        columns: list[tuple[str, int, int]] = []
        cursor = 0
        for separator in re.finditer(r"(?: {2,}|\s+[.…]\s+)", text):
            if separator.start() > cursor:
                columns.append((text[cursor:separator.start()], cursor, separator.start()))
            cursor = separator.end()
        if cursor < len(text):
            columns.append((text[cursor:], cursor, len(text)))
        return columns

    def _apply_positions_row_colors(self, text: str, stripped_text: str) -> None:
        if self._current_chart_data_section() != "POSITIONS":
            return
        if not stripped_text or stripped_text == "POSITIONS" or stripped_text == CHART_DATA_DIVIDER:
            return
        columns = self._split_padded_columns(text.rstrip())
        if len(columns) < 4:
            return

        has_info_icon = columns[-1][0].strip() == "ⓘ"
        data_columns = columns[:-1] if has_info_icon else columns
        if len(data_columns) < 4:
            return

        body_text = data_columns[0][0].strip()
        body_format = self._planet_format_for_body_cell(body_text)
        body_prefix_match = re.match(r"^\s*[PD]\.", text)
        if body_prefix_match and body_format is not None:
            self.setFormat(
                self._qt_index(text, body_prefix_match.start()),
                self._qt_len(text[body_prefix_match.start():body_prefix_match.end()]),
                body_format,
            )

        sign_text, _sign_start, _sign_end = data_columns[1]
        sign_format = self._format_for_sign_cell(sign_text)

        if sign_format is not None:
            degree_text, degree_start, degree_end = data_columns[2]
            degree_value = degree_text.strip()
            is_standard_degree = re.fullmatch(r"\d{1,2}°\d{2}'(?:\s+\(Я\))?", degree_value)
            is_hd_longitude = re.fullmatch(r"\d{1,3}(?:\.\d+)?°", degree_value)
            if is_standard_degree or is_hd_longitude:
                self.setFormat(
                    self._qt_index(text, degree_start),
                    self._qt_len(text[degree_start:degree_end]),
                    sign_format,
                )

            if is_hd_longitude:
                for value_text, value_start, value_end in data_columns[3:7]:
                    value_match = re.search(r"\S+(?:->\S+)*", value_text)
                    if value_match is None:
                        continue
                    self.setFormat(
                        self._qt_index(text, value_start + value_match.start()),
                        self._qt_len(value_text[value_match.start():value_match.end()]),
                        sign_format,
                    )
            else:
                gate_line_column: tuple[str, int, int] | None = data_columns[5] if len(data_columns) >= 6 else None
                if gate_line_column is not None:
                    gate_line_text, gate_line_start, gate_line_end = gate_line_column
                    if re.fullmatch(
                        r"(?:[1-9]|[1-5][0-9]|6[0-4])\.[1-6](?:->(?:[1-9]|[1-5][0-9]|6[0-4])\.[1-6])*",
                        gate_line_text.strip(),
                    ):
                        self.setFormat(
                            self._qt_index(text, gate_line_start),
                            self._qt_len(text[gate_line_start:gate_line_end]),
                            sign_format,
                        )

        icon_column = columns[-1] if has_info_icon else None
        if icon_column is None and columns:
            last_text, last_start, _last_end = columns[-1]
            if "ⓘ" in last_text:
                icon_column = (last_text, last_start, _last_end)
        if icon_column is not None:
            icon_text, icon_start, _icon_end = icon_column
            icon_offset = icon_text.find("ⓘ")
            if icon_offset != -1 and body_format is not None:
                self.setFormat(
                    self._qt_index(text, icon_start + icon_offset),
                    self._qt_len("ⓘ"),
                    body_format,
                )

    def _highlight_planet_glyphs(self, text: str) -> None:
        self._highlight_glyphs(text, self._planet_glyph_formats)

    def _highlight_glyphs(self, text: str, glyph_formats: dict[str, QTextCharFormat]) -> None:
        for glyph, text_format in glyph_formats.items():
            start = 0
            while True:
                index = text.find(glyph, start)
                if index == -1:
                    break
                if glyph.isalnum():
                    before_ok = index == 0 or not text[index - 1].isalnum()
                    after_index = index + len(glyph)
                    after_ok = after_index >= len(text) or not text[after_index].isalnum()
                    if not (before_ok and after_ok):
                        start = index + len(glyph)
                        continue
                self.setFormat(
                    self._qt_index(text, index),
                    self._qt_len(glyph),
                    text_format,
                )
                start = index + len(glyph)

    def _highlight_attached_body_relational_glyphs(self, text: str) -> None:
        for sign, text_format in self._sign_formats.items():
            start = 0
            while True:
                index = text.find(sign, start)
                if index == -1:
                    break
                self._highlight_preceding_body_relational_glyph(text, index, text_format)
                start = index + len(sign)
        for glyph, text_format in self._sign_glyph_formats.items():
            start = 0
            while True:
                index = text.find(glyph, start)
                if index == -1:
                    break
                self._highlight_preceding_body_relational_glyph(text, index, text_format)
                start = index + len(glyph)

    def _highlight_preceding_body_relational_glyph(
        self,
        text: str,
        attachment_start: int,
        text_format: QTextCharFormat,
    ) -> None:
        prefix_text = text[:attachment_start].rstrip()
        match = self._body_relational_glyph_pattern.search(prefix_text)
        if match is None or match.end() != len(prefix_text):
            return
        self.setFormat(
            self._qt_index(text, match.start()),
            self._qt_len(match.group(0)),
            text_format,
        )

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
    human_design_synastry_mode: bool = False,
) -> ChartSummaryHighlighter:
    """Attach the shared chart-data highlighter to an output widget."""
    highlighter = ChartSummaryHighlighter(
        output_widget.document(),
        emphasize_dnd_class_headers=emphasize_dnd_class_headers,
        emphasize_species_info_headers=emphasize_species_info_headers,
        human_design_synastry_mode=human_design_synastry_mode,
    )
    output_widget._summary_highlighter = highlighter
    return highlighter
