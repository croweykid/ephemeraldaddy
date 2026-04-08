"""Chart summary text builders extracted from gui.app."""

from __future__ import annotations

import datetime
import math
import unicodedata
from typing import Any

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASSES,
    DnDClassScorer,
    build_dnd_statblock_profile_lines,
    score_class_axes,
    score_dnd_statblock,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import assign_top_three_species_with_evidence
from ephemeraldaddy.core.aspects import ASPECT_DEFS
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.curse_scoring import AspectRecord, MOST_CURSED_SCORE, chart_cursedness
from ephemeraldaddy.core.ephemeris import (
    get_lilith_display_name,
    planetary_positions,
    planetary_retrogrades,
)
from ephemeraldaddy.core.interpretations import (
    ASPECT_BODY_ALIASES,
    ASPECT_SORT_OPTIONS,
    aspect_duration_score,
    aspect_pair_weight,
    aspect_score,
    PLANET_GLYPHS,
    PLANET_ORDER,
)
from ephemeraldaddy.gui.features.charts.aspect_sorting import sort_natal_aspects
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_planet_weights,
    chart_uses_houses,
    house_for_longitude,
)
from ephemeraldaddy.gui.features.charts.presentation import (
    format_degree_minutes,
    format_longitude,
    get_nakshatra,
    sign_for_longitude,
)
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER, format_chart_header


def _display_cell_width(text: str) -> int:
    """Approximate rendered width for mixed unicode text in monospaced columns."""
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def _pad_display_column(text: str, width: int) -> str:
    padding = max(width - _display_cell_width(text), 0)
    return f"{text}{' ' * padding}"


# _AXIS_LABEL_OVERRIDES: dict[str, str] = {
#     "mercy_restoration": "mercy & restoration",
#     "control_planning": "control & planning",
#     "stealth_indirection": "stealth",
# }


# def _format_axis_label(axis_name: str) -> str:
#     return _AXIS_LABEL_OVERRIDES.get(axis_name, axis_name.replace("_", " "))


# def _build_class_axis_weight_evidence(class_key: str) -> list[str]:
#     definition = DND_CLASSES.get(class_key)
#     if definition is None:
#         return []
#     return [
#         f"{_format_axis_label(axis_name)}: {(1.0 - weight) * 100:.0f}%"
#         for axis_name, weight in definition.axis_weights.items()
#     ]


def _format_time_variant_signs(chart: Chart) -> dict[str, dict[str, object]]:
    if not getattr(chart, "birthtime_unknown", False) or getattr(
        chart, "retcon_time_used", False
    ):
        return {}
    tzinfo = chart.dt.tzinfo
    if tzinfo is None:
        return {}
    base_date = chart.dt.date()
    midnight = datetime.datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        0,
        0,
        tzinfo=tzinfo,
    )
    pre_midnight = datetime.datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        23,
        59,
        tzinfo=tzinfo,
    )
    positions_midnight = planetary_positions(midnight, chart.lat, chart.lon)
    positions_pre_noon = planetary_positions(pre_midnight, chart.lat, chart.lon)
    ordered_names = [body for body in PLANET_ORDER if body in positions_midnight]
    extras = sorted(
        set(positions_midnight)
        .intersection(positions_pre_noon)
        .difference(ordered_names)
    )
    ordered_names.extend(extras)
    lines: dict[str, dict[str, object]] = {}
    for body in ordered_names:
        sign_midnight = sign_for_longitude(positions_midnight[body])
        sign_pre_noon = sign_for_longitude(positions_pre_noon[body])
        if sign_midnight != sign_pre_noon:
            dawn_lon = positions_midnight[body]
            dusk_lon = positions_pre_noon[body]
            dawn_pretty = format_longitude(dawn_lon)
            dusk_pretty = format_longitude(dusk_lon)
            dawn_nakshatra = get_nakshatra(dawn_lon)
            dusk_nakshatra = get_nakshatra(dusk_lon)
            text = (
                f"{_display_body_with_glyph(body):<11} 🌅{dawn_pretty} ({dawn_nakshatra})ⓘ -> "
                f"🌌{dusk_pretty} ({dusk_nakshatra})ⓘ"
            )
            lines[body] = {
                "text": text,
                "info": [
                    {
                        "body": body,
                        "sign": sign_midnight,
                        "house": None,
                        "icon_index": text.find("ⓘ"),
                    },
                    {
                        "body": body,
                        "sign": sign_pre_noon,
                        "house": None,
                        "icon_index": text.rfind("ⓘ"),
                    },
                ],
            }
    return lines



















