"""Helpers for Similar Charts list rendering and popout UI."""

from __future__ import annotations

import html
import re
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.core.interpretations import HOUSE_COLORS, NAKSHATRA_PLANET_COLOR, PLANET_COLORS, SIGN_COLORS
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra, sign_for_longitude
from ephemeraldaddy.gui.features.charts.text_summary import _aspect_label


SIMILAR_INFO_TARGET_PREFIX = "sim-info"
SIMILARITY_SECTION_HEADER_COLOR = "#B87333"
_PLACEMENT_BODIES: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "AS",
    "MC",
)
_ASPECT_COLORS: dict[str, str] = {
    "conjunction": "#c7a56a",
    "sextile": "#6b8ba4",
    "square": "#8d6e63",
    "trine": "#6b705c",
    "opposition": "#c26d3a",
}
_SIMILARITY_BODY_TEXT_COLOR = "#B87333"
_PLANET_COLOR_MAP: dict[str, str] = {str(name): str(color) for name, color in PLANET_COLORS.items() if color}
_SIGN_COLOR_MAP: dict[str, str] = {str(name): str(color) for name, color in SIGN_COLORS.items() if color}
_NAKSHATRA_COLOR_MAP: dict[str, str] = {
    str(nakshatra): str(color)
    for nakshatra, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()
    if color
}
_HOUSE_COLOR_MAP: dict[str, str] = {str(key): str(color) for key, color in HOUSE_COLORS.items() if color}
_SIMILARITY_TOKEN_COLORS: dict[str, str] = {}
_SIMILARITY_TOKEN_COLORS.update(_PLANET_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_SIGN_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_NAKSHATRA_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_ASPECT_COLORS)
_SIMILARITY_TOKEN_COLORS.update(
    {str(center): str(data.get("color") or "#cccccc") for center, data in HD_CENTERS.items()}
)


def _house_for_longitude(houses: list[float] | None, longitude: float | None) -> int | None:
    if not houses or longitude is None or len(houses) < 12:
        return None
    normalized = float(longitude) % 360.0
    bounds = [float(cusp) % 360.0 for cusp in houses[:12]]
    for index in range(12):
        start = bounds[index]
        end = bounds[(index + 1) % 12]
        in_span = start <= normalized < end if start < end else normalized >= start or normalized < end
        if in_span:
            return index + 1
    return None


def _safe_chart_name(chart: Any, fallback: str) -> str:
    return str(getattr(chart, "name", "") or fallback).strip() or fallback


