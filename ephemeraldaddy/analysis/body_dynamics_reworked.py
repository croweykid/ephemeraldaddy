from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.interpretations import (
    ASPECT_FRICTION,
    ASPECT_SCORE_WEIGHTS,
    CHART_RULER_BONUS,
    DETRIMENT_WEIGHT,
    DISPOSITOR_PLANET_ATTENUATION,
    EXALTATION_WEIGHT,
    FALL_WEIGHT,
    HOUSE_WEIGHTS,
    NATAL_WEIGHT,
    NATURAL_HOUSE_PLANET_BONUS,
    NATURAL_HOUSE_PLANETS,
    NATURAL_HOUSE_SIGN_BONUS,
    NATURAL_HOUSE_SIGNS,
    PLANET_DETRIMENT,
    PLANET_EXALTATION,
    PLANET_FALL,
    JONES_PLANETS,
    PLANET_ORDER,
    PLANET_RULERSHIP,
    RULERSHIP_WEIGHT,
    ZODIAC_NAMES,
    aspect_orb_allowance,
    normalize_body_name,
)

BODY_INDEX = {body: i for i, body in enumerate(JONES_PLANETS)}

def normalize_body_pair(a: str, b: str) -> tuple[str, str]:
    """
    Canonicalize pair order for tuple-key lookup.
    """
    return tuple(sorted((a, b), key=BODY_INDEX.__getitem__))

# Pair-tone prior:
# - enabling_pair: conjunction / semisextile are treated as enabling
# - antagonizing_pair: conjunction / semisextile are treated as antagonizing
# - volatile_pair: conjunction / semisextile remain escalating
#
# This is an opinionated prior, not sacred scripture. It is meant to drive scoring.
BODY_PAIR_DYNAMICS = {
    # Sun
    ("Sun", "Moon"): "enabling_pair",
    ("Sun", "Mercury"): "enabling_pair",
    ("Sun", "Venus"): "enabling_pair",
    ("Sun", "Mars"): "volatile_pair",
    ("Sun", "Jupiter"): "enabling_pair",
    ("Sun", "Saturn"): "antagonizing_pair",
    ("Sun", "Uranus"): "volatile_pair",
    ("Sun", "Neptune"): "volatile_pair",
    ("Sun", "Pluto"): "volatile_pair",

    # Moon
    ("Moon", "Mercury"): "enabling_pair",
    ("Moon", "Venus"): "enabling_pair",
    ("Moon", "Mars"): "antagonizing_pair",
    ("Moon", "Jupiter"): "enabling_pair",
    ("Moon", "Saturn"): "antagonizing_pair",
    ("Moon", "Uranus"): "antagonizing_pair",
    ("Moon", "Neptune"): "volatile_pair",
    ("Moon", "Pluto"): "antagonizing_pair",

    # Mercury
    ("Mercury", "Venus"): "enabling_pair",
    ("Mercury", "Mars"): "antagonizing_pair",
    ("Mercury", "Jupiter"): "enabling_pair",
    ("Mercury", "Saturn"): "volatile_pair",
    ("Mercury", "Uranus"): "enabling_pair",
    ("Mercury", "Neptune"): "volatile_pair",
    ("Mercury", "Pluto"): "volatile_pair",

    # Venus
    ("Venus", "Mars"): "volatile_pair",
    ("Venus", "Jupiter"): "enabling_pair",
    ("Venus", "Saturn"): "antagonizing_pair",
    ("Venus", "Uranus"): "antagonizing_pair",
    ("Venus", "Neptune"): "volatile_pair",
    ("Venus", "Pluto"): "antagonizing_pair", #maybe volatile.

    # Mars
    ("Mars", "Jupiter"): "enabling_pair",
    ("Mars", "Saturn"): "antagonizing_pair",
    ("Mars", "Uranus"): "antagonizing_pair",
    ("Mars", "Neptune"): "antagonizing_pair",
    ("Mars", "Pluto"): "volatile_pair",

    # Jupiter
    ("Jupiter", "Saturn"): "volatile_pair",
    ("Jupiter", "Uranus"): "enabling_pair",
    ("Jupiter", "Neptune"): "volatile_pair",
    ("Jupiter", "Pluto"): "volatile_pair",

    # Saturn
    ("Saturn", "Uranus"): "antagonizing_pair",
    ("Saturn", "Neptune"): "antagonizing_pair",
    ("Saturn", "Pluto"): "antagonizing_pair",

    # Uranus
    ("Uranus", "Neptune"): "volatile_pair",
    ("Uranus", "Pluto"): "volatile_pair",

    # Neptune
    ("Neptune", "Pluto"): "volatile_pair",
}


