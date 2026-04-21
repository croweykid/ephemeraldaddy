"""Helpers for Similar Charts list rendering and popout UI."""

from __future__ import annotations

import html
import re
from typing import Any, Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.analysis.get_astro_twin import (
    BODY_WEIGHTS,
    CORE_BODIES,
    NATAL_WEIGHT,
    PLACEMENT_WEIGHTING_MODE_HYBRID,
    SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE,
    SIMILAR_CHARTS_ALGORITHM_CUSTOM,
    SimilarityCalculatorSettings,
    _placement_body_weights,
    chart_similarity_score_custom,
    normalize_placement_weighting_mode,
    normalize_similar_charts_algorithm_mode,
)
from ephemeraldaddy.core.interpretations import (
    ASPECT_SCORE_WEIGHTS,
    ELEMENT_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    SIGN_COLORS,
    MODE_COLORS,
    aspect_pair_weight,
    aspect_score,
)
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra, sign_for_longitude
from ephemeraldaddy.gui.features.charts.text_summary import _aspect_label
from ephemeraldaddy.gui.style import DEFAULT_DROPDOWN_STYLE


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
_SIMILARITY_LIST_TEXT_COLOR = "#B87333"
_SIMILARITY_PANEL_BODY_TEXT_COLOR = "#FFFFFF"
_SIMILARITY_COMPONENT_LABELS: dict[str, str] = {
    "placement": "placements",
    "aspect": "aspects",
    "distribution": "distribution (element/mode)",
    "combined_dominance": "dominance (sign/body/house)",
    "nakshatra_placement": "nakshatra placement",
    "nakshatra_dominance": "nakshatra dominance",
    "defined_centers": "defined centers (HD)",
    "human_design_gates": "active gates (HD)",
}
_PLANET_COLOR_MAP: dict[str, str] = {str(name): str(color) for name, color in PLANET_COLORS.items() if color}
_SIGN_COLOR_MAP: dict[str, str] = {str(name): str(color) for name, color in SIGN_COLORS.items() if color}
_NAKSHATRA_COLOR_MAP: dict[str, str] = {
    str(nakshatra): str(color)
    for nakshatra, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()
    if color
}
_HOUSE_COLOR_MAP: dict[str, str] = {str(key): str(color) for key, color in HOUSE_COLORS.items() if color}
_ELEMENT_COLOR_MAP: dict[str, str] = {str(name): str(color) for name, color in ELEMENT_COLORS.items() if color}
_SIMILARITY_TOKEN_COLORS: dict[str, str] = {}
_SIMILARITY_TOKEN_COLORS.update(_PLANET_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_SIGN_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_NAKSHATRA_COLOR_MAP)
_SIMILARITY_TOKEN_COLORS.update(_ELEMENT_COLOR_MAP)
for mode_name, mode_color in MODE_COLORS.items():
    normalized_mode = str(mode_name).strip()
    if not normalized_mode:
        continue
    _SIMILARITY_TOKEN_COLORS[normalized_mode] = str(mode_color)
    _SIMILARITY_TOKEN_COLORS[normalized_mode.title()] = str(mode_color)
    _SIMILARITY_TOKEN_COLORS[normalized_mode.upper()] = str(mode_color)
_SIMILARITY_TOKEN_COLORS.update(_ASPECT_COLORS)
_SIMILARITY_TOKEN_COLORS.update(
    {str(center): str(data.get("color") or "#cccccc") for center, data in HD_CENTERS.items()}
)
_ANGLE_POINTS: frozenset[str] = frozenset({"AS", "IC", "MC", "DS"})
_DEFAULT_ALGORITHM_COMPONENT_WEIGHTS: dict[str, float] = {
    "placement": 0.38,
    "aspect": 0.27,
    "distribution": 0.10,
    "combined_dominance": 0.25,
}
_SIGN_SEQUENCE: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
_DOMINANCE_BODIES: tuple[str, ...] = tuple(body for body in CORE_BODIES if body not in {"AS", "IC", "DS", "MC"})


