"""Chart metric and house-calculation helpers extracted from app."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import (
    ASPECT_SCORE_MULTIPLIERS,
    ASPECT_SCORE_WEIGHTS,
    DETRIMENT_WEIGHT,
    EXALTATION_WEIGHT,
    FALL_WEIGHT,
    HOUSE_WEIGHTS,
    MODES,
    NAKSHATRA_PLANET_COLOR,
    NAKSHATRA_RANGES,
    NATAL_WEIGHT,
    NATURAL_HOUSE_PLANETS,
    NATURAL_HOUSE_SIGNS,
    PLANET_DETRIMENT,
    PLANET_EXALTATION,
    PLANET_FALL,
    PLANET_ORDER,
    PLANET_RULERSHIP,
    RULERSHIP_WEIGHT,
    SIGN_GENDERS,
    SIGN_ELEMENTS,
    NATAL_BODY_LOUDNESS,
    ZODIAC_NAMES,
    aspect_orb_allowance,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra, sign_for_longitude

HOUSE_CUSP_BLEND_DEGREES = 8.0
DISPOSITOR_PLANET_ATTENUATION = 0.35
DISPOSITOR_SIGN_ATTENUATION = 0.30
DISPOSITOR_MAX_DEPTH = 2
CHART_RULER_BONUS = 4.0
TIGHT_ASPECT_ORB_DEGREES = 1.0
TIGHT_ASPECT_INTENSITY_MIN = 1.2
TIGHT_ASPECT_INTENSITY_MAX = 1.4

NATURAL_HOUSE_SIGN_BONUS = 6.0
NATURAL_HOUSE_PLANET_BONUS = 6.0

PLANET_DYNAMICS_METRICS = (
    "stability",
    "constructiveness",
    "volatility",
    "fragility",
    "adaptability",
)

_DYNAMICS_MIN = 0.0
_DYNAMICS_MAX = 10.0

_SECT_DIURNAL_BENEFICS = {"Sun", "Jupiter", "Saturn"}
_SECT_NOCTURNAL_BENEFICS = {"Moon", "Venus", "Mars"}


def _clamp_dynamics_score(value: float) -> float:
    return max(_DYNAMICS_MIN, min(_DYNAMICS_MAX, value))


def _round_dynamics_score(value: float) -> float:
    return round(_clamp_dynamics_score(float(value)), 1)


def _is_day_chart(chart: Chart) -> bool:
    houses = getattr(chart, "houses", None)
    if not houses or len(houses) < 12:
        return False
    sun_lon = chart.positions.get("Sun")
    if sun_lon is None:
        return False
    house_num = house_for_longitude(houses, sun_lon)
    return bool(house_num and 7 <= house_num <= 12)


def _planet_dignity_delta(body: str, sign: str) -> float:
    delta = 0.0
    if sign in PLANET_RULERSHIP.get(body, []):
        delta += 2.0
    exaltation = PLANET_EXALTATION.get(body)
    if exaltation and sign == exaltation.get("sign"):
        delta += 1.6
    if sign in PLANET_DETRIMENT.get(body, []):
        delta -= 2.0
    fall = PLANET_FALL.get(body)
    if fall and sign == fall.get("sign"):
        delta -= 1.6
    return delta


def calculate_planet_dynamics_scores(chart: Chart) -> dict[str, dict[str, float]]:
    """Derive per-planet dynamics metrics for Natal Chart View analytics.

    Scores are normalized to 0.0-10.0 and rounded to one decimal place.
    """
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    planet_keys = dominant_planet_keys(chart)
    day_chart = _is_day_chart(chart)

    dominant_weights = calculate_dominant_planet_weights(chart)
    max_dominant_weight = max(
        [value for value in dominant_weights.values() if isinstance(value, (int, float))],
        default=1.0,
    )
    if max_dominant_weight <= 0:
        max_dominant_weight = 1.0

    ruler_boosts: dict[str, float] = {planet: 0.0 for planet in planet_keys}
    if use_houses and houses:
        for cusp_lon in houses[:12]:
            sign = sign_for_longitude(cusp_lon)
            for ruler in _sign_rulers(sign):
                if ruler in ruler_boosts:
                    ruler_boosts[ruler] += 0.4

    thematic_repetition: dict[str, float] = {planet: 0.0 for planet in planet_keys}
    sign_to_bodies: dict[str, list[str]] = {}
    for body in planet_keys:
        lon = chart.positions.get(body)
        if lon is None:
            continue
        sign = sign_for_longitude(lon)
        sign_to_bodies.setdefault(sign, []).append(body)
    for sign_bodies in sign_to_bodies.values():
        if len(sign_bodies) < 2:
            continue
        repetition_gain = min(1.2, 0.4 * (len(sign_bodies) - 1))
        for body in sign_bodies:
            thematic_repetition[body] += repetition_gain

    aspect_effects: dict[str, dict[str, float]] = {
        body: {
            "support": 0.0,
            "stress": 0.0,
            "activation": 0.0,
        }
        for body in planet_keys
    }
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if p1 not in aspect_effects or p2 not in aspect_effects:
            continue
        orb_factor = _aspect_orb_factor(aspect)
        if orb_factor <= 0:
            continue
        aspect_type = str(aspect.get("type", "")).replace(" ", "_").lower()
        if aspect_type in {"trine", "sextile", "quintile", "biquintile"}:
            aspect_effects[p1]["support"] += orb_factor
            aspect_effects[p2]["support"] += orb_factor
        elif aspect_type in {"square", "opposition", "quincunx", "semisquare", "sesquiquadrate"}:
            aspect_effects[p1]["stress"] += orb_factor
            aspect_effects[p2]["stress"] += orb_factor
        elif aspect_type == "conjunction":
            aspect_effects[p1]["activation"] += orb_factor
            aspect_effects[p2]["activation"] += orb_factor
        else:
            aspect_effects[p1]["activation"] += orb_factor * 0.5
            aspect_effects[p2]["activation"] += orb_factor * 0.5

    dynamics: dict[str, dict[str, float]] = {}
    for body in planet_keys:
        lon = chart.positions.get(body)
        if lon is None:
            continue
        sign = sign_for_longitude(lon)
        house_num = house_for_longitude(houses, lon)

        dignity_delta = _planet_dignity_delta(body, sign)
        angularity = 0.0
        if house_num in {1, 4, 7, 10}:
            angularity = 1.2
        elif house_num in {2, 5, 8, 11}:
            angularity = 0.5

        sect_delta = 0.0
        if day_chart and body in _SECT_DIURNAL_BENEFICS:
            sect_delta = 0.6
        elif (not day_chart) and body in _SECT_NOCTURNAL_BENEFICS:
            sect_delta = 0.6
        elif body in _SECT_DIURNAL_BENEFICS | _SECT_NOCTURNAL_BENEFICS:
            sect_delta = -0.3

        dominant_norm = float(dominant_weights.get(body, 0.0)) / max_dominant_weight
        support = aspect_effects[body]["support"]
        stress = aspect_effects[body]["stress"]
        activation = aspect_effects[body]["activation"]
        rulership_power = ruler_boosts.get(body, 0.0)
        repetition = thematic_repetition.get(body, 0.0)
        dispositor_rulers = [r for r in _sign_rulers(sign) if r in planet_keys and r != body]
        dispositor_condition = 0.0
        if dispositor_rulers:
            dispositor_condition = sum(
                _planet_dignity_delta(ruler, sign_for_longitude(chart.positions[ruler]))
                for ruler in dispositor_rulers
                if ruler in chart.positions
            ) / len(dispositor_rulers)

        stability = 5.2 + (dignity_delta * 0.9) + (support * 0.7) + (sect_delta * 0.8) - (stress * 0.8) + (rulership_power * 0.4)
        constructiveness = 5.0 + (dignity_delta * 0.8) + (support * 0.8) + (dominant_norm * 1.2) + (rulership_power * 0.5) + (dispositor_condition * 0.5)
        volatility = 4.0 + (activation * 1.2) + (stress * 1.0) + (angularity * 0.6) - (dignity_delta * 0.6) - (support * 0.4)
        strain_sensitivity = 4.4 + (stress * 1.2) + (activation * 0.6) - (dignity_delta * 0.7) - (support * 0.5) - (sect_delta * 0.5)
        resourcefulness = 4.8 + (dominant_norm * 1.0) + (dispositor_condition * 0.6) + (rulership_power * 0.6) + (repetition * 0.5) + (support * 0.5) - (stress * 0.3)

        dynamics[body] = {
            "stability": _round_dynamics_score(stability),
            "constructiveness": _round_dynamics_score(constructiveness),
            "volatility": _round_dynamics_score(volatility),
            "fragility": _round_dynamics_score(strain_sensitivity),
            "adaptability": _round_dynamics_score(resourcefulness),
        }

    return dynamics


def house_membership_weights(
    cusps: list[float] | None,
    lon: float,
    blend_degrees: float = HOUSE_CUSP_BLEND_DEGREES,
) -> dict[int, float]:
    primary_house = house_for_longitude(cusps, lon)
    if primary_house is None:
        return {}

    if not cusps or blend_degrees <= 0:
        return {primary_house: 1.0}

    lon_norm = lon % 360.0
    index = primary_house - 1
    start = cusps[index] % 360.0
    end = cusps[(index + 1) % 12] % 360.0
    if end <= start:
        end += 360.0
    check_lon = lon_norm
    if check_lon < start:
        check_lon += 360.0

    dist_to_start = check_lon - start
    dist_to_end = end - check_lon

    weights = {primary_house: 1.0}
    prev_house = 12 if primary_house == 1 else primary_house - 1
    next_house = 1 if primary_house == 12 else primary_house + 1

    if dist_to_start < blend_degrees:
        share_prev = max(0.0, (blend_degrees - dist_to_start) / blend_degrees) * 0.5
        weights[primary_house] -= share_prev
        weights[prev_house] = weights.get(prev_house, 0.0) + share_prev

    if dist_to_end < blend_degrees:
        share_next = max(0.0, (blend_degrees - dist_to_end) / blend_degrees) * 0.5
        weights[primary_house] -= share_next
        weights[next_house] = weights.get(next_house, 0.0) + share_next

    total = sum(weights.values())
    if total <= 0:
        return {primary_house: 1.0}
    return {house: value / total for house, value in weights.items() if value > 0}


def _sign_rulers(sign: str) -> list[str]:
    return [planet for planet, signs in PLANET_RULERSHIP.items() if sign in signs]


def _aspect_orb_factor(aspect: dict) -> float:
    p1 = normalize_body_name(str(aspect.get("p1", "")))
    p2 = normalize_body_name(str(aspect.get("p2", "")))
    allowance = aspect_orb_allowance(str(aspect.get("type", "")), p1, p2)
    if allowance <= 0:
        return 0.0
    orb = abs(float(aspect.get("delta", 0.0)))
    ratio = orb / allowance
    return max(0.0, 1.0 - (ratio * ratio))


def _aspect_multiplier(aspect_type: str) -> float:
    normalized_type = str(aspect_type).replace(" ", "_").lower()
    return float(ASPECT_SCORE_MULTIPLIERS.get(normalized_type, 0.0))


def _tight_aspect_intensity_bonus(aspect: dict) -> float:
    orb = abs(float(aspect.get("delta", 0.0)))
    if orb >= TIGHT_ASPECT_ORB_DEGREES:
        return 1.0
    normalized = 1.0 - (orb / TIGHT_ASPECT_ORB_DEGREES)
    spread = TIGHT_ASPECT_INTENSITY_MAX - TIGHT_ASPECT_INTENSITY_MIN
    return TIGHT_ASPECT_INTENSITY_MIN + (normalized * spread)


# This is slightly overweighting outer planets:
# def _aspect_receiver_scale(body: str) -> float:
#     """Scale aspect gains to avoid inner-planet dominance drift.

