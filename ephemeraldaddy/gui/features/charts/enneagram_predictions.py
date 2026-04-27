"""Enneagram prediction chart rendering and popout info helpers."""

from __future__ import annotations

import html
import random
import re
from typing import Any, Callable

from ephemeraldaddy.core.interpretations import (
    ASPECT_SCORE_WEIGHTS,
    PLANET_ORDER,
    ZODIAC_NAMES,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_nakshatra_weights, house_for_longitude
from ephemeraldaddy.gui.features.charts.presentation import sign_for_longitude


ENNEAGRAM_DEBUG_LOGGING = False
BODY_ALIASES = {
    "fortune": "Part of Fortune",
    "part of fortune": "Part of Fortune",
    "true lilith": "Lilith",
    "lilith": "Lilith",
}
CANONICAL_FACTOR_NAMES = tuple(dict.fromkeys([*PLANET_ORDER, *ZODIAC_NAMES, "AS", "DS", "IC", "MC"]))
CANONICAL_FACTOR_LOOKUP = {name.casefold(): name for name in CANONICAL_FACTOR_NAMES}


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

    active_gates = {
        int(gate)
        for gate in (getattr(chart, "human_design_gates", None) or [])
        if str(gate).strip().isdigit() and 1 <= int(gate) <= 64
    }

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

        scores[enneagram_type] += sum(float(sign_weights.get(sign, 0.0)) for sign in signs)
        scores[enneagram_type] -= sum(float(sign_weights.get(sign, 0.0)) for sign in antisigns)
        scores[enneagram_type] += sum(float(body_weights.get(body, 0.0)) for body in bodies)
        scores[enneagram_type] -= sum(float(body_weights.get(body, 0.0)) for body in antibodies)
        scores[enneagram_type] += sum(float(nakshatra_weights.get(nakshatra, 0.0)) for nakshatra in nakshatras)
        scores[enneagram_type] -= sum(
            float(nakshatra_weights.get(nakshatra, 0.0)) for nakshatra in antinakshatras
        )
        if use_houses:
            scores[enneagram_type] += sum(float(house_weights.get(house_num, 0.0)) for house_num in houses)
            scores[enneagram_type] -= sum(float(house_weights.get(house_num, 0.0)) for house_num in antihouses)

        for gate in gates:
            if gate in active_gates:
                scores[enneagram_type] += 6.0
        for gate in antigates:
            if gate in active_gates:
                scores[enneagram_type] -= 6.0

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
                scores[enneagram_type] += bonus
                _debug_log(
                    f"[Enneagram Debug] {chart_name}: type {enneagram_type} position TRUE -> "
                    f"'{raw_position}' (+{bonus:.2f})"
                )

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
                scores[enneagram_type] -= malus

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
                scores[enneagram_type] += bonus
                _debug_log(
                    f"[Enneagram Debug] {chart_name}: type {enneagram_type} aspect TRUE -> "
                    f"'{raw_aspect}' (+{bonus:.2f})"
                )
                break

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
                scores[enneagram_type] -= malus
                break

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
