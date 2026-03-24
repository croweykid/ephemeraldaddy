from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from ephemeraldaddy.core.chart import Chart

CORE_BODIES: tuple[str, ...] = (
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

BODY_WEIGHTS: dict[str, float] = {
    "Sun": 1.25,
    "Moon": 1.25,
    "Mercury": 1.0,
    "Venus": 1.0,
    "Mars": 1.0,
    "Jupiter": 0.9,
    "Saturn": 1.0,
    "Uranus": 0.65,
    "Neptune": 0.65,
    "Pluto": 0.7,
    "AS": 1.35,
    "MC": 1.1,
}

ASPECT_WEIGHTS: dict[str, float] = {
    "conjunction": 1.0,
    "opposition": 0.9,
    "square": 0.9,
    "trine": 0.8,
    "sextile": 0.7,
    "quincunx": 0.55,
    "semisquare": 0.4,
    "sesquiquadrate": 0.45,
    "semisextile": 0.35,
    "quintile": 0.35,
    "biquintile": 0.35,
}

ELEMENT_BY_SIGN_INDEX = {
    0: "fire", 1: "earth", 2: "air", 3: "water",
    4: "fire", 5: "earth", 6: "air", 7: "water",
    8: "fire", 9: "earth", 10: "air", 11: "water",
}

MODE_BY_SIGN_INDEX = {
    0: "cardinal", 1: "fixed", 2: "mutable", 3: "cardinal",
    4: "fixed", 5: "mutable", 6: "cardinal", 7: "fixed",
    8: "mutable", 9: "cardinal", 10: "fixed", 11: "mutable",
}


@dataclass(slots=True)
class AstroTwinMatch:
    chart_id: int
    chart_name: str
    score: float
    placement_score: float
    aspect_score: float
    distribution_score: float


def _safe_divide(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def _sign_index(lon: float | None) -> int | None:
    if lon is None:
        return None
    return int(float(lon) % 360.0 // 30)


def _house_for_body(chart: Chart, body: str) -> int | None:
    houses = getattr(chart, "houses", None)
    positions = getattr(chart, "positions", None) or {}
    lon = positions.get(body)
    if not houses or lon is None:
        return None
    if len(houses) < 12:
        return None
    return Chart._house_index(float(lon), list(houses)) + 1


def _placement_similarity(query: Chart, candidate: Chart) -> float:
    q_positions = getattr(query, "positions", None) or {}
    c_positions = getattr(candidate, "positions", None) or {}

    total = 0.0
    possible = 0.0
    use_houses = bool(getattr(query, "houses", None)) and bool(getattr(candidate, "houses", None))

    for body in CORE_BODIES:
        q_lon = q_positions.get(body)
        c_lon = c_positions.get(body)
        if q_lon is None or c_lon is None:
            continue

        body_weight = BODY_WEIGHTS.get(body, 0.8)

        possible += body_weight
        if _sign_index(q_lon) == _sign_index(c_lon):
            total += body_weight

        if use_houses:
            q_house = _house_for_body(query, body)
            c_house = _house_for_body(candidate, body)
            house_weight = body_weight * 0.65
            possible += house_weight
            if q_house is not None and q_house == c_house:
                total += house_weight

    return _safe_divide(total, possible)


def _canonical_aspect_key(aspect: dict) -> tuple[tuple[str, str], str] | None:
    a = str(aspect.get("p1") or "").strip()
    b = str(aspect.get("p2") or "").strip()
    asp_type = str(aspect.get("type") or "").strip().lower()
    if not a or not b or not asp_type:
        return None
    left, right = sorted((a, b))
    return (left, right), asp_type


def _aspect_map(chart: Chart) -> dict[tuple[tuple[str, str], str], list[float]]:
    aspect_map: dict[tuple[tuple[str, str], str], list[float]] = {}
    for aspect in getattr(chart, "aspects", None) or []:
        key = _canonical_aspect_key(aspect)
        if key is None:
            continue
        orb = abs(float(aspect.get("delta", 0.0) or 0.0))
        aspect_map.setdefault(key, []).append(orb)
    return aspect_map


def _orb_similarity(orb_a: float, orb_b: float, max_orb_delta: float = 8.0) -> float:
    diff = abs(orb_a - orb_b)
    return max(0.0, 1.0 - (diff / max_orb_delta))


def _aspect_similarity(query: Chart, candidate: Chart) -> float:
    q_map = _aspect_map(query)
    c_map = _aspect_map(candidate)
    if not q_map:
        return 0.0

    total = 0.0
    possible = 0.0

    for key, q_orbs in q_map.items():
        (a, b), asp_type = key
        aspect_weight = ASPECT_WEIGHTS.get(asp_type, 0.3)
        body_weight = (BODY_WEIGHTS.get(a, 0.75) + BODY_WEIGHTS.get(b, 0.75)) / 2.0
        base_weight = aspect_weight * body_weight
        possible += base_weight

        candidate_orbs = c_map.get(key)
        if not candidate_orbs:
            continue

        best_match = 0.0
        for q_orb in q_orbs:
            for c_orb in candidate_orbs:
                best_match = max(best_match, _orb_similarity(q_orb, c_orb))
        total += base_weight * best_match

    return _safe_divide(total, possible)


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) | set(vec_b)
    dot = sum(float(vec_a.get(key, 0.0)) * float(vec_b.get(key, 0.0)) for key in keys)
    norm_a = sqrt(sum(float(vec_a.get(key, 0.0)) ** 2 for key in keys))
    norm_b = sqrt(sum(float(vec_b.get(key, 0.0)) ** 2 for key in keys))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _distribution_vectors(chart: Chart) -> tuple[dict[str, float], dict[str, float]]:
    positions = getattr(chart, "positions", None) or {}
    element_counts = {"fire": 0.0, "earth": 0.0, "air": 0.0, "water": 0.0}
    mode_counts = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
    for body in CORE_BODIES:
        if body in {"AS", "MC"}:
            continue
        sign_idx = _sign_index(positions.get(body))
        if sign_idx is None:
            continue
        element_counts[ELEMENT_BY_SIGN_INDEX[sign_idx]] += 1.0
        mode_counts[MODE_BY_SIGN_INDEX[sign_idx]] += 1.0

    element_total = max(1.0, sum(element_counts.values()))
    mode_total = max(1.0, sum(mode_counts.values()))
    return (
        {k: v / element_total for k, v in element_counts.items()},
        {k: v / mode_total for k, v in mode_counts.items()},
    )


def _distribution_similarity(query: Chart, candidate: Chart) -> float:
    q_elements, q_modes = _distribution_vectors(query)
    c_elements, c_modes = _distribution_vectors(candidate)
    element_similarity = _cosine_similarity(q_elements, c_elements)
    mode_similarity = _cosine_similarity(q_modes, c_modes)
    return (element_similarity * 0.55) + (mode_similarity * 0.45)


def chart_similarity_score(query: Chart, candidate: Chart) -> tuple[float, float, float, float]:
    placement_score = _placement_similarity(query, candidate)
    aspect_score = _aspect_similarity(query, candidate)
    distribution_score = _distribution_similarity(query, candidate)
    final_score = (
        (placement_score * 0.46)
        + (aspect_score * 0.39)
        + (distribution_score * 0.15)
    )
    return final_score, placement_score, aspect_score, distribution_score


def find_astro_twins(
    query_chart: Chart,
    candidates: Iterable[tuple[int, Chart]],
    *,
    top_k: int = 3,
    exclude_chart_id: int | None = None,
    least_similar: bool = False,
) -> list[AstroTwinMatch]:
    results: list[AstroTwinMatch] = []
    for chart_id, candidate in candidates:
        if exclude_chart_id is not None and chart_id == exclude_chart_id:
            continue
        if bool(getattr(candidate, "is_placeholder", False)):
            continue
        if not getattr(candidate, "positions", None):
            continue

        final_score, placement_score, aspect_score, distribution_score = chart_similarity_score(
            query_chart,
            candidate,
        )
        results.append(
            AstroTwinMatch(
                chart_id=int(chart_id),
                chart_name=str(getattr(candidate, "name", "") or "Unnamed"),
                score=final_score,
                placement_score=placement_score,
                aspect_score=aspect_score,
                distribution_score=distribution_score,
            )
        )

    results.sort(key=lambda item: item.score, reverse=not least_similar)
    return results[:max(1, int(top_k))]
