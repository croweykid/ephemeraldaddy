"""Window-independent Markdown export rendering for one chart."""

from __future__ import annotations

import json

from ephemeraldaddy.core.aspect_display import iter_displayable_aspects
from ephemeraldaddy.core.astrology import sign_for_longitude
from ephemeraldaddy.core.chart import resolve_use_birth_time_data
from ephemeraldaddy.core.interpretations import PLANET_ORDER, ZODIAC_NAMES, aspect_score


def _format_longitude(longitude: float) -> str:
    normalized = longitude % 360.0
    sign_index = int(normalized // 30) % 12
    degrees_in_sign = normalized % 30.0
    degrees = int(degrees_in_sign)
    minutes = int(round((degrees_in_sign - degrees) * 60))
    if minutes == 60:
        minutes = 0
        degrees += 1
        if degrees == 30:
            degrees = 0
            sign_index = (sign_index + 1) % 12
    return f"{degrees:02d}°{minutes:02d}' {ZODIAC_NAMES[sign_index]}"


def _format_degree_minutes(value: float, *, include_sign: bool = True) -> str:
    magnitude = abs(float(value))
    degrees = int(magnitude)
    minutes = int(round((magnitude - degrees) * 60))
    if minutes == 60:
        degrees += 1
        minutes = 0
    prefix = "-" if value < 0 and include_sign else ""
    return f"{prefix}{degrees:02d}°{minutes:02d}'"


def _house_for_longitude(cusps: list[float] | None, longitude: float) -> int | None:
    if not cusps or len(cusps) < 12:
        return None
    normalized = longitude % 360.0
    for index in range(12):
        start = cusps[index] % 360.0
        end = cusps[(index + 1) % 12] % 360.0
        if end <= start:
            end += 360.0
        candidate = normalized + 360.0 if normalized < start else normalized
        if start <= candidate < end:
            return index + 1
    return None


def _aspect_label(aspect_type: str) -> str:
    return aspect_type.replace("_", " ").title()


def build_chart_export_markdown(chart: object) -> str:
    """Return the complete Markdown export for ``chart`` without GUI state."""
    dt = getattr(chart, "dt", None)
    date_label = dt.strftime("%Y-%m-%d") if dt else "Unknown"
    time_label = (
        "Unknown"
        if getattr(chart, "birthtime_unknown", False) or dt is None
        else dt.strftime("%H:%M %Z")
    )
    name = getattr(chart, "name", None) or "Unnamed"
    alias = getattr(chart, "alias", None) or ""
    birth_place = getattr(chart, "birth_place", None) or "Unknown"
    use_houses = bool(resolve_use_birth_time_data(chart))
    houses = getattr(chart, "houses", None) if use_houses else None

    lines = [
        f"# Chart Export: {name}",
        "",
        "## Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Name | {name} |",
        f"| Alias | {alias or '—'} |",
        f"| 🐣Date | {date_label} |",
        f"| 🐣Time | {time_label} |",
        f"| 🐣Place | {birth_place} |",
        f"| Latitude / Longitude | {getattr(chart, 'lat', 0.0):.4f} / {getattr(chart, 'lon', 0.0):.4f} |",
        f"| 🐣Time unknown | {getattr(chart, 'birthtime_unknown', False)} |",
        f"| Rectified 🐣Time used | {getattr(chart, 'retcon_time_used', False)} |",
        f"| UTC fallback used | {getattr(chart, 'used_utc_fallback', False)} |",
        "",
        "## Positions",
        "",
        "| Body | Position | Sign | House |",
        "| --- | --- | --- | --- |",
    ]

    positions = getattr(chart, "positions", {}) or {}
    ordered_bodies = [body for body in PLANET_ORDER if body in positions]
    ordered_bodies.extend(sorted(set(positions).difference(ordered_bodies)))
    for body in ordered_bodies:
        longitude = positions.get(body)
        if longitude is None:
            lines.append(f"| {body} | Unknown | Unknown | — |")
            continue
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            lines.append(f"| {body} | Unknown (🐣Time unknown) | Unknown | — |")
            continue
        house_number = _house_for_longitude(houses, longitude) if use_houses else None
        lines.append(
            f"| {body} | {_format_longitude(longitude)} | "
            f"{sign_for_longitude(longitude)} | {house_number or '—'} |"
        )

    if use_houses and houses:
        lines.extend(["", "## House Cusps", "", "| House | Cusp |", "| --- | --- |"])
        for index, cusp in enumerate(houses[:12], start=1):
            lines.append(f"| {index} | {_format_longitude(cusp)} |")

    lines.extend(
        [
            "",
            "## Aspects",
            "",
            "| Body A | Aspect | Body B | Exact Angle | Orb (Δ) | Score |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    aspects = list(
        iter_displayable_aspects(
            getattr(chart, "aspects", None) or [],
            use_houses=use_houses,
            known_positions=positions,
        )
    )
    if not aspects:
        lines.append("| — | — | — | — | — | — |")
    else:
        # Transitional dependency: aspect scoring still lives in the legacy
        # charts package. Keeping it lazy preserves this pure export module's
        # non-Qt import path until that calculation receives its canonical home.
        planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not planet_weights:
            from ephemeraldaddy.gui.features.charts.metrics import (
                calculate_dominant_planet_weights,
            )

            planet_weights = calculate_dominant_planet_weights(chart)
        aspects.sort(
            key=lambda aspect: aspect_score(aspect, planet_weights=planet_weights),
            reverse=True,
        )
        for aspect in aspects:
            lines.append(
                "| "
                f"{aspect.get('p1', '?')} | {_aspect_label(aspect.get('type', ''))} | {aspect.get('p2', '?')} | "
                f"{_format_degree_minutes(float(aspect.get('angle', 0.0)), include_sign=False)} | "
                f"{_format_degree_minutes(float(aspect.get('delta', 0.0)))} | "
                f"{aspect_score(aspect, planet_weights=planet_weights):.2f} |"
            )

    as_dict = getattr(chart, "as_dict")
    lines.extend(
        ["", "## Raw Chart Data (JSON)", "", "```json", json.dumps(as_dict(), indent=2, ensure_ascii=False), "```", ""]
    )
    return "\n".join(lines)