def _aspect_label(atype: str) -> str:
    return atype.replace("_", " ").title()

def _aspect_body_with_sign(body: str, positions: dict[str, float]) -> str:
    display_body = _display_body_name(body)
    lon = positions.get(body)
    if lon is None:
        return display_body
    return f"{display_body} ({sign_for_longitude(lon)})"


def _display_body_with_glyph(body: str) -> str:
    display_body = _display_body_name(body)
    glyph = PLANET_GLYPHS.get(body) or PLANET_GLYPHS.get(display_body)
    if not glyph:
        return display_body
    # Angle "glyphs" are intentionally plain-text abbreviations (AS/MC/DS/IC).
    # Avoid rendering duplicates like "AS AS" in chart output.
    if str(glyph).strip().casefold() == str(display_body).strip().casefold():
        return display_body
    return f"{glyph} {display_body}"


def _display_body_name(body: str) -> str:
    if body == "Lilith (mean)":
        return "Black☽ Lilith"
    if body == "Lilith":
        display_name = get_lilith_display_name()
        if display_name == "Black Moon Lilith":
            return "Black☽ Lilith"
        return display_name
    if body == "Part of Fortune":
        return "Fortune"
    return body



def _format_popout_aspect_endpoint(body: Any, *, include_house: bool) -> str:
    display_name = _display_body_name(getattr(body, "name", ""))
    lon_deg = getattr(body, "lon_deg", None)
    sign = getattr(body, "sign", None)
    if sign is None and lon_deg is not None:
        sign = sign_for_longitude(float(lon_deg))
    if not sign:
        return display_name
    if include_house:
        house = getattr(body, "house", None)
        if house:
            return f"{display_name} ({sign} H{house})"
    return f"{display_name} ({sign})"


def _overlay_aspect_segments(aspect_hits: list[Any]) -> list[dict[str, float | str]]:
    segments: list[dict[str, float | str]] = []
    for hit in aspect_hits:
        lon1 = getattr(hit.a, "lon_deg", None)
        lon2 = getattr(hit.b, "lon_deg", None)
        if lon1 is None or lon2 is None:
            continue
        segments.append(
            {
                "lon1_deg": float(lon1),
                "lon2_deg": float(lon2),
                "type": str(hit.aspect),
                "score": float(getattr(hit, "exactness", 0.0)) * float(getattr(hit, "weight", 1.0)),
            }
        )
    return segments


def _normalize_aspect_body(body: str) -> str:
    return ASPECT_BODY_ALIASES.get(body, body)

def _aspect_pair_weight(p1: str, p2: str) -> float:
        return aspect_pair_weight(p1, p2)


def _aspect_score(asp: dict, planet_weights: dict[str, float] | None = None) -> float:
    return aspect_score(asp, planet_weights=planet_weights)


def _aspect_duration_score(asp: dict) -> float:
    return aspect_duration_score(asp)



def _normalize_planet_weight_map(weights: dict[str, float] | None) -> dict[str, float]:
    if not weights:
        return {}
    normalized: dict[str, float] = {}
    total = 0.0
    for body, raw_weight in weights.items():
        value = max(0.0, float(raw_weight))
        normalized[str(body)] = value
        total += value
    if total <= 0.0:
        return {}
    return {body: (value / total) for body, value in normalized.items()}


def _synastry_pair_weight(
    overlay_body: str,
    base_body: str,
    normalized_overlay_weights: dict[str, float],
    normalized_base_weights: dict[str, float],
) -> float:
    """Balanced pair score for synastry using geometric mean of normalized weights."""
    overlay_weight = float(normalized_overlay_weights.get(overlay_body, 0.0))
    base_weight = float(normalized_base_weights.get(base_body, 0.0))
    if overlay_weight <= 0.0 or base_weight <= 0.0:
        # fallback to static pair weight when normalized maps are unavailable/missing
        return _aspect_pair_weight(overlay_body, base_body)
    return math.sqrt(overlay_weight * base_weight)


