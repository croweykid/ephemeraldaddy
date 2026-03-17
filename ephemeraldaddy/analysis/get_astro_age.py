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
    return (
        planet_coeff * PLANET_AGES[planet]
        + sign_coeff * SIGN_AGES[sign]
    )

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
        planet = p["planet"]
        sign = p["sign"]
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