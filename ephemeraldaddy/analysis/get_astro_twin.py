from __future__ import annotations

from dataclasses import dataclass
import heapq
from math import sqrt
from typing import Iterable

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import NATAL_WEIGHT

SIMILAR_CHARTS_ALGORITHM_DEFAULT = "default"
SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE = "comprehensive"
SIMILAR_CHARTS_ALGORITHM_CUSTOM = "custom"
PLACEMENT_WEIGHTING_MODE_CHART_DEFINED = "chart_defined"
PLACEMENT_WEIGHTING_MODE_GENERIC = "generic"
PLACEMENT_WEIGHTING_MODE_HYBRID = "hybrid"
HYBRID_LUMINARY_BONUS_BY_SIGN_MATCHES: dict[int, float] = {
    0: 0.82,
    1: 0.92,
    2: 1.00,
}

SIMILARITY_COMPONENT_KEYS: tuple[str, ...] = (
    "placement",
    "aspect",
    "distribution",
    "combined_dominance",
    "nakshatra_placement",
    "nakshatra_dominance",
    "defined_centers",
    "human_design_gates",
)

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
    # Angles are retained here strictly for aspect endpoint weighting.
    "AS": 1.35,
    "DS": 1.0,
    "MC": 1.1,
    "IC": 1.0,
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

NATAL_ANGLES: frozenset[str] = frozenset({"AS", "IC", "MC", "DS"})

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
    dominance_score: float | None = None
    nakshatra_score: float | None = None
    hd_centers_score: float | None = None
    algorithm_mode: str = SIMILAR_CHARTS_ALGORITHM_DEFAULT


@dataclass(slots=True)
class SimilarityCalculatorSettings:
    use_placement: bool = True
    weight_placement: float = 0.33
    use_aspect: bool = True
    weight_aspect: float = 0.18
    use_distribution: bool = True
    weight_distribution: float = 0.03
    use_combined_dominance: bool = True
    weight_combined_dominance: float = 0.26
    use_nakshatra_placement: bool = True
    weight_nakshatra_placement: float = 0.12
    use_nakshatra_dominance: bool = False
    weight_nakshatra_dominance: float = 0.00
    use_defined_centers: bool = True
    weight_defined_centers: float = 0.08
    use_human_design_gates: bool = False
    weight_human_design_gates: float = 0.00
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED

    @classmethod
    def defaults_from_comprehensive(cls) -> "SimilarityCalculatorSettings":
        return cls()

    def weights_by_component(self) -> dict[str, float]:
        return {
            "placement": max(0.0, float(self.weight_placement)),
            "aspect": max(0.0, float(self.weight_aspect)),
            "distribution": max(0.0, float(self.weight_distribution)),
            "combined_dominance": max(0.0, float(self.weight_combined_dominance)),
            "nakshatra_placement": max(0.0, float(self.weight_nakshatra_placement)),
            "nakshatra_dominance": max(0.0, float(self.weight_nakshatra_dominance)),
            "defined_centers": max(0.0, float(self.weight_defined_centers)),
            "human_design_gates": max(0.0, float(self.weight_human_design_gates)),
        }

    def enabled_components(self) -> dict[str, bool]:
        return {
            "placement": bool(self.use_placement),
            "aspect": bool(self.use_aspect),
            "distribution": bool(self.use_distribution),
            "combined_dominance": bool(self.use_combined_dominance),
            "nakshatra_placement": bool(self.use_nakshatra_placement),
            "nakshatra_dominance": bool(self.use_nakshatra_dominance),
            "defined_centers": bool(self.use_defined_centers),
            "human_design_gates": bool(self.use_human_design_gates),
        }

    def normalized_placement_weighting_mode(self) -> str:
        return normalize_placement_weighting_mode(self.placement_weighting_mode)


def normalize_similar_charts_algorithm_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {
        SIMILAR_CHARTS_ALGORITHM_DEFAULT,
        SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE,
        SIMILAR_CHARTS_ALGORITHM_CUSTOM,
    }:
        return normalized
    return SIMILAR_CHARTS_ALGORITHM_DEFAULT


def normalize_placement_weighting_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {
        PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
        PLACEMENT_WEIGHTING_MODE_GENERIC,
        PLACEMENT_WEIGHTING_MODE_HYBRID,
    }:
        return normalized
    return PLACEMENT_WEIGHTING_MODE_CHART_DEFINED


