"""Presentation-oriented formatting helpers for chart-facing GUI text."""

from __future__ import annotations

import datetime
import html
from functools import lru_cache
from typing import Any

from matplotlib import font_manager as mpl_font_manager

from ephemeraldaddy.core.hd import get_channels_for_gate, get_line
from ephemeraldaddy.core.interpretations import (
    NAKSHATRA_PLANET_COLOR,
    NAKSHATRA_DESCRIPTIONS,
    NAKSHATRA_RANGES,
    ZODIAC_NAMES,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR


def format_longitude(lon: float) -> str:
    """Return something like 10°23' Aries."""
    lon = lon % 360.0
    sign_index = int(lon // 30) % 12
    sign = ZODIAC_NAMES[sign_index]
    degrees_in_sign = lon % 30.0
    deg = int(degrees_in_sign)
    minutes = int(round((degrees_in_sign - deg) * 60))

    # Handle 29°59' rounding to 30°00'.
    if minutes == 60:
        minutes = 0
        deg += 1
        if deg == 30:
            deg = 0
            sign_index = (sign_index + 1) % 12
            sign = ZODIAC_NAMES[sign_index]

    return f"{deg:02d}°{minutes:02d}' {sign}"


def format_degree_minutes(value: float, *, include_sign: bool = True) -> str:
    magnitude = abs(float(value))
    deg = int(magnitude)
    minutes = int(round((magnitude - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    prefix = "-" if value < 0 and include_sign else ""
    return f"{prefix}{deg:02d}°{minutes:02d}'"


def format_transit_range(
    start_dt: datetime.datetime | None,
    end_dt: datetime.datetime | None,
    *,
    include_time: bool,
    start_truncated_to_scope: bool = False,
    end_truncated_to_scope: bool = False,
) -> str:
    stamp = "%m-%d-%Y %H:%M" if include_time else "%m-%d-%Y"

    start_label = start_dt.strftime(stamp) if start_dt is not None else "…"
    end_label = end_dt.strftime(stamp) if end_dt is not None else "…"
    if start_truncated_to_scope:
        start_label = f"{start_label}*"
    if end_truncated_to_scope:
        end_label = f"{end_label}*"
    range_label = f"{start_label} -> {end_label}"
    if start_truncated_to_scope or end_truncated_to_scope:
        range_label += " (scope-limited)"
    return range_label


def sign_for_longitude(lon: float) -> str:
    sign_index = int((lon % 360.0) // 30) % 12
    return ZODIAC_NAMES[sign_index]


def sign_degrees(sign: str, deg: int, minutes: int) -> float:
    sign_index = ZODIAC_NAMES.index(sign)
    return (sign_index * 30.0) + deg + (minutes / 60.0)


def get_nakshatra(lon: float) -> str:
    lon = lon % 360.0
    for name, start_sign, start_deg, start_min, end_sign, end_deg, end_min in NAKSHATRA_RANGES:
        start = sign_degrees(start_sign, start_deg, start_min)
        end = sign_degrees(end_sign, end_deg, end_min)
        if start <= end:
            if start <= lon < end:
                return name
        else:
            if lon >= start or lon < end:
                return name
    return "Unknown"


def format_hd_annotation(lon: float, active_channels: set[tuple[int, int]]) -> str:
    gate, line = get_line(lon)
    channels = get_channels_for_gate(gate, active_channels)
    channel_text = f" Ch:{','.join(channels)}" if channels else ""
    return f"G{gate}.L{line}{channel_text}"


def format_nakshatra_description_text(nakshatra: str) -> str:
    details = NAKSHATRA_DESCRIPTIONS.get(nakshatra)
    if not details:
        return f"{nakshatra}\n\nNo nakshatra description is available."

    field_labels = [
        ("symbol", "Symbol"),
        ("shakti", "Shakti"),
        ("essence", "Essence"),
        ("quality", "Quality"),
        ("favorable_activities", "Favorable Activities"),
        ("sidereal_sign", "Sidereal Sign"),
        ("archetypes", "Archetypes"),
        ("deity", "Deity"),
        ("ruler", "Ruler"),
        ("planetary_associations", "Body Associations"),
        ("comments_A", "Notes A"),
        ("comments_B", "Notes B"),
    ]

    title = details.get("name") or nakshatra
    lines = [title, ""]
    for key, label in field_labels:
        value = details.get(key)
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not value:
            continue
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def format_nakshatra_description_html(nakshatra: str) -> str:
    details = NAKSHATRA_DESCRIPTIONS.get(nakshatra)
    if not details:
        return (
            f"<div><strong>{html.escape(nakshatra)}</strong></div>"
            "<div style='margin-top: 8px;'>No nakshatra description is available.</div>"
        )

    raw_title = str(details.get("name") or nakshatra)
    title = html.escape(raw_title)
    title_color = NAKSHATRA_PLANET_COLOR.get(raw_title, (None, "#6fa8dc"))[1]

    def _header(label: str) -> str:
        return f"<span style='font-weight: bold; color: {CHART_DATA_HIGHLIGHT_COLOR};'>{label}</span>"

    def _value(key: str) -> str:
        raw = details.get(key)
        if isinstance(raw, str):
            return html.escape(raw.strip())
        return ""

    quality = _value("quality")
    quality_html = ""
    if quality:
        quality_name, sep, quality_desc = quality.partition(":")
        if sep:
            quality_html = f"<strong>{quality_name.strip()}:</strong> {quality_desc.strip()}"
        else:
            quality_html = quality

    body_assoc_value = _value("planetary_associations")
    sections: list[tuple[str, str]] = [
        ("Symbol:", _value("symbol")),
        ("Shakti:", _value("shakti")),
        ("Essence:", _value("essence")),
        ("Quality:", quality_html),
        ("Favorable Activities:", _value("favorable_activities")),
        ("Sidereal Sign:", _value("sidereal_sign")),
        ("Archetypes:", _value("archetypes")),
        ("Deity:", _value("deity")),
        ("Ruler:", _value("ruler")),
        ("Body Associations:", body_assoc_value),
    ]
    lines = [
        f"<div style='font-size: 14px; font-weight: bold; color: {title_color};'>{title}</div>",
        "<div style='margin-top: 8px;'>",
    ]
    for label, value in sections:
        if not value:
            continue
        lines.append(f"<div>{_header(label)} {value}</div>")
    lines.append("</div>")
    return "".join(lines)


def apply_nakshatra_tick_info_markers(ax: Any, nakshatras: list[str]) -> None:
    ax.set_xticks(range(len(nakshatras)), nakshatras)
    info_font_name = _nakshatra_info_marker_font_name()
    for label, nakshatra_name in zip(ax.get_xticklabels(), nakshatras, strict=True):
        if info_font_name:
            label.set_fontfamily(info_font_name)
        label.set_picker(True)
        label.set_gid(nakshatra_name)

@lru_cache(maxsize=1)
def _nakshatra_info_marker_font_name() -> str | None:
    for candidate in ("Arial Unicode MS", "Segoe UI Symbol", "Apple Symbols", "DejaVu Sans"):
        try:
            font_path = mpl_font_manager.findfont(candidate, fallback_to_default=False)
        except Exception:
            continue
        if font_path:
            return candidate
    return None
    
def format_percent(value: float, decimals: int = 0) -> str:
    return f"{value * 100:.{decimals}f}%"
