import math

PLANET_AGES = {
    "Moon": 1, #very early life
    "Mercury": 7, #childhood/adolescence
    "Venus": 13, #teens, early adult bonding/socializing
    "Sun": 18, #identity consolidation / early adulthood
    "Mars": 13, #young adulthood / assertion era
    "Jupiter": 40, #expansion/expanded adulthood
    "Saturn": 56, #later maturity/full accountability
    "Uranus": 65, #transpersonal eras, late life, generational
    "Neptune": 72, #transpersonal eras, late life, generational
    "Pluto": 100, #transpersonal eras, late life, generational
    "Rahu": 65,
    "Ketu": 65,
    "Lilith": 45,
    "Part of Fortune": 30,
}

PLANET_NAME_ALIASES = {
    "North Node": "Rahu",
    "South Node": "Ketu",
    "Lilith (mean)": "Lilith",
    "Fortune": "Part of Fortune",
}

SIGN_AGES = {
    "Aries": 1,
    "Taurus": 3,
    "Gemini": 7,
    "Cancer": 12,
    "Leo": 16,
    "Virgo": 18,
    "Libra": 20,
    "Scorpio": 30,
    "Sagittarius": 40,
    "Capricorn": 50,
    "Aquarius": 60,
    "Pisces": 120,
}


ASPECT_AGE_SHIFT = {
    ("Saturn", "Moon", "conjunction"): 8,
    ("Saturn", "Moon", "square"): 7,
    ("Saturn", "Moon", "opposition"): 7,
    ("Saturn", "Moon", "trine"): 4,
    ("Saturn", "Moon", "sextile"): 3,

    ("Saturn", "Sun", "conjunction"): 7,
    ("Saturn", "Sun", "square"): 6,
    ("Saturn", "Sun", "opposition"): 6,

    ("Saturn", "Mercury", "conjunction"): 5,
    ("Saturn", "Mercury", "square"): 4,

    ("Moon", "Mars", "conjunction"): -3,
    ("Moon", "Mars", "square"): -4,

    ("Mercury", "Uranus", "conjunction"): -4,
    ("Mercury", "Uranus", "trine"): -2,

    ("Venus", "Neptune", "conjunction"): -2,
}

#shift = base_shift * exactness * ((p1_strength + p2_strength) / 2.0)

#not yet deployed
AGE_BANDS = [
    ("infantile", 0, 6),
    ("childlike", 7, 12),
    ("adolescent", 13, 17),
    ("emerging_adult", 18, 25),
    ("young_adult", 26, 39),
    ("established_adult", 40, 59),
    ("elder", 60, 89),
    ("ancient", 90, 200),
]


def placement_age(planet: str, sign: str,
                  planet_coeff: float = 0.65,
                  sign_coeff: float = 0.35) -> float:
    planet = PLANET_NAME_ALIASES.get(planet, planet)
    return (
        planet_coeff * PLANET_AGES[planet]
        + sign_coeff * SIGN_AGES[sign]
    )


def normalize_planet_name(planet: str) -> str:
    return PLANET_NAME_ALIASES.get(planet, planet)

def weighted_mean(items):
    total_w = sum(weight for _, weight in items)
    if total_w == 0:
        return 0.0
    return sum(age * weight for age, weight in items) / total_w

def weighted_median(items):
    if not items:
        return 0.0
    sorted_items = sorted(items, key=lambda x: x[0])
    total_w = sum(weight for _, weight in sorted_items)
    running = 0.0
    for age, weight in sorted_items:
        running += weight
        if running >= total_w / 2:
            return age
    return sorted_items[-1][0]

def weighted_std(items):
    if not items:
        return 0.0
    mu = weighted_mean(items)
    total_w = sum(weight for _, weight in items)
    variance = sum(weight * (age - mu) ** 2 for age, weight in items) / total_w
    return math.sqrt(variance)

def chart_age(placements, planet_strengths):
    """
    placements = [
        {"planet": "Sun", "sign": "Capricorn"},
        {"planet": "Moon", "sign": "Gemini"},
        ...
    ]
    planet_strengths = {
        "Sun": 1.4,
        "Moon": 1.1,
        ...
    }
    """
    items = []
    breakdown = []

    for p in placements:
        planet = normalize_planet_name(p["planet"])
        sign = p["sign"]
        if planet not in PLANET_AGES or sign not in SIGN_AGES:
            continue
        age = placement_age(planet, sign)
        weight = planet_strengths.get(planet, 1.0)
        items.append((age, weight))
        breakdown.append({
            "planet": planet,
            "sign": sign,
            "placement_age": age,
            "weight": weight,
            "weighted_contribution": age * weight,
        })

    return {
        "mean_age": weighted_mean(items),
        "median_age": weighted_median(items),
        "std_age": weighted_std(items),
        "breakdown": breakdown,
    }


def chart_age_from_positions(positions, sign_for_longitude, planet_strengths=None):
    """Compute astro age metrics directly from an app `positions` mapping.

    positions should be a dict[str, float] keyed by planet/body name.
    sign_for_longitude should convert longitude (float) into zodiac sign name.
    """
    placements = []
    for body, longitude in (positions or {}).items():
        if longitude is None:
            continue
        normalized = normalize_planet_name(str(body))
        if normalized not in PLANET_AGES:
            continue
        sign = sign_for_longitude(float(longitude))
        if sign not in SIGN_AGES:
            continue
        placements.append({"planet": normalized, "sign": sign})
    return chart_age(placements, planet_strengths or {})