def _safe_divide(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def _sign_index(lon: float | None) -> int | None:
    if lon is None:
        return None
    return int(float(lon) % 360.0 // 30)


def _nakshatra_index(lon: float | None) -> int | None:
    if lon is None:
        return None
    segment_size = 360.0 / 27.0
    return int((float(lon) % 360.0) // segment_size)


def _house_for_body(chart: Chart, body: str) -> int | None:
    uses_houses = (not bool(getattr(chart, "birthtime_unknown", False))) or bool(
        getattr(chart, "retcon_time_used", False)
    )
    if not uses_houses:
        return None
    houses = getattr(chart, "houses", None)
    positions = getattr(chart, "positions", None) or {}
    lon = positions.get(body)
    if not houses or lon is None:
        return None
    if len(houses) < 12:
        return None
    return Chart._house_index(float(lon), list(houses)) + 1


def _placement_body_weights(query: Chart, weighting_mode: str) -> dict[str, float]:
    normalized_mode = normalize_placement_weighting_mode(weighting_mode)
    generic_weights = {
        body: max(0.0, float(NATAL_WEIGHT.get(body, 1.0)))
        for body in CORE_BODIES
    }
    if normalized_mode == PLACEMENT_WEIGHTING_MODE_GENERIC:
        return generic_weights

    chart_weights = getattr(query, "dominant_planet_weights", None) or {}
    resolved = dict(generic_weights)

    for body in CORE_BODIES:
        chart_weight = chart_weights.get(body)
        if chart_weight is None:
            continue
        resolved[body] = max(0.0, float(chart_weight))

    if normalized_mode == PLACEMENT_WEIGHTING_MODE_CHART_DEFINED:
        return resolved

    if not chart_weights:
        return generic_weights

    ranked_bodies = [
        body
        for body, _ in sorted(
            (
                (body, max(0.0, float(weight)))
                for body, weight in chart_weights.items()
                if body in CORE_BODIES and weight is not None
            ),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    top_bodies = ranked_bodies[:3]
    top_set = set(top_bodies)
    bottom_bodies = [body for body in reversed(ranked_bodies) if body not in top_set][:3]

    hybrid_weights = dict(generic_weights)
    for body in top_bodies:
        hybrid_weights[body] = hybrid_weights.get(body, 1.0) * 1.25
    for body in bottom_bodies:
        hybrid_weights[body] = hybrid_weights.get(body, 1.0) * 0.75
    return hybrid_weights


def _placement_similarity(
    query: Chart,
    candidate: Chart,
    *,
    weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> float:
    q_positions = getattr(query, "positions", None) or {}
    c_positions = getattr(candidate, "positions", None) or {}
    body_weights = _placement_body_weights(query, weighting_mode)

    total = 0.0
    possible = 0.0
    use_houses = bool(getattr(query, "houses", None)) and bool(getattr(candidate, "houses", None))

    for body in CORE_BODIES:
        q_lon = q_positions.get(body)
        c_lon = c_positions.get(body)
        if q_lon is None or c_lon is None:
            continue

        body_weight = max(0.0, float(body_weights.get(body, NATAL_WEIGHT.get(body, 1.0))))

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

    similarity = _safe_divide(total, possible)
    normalized_mode = normalize_placement_weighting_mode(weighting_mode)
    if normalized_mode != PLACEMENT_WEIGHTING_MODE_HYBRID:
        return similarity

    # Hybrid mode intentionally blends chart-defined dominance with generic
    # body priorities. To keep "same core identity" charts from being buried
    # by high aspect overlap, we anchor placement similarity to luminary signs.
    luminary_sign_matches = 0
    for luminary in ("Sun", "Moon"):
        q_lon = q_positions.get(luminary)
        c_lon = c_positions.get(luminary)
        if q_lon is None or c_lon is None:
            continue
        if _sign_index(q_lon) == _sign_index(c_lon):
            luminary_sign_matches += 1
    luminary_multiplier = HYBRID_LUMINARY_BONUS_BY_SIGN_MATCHES.get(luminary_sign_matches, 1.0)
    return max(0.0, min(1.0, similarity * luminary_multiplier))


def _canonical_aspect_key(aspect: dict) -> tuple[tuple[str, str], str] | None:
    a = str(aspect.get("p1") or "").strip()
    b = str(aspect.get("p2") or "").strip()
    asp_type = str(aspect.get("type") or "").strip().lower()
    if not a or not b or not asp_type:
        return None
    left, right = sorted((a, b))
    return (left, right), asp_type


def _is_tautological_angle_aspect(body_a: str, body_b: str) -> bool:
    return body_a in NATAL_ANGLES and body_b in NATAL_ANGLES


def _aspect_map(chart: Chart) -> dict[tuple[tuple[str, str], str], list[float]]:
    aspect_map: dict[tuple[tuple[str, str], str], list[float]] = {}
    for aspect in getattr(chart, "aspects", None) or []:
        key = _canonical_aspect_key(aspect)
        if key is None:
            continue
        (a, b), _ = key
        if _is_tautological_angle_aspect(a, b):
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
    if not q_map and not c_map:
        return 0.5
    if not q_map or not c_map:
        return 0.0

    def _directional_overlap(
        source_map: dict[tuple[tuple[str, str], str], list[float]],
        target_map: dict[tuple[tuple[str, str], str], list[float]],
    ) -> float:
        total = 0.0
        possible = 0.0

        for key, source_orbs in source_map.items():
            (a, b), asp_type = key
            aspect_weight = ASPECT_WEIGHTS.get(asp_type, 0.3)
            body_weight = (BODY_WEIGHTS.get(a, 0.75) + BODY_WEIGHTS.get(b, 0.75)) / 2.0
            base_weight = aspect_weight * body_weight
            possible += base_weight

            target_orbs = target_map.get(key)
            if not target_orbs:
                continue

            best_match = 0.0
            for source_orb in source_orbs:
                for target_orb in target_orbs:
                    best_match = max(best_match, _orb_similarity(source_orb, target_orb))
            total += base_weight * best_match

        return _safe_divide(total, possible)

    # Symmetric overlap penalizes "extra-only" aspect sets and helps prevent
    # highly noisy charts from ranking as similar merely by containing a subset
    # of the query's aspects.
    source_recall = _directional_overlap(q_map, c_map)
    target_precision = _directional_overlap(c_map, q_map)
    return max(0.0, min(1.0, (source_recall + target_precision) / 2.0))


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


def _sign_weight_profile(chart: Chart) -> dict[int, float]:
    positions = getattr(chart, "positions", None) or {}
    weights = {index: 0.0 for index in range(12)}
    for body in CORE_BODIES:
        sign_idx = _sign_index(positions.get(body))
        if sign_idx is None:
            continue
        weights[sign_idx] += BODY_WEIGHTS.get(body, 0.8)
    return weights


def _body_dominance_profile(chart: Chart) -> dict[str, float]:
    dominant_weights = getattr(chart, "dominant_planet_weights", None) or {}
    if dominant_weights:
        resolved_profile: dict[str, float] = {}
        for body in CORE_BODIES:
            value = dominant_weights.get(body)
            if value is None:
                continue
            resolved_profile[body] = max(0.0, float(value))
        if resolved_profile:
            total = sum(resolved_profile.values())
            if total > 0.0:
                return {body: value / total for body, value in resolved_profile.items()}

    positions = getattr(chart, "positions", None) or {}
    profile: dict[str, float] = {}
    for body in CORE_BODIES:
        longitude = positions.get(body)
        if longitude is None:
            continue
        weight = BODY_WEIGHTS.get(body, 0.8)
        house = _house_for_body(chart, body)
        if house in {1, 4, 7, 10}:
            weight *= 1.30
        elif house in {2, 5, 8, 11}:
            weight *= 1.12
        profile[body] = weight
    return profile


def _house_weight_profile(chart: Chart) -> dict[int, float]:
    positions = getattr(chart, "positions", None) or {}
    profile = {house: 0.0 for house in range(1, 13)}
    for body in CORE_BODIES:
        longitude = positions.get(body)
        if longitude is None:
            continue
        house = _house_for_body(chart, body)
        if house is None:
            continue
        profile[house] += BODY_WEIGHTS.get(body, 0.8)
    return profile


def _weighted_overlap_similarity(values_a: dict[object, float], values_b: dict[object, float]) -> float:
    total_a = sum(max(0.0, float(value)) for value in values_a.values())
    total_b = sum(max(0.0, float(value)) for value in values_b.values())
    if total_a <= 0.0 or total_b <= 0.0:
        return 0.0
    keys = set(values_a) | set(values_b)
    overlap = sum(min(max(0.0, float(values_a.get(key, 0.0))), max(0.0, float(values_b.get(key, 0.0)))) for key in keys)
    return max(0.0, min(1.0, overlap / min(total_a, total_b)))


def _top_keys(weights: dict[object, float], count: int = 3) -> set[object]:
    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return {key for key, value in ranked[:count] if value > 0.0}


def _top_sign_indices(weights: dict[int, float], count: int = 2) -> set[int]:
    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return {idx for idx, weight in ranked[:count] if weight > 0.0}


def _sign_dominance_similarity(query: Chart, candidate: Chart) -> float:
    q_weights = _sign_weight_profile(query)
    c_weights = _sign_weight_profile(candidate)
    q_top2 = _top_sign_indices(q_weights, count=2)
    c_top2 = _top_sign_indices(c_weights, count=2)
    top2_overlap = len(q_top2 & c_top2) / 2.0
    overlap_similarity = _weighted_overlap_similarity(q_weights, c_weights)
    return max(0.0, min(1.0, (overlap_similarity * 0.72) + (top2_overlap * 0.28)))


def _dominance_similarity(query: Chart, candidate: Chart) -> float:
    q_sign = _sign_weight_profile(query)
    c_sign = _sign_weight_profile(candidate)
    q_house = _house_weight_profile(query)
    c_house = _house_weight_profile(candidate)
    q_body = _body_dominance_profile(query)
    c_body = _body_dominance_profile(candidate)

    sign_overlap = _weighted_overlap_similarity(q_sign, c_sign)
    house_overlap = _weighted_overlap_similarity(q_house, c_house)
    body_overlap = _weighted_overlap_similarity(q_body, c_body)

    sign_top3_overlap = len(_top_keys(q_sign, count=3) & _top_keys(c_sign, count=3)) / 3.0
    house_top3_overlap = len(_top_keys(q_house, count=3) & _top_keys(c_house, count=3)) / 3.0
    body_top3_overlap = len(_top_keys(q_body, count=3) & _top_keys(c_body, count=3)) / 3.0

    sign_component = (sign_overlap * 0.72) + (sign_top3_overlap * 0.28)
    house_component = (house_overlap * 0.68) + (house_top3_overlap * 0.32)
    body_component = (body_overlap * 0.66) + (body_top3_overlap * 0.34)
    house_component_enabled = (
        (not bool(getattr(query, "birthtime_unknown", False)) or bool(getattr(query, "retcon_time_used", False)))
        and (not bool(getattr(candidate, "birthtime_unknown", False)) or bool(getattr(candidate, "retcon_time_used", False)))
    )
    component_values = {
        "sign": sign_component,
        "body": body_component,
    }
    component_weights = {
        "sign": 0.40,
        "body": 0.30,
    }
    if house_component_enabled:
        component_values["house"] = house_component
        component_weights["house"] = 0.30
    total_weight = sum(component_weights.values()) or 1.0
    normalized_score = sum(
        component_values[key] * component_weights[key]
        for key in component_values
    ) / total_weight
    return max(0.0, min(1.0, normalized_score))


def _combined_dominance_similarity(query: Chart, candidate: Chart) -> float:
    return _dominance_similarity(query, candidate)


def _nakshatra_weight_profile(chart: Chart) -> dict[int, float]:
    positions = getattr(chart, "positions", None) or {}
    weighted_counts = {index: 0.0 for index in range(27)}
    for body in CORE_BODIES:
        if body in {"AS", "MC"}:
            continue
        nakshatra_idx = _nakshatra_index(positions.get(body))
        if nakshatra_idx is None:
            continue
        weighted_counts[nakshatra_idx] += BODY_WEIGHTS.get(body, 0.8)
    total = sum(weighted_counts.values())
    if total <= 0:
        return weighted_counts
    return {index: (value / total) for index, value in weighted_counts.items()}


def _nakshatra_similarity(query: Chart, candidate: Chart) -> float:
    q_profile = _nakshatra_weight_profile(query)
    c_profile = _nakshatra_weight_profile(candidate)
    overlap = sum(min(q_profile[index], c_profile[index]) for index in range(27))
    cosine = _cosine_similarity(
        {str(index): value for index, value in q_profile.items()},
        {str(index): value for index, value in c_profile.items()},
    )
    return max(0.0, min(1.0, (overlap * 0.65) + (cosine * 0.35)))


def _nakshatra_dominance_similarity(query: Chart, candidate: Chart) -> float:
    q_profile = _nakshatra_weight_profile(query)
    c_profile = _nakshatra_weight_profile(candidate)
    overlap = _weighted_overlap_similarity(q_profile, c_profile)
    q_top3 = _top_keys(q_profile, count=3)
    c_top3 = _top_keys(c_profile, count=3)
    top3_overlap = len(q_top3 & c_top3) / 3.0
    return max(0.0, min(1.0, (overlap * 0.75) + (top3_overlap * 0.25)))


def _human_design_gates(chart: Chart) -> set[int]:
    raw_gates = getattr(chart, "human_design_gates", None) or []
    resolved_gates: set[int] = set()
    for gate in raw_gates:
        try:
            resolved_gates.add(int(gate))
        except (TypeError, ValueError):
            continue
    return resolved_gates


def _human_design_gates_similarity(query: Chart, candidate: Chart) -> float:
    q_gates = _human_design_gates(query)
    c_gates = _human_design_gates(candidate)
    if not q_gates and not c_gates:
        return 0.5
    union = q_gates | c_gates
    if not union:
        return 0.0
    intersection = q_gates & c_gates
    return len(intersection) / len(union)


def _similarity_component_scores(
    query: Chart,
    candidate: Chart,
    *,
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> dict[str, float]:
    return {
        "placement": _placement_similarity(query, candidate, weighting_mode=placement_weighting_mode),
        "aspect": _aspect_similarity(query, candidate),
        "distribution": _distribution_similarity(query, candidate),
        "combined_dominance": _combined_dominance_similarity(query, candidate),
        "nakshatra_placement": _nakshatra_similarity(query, candidate),
        "nakshatra_dominance": _nakshatra_dominance_similarity(query, candidate),
        "defined_centers": _defined_centers_similarity(query, candidate),
        "human_design_gates": _human_design_gates_similarity(query, candidate),
    }


def _weighted_similarity_score(
    component_scores: dict[str, float],
    weights_by_component: dict[str, float],
    enabled_components: dict[str, bool] | None = None,
) -> float:
    total_weight = 0.0
    weighted_score = 0.0
    for key in SIMILARITY_COMPONENT_KEYS:
        if enabled_components is not None and not enabled_components.get(key, False):
            continue
        weight = max(0.0, float(weights_by_component.get(key, 0.0)))
        if weight <= 0.0:
            continue
        weighted_score += float(component_scores.get(key, 0.0)) * weight
        total_weight += weight
    if total_weight <= 0.0:
        return 0.0
    return weighted_score / total_weight


def _defined_centers(chart: Chart) -> set[str]:
    centers = getattr(chart, "human_design_defined_centers", None) or []
    return {
        str(center).strip().lower()
        for center in centers
        if str(center).strip()
    }


def _defined_centers_similarity(query: Chart, candidate: Chart) -> float:
    q_centers = _defined_centers(query)
    c_centers = _defined_centers(candidate)
    if not q_centers and not c_centers:
        return 0.5
    union = q_centers | c_centers
    if not union:
        return 0.0
    intersection = q_centers & c_centers
    return len(intersection) / len(union)


def chart_similarity_score(
    query: Chart,
    candidate: Chart,
    *,
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> tuple[float, float, float, float]:
    placement_score = _placement_similarity(
        query,
        candidate,
        weighting_mode=placement_weighting_mode,
    )
    aspect_score = _aspect_similarity(query, candidate)
    distribution_score = _distribution_similarity(query, candidate)
    dominance_score = _combined_dominance_similarity(query, candidate)
    final_score = (
        (placement_score * 0.38)
        + (aspect_score * 0.27)
        + (distribution_score * 0.10)
        + (dominance_score * 0.25)
    )
    return final_score, placement_score, aspect_score, distribution_score


def chart_similarity_score_comprehensive(
    query: Chart,
    candidate: Chart,
    *,
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> tuple[float, float, float, float, float, float]:
    component_scores = _similarity_component_scores(
        query,
        candidate,
        placement_weighting_mode=placement_weighting_mode,
    )
    weights = SimilarityCalculatorSettings.defaults_from_comprehensive().weights_by_component()
    comprehensive_score = _weighted_similarity_score(component_scores, weights)
    return (
        comprehensive_score,
        component_scores["placement"],
        component_scores["aspect"],
        component_scores["distribution"],
        component_scores["nakshatra_placement"],
        component_scores["defined_centers"],
    )


def chart_similarity_score_custom(
    query: Chart,
    candidate: Chart,
    settings: SimilarityCalculatorSettings,
) -> tuple[float, dict[str, float]]:
    component_scores = _similarity_component_scores(
        query,
        candidate,
        placement_weighting_mode=settings.normalized_placement_weighting_mode(),
    )
    final_score = _weighted_similarity_score(
        component_scores,
        settings.weights_by_component(),
        enabled_components=settings.enabled_components(),
    )
    return final_score, component_scores


def chart_dissimilarity_score(
    query: Chart,
    candidate: Chart,
    *,
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> tuple[float, float, float, float, float]:
    similarity_score, placement_score, aspect_score, distribution_score = chart_similarity_score(
        query,
        candidate,
        placement_weighting_mode=placement_weighting_mode,
    )
    # For "least similar", prioritize core placements and sign dominance heavily:
    # charts with the same dominant sign signatures should not surface as most dissimilar
    # even if they diverge on aspects.
    inverse_weighted = (
        ((1.0 - placement_score) * 0.33)
        + ((1.0 - aspect_score) * 0.20)
        + ((1.0 - distribution_score) * 0.10)
        + ((1.0 - _dominance_similarity(query, candidate)) * 0.37)
    )
    dominance_similarity = _sign_dominance_similarity(query, candidate)
    dominance_penalty = 0.40 * dominance_similarity
    dissimilarity_score = inverse_weighted * (1.0 - dominance_penalty)
    return dissimilarity_score, similarity_score, placement_score, aspect_score, distribution_score


def chart_dissimilarity_score_comprehensive(
    query: Chart,
    candidate: Chart,
    *,
    placement_weighting_mode: str = PLACEMENT_WEIGHTING_MODE_CHART_DEFINED,
) -> tuple[float, float, float, float, float, float, float]:
    (
        similarity_score,
        placement_score,
        aspect_score,
        distribution_score,
        nakshatra_score,
        hd_centers_score,
    ) = chart_similarity_score_comprehensive(
        query,
        candidate,
        placement_weighting_mode=placement_weighting_mode,
    )
    inverse_weighted = (
        ((1.0 - placement_score) * 0.26)
        + ((1.0 - aspect_score) * 0.17)
        + ((1.0 - distribution_score) * 0.08)
        + ((1.0 - _combined_dominance_similarity(query, candidate)) * 0.28)
        + ((1.0 - nakshatra_score) * 0.13)
        + ((1.0 - hd_centers_score) * 0.08)
    )
    dominance_similarity = _sign_dominance_similarity(query, candidate)
    dominance_penalty = 0.35 * dominance_similarity
    dissimilarity_score = inverse_weighted * (1.0 - dominance_penalty)
    return (
        dissimilarity_score,
        similarity_score,
        placement_score,
        aspect_score,
        distribution_score,
        nakshatra_score,
        hd_centers_score,
    )


def find_astro_twins(
    query_chart: Chart,
    candidates: Iterable[tuple[int, Chart]],
    *,
    top_k: int = 3,
    exclude_chart_id: int | None = None,
    least_similar: bool = False,
    algorithm_mode: str = SIMILAR_CHARTS_ALGORITHM_DEFAULT,
    custom_settings: SimilarityCalculatorSettings | None = None,
) -> list[AstroTwinMatch]:
    target_k = max(1, int(top_k))
    # Keep only k best candidates as we iterate so we avoid sorting all rows.
    scored_matches: list[tuple[float, int, AstroTwinMatch]] = []
    relaxed_scored_matches: list[tuple[float, int, AstroTwinMatch]] = []
    query_top3_signs = _top_sign_indices(_sign_weight_profile(query_chart), count=3) if least_similar else set()
    normalized_mode = normalize_similar_charts_algorithm_mode(algorithm_mode)
    use_comprehensive = normalized_mode == SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE
    use_custom = normalized_mode == SIMILAR_CHARTS_ALGORITHM_CUSTOM
    normalized_custom_settings = custom_settings or SimilarityCalculatorSettings.defaults_from_comprehensive()
    placement_weighting_mode = normalized_custom_settings.normalized_placement_weighting_mode()
    for chart_id, candidate in candidates:
        if exclude_chart_id is not None and chart_id == exclude_chart_id:
            continue
        if bool(getattr(candidate, "is_placeholder", False)):
            continue
        if not getattr(candidate, "positions", None):
            continue

        if least_similar:
            if use_custom:
                custom_similarity_score, component_scores = chart_similarity_score_custom(
                    query_chart,
                    candidate,
                    normalized_custom_settings,
                )
                rank_score = 1.0 - custom_similarity_score
                final_score = custom_similarity_score
                placement_score = component_scores["placement"]
                aspect_score = component_scores["aspect"]
                distribution_score = component_scores["distribution"]
                nakshatra_score = component_scores["nakshatra_placement"]
                hd_centers_score = component_scores["defined_centers"]
            elif use_comprehensive:
                (
                    rank_score,
                    final_score,
                    placement_score,
                    aspect_score,
                    distribution_score,
                    nakshatra_score,
                    hd_centers_score,
                ) = chart_dissimilarity_score_comprehensive(
                    query_chart,
                    candidate,
                    placement_weighting_mode=placement_weighting_mode,
                )
            else:
                rank_score, final_score, placement_score, aspect_score, distribution_score = chart_dissimilarity_score(
                    query_chart,
                    candidate,
                    placement_weighting_mode=placement_weighting_mode,
                )
                nakshatra_score = None
                hd_centers_score = None
        else:
            if use_custom:
                final_score, component_scores = chart_similarity_score_custom(
                    query_chart,
                    candidate,
                    normalized_custom_settings,
                )
                placement_score = component_scores["placement"]
                aspect_score = component_scores["aspect"]
                distribution_score = component_scores["distribution"]
                nakshatra_score = component_scores["nakshatra_placement"]
                hd_centers_score = component_scores["defined_centers"]
            elif use_comprehensive:
                (
                    final_score,
                    placement_score,
                    aspect_score,
                    distribution_score,
                    nakshatra_score,
                    hd_centers_score,
                ) = chart_similarity_score_comprehensive(
                    query_chart,
                    candidate,
                    placement_weighting_mode=placement_weighting_mode,
                )
            else:
                final_score, placement_score, aspect_score, distribution_score = chart_similarity_score(
                    query_chart,
                    candidate,
                    placement_weighting_mode=placement_weighting_mode,
                )
                nakshatra_score = None
                hd_centers_score = None
            rank_score = final_score

        dominance_score = _combined_dominance_similarity(query_chart, candidate)
        match = AstroTwinMatch(
            chart_id=int(chart_id),
            chart_name=str(getattr(candidate, "name", "") or "Unnamed"),
            score=final_score,
            placement_score=placement_score,
            aspect_score=aspect_score,
            distribution_score=distribution_score,
            dominance_score=dominance_score,
            nakshatra_score=nakshatra_score,
            hd_centers_score=hd_centers_score,
            algorithm_mode=normalized_mode,
        )
        destination_heap = scored_matches
        if least_similar and query_top3_signs:
            candidate_top3_signs = _top_sign_indices(_sign_weight_profile(candidate), count=3)
            top3_overlap = len(query_top3_signs & candidate_top3_signs)
            # Hard guardrail for least-similar mode:
            # if charts share any top-3 dominant sign, they should not rank as truly "least similar".
            if top3_overlap > 0:
                destination_heap = relaxed_scored_matches

        if len(destination_heap) < target_k:
            heapq.heappush(destination_heap, (rank_score, int(chart_id), match))
            continue
        if rank_score > destination_heap[0][0]:
            heapq.heapreplace(destination_heap, (rank_score, int(chart_id), match))

    if least_similar and len(scored_matches) < target_k:
        # Fallback behavior: if strict guardrails produce too few matches,
        # top off from the relaxed pool so UI still gets results.
        needed = target_k - len(scored_matches)
        scored_matches.extend(sorted(relaxed_scored_matches, key=lambda item: item[0], reverse=True)[:needed])

    ranked = sorted(scored_matches, key=lambda item: item[0], reverse=True)
    return [match for _, _, match in ranked]