#     Uses NATAL_BODY_LOUDNESS as a practical proxy for slower/heavier bodies carrying
#     more structural impact when tied into aspect networks.
#     """
#     base = float(NATAL_BODY_LOUDNESS.get(body, 5.0))
#     # Normalize around Mars-like baseline (~5) and keep bounded.
#     return max(0.6, min(2.0, base / 5.0))


def _dispositor_sign_transfers(chart: Chart, source_weight: float, sign: str) -> dict[str, float]:
    transfers = {name: 0.0 for name in ZODIAC_NAMES}
    current_sign = sign
    depth_weight = float(source_weight)
    for depth in range(1, DISPOSITOR_MAX_DEPTH + 1):
        rulers = [r for r in _sign_rulers(current_sign) if r in chart.positions]
        if not rulers:
            break
        attenuation = DISPOSITOR_SIGN_ATTENUATION / (depth * len(rulers))
        total_transfer = depth_weight * attenuation
        if total_transfer <= 0:
            break
        next_sign = sign_for_longitude(chart.positions[rulers[0]])
        for ruler in rulers:
            ruler_sign = sign_for_longitude(chart.positions[ruler])
            transfers[ruler_sign] += total_transfer
            next_sign = ruler_sign
        depth_weight = total_transfer
        current_sign = next_sign
    return transfers