def _is_structural_tautology(asp: dict) -> bool:
    aspect_label = _aspect_label(asp["type"])
    if aspect_label not in {"Opposition", "Square"}:
        return False
    pair = frozenset(
        {
            _normalize_aspect_body(asp["p1"]),
            _normalize_aspect_body(asp["p2"]),
        }
    )
    structural_pairs = {
        "Opposition": {
            frozenset({"AS", "DS"}),
            frozenset({"MC", "IC"}),
            frozenset({"Rahu", "Ketu"}),
        },
        "Square": {
            frozenset({"AS", "MC"}),
            frozenset({"AS", "IC"}),
            frozenset({"MC", "DS"}),
            frozenset({"DS", "IC"}),
        },
    }
    return pair in structural_pairs.get(aspect_label, set())


def format_chart_text(
    chart: Chart,
    aspect_sort: str = "Priority",
    *,
    show_cursedness: bool = True,
    show_dnd_output: bool = True,
) -> tuple[
    str,
    dict[int, list[dict[str, object]]],
    dict[int, dict[str, object]],
    dict[int, list[dict[str, object]]],
]:
    """Build a copy-pasteable text summary of positions, houses, and aspects."""
    lines: list[str] = []
    position_info_map: dict[int, list[dict[str, object]]] = {}
    aspect_info_map: dict[int, dict[str, object]] = {}
    species_info_map: dict[int, list[dict[str, object]]] = {}
    use_houses = chart_uses_houses(chart)
    angular_bodies = {"AS", "MC", "DS", "IC"}

    def _degree_in_sign_text(lon_value: float) -> str:
        lon_normalized = lon_value % 360.0
        degrees_in_sign = lon_normalized % 30.0
        deg = int(degrees_in_sign)
        minutes = int(round((degrees_in_sign - deg) * 60))
        if minutes == 60:
            deg += 1
            minutes = 0
            if deg == 30:
                deg = 0
        return f"{deg:02d}°{minutes:02d}'"

    def _format_species_variant(subtype: object) -> str:
        subtype_text = str(subtype or "").strip()
        if not subtype_text:
            return ""
        return f" ({subtype_text})"

    # Chart Info
    date_label = chart.dt.strftime("%m.%d.%Y") if chart.dt else "??.??.????"
    official_time_label = "unknown" if getattr(chart, "birthtime_unknown", False) else chart.dt.strftime("%H:%M")
    retcon_time_label = chart.dt.strftime("%H:%M") if getattr(chart, "retcon_time_used", False) else "unknown"
    birth_place = getattr(chart, "birth_place", None) or "Unknown"
    alias_text = getattr(chart, "alias", None) or "unknown"
    lines.append(format_chart_header("name_alias", name=chart.name, alias=alias_text))
    lines.append(
        format_chart_header(
            "date_times",
            date=date_label,
            official_time=official_time_label,
            retcon_time=retcon_time_label,
        )
    )
    lines.append(
        format_chart_header(
            "place",
            birth_place=birth_place,
            lat=chart.lat,
            lon=chart.lon,
        )
    )
    houses = getattr(chart, "houses", None) if use_houses else None
    aspects = getattr(chart, "aspects", None)
    filtered_aspects: list[dict] = []
    if aspects:
        filtered_aspects = [asp for asp in aspects if not _is_structural_tautology(asp)]
        if not use_houses:
            filtered_aspects = [
                asp
                for asp in filtered_aspects
                if asp["p1"] not in angular_bodies and asp["p2"] not in angular_bodies
            ]
    cursedness_line = ""
    if filtered_aspects and show_cursedness:
        positions = getattr(chart, "positions", {})
        curse_aspects: list[AspectRecord] = []
        for asp in filtered_aspects:
            lon_a = positions.get(asp["p1"])
            lon_b = positions.get(asp["p2"])
            if lon_a is None or lon_b is None:
                continue
            sign_a = sign_for_longitude(lon_a)
            sign_b = sign_for_longitude(lon_b)
            house_a = house_for_longitude(houses, lon_a) if use_houses else None
            house_b = house_for_longitude(houses, lon_b) if use_houses else None
            aspect_key = asp["type"].replace(" ", "_").lower()
            max_orb_deg = float(ASPECT_DEFS.get(aspect_key, {}).get("orb", 0.0))
            curse_aspects.append(
                AspectRecord(
                    aspect=aspect_key,
                    body_a=asp["p1"],
                    sign_a=sign_a,
                    house_a=house_a or 0,
                    body_b=asp["p2"],
                    sign_b=sign_b,
                    house_b=house_b or 0,
                    orb_deg=abs(float(asp.get("delta", 0.0))),
                    max_orb_deg=max_orb_deg,
                    applying=float(asp.get("delta", 0.0)) < 0,
                )
            )
        if curse_aspects:
            cursedness = chart_cursedness(curse_aspects)
            percent = min(100.0, (cursedness["total"] / MOST_CURSED_SCORE) * 100.0)
            cursedness_line = f"{percent:.1f}%"

    try:
        species_top_three = assign_top_three_species_with_evidence(chart)
    except Exception:
        species_top_three = []
    species_payloads: list[dict[str, object]] = []
    if species_top_three and show_dnd_output:
        for rank, (family, subtype, score, evidence) in enumerate(species_top_three):
            species_payloads.append(
                {
                    "line": f"{rank + 1}) {family}{_format_species_variant(subtype)} ⓘ",
                    "kind": "species",
                    "family": family,
                    "subtype": subtype,
                    "score": score,
                    "evidence": evidence,
                }
            )
    class_payloads: list[dict[str, object]] = []
    statblock_payload: dict[str, object] | None = None
    if show_dnd_output:
        try:
            axis_scores = score_class_axes(chart)
            class_scores = DnDClassScorer().score_classes(axis_scores)
            ranked_classes = sorted(
                class_scores.values(),
                key=lambda scored_class: scored_class.score,
                reverse=True,
            )
            statblock = score_dnd_statblock(chart, stat_floor=5, stat_ceiling=20)
            statblock_payload = {
                "line": "Statblock ⓘ",
                "kind": "statblock",
                "profile_lines": build_dnd_statblock_profile_lines(
                    statblock,
                    bar_width=18,
                    floor=5,
                    ceiling=20,
                ),
            }
        except Exception:
            ranked_classes = []
        for rank, scored_class in enumerate(ranked_classes[:3]):
            class_definition = DND_CLASSES.get(scored_class.key)
            class_display_name = (
                class_definition.display_name
                if class_definition is not None
                else scored_class.key.replace("_", " ").title()
            )
            class_payloads.append(
                {
                    "line": f"{rank + 1}) {class_display_name} ⓘ",
                    "kind": "class",
                    "name": class_display_name,
                    "class_key": scored_class.key,
                    "score": scored_class.score,
                    "axis_scores": {axis_key: float(value) for axis_key, value in axis_scores.items()},
                }
            )
    if getattr(chart, "used_utc_fallback", False):
        lines.append("NOTE: UTC fallback was used for timezone inference.")
        lines.append("")
        lines.append("")


    # Positions
    lines.append(CHART_DATA_DIVIDER)
    lines.append("POSITIONS")
    lines.append(CHART_DATA_DIVIDER)
    body_width = 10
    sign_width = 11
    degree_width = 12
    nakshatra_width = 22
    house_width = 5
    if use_houses:
        lines.append(
            "  ".join(
                [
                    _pad_display_column("Body", body_width),
                    _pad_display_column("Sign", sign_width),
                    _pad_display_column("Degree", degree_width),
                    _pad_display_column("Nakshatra", nakshatra_width),
                    _pad_display_column("House", house_width),
                ]
            )
        )
    else:
        lines.append(
            "  ".join(
                [
                    _pad_display_column("Body", body_width),
                    _pad_display_column("Sign", sign_width),
                    _pad_display_column("Degree", degree_width),
                    _pad_display_column("Nakshatra", nakshatra_width),
                ]
            )
        )
    lines.append("")

    #houses = getattr(chart, "houses", None) if use_houses else None
    time_variant_lines = _format_time_variant_signs(chart)
    required_chart_info_bodies = ["Chiron", "Ceres", "Pallas", "Juno", "Vesta"]
    missing_required = [
        body for body in required_chart_info_bodies if body not in chart.positions
    ]
    if missing_required:
        try:
            refreshed_positions = planetary_positions(chart.dt, chart.lat, chart.lon)
        except Exception:
            refreshed_positions = {}
        for body in missing_required:
            if body in refreshed_positions:
                chart.positions[body] = refreshed_positions[body]
    if not getattr(chart, "retrogrades", None):
        try:
            chart.retrogrades = planetary_retrogrades(chart.dt)
        except Exception:
            chart.retrogrades = {}
    retrogrades = dict(getattr(chart, "retrogrades", {}) or {})
    ordered_bodies = [
        body
        for body in PLANET_ORDER
        if body in chart.positions or body in required_chart_info_bodies
    ]
    extras = sorted(set(chart.positions).difference(ordered_bodies))
    ordered_bodies.extend(extras)
    for body in ordered_bodies:
        display_body = _display_body_with_glyph(body)
        lon = chart.positions.get(body)
        if lon is None:
            lines.append(f"{display_body:<9} Unknown")
            continue
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            lines.append(f"{display_body:<9} Unknown (birth time unknown)")
            continue
        if body in time_variant_lines:
            time_variant = time_variant_lines[body]
            position_info_map[len(lines)] = time_variant["info"]
            lines.append(time_variant["text"])
            continue
        pretty = format_longitude(lon)
        sign_label = sign_for_longitude(lon)
        degree_text = _degree_in_sign_text(lon)
        if retrogrades.get(body):
            pretty = f"{pretty} (Я)"
            degree_text = f"{degree_text} (Я)"
        nakshatra = get_nakshatra(lon)
        #nakshatra_with_info = f"{nakshatra} ⓘ"

        if use_houses:
            house_num = house_for_longitude(houses, lon)
            house_label = f"H{house_num}" if house_num is not None else "-"
            body_column = _pad_display_column(display_body, body_width)
            sign_column = _pad_display_column(sign_label, sign_width)
            degree_column = _pad_display_column(degree_text, degree_width)
            nakshatra_column = _pad_display_column(nakshatra, nakshatra_width)
            house_column = _pad_display_column(house_label, house_width)
            columns = [body_column, sign_column, degree_column, nakshatra_column, house_column]
            column_offsets: list[int] = []
            line_cursor = 0
            for index, column in enumerate(columns):
                column_offsets.append(line_cursor)
                line_cursor += len(column)
                if index < len(columns) - 1:
                    line_cursor += 2
            line = "  ".join(columns)
            entry_list = [
                {
                    "kind": "planet_keyword",
                    "body": body,
                    "column": 0,
                    "span_start": column_offsets[0],
                    "span_end": column_offsets[0] + len(display_body),
                },
                {
                    "kind": "sign_keyword",
                    "sign": sign_label,
                    "column": 1,
                    "span_start": column_offsets[1],
                    "span_end": column_offsets[1] + len(sign_label),
                },
                {
                    "kind": "nakshatra",
                    "nakshatra": nakshatra,
                    "column": 3,
                    "span_start": column_offsets[3],
                    "span_end": column_offsets[3] + len(nakshatra),
                }
            ]
            if house_num is not None:
                entry_list.append(
                    {
                        "kind": "house_keyword",
                        "house": house_num,
                        "column": 4,
                        "span_start": column_offsets[4],
                        "span_end": column_offsets[4] + len(house_label),
                    }
                )
                line = f"{line} ⓘ"
                entry_list.append(
                    {
                        "kind": "position",
                        "body": body,
                        "sign": sign_for_longitude(lon),
                        "house": house_num,
                        "column": 4,
                        "icon_index": line.rfind("ⓘ"),
                    }
                )
            position_info_map[len(lines)] = entry_list
            lines.append(line)
        else:
            body_column = _pad_display_column(display_body, body_width)
            sign_column = _pad_display_column(sign_label, sign_width)
            degree_column = _pad_display_column(degree_text, degree_width)
            nakshatra_column = _pad_display_column(nakshatra, nakshatra_width)
            columns = [body_column, sign_column, degree_column, nakshatra_column]
            column_offsets: list[int] = []
            line_cursor = 0
            for index, column in enumerate(columns):
                column_offsets.append(line_cursor)
                line_cursor += len(column)
                if index < len(columns) - 1:
                    line_cursor += 2
            line = "  ".join(columns)
            line = f"{line} ⓘ"
            position_info_map[len(lines)] = [
                {
                    "kind": "planet_keyword",
                    "body": body,
                    "column": 0,
                    "span_start": column_offsets[0],
                    "span_end": column_offsets[0] + len(display_body),
                },
                {
                    "kind": "sign_keyword",
                    "sign": sign_label,
                    "column": 1,
                    "span_start": column_offsets[1],
                    "span_end": column_offsets[1] + len(sign_label),
                },
                {
                    "kind": "nakshatra",
                    "nakshatra": nakshatra,
                    "column": 3,
                    "span_start": column_offsets[3],
                    "span_end": column_offsets[3] + len(nakshatra),
                },
                {
                    "kind": "position",
                    "body": body,
                    "sign": sign_for_longitude(lon),
                    "house": None,
                    "column": 3,
                    "icon_index": line.rfind("ⓘ"),
                }
            ]
            lines.append(line)
    lines.append("")

    # Houses: assume chart.houses is [1st, 2nd, ..., 12th] in order
    if use_houses and houses:
        lines.append(CHART_DATA_DIVIDER)
        lines.append("HOUSES")
        lines.append(CHART_DATA_DIVIDER)

        # Normalise to a list of length 12
        cusps = [None] * 12

        if isinstance(houses, (list, tuple)):
            for i, v in enumerate(houses[:12]):
                cusps[i] = v
        elif isinstance(houses, dict):
            # If someone ever switches to dict-style, map keys → indices
            for k, v in houses.items():
                idx = None
                if isinstance(k, int):
                    idx = k - 1
                else:
                    s = str(k).strip().lower()
                    if s.startswith("h"):
                        s = s[1:]
                    if s.startswith("house"):
                        s = s[5:]
                    s = s.strip()
                    if s.isdigit():
                        idx = int(s) - 1
                if idx is not None and 0 <= idx < 12:
                    cusps[idx] = v
        else:
            # fallback: just show whatever it is
            lines.append(str(houses))
            lines.append("")
            return "\n".join(lines), position_info_map, aspect_info_map, species_info_map

        for i, v in enumerate(cusps):
            if isinstance(v, (int, float)):
                lines.append(f"{i + 1:<2}: {sign_for_longitude(float(v)):<11} {_degree_in_sign_text(float(v))}")
            elif v is None:
                lines.append(f"{i + 1:<2}: -")
            else:
                lines.append(f"{i + 1:<2}: {v}")

        lines.append("")
    elif not use_houses:
        lines.append(CHART_DATA_DIVIDER)
        lines.append("HOUSES")
        lines.append(CHART_DATA_DIVIDER)
        lines.append("Unknown (birth time unknown)")
        lines.append("")

    # Aspects
    #aspects = getattr(chart, "aspects", None)
    #if aspects:
    if filtered_aspects:
        lines.append(CHART_DATA_DIVIDER)
        lines.append("ASPECTS")
        lines.append(CHART_DATA_DIVIDER)
        # aspects = [asp for asp in aspects if not _is_structural_tautology(asp)]
        # if not use_houses:
        #     aspects = [
        #         asp
        #         for asp in aspects
        #         if asp["p1"] not in angular_bodies and asp["p2"] not in angular_bodies
        #     ]
        sort_mode = aspect_sort if aspect_sort in ASPECT_SORT_OPTIONS else "Priority"
        dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not dominant_planet_weights:
            dominant_planet_weights = calculate_dominant_planet_weights(chart)
        sorted_aspects = sort_natal_aspects(
            filtered_aspects,
            sort_mode,
            planet_weights=dominant_planet_weights,
        )
        positions = getattr(chart, "positions", {})
        aspect_body_labels: dict[str, str] = {}
        for asp in sorted_aspects:
            for body in (asp["p1"], asp["p2"]):
                if body not in aspect_body_labels:
                    aspect_body_labels[body] = _aspect_body_with_sign(
                        body, positions
                    )
        label_width = max((len(label) for label in aspect_body_labels.values()), default=8)
        label_width = max(label_width, 8)
        for asp in sorted_aspects:
            p1 = asp["p1"]
            p2 = asp["p2"]
            atype = asp["type"]
            angle = asp["angle"]
            delta = asp["delta"]
            p1_label = aspect_body_labels.get(p1, p1)
            p2_label = aspect_body_labels.get(p2, p2)
            line = (
                f"{p1_label:<{label_width}} {atype:<12} {p2_label:<{label_width}} "
                f"{format_degree_minutes(angle, include_sign=False):>8}  (orb {format_degree_minutes(delta)})"
            )
            line = f"{line} ⓘ"
            aspect_info_map[len(lines)] = {
                "p1": p1,
                "p2": p2,
                "type": atype,
                "angle": angle,
                "delta": delta,
                "sign1": sign_for_longitude(positions[p1]) if p1 in positions else None,
                "sign2": sign_for_longitude(positions[p2]) if p2 in positions else None,
                "house1": house_for_longitude(houses, positions[p1]) if use_houses and houses and p1 in positions else None,
                "house2": house_for_longitude(houses, positions[p2]) if use_houses and houses and p2 in positions else None,
            }
            lines.append(line)

    if cursedness_line:
        lines.append("---------")
        lines.append("CURSEDNESS")
        lines.append("---------")
        lines.append(cursedness_line)
    if species_payloads or class_payloads or statblock_payload:
        lines.append("---------")
        lines.append("D&D-ification")
        lines.append("---------")
    if statblock_payload:
        stat_line_text = str(statblock_payload["line"])
        species_info_map[len(lines)] = [
            {
                "kind": statblock_payload.get("kind"),
                "profile_lines": statblock_payload.get("profile_lines", []),
                "icon_index": stat_line_text.find("ⓘ"),
            }
        ]
        lines.append(stat_line_text)
        for profile_line in statblock_payload.get("profile_lines", []):
            lines.append(f"  {profile_line}")
        if species_payloads or class_payloads:
            lines.append("")
    if species_payloads:
        lines.append("Top 3 Species")
        for payload in species_payloads:
            species_line_text = str(payload["line"])
            species_info_map[len(lines)] = [
                {
                    "kind": payload.get("kind"),
                    "family": payload["family"],
                    "subtype": payload["subtype"],
                    "score": payload["score"],
                    "evidence": payload["evidence"],
                    "icon_index": species_line_text.find("ⓘ"),
                }
            ]
            lines.append(species_line_text)
    if class_payloads:
        if species_payloads:
            lines.append("")
        lines.append("Top 3 Classes* (alpha phase prototype, not amazing yet)")
        for payload in class_payloads:
            class_line_text = str(payload["line"])
            species_info_map[len(lines)] = [
                {
                    "kind": payload.get("kind"),
                    "name": payload["name"],
                    "class_key": payload["class_key"],
                    "score": payload["score"],
                    "axis_scores": payload["axis_scores"],
                    "icon_index": class_line_text.find("ⓘ"),
                }
            ]
            lines.append(class_line_text)

    return "\n".join(lines), position_info_map, aspect_info_map, species_info_map