def _common_placement_labels(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    use_houses = bool(getattr(subject_chart, "houses", None)) and bool(getattr(compared_chart, "houses", None))
    matches: list[str] = []
    for body in _PLACEMENT_BODIES:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is None or compared_lon is None:
            continue
        subject_sign = sign_for_longitude(subject_lon)
        compared_sign = sign_for_longitude(compared_lon)
        if subject_sign != compared_sign:
            continue
        label = f"{body} in {subject_sign}"
        if use_houses:
            subject_house = _house_for_longitude(getattr(subject_chart, "houses", None), subject_lon)
            compared_house = _house_for_longitude(getattr(compared_chart, "houses", None), compared_lon)
            if subject_house is not None and compared_house is not None and subject_house == compared_house:
                label = f"{label} (House {subject_house})"
        matches.append(label)
    return matches


def _common_aspect_labels(subject_chart: Any, compared_chart: Any) -> list[str]:
    def _canonical(aspect: dict[str, Any]) -> tuple[tuple[str, str], str] | None:
        p1 = str(aspect.get("p1") or "").strip()
        p2 = str(aspect.get("p2") or "").strip()
        aspect_type = str(aspect.get("type") or "").strip().lower()
        if not p1 or not p2 or not aspect_type:
            return None
        left, right = sorted((p1, p2))
        return (left, right), aspect_type

    subject_keys = {
        key
        for aspect in (getattr(subject_chart, "aspects", None) or [])
        if (key := _canonical(aspect)) is not None
    }
    common_keys = {
        key
        for aspect in (getattr(compared_chart, "aspects", None) or [])
        if (key := _canonical(aspect)) is not None and key in subject_keys
    }
    labels: list[str] = []
    for (left, right), aspect_type in sorted(common_keys):
        labels.append(f"{left} {_aspect_label(aspect_type).lower()} {right}")
    return labels


def _distribution_summary(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    elements_by_sign = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    modes_by_sign = {
        "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
        "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
        "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
    }
    body_subset = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    subject_element_counts: dict[str, int] = {}
    compared_element_counts: dict[str, int] = {}
    subject_mode_counts: dict[str, int] = {}
    compared_mode_counts: dict[str, int] = {}
    for body in body_subset:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is not None:
            sign = sign_for_longitude(subject_lon)
            if sign in elements_by_sign:
                subject_element_counts[elements_by_sign[sign]] = subject_element_counts.get(elements_by_sign[sign], 0) + 1
                subject_mode_counts[modes_by_sign[sign]] = subject_mode_counts.get(modes_by_sign[sign], 0) + 1
        if compared_lon is not None:
            sign = sign_for_longitude(compared_lon)
            if sign in elements_by_sign:
                compared_element_counts[elements_by_sign[sign]] = compared_element_counts.get(elements_by_sign[sign], 0) + 1
                compared_mode_counts[modes_by_sign[sign]] = compared_mode_counts.get(modes_by_sign[sign], 0) + 1

    shared_elements = sorted(
        element
        for element in {"Fire", "Earth", "Air", "Water"}
        if subject_element_counts.get(element, 0) > 0 and compared_element_counts.get(element, 0) > 0
    )
    shared_modes = sorted(
        mode
        for mode in {"Cardinal", "Fixed", "Mutable"}
        if subject_mode_counts.get(mode, 0) > 0 and compared_mode_counts.get(mode, 0) > 0
    )
    lines: list[str] = []
    if shared_elements:
        lines.append(
            "Shared elemental emphasis: "
            + ", ".join(
                f"{element} ({subject_element_counts.get(element, 0)} vs {compared_element_counts.get(element, 0)})"
                for element in shared_elements
            )
        )
    if shared_modes:
        lines.append(
            "Shared modality emphasis: "
            + ", ".join(
                f"{mode} ({subject_mode_counts.get(mode, 0)} vs {compared_mode_counts.get(mode, 0)})"
                for mode in shared_modes
            )
        )
    return lines


def _nakshatra_overlap_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    same_body_matches: list[str] = []
    for body in _PLACEMENT_BODIES:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is None or compared_lon is None:
            continue
        subject_nak = get_nakshatra(subject_lon)
        compared_nak = get_nakshatra(compared_lon)
        if subject_nak and subject_nak == compared_nak:
            same_body_matches.append(f"{body} in {subject_nak}")
    return sorted(same_body_matches)


def _defined_center_overlap_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    def _centers(chart: Any) -> set[str]:
        existing = {
            str(center).strip()
            for center in (getattr(chart, "human_design_defined_centers", None) or [])
            if str(center).strip()
        }
        if existing:
            return existing
        try:
            result = build_human_design_result(chart)
            return {
                str(center).strip()
                for center in getattr(result, "defined_centers", [])
                if str(center).strip()
            }
        except Exception:
            return set()

    overlap = sorted(_centers(subject_chart) & _centers(compared_chart))
    return overlap


def is_similar_info_target(target: str) -> bool:
    return str(target or "").strip().startswith(f"{SIMILAR_INFO_TARGET_PREFIX}:")


def make_similar_info_target(*, info_link_prefix: str, chart_id: int) -> str:
    return f"{info_link_prefix}:{int(chart_id)}"


def map_similar_info_targets(
    *,
    matches: list[Any],
    info_link_prefix: str,
) -> dict[str, Any]:
    return {
        make_similar_info_target(info_link_prefix=info_link_prefix, chart_id=int(match.chart_id)): match
        for match in matches
    }


def build_similarity_reasoning_panel_text(
    *,
    match: Any,
    subject_name: str,
    subject_chart: Any | None = None,
    compared_chart: Any | None = None,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
) -> str:
    _band_label, _band_color = resolve_similarity_band(float(getattr(match, "score", 0.0)) * 100.0)
    compared_name = _safe_chart_name(
        compared_chart,
        str(getattr(match, "chart_name", "") or f"Chart #{getattr(match, 'chart_id', '?')}"),
    )
    subject_title = _safe_chart_name(subject_chart, subject_name or "Current chart")
    lines: list[str] = []
    if subject_chart is not None and compared_chart is not None:
        placement_labels = _common_placement_labels(subject_chart, compared_chart)
        lines.append("Placements in common:")
        lines.append("; ".join(placement_labels) if placement_labels else "No exact same-sign placements found in tracked bodies.")

        aspect_labels = _common_aspect_labels(subject_chart, compared_chart)
        lines.append("")
        lines.append("Aspects in common:")
        lines.append("; ".join(aspect_labels) if aspect_labels else "No shared aspect signatures were found.")

        distribution_lines = _distribution_summary(subject_chart, compared_chart)
        lines.append("")
        lines.append("Distribution similarities:")
        lines.append(" | ".join(distribution_lines) if distribution_lines else "No clear elemental/modality overlap was detected.")

        nak_lines = _nakshatra_overlap_lines(subject_chart, compared_chart)
        lines.append("")
        lines.append("Nakshatras:")
        lines.append("; ".join(nak_lines) if nak_lines else "No same-body nakshatra overlaps were found.")

        centers = _defined_center_overlap_lines(subject_chart, compared_chart)
        lines.append("")
        lines.append("Defined centers in common:")
        lines.append(", ".join(centers) if centers else "No overlapping defined centers were found.")
    else:
        lines.append("Detailed similarity details are unavailable because one or both charts could not be loaded.")
    return "\n".join(
        [
            "SIMILARITY ANALYSIS",
            "",
            f"Charts: {subject_title} ↔ {compared_name}",
            "\n".join(lines),
        ]
    )


def build_similarity_reasoning_panel_html(
    *,
    match: Any,
    subject_name: str,
    subject_chart: Any | None = None,
    compared_chart: Any | None = None,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
) -> str:
    def _apply_word_colors(text_value: str, lookup: dict[str, str], *, weight: str = "400") -> str:
        if not text_value or not lookup:
            return html.escape(text_value)
        parts = sorted(lookup.keys(), key=len, reverse=True)
        pattern = r"\b(" + "|".join(re.escape(token) for token in parts) + r")\b"
        chunks: list[str] = []
        cursor = 0
        for match in re.finditer(pattern, text_value):
            if match.start() > cursor:
                chunks.append(html.escape(text_value[cursor:match.start()]))
            token = match.group(0)
            color = lookup.get(token)
            if color:
                chunks.append(
                    f"<span style='color:{html.escape(color)};font-weight:{weight}'>{html.escape(token)}</span>"
                )
            else:
                chunks.append(html.escape(token))
            cursor = match.end()
        if cursor < len(text_value):
            chunks.append(html.escape(text_value[cursor:]))
        return "".join(chunks)

    def _colorize_body_line(raw_line: str) -> str:
        colored = _apply_word_colors(raw_line, _SIMILARITY_TOKEN_COLORS)
        colored = re.sub(
            r"\bHouse\s+(1[0-2]|[1-9])\b",
            lambda m: (
                f"House <span style='color:{html.escape(_HOUSE_COLOR_MAP.get(m.group(1), '#cccccc'))};font-weight:400'>"
                f"{html.escape(m.group(1))}</span>"
            ),
            colored,
        )
        return colored

    text = build_similarity_reasoning_panel_text(
        match=match,
        subject_name=subject_name,
        subject_chart=subject_chart,
        compared_chart=compared_chart,
        resolve_similarity_band=resolve_similarity_band,
    )
    lines = text.splitlines()
    html_lines: list[str] = []
    for raw_line in lines:
        line = html.escape(raw_line)
        if raw_line.startswith("SIMILARITY ANALYSIS"):
            html_lines.append(
                f"<div style='font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>{line}</div>"
            )
            continue
        if raw_line in {"Placements in common:", "Aspects in common:", "Distribution similarities:", "Nakshatras:", "Defined centers in common:"}:
            html_lines.append(
                f"<div style='margin-top:6px;font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>{line}</div>"
            )
            continue
        if raw_line.startswith("Charts: "):
            html_lines.append(
                f"<div><span style='font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>Charts:</span> "
                f"{html.escape(raw_line.replace('Charts: ', '', 1))}</div>"
            )
            continue
        if raw_line and "," in raw_line and all(token.strip() in HD_CENTERS for token in raw_line.split(",")):
            colored = []
            for center_name in [token.strip() for token in raw_line.split(",")]:
                color = str(HD_CENTERS.get(center_name, {}).get("color") or "#cccccc")
                colored.append(f"<span style='color:{html.escape(color)};font-weight:600'>{html.escape(center_name)}</span>")
            html_lines.append("<div>" + ", ".join(colored) + "</div>")
            continue
        html_lines.append(
            f"<div style='color:{_SIMILARITY_BODY_TEXT_COLOR};font-weight:400'>"
            f"{_colorize_body_line(raw_line) if raw_line else '&nbsp;'}</div>"
        )
    return "".join(html_lines)

def load_similar_chart_candidates(
    *,
    rows: list[tuple[Any, ...]],
    current_chart_id: int | None,
    load_chart_by_id: Callable[[int], Any],
) -> list[tuple[int, Any]]:
    candidates: list[tuple[int, Any]] = []
    for row in rows:
        chart_id = int(row[0])
        is_placeholder = bool(row[15]) if len(row) > 15 else False
        if current_chart_id is not None and chart_id == current_chart_id:
            continue
        if is_placeholder:
            continue
        try:
            candidate = load_chart_by_id(chart_id)
        except Exception:
            continue
        candidates.append((chart_id, candidate))
    return candidates


def render_similar_match_blocks(
    *,
    matches: list[Any],
    highlight_color: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    info_link_prefix: str = "sim-info",
) -> str:
    if not matches:
        return "No charts found."
    blocks: list[str] = []
    for rank, match in enumerate(matches, start=1):
        safe_name = html.escape(str(match.chart_name))
        similarity_percent = float(match.score) * 100.0
        band_label, band_color = resolve_similarity_band(similarity_percent)
        extra_bits: list[str] = []
        if getattr(match, "nakshatra_score", None) is not None:
            extra_bits.append(f"nakshatra {float(match.nakshatra_score) * 100.0:.0f}%")
        if getattr(match, "hd_centers_score", None) is not None:
            extra_bits.append(f"defined centers {float(match.hd_centers_score) * 100.0:.0f}%")
        if getattr(match, "dominance_score", None) is not None:
            extra_bits.insert(0, f"dominance {float(match.dominance_score) * 100.0:.0f}%")
        extra_suffix = f", {', '.join(extra_bits)}" if extra_bits else ""
        blocks.append(
            (
                f'<span style="font-weight: bold; color: {highlight_color};">{rank}.</span> '
                f'#{match.chart_id} — <a href="{match.chart_id}">{safe_name}</a> '
                f'<a href="{make_similar_info_target(info_link_prefix=info_link_prefix, chart_id=int(match.chart_id))}">ⓘ</a><br>'
                f'Similarity <span style="color: {band_color}; font-weight: 600;">'
                f"{similarity_percent:.1f}% ({band_label})</span> "
                f'<span style="font-weight: 400; color: {_SIMILARITY_BODY_TEXT_COLOR};">'
                f"(placements {match.placement_score * 100.0:.0f}%, "
                f"aspects {match.aspect_score * 100.0:.0f}%, "
                f"distribution {match.distribution_score * 100.0:.0f}%{extra_suffix})"
                "</span>"
            )
        )
    return "<br><br>".join(blocks)


def build_similar_charts_popout_dialog(
    *,
    parent: QWidget,
    subject_name: str,
    most_similar_matches: list[Any],
    least_similar_matches: list[Any],
    on_link_activated: Callable[[QDialog, str], None],
    header_style: str,
    output_style: str,
    highlight_color: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    info_link_prefix: str = "sim-info",
    configure_splitter: Callable[[QSplitter], None] | None = None,
) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Similar Charts — {subject_name}")
    dialog.setModal(False)
    dialog.resize(860, 700)
    layout = QVBoxLayout(dialog)

    title_label = QLabel(f"Similar Charts for {subject_name}")
    title_label.setStyleSheet(header_style)
    layout.addWidget(title_label)

    splitter = QSplitter(Qt.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(6)
    if configure_splitter is not None:
        configure_splitter(splitter)
    layout.addWidget(splitter, 1)

    info_panel = QWidget()
    info_layout = QVBoxLayout(info_panel)
    info_layout.setContentsMargins(0, 0, 0, 0)
    info_layout.setSpacing(6)
    info_header = QLabel("Chart Info")
    info_header.setStyleSheet(header_style)
    info_layout.addWidget(info_header)
    info_output = QLabel("Click ⓘ next to a chart to view similarity analysis.")
    info_output.setWordWrap(True)
    info_output.setTextInteractionFlags(Qt.TextBrowserInteraction)
    info_output.setOpenExternalLinks(False)
    info_output.setStyleSheet(output_style)
    info_layout.addWidget(info_output, 1)
    dialog._similar_chart_popout_info_output = info_output
    splitter.addWidget(info_panel)

    list_splitter = QSplitter(Qt.Horizontal)
    list_splitter.setChildrenCollapsible(False)
    list_splitter.setHandleWidth(6)
    if configure_splitter is not None:
        configure_splitter(list_splitter)
    splitter.addWidget(list_splitter)

    def _panel(title: str, matches: list[Any], panel_key: str) -> QWidget:
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)
        header_label = QLabel(title)
        header_label.setStyleSheet(header_style)
        panel_layout.addWidget(header_label)

        result_label = QLabel()
        result_label.setWordWrap(True)
        result_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        result_label.setOpenExternalLinks(False)
        result_label.linkActivated.connect(lambda target: on_link_activated(dialog, target))
        result_label.setStyleSheet(output_style)
        result_label.setText(
            render_similar_match_blocks(
                matches=matches,
                highlight_color=highlight_color,
                resolve_similarity_band=resolve_similarity_band,
                info_link_prefix=f"{info_link_prefix}:{panel_key}",
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(result_label)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        panel_layout.addWidget(scroll, 1)
        return panel_widget

    list_splitter.addWidget(_panel("Top 25 Most Similar charts", most_similar_matches, "most"))
    list_splitter.addWidget(_panel("Top 25 Least Similar Charts", least_similar_matches, "least"))
    splitter.setSizes([320, 860])
    list_splitter.setSizes([430, 430])
    return dialog