EXPECTED_UNORDERED_PAIR_COUNT = len(JONES_PLANETS) * (len(JONES_PLANETS) - 1) // 2
assert len(BODY_PAIR_DYNAMICS) == EXPECTED_UNORDERED_PAIR_COUNT == 45

PAIR_TONE_DISTRIBUTION = {
    "enabling_pair": {
        "enabling_aspect":     {"Enabling": 0.85, "Antagonizing": 0.00, "Escalating": 0.15},
        "antagonizing_aspect": {"Enabling": 0.10, "Antagonizing": 0.65, "Escalating": 0.25},
        "escalating_aspect":   {"Enabling": 0.60, "Antagonizing": 0.00, "Escalating": 0.40},
    },
    "antagonizing_pair": {
        "enabling_aspect":     {"Enabling": 0.55, "Antagonizing": 0.20, "Escalating": 0.25},
        "antagonizing_aspect": {"Enabling": 0.00, "Antagonizing": 0.80, "Escalating": 0.20},
        "escalating_aspect":   {"Enabling": 0.10, "Antagonizing": 0.45, "Escalating": 0.45},
    },
    "volatile_pair": {
        "enabling_aspect":     {"Enabling": 0.65, "Antagonizing": 0.00, "Escalating": 0.35},
        "antagonizing_aspect": {"Enabling": 0.00, "Antagonizing": 0.55, "Escalating": 0.45},
        "escalating_aspect":   {"Enabling": 0.25, "Antagonizing": 0.25, "Escalating": 0.50},
    },
}
ASPECT_BUCKET_KEYS = {
    "harmonious": "enabling_aspect",
    "conflicted": "antagonizing_aspect",
    "neutral/variable": "escalating_aspect",
}


PAIR_TYPE_DISTRIBUTION = {
    pair: {
        aspect_name: PAIR_TONE_DISTRIBUTION[tone][ASPECT_BUCKET_KEYS[bucket_name]]
        for bucket_name, bucket_data in ASPECT_FRICTION.items()
        for aspect_name in bucket_data.get("aspects", frozenset())
    }
    for pair, tone in BODY_PAIR_DYNAMICS.items()
}

#to add:
#the scoring gist is something like: aspect_score = pair_polarity_sign * orb_weight * aspect_base_weight * sqrt(dom_a * dom_b)


