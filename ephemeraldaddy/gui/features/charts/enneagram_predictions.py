"""Enneagram prediction chart rendering and popout info helpers."""

from __future__ import annotations

import html
import random
import re
from typing import Any, Callable

from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    ASPECT_SCORE_WEIGHTS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    PLANET_ORDER,
    SIGN_COLORS,
    ZODIAC_NAMES,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_nakshatra_weights,
    house_for_longitude,
)
from ephemeraldaddy.gui.features.charts.presentation import sign_for_longitude
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR
from ephemeraldaddy.analysis.human_design import derive_human_design_profile


ENNEAGRAM_DEBUG_LOGGING = False
ENNEAGRAM_ANTI_FACTOR = 1.0
ENNEAGRAM_CATEGORY_WEIGHTS: dict[str, float] = {
    "signs": 1.0,
    "bodies": 1.0,
    "nakshatras": 1.0,
    "houses": 1.0,
    "gates": 1.0,
    "positions": 1.0,
    "aspects": 1.0,
}
BODY_ALIASES = {
    "fortune": "Part of Fortune",
    "part of fortune": "Part of Fortune",
    "true lilith": "Lilith",
    "lilith": "Lilith",
}
CANONICAL_FACTOR_NAMES = tuple(dict.fromkeys([*PLANET_ORDER, *ZODIAC_NAMES, "AS", "DS", "IC", "MC"]))
CANONICAL_FACTOR_LOOKUP = {name.casefold(): name for name in CANONICAL_FACTOR_NAMES}


def _active_human_design_gates(chart: Any) -> set[int]:
    cached = {
        int(gate)
        for gate in (getattr(chart, "human_design_gates", None) or [])
        if str(gate).strip().isdigit() and 1 <= int(gate) <= 64
    }
    if cached:
        return cached
    try:
        gates, _lines, _channels, _hd_type = derive_human_design_profile(chart)
    except Exception:
        return set()
    return {int(gate) for gate in gates if 1 <= int(gate) <= 64}


def _debug_log(message: str) -> None:
    if ENNEAGRAM_DEBUG_LOGGING:
        print(message)


def _normalize_factor_value(value: str) -> str:
    token = str(value or "").strip()
    canonical_alias = BODY_ALIASES.get(token.lower())
    if canonical_alias:
        return canonical_alias
    canonical_from_lookup = CANONICAL_FACTOR_LOOKUP.get(token.casefold())
    if canonical_from_lookup:
        return canonical_from_lookup
    normalized = normalize_body_name(token)
    if normalized:
        normalized_lookup = CANONICAL_FACTOR_LOOKUP.get(str(normalized).casefold())
        if normalized_lookup:
            return normalized_lookup
        return str(normalized)
    return token


def _normalize_string_set(values: Any) -> set[str]:
    return {
        _normalize_factor_value(str(value).strip())
        for value in values or set()
        if str(value).strip()
    }


def _normalize_house_set(values: Any) -> set[int]:
    return {
        int(house_num)
        for house_num in values or set()
        if str(house_num).strip().isdigit() and 1 <= int(house_num) <= 12
    }


def _normalize_gate_set(values: Any) -> set[int]:
    return {
        int(gate_num)
        for gate_num in values or set()
        if str(gate_num).strip().isdigit() and 1 <= int(gate_num) <= 64
    }


def _parse_house_token(token: str) -> int | None:
    match = re.fullmatch(r"H\s*(\d{1,2})", token.strip(), re.IGNORECASE)
    if not match:
        return None
    house_num = int(match.group(1))
    return house_num if 1 <= house_num <= 12 else None


def _parse_position_spec(raw_spec: str) -> tuple[str, str | int, str] | None:
    parts = [part.strip() for part in str(raw_spec).split(" in ")]
    if len(parts) != 2:
        return None
    left, right = parts
    if not left or not right:
        return None
    right_house = _parse_house_token(right)
    if right_house is not None:
        if left in ZODIAC_NAMES:
            return ("sign_in_house", right_house, left)
        return ("body_in_house", right_house, _normalize_factor_value(left))
    if right in ZODIAC_NAMES:
        return ("body_in_sign", right, _normalize_factor_value(left))
    return None