def house_span_signs(cusps):
    """
    Given a 12-element list of house cusps in degrees (0–360),
    return a 12-element list, where each entry is the list of sign
    names that house spans in zodiacal order.
    """
    spans = []
    for i in range(12):
        start = cusps[i] % 360.0
        end = cusps[(i + 1) % 12] % 360.0

        # move forward in zodiac
        if end <= start:
            end += 360.0

        start_sign = int(start // 30) % 12
        end_sign = int(end // 30) % 12

        sign_indices = [start_sign]
        idx = start_sign
        # walk forward sign by sign until we reach end_sign
        while idx != end_sign:
            idx = (idx + 1) % 12
            sign_indices.append(idx)

        spans.append([ZODIAC_NAMES[j] for j in sign_indices])
    return spans

def house_for_longitude(
    cusps: list[float] | None,
    lon: float,
) -> int | None:
    if not cusps or len(cusps) < 12:
        return None
    lon = lon % 360.0
    for i in range(12):
        start = cusps[i] % 360.0
        end = cusps[(i + 1) % 12] % 360.0
        if end <= start:
            end += 360.0
        check_lon = lon
        if check_lon < start:
            check_lon += 360.0
        if start <= check_lon < end:
            return i + 1
    return None

def chart_uses_houses(chart: Chart) -> bool:
    return not getattr(chart, "birthtime_unknown", False) or getattr(
        chart,
        "retcon_time_used",
        False,
    )

def planet_sign_weight(
    body: str,
    lon: float,
    houses: list[float] | None,
    house_num: int | None,
) -> tuple[str, float]:
    sign = sign_for_longitude(lon)
    canonical_body = normalize_body_name(body)
    weight = float(NATAL_WEIGHT.get(canonical_body, 1))
    rulerships = PLANET_RULERSHIP.get(body)
    if rulerships and sign in rulerships:
        weight += RULERSHIP_WEIGHT

    exaltation = PLANET_EXALTATION.get(body)
    if exaltation and sign == exaltation["sign"]:
        weight += EXALTATION_WEIGHT

    detriments = PLANET_DETRIMENT.get(body)
    if detriments and sign in detriments:
        weight += DETRIMENT_WEIGHT

    fall = PLANET_FALL.get(body)
    if fall and sign == fall["sign"]:
        weight += FALL_WEIGHT

    if house_num:
        weight += HOUSE_WEIGHTS.get(house_num, 0.0)
    if house_num and NATURAL_HOUSE_SIGNS.get(house_num) == sign:
        weight += NATURAL_HOUSE_SIGN_BONUS

    return sign, weight

def planet_weight(
    body: str,
    lon: float,
    houses: list[float] | None,
    house_num: int | None,
) -> float:
    _sign, weight = planet_sign_weight(body, lon, houses, house_num)
    canonical_body = normalize_body_name(body)
    if house_num and NATURAL_HOUSE_PLANETS.get(house_num) == canonical_body:
        weight += NATURAL_HOUSE_PLANET_BONUS
    return weight


def _aspect_strength(aspect: dict) -> float:
    normalized_type = str(aspect.get("type", "")).replace(" ", "_").lower()
    aspect_weight = float(ASPECT_SCORE_WEIGHTS.get(normalized_type, 0.0))
    if aspect_weight <= 0:
        return 0.0
    orb_factor = _aspect_orb_factor(aspect)
    if orb_factor <= 0:
        return 0.0
    intensity_bonus = _tight_aspect_intensity_bonus(aspect)
    return aspect_weight * orb_factor * intensity_bonus

def dominant_planet_keys(chart: Chart) -> list[str]:
    planets = [body for body in PLANET_ORDER if normalize_body_name(body) in NATAL_WEIGHT]
    return [body for body in planets if body not in {"AS", "MC", "DS", "IC"}]


def _house_dominance_keys(chart: Chart) -> list[str]:
    keys = dominant_planet_keys(chart)
    if chart_uses_houses(chart):
        keys.extend(["AS", "IC", "DS", "MC"])
    return keys


def _chart_ruler_planets(chart: Chart) -> set[str]:
    houses = getattr(chart, "houses", None)
    if not houses or len(houses) < 1:
        return set()

    ascendant_sign = sign_for_longitude(houses[0])
    return {
        planet
        for planet, ruled_signs in PLANET_RULERSHIP.items()
        if ascendant_sign in ruled_signs
    }

def calculate_dominant_planet_weights(chart: Chart) -> dict[str, float]:
    use_houses = chart_uses_houses(chart)
    planets = dominant_planet_keys(chart)
    subtotal_weights = {body: 0.0 for body in planets}
    houses = getattr(chart, "houses", None) if use_houses else None
    for body in planets:
        if body not in chart.positions:
            continue
        lon = chart.positions[body]
        house_num = house_for_longitude(houses, lon)
        weight = float(planet_weight(body, lon, houses, house_num))
        subtotal_weights[body] += weight

    for chart_ruler in _chart_ruler_planets(chart):
        if chart_ruler in subtotal_weights:
            subtotal_weights[chart_ruler] += CHART_RULER_BONUS

    snapshot_weights = dict(subtotal_weights)
    dispositor_transfers = {body: 0.0 for body in subtotal_weights}
    for body, body_weight in snapshot_weights.items():
        if body not in chart.positions:
            continue
        sign = sign_for_longitude(chart.positions[body])
        rulers = [r for r in _sign_rulers(sign) if r in subtotal_weights]
        if not rulers:
            continue
        transfer = body_weight * (DISPOSITOR_PLANET_ATTENUATION / len(rulers))
        for ruler in rulers:
            dispositor_transfers[ruler] += transfer

    for body, transfer in dispositor_transfers.items():
        subtotal_weights[body] += transfer

    # Aspect interactions increase per-chart dominant planet weights here.
    final_weights = dict(subtotal_weights)
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if p1 not in subtotal_weights or p2 not in subtotal_weights:
            continue
        aspect_multiplier = _aspect_multiplier(str(aspect.get("type", "")))
        if aspect_multiplier <= 0:
            continue
        orb_factor = _aspect_orb_factor(aspect)
        if orb_factor <= 0:
            continue
        intensity_bonus = _tight_aspect_intensity_bonus(aspect)
        gain = (subtotal_weights[p1] + subtotal_weights[p2]) * aspect_multiplier * orb_factor * intensity_bonus
        final_weights[p1] += gain
        final_weights[p2] += gain

    return final_weights

def calculate_dominant_sign_weights(chart: Chart) -> dict[str, float]:
    weighted_counts = {sign: 0.0 for sign in ZODIAC_NAMES}
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        if body not in chart.positions:
            continue
        lon = chart.positions[body]
        sign = sign_for_longitude(lon)
        house_num = house_for_longitude(houses, lon)
        weighted_sign, weight = planet_sign_weight(body, lon, houses, house_num)
        weighted_counts[weighted_sign] += weight
        transfers = _dispositor_sign_transfers(chart, weight, weighted_sign)
        for sign_name, transfer in transfers.items():
            weighted_counts[sign_name] += transfer

    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if p1 not in chart.positions or p2 not in chart.positions:
            continue
        aspect_strength = _aspect_strength(aspect)
        if aspect_strength <= 0:
            continue
        sign_1 = sign_for_longitude(chart.positions[p1])
        sign_2 = sign_for_longitude(chart.positions[p2])
        weighted_counts[sign_1] += aspect_strength
        weighted_counts[sign_2] += aspect_strength
        if abs(float(aspect.get("delta", 0.0))) < TIGHT_ASPECT_ORB_DEGREES:
            weighted_counts[sign_1] += aspect_strength
            weighted_counts[sign_2] += aspect_strength

    sign_prevalence_counts = calculate_sign_prevalence_counts(chart)
    for sign, count in sign_prevalence_counts.items():
        if count >= 3:
            weighted_counts[sign] += float(count)

    return weighted_counts

def calculate_sign_prevalence_counts(chart: Chart) -> dict[str, int]:
    counts = {sign: 0 for sign in ZODIAC_NAMES}
    use_houses = chart_uses_houses(chart)
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None:
            continue
        sign = sign_for_longitude(lon)
        counts[sign] += 1
    return counts

def calculate_house_prevalence_counts(chart: Chart) -> dict[int, int]:
    house_counts = {house_num: 0 for house_num in range(1, 13)}
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    if not use_houses or not houses:
        return house_counts
    for body in PLANET_ORDER:
        if body not in chart.positions:
            continue
        lon = chart.positions[body]
        house_num = house_for_longitude(houses, lon)
        if house_num is not None:
            house_counts[house_num] += 1
    return house_counts


def calculate_dominant_house_weights(chart: Chart) -> dict[int, float]:
    house_counts = {house_num: 0.0 for house_num in range(1, 13)}
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    if not use_houses or not houses:
        return house_counts

    for body in _house_dominance_keys(chart):
        lon = chart.positions.get(body)
        if lon is None:
            continue
        house_weights = house_membership_weights(houses, lon)
        if not house_weights:
            continue
        primary_house = house_for_longitude(houses, lon)
        if primary_house is None:
            continue
        total_weight = float(planet_weight(body, lon, houses, primary_house))
        for house_num, share in house_weights.items():
            house_counts[house_num] += total_weight * share

    return house_counts

def calculate_mode_weights(chart: Chart) -> dict[str, int]:
    mode_counts = {"cardinal": 0, "mutable": 0, "fixed": 0}
    use_houses = chart_uses_houses(chart)
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None:
            continue
        sign = sign_for_longitude(lon)
        weight = NATAL_WEIGHT.get(body, 1)
        for mode, signs in MODES.items():
            if sign in signs:
                mode_counts[mode] += weight
                break
    return mode_counts

def calculate_element_prevalence_counts(chart: Chart) -> dict[str, int]:
    elements = ["Fire", "Earth", "Air", "Water"]
    element_counts = {element: 0 for element in elements}
    use_houses = chart_uses_houses(chart)
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None:
            continue
        sign = sign_for_longitude(lon)
        natural_element = SIGN_ELEMENTS.get(sign)
        if natural_element in element_counts:
            element_counts[natural_element] += 1
    return element_counts

def calculate_dominant_element_weights(chart: Chart) -> dict[str, float]:
    element_counts = {element: 0.0 for element in ("Fire", "Earth", "Air", "Water")}
    weighted_sign_counts = calculate_dominant_sign_weights(chart)
    for sign, weight in weighted_sign_counts.items():
        element = SIGN_ELEMENTS.get(sign)
        if element in element_counts:
            element_counts[element] += weight
    return element_counts

def calculate_nakshatra_prevalence_counts(chart: Chart) -> dict[str, int]:
    nakshatras = [name for name, *_ in NAKSHATRA_RANGES]
    counts = {name: 0 for name in nakshatras}
    use_houses = chart_uses_houses(chart)
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None:
            continue
        nakshatra = get_nakshatra(lon)
        if nakshatra in counts:
            counts[nakshatra] += NATAL_WEIGHT.get(body, 1)
    return counts


def calculate_dominant_nakshatra_weights(chart: Chart) -> dict[str, float]:
    nakshatras = [name for name, *_ in NAKSHATRA_RANGES]
    weighted_counts = {name: 0.0 for name in nakshatras}
    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    base_bodies = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
    bodies = list(base_bodies)
    if use_houses:
        bodies.extend(["AS", "IC", "DS", "MC"])

    for body in bodies:
        lon = chart.positions.get(body)
        if lon is None:
            continue
        house_num = house_for_longitude(houses, lon)
        weight = planet_weight(body, lon, houses, house_num)
        nakshatra = get_nakshatra(lon)
        if nakshatra in weighted_counts:
            weighted_counts[nakshatra] += weight

    allowed_bodies = set(bodies)
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if p1 not in allowed_bodies or p2 not in allowed_bodies:
            continue
        if p1 not in chart.positions or p2 not in chart.positions:
            continue
        aspect_strength = _aspect_strength(aspect)
        if aspect_strength <= 0:
            continue
        nakshatra_1 = get_nakshatra(chart.positions[p1])
        nakshatra_2 = get_nakshatra(chart.positions[p2])
        if nakshatra_1 in weighted_counts:
            weighted_counts[nakshatra_1] += aspect_strength
        if nakshatra_2 in weighted_counts:
            weighted_counts[nakshatra_2] += aspect_strength
        if abs(float(aspect.get("delta", 0.0))) < TIGHT_ASPECT_ORB_DEGREES:
            if nakshatra_1 in weighted_counts:
                weighted_counts[nakshatra_1] += aspect_strength
            if nakshatra_2 in weighted_counts:
                weighted_counts[nakshatra_2] += aspect_strength

    prevalence_counts = calculate_nakshatra_prevalence_counts(chart)
    for nakshatra, count in prevalence_counts.items():
        if count >= 3:
            weighted_counts[nakshatra] += float(count)

    return weighted_counts


def calculate_sidereal_planet_prevalence_counts(chart: Chart) -> dict[str, float]:
    """Return weighted body dominance grouped by each body's nakshatra ruler."""
    sidereal_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    counts = {planet: 0.0 for planet in sidereal_planets}
    use_houses = chart_uses_houses(chart)
    houses = chart.houses if use_houses else []
    for body in PLANET_ORDER:
        if not use_houses and body in {"AS", "MC", "DS", "IC"}:
            continue
        lon = chart.positions.get(body)
        if lon is None:
            continue
        house_num = house_for_longitude(houses, lon)
        weight = planet_weight(body, lon, houses, house_num)
        nakshatra = get_nakshatra(lon)
        planet_name, _color = NAKSHATRA_PLANET_COLOR.get(nakshatra, (None, None))
        if planet_name in counts:
            counts[planet_name] += float(weight)
    return counts

def calculate_modal_distribution_counts(chart: Chart) -> dict[str, int]:
    return calculate_mode_weights(chart)


def calculate_gender_prevalence_score(chart: Chart) -> float:
    sign_gender_scores = dict(SIGN_GENDERS)
    sign_counts = calculate_sign_prevalence_counts(chart)
    total_count = float(sum(sign_counts.values()))
    if total_count <= 0:
        return 5.0
    weighted_total = sum(
        float(sign_gender_scores.get(sign, 5.0)) * float(count)
        for sign, count in sign_counts.items()
    )
    return weighted_total / total_count


def calculate_gender_weight_score(chart: Chart) -> float:
    sign_gender_scores = dict(SIGN_GENDERS)
    weighted_sign_counts = calculate_dominant_sign_weights(chart)
    total_weight = float(sum(weighted_sign_counts.values()))
    if total_weight <= 0:
        return 5.0
    weighted_total = sum(
        float(sign_gender_scores.get(sign, 5.0)) * float(weight)
        for sign, weight in weighted_sign_counts.items()
    )
    return weighted_total / total_weight