def sign_for_longitude(lon: float) -> str:
    sign_index = int((lon % 360.0) // 30) % 12
    return ZODIAC_NAMES[sign_index]


def house_for_longitude(cusps: list[float] | None, lon: float) -> int | None:
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


def _sign_rulers(sign: str) -> list[str]:
    return [planet for planet, signs in PLANET_RULERSHIP.items() if sign in signs]


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


def _chart_ruler_planets(chart) -> set[str]:
    houses = getattr(chart, "houses", None)
    if not houses or len(houses) < 1:
        return set()
    ascendant_sign = sign_for_longitude(houses[0])
    return {
        planet
        for planet, ruled_signs in PLANET_RULERSHIP.items()
        if ascendant_sign in ruled_signs
    }


def calculate_planet_condition_weights(chart) -> dict[str, float]:
    """Body condition weights used by Body Dynamics multipliers."""
    use_houses = chart_uses_houses(chart)
    planets = [body for body in PLANET_ORDER if normalize_body_name(body) in NATAL_WEIGHT]
    condition_weights = {body: 0.0 for body in planets}
    houses = getattr(chart, "houses", None) if use_houses else None
    positions = getattr(chart, "positions", {}) or {}
    for body in planets:
        if body not in positions:
            continue
        lon = positions[body]
        house_num = house_for_longitude(houses, lon)
        condition_weights[body] += float(planet_weight(body, lon, houses, house_num))

    if use_houses:
        for chart_ruler in _chart_ruler_planets(chart):
            if chart_ruler in condition_weights:
                condition_weights[chart_ruler] += CHART_RULER_BONUS

        snapshot_weights = dict(condition_weights)
        dispositor_transfers = {body: 0.0 for body in condition_weights}
        for body, body_weight in snapshot_weights.items():
            if body not in positions:
                continue
            sign = sign_for_longitude(positions[body])
            rulers = [r for r in _sign_rulers(sign) if r in condition_weights]
            if not rulers:
                continue
            transfer = body_weight * (DISPOSITOR_PLANET_ATTENUATION / len(rulers))
            for ruler in rulers:
                dispositor_transfers[ruler] += transfer

        for body, transfer in dispositor_transfers.items():
            condition_weights[body] += transfer

    return condition_weights


def _aspect_orb_factor(aspect: dict) -> float:
    p1 = normalize_body_name(str(aspect.get("p1", "")))
    p2 = normalize_body_name(str(aspect.get("p2", "")))
    allowance = aspect_orb_allowance(str(aspect.get("type", "")), p1, p2)
    if allowance <= 0:
        return 0.0
    orb = abs(float(aspect.get("delta", 0.0)))
    ratio = orb / allowance
    return max(0.0, 1.0 - (ratio * ratio))


def calculate_planet_dynamics_scores(chart) -> dict[str, dict[str, float]]:
    """Compute per-JONES-body dynamics scores from aspect type + pair tone."""
    positions = getattr(chart, "positions", {}) or {}
    tracked_bodies = tuple(body for body in JONES_PLANETS if body in positions)
    dynamics: dict[str, dict[str, float]] = {
        body: {"antagonizing": 0.0, "enabling": 0.0, "escalating": 0.0}
        for body in tracked_bodies
    }

    condition_weights = calculate_planet_condition_weights(chart)
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if p1 not in dynamics or p2 not in dynamics:
            continue
        aspect_type = str(aspect.get("type", "")).replace(" ", "_").lower()
        pair = normalize_body_pair(p1, p2)
        pair_tone = BODY_PAIR_DYNAMICS.get(pair)
        distribution = (PAIR_TYPE_DISTRIBUTION.get(pair) or {}).get(aspect_type)
        if not distribution:
            continue
        orb_weight = _aspect_orb_factor(aspect)
        aspect_base_weight = float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0))
        if orb_weight <= 0.0 or aspect_base_weight <= 0.0:
            continue
        dom_a = max(float(condition_weights.get(p1, 0.0)), 0.0)
        dom_b = max(float(condition_weights.get(p2, 0.0)), 0.0)
        aspect_score = orb_weight * aspect_base_weight * ((dom_a * dom_b) ** 0.5)
        for metric, weight in (
            ("enabling", float(distribution.get("Enabling", 0.0))),
            ("antagonizing", float(distribution.get("Antagonizing", 0.0))),
            ("escalating", float(distribution.get("Escalating", 0.0))),
        ):
            weighted_score = aspect_score * weight
            if metric == "escalating" and pair_tone == "volatile_pair":
                weighted_score *= 1.15
            if weighted_score > 0.0:
                dynamics[p1][metric] += weighted_score
                dynamics[p2][metric] += weighted_score

    chart.planet_dynamics_scores = dynamics
    return dynamics