TRANSIT_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("Name:",),
    "alias": ("Alias:",),
    "date": ("Birth date:", "Date:"),
    "time": ("Birth time:", "Official Time:", "Time:"),
    "place": ("Birthplace:", "Place:", "Location:"),
}


def _starts_with_any_prefix(line: str, prefixes: tuple[str, ...]) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(prefix) for prefix in prefixes)


def _replace_first_matching_prefix(
    line: str,
    prefixes: tuple[str, ...],
    replacement: str,
) -> str:
    stripped = line.strip()
    for prefix in prefixes:
        if stripped.startswith(prefix):
            return line.replace(prefix, replacement, 1)
    return line


def format_transit_chart_text(chart: Chart, location_label: str) -> str:
    summary, _, _, _ = format_chart_text(chart)
    lines = summary.splitlines()
    positions_start_index = next(
        (idx for idx, line in enumerate(lines) if line.strip() == "POSITIONS"),
        0,
    )
    cleaned_lines: list[str] = []
    for line in lines[positions_start_index:]:
        if _starts_with_any_prefix(line, TRANSIT_HEADER_ALIASES["name"]) or _starts_with_any_prefix(
            line,
            TRANSIT_HEADER_ALIASES["alias"],
        ):
            continue
        if _starts_with_any_prefix(line, TRANSIT_HEADER_ALIASES["date"]):
            cleaned_lines.append(
                _replace_first_matching_prefix(
                    line,
                    TRANSIT_HEADER_ALIASES["date"],
                    "Date:",
                )
            )
            continue
        if _starts_with_any_prefix(line, TRANSIT_HEADER_ALIASES["time"]):
            cleaned_lines.append(
                _replace_first_matching_prefix(
                    line,
                    TRANSIT_HEADER_ALIASES["time"],
                    "Time:",
                )
            )
            continue
        if _starts_with_any_prefix(line, TRANSIT_HEADER_ALIASES["place"]):
            cleaned_lines.append(
                f"Location:   {location_label}, {chart.lat:.4f}, {chart.lon:.4f}"
            )
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)