def build_similar_charts_export_rows_from_matches(
    *,
    matches: list[Any],
    resolve_similarity_band: Callable[[float], tuple[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, match in enumerate(matches, start=1):
        similarity_percent = float(getattr(match, "score", 0.0) or 0.0) * 100.0
        band_label, _band_color = resolve_similarity_band(similarity_percent)
        rows.append(
            {
                "rank": rank,
                "chart_id": int(getattr(match, "chart_id", 0) or 0),
                "chart_name": str(getattr(match, "chart_name", "") or ""),
                "similarity_percent": round(similarity_percent, 1),
                "similarity_band": band_label,
                "placement_percent": round(float(getattr(match, "placement_score", 0.0) or 0.0) * 100.0, 1),
                "aspect_percent": round(float(getattr(match, "aspect_score", 0.0) or 0.0) * 100.0, 1),
                "distribution_percent": round(float(getattr(match, "distribution_score", 0.0) or 0.0) * 100.0, 1),
                "dominance_percent": (
                    round(float(getattr(match, "dominance_score", 0.0) or 0.0) * 100.0, 1)
                    if getattr(match, "dominance_score", None) is not None
                    else None
                ),
            }
        )
    return rows


def build_similar_charts_export_lines(
    *,
    subject_name: str,
    rows: list[dict[str, Any]],
    is_markdown: bool,
) -> list[str]:
    lines: list[str] = []
    if is_markdown:
        lines.append(f"# Similar Charts for {subject_name}")
        lines.append("")
        lines.append(
            "| Rank | Chart ID | Chart | Similarity | Band | Placement | Aspects | Distribution | Dominance |"
        )
        lines.append("|---:|---:|---|---:|---|---:|---:|---:|---:|")
        for row in rows:
            lines.append(
                f"| {row['rank']} | {row['chart_id']} | {row['chart_name']} | "
                f"{row['similarity_percent']:.1f}% | {row.get('similarity_band', '')} | {row['placement_percent']:.1f}% | "
                f"{row['aspect_percent']:.1f}% | {row['distribution_percent']:.1f}% | {float(row.get('dominance_percent') or 0.0):.1f}% |"
            )
        return lines

    lines.append(f"Similar Charts for {subject_name}")
    lines.append("")
    for row in rows:
        lines.append(
            f"{row['rank']}. #{row['chart_id']} — {row['chart_name']}: "
            f"Similarity {row['similarity_percent']:.1f}% "
            f"[{row.get('similarity_band', 'unclassified')}] "
            f"(placements {row['placement_percent']:.1f}%, "
            f"aspects {row['aspect_percent']:.1f}%, "
            f"distribution {row['distribution_percent']:.1f}%, "
            f"dominance {float(row.get('dominance_percent') or 0.0):.1f}%)"
        )
    return lines


def _is_tautological_node_opposition(p1: str, p2: str, aspect_type: str) -> bool:
    if str(aspect_type).strip().lower() != "opposition":
        return False
    return {str(p1).strip(), str(p2).strip()} == {"Rahu", "Ketu"}


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

def _chart_possessive_label(chart: Any, fallback: str) -> str:
    name = _safe_chart_name(chart, fallback)
    suffix = "'" if name.endswith("s") else "'s"
    return f"{name}{suffix} chart"

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


def _common_placement_labels_with_weight_details(
    subject_chart: Any,
    compared_chart: Any,
    *,
    placement_weighting_mode: str,
) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    use_houses = bool(getattr(subject_chart, "houses", None)) and bool(getattr(compared_chart, "houses", None))
    normalized_mode = normalize_placement_weighting_mode(placement_weighting_mode)
    effective_weights = _placement_body_weights(subject_chart, normalized_mode)
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
        base_weight = max(0.0, float(NATAL_WEIGHT.get(body, 1.0)))
        effective_weight = max(0.0, float(effective_weights.get(body, base_weight)))
        multiplier = (effective_weight / base_weight) if base_weight > 0.0 else 1.0
        detail = (
            f"(base {base_weight:.2f} × mode multiplier {multiplier:.2f} = {effective_weight:.2f}; "
            f"sign +{effective_weight:.2f} placement pts"
        )
        label = f"{body} in {subject_sign}"
        if use_houses:
            subject_house = _house_for_longitude(getattr(subject_chart, "houses", None), subject_lon)
            compared_house = _house_for_longitude(getattr(compared_chart, "houses", None), compared_lon)
            house_weight = effective_weight * 0.65
            if subject_house is not None and compared_house is not None and subject_house == compared_house:
                label = f"{label} (House {subject_house})"
                detail = f"{detail}; house +{house_weight:.2f} placement pts)"
            else:
                detail = f"{detail}; house match not met, +0.00/{house_weight:.2f} house pts)"
        else:
            detail = f"{detail}; house component unavailable)"
        if normalized_mode == PLACEMENT_WEIGHTING_MODE_HYBRID:
            detail = f"{detail[:-1]}; luminary hybrid bonus applied at section level)"
        matches.append(f"{label} {detail}")
    return matches


def _differing_placement_labels(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    use_houses = bool(getattr(subject_chart, "houses", None)) and bool(getattr(compared_chart, "houses", None))
    differences: list[str] = []
    for body in _PLACEMENT_BODIES:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is None or compared_lon is None:
            continue
        subject_sign = sign_for_longitude(subject_lon)
        compared_sign = sign_for_longitude(compared_lon)
        if subject_sign != compared_sign:
            differences.append(f"{body}: {subject_sign} vs {compared_sign}")
            continue
        if use_houses:
            subject_house = _house_for_longitude(getattr(subject_chart, "houses", None), subject_lon)
            compared_house = _house_for_longitude(getattr(compared_chart, "houses", None), compared_lon)
            if (
                subject_house is not None
                and compared_house is not None
                and subject_house != compared_house
            ):
                differences.append(
                    f"{body} in {subject_sign}: House {subject_house} vs House {compared_house}"
                )
    return differences


def _differing_placement_labels_with_weight_details(
    subject_chart: Any,
    compared_chart: Any,
    *,
    placement_weighting_mode: str,
) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    use_houses = bool(getattr(subject_chart, "houses", None)) and bool(getattr(compared_chart, "houses", None))
    effective_weights = _placement_body_weights(subject_chart, placement_weighting_mode)
    differences: list[str] = []
    for body in _PLACEMENT_BODIES:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is None or compared_lon is None:
            continue
        subject_sign = sign_for_longitude(subject_lon)
        compared_sign = sign_for_longitude(compared_lon)
        base_weight = max(0.0, float(NATAL_WEIGHT.get(body, 1.0)))
        effective_weight = max(0.0, float(effective_weights.get(body, base_weight)))
        multiplier = (effective_weight / base_weight) if base_weight > 0.0 else 1.0
        house_weight = effective_weight * 0.65
        if subject_sign != compared_sign:
            differences.append(
                f"{body}: {subject_sign} vs {compared_sign} "
                f"(base {base_weight:.2f} × mode multiplier {multiplier:.2f} = {effective_weight:.2f}; "
                f"sign +0.00/{effective_weight:.2f} placement pts)"
            )
            continue
        if use_houses:
            subject_house = _house_for_longitude(getattr(subject_chart, "houses", None), subject_lon)
            compared_house = _house_for_longitude(getattr(compared_chart, "houses", None), compared_lon)
            if (
                subject_house is not None
                and compared_house is not None
                and subject_house != compared_house
            ):
                differences.append(
                    f"{body} in {subject_sign}: House {subject_house} vs House {compared_house} "
                    f"(base {base_weight:.2f} × mode multiplier {multiplier:.2f} = {effective_weight:.2f}; "
                    f"sign +{effective_weight:.2f} pts, house +0.00/{house_weight:.2f} pts)"
                )
    return differences


def _common_aspect_labels(subject_chart: Any, compared_chart: Any) -> list[str]:
    def _canonical(aspect: dict[str, Any]) -> tuple[tuple[str, str], str] | None:
        p1 = str(aspect.get("p1") or "").strip()
        p2 = str(aspect.get("p2") or "").strip()
        aspect_type = str(aspect.get("type") or "").strip().lower()
        if not p1 or not p2 or not aspect_type:
            return None
        if p1 in _ANGLE_POINTS and p2 in _ANGLE_POINTS:
            return None
        if _is_tautological_node_opposition(p1, p2, aspect_type):
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


def _common_aspect_labels_with_relevance(subject_chart: Any, compared_chart: Any) -> list[tuple[str, float]]:
    def _canonical(aspect: dict[str, Any]) -> tuple[tuple[str, str], str] | None:
        p1 = str(aspect.get("p1") or "").strip()
        p2 = str(aspect.get("p2") or "").strip()
        aspect_type = str(aspect.get("type") or "").strip().lower()
        if not p1 or not p2 or not aspect_type:
            return None
        if p1 in _ANGLE_POINTS and p2 in _ANGLE_POINTS:
            return None
        if _is_tautological_node_opposition(p1, p2, aspect_type):
            return None
        left, right = sorted((p1, p2))
        return (left, right), aspect_type

    def _aspect_base_weight(chart: Any, key: tuple[tuple[str, str], str]) -> float:
        (left, right), aspect_type = key
        planet_weights = getattr(chart, "dominant_planet_weights", None) or None
        matching_orbs: list[float] = []
        for aspect in (getattr(chart, "aspects", None) or []):
            canonical = _canonical(aspect)
            if canonical != key:
                continue
            matching_orbs.append(abs(float(aspect.get("delta", 0.0) or 0.0)))
        source_aspect_scores = [
            max(
                0.0,
                float(
                    aspect_score(
                        {"p1": left, "p2": right, "type": aspect_type, "delta": orb},
                        planet_weights=planet_weights,
                    )
                ),
            )
            for orb in matching_orbs
        ]
        orb_weighted_base = max(source_aspect_scores, default=0.0)
        fallback_base = max(
            (
                max(0.0, float(ASPECT_SCORE_WEIGHTS.get(str(aspect_type).replace(" ", "_").lower(), 0.0)))
                * max(0.0, float(aspect_pair_weight(left, right, planet_weights=planet_weights)))
            ),
            0.0,
        )
        return orb_weighted_base if orb_weighted_base > 0.0 else fallback_base

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
    sorted_keys = sorted(common_keys)
    if not sorted_keys:
        return []

    weighted_rows: list[tuple[str, float]] = []
    raw_weights: list[float] = []
    for key in sorted_keys:
        (left, right), aspect_type = key
        label = f"{left} {_aspect_label(aspect_type).lower()} {right}"
        subject_weight = _aspect_base_weight(subject_chart, key)
        compared_weight = _aspect_base_weight(compared_chart, key)
        raw_weight = (subject_weight + compared_weight) / 2.0
        raw_weights.append(raw_weight)
        weighted_rows.append((label, raw_weight))

    total_raw = sum(raw_weights)
    if total_raw <= 0.0:
        equal_share = 100.0 / float(len(weighted_rows))
        return [(label, equal_share) for label, _ in weighted_rows]
    return [(label, (raw / total_raw) * 100.0) for label, raw in weighted_rows]


def _common_aspect_labels_with_weight_details(subject_chart: Any, compared_chart: Any) -> list[str]:
    def _canonical(aspect: dict[str, Any]) -> tuple[tuple[str, str], str] | None:
        p1 = str(aspect.get("p1") or "").strip()
        p2 = str(aspect.get("p2") or "").strip()
        aspect_type = str(aspect.get("type") or "").strip().lower()
        if not p1 or not p2 or not aspect_type:
            return None
        if p1 in _ANGLE_POINTS and p2 in _ANGLE_POINTS:
            return None
        if _is_tautological_node_opposition(p1, p2, aspect_type):
            return None
        left, right = sorted((p1, p2))
        return (left, right), aspect_type

    def _aspect_base_weight(chart: Any, key: tuple[tuple[str, str], str]) -> tuple[float, float, float]:
        (left, right), aspect_type = key
        planet_weights = getattr(chart, "dominant_planet_weights", None) or None
        matching_orbs: list[float] = []
        for aspect in (getattr(chart, "aspects", None) or []):
            canonical = _canonical(aspect)
            if canonical != key:
                continue
            matching_orbs.append(abs(float(aspect.get("delta", 0.0) or 0.0)))
        source_aspect_scores = [
            max(
                0.0,
                float(
                    aspect_score(
                        {"p1": left, "p2": right, "type": aspect_type, "delta": orb},
                        planet_weights=planet_weights,
                    )
                ),
            )
            for orb in matching_orbs
        ]
        orb_weighted_base = max(source_aspect_scores, default=0.0)
        type_weight = max(0.0, float(ASPECT_SCORE_WEIGHTS.get(str(aspect_type).replace(" ", "_").lower(), 0.0)))
        pair_weight = max(0.0, float(aspect_pair_weight(left, right, planet_weights=planet_weights)))
        fallback_base = max(type_weight * pair_weight, 0.0)
        base_weight = orb_weighted_base if orb_weighted_base > 0.0 else fallback_base
        return base_weight, type_weight, pair_weight

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
    sorted_keys = sorted(common_keys)
    if not sorted_keys:
        return []

    rows: list[tuple[str, float, float, float, float, float]] = []
    total_raw = 0.0
    for key in sorted_keys:
        (left, right), aspect_type = key
        label = f"{left} {_aspect_label(aspect_type).lower()} {right}"
        subject_weight, subject_type_weight, subject_pair_weight = _aspect_base_weight(subject_chart, key)
        compared_weight, compared_type_weight, compared_pair_weight = _aspect_base_weight(compared_chart, key)
        raw_weight = (subject_weight + compared_weight) / 2.0
        total_raw += raw_weight
        rows.append(
            (
                label,
                raw_weight,
                subject_weight,
                compared_weight,
                (subject_type_weight + compared_type_weight) / 2.0,
                (subject_pair_weight + compared_pair_weight) / 2.0,
            )
        )

    if total_raw <= 0.0:
        equal_share = 100.0 / float(len(rows))
        return [
            (
                f"{label} ([{equal_share:.1f}% weight total]) "
                f"(avg type base {type_weight:.2f} × avg pair/body weight {pair_weight:.2f}; "
                f"query {query_weight:.2f}, candidate {candidate_weight:.2f}, avg raw {raw_weight:.2f})"
            )
            for label, raw_weight, query_weight, candidate_weight, type_weight, pair_weight in rows
        ]
    return [
        (
            f"{label} ([{((raw_weight / total_raw) * 100.0):.1f}% weight total]) "
            f"(avg type base {type_weight:.2f} × avg pair/body weight {pair_weight:.2f}; "
            f"query {query_weight:.2f}, candidate {candidate_weight:.2f}, avg raw {raw_weight:.2f})"
        )
        for label, raw_weight, query_weight, candidate_weight, type_weight, pair_weight in rows
    ]


def _differing_aspect_labels(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_label = _chart_possessive_label(subject_chart, "Chart 1")
    compared_label = _chart_possessive_label(compared_chart, "Chart 2")

    def _canonical(aspect: dict[str, Any]) -> tuple[tuple[str, str], str] | None:
        p1 = str(aspect.get("p1") or "").strip()
        p2 = str(aspect.get("p2") or "").strip()
        aspect_type = str(aspect.get("type") or "").strip().lower()
        if not p1 or not p2 or not aspect_type:
            return None
        if p1 in _ANGLE_POINTS and p2 in _ANGLE_POINTS:
            return None
        if _is_tautological_node_opposition(p1, p2, aspect_type):
            return None
        left, right = sorted((p1, p2))
        return (left, right), aspect_type

    subject_keys = {
        key
        for aspect in (getattr(subject_chart, "aspects", None) or [])
        if (key := _canonical(aspect)) is not None
    }
    compared_keys = {
        key
        for aspect in (getattr(compared_chart, "aspects", None) or [])
        if (key := _canonical(aspect)) is not None
    }
    only_subject = sorted(subject_keys - compared_keys)
    only_compared = sorted(compared_keys - subject_keys)
    differences: list[str] = []
    if only_subject:
        differences.append(
            f"Only in {subject_label}: "
            + "; ".join(f"{left} {_aspect_label(aspect_type).lower()} {right}" for (left, right), aspect_type in only_subject)
        )
    if only_compared:
        differences.append(
            f"Only in {compared_label}: "
            + "; ".join(f"{left} {_aspect_label(aspect_type).lower()} {right}" for (left, right), aspect_type in only_compared)
        )
    return differences


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


def _distribution_differences(subject_chart: Any, compared_chart: Any) -> list[str]:
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
                element = elements_by_sign[sign]
                mode = modes_by_sign[sign]
                subject_element_counts[element] = subject_element_counts.get(element, 0) + 1
                subject_mode_counts[mode] = subject_mode_counts.get(mode, 0) + 1
        if compared_lon is not None:
            sign = sign_for_longitude(compared_lon)
            if sign in elements_by_sign:
                element = elements_by_sign[sign]
                mode = modes_by_sign[sign]
                compared_element_counts[element] = compared_element_counts.get(element, 0) + 1
                compared_mode_counts[mode] = compared_mode_counts.get(mode, 0) + 1
    element_diff = [
        f"{element} ({subject_element_counts.get(element, 0)} vs {compared_element_counts.get(element, 0)})"
        for element in ("Fire", "Earth", "Air", "Water")
        if subject_element_counts.get(element, 0) != compared_element_counts.get(element, 0)
    ]
    mode_diff = [
        f"{mode} ({subject_mode_counts.get(mode, 0)} vs {compared_mode_counts.get(mode, 0)})"
        for mode in ("Cardinal", "Fixed", "Mutable")
        if subject_mode_counts.get(mode, 0) != compared_mode_counts.get(mode, 0)
    ]
    differences: list[str] = []
    if element_diff:
        differences.append("Elemental differences: " + ", ".join(element_diff))
    if mode_diff:
        differences.append("Modality differences: " + ", ".join(mode_diff))
    return differences


def _weighted_overlap_similarity(values_a: dict[Any, float], values_b: dict[Any, float]) -> float:
    total_a = sum(max(0.0, float(value)) for value in values_a.values())
    total_b = sum(max(0.0, float(value)) for value in values_b.values())
    if total_a <= 0.0 or total_b <= 0.0:
        return 0.0
    keys = set(values_a) | set(values_b)
    overlap = sum(
        min(max(0.0, float(values_a.get(key, 0.0))), max(0.0, float(values_b.get(key, 0.0))))
        for key in keys
    )
    return max(0.0, min(1.0, overlap / min(total_a, total_b)))


def _top_weighted_items(weights: dict[Any, float], *, count: int = 3) -> list[Any]:
    return [key for key, value in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:count] if value > 0.0]


def _sign_weight_profile(chart: Any) -> dict[str, float]:
    positions = getattr(chart, "positions", None) or {}
    profile = {sign: 0.0 for sign in _SIGN_SEQUENCE}
    for body in _DOMINANCE_BODIES:
        longitude = positions.get(body)
        if longitude is None:
            continue
        sign_name = sign_for_longitude(longitude)
        if sign_name in profile:
            profile[sign_name] += float(BODY_WEIGHTS.get(body, 0.8))
    return profile


def _house_weight_profile(chart: Any) -> dict[int, float]:
    houses = getattr(chart, "houses", None)
    positions = getattr(chart, "positions", None) or {}
    profile = {house: 0.0 for house in range(1, 13)}
    for body in _DOMINANCE_BODIES:
        longitude = positions.get(body)
        if longitude is None:
            continue
        house = _house_for_longitude(houses, longitude)
        if house is None:
            continue
        profile[house] += float(BODY_WEIGHTS.get(body, 0.8))
    return profile


def _body_dominance_profile(chart: Any) -> dict[str, float]:
    houses = getattr(chart, "houses", None)
    positions = getattr(chart, "positions", None) or {}
    profile: dict[str, float] = {}
    for body in _DOMINANCE_BODIES:
        longitude = positions.get(body)
        if longitude is None:
            continue
        weight = float(BODY_WEIGHTS.get(body, 0.8))
        house = _house_for_longitude(houses, longitude)
        if house in {1, 4, 7, 10}:
            weight *= 1.30
        elif house in {2, 5, 8, 11}:
            weight *= 1.12
        profile[body] = weight
    return profile


def _combined_dominance_detail_lines(subject_chart: Any, compared_chart: Any, *, analysis_mode: str) -> list[str]:
    subject_label = _chart_possessive_label(subject_chart, "Chart 1")
    compared_label = _chart_possessive_label(compared_chart, "Chart 2")
    q_sign = _sign_weight_profile(subject_chart)
    c_sign = _sign_weight_profile(compared_chart)
    q_house = _house_weight_profile(subject_chart)
    c_house = _house_weight_profile(compared_chart)
    q_body = _body_dominance_profile(subject_chart)
    c_body = _body_dominance_profile(compared_chart)

    sign_overlap = _weighted_overlap_similarity(q_sign, c_sign)
    house_overlap = _weighted_overlap_similarity(q_house, c_house)
    body_overlap = _weighted_overlap_similarity(q_body, c_body)

    q_sign_top = _top_weighted_items(q_sign, count=3)
    c_sign_top = _top_weighted_items(c_sign, count=3)
    q_house_top = _top_weighted_items(q_house, count=3)
    c_house_top = _top_weighted_items(c_house, count=3)
    q_body_top = _top_weighted_items(q_body, count=3)
    c_body_top = _top_weighted_items(c_body, count=3)

    shared_signs = [sign for sign in q_sign_top if sign in set(c_sign_top)]
    shared_houses = [house for house in q_house_top if house in set(c_house_top)]
    shared_bodies = [body for body in q_body_top if body in set(c_body_top)]

    only_subject_signs = [sign for sign in q_sign_top if sign not in set(c_sign_top)]
    only_compared_signs = [sign for sign in c_sign_top if sign not in set(q_sign_top)]
    only_subject_houses = [house for house in q_house_top if house not in set(c_house_top)]
    only_compared_houses = [house for house in c_house_top if house not in set(q_house_top)]
    only_subject_bodies = [body for body in q_body_top if body not in set(c_body_top)]
    only_compared_bodies = [body for body in c_body_top if body not in set(q_body_top)]

    lines: list[str] = [
        "Weighted in Combined Dominance: signs 40%, houses 30%, planets/bodies 30%.",
        #"Angles (AS/IC/DS/MC) are excluded from this dominance breakdown.",
        "Nakshatra dominance is scored separately in the Nakshatra Dominance section (when enabled).",
    ]
    if analysis_mode == "dissimilarities":
        lines.extend(
            [
                f"Sign dominance mismatch: {(1.0 - sign_overlap) * 100.0:.1f}% (overlap {sign_overlap * 100.0:.1f}%).",
                (
                    "Top sign differences: "
                    f"only in {subject_label} [{', '.join(only_subject_signs) or 'none'}]; "
                    f"only in {compared_label} [{', '.join(only_compared_signs) or 'none'}]."
                ),
                f"House dominance mismatch: {(1.0 - house_overlap) * 100.0:.1f}% (overlap {house_overlap * 100.0:.1f}%).",
                (
                    "Top house differences: "
                    f"only in {subject_label} [{', '.join(f'House {house}' for house in only_subject_houses) or 'none'}]; "
                    f"only in {compared_label} [{', '.join(f'House {house}' for house in only_compared_houses) or 'none'}]."
                ),
                f"Planet/body dominance mismatch: {(1.0 - body_overlap) * 100.0:.1f}% (overlap {body_overlap * 100.0:.1f}%).",
                (
                    "Top body differences: "
                    f"only in {subject_label} [{', '.join(only_subject_bodies) or 'none'}]; "
                    f"only in {compared_label} [{', '.join(only_compared_bodies) or 'none'}]."
                ),
            ]
        )
    else:
        lines.extend(
            [
                f"Sign dominance overlap: {sign_overlap * 100.0:.1f}%; shared top signs: {', '.join(shared_signs) or 'none'}.",
                f"House dominance overlap: {house_overlap * 100.0:.1f}%; shared top houses: {', '.join(f'House {house}' for house in shared_houses) or 'none'}.",
                f"Planet/body dominance overlap: {body_overlap * 100.0:.1f}%; shared top bodies: {', '.join(shared_bodies) or 'none'}.",
            ]
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


def _nakshatra_difference_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_positions = getattr(subject_chart, "positions", None) or {}
    compared_positions = getattr(compared_chart, "positions", None) or {}
    differences: list[str] = []
    for body in _PLACEMENT_BODIES:
        subject_lon = subject_positions.get(body)
        compared_lon = compared_positions.get(body)
        if subject_lon is None or compared_lon is None:
            continue
        subject_nak = get_nakshatra(subject_lon)
        compared_nak = get_nakshatra(compared_lon)
        if subject_nak and compared_nak and subject_nak != compared_nak:
            differences.append(f"{body}: {subject_nak} vs {compared_nak}")
    return sorted(differences)

#note: currently this is using Nakshatra Prevalence, NOT Nakshatra dominance.
def _nakshatra_dominance_summary(subject_chart: Any, compared_chart: Any) -> list[str]:
    def _profile(chart: Any) -> dict[str, int]:
        positions = getattr(chart, "positions", None) or {}
        counts: dict[str, int] = {}
        for body in _PLACEMENT_BODIES:
            if body in {"AS", "MC"}:
                continue
            longitude = positions.get(body)
            if longitude is None:
                continue
            nakshatra = get_nakshatra(longitude)
            if not nakshatra:
                continue
            counts[nakshatra] = counts.get(nakshatra, 0) + 1
        return counts

    subject_profile = _profile(subject_chart)
    compared_profile = _profile(compared_chart)
    subject_top3 = [name for name, _count in sorted(subject_profile.items(), key=lambda item: item[1], reverse=True)[:3]]
    compared_top3 = [name for name, _count in sorted(compared_profile.items(), key=lambda item: item[1], reverse=True)[:3]]
    overlap = [nak for nak in subject_top3 if nak in set(compared_top3)]
    lines: list[str] = []
    if overlap:
        lines.append("Shared top nakshatras: " + ", ".join(overlap))
    lines.append(f"Top-3 overlap: {len(overlap)}/3")
    return lines


def _nakshatra_dominance_differences(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_label = _chart_possessive_label(subject_chart, "Chart 1")
    compared_label = _chart_possessive_label(compared_chart, "Chart 2")

    def _top3(chart: Any) -> list[str]:
        positions = getattr(chart, "positions", None) or {}
        counts: dict[str, int] = {}
        for body in _PLACEMENT_BODIES:
            if body in {"AS", "MC"}:
                continue
            longitude = positions.get(body)
            if longitude is None:
                continue
            nakshatra = get_nakshatra(longitude)
            if not nakshatra:
                continue
            counts[nakshatra] = counts.get(nakshatra, 0) + 1
        return [name for name, _count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3]]

    subject_top = _top3(subject_chart)
    compared_top = _top3(compared_chart)
    subject_only = [nak for nak in subject_top if nak not in set(compared_top)]
    compared_only = [nak for nak in compared_top if nak not in set(subject_top)]
    differences: list[str] = []
    if subject_only:
        differences.append(f"Top nakshatras only in {subject_label}: " + ", ".join(subject_only))
    if compared_only:
        differences.append(f"Top nakshatras only in {compared_label}: " + ", ".join(compared_only))
    if not differences:
        differences.append("Top nakshatra dominance profiles essentially the same.")
    return differences


def _defined_center_overlap_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_label = _chart_possessive_label(subject_chart, "Chart 1")
    compared_label = _chart_possessive_label(compared_chart, "Chart 2")

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


def _defined_center_difference_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
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

    subject_centers = _centers(subject_chart)
    compared_centers = _centers(compared_chart)
    subject_only = sorted(subject_centers - compared_centers)
    compared_only = sorted(compared_centers - subject_centers)
    differences: list[str] = []
    if subject_only:
        differences.append(f"Only in {subject_label}: " + ", ".join(subject_only))
    if compared_only:
        differences.append(f"Only in {compared_label}: " + ", ".join(compared_only))
    return differences


def _human_design_gate_set(chart: Any) -> set[int]:
    existing: set[int] = set()
    for gate in (getattr(chart, "human_design_gates", None) or []):
        try:
            existing.add(int(gate))
        except (TypeError, ValueError):
            continue
    if existing:
        return existing
    try:
        result = build_human_design_result(chart)
    except Exception:
        return set()
    resolved: set[int] = set()
    for gate in (getattr(result, "active_gates", None) or []):
        try:
            resolved.add(int(gate))
        except (TypeError, ValueError):
            continue
    return resolved


def _human_design_gate_overlap_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_label = _chart_possessive_label(subject_chart, "Chart 1")
    compared_label = _chart_possessive_label(compared_chart, "Chart 2")

    subject_gates = _human_design_gate_set(subject_chart)
    compared_gates = _human_design_gate_set(compared_chart)
    shared = sorted(subject_gates & compared_gates)
    union_size = len(subject_gates | compared_gates)
    overlap_percent = (len(shared) / union_size * 100.0) if union_size else 0.0
    lines = [
        f"Gate overlap: {len(shared)}/{union_size} ({overlap_percent:.1f}%)."
    ]
    if shared:
        lines.append("Shared gates: " + ", ".join(f"Gate {gate}" for gate in shared))
    return lines


def _human_design_gate_difference_lines(subject_chart: Any, compared_chart: Any) -> list[str]:
    subject_gates = _human_design_gate_set(subject_chart)
    compared_gates = _human_design_gate_set(compared_chart)
    subject_only = sorted(subject_gates - compared_gates)
    compared_only = sorted(compared_gates - subject_gates)
    differences: list[str] = []
    if subject_only:
        differences.append(f"Only in {subject_label}: " + ", ".join(f"Gate {gate}" for gate in subject_only))
    if compared_only:
        differences.append(f"Only in {compared_label}: " + ", ".join(f"Gate {gate}" for gate in compared_only))
    if not differences:
        differences.append("Human Design gate sets are identical.")
    return differences


def _resolve_component_weight_percents(
    *,
    algorithm_mode: str,
    similarity_settings: SimilarityCalculatorSettings | None,
) -> dict[str, int]:
    normalized_mode = normalize_similar_charts_algorithm_mode(algorithm_mode)
    if normalized_mode == SIMILAR_CHARTS_ALGORITHM_CUSTOM:
        settings = similarity_settings or SimilarityCalculatorSettings.defaults_from_comprehensive()
        enabled = settings.enabled_components()
        raw_weights = settings.weights_by_component()
    elif normalized_mode == SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE:
        settings = SimilarityCalculatorSettings.defaults_from_comprehensive()
        enabled = settings.enabled_components()
        raw_weights = settings.weights_by_component()
    else:
        enabled = {key: True for key in _DEFAULT_ALGORITHM_COMPONENT_WEIGHTS}
        raw_weights = dict(_DEFAULT_ALGORITHM_COMPONENT_WEIGHTS)

    included_weights = {
        key: max(0.0, float(raw_weights.get(key, 0.0)))
        for key, is_enabled in enabled.items()
        if bool(is_enabled) and float(raw_weights.get(key, 0.0)) > 0.0
    }
    total_weight = sum(included_weights.values())
    if total_weight <= 0.0:
        return {}
    return {
        key: int(round((weight / total_weight) * 100.0))
        for key, weight in included_weights.items()
    }


def resolve_similarity_component_keys_for_display(
    *,
    algorithm_mode: str,
    similarity_settings: SimilarityCalculatorSettings | None,
) -> list[str]:
    component_weight_percents = _resolve_component_weight_percents(
        algorithm_mode=algorithm_mode,
        similarity_settings=similarity_settings,
    )
    return [key for key in component_weight_percents if key in _SIMILARITY_COMPONENT_LABELS]


def format_similarity_component_summary(
    *,
    match: Any,
    component_keys: list[str] | None = None,
) -> str:
    keys = component_keys or ["placement", "aspect", "distribution", "combined_dominance"]
    values_by_component = {
        "placement": getattr(match, "placement_score", None),
        "aspect": getattr(match, "aspect_score", None),
        "distribution": getattr(match, "distribution_score", None),
        "combined_dominance": getattr(match, "dominance_score", None),
        "nakshatra_placement": getattr(match, "nakshatra_score", None),
        "nakshatra_dominance": getattr(match, "nakshatra_dominance_score", None),
        "defined_centers": getattr(match, "hd_centers_score", None),
        "human_design_gates": getattr(match, "human_design_gates_score", None),
    }
    bits: list[str] = []
    for key in keys:
        score = values_by_component.get(key)
        if score is None:
            continue
        label = _SIMILARITY_COMPONENT_LABELS.get(key)
        if not label:
            continue
        bits.append(f"{label} {float(score) * 100.0:.0f}%")
    return ", ".join(bits) if bits else "no enabled criteria"


def _section_title_with_weight(title: str, component_key: str, component_weight_percents: dict[str, int]) -> str:
    percent = component_weight_percents.get(component_key)
    if percent is None:
        return title
    return f"{title} (weighted at {percent}%)"


def _resolve_component_score_percents(
    *,
    subject_chart: Any,
    compared_chart: Any,
    algorithm_mode: str,
    similarity_settings: SimilarityCalculatorSettings | None,
) -> dict[str, int]:
    normalized_mode = normalize_similar_charts_algorithm_mode(algorithm_mode)
    active_placement_mode = (
        similarity_settings.normalized_placement_weighting_mode()
        if similarity_settings is not None
        else SimilarityCalculatorSettings.defaults_from_comprehensive().normalized_placement_weighting_mode()
    )
    if normalized_mode == SIMILAR_CHARTS_ALGORITHM_CUSTOM:
        effective_settings = similarity_settings or SimilarityCalculatorSettings.defaults_from_comprehensive()
    else:
        effective_settings = SimilarityCalculatorSettings.defaults_from_comprehensive()
        effective_settings.placement_weighting_mode = active_placement_mode

    _overall_score, component_scores = chart_similarity_score_custom(
        subject_chart,
        compared_chart,
        effective_settings,
    )
    return {
        key: int(round(max(0.0, min(1.0, float(score))) * 100.0))
        for key, score in component_scores.items()
    }


def _resolve_active_placement_weighting_mode(
    *,
    similarity_settings: SimilarityCalculatorSettings | None,
) -> str:
    mode = (
        similarity_settings.normalized_placement_weighting_mode()
        if similarity_settings is not None
        else SimilarityCalculatorSettings.defaults_from_comprehensive().normalized_placement_weighting_mode()
    )
    return normalize_placement_weighting_mode(mode)


def _section_title_with_weight_and_match(
    title: str,
    component_key: str,
    component_weight_percents: dict[str, int],
    component_score_percents: dict[str, int],
) -> str:
    title_with_weight = _section_title_with_weight(title, component_key, component_weight_percents)
    match_percent = component_score_percents.get(component_key)
    if match_percent is None:
        return title_with_weight
    return f"{title_with_weight}: {match_percent}% match"


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
    similarity_settings: SimilarityCalculatorSettings | None = None,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    show_granular_explanations: bool = False,
    analysis_mode: str = "similarities",
) -> str:
    _band_label, _band_color = resolve_similarity_band(float(getattr(match, "score", 0.0)) * 100.0)
    compared_name = _safe_chart_name(
        compared_chart,
        str(getattr(match, "chart_name", "") or f"Chart #{getattr(match, 'chart_id', '?')}"),
    )
    subject_title = _safe_chart_name(subject_chart, subject_name or "Current chart")
    lines: list[str] = []
    if subject_chart is not None and compared_chart is not None:
        algorithm_mode = str(getattr(match, "algorithm_mode", "") or "")
        active_placement_mode = _resolve_active_placement_weighting_mode(
            similarity_settings=similarity_settings,
        )
        component_weight_percents = _resolve_component_weight_percents(
            algorithm_mode=algorithm_mode,
            similarity_settings=similarity_settings,
        )
        component_score_percents = _resolve_component_score_percents(
            subject_chart=subject_chart,
            compared_chart=compared_chart,
            algorithm_mode=algorithm_mode,
            similarity_settings=similarity_settings,
        )
        if analysis_mode == "dissimilarities":
            if "placement" in component_weight_percents:
                placement_diff = (
                    _differing_placement_labels_with_weight_details(
                        subject_chart,
                        compared_chart,
                        placement_weighting_mode=active_placement_mode,
                    )
                    if show_granular_explanations
                    else _differing_placement_labels(subject_chart, compared_chart)
                )
                lines.append(
                    _section_title_with_weight_and_match(
                        "Differing placements:",
                        "placement",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append("; ".join(placement_diff) if placement_diff else "Tracked placements align closely.")
                lines.append("")
            if "aspect" in component_weight_percents:
                aspect_diff = _differing_aspect_labels(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Differing aspects:",
                        "aspect",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(aspect_diff) if aspect_diff else "Aspect signatures align closely.")
                lines.append("")
            if "distribution" in component_weight_percents:
                distribution_diff = _distribution_differences(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Distribution differences:",
                        "distribution",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(distribution_diff) if distribution_diff else "Elemental and modality distributions are closely aligned.")
                lines.append("")
            if "combined_dominance" in component_weight_percents:
                dominance_score = float(getattr(match, "dominance_score", 0.0) or 0.0)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Combined Dominance differences:",
                        "combined_dominance",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(f"Dominance mismatch estimate: {(1.0 - dominance_score) * 100.0:.1f}%.")
                lines.extend(_combined_dominance_detail_lines(subject_chart, compared_chart, analysis_mode="dissimilarities"))
                lines.append("")
            if "nakshatra_placement" in component_weight_percents:
                nak_diff = _nakshatra_difference_lines(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Nakshatra Prevalence differences:",
                        "nakshatra_placement",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append("; ".join(nak_diff) if nak_diff else "No same-body nakshatra differences were found.")
                lines.append("")
            if "nakshatra_dominance" in component_weight_percents:
                nak_dominance_diff = _nakshatra_dominance_differences(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Nakshatra Dominance differences:",
                        "nakshatra_dominance",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(nak_dominance_diff))
                lines.append("")
            if "defined_centers" in component_weight_percents:
                centers_diff = _defined_center_difference_lines(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Defined center differences:",
                        "defined_centers",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(centers_diff) if centers_diff else "Defined center sets are the same.")
            if "human_design_gates" in component_weight_percents:
                hd_gate_diff = _human_design_gate_difference_lines(subject_chart, compared_chart)
                lines.append("")
                lines.append(
                    _section_title_with_weight_and_match(
                        "Human Design gate differences:",
                        "human_design_gates",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(hd_gate_diff))
        else:
            if "placement" in component_weight_percents:
                placement_labels = (
                    _common_placement_labels_with_weight_details(
                        subject_chart,
                        compared_chart,
                        placement_weighting_mode=active_placement_mode,
                    )
                    if show_granular_explanations
                    else _common_placement_labels(subject_chart, compared_chart)
                )
                lines.append(
                    _section_title_with_weight_and_match(
                        "Placements in common:",
                        "placement",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append("; ".join(placement_labels) if placement_labels else "No exact same-sign placements found in tracked bodies.")
                lines.append("")
            if "aspect" in component_weight_percents:
                if show_granular_explanations:
                    aspect_weighted_labels = _common_aspect_labels_with_relevance(subject_chart, compared_chart)
                    aspect_labels = _common_aspect_labels_with_weight_details(subject_chart, compared_chart)
                    aspect_weight_percent = component_weight_percents.get("aspect")
                    aspect_match_percent = component_score_percents.get("aspect")
                    title = _section_title_with_weight_and_match(
                        "Aspects in common:",
                        "aspect",
                        component_weight_percents,
                        component_score_percents,
                    )
                    if (
                        aspect_weighted_labels
                        and aspect_weight_percent is not None
                        and aspect_match_percent is not None
                    ):
                        relevance_points = (float(aspect_weight_percent) * float(aspect_match_percent)) / 100.0
                        title = (
                            f"{title} + [{relevance_points:.1f} relevance points] = "
                            f"[{relevance_points:.1f}/100 similarity points]"
                        )
                else:
                    aspect_labels = _common_aspect_labels(subject_chart, compared_chart)
                    title = _section_title_with_weight_and_match(
                        "Aspects in common:",
                        "aspect",
                        component_weight_percents,
                        component_score_percents,
                    )
                lines.append(
                    title
                )
                lines.append("; ".join(aspect_labels) if aspect_labels else "No shared aspect signatures were found.")
                lines.append("")
            if "distribution" in component_weight_percents:
                distribution_lines = _distribution_summary(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Distribution similarities:",
                        "distribution",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(distribution_lines) if distribution_lines else "No clear elemental/modality overlap was detected.")
                lines.append("")
            if "combined_dominance" in component_weight_percents:
                dominance_score = float(getattr(match, "dominance_score", 0.0) or 0.0)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Combined Dominance:",
                        "combined_dominance",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(f"Dominance pattern overlap: {dominance_score * 100.0:.1f}%.")
                lines.extend(_combined_dominance_detail_lines(subject_chart, compared_chart, analysis_mode="similarities"))
                lines.append("")
            if "nakshatra_placement" in component_weight_percents:
                nak_lines = _nakshatra_overlap_lines(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Nakshatra Prevalence:",
                        "nakshatra_placement",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append("; ".join(nak_lines) if nak_lines else "No same-body nakshatra overlaps were found.")
                lines.append("")
            if "nakshatra_dominance" in component_weight_percents:
                nak_dominance_lines = _nakshatra_dominance_summary(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Nakshatra Dominance:",
                        "nakshatra_dominance",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(nak_dominance_lines))
                lines.append("")
            if "defined_centers" in component_weight_percents:
                centers = _defined_center_overlap_lines(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Defined centers in common:",
                        "defined_centers",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(", ".join(centers) if centers else "No overlapping defined centers were found.")
                lines.append("")
            if "human_design_gates" in component_weight_percents:
                hd_gate_lines = _human_design_gate_overlap_lines(subject_chart, compared_chart)
                lines.append(
                    _section_title_with_weight_and_match(
                        "Human Design gates in common:",
                        "human_design_gates",
                        component_weight_percents,
                        component_score_percents,
                    )
                )
                lines.append(" | ".join(hd_gate_lines) if hd_gate_lines else "No Human Design gate overlap was found.")
                lines.append("")
    else:
        lines.append("Detailed similarity details are unavailable because one or both charts could not be loaded.")
    return "\n".join(
        [
            "ⓘDISSIMILARITIES ANALYSIS" if analysis_mode == "dissimilarities" else "ⓘSIMILARITIES ANALYSIS",
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
    similarity_settings: SimilarityCalculatorSettings | None = None,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    show_granular_explanations: bool = False,
    analysis_mode: str = "similarities",
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

    compared_name = _safe_chart_name(
        compared_chart,
        str(getattr(match, "chart_name", "") or f"Chart #{getattr(match, 'chart_id', '?')}"),
    )
    subject_title = _safe_chart_name(subject_chart, subject_name or "Current chart")

    def _section(title: str, items: list[str]) -> str:
        bullet_items = items or ["None noted."]
        rendered_items = []
        for item in bullet_items:
            rendered_items.append(
                "<li style='margin:2px 0;'>"
                f"{_colorize_body_line(item)}"
                "</li>"
            )
        return (
            f"<div style='margin-top:8px;font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>{html.escape(title)}</div>"
            f"<ul style='margin:4px 0 0 9px;padding:0;color:{_SIMILARITY_PANEL_BODY_TEXT_COLOR};font-weight:400'>"
            + "".join(rendered_items)
            + "</ul>"
        )

    html_lines: list[str] = [
        (
            f"<div style='font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>"
            + ("ⓘDISSIMILARITIES ANALYSIS" if analysis_mode == "dissimilarities" else "ⓘSIMILARITIES ANALYSIS")
            + "</div>"
        ),
        (
            f"<div style='margin-top:4px;color:{_SIMILARITY_PANEL_BODY_TEXT_COLOR};'>"
            f"<span style='font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>Charts:</span> "
            f"{html.escape(subject_title)} ↔ {html.escape(compared_name)}"
            "</div>"
        ),
    ]
    if subject_chart is not None and compared_chart is not None:
        algorithm_mode = str(getattr(match, "algorithm_mode", "") or "")
        active_placement_mode = _resolve_active_placement_weighting_mode(
            similarity_settings=similarity_settings,
        )
        component_weight_percents = _resolve_component_weight_percents(
            algorithm_mode=algorithm_mode,
            similarity_settings=similarity_settings,
        )
        component_score_percents = _resolve_component_score_percents(
            subject_chart=subject_chart,
            compared_chart=compared_chart,
            algorithm_mode=algorithm_mode,
            similarity_settings=similarity_settings,
        )
        if analysis_mode == "dissimilarities":
            if "placement" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Differing placements:",
                            "placement",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        (
                            _differing_placement_labels_with_weight_details(
                                subject_chart,
                                compared_chart,
                                placement_weighting_mode=active_placement_mode,
                            )
                            if show_granular_explanations
                            else _differing_placement_labels(subject_chart, compared_chart)
                        )
                        or ["Tracked placements align closely."],
                    )
                )
            if "aspect" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Differing aspects:",
                            "aspect",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _differing_aspect_labels(subject_chart, compared_chart)
                        or ["Aspect signatures align closely."],
                    )
                )
            if "distribution" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Distribution differences:",
                            "distribution",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _distribution_differences(subject_chart, compared_chart)
                        or ["Elemental and modality distributions are closely aligned."],
                    )
                )
            if "combined_dominance" in component_weight_percents:
                dominance_score = float(getattr(match, "dominance_score", 0.0) or 0.0)
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Combined Dominance differences:",
                            "combined_dominance",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        [f"Dominance mismatch estimate: {(1.0 - dominance_score) * 100.0:.1f}%."]
                        + _combined_dominance_detail_lines(subject_chart, compared_chart, analysis_mode="dissimilarities"),
                    )
                )
            if "nakshatra_placement" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Nakshatra Prevalence differences:",
                            "nakshatra_placement",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _nakshatra_difference_lines(subject_chart, compared_chart)
                        or ["No same-body nakshatra differences were found."],
                    )
                )
            if "nakshatra_dominance" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Nakshatra Dominance differences:",
                            "nakshatra_dominance",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _nakshatra_dominance_differences(subject_chart, compared_chart),
                    )
                )
            if "defined_centers" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Defined center differences:",
                            "defined_centers",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _defined_center_difference_lines(subject_chart, compared_chart)
                        or ["Defined center sets are the same."],
                    )
                )
            if "human_design_gates" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Human Design gate differences:",
                            "human_design_gates",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _human_design_gate_difference_lines(subject_chart, compared_chart),
                    )
                )
        else:
            if "placement" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Placements in common:",
                            "placement",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        (
                            _common_placement_labels_with_weight_details(
                                subject_chart,
                                compared_chart,
                                placement_weighting_mode=active_placement_mode,
                            )
                            if show_granular_explanations
                            else _common_placement_labels(subject_chart, compared_chart)
                        )
                        or ["No exact same-sign placements found in tracked bodies."],
                    )
                )
            if "aspect" in component_weight_percents:
                if show_granular_explanations:
                    aspect_weighted_labels = _common_aspect_labels_with_relevance(subject_chart, compared_chart)
                    aspect_items = (
                        _common_aspect_labels_with_weight_details(subject_chart, compared_chart)
                        if aspect_weighted_labels
                        else ["No shared aspect signatures were found."]
                    )
                    aspect_weight_percent = component_weight_percents.get("aspect")
                    aspect_match_percent = component_score_percents.get("aspect")
                    title = _section_title_with_weight_and_match(
                        "Aspects in common:",
                        "aspect",
                        component_weight_percents,
                        component_score_percents,
                    )
                    if (
                        aspect_weighted_labels
                        and aspect_weight_percent is not None
                        and aspect_match_percent is not None
                    ):
                        relevance_points = (float(aspect_weight_percent) * float(aspect_match_percent)) / 100.0
                        title = (
                            f"{title} + [{relevance_points:.1f} relevance points] = "
                            f"[{relevance_points:.1f}/100 similarity points]"
                        )
                else:
                    title = _section_title_with_weight_and_match(
                        "Aspects in common:",
                        "aspect",
                        component_weight_percents,
                        component_score_percents,
                    )
                    aspect_items = _common_aspect_labels(subject_chart, compared_chart) or [
                        "No shared aspect signatures were found."
                    ]
                html_lines.append(
                    _section(
                        title,
                        aspect_items,
                    )
                )
            if "distribution" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Distribution similarities:",
                            "distribution",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _distribution_summary(subject_chart, compared_chart)
                        or ["No clear elemental/modality overlap was detected."],
                    )
                )
            if "combined_dominance" in component_weight_percents:
                dominance_score = float(getattr(match, "dominance_score", 0.0) or 0.0)
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Combined Dominance:",
                            "combined_dominance",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        [f"Dominance pattern overlap: {dominance_score * 100.0:.1f}%."]
                        + _combined_dominance_detail_lines(subject_chart, compared_chart, analysis_mode="similarities"),
                    )
                )
            if "nakshatra_placement" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Nakshatra Prevalence:",
                            "nakshatra_placement",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _nakshatra_overlap_lines(subject_chart, compared_chart)
                        or ["No same-body nakshatra overlaps were found."],
                    )
                )
            if "nakshatra_dominance" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Nakshatra Dominance:",
                            "nakshatra_dominance",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _nakshatra_dominance_summary(subject_chart, compared_chart),
                    )
                )
            if "defined_centers" in component_weight_percents:
                centers = _defined_center_overlap_lines(subject_chart, compared_chart)
                center_items = centers or ["No overlapping defined centers were found."]
                if centers:
                    center_items = [
                        f"<span style='color:{html.escape(str(HD_CENTERS.get(center_name, {}).get('color') or '#cccccc'))};font-weight:600'>"
                        f"{html.escape(center_name)}</span>"
                        for center_name in centers
                    ]
                    html_lines.append(
                        f"<div style='margin-top:8px;font-weight:700;color:{SIMILARITY_SECTION_HEADER_COLOR}'>"
                        f"{html.escape(_section_title_with_weight_and_match('Defined centers in common:', 'defined_centers', component_weight_percents, component_score_percents))}</div>"
                        f"<ul style='margin:4px 0 0 9px;padding:0;color:{_SIMILARITY_PANEL_BODY_TEXT_COLOR};font-weight:400'>"
                        + "".join(f"<li style='margin:2px 0;'>{center_markup}</li>" for center_markup in center_items)
                        + "</ul>"
                    )
                else:
                    html_lines.append(
                        _section(
                            _section_title_with_weight_and_match(
                                "Defined centers in common:",
                                "defined_centers",
                                component_weight_percents,
                                component_score_percents,
                            ),
                            center_items,
                        )
                    )
            if "human_design_gates" in component_weight_percents:
                html_lines.append(
                    _section(
                        _section_title_with_weight_and_match(
                            "Human Design gates in common:",
                            "human_design_gates",
                            component_weight_percents,
                            component_score_percents,
                        ),
                        _human_design_gate_overlap_lines(subject_chart, compared_chart)
                        or ["No Human Design gate overlap was found."],
                    )
                )
    else:
        html_lines.append(
            _section(
                "Details:",
                ["Detailed similarity details are unavailable because one or both charts could not be loaded."],
            )
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
    algorithm_mode: str = "default",
    similarity_settings: SimilarityCalculatorSettings | None = None,
) -> str:
    if not matches:
        return "No charts found."
    component_keys = resolve_similarity_component_keys_for_display(
        algorithm_mode=algorithm_mode,
        similarity_settings=similarity_settings,
    )
    blocks: list[str] = []
    for rank, match in enumerate(matches, start=1):
        safe_name = html.escape(str(match.chart_name))
        similarity_percent = float(match.score) * 100.0
        band_label, band_color = resolve_similarity_band(similarity_percent)
        component_summary = format_similarity_component_summary(
            match=match,
            component_keys=component_keys,
        )
        blocks.append(
            (
                f'<span style="font-weight: bold; color: {highlight_color};">{rank}.</span> '
                f'#{match.chart_id} — <a href="{match.chart_id}">{safe_name}</a> '
                f'<a href="{make_similar_info_target(info_link_prefix=info_link_prefix, chart_id=int(match.chart_id))}">ⓘ</a><br>'
                f'Similarity <span style="color: {band_color}; font-weight: 600;">'
                f"{similarity_percent:.1f}% ({band_label})</span> "
                f'<span style="font-weight: 400; color: {_SIMILARITY_LIST_TEXT_COLOR};">'
                f"({component_summary})"
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
    info_output_style: str | None = None,
    highlight_color: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    algorithm_mode: str = "default",
    similarity_settings: SimilarityCalculatorSettings | None = None,
    info_link_prefix: str = "sim-info",
    configure_splitter: Callable[[QSplitter], None] | None = None,
    on_analysis_mode_changed: Callable[[QDialog], None] | None = None,
    on_make_collection_clicked: Callable[[QDialog], None] | None = None,
    on_export_clicked: Callable[[QDialog], None] | None = None,
    share_icon_path: str | None = None,
) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Similar Charts — {subject_name}")
    dialog.setModal(False)
    dialog.resize(860, 700)
    layout = QVBoxLayout(dialog)

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.addStretch(1)
    make_collection_button = QPushButton("Make collection from similar charts")
    make_collection_button.setCursor(Qt.PointingHandCursor)
    make_collection_button.setVisible(on_make_collection_clicked is not None)
    if on_make_collection_clicked is not None:
        make_collection_button.clicked.connect(lambda _checked=False: on_make_collection_clicked(dialog))
    top_row.addWidget(make_collection_button, 0, Qt.AlignRight)
    export_button = QToolButton()
    if share_icon_path:
        export_button.setIcon(QIcon(share_icon_path))
        export_button.setIconSize(QSize(14, 14))
    else:
        export_button.setText("↗")
    export_button.setAutoRaise(True)
    export_button.setCursor(Qt.PointingHandCursor)
    export_button.setToolTip("Export Top 25 Most Similar & Top 25 Least Similar charts as TXT or Markdown")
    export_button.setVisible(on_export_clicked is not None)
    if on_export_clicked is not None:
        export_button.clicked.connect(lambda _checked=False: on_export_clicked(dialog))
    top_row.addWidget(export_button, 0, Qt.AlignRight)
    layout.addLayout(top_row)

    # title_label = QLabel(f"Similar Charts for {subject_name}")
    # title_label.setStyleSheet(header_style)
    # layout.addWidget(title_label)

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
    # info_header = QLabel("") #don't need no stinkin' QLabel here.
    # info_header.setStyleSheet(header_style)
    # info_layout.addWidget(info_header)
    analysis_dropdown = QComboBox()
    analysis_dropdown.addItem("ⓘSIMILARITIES ANALYSIS", "similarities")
    analysis_dropdown.addItem("ⓘDISSIMILARITIES ANALYSIS", "dissimilarities")
    analysis_dropdown.addItem("ⓘBIO", "bio")
    analysis_dropdown.setStyleSheet(DEFAULT_DROPDOWN_STYLE)
    info_layout.addWidget(analysis_dropdown, 0)

    info_output = QLabel("Click ⓘ next to a chart to view similarities analysis.")
    info_output.setWordWrap(True)
    info_output.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    info_output.setTextInteractionFlags(Qt.TextBrowserInteraction)
    info_output.setOpenExternalLinks(False)
    info_output.setStyleSheet(info_output_style or output_style)
    info_scroll = QScrollArea()
    info_scroll.setWidgetResizable(True)
    info_scroll.setFrameShape(QFrame.NoFrame)
    info_content = QWidget()
    info_content_layout = QVBoxLayout(info_content)
    info_content_layout.setContentsMargins(0, 0, 0, 0)
    info_content_layout.setSpacing(0)
    info_content_layout.addWidget(info_output)
    info_content_layout.addStretch(1)
    info_scroll.setWidget(info_content)
    info_layout.addWidget(info_scroll, 1)
    if on_analysis_mode_changed is not None:
        analysis_dropdown.currentIndexChanged.connect(lambda _index: on_analysis_mode_changed(dialog))
    dialog._similar_chart_popout_analysis_dropdown = analysis_dropdown
    dialog._similar_chart_popout_info_output = info_output
    dialog._similar_chart_popout_make_collection_button = make_collection_button
    dialog._similar_chart_popout_export_button = export_button
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
                algorithm_mode=algorithm_mode,
                similarity_settings=similarity_settings,
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
