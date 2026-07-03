"""Chart View analytics popout info rendering helpers."""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from ephemeraldaddy.analysis.get_astro_twin import build_body_dominance_explanation_bullets
from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    ELEMENT_COLORS,
    HOUSE_COLORS,
    MODE_COLORS,
    MODES,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    PLANET_ORDER,
    SIGN_ELEMENTS,
    SIGN_COLORS,
    ZODIAC_NAMES,
)

if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart


def _display_body_name(body: str) -> str:
    if body == "Lilith (mean)":
        return "Black☽ Lilith"
    if body == "Lilith":
        from ephemeraldaddy.core.ephemeris import get_lilith_display_name

        display_name = get_lilith_display_name()
        if display_name == "Black Moon Lilith":
            return "Black☽ Lilith"
        return display_name
    if body == "Part of Fortune":
        return "Fortune"
    return body


def _sign_for_longitude(lon: float) -> str:
    return ZODIAC_NAMES[int((float(lon) % 360.0) // 30) % 12]


def colorized_dominance_label_html(label: object, color: object | None) -> str:
    """Return escaped HTML for one colored dominance-reasoning token."""
    label_text = str(label or "")
    color_text = str(color or "").strip()
    if not color_text:
        return html.escape(label_text)
    return (
        f'<span style="color: {html.escape(color_text)}; font-weight: 600;">'
        f"{html.escape(label_text)}</span>"
    )


def dominance_body_label_html(body: str, *, fallback_text_color: str) -> str:
    """Return a dominant-body label colored from interpretations.PLANET_COLORS."""
    return colorized_dominance_label_html(
        _display_body_name(body),
        PLANET_COLORS.get(body, fallback_text_color),
    )


def dominance_sign_label_html(sign: str, *, fallback_text_color: str) -> str:
    """Return a zodiac-sign label colored from interpretations.SIGN_COLORS."""
    return colorized_dominance_label_html(
        sign,
        SIGN_COLORS.get(sign, fallback_text_color),
    )


def dominance_house_label_html(house_num: int | str, *, fallback_text_color: str) -> str:
    """Return a house label colored from interpretations.HOUSE_COLORS."""
    house_label = f"House {house_num}"
    return colorized_dominance_label_html(
        house_label,
        HOUSE_COLORS.get(str(house_num), fallback_text_color),
    )


def dominance_aspect_label_html(aspect_type: str, *, fallback_text_color: str) -> str:
    """Return an aspect label colored from interpretations.ASPECT_COLORS."""
    aspect_label = str(aspect_type or "aspect").strip() or "aspect"
    aspect_key = aspect_label.replace(" ", "_").lower()
    return colorized_dominance_label_html(
        aspect_label,
        ASPECT_COLORS.get(aspect_key, fallback_text_color),
    )


def dominance_element_label_html(element: str, *, fallback_text_color: str) -> str:
    """Return an element label colored from interpretations.ELEMENT_COLORS."""
    return colorized_dominance_label_html(
        str(element or "").title(),
        ELEMENT_COLORS.get(str(element or "").title(), fallback_text_color),
    )


def dominance_mode_label_html(mode: str, *, fallback_text_color: str) -> str:
    """Return a mode label colored from interpretations.MODE_COLORS."""
    mode_key = str(mode or "").strip().lower()
    return colorized_dominance_label_html(
        mode_key.title(),
        MODE_COLORS.get(mode_key, fallback_text_color),
    )


def dominance_nakshatra_label_html(nakshatra: str, *, fallback_text_color: str) -> str:
    """Return a nakshatra label colored by its planetary ruler color."""
    return colorized_dominance_label_html(
        nakshatra,
        NAKSHATRA_PLANET_COLOR.get(str(nakshatra), (None, fallback_text_color))[1],
    )


def dominance_reason_line_html(text: object, *, fallback_text_color: str) -> str:
    """Color known body/sign/house/aspect tokens within a reasoning sentence."""
    raw_text = str(text or "")
    body_labels: dict[str, str] = {}
    for body in PLANET_COLORS:
        display = _display_body_name(body)
        body_labels[body] = body
        body_labels[display] = body

    token_labels = sorted(
        set(body_labels)
        | set(ZODIAC_NAMES)
        | {key.replace("_", " ") for key in ASPECT_COLORS},
        key=len,
        reverse=True,
    )
    token_pattern = "|".join(re.escape(label) for label in token_labels if label)
    pattern = re.compile(
        rf"(?<![\w])(?:House\s+(?P<house>1[0-2]|[1-9])|(?P<token>{token_pattern}))(?![\w])",
        re.IGNORECASE,
    )

    parts: list[str] = []
    last_end = 0
    for match in pattern.finditer(raw_text):
        parts.append(html.escape(raw_text[last_end : match.start()]))
        house_match = match.group("house")
        if house_match:
            parts.append(
                dominance_house_label_html(
                    house_match,
                    fallback_text_color=fallback_text_color,
                )
            )
        else:
            token = match.group("token") or match.group(0)
            canonical_body = next(
                (body for label, body in body_labels.items() if label.lower() == token.lower()),
                None,
            )
            if canonical_body is not None:
                parts.append(
                    colorized_dominance_label_html(
                        token,
                        PLANET_COLORS.get(canonical_body, fallback_text_color),
                    )
                )
            else:
                canonical_sign = next(
                    (sign for sign in ZODIAC_NAMES if sign.lower() == token.lower()),
                    None,
                )
                if canonical_sign is not None:
                    parts.append(
                        dominance_sign_label_html(
                            canonical_sign,
                            fallback_text_color=fallback_text_color,
                        )
                    )
                else:
                    aspect_key = token.replace(" ", "_").lower()
                    parts.append(
                        colorized_dominance_label_html(
                            token,
                            ASPECT_COLORS.get(aspect_key, fallback_text_color),
                        )
                    )
        last_end = match.end()
    parts.append(html.escape(raw_text[last_end:]))
    return "".join(parts)


def dominance_section_header_html(chart: Chart, *, highlight_color: str) -> str:
    """Return the shared dominance-reasoning section header."""
    chart_name = str(getattr(chart, "name", "") or "").strip() or "this chart"
    return (
        f'<div style="font-weight: bold; color: {html.escape(highlight_color)}; margin-top: 0.75em;">'
        f"Why Dominant (or Not)? (for {html.escape(chart_name)})"
        "</div>"
    )


def build_sign_dominance_section_html(
    chart: Chart,
    sign_name: str,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Signs popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "sign_prevalence":
        lines.append(
            "<ul><li>Sign Prevalence mode is active "
            "(raw placements, not weighted dominance).</li></ul>"
        )
        return "".join(lines)

    from ephemeraldaddy.gui.features.charts.metrics import (
        _aspect_strength,
        chart_uses_houses,
        house_for_longitude,
        planet_sign_weight,
    )

    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    placement_lines: list[str] = []
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None or _sign_for_longitude(lon) != sign_name:
            continue
        house_num = house_for_longitude(houses, lon)
        _weighted_sign, body_weight = planet_sign_weight(body, lon, houses, house_num)
        placement_lines.append(
            f"{dominance_body_label_html(body, fallback_text_color=fallback_text_color)} "
            f"in {dominance_sign_label_html(sign_name, fallback_text_color=fallback_text_color)}"
            + (
                f", {dominance_house_label_html(house_num, fallback_text_color=fallback_text_color)}"
                if house_num
                else ""
            )
            + f" (base sign weight {body_weight:.2f})"
        )

    if placement_lines:
        lines.append("<ul>" + "".join(f"<li>{entry}</li>" for entry in placement_lines) + "</ul>")
    else:
        lines.append("<ul><li>No chart points are currently in this sign.</li></ul>")

    aspect_lines: list[str] = []
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = str(aspect.get("p1", ""))
        p2 = str(aspect.get("p2", ""))
        lon1 = chart.positions.get(p1)
        lon2 = chart.positions.get(p2)
        if lon1 is None or lon2 is None:
            continue
        if sign_name not in {_sign_for_longitude(lon1), _sign_for_longitude(lon2)}:
            continue
        aspect_type = str(aspect.get("type", "")).strip() or "aspect"
        aspect_weight = _aspect_strength(aspect)
        if aspect_weight <= 0:
            continue
        aspect_lines.append(
            f"{dominance_body_label_html(p1, fallback_text_color=fallback_text_color)} "
            f"{dominance_aspect_label_html(aspect_type, fallback_text_color=fallback_text_color)} "
            f"{dominance_body_label_html(p2, fallback_text_color=fallback_text_color)} "
            f"(aspect weight of {aspect_weight:.2f})"
        )
    if aspect_lines:
        lines.append(
            "<ul>"
            + "".join(f"<li>{entry}</li>" for entry in aspect_lines[:8])
            + "</ul>"
        )
    return "".join(lines)


def build_body_dominance_section_html(
    chart: Chart,
    body_name: str,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Bodies popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "sidereal_planet_prevalence":
        lines.append(
            "<ul><li>Sidereal Planet Prevalence mode is active "
            "(raw prevalence count, not weighted dominance).</li></ul>"
        )
        return "".join(lines)

    lon = chart.positions.get(body_name)
    if lon is None:
        lines.append("<ul><li>This body is unavailable in the current chart.</li></ul>")
        return "".join(lines)

    bullets = build_body_dominance_explanation_bullets(
        chart,
        body_name,
        _display_body_name,
    )
    lines.append(
        "<ul>"
        + "".join(
            f"<li>{dominance_reason_line_html(bullet, fallback_text_color=fallback_text_color)}</li>"
            for bullet in bullets
        )
        + "</ul>"
    )
    return "".join(lines)


def build_house_dominance_section_html(
    chart: Chart,
    target_house: int,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Houses popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "house_prevalence":
        lines.append(
            "<ul><li>House Prevalence mode is active: each listed body/point "
            "counts once, with no weights applied.</li></ul>"
        )
        return "".join(lines)
    from ephemeraldaddy.gui.features.charts.metrics import (
        chart_uses_houses,
        dominant_planet_keys,
        house_for_longitude,
        house_membership_weights,
        house_span_signs,
        planet_weight,
    )

    if not chart_uses_houses(chart):
        lines.append(
            "<ul><li>Houses are unavailable for this chart, so no house-dominance "
            "scoring can be applied.</li></ul>"
        )
        return "".join(lines)
    houses = getattr(chart, "houses", None)
    if not houses:
        lines.append("<ul><li>House cusp data is missing.</li></ul>")
        return "".join(lines)

    spans = house_span_signs(houses)
    span = spans[target_house - 1] if 1 <= target_house <= 12 else []
    bullets = [
        f"House {target_house} spans: {', '.join(sign for sign in span) if span else 'n/a'}."
    ]

    contributing_points: list[str] = []
    for body in list(dominant_planet_keys(chart)) + ["AS", "IC", "DS", "MC"]:
        lon = chart.positions.get(body)
        if lon is None:
            continue
        membership = house_membership_weights(houses, lon)
        share = float(membership.get(target_house, 0.0))
        if share <= 0:
            continue
        primary_house = house_for_longitude(houses, lon)
        if primary_house is None:
            continue
        body_weight = planet_weight(body, lon, houses, primary_house)
        contributing_points.append(
            f"{_display_body_name(body)}: {body_weight:.2f} × {share:.2f} share"
        )
    if contributing_points:
        bullets.extend(contributing_points[:14])
    else:
        bullets.append("No bodies/angles contributed weight to this house.")
    lines.append(
        "<ul>"
        + "".join(
            f"<li>{dominance_reason_line_html(entry, fallback_text_color=fallback_text_color)}</li>"
            for entry in bullets
        )
        + "</ul>"
    )
    return "".join(lines)


def build_element_dominance_section_html(
    chart: Chart,
    element_name: str,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Elements popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "elemental_prevalence":
        lines.append(
            "<ul><li>Elemental Prevalence mode is active: each placement contributes "
            "equally through its sign's element, with no dominance weights applied.</li></ul>"
        )
        return "".join(lines)

    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_sign_weights

    element_label = str(element_name or "").strip().title()
    sign_weights = calculate_dominant_sign_weights(chart)
    contributors: list[tuple[str, float]] = [
        (sign, float(weight))
        for sign, weight in sign_weights.items()
        if SIGN_ELEMENTS.get(sign) == element_label and float(weight) > 0
    ]
    contributors.sort(key=lambda item: item[1], reverse=True)
    if not contributors:
        lines.append(
            f"<ul><li>No weighted sign contributions currently roll up into "
            f"{dominance_element_label_html(element_label, fallback_text_color=fallback_text_color)}.</li></ul>"
        )
        return "".join(lines)
    lines.append(
        "<ul>"
        + "".join(
            "<li>"
            f"{dominance_sign_label_html(sign, fallback_text_color=fallback_text_color)} "
            f"contributes {weight:.2f} weighted sign points to "
            f"{dominance_element_label_html(element_label, fallback_text_color=fallback_text_color)}"
            "</li>"
            for sign, weight in contributors
        )
        + "</ul>"
    )
    return "".join(lines)


def build_mode_dominance_section_html(
    chart: Chart,
    mode_name: str,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Modes popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "modal_prevalence":
        lines.append(
            "<ul><li>Modal Prevalence mode is active: each placement contributes "
            "equally through its sign's modality, with no dominance weights applied.</li></ul>"
        )
        return "".join(lines)

    from ephemeraldaddy.gui.features.charts.metrics import calculate_dominant_sign_weights

    mode_key = str(mode_name or "").strip().lower()
    sign_weights = calculate_dominant_sign_weights(chart)
    contributors: list[tuple[str, float]] = [
        (sign, float(sign_weights.get(sign, 0.0)))
        for sign in MODES.get(mode_key, set())
        if float(sign_weights.get(sign, 0.0)) > 0
    ]
    contributors.sort(key=lambda item: item[1], reverse=True)
    if not contributors:
        lines.append(
            f"<ul><li>No weighted sign contributions currently roll up into "
            f"{dominance_mode_label_html(mode_key, fallback_text_color=fallback_text_color)}.</li></ul>"
        )
        return "".join(lines)
    lines.append(
        "<ul>"
        + "".join(
            "<li>"
            f"{dominance_sign_label_html(sign, fallback_text_color=fallback_text_color)} "
            f"contributes {weight:.2f} weighted sign points to "
            f"{dominance_mode_label_html(mode_key, fallback_text_color=fallback_text_color)}"
            "</li>"
            for sign, weight in contributors
        )
        + "</ul>"
    )
    return "".join(lines)


def build_nakshatra_dominance_section_html(
    chart: Chart,
    nakshatra_name: str,
    *,
    mode: str,
    highlight_color: str,
    fallback_text_color: str,
) -> str:
    """Build the Dominant Nakshatras popout's weighted-reasoning section."""
    lines: list[str] = [dominance_section_header_html(chart, highlight_color=highlight_color)]
    if mode == "nakshatra_prevalence":
        lines.append(
            "<ul><li>Nakshatra Prevalence mode is active: placements are counted by "
            "nakshatra without dominance weights or aspect bonuses.</li></ul>"
        )
        return "".join(lines)

    from ephemeraldaddy.gui.features.charts.metrics import (
        _aspect_strength,
        chart_uses_houses,
        get_nakshatra,
        house_for_longitude,
        planet_weight,
    )

    target = str(nakshatra_name or "").strip()
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    bodies = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
    if use_houses:
        bodies.extend(["AS", "IC", "DS", "MC"])

    placement_lines: list[str] = []
    for body in bodies:
        lon = chart.positions.get(body)
        if lon is None or get_nakshatra(lon) != target:
            continue
        house_num = house_for_longitude(houses, lon)
        weight = planet_weight(body, lon, houses, house_num)
        placement_lines.append(
            f"{dominance_body_label_html(body, fallback_text_color=fallback_text_color)} in "
            f"{dominance_nakshatra_label_html(target, fallback_text_color=fallback_text_color)} "
            f"(body/house weight {weight:.2f})"
        )

    aspect_lines: list[str] = []
    allowed_bodies = set(bodies)
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = str(aspect.get("p1", ""))
        p2 = str(aspect.get("p2", ""))
        if p1 not in allowed_bodies or p2 not in allowed_bodies:
            continue
        lon1 = chart.positions.get(p1)
        lon2 = chart.positions.get(p2)
        if lon1 is None or lon2 is None:
            continue
        if target not in {get_nakshatra(lon1), get_nakshatra(lon2)}:
            continue
        aspect_weight = _aspect_strength(aspect)
        if aspect_weight <= 0:
            continue
        aspect_type = str(aspect.get("type", "")).strip() or "aspect"
        aspect_lines.append(
            f"{dominance_body_label_html(p1, fallback_text_color=fallback_text_color)} "
            f"{dominance_aspect_label_html(aspect_type, fallback_text_color=fallback_text_color)} "
            f"{dominance_body_label_html(p2, fallback_text_color=fallback_text_color)} "
            f"(aspect contribution {aspect_weight:.2f})"
        )

    all_lines = placement_lines + aspect_lines[:8]
    if all_lines:
        lines.append("<ul>" + "".join(f"<li>{entry}</li>" for entry in all_lines) + "</ul>")
    else:
        lines.append(
            f"<ul><li>No bodies or scored aspects currently contribute to "
            f"{dominance_nakshatra_label_html(target, fallback_text_color=fallback_text_color)}.</li></ul>"
        )
    return "".join(lines)
