from __future__ import annotations

from collections import Counter
from itertools import combinations

from ephemeraldaddy.core.interpretations import ASPECT_PATTERN_DEFS, JONES_PLANETS, JONES_SHAPES

def _circular_gaps(sorted_lons: list[float]) -> list[float]:
    gaps: list[float] = []
    count = len(sorted_lons)
    for idx in range(count):
        a = sorted_lons[idx]
        b = sorted_lons[(idx + 1) % count]
        gaps.append((b - a) % 360.0)
    return gaps

def pattern_strength_from_orbs(edge_list, lookup):
    weights = []
    for edge in edge_list:
        aspect = lookup[sorted_pair(*edge)]["aspect"]
        orb = lookup[sorted_pair(*edge)]["orb"]
        max_orb = MAX_ORB_BY_ASPECT[aspect]
        weights.append(PATTERN_ASPECT_WEIGHTS[aspect] * orb_weight(orb, max_orb))
    return sum(weights) / len(weights)

def _occupied_span(sorted_lons: list[float]) -> float:
    if not sorted_lons:
        return 0.0
    return 360.0 - max(_circular_gaps(sorted_lons))

def classify_jones_shape(positions: dict[str, float]) -> tuple[str, dict[str, str]]:
    tracked = [(body, lon % 360.0) for body, lon in positions.items() if body in JONES_PLANETS]
    if len(tracked) < 3:
        return "unknown", {}
    tracked.sort(key=lambda item: item[1])
    sorted_lons = [lon for _, lon in tracked]
    gaps = _circular_gaps(sorted_lons)
    largest_gap = max(gaps)
    span = _occupied_span(sorted_lons)

    if span <= float(JONES_SHAPES["bundle"].get("occupied_span_max", 120)) + 8:
        return "bundle", {}
    if span <= float(JONES_SHAPES["bowl"].get("occupied_span_max", 180)) + 8:
        return "bowl", {}
    if largest_gap >= float(JONES_SHAPES["locomotive"].get("empty_span_min", 120)) - 8 and span <= 248:
        lead_index = gaps.index(largest_gap)
        trailer_boundary = tracked[lead_index]
        leader_boundary = tracked[(lead_index + 1) % len(tracked)]
        return "locomotive", {
            # We treat ascending zodiac longitude as the wheel's forward order.
            # With that choice, the leader is the first body encountered after
            # crossing the largest empty arc into the occupied arc.
            "leader": leader_boundary[0],
            "trailer": trailer_boundary[0],
            "leader_direction": "ascending_longitude",
            "largest_gap_degrees": f"{largest_gap:.2f}",
        }
    if max(int(g // 30.0) for g in gaps) <= int(JONES_SHAPES["splash"].get("max_consecutive_empty_houses", 2)):
        return "splash", {}
    return "splay", {}


def detect_aspect_patterns(aspects: list[dict]) -> list[str]:
    pair_types: dict[frozenset[str], str] = {}
    allowed_bodies = set(JONES_PLANETS)
    for aspect in aspects or []:
        p1 = str(aspect.get("p1", "")).strip()
        p2 = str(aspect.get("p2", "")).strip()
        typ = str(aspect.get("type", "")).strip().lower().replace(" ", "_")
        if (
            not p1
            or not p2
            or p1 == p2
            or p1 not in allowed_bodies
            or p2 not in allowed_bodies
        ):
            continue
        pair_types[frozenset((p1, p2))] = typ

    found: Counter[str] = Counter()
    bodies = sorted({body for pair in pair_types for body in pair})

    for trio in combinations(bodies, 3):
        t = sorted(
            pair_types.get(frozenset(edge), "")
            for edge in combinations(trio, 2)
        )
        if t == ["opposition", "square", "square"]:
            found["t_square"] += 1
        elif t == ["trine", "trine", "trine"]:
            found["grand_trine"] += 1
        elif t == ["quincunx", "quincunx", "sextile"]:
            found["yod"] += 1

    ordered = [key for key, _ in found.most_common() if key in ASPECT_PATTERN_DEFS]
    return ordered


def chart_type_summary(chart: object) -> dict[str, object]:
    positions = getattr(chart, "positions", {}) or {}
    aspects = getattr(chart, "aspects", []) or []
    shape, shape_meta = classify_jones_shape(positions)
    patterns = detect_aspect_patterns(aspects)
    return {"shape": shape, "shape_meta": shape_meta, "patterns": patterns}