def _parse_aspect_spec(raw_spec: str) -> tuple[str, str, str] | None:
    text = str(raw_spec).strip()
    if not text:
        return None
    aspect_pattern = "|".join(sorted(ASPECT_SCORE_WEIGHTS.keys(), key=len, reverse=True))
    match = re.fullmatch(rf"(.+?)\s+({aspect_pattern})\s+(.+)", text, re.IGNORECASE)
    if not match:
        return None
    left = _normalize_factor_value(match.group(1).strip())
    aspect_type = match.group(2).strip().lower()
    right = _normalize_factor_value(match.group(3).strip())
    if not left or not right:
        return None
    return (left, aspect_type, right)


def _normalize_category_delta(
    positive_delta: float,
    negative_delta: float,
    *,
    criteria_count: int,
    anti_factor: float = ENNEAGRAM_ANTI_FACTOR,
) -> float:
    if criteria_count <= 0:
        return 0.0
    return (positive_delta - (anti_factor * negative_delta)) / float(criteria_count)


def calculate_enneagram_type_weights(
    chart: Any,
    *,
    enneagram: dict[int, dict[str, Any]],
    calculate_sign_weights: Callable[[Any], dict[str, float]],
    calculate_body_weights: Callable[[Any], dict[str, float]],
    calculate_house_weights: Callable[[Any], dict[int, float]],
    chart_uses_houses: Callable[[Any], bool],
) -> dict[int, float]:
    """Compute Enneagram type scores from chart-level dominant weights."""
    scores = {enneagram_type: 0.0 for enneagram_type in range(1, 10)}
    sign_weights = getattr(chart, "dominant_sign_weights", None) or calculate_sign_weights(chart)
    body_weights = getattr(chart, "dominant_planet_weights", None) or calculate_body_weights(chart)
    use_houses = chart_uses_houses(chart)
    house_weights = calculate_house_weights(chart) if use_houses else {}
    nakshatra_weights = getattr(chart, "dominant_nakshatra_weights", None) or calculate_dominant_nakshatra_weights(chart)
    chart_name = str(getattr(chart, "name", "Unnamed Chart"))
    body_house_lookup: dict[str, int] = {}
    if use_houses:
        for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
            body = _normalize_factor_value(str(raw_body))
            try:
                house_num = house_for_longitude(getattr(chart, "houses", None), float(lon))
            except (TypeError, ValueError):
                continue
            if house_num is not None:
                body_house_lookup[body] = house_num

    active_gates = _active_human_design_gates(chart)

    for enneagram_type, factors in enneagram.items():
        signs = _normalize_string_set(factors.get("signs", set()))
        antisigns = _normalize_string_set(factors.get("antisigns", set()))
        bodies = _normalize_string_set(factors.get("bodies", set()))
        antibodies = _normalize_string_set(factors.get("antibodies", set()))
        nakshatras = _normalize_string_set(factors.get("nakshatras", set()))
        antinakshatras = _normalize_string_set(factors.get("antinakshatras", set()))
        houses = _normalize_house_set(factors.get("houses", set()))
        antihouses = _normalize_house_set(factors.get("antihouses", set()))
        gates = _normalize_gate_set(factors.get("gates", set()))
        antigates = _normalize_gate_set(factors.get("antigates", set()))
        positions = {str(value).strip() for value in factors.get("positions", set()) if str(value).strip()}
        antipositions = {str(value).strip() for value in factors.get("antipositions", set()) if str(value).strip()}
        aspects = {str(value).strip() for value in factors.get("aspects", set()) if str(value).strip()}
        antiaspects = {str(value).strip() for value in factors.get("antiaspects", set()) if str(value).strip()}

        sign_positive = sum(float(sign_weights.get(sign, 0.0)) for sign in signs)
        sign_negative = sum(float(sign_weights.get(sign, 0.0)) for sign in antisigns)
        body_positive = sum(float(body_weights.get(body, 0.0)) for body in bodies)
        body_negative = sum(float(body_weights.get(body, 0.0)) for body in antibodies)
        nakshatra_positive = sum(float(nakshatra_weights.get(nakshatra, 0.0)) for nakshatra in nakshatras)
        nakshatra_negative = sum(
            float(nakshatra_weights.get(nakshatra, 0.0)) for nakshatra in antinakshatras
        )
        house_positive = 0.0
        house_negative = 0.0
        if use_houses:
            house_positive = sum(float(house_weights.get(house_num, 0.0)) for house_num in houses)
            house_negative = sum(float(house_weights.get(house_num, 0.0)) for house_num in antihouses)

        gates_positive = 0.0
        gates_negative = 0.0
        for gate in gates:
            if gate in active_gates:
                gates_positive += 6.0
        for gate in antigates:
            if gate in active_gates:
                gates_negative += 6.0

        positions_positive = 0.0
        for raw_position in positions:
            parsed = _parse_position_spec(raw_position)
            if parsed is None:
                continue
            category, container, subject = parsed
            bonus = 0.0
            if category == "body_in_house" and isinstance(container, int) and use_houses:
                body_house = body_house_lookup.get(subject)
                if body_house == container:
                    bonus = float(body_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
            elif category == "sign_in_house" and isinstance(container, int) and use_houses:
                for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
                    body = _normalize_factor_value(str(raw_body))
                    if body not in body_house_lookup or body_house_lookup[body] != container:
                        continue
                    try:
                        lon_value = float(lon)
                    except (TypeError, ValueError):
                        continue
                    if sign_for_longitude(lon_value) == subject:
                        bonus = float(sign_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
                        break
            elif category == "body_in_sign" and isinstance(container, str):
                body_lon = (getattr(chart, "positions", None) or {}).get(subject)
                try:
                    lon_value = float(body_lon)
                except (TypeError, ValueError):
                    lon_value = None
                if lon_value is not None and sign_for_longitude(lon_value) == container:
                    bonus = float(body_weights.get(subject, 0.0)) + float(sign_weights.get(container, 0.0))
            if bonus > 0:
                positions_positive += bonus
                _debug_log(
                    f"[Enneagram Debug] {chart_name}: type {enneagram_type} position TRUE -> "
                    f"'{raw_position}' (+{bonus:.2f})"
                )

        positions_negative = 0.0
        for raw_position in antipositions:
            parsed = _parse_position_spec(raw_position)
            if parsed is None:
                continue
            category, container, subject = parsed
            malus = 0.0
            if category == "body_in_house" and isinstance(container, int) and use_houses:
                body_house = body_house_lookup.get(subject)
                if body_house == container:
                    malus = float(body_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
            elif category == "sign_in_house" and isinstance(container, int) and use_houses:
                for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
                    body = _normalize_factor_value(str(raw_body))
                    if body not in body_house_lookup or body_house_lookup[body] != container:
                        continue
                    try:
                        lon_value = float(lon)
                    except (TypeError, ValueError):
                        continue
                    if sign_for_longitude(lon_value) == subject:
                        malus = float(sign_weights.get(subject, 0.0)) + float(house_weights.get(container, 0.0))
                        break
            elif category == "body_in_sign" and isinstance(container, str):
                body_lon = (getattr(chart, "positions", None) or {}).get(subject)
                try:
                    lon_value = float(body_lon)
                except (TypeError, ValueError):
                    lon_value = None
                if lon_value is not None and sign_for_longitude(lon_value) == container:
                    malus = float(body_weights.get(subject, 0.0)) + float(sign_weights.get(container, 0.0))
            if malus > 0:
                positions_negative += malus

        aspects_positive = 0.0
        for raw_aspect in aspects:
            parsed = _parse_aspect_spec(raw_aspect)
            if parsed is None:
                print(
                    f"[Enneagram Parse Error] {chart_name}: could not parse aspect spec '{raw_aspect}'"
                )
                continue
            left_body, aspect_type, right_body = parsed
            for aspect in getattr(chart, "aspects", []) or []:
                p1 = _normalize_factor_value(str(aspect.get("p1", "")))
                p2 = _normalize_factor_value(str(aspect.get("p2", "")))
                current_type = str(aspect.get("type", "")).strip().lower()
                if current_type != aspect_type:
                    continue
                if {p1, p2} != {left_body, right_body}:
                    continue
                aspect_weight = float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0))
                bonus = (
                    float(body_weights.get(left_body, 0.0))
                    + aspect_weight
                    + float(body_weights.get(right_body, 0.0))
                )
                aspects_positive += bonus
                _debug_log(
                    f"[Enneagram Debug] {chart_name}: type {enneagram_type} aspect TRUE -> "
                    f"'{raw_aspect}' (+{bonus:.2f})"
                )
                break

        aspects_negative = 0.0
        for raw_aspect in antiaspects:
            parsed = _parse_aspect_spec(raw_aspect)
            if parsed is None:
                print(
                    f"[Enneagram Parse Error] {chart_name}: could not parse antiaspect spec '{raw_aspect}'"
                )
                continue
            left_body, aspect_type, right_body = parsed
            for aspect in getattr(chart, "aspects", []) or []:
                p1 = _normalize_factor_value(str(aspect.get("p1", "")))
                p2 = _normalize_factor_value(str(aspect.get("p2", "")))
                current_type = str(aspect.get("type", "")).strip().lower()
                if current_type != aspect_type:
                    continue
                if {p1, p2} != {left_body, right_body}:
                    continue
                aspect_weight = float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0))
                malus = (
                    float(body_weights.get(left_body, 0.0))
                    + aspect_weight
                    + float(body_weights.get(right_body, 0.0))
                )
                aspects_negative += malus
                break

        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["signs"] * _normalize_category_delta(
            sign_positive,
            sign_negative,
            criteria_count=len(signs) + len(antisigns),
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["bodies"] * _normalize_category_delta(
            body_positive,
            body_negative,
            criteria_count=len(bodies) + len(antibodies),
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["nakshatras"] * _normalize_category_delta(
            nakshatra_positive,
            nakshatra_negative,
            criteria_count=len(nakshatras) + len(antinakshatras),
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["houses"] * _normalize_category_delta(
            house_positive,
            house_negative,
            criteria_count=(len(houses) + len(antihouses)) if use_houses else 0,
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["gates"] * _normalize_category_delta(
            gates_positive,
            gates_negative,
            criteria_count=len(gates) + len(antigates),
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["positions"] * _normalize_category_delta(
            positions_positive,
            positions_negative,
            criteria_count=len(positions) + len(antipositions),
        )
        scores[enneagram_type] += ENNEAGRAM_CATEGORY_WEIGHTS["aspects"] * _normalize_category_delta(
            aspects_positive,
            aspects_negative,
            criteria_count=len(aspects) + len(antiaspects),
        )

    return scores


def draw_enneagram_predictions(
    ax: Any,
    *,
    chart: Any,
    enneagram: dict[int, dict[str, Any]],
    calculate_type_weights: Callable[[Any], dict[int, float]],
    chart_theme_colors: dict[str, str],
    apply_standard_bar_axes: Callable[[Any, list[str]], None],
    standard_chart_layout: dict[str, float],
) -> None:
    """Draw the Enneagram prediction bar chart on the provided Matplotlib axis."""
    fallback_bar_color = str(
        chart_theme_colors.get("accent", chart_theme_colors.get("text", "#f5f5f5"))
    )
    text_color = str(chart_theme_colors.get("text", "#f5f5f5"))
    spine_color = str(chart_theme_colors.get("spine", "#444444"))

    type_labels = [str(num) for num in range(1, 10)]
    type_scores = calculate_type_weights(chart)
    values = [float(type_scores.get(num, 0.0)) for num in range(1, 10)]
    max_value = max(values) if values else 0.0

    enneagram_colors = [
        str(enneagram.get(num, {}).get("color", fallback_bar_color))
        for num in range(1, 10)
    ]
    bars = ax.bar(type_labels, values, color=enneagram_colors)
    apply_standard_bar_axes(ax, type_labels)
    ax.set_ylim(0, max(1.0, max_value + 1.0))
    ax.set_anchor("W")
    label_offset = max(0.15, (max_value * 0.02) if max_value else 0.15)
    for bar, type_label in zip(bars, type_labels, strict=True):
        bar.set_gid(f"enneagram:{type_label}")
        bar.set_picker(True)
        score = bar.get_height()
        ax.text(
            bar.get_x() + (bar.get_width() / 2.0),
            max(score, 0.0) + label_offset,
            f"{score:.0f}",
            ha="center",
            va="bottom",
            color=text_color,
            fontsize=7.5,
        )
    for spine in ax.spines.values():
        spine.set_color(spine_color)
    ax.figure.tight_layout()
    ax.figure.subplots_adjust(
        left=standard_chart_layout["left"],
        bottom=standard_chart_layout["bottom"],
        top=standard_chart_layout["top"],
        right=standard_chart_layout["right"],
    )


def build_enneagram_popout_info_html(
    enneagram_type: int,
    *,
    enneagram: dict[int, dict[str, Any]],
    chart_theme_colors: dict[str, str],
    highlight_color: str,
    debug_math_enabled: bool = False,
    chart: Any | None = None,
    calculate_type_weights: Callable[[Any], dict[int, float]] | None = None,
) -> str:
    """Build HTML for the Enneagram popout info panel selection."""
    text_color = str(chart_theme_colors.get("text", "#f5f5f5"))
    type_data = enneagram.get(int(enneagram_type), {})
    type_color = str(type_data.get("color") or text_color).strip() or text_color
    motivation = str(type_data.get("motivation", "No motivation data available.")).strip()
    description = str(type_data.get("description", "No description data available.")).strip()
    quotes = type_data.get("quotes", [])
    quote_list = [str(quote).strip() for quote in quotes if str(quote).strip()]
    selected_quote = random.choice(quote_list) if quote_list else "No quote available."

    debug_html = ""
    if debug_math_enabled and chart is not None and callable(calculate_type_weights):
        type_scores = calculate_type_weights(chart)
        selected_score = float(type_scores.get(int(enneagram_type), 0.0))
        factors = enneagram.get(int(enneagram_type), {})
        sign_weights = getattr(chart, "dominant_sign_weights", None) or {}
        body_weights = getattr(chart, "dominant_planet_weights", None) or {}
        nak_weights = getattr(chart, "dominant_nakshatra_weights", None) or {}
        use_houses = bool(getattr(chart, "house_system", None))
        house_weights = (
            (getattr(chart, "dominant_house_weights", None) or calculate_dominant_house_weights(chart))
            if use_houses
            else {}
        )
        body_house_lookup: dict[str, int] = {}
        if use_houses:
            for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
                try:
                    house_num = house_for_longitude(getattr(chart, "houses", None), float(lon))
                except (TypeError, ValueError):
                    continue
                if house_num is not None:
                    body_house_lookup[_normalize_factor_value(str(raw_body))] = house_num
        active_gates = _active_human_design_gates(chart)
        houses_pos = _normalize_house_set(factors.get("houses", set()))
        houses_neg = _normalize_house_set(factors.get("antihouses", set()))
        house_positive_total = (
            sum(float(house_weights.get(house_num, 0.0)) for house_num in houses_pos) if use_houses else 0.0
        )
        house_negative_total = (
            sum(float(house_weights.get(house_num, 0.0)) for house_num in houses_neg) if use_houses else 0.0
        )
        house_criteria_count = len(houses_pos) + len(houses_neg)
        house_normalized_delta = _normalize_category_delta(
            house_positive_total, house_negative_total, criteria_count=house_criteria_count if use_houses else 0
        )
        gates_pos = _normalize_gate_set(factors.get("gates", set()))
        gates_neg = _normalize_gate_set(factors.get("antigates", set()))
        gate_positive_total = sum(6.0 for gate in gates_pos if gate in active_gates)
        gate_negative_total = sum(6.0 for gate in gates_neg if gate in active_gates)
        gate_criteria_count = len(gates_pos) + len(gates_neg)
        gate_normalized_delta = _normalize_category_delta(
            gate_positive_total, gate_negative_total, criteria_count=gate_criteria_count
        )
        sorted_rows = "".join(
            (
                "<li>"
                f"<span style='color:{html.escape(str(enneagram.get(type_num, {}).get('color', text_color)))};"
                "font-weight:700;'>"
                f"Type {type_num}</span>: {float(type_scores.get(type_num, 0.0)):.4f}"
                "</li>"
            )
            for type_num in range(1, 10)
        )
        def _color_token(label: str, color: str) -> str:
            return f"<span style='color:{color};font-weight:700;'>{html.escape(label)}</span>"
        sign_items = "".join(
            f"<li>{_color_token(sign, SIGN_COLORS.get(sign, text_color))}: {float(sign_weights.get(sign, 0.0)):.4f}</li>"
            for sign in sorted(_normalize_string_set(factors.get('signs', set())))
        ) or "<li>None</li>"
        body_items = "".join(
            f"<li>{_color_token(body, PLANET_COLORS.get(body, text_color))}: {float(body_weights.get(body, 0.0)):.4f}</li>"
            for body in sorted(_normalize_string_set(factors.get('bodies', set())))
        ) or "<li>None</li>"
        house_items = "".join(
            f"<li>{_color_token(f'House {house_num}', HOUSE_COLORS.get(str(house_num), text_color))}: {float(house_weights.get(house_num, 0.0)):.4f}</li>"
            for house_num in sorted(_normalize_house_set(factors.get('houses', set())))
        ) or "<li>None</li>"
        anti_house_items = "".join(
            f"<li>{_color_token(f'House {house_num}', HOUSE_COLORS.get(str(house_num), text_color))}: {float(house_weights.get(house_num, 0.0)):.4f}</li>"
            for house_num in sorted(_normalize_house_set(factors.get('antihouses', set())))
        ) or "<li>None</li>"
        nak_items = "".join(
            f"<li>{_color_token(nak, NAKSHATRA_PLANET_COLOR.get(nak, (None, text_color))[1] or text_color)}: {float(nak_weights.get(nak, 0.0)):.4f}</li>"
            for nak in sorted(_normalize_string_set(factors.get('nakshatras', set())))
        ) or "<li>None</li>"
        anti_nak_items = "".join(
            f"<li>{_color_token(nak, NAKSHATRA_PLANET_COLOR.get(nak, (None, text_color))[1] or text_color)}: {float(nak_weights.get(nak, 0.0)):.4f}</li>"
            for nak in sorted(_normalize_string_set(factors.get('antinakshatras', set())))
        ) or "<li>None</li>"
        aspect_items_parts: list[str] = []
        for aspect in sorted({str(v).strip() for v in factors.get("aspects", set()) if str(v).strip()}):
            parsed_aspect = _parse_aspect_spec(aspect)
            if parsed_aspect is None:
                aspect_items_parts.append(f"<li>{html.escape(aspect)}</li>")
                continue
            left_body, aspect_type, right_body = parsed_aspect
            left_html = _color_token(left_body, PLANET_COLORS.get(left_body, text_color))
            aspect_html = _color_token(aspect_type.title(), ASPECT_COLORS.get(aspect_type.lower(), text_color))
            right_html = _color_token(right_body, PLANET_COLORS.get(right_body, text_color))
            aspect_items_parts.append(f"<li>{left_html} {aspect_html} {right_html}</li>")
        aspect_items = "".join(aspect_items_parts) or "<li>None</li>"
        anti_aspect_items_parts: list[str] = []
        for aspect in sorted({str(v).strip() for v in factors.get("antiaspects", set()) if str(v).strip()}):
            parsed_aspect = _parse_aspect_spec(aspect)
            if parsed_aspect is None:
                anti_aspect_items_parts.append(f"<li>{html.escape(aspect)}</li>")
                continue
            left_body, aspect_type, right_body = parsed_aspect
            left_html = _color_token(left_body, PLANET_COLORS.get(left_body, text_color))
            aspect_html = _color_token(aspect_type.title(), ASPECT_COLORS.get(aspect_type.lower(), text_color))
            right_html = _color_token(right_body, PLANET_COLORS.get(right_body, text_color))
            anti_aspect_items_parts.append(f"<li>{left_html} {aspect_html} {right_html}</li>")
        anti_aspect_items = "".join(anti_aspect_items_parts) or "<li>None</li>"
        anti_sign_items = "".join(
            f"<li>{_color_token(sign, SIGN_COLORS.get(sign, text_color))}: {float(sign_weights.get(sign, 0.0)):.4f}</li>"
            for sign in sorted(_normalize_string_set(factors.get('antisigns', set())))
        ) or "<li>None</li>"
        anti_body_items = "".join(
            f"<li>{_color_token(body, PLANET_COLORS.get(body, text_color))}: {float(body_weights.get(body, 0.0)):.4f}</li>"
            for body in sorted(_normalize_string_set(factors.get('antibodies', set())))
        ) or "<li>None</li>"
        gate_items = "".join(
            f"<li>Gate {gate}: {'✓ active' if gate in active_gates else '✗ inactive'}</li>"
            for gate in sorted(_normalize_gate_set(factors.get('gates', set())))
        ) or "<li>None</li>"
        anti_gate_items = "".join(
            f"<li>Gate {gate}: {'✓ active (negative hit)' if gate in active_gates else '✗ inactive'}</li>"
            for gate in sorted(_normalize_gate_set(factors.get('antigates', set())))
        ) or "<li>None</li>"
        position_items = "".join(
            f"<li>{html.escape(position)}: {'✓ parsed' if _parse_position_spec(position) is not None else '✗ parse error'}</li>"
            for position in sorted({str(v).strip() for v in factors.get('positions', set()) if str(v).strip()})
        ) or "<li>None</li>"
        anti_position_items = "".join(
            f"<li>{html.escape(position)}: {'✓ parsed' if _parse_position_spec(position) is not None else '✗ parse error'}</li>"
            for position in sorted({str(v).strip() for v in factors.get('antipositions', set()) if str(v).strip()})
        ) or "<li>None</li>"
        formula_bits = ", ".join(
            f"{category}×{weight:.2f}" for category, weight in ENNEAGRAM_CATEGORY_WEIGHTS.items()
        )
        debug_html = (
            "<hr style='margin-top:12px;margin-bottom:10px;border:0;border-top:1px solid #555;'/>"
            f"<div style='font-size:13px;color:{text_color};'>"
            f"<div style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Calculator debug details</div>"
            "<div style='margin-top:6px;'>"
            "Score model (per type): normalized contribution per criterion = "
            "(positive matched-weight sum - anti_factor × negative matched-weight sum) / criterion_count."
            "</div>"
            f"<div style='margin-top:6px;'>Category weights currently used: {html.escape(formula_bits)}; "
            f"anti_factor={ENNEAGRAM_ANTI_FACTOR:.2f}.</div>"
            f"<div style='margin-top:6px;'>Selected type final score: <b>{selected_score:.4f}</b>.</div>"
            "<div style='margin-top:6px;'>All final type scores (so you can verify ranking math):</div>"
            f"<ol style='margin-top:4px;'>{sorted_rows}</ol>"
            f"<div style='margin-top:8px;font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Criterion breakdown for selected type</div>"
            "<ul style='margin-top:4px;'>"
            f"<li><b>Signs (+)</b><ul>{sign_items}</ul></li>"
            f"<li><b>Signs (-)</b><ul>{anti_sign_items}</ul></li>"
            f"<li><b>Bodies (+)</b><ul>{body_items}</ul></li>"
            f"<li><b>Bodies (-)</b><ul>{anti_body_items}</ul></li>"
            f"<li><b>Houses (+)</b><ul>{house_items}</ul></li>"
            f"<li><b>Houses (-)</b><ul>{anti_house_items}</ul></li>"
            f"<li><b>Houses contribution</b>: +{house_positive_total:.4f} / -{house_negative_total:.4f} "
            f"→ normalized {house_normalized_delta:.4f}</li>"
            f"<li><b>Nakshatras (+)</b><ul>{nak_items}</ul></li>"
            f"<li><b>Nakshatras (-)</b><ul>{anti_nak_items}</ul></li>"
            f"<li><b>HD Gates (+)</b><ul>{gate_items}</ul></li>"
            f"<li><b>HD Gates (-)</b><ul>{anti_gate_items}</ul></li>"
            f"<li><b>HD Gates contribution</b>: +{gate_positive_total:.4f} / -{gate_negative_total:.4f} "
            f"→ normalized {gate_normalized_delta:.4f}; active gates detected: {len(active_gates)}</li>"
            f"<li><b>Positions (+)</b><ul>{position_items}</ul></li>"
            f"<li><b>Positions (-)</b><ul>{anti_position_items}</ul></li>"
            f"<li><b>Aspects (+)</b><ul>{aspect_items}</ul></li>"
            f"<li><b>Aspects (-)</b><ul>{anti_aspect_items}</ul></li>"
            "</ul>"
            "<div style='margin-top:6px;'>"
            "To verify manually with a calculator: compute each criterion's normalized value, multiply each by the criterion weight, then sum all weighted criterion values for the final type score."
            "</div>"
            "</div>"
        )

    return (
        f"<div style='font-size:18px;font-weight:700;color:{html.escape(type_color)};'>"
        f"Enneagram Type {enneagram_type}"
        "</div>"
        f"<div style='margin-top:8px;'><span style='font-weight:700;color:{highlight_color};'>"
        "Motivation:"
        f"</span> {html.escape(motivation)}</div>"
        f"<div style='margin-top:8px;font-size:12px;color:{text_color};font-style:italic;'>"
        f"{html.escape(selected_quote)}"
        "</div>"
        f"<div style='margin-top:8px;color:{text_color};'>"
        f"{html.escape(description)}"
        "</div>"
        f"{debug_html}"
    )


def tritype_text_for_scores(type_scores: dict[int, float]) -> str:
    """Return the top-ranked tritype string from Enneagram scores."""
    ranked_types = sorted(
        range(1, 10),
        key=lambda type_num: (float(type_scores.get(type_num, 0.0)), -type_num),
        reverse=True,
    )[:3]
    return "-".join(str(type_num) for type_num in ranked_types)


def connect_enneagram_popout_pick_handler(
    popout_canvas: Any,
    info_panel: Any,
    *,
    build_info_html: Callable[[int], str],
) -> None:
    """Attach standard Enneagram bar click behavior to the popout chart canvas."""

    def _on_pick(event) -> None:
        artist = getattr(event, "artist", None)
        artist_gid = artist.get_gid() if artist is not None else None
        if not isinstance(artist_gid, str) or ":" not in artist_gid:
            return
        chart_key, raw_value = artist_gid.split(":", 1)
        if chart_key != "enneagram":
            return
        try:
            enneagram_type = int(raw_value)
        except ValueError:
            return
        info_panel.setHtml(build_info_html(enneagram_type))

    popout_canvas.mpl_connect("pick_event", _on_pick)
