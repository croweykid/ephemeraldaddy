from __future__ import annotations

import datetime
import math

# from ephemeraldaddy.gui.style import DARK_THEME

# Aspect scoring constants/helpers consolidated here to keep major astro constants in one module.

CURRENT_YEAR = datetime.date.today().year

# Unified date brackets for ephemeris-backed transit calculations/searches.
# Earliest year is fixed as a precise sandbox floor for debugging/troubleshooting.
EPHEMERIS_MIN_YEAR = 1800
EPHEMERIS_SCOPE_FUTURE_YEARS = 100
EPHEMERIS_MAX_YEAR = CURRENT_YEAR + EPHEMERIS_SCOPE_FUTURE_YEARS
EPHEMERIS_MIN_DATE = datetime.date(EPHEMERIS_MIN_YEAR, 1, 1)
EPHEMERIS_MAX_DATE = datetime.date(EPHEMERIS_MAX_YEAR, 12, 31)

# Unified date brackets for natal chart creation input constraints.
NATAL_CHART_MIN_YEAR = 1700
NATAL_CHART_MAX_YEAR = CURRENT_YEAR + 60
NATAL_CHART_MIN_DATE = datetime.date(NATAL_CHART_MIN_YEAR, 1, 1)
NATAL_CHART_MAX_DATE = datetime.date(NATAL_CHART_MAX_YEAR, 12, 31)


AGE_BRACKETS: tuple[tuple[str, int | None, int | None], ...] = (
    ("0-5", 0, 5),
    ("5-10", 5, 10),
    ("10-18", 10, 18),
    ("18-29", 18, 29),
    ("30-39", 30, 39),
    ("40-49", 40, 49),
    ("50-59", 50, 59),
    ("60-69", 60, 69),
    ("70-79", 70, 79),
    ("80-89", 80, 89),
    ("90-99", 90, 99),
    ("100-110", 100, 110),
    (">110", 110, None),
)

SEASONAL_COLORS = {
    "spring":"#ccffcc", #pale spring green
    "summer":"#ffff00", #bright sunshine yellow
    "fall":"#cc3300", #mahogany, or #993600 or #b34019
    "winter":"#ccccff", #pale periwinkle
}

SEASONAL_COLOR_SPECTRUM = {
    "march": "#ccffcc",
    "april": "#ddff88",
    "may": "#eeff44",

    "june": "#ffff00",
    "july": "#eebb00",
    "august": "#dd7700",

    "september": "#cc3300",
    "october": "#cc6655",
    "november": "#cc99aa",

    "december": "#ccccff",
    "january": "#ccddee",
    "february": "#cceedd",
}

#Here for reference but not imported to any other file.
OUTER_PLANETS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}  # slow / structural
INNER_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars"}       # fast / personal
ANGLES = {"AS", "DS", "MC", "IC"}

PERSONAL = INNER_PLANETS | ANGLES

NODES = {"Rahu", "Ketu"}
ASTEROIDS = {"Vesta", "Ceres", "Juno", "Pallas"}
BLACK_MOON_LILITH = {"Lilith"}
POINTS = {"Part of Fortune"} # canonical label only; aka "Fortune"
ANGLE_POINTS = ("AS", "IC", "DS", "MC")

# Canonical angle aliases. Internal storage should always be AS/IC/DS/MC.
ANGLE_ALIASES = {
    "AS": "AS",
    "ASC": "AS",
    "Ascendant": "AS",
    "MC": "MC",
    "Midhaven": "MC",
    "Medium Coeli": "MC",
    "DS": "DS",
    "DSC": "DS",
    "Descendant": "DS",
    "IC": "IC",
    "Imum Coeli": "IC",
}

MAJOR_ASPECTS = {0, 60, 90, 120, 180}
MINOR_ASPECTS = {30, 45, 72, 135, 144, 150}

SLOW_TRANSIT_BODIES = OUTER_PLANETS | NODES | ASTEROIDS | BLACK_MOON_LILITH
FAST_TRANSIT_BODIES = {"Sun","Mercury", "Venus", "Mars"}  # Sun, Moon, Mercury, Venus, Mars
VERY_FAST_TRANSIT_BODIES = {"Moon"}


NATAL_WEIGHT = { #aka NATAL_WEIGHT - use for calculating sign/planet/house/element dominance
    "Sun": 10,
    "Moon": 10,
    "Mercury": 7,
    "Venus": 7,
    "Mars": 7,
    "Jupiter": 6,
    "Saturn": 6,
    "Uranus": 5.5,
    "Neptune": 5.5,
    "Pluto": 5.5,
    "Rahu": 4,
    "Ketu": 4,
    "Chiron": 1.5, #was 2, but I think that was high
    "Ceres": 1.5, #was 2, but I think that was high
    "Lilith": 1.5, #was 2, but I think that was high
    "Juno": 1.5, #was 2, but I think that was high
    "Vesta": 1.5, #was 2, but I think that was high
    "Pallas": 1.5, #was 2, but I think that was high
    "Part of Fortune": 1,
}

# Back-compat alias used by aspect scoring helpers.
POSITION_WEIGHTS = NATAL_WEIGHT

# Angle points should only be treated as aspect endpoints, not as generic
# body/planet dominance weights.
ANGLE_ASPECT_WEIGHTS = {
    "AS": 10,
    "MC": 9,
    "IC": 6,
    "DS": 6,
}

TRANSIT_WEIGHT = { #use for calculating aspect priority in charts
    "Pluto": 10,
    "Neptune": 9,
    "Uranus": 8,
    "Saturn": 7,
    "Jupiter": 6,
    "Rahu": 5,
    "Ketu": 5,
    "Mars": 5,
    "Venus": 4,
    "Mercury": 3,
    "Sun": 4,
    "Moon": 3,
}

NATAL_BODY_LOUDNESS = { #use for 
    "Pluto": 10,
    "Neptune": 9,
    "Uranus": 8,
    "Saturn": 7,
    "Jupiter": 6,
    "Rahu": 5,
    "Ketu": 5,
    "Mars": 5,
    "Venus": 4,
    "Mercury": 3,
    "Sun": 4,
    "Moon": 3,
}

ANGLE_WEIGHT = {
    0: 5,
    60: 2,
    90: 3,
    120: 3,
    180: 4,
    30: 1,
    45: 1,
    72: 1,
    135: 1,
    144: 1,
    150: 1,
}

ASPECT_SCORE_WEIGHTS = {
    "conjunction": 9,
    "opposition": 9,
    "trine": 8,
    "square": 9,
    "sextile": 8,
    "quincunx": 3,
    "semisextile": 2,
    "semisquare": 2,
    "sesquiquadrate": 2,
    "quintile": 2,
    "biquintile": 2,
}

ASPECT_ANGLE_DEGREES = {
    "conjunction": 0.0,
    "semisextile": 30.0,
    "semisquare": 45.0,
    "sextile": 60.0,
    "quintile": 72.0,
    "square": 90.0,
    "trine": 120.0,
    "sesquiquadrate": 135.0,
    "biquintile": 144.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}

ASPECT_SCORE_MULTIPLIERS = {
    "conjunction": 1, #1.3
    "opposition": 1, #1.2
    "trine": 0.85, #1.15
    "square": 1, #1
    "sextile": 0.85, #.8
    "quincunx": 0.2, #.75
    "semisextile": 0.3, #.65
    "semisquare": 0.3, #.7
    "sesquiquadrate": 0.3, #.5
    "quintile": 0.3, #.6
    "biquintile": 0.3, #.65
}


ASPECT_ORB_ALLOWANCES = {
    "conjunction": 6,
    "opposition": 6,
    "square": 6,
    "trine": 6,
    "sextile": 4,
    "quincunx":3,
    "semisextile":2,
    "semisquare":2,
    "sesquiquadrate": 2,
    "quintile": 2,
    "biquintile": 2,
}

ASPECT_ORB_SUN_MOON_BONUS = 2
ASPECT_ORB_ANGLE_BONUS = 1

ASPECT_BODY_ALIASES = ANGLE_ALIASES

ASPECT_SORT_OPTIONS = ("Priority", "Position", "Aspect", "Duration")

# Approximate mean durations (in days) for how long a body remains in one sign.
# These are static values meant for UI sorting, not ephemeris-precision forecasting.
BODY_SIGN_DURATION_DAYS = {
    "Moon": 2.5,
    "Sun": 30.4,
    "Mercury": 29.0,
    "Venus": 24.7,
    "Mars": 57.3,
    "Jupiter": 361.0,
    "Saturn": 896.0,
    "Uranus": 2556.0,
    "Neptune": 5004.0,
    "Pluto": 7488.0,
    "Rahu": 566.0,
    "Ketu": 566.0,
    "Chiron": 1504.0,
    "Lilith": 273.0,
    "Part of Fortune": 1.0,
    "AS": 0.08,
    "DS": 0.08,
    "MC": 0.08,
    "IC": 0.08,
}


def normalize_body_name(body: str) -> str:
    """Normalize legacy body aliases to canonical internal labels."""
    return ANGLE_ALIASES.get(body, body)


def normalize_aspect_body(body: str) -> str:
    return normalize_body_name(body)


def aspect_orb_allowance(atype: str, p1: str, p2: str) -> float:
    normalized_type = atype.replace(" ", "_").lower()
    allowance = ASPECT_ORB_ALLOWANCES.get(normalized_type)
    if allowance is None:
        return 0.0
    p1 = normalize_aspect_body(p1)
    p2 = normalize_aspect_body(p2)
    if p1 in {"Sun", "Moon"} or p2 in {"Sun", "Moon"}:
        allowance += ASPECT_ORB_SUN_MOON_BONUS
    if p1 in {"AS", "MC"} or p2 in {"AS", "MC"}:
        allowance += ASPECT_ORB_ANGLE_BONUS
    return float(allowance)


def aspect_orb_factor(asp: dict) -> float:
    allowance = aspect_orb_allowance(asp["type"], asp["p1"], asp["p2"])
    if allowance <= 0:
        return 0.0
    orb = abs(asp["delta"])
    return max(0.0, (allowance - orb) / allowance)


def aspect_pair_weight(p1: str, p2: str, planet_weights: dict[str, float] | None = None) -> float:
    p1 = normalize_aspect_body(p1)
    p2 = normalize_aspect_body(p2)
    aspect_base_weights = {**NATAL_WEIGHT, **ANGLE_ASPECT_WEIGHTS}
    if planet_weights:
        p1_weight = float(planet_weights.get(p1, aspect_base_weights.get(p1, 1)))
        p2_weight = float(planet_weights.get(p2, aspect_base_weights.get(p2, 1)))
    else:
        p1_weight = float(aspect_base_weights.get(p1, 1))
        p2_weight = float(aspect_base_weights.get(p2, 1))
    return math.sqrt(max(p1_weight, 0.0) * max(p2_weight, 0.0))


def aspect_body_sign_duration(body: str) -> float:
    normalized = normalize_aspect_body(body)
    if normalized == "Lilith (mean)":
        normalized = "Lilith"
    return BODY_SIGN_DURATION_DAYS.get(normalized, 1.0)


def aspect_duration_score(asp: dict) -> float:
    return max(
        aspect_body_sign_duration(asp["p1"]),
        aspect_body_sign_duration(asp["p2"]),
    )


def aspect_score(
    asp: dict,
    planet_weights: dict[str, float] | None = None,
    context_weight: float = 1.0,
) -> float:
    """Return an aspect score for ranking/export.

    Formula:
        sqrt(weight(p1) * weight(p2)) * aspect_type_weight * orb_factor * context_weight

    `planet_weights` can be chart-specific (e.g. dominant_planet_weights). If
    omitted, static NATAL_WEIGHT values are used.
    """
    normalized_type = asp["type"].replace(" ", "_").lower()
    aspect_weight = ASPECT_SCORE_WEIGHTS.get(normalized_type, 0.0)
    pair_weight = aspect_pair_weight(asp["p1"], asp["p2"], planet_weights=planet_weights)
    orb_factor = aspect_orb_factor(asp)
    return pair_weight * aspect_weight * orb_factor * float(context_weight)


#structure: for each house, sign & planet in the positions line, look up their values below and print: a [HOUSE_NOUNS] that's [SIGN_KEYWORDS ->adverbs->(a concat of best_adverbs & worst_adverbs)] [PLANET_KEYWORDS->verbs]
#randomly draw 6 different combinations.

ZODIAC_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_GENDERS = [ #higher number = more femme. Average a chart by prevalence & also with weights, with 11 being most femme.
    ("Taurus", 10), #8
    ("Cancer", 10), #10
    ("Virgo", 10), #8
    ("Pisces", 10), #10
    ("Capricorn", 10), #6 #ambitious, rambunctious & rugged but networked & discreet
    ("Scorpio", 10), #6 #co-ruled by mars

    ("Gemini", 0), #5
    ("Aquarius", 0), #4
    ("Libra", 0), #3
    ("Sagittarius", 0), #0 #sportiest, blunt, barbaric, butch
    ("Leo", 0), #0 #lots of peacocking, but high glam too, very flamboyant
    ("Aries", 0), #0 #literally god of war, ruled by mars
]

PLANET_ORDER = [
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
    "Rahu",
    "Ketu",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Lilith",
    "Part of Fortune",
    *ANGLE_POINTS,
]

SIGN_ELEMENTS = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

NAKSHATRA_RANGES = [
    ("Ashwini", "Aries", 23, 51, "Taurus", 7, 11),
    ("Bharani", "Taurus", 7, 11, "Taurus", 20, 31),
    ("Krittika", "Taurus", 20, 31, "Gemini", 3, 51),
    ("Rohini", "Gemini", 3, 51, "Gemini", 17, 11),
    ("Mrigashira", "Gemini", 17, 11, "Cancer", 0, 31),
    ("Ardra", "Cancer", 0, 31, "Cancer", 13, 51),
    ("Punarvasu", "Cancer", 13, 51, "Cancer", 27, 11),
    ("Pushya", "Cancer", 27, 11, "Leo", 10, 31),
    ("Ashlesha", "Leo", 10, 31, "Leo", 23, 51),
    ("Magha", "Leo", 23, 51, "Virgo", 7, 11),
    ("Purva Phalguni", "Virgo", 7, 11, "Virgo", 20, 31),
    ("Uttara Phalguni", "Virgo", 20, 31, "Libra", 3, 51),
    ("Hasta", "Libra", 3, 51, "Libra", 17, 11),
    ("Chitra", "Libra", 17, 11, "Scorpio", 0, 31),
    ("Swati", "Scorpio", 0, 31, "Scorpio", 13, 51),
    ("Vishakha", "Scorpio", 13, 51, "Scorpio", 27, 11),
    ("Anuradha", "Scorpio", 27, 11, "Sagittarius", 10, 31),
    ("Jyestha", "Sagittarius", 10, 31, "Sagittarius", 23, 51),
    ("Mula", "Sagittarius", 23, 51, "Capricorn", 7, 11),
    ("Purva Ashadha", "Capricorn", 7, 11, "Capricorn", 20, 31),
    ("Uttara Ashadha", "Capricorn", 20, 11, "Aquarius", 3, 51),
    ("Shravana", "Aquarius", 3, 51, "Aquarius", 17, 11),
    ("Dhanishta", "Aquarius", 17, 11, "Pisces", 0, 31),
    ("Shatabhisha", "Pisces", 0, 31, "Pisces", 13, 51),
    ("Purva Bhadrapada", "Pisces", 13, 51, "Pisces", 27, 11),
    ("Uttara Bhadrapada", "Pisces", 27, 11, "Aries", 10, 31),
    ("Revati", "Aries", 10, 31, "Aries", 23, 51),
]


MODES = {
    "cardinal": {"Aries","Cancer","Libra","Capricorn"},
    "mutable": {"Gemini", "Virgo","Sagittarius","Pisces"},
    "fixed": {"Taurus","Leo","Scorpio","Aquarius"},
}

MODE_KEYWORDS = {
    "cardinal": {"go-getter","dynamic","action-oriented","pushy","catalyzing","aggro"},
    "mutable": {"adaptable","responsive","takes people & things as they come","flexible","ever-evolving"},
    "fixed": {"static","unyielding","firm","unmoveable","set in one's ways","resolved"},
}

MODE_COLORS = {
    "cardinal": "#993333", #burnt orange
    "mutable": "#6699ff", #blue
    "fixed": "#336600", #olive
}

#commented this out to prevent future confusion, cos I don't actually want to use this; it unbalances the whole system for modern planets! :(
# PLANET_RULERSHIP_CLASSICAL = {
#     "Sun": {"Leo"},
#     "Moon": {"Cancer"},
#     "Mercury": {"Gemini", "Virgo"},
#     "Venus": {"Taurus", "Libra"},
#     "Mars": {"Aries","Scorpio"},
#     "Jupiter": {"Sagittarius","Pisces"},
#     "Saturn": {"Capricorn","Aquarius"},
# }

HELLENISTIC_HEMISPHERES = { #this is evidently about BALANCE; where they best thrive, not their nature
    "Sun": {"diurnal"}, #because of fire.
    "Moon": {"nocturnal"}, #because of earth
    "Mercury": {"crepuscular"}, #ambivalent, transgender, 
    "Venus": {"nocturnal"}, #'esp effective in darkness' was the rationale. But sculptors & painters of the world disagree...
    "Mars": {"nocturnal"}, #'fiery and impulsive energy is calmed by the coolness of night'. Hey back in the day, did you know most war deities were female? fun fact. Arsinoe & Astarte for...astarters...
    "Jupiter": {"diurnal"}, #expanding & bringing good fortune in daylight 
    "Saturn": {"diurnal"}, #cold restrictive malefic moderated by daytime warmth
    #then I got nuts and added outer planets; fight me, bro...
    "Neptune": {"nocturnal"}, #noncanonical - but neptune is arguably best when it's dreaming, not sleepwalking awake; sleepingin the day is like a coma and who wants that? lol
    "Uranus": {"crepuscular"}, #noncanonical - but it's the liminal, changeful unpredictability of it.
    "Pluto": {"diurnal"}, #noncanonical - but in keeping with the motif, let's hold power to account in broad daylight?
}

PLANETARY_JOYS = { #2,4,7,8 & 10 don't get bonuses
    "Sun": {9}, #'God'
    "Moon": {3}, #'Goddess'
    "Mercury": {1}, #'Helm'
    "Venus": {5}, #'Good fortune'
    "Mars": {6},  #'Bad fortune'
    "Jupiter": {11}, #'Good spirit'
    "Saturn": {12}, #'Bad spirit'
    "Neptune": {8}, #noncanonical in Hellenistic tradition, but Neptune is at home with ego death
    "Uranus": {}, #noncanonical in Hellenistic tradition. Neither 2, 7 nor 4 make much sense for Uranus.
    "Pluto": {10}, #noncanonical in Hellenistic tradition, but Pluto loves power.
}

#not sure if I should use both signs or not.
PLANET_RULERSHIP = {
    "Sun": {"Leo"},
    "Moon": {"Cancer"},
    "Mercury": {"Gemini", "Virgo"},
    "Venus": {"Taurus", "Libra"},
    "Mars": {"Aries","Scorpio"}, #"Scorpio"
    "Jupiter": {"Sagittarius","Pisces"}, #"Pisces"
    "Saturn": {"Capricorn","Aquarius"}, #"Aquarius"
    "Neptune": {"Pisces"},
    "Uranus": {"Aquarius"},
    "Pluto": {"Scorpio"},
}

PLANET_EXALTATION = {
    "Sun": {"sign": "Aries", "degree": 19},
    "Moon": {"sign": "Taurus", "degree": 3},
    "Mercury": {"sign": "Virgo", "degree": 15},
    "Venus": {"sign": "Pisces", "degree": 27},
    "Mars": {"sign": "Capricorn", "degree": 28},
    "Jupiter": {"sign": "Cancer", "degree": 15},
    "Saturn": {"sign": "Libra", "degree": 21},
}

PLANET_DETRIMENT = {
    "Sun": {"Aquarius"},
    "Moon": {"Capricorn"},
    "Mercury": {"Sagittarius", "Pisces"},
    "Venus": {"Scorpio", "Aries"},
    "Mars": {"Libra", "Taurus"},
    "Jupiter": {"Gemini", "Virgo"},
    "Saturn": {"Cancer", "Leo"},
}

PLANET_FALL = {
    "Sun": {"sign": "Libra", "degree": 19},
    "Moon": {"sign": "Scorpio", "degree": 3},
    "Mercury": {"sign": "Pisces", "degree": 15},
    "Venus": {"sign": "Virgo", "degree": 27},
    "Mars": {"sign": "Cancer", "degree": 28},
    "Jupiter": {"sign": "Capricorn", "degree": 15},
    "Saturn": {"sign": "Aries", "degree": 21},
}

RULERSHIP_WEIGHT = 5
EXALTATION_WEIGHT = 4
TRIPLICITY_WEIGHT = 3
DETRIMENT_WEIGHT = -5
FALL_WEIGHT = -4

HOUSE_CUSP_BLEND_DEGREES = 8.0
NATURAL_HOUSE_SIGN_BONUS = 6.0
NATURAL_HOUSE_PLANET_BONUS = 6.0
DISPOSITOR_PLANET_ATTENUATION = 0.35
DISPOSITOR_SIGN_ATTENUATION = 0.30
DISPOSITOR_MAX_DEPTH = 2
CHART_RULER_BONUS = 4.0
TIGHT_ASPECT_ORB_DEGREES = 1.0
TIGHT_ASPECT_INTENSITY_MIN = 1.2
TIGHT_ASPECT_INTENSITY_MAX = 1.4

NATURAL_HOUSE_SIGNS = {
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

NATURAL_HOUSE_PLANETS = {
    1: "Mars",
    2: "Venus",
    3: "Mercury",
    4: "Moon",
    5: "Sun",
    6: "Mercury",
    7: "Venus",
    8: "Pluto",
    9: "Jupiter",
    10: "Saturn",
    11: "Uranus",
    12: "Neptune",
}

#currently ignoring house weights, except for the 4 main angles, cos I'm not sure it's even a legit thing.
HOUSE_WEIGHTS = {
    1: 4,
    4: 3,
    7: 3,
    10: 4,
    2: 2.75,
    5: 2.75,
    8: 2.75,
    11: 2.75,
    3: 2.7,
    6: 2.7,
    9: 2.7,
    12: 2.7,
}

ANGULAR_AMPLIFICATION = (
    (5, 4),
    (10, 2),
    (15, 1),
)

ZODIAC_SIGNS = [
    "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎",
    "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎",
]

ELEMENT_COLORS = {
    "Fire": "#cc3300", #was #7a4747, #503030
    "Earth": "#049534", #was #339966, before that it was #2e6b42
    "Air": "#999900", #was #8b73a3, #66527a
    "Water": "#5f5f8f", #was 2d2d5c
}

BAZI_ELEMENTS = { #BAZI_ELEMENT_COLORS <-rename this, appwide
    "wood": {
        "color": "#999900",
        "one_liner": "Growth with an agenda; the vine that joins committees and keeps climbing anyway.",
    },
    "water": {
        "color": ELEMENT_COLORS["Water"],
        "one_liner": "Finds the gap, ignores the memo, arrives everywhere eventually.",
    },
    "earth": {
        "color": ELEMENT_COLORS["Earth"],
        "one_liner": "The load-bearing adult in the room, quietly judging others' poor planning.",
    },
    "fire": {
        "color": ELEMENT_COLORS["Fire"],
        "one_liner": "Charisma, heat, spectacle; excellent at getting attention and setting off alarms.",
    },
    "metal": {
        "color": "#669999",
        "one_liner": "Precision with attitude; polished, sharp, and not here for sloppy nonsense.",
    },
}

BAZI_ZODIAC = {
    "rat": {
        "color": "#5f6874",  # smoky blue-gray
        "one_liner": "Keeper of openings; where others see scarcity, Rat notices the one usable passage."
    },
    "ox": {
        "color": "#6b5a3a",  # weathered umber
        "one_liner": "Patient force; built to carry the season without asking to be admired.",
    },
    "tiger": {
        "color": "#a35f2d",  # burnt amber
        "one_liner": "Sovereign appetite; it does not wait for permission to become itself.",
    },
    "rabbit": {
        "color": "#9c9f8a",  # soft sage stone
        "one_liner": "Guardian of peace; it survives by sensing disturbance before it takes shape.",
    },
    "dragon": {
        "color": "#4f6f63",  # deep jade
        "one_liner": "A sign of excess vitality; destiny tends to arrive noisily around it.",
    },
    "snake": {
        "color": "#6f6a4b",  # olive bronze
        "one_liner": "Still intelligence; it removes the unnecessary and keeps only what matters.",
    },
    "horse": {
        "color": "#8a5a3b",  # chestnut clay
        "one_liner": "Unharnessed motion; freedom is not a preference here but a governing law.",
    },
    "goat": {
        "color": "#b19b8c",  # warm taupe
        "one_liner":"Tender refinement; it makes beauty feel necessary rather than decorative.",
    },
    "monkey": {
        "color": "#8b7650",  # antique brass
        "one_liner": "Restless ingenuity; the pattern, the loophole, and the trick reveal themselves quickly.",
    },
    "rooster": {
        "color": "#7d4a3f",  # muted garnet
        "one_liner": "Ceremonial precision; it names the hour, the flaw, and the standard.",
    },
    "dog": {
        "color": "#6a5448",  # ironwood brown
        "one_liner": "Faithful conscience; it stands guard over what it believes is right.",
    },
    "pig": {
        "color": "#b07d72",  # dusty rose clay
        "one_liner": "Honest abundance; it understands that fullness, rightly held, is its own wisdom.",
    },
}

SIGN_COLORS = {
    "Aries": ELEMENT_COLORS["Fire"],
    "Leo": ELEMENT_COLORS["Fire"],
    "Sagittarius": ELEMENT_COLORS["Fire"], #e67300
    "Taurus": ELEMENT_COLORS["Earth"],
    "Virgo": ELEMENT_COLORS["Earth"],
    "Capricorn": ELEMENT_COLORS["Earth"],
    "Gemini": ELEMENT_COLORS["Air"],
    "Libra": ELEMENT_COLORS["Air"],
    "Aquarius": ELEMENT_COLORS["Air"],
    "Cancer": ELEMENT_COLORS["Water"],
    "Scorpio": ELEMENT_COLORS["Water"],
    "Pisces": ELEMENT_COLORS["Water"],
}


SIGN_WHEELS = {
    "Aries": "ephemeraldaddy/graphics/chartwheel_components/aries.png",
    "Taurus": "ephemeraldaddy/graphics/chartwheel_components/taurus.png",
    "Gemini": "ephemeraldaddy/graphics/chartwheel_components/gemini.png",
    "Cancer": "ephemeraldaddy/graphics/chartwheel_components/cancer.png",
    "Leo": "ephemeraldaddy/graphics/chartwheel_components/leo.png",
    "Virgo": "ephemeraldaddy/graphics/chartwheel_components/virgo.png",
    "Libra": "ephemeraldaddy/graphics/chartwheel_components/libra.png",
    "Scorpio": "ephemeraldaddy/graphics/chartwheel_components/scorpio.png",
    "Sagittarius": "ephemeraldaddy/graphics/chartwheel_components/sagittarius.png",
    "Capricorn": "ephemeraldaddy/graphics/chartwheel_components/capricorn.png",
    "Aquarius": "ephemeraldaddy/graphics/chartwheel_components/aquarius.png",
    "Pisces": "ephemeraldaddy/graphics/chartwheel_components/pisces.png",
}

SIGN_DOMESTICATION = { #0 is most chthonic, 10 is most apolonian
    "Aries":6, #barbaric but concerned with rationality
    "Taurus":2, #primal
    "Gemini":7, #absurdly civilized
    "Cancer":4, #pretty primal
    "Leo":5, #can go either way
    "Virgo":9, #sensible & orderly
    "Libra":10, #all about balance & refinement, epitomizes apolonian ideal
    "Scorpio":1, #hella primal
    "Sagittarius":3, #pan incarnate, but scholarly
    "Capricorn":5, #can go either way
    "Aquarius":8, #respects order & reaason
    "Pisces":0, #most primal
}

PLANET_COLORS = {
    "Sun": "#ffd700", #"gold" - formerly #ffff66 buttercup
    "Moon": "#00ffff", #6699ff or #4d6680 dark grey blue might be thematically better but we need readability
    "Mercury": "#adff3f", #was #fff8dc cornsilk yellow-white, but that looked too much like rahu/ketu
    "Venus": "#ffccff", #pale rose
    "Mars": "#b94646", #brick red
    "Jupiter": "#e67300", #amber
    "Saturn": "#6b946b", #grandpa green
    "Uranus": "#9933ff", #went #7fff00 "chartreuse" but looked too much like mercury
    "Neptune": "#99ffcc", #6600ff was great but unreadable :(
    "Pluto": "#0099ff", #383894 or #2a2a6f might be superior but you can't read it at all :(
    "Rahu": "#6699ff", #fffff0 #"ivory" - formerly #355A55 smoky teal, but we needed readability
    "Ketu": "#6699ff", #dcdcdc #"gainsboro" - formerly #5A4A52 ash-violet, but we needed readability
    "Chiron":"#6699ff", #basic blue
    "Ceres":"#6699ff", #basic blue
    "Pallas":"#6699ff", #basic blue
    "Juno":"#6699ff", #basic blue
    "Vesta":"#6699ff", #basic blue
    "Lilith":"#6699ff", #basic blue
    "Part of Fortune":"#6699ff", #basic blue
    "Fortune":"#6699ff", #basic blue #should be treated as an alias
    "AS":"#33ccff", #lighter basic blue to indicate angles
    "IC":"#33ccff", #lighter basic blue to indicate angles #lighter basic blue to indicate angles
    "DS":"#33ccff", #lighter basic blue to indicate angles
    "MC":"#33ccff", #lighter basic blue to indicate angles
    "Earth":"#049534", #was #339966 #slightly bluish green
}

# not used anywhere, as far as I can tell
# PLANET_COLORS_EARTH = {
#   "Sun": "#8A7A3B", # muted ochre
#   "Moon": "#4D6680", # your slate is already fine
#   "Mercury": "#8E8570", # parchment/khaki
#   "Venus": "#7C5C73", # dusty mauve #not in use as far as I can find?
#   "Mars": "#6F3D35", # brick
#   "Jupiter": "#8A4E1E", # burnt orange
#   "Saturn": "#2B3B2B", # your deep olive is already earthtone
#   "Rahu": "#355A55", # smoky teal
#   "Ketu": "#5A4A52", # ash-violet
# }

#I should maybe link this directly to sign colors? Or at least add a reference lookup in case I want to have a default mode with hexcolor overrides?
HOUSE_COLORS = {
    "1": PLANET_COLORS["Mars"],
    "2": PLANET_COLORS["Venus"],
    "3": PLANET_COLORS["Mercury"],
    "4": PLANET_COLORS["Moon"],
    "5": PLANET_COLORS["Sun"],
    "6": PLANET_COLORS["Mercury"],
    "7": PLANET_COLORS["Venus"],
    "8": PLANET_COLORS["Pluto"],
    "9": PLANET_COLORS["Jupiter"],
    "10": PLANET_COLORS["Saturn"],
    "11": PLANET_COLORS["Uranus"],
    "12": PLANET_COLORS["Neptune"],
    "Rahu": PLANET_COLORS["Rahu"],
    "Ketu": PLANET_COLORS["Ketu"],
}

ASPECT_COLORS = {
    "conjunction": "#aaaaaa",
    "sextile":     "#4caf50",
    "square":      "#f44336",
    "trine":       "#2196f3",
    "opposition":  "#ff9800",
    "sesquiquadrate": "grey",
    "quincunx":    "#9c27b0",
    "semisextile": "#26a69a",
    "semisquare":  "#00bcd4",
    "quintile":    "#8bc34a",
    "biquintile":  "#cddc39",
}

NAKSHATRA_PLANET_COLOR = {
    "Ashwini": ("Ketu", PLANET_COLORS["Ketu"]),
    "Bharani": ("Venus", PLANET_COLORS["Venus"]),
    "Krittika": ("Sun", PLANET_COLORS["Sun"]),
    "Rohini": ("Moon", PLANET_COLORS["Moon"]),
    "Mrigashira": ("Mars", PLANET_COLORS["Mars"]),
    "Ardra": ("Rahu", PLANET_COLORS["Rahu"]),
    "Punarvasu": ("Jupiter", PLANET_COLORS["Jupiter"]),
    "Pushya": ("Saturn", PLANET_COLORS["Saturn"]),
    "Ashlesha": ("Mercury", PLANET_COLORS["Mercury"]),
    "Magha": ("Ketu", PLANET_COLORS["Ketu"]),
    "Purva Phalguni": ("Venus", "#7C5C73"),
    "Uttara Phalguni": ("Sun", PLANET_COLORS["Sun"]),
    "Hasta": ("Moon", PLANET_COLORS["Moon"]),
    "Chitra": ("Mars", PLANET_COLORS["Mars"]),
    "Swati": ("Rahu", PLANET_COLORS["Rahu"]),
    "Vishakha": ("Jupiter", PLANET_COLORS["Jupiter"]),
    "Anuradha": ("Saturn", PLANET_COLORS["Saturn"]),
    "Jyestha": ("Mercury", PLANET_COLORS["Mercury"]),
    "Mula": ("Ketu", PLANET_COLORS["Ketu"]),
    "Purva Ashadha": ("Venus", PLANET_COLORS["Venus"]),
    "Uttara Ashadha": ("Sun", PLANET_COLORS["Sun"]),
    "Shravana": ("Moon", PLANET_COLORS["Moon"]),
    "Dhanishta": ("Mars", PLANET_COLORS["Mars"]),
    "Shatabhisha": ("Rahu", PLANET_COLORS["Rahu"]),
    "Purva Bhadrapada": ("Jupiter", PLANET_COLORS["Jupiter"]),
    "Uttara Bhadrapada": ("Saturn", PLANET_COLORS["Saturn"]),
    "Revati": ("Mercury", PLANET_COLORS["Mercury"]),
}

NAKSHATRA_DESCRIPTIONS = {
    "Ashwini": {
        "name": "Ashwini",
        "symbol": "Horse – Star of Transport",
        "shakti": "The power to heal self and others quickly.",
        "essence": "Healing, energy, movement and speed.",
        "quality": "Laghu: light, swift & auspicious",
        "favorable_activities": "Favorable activities : Commence a journey, trade, and transactions, involve in sports activities, and also starting sales, business or repaying loan/debts.",
        "sidereal_sign": "Aries",
        "archetypes": "The Comedian (sun), serial killer (moon, also sun/moon/asc), MMA (mars), lesser scream queens (all Ketu, but Mula is #1 by far), #3 golddigger",
        "deity": "Ketu",
        "ruler": "Ketu",
        "planetary_associations": "Mars/Venus",
        "comments_A": "",
        "comments_B": ""
    },

    "Bharani": {
        "name": "Bharani",
        "symbol": "Yoni – Star of Restraint",
        "shakti": "The power of renewal & metamorphosis.",
        "essence": "Restraint, death & rebirth; transformation of spirit",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Aries",
        "archetypes": "Karma & erotic revenge; eternal youth & resurrection",
        "deity": "Shukra",
        "ruler": "Venus",
        "planetary_associations": "Venus",
        "comments_A": "",
        "comments_B": ""
    },

    "Krittika": {
        "name": "Krittika",
        "symbol": "Knife – Star of Fire",
        "shakti": "The power to cut through problems.",
        "essence": "Burning through illusion to get to truth.",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Aries/Taurus",
        "archetypes": "MMA (moon)",
        "deity": "Surya",
        "ruler": "Sun",
        "planetary_associations": "Venus/Mercury",
        "comments_A": "",
        "comments_B": ""
    },

    "Rohini": {
        "name": "Rohini",
        "symbol": "Red One – Ox – Star of Ascent",
        "shakti": "Power to make things grow.",
        "essence": "Enjoyment, fertility, attraction, creative expansion.",
        "quality": "Sthira & Mridu: fixed, stable & soft, gentle, yielding.",
        "favorable_activities": "Build homes, plant trees, purchase property, lay a foundation, and buying agricultural property.",
        "sidereal_sign": "Taurus",
        "archetypes": "Born Sexy Yesterday, Sugar Baby; MMA (moon), #5 occultist (dom). Few millionaires/billionaires (moon).",
        "deity": "Chandra",
        "ruler": "Moon",
        "planetary_associations": "Mercury",
        "comments_A": "",
        "comments_B": "Lakshmi"
    },

    "Mrigashira": {
        "name": "Mrigashira",
        "symbol": "Deer Head – Star of Searching",
        "shakti": "The power to find fulfillment",
        "essence": "Wandering, searching, and seeking truth.",
        "quality": "Mridu: soft, gentle, yielding.",
        "favorable_activities": "Learning music, dance, arts and marriages. They are also ideal for the enjoyment of pleasures, making new friends, and wearing new clothes.",
        "sidereal_sign": "Taurus/Gemini",
        "archetypes": "Artemis, serial killer (asc). Few millionaires/billionaires (moon). Amnesia plots & memory issues seem to be a theme. Encourages sovereignty in others.",
        "deity": "Mangal",
        "ruler": "Mars",
        "planetary_associations": "Mercury",
        "comments_A": "",
        "comments_B": ""
    },

    "Ardra": {
        "name": "Ardra",
        "symbol": "Teardrop – Star of Emotion",
        "shakti": "The power to feel & act",
        "essence": "Stormy, caustic; intensity & passionate drive for expression.",
        "quality": "Tikshna: sharp, penetrating, active",
        "favorable_activities": "Filing a divorce, breaking a relationship, black magic, exorcism, and other brash/bold activities.",
        "sidereal_sign": "Gemini",
        "archetypes": "Haterade, snarkfest; Comedian (moon)",
        "deity": "Rahu",
        "ruler": "Rahu",
        "planetary_associations": "Mercury/Moon",
        "comments_A": "",
        "comments_B": ""
    },

    "Punarvasu": {
        "name": "Punarvasu",
        "symbol": "Arrows – Star of Renewal",
        "shakti": "Renewal, return of the light.",
        "essence": "Enlightening the world with hope & calling in a new dawn.",
        "quality": "Mridu & Chara: soft, gentle, yielding & movable, changeable",
        "favorable_activities": "Buy automobiles, vehicles, beginning a journey or procession, travel, change of residence or job, and other major changes.",
        "sidereal_sign": "Gemini/Cancer",
        "archetypes": "Ugly curse - beast needs love to heal/become beautiful (mostly male trope). #3 richest moon. #3 in ugly duckling glow-up plots. Alt kids & offbeat beatnics. Vulnerable to golddiggers & con artists. Voted 2nd least likely to deny their boundless primal urges. :-P",
        "deity": "Guru",
        "ruler": "Jupiter",
        "planetary_associations": "Moon",
        "comments_A": "Teardrop, diamond",
        "comments_B": ""
    },

    "Pushya": {
        "name": "Pushya",
        "symbol": "Cow Udder – Star of Nourishment",
        "shakti": "Revered elder, sensei.",
        "essence": "Teaching and nourishment, mentorship.",
        "quality": "Laghu: light, swift & auspicious",
        "favorable_activities": "Favorable activities : Commence a journey, trade, and transactions, involve in sports activities, and also starting sales, business or repaying loan/debts.",
        "sidereal_sign": "Cancer",
        "archetypes": "#3 Occultist (sun & dom). #3 most famous (asc). Considered the luckiest. Also the wealthiest.",
        "deity": "Shani",
        "ruler": "Saturn",
        "planetary_associations": "Moon/Sun",
        "comments_A": "Expansive, boundless",
        "comments_B": ""
    },

    "Ashlesha": {
        "name": "Ashlesha",
        "symbol": "Snake – Clinging Star",
        "shakti": "The powers of poison and medicine.",
        "essence": "Hypnotizing the mind while transforming and healing afflictions.",
        "quality": "Tikshna: sharp, penetrating, active",
        "favorable_activities": "Filing a divorce, breaking a relationship, black magic, exorcism, and other brash/bold activities.",
        "sidereal_sign": "Cancer",
        "archetypes": "",
        "deity": "Budh",
        "ruler": "Mercury",
        "planetary_associations": "Sun",
        "comments_A": "",
        "comments_B": ""
    },

    "Magha": {
        "name": "Magha",
        "symbol": "Throne – Star of Power",
        "shakti": "The power to leave the body & travel beyond this realm",
        "essence": "Honoring the ancestor spirits; leading forward with respect & dignity",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Leo",
        "archetypes": "MMA (mars), occultist, lesser scream queens (all Ketu, but Mula is #1 by far); golddiggers (as well as Mula).",
        "deity": "Ketu",
        "ruler": "Ketu",
        "planetary_associations": "Sun",
        "comments_A": "",
        "comments_B": ""
    },

    "Purva Phalguni": {
        "name": "Purva Phalguni",
        "symbol": "Foot of Bed – Star of Fortune",
        "shakti": "Pleasure: The power of creation and family.",
        "essence": "Finding love, enjoyment, and ease.",
        "quality": "Mridu: soft, gentle, yielding",
        "favorable_activities": "Learn music, dance, make art and get married. They are also ideal for the enjoyment of pleasures, making new friends, and wearing new clothes.",
        "sidereal_sign": "Leo",
        "archetypes": "Few millionaires/billionaires (moon).",
        "deity": "Shukra",
        "ruler": "Venus",
        "planetary_associations": "Sun/Mercury/Vulcan",
        "comments_A": "",
        "comments_B": ""
    },

    "Uttara Phalguni": {
        "name": "Uttara Phalguni",
        "symbol": "Head of bed – Star of Patronage",
        "shakti": "Contracts: The power to accumulate security.",
        "essence": "Upholding sacred vows of love and friendship.",
        "quality": "Mridu & Sthira: fixed, stable & soft, gentle, yielding",
        "favorable_activities": "Build homes, plant trees, purchase property, lay a foundation, and buying agricultural property.",
        "sidereal_sign": "Leo/Virgo",
        "archetypes": "Most famous (asc).",
        "deity": "Surya",
        "ruler": "Sun",
        "planetary_associations": "Mercury/Vulcan/Venus",
        "comments_A": "",
        "comments_B": ""
    },

    "Hasta": {
        "name": "Hasta",
        "symbol": "Hand – Star of the Golden-Handed",
        "shakti": "The power to manifest one’s desires.",
        "essence": "Handling with skill and making magic.",
        "quality": "Laghu: light, swift & auspicious",
        "favorable_activities": "Favorable activities : Commence a journey, trade, and transactions, involve in sports activities, and also starting sales, business or repaying loan/debts.",
        "sidereal_sign": "Virgo",
        "archetypes": "Trickster, shapeshifter. #2 occultist (dom). #2 richest (moon, mercury). Master manipulator.",
        "deity": "Chandra",
        "ruler": "Moon",
        "planetary_associations": "Venus",
        "comments_A": "",
        "comments_B": ""
    },

    "Chitra": {
        "name": "Chitra",
        "symbol": "Jewel – Star of Opportunity",
        "shakti": "Shapeshifter, trickster. The power to accumulate merit.",
        "essence": "Inventing wonderful new creations, sometimes becoming them.",
        "quality": "Tikshna: sharp, penetrating, active",
        "favorable_activities": "Filing a divorce, breaking a relationship, black magic, exorcism, and other brash/bold activities.",
        "sidereal_sign": "Virgo/Libra",
        "archetypes": "Trickster, shapeshifter; serial killer (lagna)",
        "deity": "Mangal",
        "ruler": "Mars",
        "planetary_associations": "Venus/Pluto/Mars",
        "comments_A": "",
        "comments_B": ""
    },

    "Swati": {
        "name": "Swati",
        "symbol": "Sword – Star of Independence",
        "shakti": "The power to scatter like the wind.",
        "essence": "Staying flexible and free for self-inquiry.",
        "quality": "Chara: movable, changeable",
        "favorable_activities": "Buy automobiles, vehicles, beginning a journey or procession, travel, change of residence or job, and other major changes.",
        "sidereal_sign": "Libra",
        "archetypes": "Hologram, dream empire; Comedian (moon). #3 most creative. Few millionaires/billionaires (moon). #2 most famous (asc).",
        "deity": "Rahu",
        "ruler": "Rahu",
        "planetary_associations": "Pluto/Mars",
        "comments_A": "Coral",
        "comments_B": ""
    },

    "Vishakha": {
        "name": "Vishakha",
        "symbol": "Trident – Archway – Star of Purpose",
        "shakti": "The power to achieve many things in life.",
        "essence": "Connecting to the will and drive of spirit.",
        "quality": "Tikshna: sharp, penetrating, active",
        "favorable_activities": "Filing a divorce, breaking a relationship, black magic, exorcism, and other brash/bold activities.",
        "sidereal_sign": "Libra/Scorpio",
        "archetypes": "MMA (moon). #1 in ugly duckling glow-up plots. Dr. Jekyl & Mr. Hyde / The Mask: Dangerous extremes finding profound balance (split personality, evil alternate self). Often begin with repressed \"nice person\" energy that tries to quarantine all their darkest impulses (which eventually emerge). Wild child / borderline PD.",
        "deity": "Guru",
        "ruler": "Jupiter",
        "planetary_associations": "Pluto/Mars",
        "comments_A": "",
        "comments_B": ""
    },

    "Anuradha": {
        "name": "Anuradha",
        "symbol": "Lotus – Star of Success",
        "shakti": "The power to worship (bhakti).",
        "essence": "Succeeding though kindness, co-operation",
        "quality": "Mridu: soft, gentle, yielding",
        "favorable_activities": "Learn music, dance, make arts and get married. They are also ideal for the enjoyment of pleasures, making new friends, and wearing new clothes.",
        "sidereal_sign": "Scorpio",
        "archetypes": "Occultist",
        "deity": "Shani",
        "ruler": "Saturn",
        "planetary_associations": "Pluto/Mars/Jupiter",
        "comments_A": "",
        "comments_B": ""
    },

    "Jyestha": {
        "name": "Jyestha",
        "symbol": "Umbrella – Eldest Sister – Chief Star",
        "shakti": "Power to conquer and gain courage.",
        "essence": "Rising up to overcome oppression.",
        "quality": "Tikshna: sharp, penetrating, active",
        "favorable_activities": "Filing a divorce, breaking a relationship, black magic, exorcism, and other brash/bold activities.",
        "sidereal_sign": "Scorpio",
        "archetypes": "'Tiger blood' - you know, the Charlie Sheen quote; killer instinct, domination urge, insatiable rapacity. Richest (moon). Show-off / bombastic.",
        "deity": "Budh",
        "ruler": "Mercury",
        "planetary_associations": "Jupiter",
        "comments_A": "Empty, dry, barren",
        "comments_B": "Alakshmi"
    },

    "Mula": {
        "name": "Mula",
        "symbol": "Roots – Foundation Star",
        "shakti": "The power to transform from the root.",
        "essence": "Destroying illusion to go beyond it.",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Sagittarius",
        "archetypes": "Belle, destroys/transforms the monster. Occult. To face & destroy artifice, to penetrate the mask, The Final Girl (lone survivor due to superior intelligence & resourcefulness), subdues the beast, The Strength card, superego beats the id, always the virgin, uses a fire poker, the beast often becomes obsessed with the mula. #1 nakshatra representred in 'vegetarian vampire' trope. All about controlling the primal urge in the name of justice.",
        "deity": "Ketu",
        "ruler": "Ketu",
        "planetary_associations": "Jupiter/Saturn",
        "comments_A": "",
        "comments_B": ""
    },

    "Purva Ashadha": {
        "name": "Purva Ashadha",
        "symbol": "Elephant Tusk – Fan – Invincible Star",
        "shakti": "The power to invigorate.",
        "essence": "Energizing towards greater empowerment",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Sagittarius",
        "archetypes": "Purification, the purge. Most represented in black metal. Lunar nakshatra found in many comedians. Deemed '2nd most artistic/creative' by Claire Nakti. Seeks destruction of perceived impurities & flaws in the system.",
        "deity": "Sukhra",
        "ruler": "Venus",
        "planetary_associations": "Saturn",
        "comments_A": "",
        "comments_B": ""
    },

    "Uttara Ashadha": {
        "name": "Uttara Ashadha",
        "symbol": "Elephant Tusk – Bed planks – Universal Star",
        "shakti": "The power of complete victory.",
        "essence": "Winning for the highest good of all.",
        "quality": "Sthira: fixed, stable.",
        "favorable_activities": "Build homes, plant trees, purchase property, lay a foundation, and buying agricultural property.",
        "sidereal_sign": "Sagittarius/Capricorn",
        "archetypes": "Least combative mars placement. Enabling status quo apologists.",
        "deity": "Surya",
        "ruler": "Sun",
        "planetary_associations": "Saturn/Uranus",
        "comments_A": "",
        "comments_B": ""
    },

    "Shravana": {
        "name": "Shravana",
        "symbol": "Ear – Star of Learning",
        "shakti": "The power to connect.",
        "essence": "Listening to others for wisdom and greater understanding.",
        "quality": "Chara: movable, changeable",
        "favorable_activities": "Buy automobiles, vehicles, beginning a journey or procession, travel, change of residence or job, and other major changes.",
        "sidereal_sign": "Capricorn",
        "archetypes": "#1 Most magical (sun, dom)",
        "deity": "Chandra",
        "ruler": "Moon",
        "planetary_associations": "Saturn/Uranus",
        "comments_A": "",
        "comments_B": ""
    },

    "Dhanishta": {
        "name": "Dhanishta",
        "symbol": "Drum – Star of Symphony",
        "shakti": "The power to give fame and abundance.",
        "essence": "Hearing the music of infinite possibility.",
        "quality": "Chara: movable, changeable",
        "favorable_activities": "Buy automobiles, vehicles, beginning a journey or procession, travel, change of residence or job, and other major changes.",
        "sidereal_sign": "Capricorn/Aquarius",
        "archetypes": "Allegedly \"cursed by fame & beauty\" but I think some just have fame & beauty (clearly not a lot - there aren't a lot of Dhanishtas in the public eye) - and some of them are cursed by it, naturally, but certainly not all. Also least likely to serial kill (asc). Most famous Dhan stels are in humanitarian work. More represented than average playing werewolves in films",
        "deity": "Mangal",
        "ruler": "Mars",
        "planetary_associations": "Saturn/Uranus/Neptune/Jupiter",
        "comments_A": "",
        "comments_B": ""
    },

    "Shatabhisha": {
        "name": "Shatabhisha",
        "symbol": "Circle – Veiling Star",
        "shakti": "The power of healing and secrets.",
        "essence": "Cloaking life’s miracles in mystery.",
        "quality": "Chara: movable, changeable",
        "favorable_activities": "Buy automobiles, vehicles, beginning a journey or procession, travel, change of residence or job, and other major changes.",
        "sidereal_sign": "Aquarius",
        "archetypes": "The Inventor; Science & Art; Comedian (moon). Most creative.",
        "deity": "Rahu",
        "ruler": "Rahu",
        "planetary_associations": "Neptune/Jupiter",
        "comments_A": "",
        "comments_B": ""
    },

    "Purva Bhadrapada": {
        "name": "Purva Bhadrapada",
        "symbol": "Head of Bed – Blessed Foot – Scorching Star",
        "shakti": "The power of breathing spiritual fire.",
        "essence": "Rising from the ashes to awaken.",
        "quality": "Ugra: fierce, intense, forceful",
        "favorable_activities": "Performing destructive deeds such as demolishing, poisoning, setting fire, and confronting enemies.",
        "sidereal_sign": "Aquarius/Pisces",
        "archetypes": "Kali the Destroyer; serial killer & MMA (moon). #4 occultist (dom). Femme fatales. Sometimes found starring in ugly duckling glow-up plots (#4th most likely). Outsiders. Voted least likely to deny their boundless primal urges. :-P",
        "deity": "Guru",
        "ruler": "Jupiter",
        "planetary_associations": "Neptune/Jupiter",
        "comments_A": "",
        "comments_B": ""
    },

    "Uttara Bhadrapada": {
        "name": "Uttara Bhadrapada",
        "symbol": "Foot of Bed – Blessed Foot – Warrior Star",
        "shakti": "The power to bring cosmic rain.",
        "essence": "Surrendering to the flow of spiritual waters.",
        "quality": "Sthira: fixed, stable",
        "favorable_activities": "Build homes, plant trees, purchase property, lay a foundation, and buying agricultural property.",
        "sidereal_sign": "Pisces",
        "archetypes": "Cinderella (Rags to Riches). Absolutely no millionaires/billionaires (moon). Height of male comeraderie. Andrew Tate / Man's Man, often hates women.",
        "deity": "Shani",
        "ruler": "Saturn",
        "planetary_associations": "Neptune/Jupiter/Mars",
        "comments_A": "",
        "comments_B": ""
    },

    "Revati": {
        "name": "Revati",
        "symbol": "Drum – Star of Wealth",
        "shakti": "The power to nourish and transcend.",
        "essence": "Protecting and guiding a soul home.",
        "quality": "Mridu: soft, gentle, yielding",
        "favorable_activities": "Learn music, dance, make art and get married. They are also ideal for the enjoyment of pleasures, making new friends, and wearing new clothes.",
        "sidereal_sign": "Pisces",
        "archetypes": "Fish face, nepo babies",
        "deity": "Budh",
        "ruler": "Mercury",
        "planetary_associations": "Mars",
        "comments_A": "",
        "comments_B": ""
    }
}


PLANET_GLYPHS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Chiron": "⚷",
    "Ceres": "⚳",
    "Pallas": "⚴",
    "Juno": "⚵",
    "Vesta": "⚶",
    "Rahu": "☊",
    "Ketu": "☋",
    "Lilith": "⚸",
    "Part of Fortune": "⊗",
    "AS": "AS",
    "MC": "MC",
    "DS": "DS",
    "IC": "IC",
}

SYNASTRY_PAIR_WEIGHTS = {
    ("Sun", "Moon"): 10.0,
    ("Moon", "Moon"): 9.5,
    ("Venus", "Mars"): 9.0,
    ("Venus", "Venus"): 8.5,
    ("Sun", "Venus"): 8.0,
    ("Moon", "Venus"): 8.0,
    ("Mercury", "Mercury"): 7.5,
    ("Saturn", "Sun"): 8.5,
    ("Saturn", "Moon"): 9.0,
    ("Saturn", "Venus"): 8.5,
    ("Mars", "Mars"): 7.0,
    ("Pluto", "Venus"): 6.5,
    ("Uranus", "Moon"): 6.0,
}

# composite_natal_relevance = (relevance_A[planetA] + relevance_B[planetB]) / 2

SYNASTRY_AXES = {
    "emotional harmony",
    "romance",
    "sexiness",
    "communication",
    "stability",
    "friction",
    "obsession & intensity",
    "domestic compatibility",
    "overall",
}


# contact_score = [
#     SYNASTRY_PAIR_WEIGHTS
#     * aspect_weight
#     * orb_factor
#     * composite_natal_relevance #the weight of each planet from each chart
#     * directional_receptivity
#     * repetition_bonus
# ]

SIGN_KEYWORDS_CANONICAL = {
    "aries": {
        "function": "starts",
        "adverbs": [
            "directly",
            "impatiently",
            "boldly",
            "competitively",
            "impulsively",
        ],
        "talents": [
            "initiating action before consensus forms",
            "forcing movement where others stall out",
            "deciding under pressure without hand-wringing",
            "taking risks other signs keep theorizing about",
            "bouncing back fast after embarrassment, failure, or conflict",
        ],
        "challenges": [
            "creating avoidable messes through haste",
            "treating delay like disrespect",
            "starting on adrenaline and abandoning on boredom",
            "picking fights just to feel motion",
            "confusing nerve with competence",
        ],
        "greatest_fears": [
            "being blocked, bossed, or slowed by weaker people",
            "looking hesitant",
            "having to wait on consensus",
            "feeling powerless in real time",
        ],
        "motivations": [
            "first access",
            "freedom to act without permission",
            "testing themselves against resistance",
            "proving they can move before others even wake up",
        ],
    },

    "taurus": {
        "function": "sustains",
        "adverbs": [
            "steadily",
            "stubbornly",
            "deliberately",
            "sensually",
            "possessively",
        ],
        "talents": [
            "stabilizing what more restless signs destabilize",
            "building value slowly and keeping it",
            "judging quality through direct material reality rather than hype",
            "enduring discomfort without theatricality",
            "making repetition productive instead of soul-killing",
        ],
        "challenges": [
            "digging in long after common sense has left the room",
            "mistaking inertia for wisdom",
            "becoming territorial about things, routines, and people",
            "refusing necessary change because comfort has seniority",
            "going inert when pressured",
        ],
        "greatest_fears": [
            "sudden instability",
            "being rushed into bad decisions",
            "losing control of money, body, or home",
            "dependence on people who are inconsistent",
        ],
        "motivations": [
            "security that is tangible, not conceptual",
            "comfort with permanence",
            "ownership",
            "proving that what lasts beats what merely dazzles",
        ],
    },

    "gemini": {
        "function": "connects",
        "adverbs": [
            "quickly",
            "restlessly",
            "cleverly",
            "verbally",
            "adaptably",
        ],
        "talents": [
            "linking facts before slower minds notice the pattern",
            "switching tone, subject, and audience without strain",
            "collecting usable information at high speed",
            "making complexity portable through language",
            "keeping several possibilities alive at once",
        ],
        "challenges": [
            "talking around commitment until the subject dies",
            "mistaking fluency for depth",
            "scattering attention across too many inputs",
            "staying mobile so nobody can pin them down",
            "using wit to dodge seriousness",
        ],
        "greatest_fears": [
            "mental stagnation",
            "being trapped in one role or one answer",
            "silence with no stimulation",
            "having to live inside a single rigid framework",
        ],
        "motivations": [
            "novelty",
            "access to information",
            "mental agility",
            "the freedom to compare, classify, and keep moving",
        ],
    },

    "cancer": {
        "function": "protects",
        "adverbs": [
            "guardedly",
            "tenaciously",
            "privately",
            "emotionally",
            "defensively",
        ],
        "talents": [
            "detecting shifts in emotional climate before anyone names them",
            "creating shelter, loyalty, and continuity",
            "remembering what matters to people when they are exposed or distressed",
            "binding others through care, history, and belonging",
            "protecting what is theirs with remarkable persistence",
        ],
        "challenges": [
            "using retreat, guilt, or mood as indirect control",
            "treating old attachments as sacred even when they have expired",
            "becoming prickly when plain speech would solve the issue",
            "confusing protectiveness with ownership",
            "letting memory rule over present evidence",
        ],
        "greatest_fears": [
            "exposure without cover",
            "rejection by those they fed, helped, or defended",
            "emotional homelessness",
            "having their attachments dismissed as weakness",
        ],
        "motivations": [
            "safety",
            "belonging",
            "continuity of bond and home",
            "the right to keep what they love from intrusion",
        ],
    },

    "leo": {
        "function": "radiates",
        "adverbs": [
            "proudly",
            "dramatically",
            "warmly",
            "visibly",
            "commandingly",
        ],
        "talents": [
            "organizing attention around themselves without begging for it",
            "leading through confidence, style, and personal force",
            "animating a room through warmth and theatrical conviction",
            "making creative output unmistakably personal",
            "giving others courage through open-hearted presence",
        ],
        "challenges": [
            "turning sulky when they are not appreciated enough",
            "taking ordinary neglect as a moral offense",
            "becoming vain, bossy, or embarrassingly approval-hungry",
            "confusing generosity with entitlement to the center",
            "performing strength instead of admitting hurt",
        ],
        "greatest_fears": [
            "humiliation",
            "irrelevance",
            "being treated as ordinary after giving everything full voltage",
            "offering loyalty and getting indifference back",
        ],
        "motivations": [
            "recognition",
            "creative self-expression",
            "honor",
            "being loved for a visible, undeniable personal identity",
        ],
    },

    "virgo": {
        "function": "refines",
        "adverbs": [
            "precisely",
            "methodically",
            "critically",
            "usefully",
            "fastidiously",
        ],
        "talents": [
            "detecting error, waste, slop, and inconsistency with irritating accuracy",
            "improving systems through small exact corrections",
            "separating what is useful from what is decorative nonsense",
            "translating vague goals into workable procedure",
            "serving through competence instead of noise",
        ],
        "challenges": [
            "becoming impossible to satisfy",
            "editing life to death",
            "treating anxiety as responsibility",
            "reducing people to flaws, habits, and maintenance issues",
            "stalling action because the standard keeps crawling upward",
        ],
        "greatest_fears": [
            "being sloppy, unprepared, or unnecessary",
            "causing preventable failure",
            "loss of control over meaningful details",
            "disorder that could have been fixed earlier",
        ],
        "motivations": [
            "functional order",
            "competence",
            "clean execution",
            "the relief of knowing nothing obvious has been neglected",
        ],
    },

    "libra": {
        "function": "balances",
        "adverbs": [
            "gracefully",
            "relationally",
            "diplomatically",
            "measuredly",
            "indecisively",
        ],
        "talents": [
            "judging proportion, fairness, and tone with sharp social accuracy",
            "making opposing sides legible to each other",
            "reducing friction through wording, timing, and style",
            "understanding that presentation changes outcomes",
            "creating cooperation where cruder signs would just escalate",
        ],
        "challenges": [
            "delaying decisions until the choice has gone stale",
            "sacrificing conviction to keep things pretty",
            "outsourcing judgment to anticipated reactions",
            "using charm as a substitute for honesty",
            "preferring elegance over clarity when the two conflict",
        ],
        "greatest_fears": [
            "social ugliness",
            "being cast as unreasonable or undesirable",
            "direct conflict with no graceful exit",
            "making the wrong choice and having to live with it publicly",
        ],
        "motivations": [
            "mutuality",
            "equilibrium",
            "social legitimacy",
            "being met halfway instead of dragged into brute contests",
        ],
    },

    "scorpio": {
        "function": "penetrates",
        "adverbs": [
            "intensely",
            "secretively",
            "strategically",
            "obsessively",
            "unflinchingly",
        ],
        "talents": [
            "reading hidden motives and pressure points with unnerving accuracy",
            "staying present in taboo, crisis, and high-stakes conditions",
            "committing completely when others stay half-invested",
            "operating well under secrecy, depth, and psychological complexity",
            "forcing contact with what others prefer to keep buried",
        ],
        "challenges": [
            "assuming rot beneath every surface",
            "testing loyalty until the relationship becomes a laboratory",
            "preferring control over trust",
            "holding grudges like treasured property",
            "making intensity the price of admission for everything",
        ],
        "greatest_fears": [
            "betrayal after total investment",
            "loss of control in intimate or exposed conditions",
            "being truly known by the wrong person",
            "superficiality masking corruption underneath",
        ],
        "motivations": [
            "truth under pressure",
            "absolute loyalty",
            "power through psychological precision",
            "the need to know what is really going on, not the sanitized version",
        ],
    },

    "sagittarius": {
        "function": "expands",
        "adverbs": [
            "freely",
            "bluntly",
            "enthusiastically",
            "speculatively",
            "restlessly",
        ],
        "talents": [
            "extracting broad meaning from scattered experience",
            "moving toward distant aims with confidence and appetite",
            "teaching through vision rather than technical fussiness",
            "lifting morale through candor and scale",
            "spotting how a local issue fits into a larger belief structure",
        ],
        "challenges": [
            "overshooting the facts because the bigger story feels better",
            "becoming preachy, reckless, or intellectually lazy",
            "treating precision as petty",
            "assuming conviction excuses sloppiness",
            "running from limits as though adulthood were a clerical error",
        ],
        "greatest_fears": [
            "confinement",
            "small-minded routine",
            "cynicism",
            "a life with no horizon beyond immediate obligation",
        ],
        "motivations": [
            "freedom",
            "discovery",
            "belief with range",
            "the right to chase meaning beyond what is already mapped",
        ],
    },

    "capricorn": {
        "function": "consolidates",
        "adverbs": [
            "seriously",
            "strategically",
            "disciplinedly",
            "patiently",
            "unsentimentally",
        ],
        "talents": [
            "working within real limits instead of whining about them",
            "building authority through discipline and timing",
            "turning ambition into durable structure",
            "assuming responsibility when consequences are real",
            "valuing what survives fashion, mood, and fantasy",
        ],
        "challenges": [
            "treating warmth like a luxury item",
            "equating worth with output, rank, or usefulness",
            "defaulting to severity because softness looks risky",
            "staying in barren conditions out of pride",
            "confusing control with maturity",
        ],
        "greatest_fears": [
            "public failure",
            "dependency",
            "wasted effort",
            "loss of status, structure, or command",
        ],
        "motivations": [
            "mastery",
            "credibility",
            "earned authority",
            "building something solid enough to outlast weaker people and passing moods",
        ],
    },

    "aquarius": {
        "function": "differentiates",
        "adverbs": [
            "independently",
            "coolly",
            "abstractly",
            "contrarily",
            "systematically",
        ],
        "talents": [
            "seeing systems from outside their usual assumptions",
            "thinking against group pressure without immediate panic",
            "organizing around principles instead of personal favoritism",
            "spotting future patterns before they become obvious",
            "holding an intellectual line when convention is plainly irrational",
        ],
        "challenges": [
            "mistaking emotional distance for objectivity",
            "becoming contrary on autopilot",
            "using theory to dodge ordinary human obligation",
            "treating personal warmth like a design flaw",
            "hardening into dogma while congratulating themselves for independence",
        ],
        "greatest_fears": [
            "being absorbed into the herd",
            "coercive conformity",
            "dependence on approval",
            "closed systems that punish experiment",
        ],
        "motivations": [
            "freedom of thought",
            "reform",
            "participation in a larger pattern",
            "living by chosen principles instead of inherited social scripts",
        ],
    },

    "pisces": {
        "function": "dissolves",
        "adverbs": [
            "fluidly",
            "softly",
            "imaginatively",
            "porously",
            "evasively",
        ],
        "talents": [
            "perceiving subtle atmospheres and symbolic undertones",
            "softening hard boundaries so empathy, art, and faith can function",
            "inhabiting emotional ambiguity without immediate judgment",
            "translating longing, sorrow, and transcendence into image or devotion",
            "adapting where rigid definitions fail",
        ],
        "challenges": [
            "leaking boundaries until there is barely a self left to defend",
            "escaping into fantasy, passivity, or denial",
            "idealizing what should be inspected soberly",
            "avoiding confrontation because blunt reality feels vulgar",
            "drifting when structure is non-negotiable",
        ],
        "greatest_fears": [
            "spiritual desolation",
            "a world with no mercy, mystery, or symbolic depth",
            "harsh separation from what they yearn for",
            "being trapped in conditions too rigid for imagination or surrender",
        ],
        "motivations": [
            "union",
            "transcendence",
            "compassion",
            "release from hard separateness, category, and ego rigidity",
        ],
    },
}

SIGN_KEYWORDS = {
    "aries": {
        "best": [
            "charming","perceptive", "quick", "adaptive", "funny", "analytical", "pragmatic", "sharp",
            "flexible", "direct", "aware", "improvisational", "dry", "observant", "skeptical",
            "wry", "vigilant", "alert", "mobile", "ironic",
        ],
        "worst": [
            "rigid (in principle)","jittery", "scattered", "reactive", "suspicious", "snide", "evasive",
            "cynical", "unfocused", "restless", "sarcastic", "disjointed", "critical", "uneasy",
        ],
        "best_adverbs": [
            "sharply", "flexibly", "directly", "with awareness", "improvisationally", "dryly","sardonically",
            "observantly", "skeptically", "wryly", "vigilantly", "alertly", "mobily", "ironically",
        ],
        "worst_adverbs": [
            "jitterily", "scatteredly", "reactively", "suspiciously", "snidely", 
            "evasively", "cynically", "without focus", "restlessly", "sarcastically",
            "disjointedly", "critically", "uneasily",
        ],
        "profile":"feron",
        "verbs": ["questioning", "criticizing", "redirecting", "pivoting", "undermining via", "qualifying", "scanning", "adjusting", "challenging", "comparing", "signaling", "reacting",
        ],
        "core":"Projects normalcy. Beneath that, a strict internal code that rarely budges.",
        "strategy":"Social fluency masking private rigor. Reads as agreeable, but has fixed beliefs.",
        "function":"Public decency avatar. A good host, a reluctant soldier. Loyalty isn't loud—but it is absolute.",
        "behavior": ["Quick read of the room.","Doesn’t trust easy.","Always adjusting for control or clarity.","Knows how to pivot mid-sentence.",],
        "season": "vernal",
        "fertility": None,
        "bicorporeal": False,
        "mute": False,
        "humane": False,
        "bestial": False,
        "feral": False,
        "quadrupedian": True,
        "famous_casestudies":[],
        "deity":{"Sekhmet"},
        "house":1,
    },

    "taurus": {
        "best": [
            "charismatic", "steady", "loyal", "embodied", "grounded", "durable", "magnetic",
            "protective", "resolved", "contained", "deep", "faithful", "seductive", "symbolic",
            "private", "still","traditional",
        ],
        "worst": [
            "inert", "withholding", "rigid", "repressed", "avoidant", "noncommittal",
            "emotionally distant", "sexually flattened", "passive-aggressive", "static",
            "unreadable", "cold", "inertial", "withheld", "resistant", "exiling",
        ],
        "best_adverbs": [
            "charismatically", "steadily", "loyally", "in an embodied way", "in a grounded way",
            "durably", "magnetically", "protectively", "resolvedly", "in a contained way",
            "deeply", "faithfully", "seductively", "symbolically", "privately", "still",
        ],
        "worst_adverbs": [
            "inertly", "in a withholding way", "rigidly", "repressively", "avoidantly",
            "noncommittally", "emotionally distantly", "in a sexually flattened way",
            "passive-aggressively", "statically", "unreadably", "coldly", "inertially",
            "in a withheld way", "resistantly", "in an exiling way",
        ],
        "profile":"urokh",
        "verbs": ["seducing", "provoking", "withholding", "resisting", "excommunicating", "steading", "holds onto", "embodying", "mythologizing", "protecting", "attracting", "anchoring",],"core":"",
        "core":"Tribal continuity. Embodied inheritance. Will not bend faster than the tribe.",
        "strategy":"Resists change by being the form that refuses to yield. Carries weight, not spark.",
        "function":"Boulder in the stream. The world must move around them. What they are is not up for reinvention.",
        "behavior": ["Archetypal authority.","Walks with ancestral gravity.","Doesn’t change shape to fit the room.","Others bend around them.","They trigger reaction just by holding steady.",],
        "season": "vernal",
        "fertility": None,
        "bicorporeal": False,
        "mute": False,
        "humane": False,
        "bestial": True,
        "feral": False,
        "quadrupedian": True,
        "famous_casestudies":[],
        "deity":{"Enki"},
        "house":2,
    },

    "gemini": {
        "best": [
            "likable", "clever", "charming", "funny", "tactful", "spontaneous",
            "relatable", "light", "socially fluent", "self-aware", "pragmatic", "pliable",
            "context-sensitive","nonlinear","ambiguous","fluid","adaptable","slick","crafty","cunning",
        ],
        "worst": [
            "evasive", "slippery", "vague", "inauthentic", "ingratiating", "disingenuous",
            "flaky", "surface-level", "opportunistic", "manipulative", "avoidant", "two-faced",
            "edited", "masked", "indirect",
        ],
        "best_adverbs": [
            "likably", "cleverly", "adaptively", "charmingly", "funnily", "tactfully",
            "spontaneously", "relatably", "lightly", "with social fluency", "with self-awareness",
            "pragmatically", "pliably", "in a context-sensitive way",
        ],
        "worst_adverbs": [
            "evasively", "slipperily", "vaguely", "inauthentically", "ingratiatingly",
            "disingenuously", "flakily", "in a surface-level way", "opportunistically",
            "manipulatively", "avoidantly", "in a two-faced way", "in an edited way",
            "in a masked way", "indirectly",
        ],
        "profile":"cleave",
        "verbs": ["curating narrative via", "impersonating", "joking about", "strategically re/framing", "evading", "adapting to", "editing", "charming", "cleverly navigating", "mimicking", "bypassing",],
        "core":"Adaptive, ambiguous, nonlinear. Charisma through fluidity.",
        "strategy":"Withholds certainty, uses flexibility as power. Navigates contradiction without flinching. Translates between worlds.",
        "function":"Social shapeshifter—not for approval, but for autonomy. Knows where to bend and when not to.",
        "behavior": ["Feels out the temperature before speaking.","Blends, entertains, deflects.","You rarely get the whole picture—and that’s the point.",],
        "season": "vernal",
        "fertility": "barren",
        "bicorporeal": True,
        "mute": False,
        "humane": True,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Hermes"},
        "house":3,
    },

    "cancer": {
        "best": [
            "expressive", "soft", "romantic", "imaginative", "emotionally open", "fluid","hoarding",
            "adaptive", "sensitive", "intuitive", "tender", "dreamy", "porous",
            "yearning", "emotional", "adaptable","softly resilient","empathic","nostalgic","sentimental",
        ],
        "worst": [
            "leaky", "unmoored", "melodramatic", "needy", "over-identifying", "escapist",
            "reactive", "self-absorbed", "unstructured", "nostalgic to a fault", "inconsistent",
            "disordered", "unresolved", "impressionable", "splintered",
        ],
        "best_adverbs": [
            "expressively", "softly", "romantically", "imaginatively", "with emotional openness",
            "fluidly", "adaptively", "sensitively", "intuitively", "artistically", "tenderly",
            "dreamily", "porously", "with yearning", "emotionally", "adaptably",
        ],
        "worst_adverbs": [
            "leakily", "in an unmoored way", "melodramatically", "needily",
            "in an over-identifying way", "escapistically", "reactively",
            "in a self-absorbed way", "unstructuredly", "nostalgically to a fault",
            "inconsistently", "in a disordered way", "in an unresolved way", "impressionably",
            "in a splintered way",
        ],
        "profile":"karth",
        "verbs": ["performing with", "reflecting", "echoing", "adapting with", "yearning for", "clinging to", "reinventing", "narrating", "harmonizing", "flattening", "pleasing", "grieving",],
        "core":"Emotional sincerity filtered through constructed style. Adaptable but sacred.",
        "strategy":" Stylized devotion. Expresses grief, love, and longing with curated impact.",
        "function":"Converts emotional density into ritual. Craves meaning, not spotlight.",
        "behavior": ["Absorbs the mood of the room.","Rewrites the story to feel something again.","Deeply attached to image and memory.",],
        "season": "aestival",
        "fertility": "fruitful",
        "bicorporeal": False,
        "mute": True,
        "humane": False,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Innana","Demeter"},
        "house":4,

    },

    "leo": {
        "best": [
            "bold", "powerful", "expressive", "commanding", "passionate", "dynamic", "brave",
            "visible", "intense", "determined", "daring", "assertive", "driven", "timed",
        ],
        "worst": [
            "performative", "egoic", "self-obsessed", "volatile", "emotionally manipulative",
            "loud", "prideful", "image-fixated", "theatrical", "erratic", "attention-hungry",
            "domineering", "reactive", "image-conscious", "impulsive", "restless", "centralizing",
        ],
        "best_adverbs": [
            "boldly", "powerfully", "expressively", "commandingly", "passionately",
            "dynamically", "bravely", "visibly", "intensely", "determinedly", "daringly",
            "assertively", "in a driven way", "with timing",
        ],
        "worst_adverbs": [
            "performatively", "egoically", "in a self-obsessed way", "in a volatile way",
            "emotionally manipulatively", "loudly", "pridefully", "in an image-fixated way",
            "theatrically", "erratically", "in an attention-hungry way", "domineeringly",
            "reactively", "in an image-conscious way", "impulsively", "restlessly",
            "in a centralizing way",
        ],
        "profile":"ardent",
        "verbs": ["broadcasting", "dominating", "escalating", "claiming", "performing", "flexing with", "dramatizing", "rebounding", "flaunting", "posturing", "insisting",],
        "core":"Spotlight-hungry. Pain becomes performance, identity becomes saga.",
        "strategy":"Ego-first, body-forward, always building the next reveal.",
        "function":"Main character in a self-written hero arc. Controls timing, tone, and triumph.",
        "behavior": ["Converts suffering into myth.","Needs to be seen, but only when the scene is right.","Doesn’t want understanding—wants the win, the arc, the shot.","Needs audience to feel real.","Life becomes theater, even offstage."],
        "season": "aestival",
        "fertility": "barren",
        "bicorporeal": False,
        "mute": False,
        "humane": False,
        "bestial": False,
        "feral": True,
        "quadrupedian": True,
        "famous_casestudies":[],
        "deity":{"Ra","Zeus"},
        "house":5,
    },

    "virgo": {
        "best": [
            "composed", "graceful", "caring", "dignified", "supportive", "strong", "thoughtful",
            "refined", "nurturing", "private", "elegant", "reliable", "stable", "warm",
            "self-contained","steady","skilled","quietly masterful",
        ],
        "worst": [
            "repressed", "martyrish", "avoidant", "emotionally shut down", "detached",
            "self-silencing", "bitter", "drained", "stiff", "inaccessible", "smothering",
            "brittle", "exhausted", "hurt",
        ],
        "best_adverbs": [
            "composedly", "gracefully", "caringly", "dignifiedly", "supportively", "strongly",
            "thoughtfully", "in a refined way", "nurturingly", "privately", "elegantly",
            "reliably", "stably", "warmly", "in a self-contained way",
        ],
        "worst_adverbs": [
            "repressively", "martyrishly", "avoidantly", "in an emotionally shut down way",
            "detachedly", "in a self-silencing way", "bitterly", "in a drained way", "stiffly",
            "inaccessibly", "smotheringly", "in a brittle way", "exhaustedly", "in a hurt way",
        ],
        "profile":"saevra",
        "verbs": ["soothing", "withholding", "stabilizing", "managing", "beautifying", "masking", "supporting", "concealing", "enduring", "nurturing", "building", "disconnecting",],
        "core":"Quiet mastery. Stable presence. Values depth over display.",
        "strategy":"Moves with care, precision, and internal discipline—without broadcasting.",
        "function":"Shows what excellence looks like when you don’t need the spotlight. Makes restraint feel grounded, not passive.",
        "behavior": ["Integrates private values with public function.","Carries their own pain without externalizing it.","Makes others feel safe even when they’re falling apart.","Stillness with history behind it.","Can become overly self-contained.","Struggles to externalize need."],
        "season": "aestival",
        "fertility": "barren",
        "bicorporeal": False,
        "mute": False,
        "humane": True,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Vulkan","Hestia"},
        "house":6,
    },

    "libra": {
        "best": [
            "elegant", "competent", "composed", "organized", "intelligent", "intentional",
            "stable", "strategic", "aesthetically controlled", "dependable", "discerning",
            "polished", "aesthetic", "assertive", "curated", "responsible", "stylized",
            "balanced", "executive", "deliberate",
        ],
        "worst": [
            "cold", "distant", "calculating", "uptight", "emotionally flat", "overmanaged",
            "image-obsessed", "inaccessible", "robotic", "inauthentic", "perfectionistic",
            "rigid",
        ],
        "best_adverbs": [
            "elegantly", "competently", "composedly", "in an organized way", "intelligently",
            "intentionally", "stably", "strategically", "in an aesthetically controlled way",
            "dependably", "discerningly", "in a polished way", "aesthetically", "assertively",
            "in a curated way", "responsibly", "in a stylized way", "in a balanced way",
            "executively", "deliberately",
        ],
        "worst_adverbs": [
            "coldly", "distantly", "calculatingly", "in an uptight way", "in an emotionally flat way",
            "in an overmanaged way", "in an image-obsessed way", "inaccessibly", "robotically",
            "inauthentically", "perfectionistically", "rigidly",
        ],
        "profile":"kesmet",
        "verbs": ["controling", "formating", "refining", "directing", "calculating", "curating", "stylizing", "asserting", "maneuvering", "correcting", "modulating", "maintaining",],
        "core":"Identity through structure. Adult-in-the-room energy. Controls reality by refining it. Overmanaged persona. Rejects mess. Enforces systems that may no longer serve.",
        "strategy":"Orchestrates style, tone, and consequence with sharp calibration.",
        "function":"Keeps the room functional. Enforces standards. Aesthetic is justice in disguise.",
        "behavior": ["Creates order & abides by protocol.","Identity through function.","They shape the frame, manage the output, and refine the tone.","Not disordered—calculated.",],
        "season": "autumnal",
        "fertility": None,
        "bicorporeal": False,
        "mute": False,
        "humane": True,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Anansi"},
        "house":7,
    },

    "scorpio": {
        "best": [
            "introspective", "thoughtful", "private", "layered", "gentle", "wise", "reflective","hunch-driven",
            "creative", "deep", "slow-burning", "internal", "emotionally nuanced", "quiet","intuitive",
            "internally-paced", "self-contained","mythically resonant","deeply-rooted & unshakeable",
        ],
        "worst": [
            "withdrawn", "evasive", "depressive", "passive", "emotionally inaccessible",
            "ambiguous", "numb", "obscure", "vague", "avoidant", "lethargic", "murky",
            "isolative", "shadowed","mysterious","enigmatic","illegible",
        ],
        "best_adverbs": [
            "introspectively", "thoughtfully", "privately", "in a layered way", "gently",
            "wisely", "reflectively", "creatively", "deeply", "in a slow-burning way",
            "internally", "in an emotionally nuanced way", "quietly", "in an internally-paced way",
            "in a self-contained way",
        ],
        "worst_adverbs": [
            "in a withdrawn way", "evasively", "depressively", "passively",
            "in an emotionally inaccessible way", "ambiguously", "numbly", "obscurely",
            "vaguely", "avoidantly", "lethargically", "murkily", "isolatively",
            "in a shadowed way",
        ],
        "profile":"nether",
        "verbs": ["observing", "withdrawing from", "reflecting", "diffusing", "resonating", "wandering the edge of", "absorbing", "quieting", "disarming", "veiling", "softening", "holding onto",],
        "core":"Internal sovereignty. Selective interface. Moves through contradiction by staying whole.",
        "strategy":"Doesn’t flinch, doesn’t explain. Retains essence through silence or surrealism. Can become illegible. Withdraws signal rather than engaging in conflict.",
        "function":"Feels like absence, but is presence on its own terms. They are never yours to decode.",
        "behavior": ["Carries depth but doesn’t hand it over.","Withdraws more than explains.","You feel more than you know.",],
        "season": "autumnal",
        "fertility": "fruitful",
        "bicorporeal": False,
        "mute": True,
        "humane": False,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Hecate"},
        "house":8,
    },

    "sagittarius": {
        "best": [
            "energetic", "raw","imaginative", "magnetic", "disruptive", "electric", "emotionally rich",
            "alive", "creative", "free-spirited", "intense", "original", "surprising",
            "expressive", "rebellious", "generative", "charismatic", "self-redefining",
        ],
        "worst": [
            "disordered", "unstable", "self-destructive", "impulsive", "volatile","reactive",
            "attention-seeking", "reckless", "overexposed", "inconsistent", "messy",
            "ungrounded", "dramatic", "explosive", "provocative", "fractured", "combustive",
        ],
        "best_adverbs": [
            "energetically", "imaginatively", "magnetically", "disruptively", "electrically",
            "in an emotionally rich way", "vivaciously", "creatively", "in a free-spirited way",
            "intensely", "originally", "surprisingly", "expressively", "rebelliously",
            "generatively", "charismatically", "in a self-redefining way","aggressively",
        ],
        "worst_adverbs": [
            "in a disordered way", "unstably", "in a self-destructive way", "impulsively",
            "in a volatile way", "in an attention-seeking way", "recklessly",
            "in an overexposed way", "inconsistently", "messily", "in an ungrounded way",
            "dramatically", "explosively", "provocatively", "in a fractured way", "combustively",
        ],
        "profile":"wxnder",
        "verbs": ["distorting", "challenging", "combusting", "reinventing", "disrupting", "electrifying", "exposing", "bleeding", "reclaiming", "detonating", "amplifying", "iconifying",],
        "core":"Drives toward freedom. Reinvents self to stay uncaged.",
        "strategy":"Identity through transformation. Expresses tension by breaking molds.",
        "function":"Must stay free. Tension magnet, not by intention—but because their aliveness offends the script. Can burn bridges to escape commitment. Emotionally catalytic.",
        "behavior": ["Can’t be held still.","Shifts shape with emotion and time.",],
        "season": "autumnal",
        "fertility": None,
        "bicorporeal": True,
        "mute": False,
        "humane": False,
        "bestial": False,
        "feral": True,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Kali","Pan","Dionysis"},
        "house":9,
    },

    "capricorn": {
        "best": [
            "warm", "grounded", "insightful", "emotionally intelligent", "stable", "kind","rugged","self-effacing","modest",
            "centering", "attuned", "wise", "patient", "generous", "connective", "measured","unshakeable",
            "thoughtful", "perceptive", "balancing", "consistent", "observing", "orienting","dignified",
            "emotionally literate", "reassuring","traditional","in-some-ways surprisingly conservative",
        ],
        "worst": [
            "overly accommodating", "invisible", "overly deferential", "bland", "emotionally exhausted","burnt out",
        ],
        "best_adverbs": [
            "warmly", "in a grounded way", "insightfully", "in an emotionally intelligent way",
            "stably", "kindly", "in a centering way", "with attunement", "wisely", "patiently",
            "generously", "in a connective way", "measuredly", "thoughtfully", "perceptively",
            "in a balancing way", "consistently", "observingly", "in an orienting way",
            "in an emotionally literate way", "reassuringly",
        ],
        "worst_adverbs": [
            "passively", "in an overly accommodating way", "in a conflict-avoidant way",
            "in an enabling way", "unassertively", "indirectly", "indecisively", "invisibly",
            "in an overly deferential way", "dependently", "blandly", "in an emotionally exhausted way",
        ],
        "profile":"dalmure",
        "verbs": ["orchestrating", "sequencing", "tracking", "moderating", "preserving", "pacing", "aligning with", "archiving", "honoring", "eulogizing","respecting","weathering","carefully timing action upon", "containing the consequences of",],
        "core":"Social engineer. Designs emotional space without starring in the show.",
        "strategy":"Invisible rhythm keeper. Makes the system work without asking for credit.",
        "function":"Tracks collective tempo. Holds others together by staying slightly adjacent.",
        "behavior": ["The gravity in the room.","Doesn’t lead loud, but people follow anyway.","Anchors others by tracking the pulse.","Understates needs.","Can become ghost director of their own life.","Calibrates timing perfectly.","Stabilizes others.","Creates legacy without fanfare.",],
        "season": "hyemal",
        "fertility": None,
        "bicorporeal": False,
        "mute": False,
        "humane": False,
        "bestial": True,
        "feral": False,
        "quadrupedian": True,
        "famous_casestudies":[],
        "deity":{"Brigid","Hank Hill"},
        "house":10,
    },

    "aquarius": {
        "best": [
            "complex", "reflective", "enigmatic", "thoughtful", "layered", "analytical",
            "symbolic", "philosophical", "composed", "deep", "intentional", "ritualized",
            "contained", "coded", "consciously structured", "interpretive", "analytic", "saturated",
        ],
        "worst": [
            "abstracted", "emotionally inaccessible", "obscure", "aloof", "grandiose",
            "overly intellectualized", "stiff", "cold", "mystified", "vague", "dissociative",
            "inert", "shrouded", "distanced",
        ],
        "best_adverbs": [
            "in a complex way", "reflectively", "enigmatically", "thoughtfully", "in a layered way",
            "analytically", "symbolically", "philosophically", "composedly", "deeply",
            "intentionally", "in a ritualized way", "in a contained way", "in a coded way",
            "in a structured way", "interpretively", "analytically",
        ],
        "worst_adverbs": [
            "in an abstracted way", "in an emotionally inaccessible way", "obscurely",
            "aloofly", "grandiosely", "in an overly intellectualized way", "stiffly", "coldly",
            "in a mystified way", "vaguely", "dissociatively", "inertly", "in a shrouded way",
            "in a distanced way",
        ],
        "profile":"fathom",
        "verbs": ["synthesizing", "encoding", "veiling", "regulating", "ritualizing", "translating", "embedding",],
        "core":"Complex scaffolding beneath calm presentation. Internal logic overrides public optics.",
        "strategy":"Emotional containment. Moves through life by systems, not spectacle.",
        "function":"The actual adult in the room—but don’t flinch if that adult appears strange. Norms are optional if they contradict structural integrity.",
        "behavior": ["Doesn’t move fast.","Builds meaning slowly, through lens and system.","You get the architecture—not the raw material.","Can become suddenly & unexpectedly opaque, instantaneously distancing self.","Prioritizes internal truth over relational clarity.","Architect of hidden order.","Unshaken by social pressure."],
        "season": "hyemal",
        "fertility": None,
        "bicorporeal": False,
        "mute": False,
        "humane": True,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Thoth"},
        "house":11,
    },

    "pisces": {
        "best": [
            "honest", "raw", "emotionally open", "vulnerable", "expressive", "confessional",
            "passionate", "intense", "unique", "brave", "authentic", "emotionally resonant",
            "unfiltered",
        ],
        "worst": [
            "unstable", "self-pitying", "impulsive", "reckless", "boundaryless", "volatile",
            "emotionally manipulative", "needy", "destructive", "obsessive",
            "disordered", "reactive", "wounded", "theatrical", "fluctuating", "erratic",
            "splintered",
        ],
        "best_adverbs": [
            "honestly", "rawly", "with emotional openness", "vulnerably", "expressively",
            "confessionally", "passionately", "intensely", "uniquely", "bravely",
            "authentically", "in an emotionally resonant way", "in an unfiltered way",
        ],
        "worst_adverbs": [
            "unstably", "in a self-pitying way", "impulsively", "recklessly", "in a boundaryless way",
            "in a volatile way", "emotionally manipulatively", "needily", "destructively",
            "obsessively", "in a disordered way", "reactively", "in a wounded way",
            "theatrically", "in a fluctuating way", "erratically", "in a splintered way",
        ],
        "profile":"hallow",
        "verbs": ["meaningfully expressing through", "eluding","slithering through","dissolving into","splintering", "overidentifying with", "emoting via", "surreally confessing via", "undercutting","inhabiting", "lashing out at", "deconstructing", "spiraling via", "reframing", "mimicking", "coping with",],
        "core":"Nervous system of the collective. Sacred contradictions.",
        "strategy":"Carries both illumination and dissonance. Resists simplicity. May implode from inner tension. Truth and distortion bleed together. Spiritually resonant. Subtly defiant. Embedded in culture’s nerve endings.",
        "function":"Cultural conductor. Feels what others won’t admit. Half priest, half disruption.",
        "behavior": ["Say too much and then pull back.","Crave an audience but recoil in equal measure.","Are always in the middle of a spiral or survival arc.",],
        "season": "hyemal",
        "fertility": "fruitful",
        "bicorporeal": True,
        "mute": True,
        "humane": False,
        "bestial": False,
        "feral": False,
        "quadrupedian": False,
        "famous_casestudies":[],
        "deity":{"Chiron","Jesus"},
        "house":12,
    },
}

# Canonicalize sign keyword keys once so all consumers can use Title Case sign labels.
SIGN_KEYWORDS = {str(sign).title(): value for sign, value in SIGN_KEYWORDS.items()}

# Example access:
# sign = "scorpio"
# one_sign_adverb = random.choice(SIGN_TRAITS[sign]["best_adverbs"])

PLANET_KEYWORDS = {
    "Sun": {
        "nouns": [
            "authority", "sovereignty", "identity", "will", "purpose", "presence",
            "leadership", "distinction", "recognition", "direction", "conviction", "visibility",
        ],
        "verbs": [
            "leading", "deciding", "expressing", "commanding", "directing", "choosing",
            "affirming", "claiming", "centering", "radiating", "authoring", "standing forth as",
        ],
        "verbsonly": [
            "leading", "deciding", "expressing", "commanding", "directing", "choosing",
            "affirming", "claiming", "centering", "radiating", "authoring", "standing forth",
        ],
        "definition1":"", #just use SIGN_KEYWORDS_CANONICAL's "talents"
        "definition2":"living", #append SIGN_KEYWORDS_CANONICAL's "adverbs" property for the sign, separated by commas in sentence form & throw in an & for the last one in the list
        "explanation":[""],
        "archetypes":[
        ],
    },
    "Moon": {
        "nouns": [
            "reactivity", "instinct", "feelings", "moods", "comfort", "needs", "memory", "care",
            "safety", "support", "familiarity", "nourishment", "recovery", "rest",
        ],
        "verbs": [
            "reacting to", "feeling", "noticing the moods of", "being nourished by", "seeking comfort from", "caring for",
            "finding familiarity in", "seeking safety through", "remembering", "settling into", "protecting", "recharging with","feeling most comfortable with","experiencing subconscious as",
        ],
        "verbsonly": [
            "reacting", "feeling", "noticing moods", "seeking comfort", "caring",
            "finding familiarity", "seeking safety", "remembering", "settling into", "protecting", "recharging",
        ],
        "definition1":"scared of", #append SIGN_KEYWORDS_CANONICAL's "greatest_fears" for the moon sign
        "definition2":"comforted by", #append SIGN_KEYWORDS_CANONICAL's "talents"
        "explanation":[""],
        "archetypes":[
        ],
    },
    "Mercury": {
        "nouns": [
            "thoughts","mental processes","words", "questions", "data", "messages", "information","language",
            "writing", "reading", "notes", "details","communication", "curiosity", "interpretation",
        ],
        "verbs": [
            "thinking of", "talking about", "asking about", "answering", "writing", "reading",
            "explaining", "learning about", "planning with", "sorting", "editing", "naming", "translating",
        ],
        "verbsonly": [
            "thinking", "talking", "asking", "answering", "writing", "reading",
            "explaining", "learning", "sorting", "editing", "naming", "translating",
        ],
        "definition1":"a lot of thought given to ", #append SIGN_KEYWORDS_CANONICAL's "motivations" property
        "definition2":"thinking", #append SIGN_KEYWORDS_CANONICAL's "adverbs"
        "explanation":[""],
        "archetypes":[
            "Hermes",
        ],
    },
    "Venus": {
        "nouns": [
            "attraction", "pleasure", "taste", "affection", "charm", "style", "beauty", #"relationships","enjoyments",
            "harmony", "preference", "connection", "romance", "appreciation", "allure", "values",
        ],
        "verbs": [
            "socializing with", "liking", "adoring", "enjoying", "connecting with", "flirting with",
            "being attracted to", "sharing with", "decorating", "appreciating", "savoring", "valuing",
            "harmonizing with", "beautifying", "making an art out of", "interpreting femininity as",
        ],
        "verbsonly": [
            "socializing", "liking", "adoring", "enjoying", "connecting", "flirting",
            "being attracted", "sharing", "decorating", "appreciating", "savoring", "valuing",
            "harmonizing", "beautifying", "making an art out of", "interpreting femininity",
        ],
        "definition1":"enamoured with people", #append SIGN_KEYWORDS_CANONICAL's "talents" 
        "definition2":"attracted to", #append SIGN_KEYWORDS_CANONICAL's "motivations" 
        "explanation":[""],
        "archetypes":[
        ],
    },
    "Mars": {
        "nouns": [
            "drive", "energy", "assertion", "action", "effort", "movement", "conflict",
            "competition", "courage", "risk", "urgency", "pursuit", "anger", "force",
        ],
        "verbs": [
            "directing energy toward", "acting on", "moving toward", "pushing against", "competing with",
            "getting fired up by", "arguing with", "pursuing", "challenging", "asserting", "building",
            "fixing", "taking risks with", "forcing the issue in", "interpreting masculinity as",
        ],
        "verbsonly": [
            "directing energy", "acting", "moving", "pushing", "competing",
            "getting fired up", "arguing", "pursuing", "challenging", "asserting", "building",
            "fixing", "taking risks", "forcing the issue", "interpreting masculinity",
        ],
        "definition1":"most compelled by", #get SIGN_KEYWORDS_CANONICAL's "motivations"
        "definition1":"made vital by", #get SIGN_KEYWORDS_CANONICAL's "motivations"
        "explanation":[""],
        "archetypes":[
        ],
    },
    "Jupiter": {
        "nouns": [
            "growth", "expansion", "learning", "teaching", "wisdom", "belief","trust", #omitted "faith" to avoid dragging church furniture into the room
            "conviction", "opportunity", "abundance", "generosity", "travel", "exploration","hope",
        ],
        "verbs": [
            "teaching", "learning from", "traveling through", "exploring", "advising", "studying",
            "publishing", "expanding", "blessing", "encouraging", "believing in", "broadening",
        ],
        "verbsonly": [
            "teaching", "learning", "traveling", "exploring", "advising", "studying",
            "publishing", "expanding", "blessing", "encouraging", "believing", "broadening",
        ],
        "definition1":"fortunate in", #append SIGN_KEYWORDS_CANONICAL's "motivations" 
        "definition2":"great at", #append SIGN_KEYWORDS_CANONICAL's "talents" 
        "explanation":[""],
        "archetypes":[
            "Santa Clause",
        ],
    },
    "Saturn": { #If you're just printing a list of keywords, you're going to want to dial back the synonyms. But as long as you're generating phrases, this is cool & keeps things spicy and varied, poetic.
        "nouns": [
            "limitations","burdens", "commitments", "duties", "responsibilities", "discipline","elders","practice","rules","institutions","orthodoxy","status quo","continuity","existing structures",
            "structure", "time", "endurance", "obligations","inertia","entropy","restrictions","bureaucracy","entrenched order","consequence","precedent","sanctioned order","accumulated dust", #dust is the residue of time, the cross we all bear, entropy incarnate
        ],
        "verbs": [
            "working on", "committing to", "reviewing", "tested by", "testing","maintaining","obligated to", #is this more 8th house? no - duty, burden, requirement, responsibility, necessity, rule-bound commitment
            "limiting", "being restricted by", "enduring", "structuring", "bearing", "delaying","practicing", #is this more 6th house?
        ],
        "verbsonly": [
            "working", "committing", "practicing", "reviewing", "testing", "maintaining",
            "limiting", "being restricted", "enduring", "structuring", "bearing", "delaying", #
        ],
        "definition1":"burdened by",  #append SIGN_KEYWORDS_CANONICAL's "challenges" 
        "definition2":"responsible for",  #append SIGN_KEYWORDS_CANONICAL's "talents" 
        "explanation": [
            "the condition under which order hardens, persists, decays and must be re-won","Saturn builds canyons and monuments, Saturn also ossifies, leaves residue and wears down. Saturn slowly moves mountains and erodes them. It's just time, bro.","The neutral reckoning of what persists, for better or worse.",
        ],
        "archetypes": [ #previously associated with Cronus (as was Saturn's structural opposite - Uranus!) but there is so much narrative drift there that the affiliation starts to collapse. Modern lore translates it essentially to Anachronism/Conservativism vs Meliorism/Progressivism (as NOTABLY distinct from "Right wing vs Left wing" - because a lot of neocon post-9/11 pundits are both Saturn & Uranus-ruled or Capricorn/Aquarius dominant).
        #The hierophant can also drift 9th-house/Jupiter/Taurus-ish depending on the symbolic system. 
            "Turtle Thomas","a tortoise","a bristlecone pine","Methuselah","ouroboros","Sisyphus","Time","Father Time", #Saturn includes both maat (order, law, continuity, obligation, structure - but unlike maat has no devotion to truth, justice or correct proportion) and isfet (order, law, continuity, obligation, structure). Saturn is the temporality that makes maat costly, fragile, and perishable, and that allows isfet to arise through neglect, rigidity, exhaustion, and decay.
        ],
    },
    "Uranus": {
        "nouns": [
            "iconoclasm", "unpredictability", "novelty", "experiments", "rebellion", "futurism","deviation","disruption",
            "pattern breaks", "innovation", "heresy", "counterculture","discontinuity","anomalies","rule challenges", 
            "eccentricity", "independence", "deviation", "liberation", "upheaval","glitches", "shocking behavior", 
        ],
        "verbs": [
            "disrupting", "experimenting", "improvising", "innovating","disrupting the status quo of",
            "challenging rules of", "surprising", "deviating from", "liberating", "destabilizing",
            "electrifying", "refusing","defying norms of",
        ],
        "verbsonly": [
            "disrupting", "breaking patterns", "experimenting", "improvising", "innovating",
            "defying", "surprising", "deviating", "liberating", "destabilizing",
            "electrifying", "refusing",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[""],
        "archetypes":[
            "a live wire",
        ],
    },
    "Neptune": {
        "nouns": [
            "imagination", "idealization", "escapism", "illusion", "yearning", "dreams","vast immersion in the primordial unknown",
            "music", "glamour", "diffusion", "dissolution", "longing", "mysticism","l'appel du vide","vastness","lack of boundaries",
            "confusion", "permeability", "intoxication","distractions","longing for the unbounded","surrender to the unknown","devotion without proof",
        ],
        "verbs": [
            "imagining", "daydreaming about", "escaping from", "avoiding", "idealizing","seeking transcendence through",
            "trusting in", "dissolving into", "drifting through", "surrendering to","projecting onto","confused for","confused by",
            "romanticizing", "misunderstanding", "finding beauty in", "blurring", "intoxicating",
        ],
        "verbsonly": [
            "imagining", "daydreaming", "escaping", "avoiding", "idealizing","transcending",
            "trusting", "doubting", "dissolving", "drifting", "surrendering",
            "romanticizing", "misunderstanding", "finding beauty", "blurring", "intoxicating",
        ],
        "definition1":"dreaming of",  #append SIGN_KEYWORDS_CANONICAL's "motivations" 
        "definition2":"believing in", #append SIGN_KEYWORDS_CANONICAL's "talents" 
        "explanation":[
            "the beautiful lie and the beautiful possibility, often in the same bottle",
        ],
        "archetypes":[
            "fog bank","deep uncharted ocean","being lost in the depths of space",
        ],
    },
    "Pluto": {
        "nouns": [
            "control", "compulsion", "obsession", "fixations", "metamorphosis", "power dynamics","power struggle",
            "subterranean motives", "purge", "eradication", "exposure", "confrontation","battle-tested bonds","excavation of hidden motives",
            "domination", "intensity", "irreversible change", "reconstruction after collapse",
        ],
        "verbs": [
            "investigating", "tracking", "controlling", "probing", "testing the limits of", "resetting",
            "cutting off", "eliminating", "insisting on", "obsessing over", "confronting", "rebuilding",
        ],
        "verbsonly": [
            "investigating", "tracking", "controlling", "probing", "testing limits", "resetting",
            "cutting off", "eliminating", "insisting", "obsessing", "confronting", "rebuilding",
        ],
        "definition1":"maintaining control by",  #append SIGN_KEYWORDS_CANONICAL's "challenges" 
        "definition2":"achieving power by",  #append SIGN_KEYWORDS_CANONICAL's "talents" 
        "explanation":[""],
        "archetypes":[
            "Kafka plots", #lol
        ],
    },
    "Chiron": {
        "nouns": [
            "trigger points", "sensitivities", "difficulty", "lessons", "adaptation", "recovery paths",
            "mistakes", "compensatory skills", "instructive failures", "awkwardness",
            "reframed perspectives", "earned insight","psychic scars",
        ],
        "verbs": [
            "noticing vulnerabilities in", "working through", "adapting to", "learning from mistakes with",
            "teaching through", "practicing around", "compensating for", "reframing", "recovering", "guiding through",
        ],
        "verbsonly": [
            "noticing vulnerabilities", "working through", "adapting", "learning from mistakes",
            "teaching through", "practicing", "compensating", "reframing", "recovering", "guiding",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the place where difficulty becomes method, and sensitivity becomes instruction",
        ],
        "archetypes": [
            "Obi-Wan Kenobe",
        ],
    },
    "Ceres": {
        "nouns": [
            "nourishment", "care", "food", "provisioning", "support", "cultivation",
            "gardens", "lunches",  "budgeting","momming",
        ],
        "verbs": [
            "feeding", "cooking", "shopping", "providing", "cleaning", "hosting",
            "gardening", "budgeting", "caring for","nurturing others with", "providing support with",
        ],
        "verbsonly": [
            "feeding", "cooking", "shopping", "providing", "cleaning", "hosting",
            "gardening", "budgeting", "caring","nurturing others", "providing support",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[
            "the instinct to feed, tend, preserve, and keep life going through seasons of scarcity and plenty alike.",
        ],
        "archetypes":[
            "the steward", "the gardener", "the keeper of stores","the potluck queen","the lunchlady",
        ],
    },
    "Pallas": {
        "nouns": [
            "strategy", "pattern recognition", "solutions", "design", "engineering", "tactics",
            "foresight", "maps", "discernment", "negotiation", "intelligence", "system architecture",
        ],
        "verbs": [
            "planning", "strategizing", "problem-solving", "noticing patterns", "designing", "organizing",
            "mapping", "negotiating", "advising", "spotting risks", "outmaneuvering", "synthesizing",
        ],
        "verbsonly": [
            "planning", "strategizing", "problem-solving", "noticing patterns", "designing", "organizing",
            "mapping", "negotiating", "advising", "spotting risks", "outmaneuvering", "synthesizing",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the intelligence that reads patterns, designs solutions, and turns perception into strategy",
        ],
        "archetypes":[
            "Samantha Carter (SG1)","Athena","Princess Leia","Seven of Nine (Star Trek: Voyager)","Dana Scully (X-Files)",
        ],
    },
    "Juno": {
        "nouns": [
            "commitment", "marriage", "partnership", "vows", "agreements", "mutuality",
            "fairness", "expectations", "loyalty", "reciprocity", "accountability", "fidelity",
        ],
        "verbs": [
            "committing to", "partnering with", "negotiating with", "making agreements with", "sharing responsibilities with",
            "keeping promises to", "insisting on fairness with regard to", "checking expectations with", "remaining loyal to", "cooperating with", "honoring vows to",
        ],
        "verbsonly": [
            "committing", "partnering", "negotiating", "making agreements", "sharing responsibilities",
            "keeping promises", "insisting on fairness", "checking expectations", "remaining loyal", "cooperating", "honoring vows",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the formal bond: commitment, reciprocity, and the terms under which two people agree to belong to one another",
        ],
        "archetypes": [
            "the lawful spouse",
        ],
    },
    "Vesta": {
        "nouns": [
            "focus", "devotion", "dedication", "practice", "study", "solitude","asceticism","purification","rejection of distraction",
            "discipline", "consecration", "containment", "standards", "sacred focus", "inner flame",
        ],
        "verbs": [
            "focusing on", "practicing", "studying", "working alone with", "maintaining devotion to", "keeping vigil over",
            "protecting time for", "limiting distractions around", "dedicating oneself to", "concentrating on", "tending", "preserving",
        ],
        "verbsonly": [
            "focusing", "practicing", "studying", "working alone", "maintaining devotion", "keeping vigil",
            "protecting time", "limiting distractions", "dedicating oneself", "concentrating", "tending", "preserving",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the devoted flame: disciplined concentration, protected interiority, and the work one serves with sustained focus.","#1 premium choice for ceremonial sacrifice to a dragon. Totally won't piss off the gods. *fingers crossed*",#"Prime ceremonial-sacrifice material.",
        ],
        "archetypes": [
            "the vestal virgin priestess", "nuns", "monks", "the cloistered scholar",
        ],
    },
    "Rahu": {
        "nouns": [
            "hunger", "craving", "obsession", "fixation", "ambition", "insatiability",
            "amplification", "fascination", "taboo attraction", "worldly appetite", "restlessness",
        ],
        "verbs": [
            "wanting more from", "chasing", "fixating on", "amplifying", "overreaching toward", "becoming fascinated with",
            "crossing boundaries for", "competing for", "grasping at", "inflating", "consuming", "pushing past",
        ],
        "verbsonly": [
            "wanting more", "chasing", "fixating", "amplifying", "overreaching", "becoming fascinated",
            "crossing boundaries", "competing", "grasping", "inflating", "consuming", "pushing past",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the appetite that does not know when it is fed: fixation, worldly hunger, and the restless pursuit of what seems necessary for completion",
        ],
        "archetypes": [
            "the poltergeist, a restless spirit who yearns to live", "the usurper", "the exile who wants the crown","the rejected fairy godmother","Alakshmi",
        ],
    },
    "Ketu": {
        "nouns": [
            "detachment", "severance", "release", "renunciation", "withdrawal", "distance","disenchantment", "spent appetite",
            "negation", "disinterest", "letting go", "emptiness", "endings", "dissolution", "end of an era","hollow victories",
        ],
        "verbs": [
            "letting go of", "quitting", "walking away from", "detaching from", "withdrawing from", "cutting off",
            "ending", "simplifying", "renouncing", "releasing", "subtracting", "disidentifying from","finding only emptiness in", 
        ],
        "verbsonly": [
            "letting go", "quitting", "walking away", "detaching", "withdrawing", "cutting off",
            "ending", "simplifying", "renouncing", "releasing", "subtracting", "disidentifying",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the severing principle: release, detachment, and the strange familiarity that no longer promises fulfillment.",
        ],
        "archetypes": [
            "the renunciant", "the cast-off skin", "being fed up with this small town like you're in a Bruce Springsteen song","Rambo when he swore he'd never go back for one more job","the one who knows how the trick works and that it isn't actually magic",
        ],
    },
    "Lilith": {
        "nouns": [
            "refusal", "defiance", "taboo", "exile", "noncompliance", "provocation",
            "untamed desire", "erotic autonomy", "rejection", "social punishment", "subversion", "disowned hunger",
        ],
        "verbs": [
            "refusing", "defying", "rejecting", "breaking taboos around", "withholding compliance from",
            "provoking", "refusing subordination in", "claiming autonomy over", "disrupting expectations around",
            "testing limits of", "walking away from", "remaining unapologetic about",
        ],
        "verbsonly": [
            "refusing", "defying", "rejecting", "breaking taboos", "withholding compliance",
            "provoking", "refusing subordination", "claiming autonomy", "disrupting expectations",
            "testing limits", "walking away", "remaining unapologetic",
        ],
        "definition1":"",
        "definition2":"",
        "explanation": [
            "the part that would rather be exiled than domesticated: taboo desire, refusal of subordination, and the social cost of remaining unassimilated",
        ],
        "archetypes": [
          "Mata Hari","Cleopatra","Jeanne d'Arc","the one they call dangerous because she would not submit", # "the wife who walked out", "the exile who will not kneel","the burned witch",  
        ],
    },
    "Part of Fortune": {
        "nouns": [
            "luck", "ease", "flow", "wellbeing", "prosperity", "fruitfulness", "timing","tao",
            "advantages", "support", "natural fit", "coherence", "rhythm", "thriving",
        ],
        "verbs": [
            "falling into rhythm with", "finding ease in", "benefiting from", "thriving through", "making the most of",
           "finding opportunities with", "being in the right place for","being well-supported by", "prospering through", "landing well in", "working smoothly with",
        ],
        "verbsonly": [
            "finding ease", "benefiting", "thriving", "making the most", "being supported",
            "finding a groove", "prospering", "landing well", "working smoothly","finding a niche",
            "meeting the right people", "being in the zone", "being in the right place",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[
            "the place of natural ease, embodied coherence, and conditions under which life tends to become more fruitful",
        ],
        "archetypes":[
            "The Tao","The Zone",
        ],
    },
    "AS": {
        "nouns": [
            "introductions", "arrival", "beginnings", "first impressions", "initiative",
            "reactions", "approaches", "style", "tone",
        ],
        "verbs": [
            "introducing yourself to", "showing up like", "meeting people via", "making first impressions", "taking initiative via",
            "reacting with", "approaching", "trying", "testing the waters of", "leading with your style via", "setting the tone with",
        ],
        "verbonly": [
            "introducing yourself", "showing up", "meeting people", "making first impressions", "taking initiative",
            "reacting", "approaching", "trying", "testing the waters", "leading with your style", "setting the tone",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[""],
        "archetypes":[
        ],
    },
    "MC": {
        "nouns": [
            "work", "leadership", "management", "presentations", "deliverables", "promotions",
            "reputation", "responsibility", "decisions", "targets", "visibility", "outcomes",
        ],
        "verbs": [
            "working with", "leading", "managing", "presenting", "delivering", "getting promoted by",
            "building a reputation around", "taking responsibility of", "making decisions about", "obtaining visibility via", "owning outcomes via",
        ],
        "verbsonly": [
            "working", "leading", "managing", "presenting", "delivering", "getting promoted",
            "building a reputation", "taking responsibility", "making decisions", "obtaining visibility", "owning outcomes",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[""],
        "archetypes":[
        ],
    },
    "DS": {
        "nouns": [
            "dating", "partnership", "listening", "compromise", "negotiation", "collaboration",
            "sharing", "matching", "terms", "arguments", "reconciliation", "commitment",
        ],
        "verbs": [
            "dating", "partnering with", "listening to", "compromising on", "negotiating with", "collaborating with",
            "sharing", "matching energy of", "setting terms for", "arguing with", "reconciling via", "committing to",
        ],
        "verbsonly": [
            "dating", "partnering", "listening", "compromising", "negotiating", "collaborating",
            "sharing", "matching energy", "setting terms", "arguing", "reconciling", "committing",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[""],
        "archetypes":[
        ],
    },
    "IC": {
        "nouns": [
            "rest", "home", "staying in", "recovery", "nesting", "meals",
            "cleaning", "family time", "memory", "reflection", "savings", "recharge",
        ],
        "verbs": [
            "resting", "going home", "staying in", "recovering", "nesting", "cooking",
            "cleaning", "spending family time with", "remembering", "reflecting", "saving money", "recharging",
        ],
        "verbsonly": [
            "resting", "going home", "bunkering down", "recovering", "nesting", "cooking",
            "cleaning", "spending family time with", "remembering", "reflecting", "saving money", "recharging",
        ],
        "definition1":"",
        "definition2":"",
        "explanation":[""],
        "archetypes":[
        ],
    },
}

DOMINANT_BODY_MEANINGS = {
    "Sun": {
        "symbol": "☉",
        "category": "planet",
        "core_theme": "Identity, vitality, central purpose, self-definition, will.",
        "summary": (
            "A Sun-dominant person is usually trying, consciously or not, to become "
            "more fully themselves. Their life often revolves around authorship, "
            "self-expression, dignity, and the question: 'Who am I when I stand in my own authority?'"
        ),
        "typical_traits": [
            "noticeable presence",
            "strong need to matter, create, lead, or define",
            "often charismatic, proud, self-aware, or dramatically self-conscious",
            "tends to orient life around purpose and personal coherence",
            "can feel 'seen' or 'exposed' very intensely",
        ],
        "at_best": [
            "radiant",
            "steady",
            "self-possessed",
            "creative and life-giving",
            "naturally galvanizes others",
            "strong sense of mission",
        ],
        "at_worst": [
            "vanity",
            "ego fragility",
            "excessive self-reference",
            "needing recognition to prop up identity insecurity",
            "performative confidence covering identity insecurity",
        ],
        "life_lesson": "To develop a self that is real, not merely admired.",
        "reaction": "There is a person here.",
        "shorthand": "I must become myself.",
    },

    "Moon": {
        "symbol": "☽",
        "category": "planet",
        "core_theme": "Emotional life, instinct, needs, bonding, memory, internal safety.",
        "summary": (
            "A Moon-dominant person lives through felt experience first. Their inner "
            "weather is not background—it is infrastructure. They often absorb atmosphere "
            "rapidly and can be deeply shaped by family systems, attachment patterns, "
            "nostalgia, rhythms, and unconscious emotional expectations."
        ),
        "typical_traits": [
            "emotionally responsive",
            "receptive",
            "impressionable",
            "intuitive about tone, subtext, mood, and belonging",
            "can be nurturing, protective, sentimental, private, or reactive",
            "often highly influenced by environment",
            "usually needs emotional continuity more than they admit",
        ],
        "at_best": [
            "caring",
            "attuned",
            "psychologically perceptive",
            "strong emotional intelligence",
            "creates safety and belonging",
            "deeply human and connective",
        ],
        "at_worst": [
            "mood-led decision-making",
            "clinginess",
            "defensiveness",
            "regression",
            "overidentification with feelings",
            "difficulty separating present reality from old emotional conditioning",
        ],
        "life_lesson": "To distinguish what is true now from what feels familiar.",
        "reaction": "This person is feeling everything.",
        "shorthand": "I must feel safe and connected.",
    },

    "Mercury": {
        "symbol": "☿",
        "category": "planet",
        "core_theme": "Mind, language, pattern recognition, interpretation, exchange.",
        "summary": (
            "A Mercury-dominant person lives by naming, sorting, comparing, decoding, "
            "and articulating. Their relationship to reality is often mediated through "
            "thought and language."
        ),
        "typical_traits": [
            "curious",
            "verbal",
            "observant",
            "mentally quick",
            "restless",
            "analytical",
            "witty",
            "adaptable",
            "often highly sensitive to ambiguity, contradiction, and precision",
            "may collect frameworks, trivia, methods, or systems",
            "often gifted at translation between people, ideas, or domains",
        ],
        "at_best": [
            "clever",
            "lucid",
            "flexible",
            "insightful",
            "excellent communicator or synthesizer",
            "can make complexity understandable",
        ],
        "at_worst": [
            "overthinking",
            "anxiety",
            "intellectualization",
            "scattered attention",
            "compulsive analysis",
            "using cleverness to avoid conviction or vulnerability",
        ],
        "life_lesson": "To move from constant processing to meaningful understanding.",
        "reaction": "Their mind is always on.",
        "shorthand": "I must understand and articulate.",
    },

    "Venus": {
        "symbol": "♀",
        "category": "planet",
        "core_theme": "Attraction, harmony, values, pleasure, aesthetics, social magnetism, relating.",
        "summary": (
            "A Venus-dominant person is often organized around taste, connection, "
            "desirability, reciprocity, and what feels worth loving. Venus is not just "
            "'pretty' or 'romantic'—it is an organizing intelligence about value."
        ),
        "typical_traits": [
            "charming",
            "relational",
            "diplomatic",
            "attractive or aesthetically coherent",
            "often refined in taste, style, voice, space, or social instinct",
            "values mutuality and emotional/social equilibrium",
            "tends to notice what is pleasing, elegant, or discordant",
        ],
        "at_best": [
            "gracious",
            "magnetic",
            "artistic",
            "socially intelligent",
            "creates warmth, beauty, and relational balance",
            "deeply aware of what is meaningful and worth preserving",
        ],
        "at_worst": [
            "conflict avoidance",
            "vanity",
            "passivity",
            "people-pleasing",
            "seduction as strategy",
            "overvaluing comfort, approval, or desirability",
        ],
        "life_lesson": "To choose what is truly valuable, not merely attractive or agreeable.",
        "reaction": "Being around them has a texture.",
        "shorthand": "I must attract, harmonize, and value.",
    },

    "Mars": {
        "symbol": "♂",
        "category": "planet",
        "core_theme": "Drive, assertion, action, desire, courage, aggression, survival force.",
        "summary": (
            "A Mars-dominant person tends to meet life as a thing to engage, pursue, "
            "challenge, confront, or move through. Mars dominance often produces a person "
            "asking: 'What do I want, and am I willing to go get it?'"
        ),
        "typical_traits": [
            "direct",
            "active",
            "decisive",
            "competitive",
            "bold",
            "often impatient with dithering, vagueness, or passivity",
            "strong instinct for conflict, urgency, and tactical movement",
            "often highly sexual, physical, or will-driven",
        ],
        "at_best": [
            "brave",
            "effective",
            "energetic",
            "self-starting",
            "knows how to act under pressure",
            "can cut through nonsense efficiently",
        ],
        "at_worst": [
            "irritability",
            "impulsiveness",
            "domination",
            "hostility",
            "acting before reflecting",
            "confusing force with strength",
        ],
        "life_lesson": "To use power cleanly, not compulsively.",
        "reaction": "This person has thrust.",
        "shorthand": "I must act, pursue, and assert.",
    },

    "Jupiter": {
        "symbol": "♃",
        "category": "planet",
        "core_theme": "Growth, meaning, faith, expansion, philosophy, abundance, worldview.",
        "summary": (
            "A Jupiter-dominant person often lives in relation to possibility. They tend "
            "to orient toward growth, perspective, big-picture meaning, and what could be "
            "made larger, wiser, freer, or more significant."
        ),
        "typical_traits": [
            "optimistic",
            "generous",
            "broad-minded",
            "future-oriented",
            "philosophical",
            "humorous",
            "exploratory",
            "often drawn to travel, learning, spirituality, law, ethics, publishing, or teaching",
            "tends to dislike pettiness and constriction",
        ],
        "at_best": [
            "inspiring",
            "wise",
            "expansive",
            "encouraging",
            "sees patterns and larger significance",
            "can restore morale and meaning",
        ],
        "at_worst": [
            "excess",
            "exaggeration",
            "arrogance",
            "overpromising",
            "spiritual or intellectual grandiosity",
            "mistaking confidence for truth",
        ],
        "life_lesson": "To cultivate discernment, not just expansion.",
        "reaction": "They make reality feel bigger.",
        "shorthand": "I must grow, believe, and expand.",
    },

    "Saturn": {
        "symbol": "♄",
        "category": "planet",
        "core_theme": "Structure, responsibility, time, discipline, fear, legitimacy, endurance, mastery.",
        "summary": (
            "A Saturn-dominant person often develops early around constraint, seriousness, "
            "pressure, standards, or the need to become competent. Saturn dominance often "
            "marks a person with enormous staying power and capacity for excellence."
        ),
        "typical_traits": [
            "reserved",
            "controlled",
            "disciplined",
            "realistic",
            "self-monitoring",
            "highly sensitive to competence, hierarchy, failure, and consequences",
            "often private, stoic, or dryly funny",
            "may feel they must earn everything",
        ],
        "at_best": [
            "mature",
            "dependable",
            "principled",
            "masterful",
            "capable of real depth and sustained achievement",
            "builds what lasts",
        ],
        "at_worst": [
            "inhibition",
            "pessimism",
            "rigidity",
            "self-criticism",
            "emotional withholding",
            "chronic defensiveness",
            "overidentifying with duty or deprivation",
        ],
        "life_lesson": "To build structure without becoming imprisoned by it.",
        "reaction": "This person has gravity.",
        "shorthand": "I must master, endure, and legitimize.",
    },

    "Uranus": {
        "symbol": "♅",
        "category": "planet",
        "core_theme": "Freedom, disruption, originality, individuation, awakening, unconventionality.",
        "summary": (
            "A Uranus-dominant person is usually built to differentiate. They often have "
            "a sharp instinct to detach from stale systems, reject false conformity, and "
            "pursue authenticity—even if it makes life less comfortable."
        ),
        "typical_traits": [
            "independent",
            "unusual",
            "inventive",
            "anti-boring",
            "mentally fast",
            "contrarian",
            "future-facing",
            "often allergic to control, stagnation, or social scripts",
            "may oscillate between detachment and sudden intensity",
        ],
        "at_best": [
            "visionary",
            "liberating",
            "original",
            "reform-minded",
            "helps others break out of dead structures",
            "often brilliantly insightful",
        ],
        "at_worst": [
            "erratic",
            "emotionally avoidant",
            "oppositional for its own sake",
            "commitment issues",
            "instability",
            "self-exile",
            "mistaking reactivity for freedom",
        ],
        "life_lesson": "To become truly free without becoming ungrounded or unreachable.",
        "reaction": "They are operating on a different frequency.",
        "shorthand": "I must differentiate and liberate.",
    },

    "Neptune": {
        "symbol": "♆",
        "category": "planet",
        "core_theme": "Imagination, transcendence, sensitivity, spirituality, longing, permeability, illusion.",
        "summary": (
            "A Neptune-dominant person often experiences life through symbol, atmosphere, "
            "longing, beauty, mystery, and porous boundaries. This often creates a major "
            "theme of inspiration versus confusion."
        ),
        "typical_traits": [
            "dreamy",
            "empathic",
            "artistic",
            "mystical",
            "suggestible",
            "deeply responsive to music, symbolism, mood, fantasy, or collective feeling",
            "often compassionate and spiritually attuned",
            "can struggle with clarity, boundaries, or concrete self-definition",
        ],
        "at_best": [
            "imaginative",
            "soulful",
            "transcendent",
            "compassionate",
            "gifted in art, spirituality, healing, symbolism, or emotional resonance",
            "can perceive subtle realities others miss",
        ],
        "at_worst": [
            "escapism",
            "idealization",
            "denial",
            "self-deception",
            "porous boundaries",
            "projection",
            "romantic delusion",
            "difficulty with practical reality",
        ],
        "life_lesson": "To protect sensitivity with discernment and form.",
        "reaction": "There’s something ungraspable about them.",
        "shorthand": "I must imagine, dissolve, and transcend.",
    },

    "Pluto": {
        "symbol": "♇",
        "category": "planet",
        "core_theme": "Intensity, transformation, power, compulsion, depth, taboo, psychological truth.",
        "summary": (
            "A Pluto-dominant person rarely does 'light and easy' in any sustained way. "
            "Even when externally calm, they often carry a deep instinct toward penetration, "
            "control, survival, truth, and metamorphosis."
        ),
        "typical_traits": [
            "intense",
            "private",
            "magnetic",
            "psychologically sharp",
            "emotionally all-or-nothing",
            "often resilient",
            "self-protective",
            "difficult to fool",
            "may attract crisis, projection, obsession, or catalytic relationships",
        ],
        "at_best": [
            "profound",
            "transformative",
            "fearless about depth",
            "powerful capacity for regeneration",
            "capable of tremendous honesty and psychological insight",
        ],
        "at_worst": [
            "control issues",
            "suspicion",
            "obsession",
            "possessiveness",
            "secrecy",
            "power struggles",
            "emotional extremity",
            "compulsive attachment to suffering, intensity, or domination",
        ],
        "life_lesson": "To seek truth without needing control over everything it reveals.",
        "reaction": "This person sees too much.",
        "shorthand": "I must penetrate, transform, and survive.",
    },

    "Rahu": {
        "symbol": "☊",
        "category": "lunar_node",
        "core_theme": "Appetite, obsession, amplification, worldly hunger, future pull, destabilizing desire.",
        "summary": (
            "A Rahu-dominant person is often organized around appetite, ambition, fascination, "
            "and unfinished desire. Rahu tends to act like a magnifier: it makes certain life "
            "areas feel urgent, intoxicating, destabilizing, and strangely fated. The person is "
            "often pulled toward what is unfamiliar, socially potent, taboo, or materially promising."
        ),
        "typical_traits": [
            "intense ambition or fixation",
            "attraction to novelty, status, edge, or transgression",
            "future-oriented but often restless",
            "can feel perpetually unfinished or unsatisfied",
            "strong instinct to become more, have more, know more, or reach further",
            "often socially strategic or unusually adaptive",
            "drawn to karmically charged experiences",
        ],
        "at_best": [
            "boldly evolutionary",
            "socially intelligent",
            "magnetic",
            "innovative",
            "fearless about entering unfamiliar terrain",
            "capable of dramatic worldly growth",
        ],
        "at_worst": [
            "obsession",
            "compulsiveness",
            "insatiability",
            "status hunger",
            "manipulation",
            "inflation",
            "chasing what cannot satisfy",
            "mistaking stimulation for destiny",
        ],
        "life_lesson": "To pursue growth without becoming possessed by craving.",
        "reaction": "This person is being pulled by something larger and less settled.",
        "shorthand": "I must chase the next frontier.",
    },

    "Ketu": {
        "symbol": "☋",
        "category": "lunar_node",
        "core_theme": "Detachment, past mastery, renunciation, karmic residue, spiritual subtraction, release.",
        "summary": (
            "A Ketu-dominant person often feels partially disenchanted with ordinary worldly "
            "rewards. Ketu can indicate old mastery, old exhaustion, and a tendency to withdraw "
            "from what others are still trying to prove. It often gives instinctive competence "
            "alongside strange emptiness or disinterest."
        ),
        "typical_traits": [
            "detached or inwardly removed",
            "strong intuition and pattern memory",
            "can seem ancient, elusive, or hard to pin down",
            "often gifted in an area they do not particularly worship",
            "periodic withdrawal from ego structures or worldly incentives",
            "tendency toward minimalism, negation, or severance",
            "may feel alienated from ordinary ambition",
        ],
        "at_best": [
            "spiritually incisive",
            "nonattached",
            "intuitive",
            "subtle",
            "capable of profound discernment",
            "less easily seduced by social nonsense",
        ],
        "at_worst": [
            "disengagement",
            "avoidance",
            "fatalism",
            "alienation",
            "difficulty investing in material life",
            "self-erasure",
            "retreating from incarnation altogether, which is very rude of the soul frankly",
        ],
        "life_lesson": "To release old overidentification without abandoning participation in life.",
        "reaction": "This person is partly elsewhere.",
        "shorthand": "I must let go of what I already know too well.",
    },

    "Lilith": {
        "symbol": "⚸",
        "category": "lunar_apogee",
        "core_theme": "Raw autonomy, refusal, erotic sovereignty, exile, taboo selfhood, untamed instinct.",
        "summary": (
            "A Lilith-dominant person often carries themes of refusal, autonomy, erotic charge, "
            "social noncompliance, and the parts of the psyche that will not submit politely. "
            "Lilith tends to describe where a person feels cast out, hypervisible, misunderstood, "
            "or unwilling to perform domesticated acceptability."
        ),
        "typical_traits": [
            "fiercely independent",
            "highly reactive to control, shame, or moral policing",
            "strong taboo radar",
            "sexual or instinctual intensity",
            "can provoke projection in others without trying",
            "often allergic to false sweetness or social falseness",
            "may oscillate between concealment and defiant exposure",
        ],
        "at_best": [
            "self-possessed",
            "psychologically honest",
            "sexually and creatively autonomous",
            "immune to cheap social conditioning",
            "capable of radical integrity",
        ],
        "at_worst": [
            "reactive defiance",
            "alienation",
            "self-isolation",
            "destructive refusal",
            "weaponized sexuality or contempt",
            "identifying so hard with rejection that intimacy becomes difficult",
        ],
        "life_lesson": "To embody untamed truth without becoming ruled by exile or antagonism.",
        "reaction": "This person does not submit cleanly.",
        "shorthand": "I must remain sovereign, even if it costs belonging.",
    },

    "Chiron": {
        "symbol": "⚷",
        "category": "asteroid",
        "core_theme": "Wound, wisdom, sensitivity, apprenticeship through pain, healing intelligence.",
        "summary": (
            "A Chiron-dominant person often develops identity around a core sensitivity, rupture, "
            "or unresolved ache that becomes a source of unusual understanding. Chiron tends to "
            "describe where someone becomes both vulnerable and instructive—where pain and meaning "
            "become intertwined."
        ),
        "typical_traits": [
            "heightened sensitivity around a recurring life theme",
            "often insightful about suffering, repair, or human limitation",
            "may become a guide, teacher, helper, or translator of difficult material",
            "often carries visible competence alongside hidden soreness",
            "drawn to healing, mentoring, or making meaning from difficulty",
        ],
        "at_best": [
            "wise",
            "compassionate",
            "deeply instructive",
            "capable of nuanced healing work",
            "able to turn injury into understanding",
        ],
        "at_worst": [
            "overidentification with woundedness",
            "martyr patterns",
            "chronic insecurity",
            "trying to heal others instead of addressing oneself",
            "making pain the organizing center of identity",
        ],
        "life_lesson": "To let sensitivity become wisdom without making it a permanent throne.",
        "reaction": "This person understands pain in a precise way.",
        "shorthand": "I must turn pain into knowledge.",
    },

    "Ceres": {
        "symbol": "⚳",
        "category": "asteroid",
        "core_theme": "Nourishment, caretaking, provision, grief, cycles of attachment and loss.",
        "summary": (
            "A Ceres-dominant person is often organized around feeding, protecting, supporting, "
            "or sustaining life. Ceres tends to describe how someone nourishes and how they cope "
            "with separation, deprivation, and the fear of not being able to keep what they love alive."
        ),
        "typical_traits": [
            "strong caretaking or provisioning instinct",
            "attentive to food, health, rhythms, routines, and practical support",
            "often deeply affected by abandonment, separation, or inconsistency",
            "can be maternal, agricultural, ecological, or body-centered in orientation",
            "often tracks whether others are truly cared for",
        ],
        "at_best": [
            "nurturing",
            "steadfast",
            "supportive",
            "embodied",
            "capable of sustaining others through real care",
        ],
        "at_worst": [
            "smothering",
            "control through caretaking",
            "anxiety around loss",
            "resentful overgiving",
            "equating love with management or provision",
        ],
        "life_lesson": "To nourish without controlling, and to love without gripping.",
        "reaction": "This person knows how to keep life going.",
        "shorthand": "I must feed, sustain, and protect.",
    },

    "Pallas": {
        "symbol": "⚴",
        "category": "asteroid",
        "core_theme": "Pattern intelligence, strategy, design, wisdom, systems thinking, tactical perception.",
        "summary": (
            "A Pallas-dominant person often leads with pattern recognition, strategic intelligence, "
            "and elegant problem-solving. Pallas tends to describe the mind as architect: seeing "
            "how parts fit, where leverage exists, and how order can be imposed intelligently."
        ),
        "typical_traits": [
            "strategic and perceptive",
            "good at pattern matching and systems design",
            "often politically or socially aware in a structural sense",
            "can think tactically under pressure",
            "often drawn to planning, analysis, architecture, coding, design, or negotiation",
        ],
        "at_best": [
            "brilliantly strategic",
            "inventive",
            "elegant in execution",
            "able to solve complex problems with economy",
        ],
        "at_worst": [
            "overintellectualization",
            "coldness",
            "detachment from feeling",
            "treating life as a puzzle instead of a lived reality",
            "using intelligence defensively",
        ],
        "life_lesson": "To unite wisdom with embodiment and not confuse analysis with wholeness.",
        "reaction": "This person sees the structure underneath the structure.",
        "shorthand": "I must understand the pattern and outmaneuver the problem.",
    },

    "Juno": {
        "symbol": "⚵",
        "category": "asteroid",
        "core_theme": "Commitment, partnership, vows, loyalty, power in union, relational contract.",
        "summary": (
            "A Juno-dominant person often organizes life around the meaning of commitment, reciprocity, "
            "and what constitutes a true bond. Juno tends to describe how a person approaches formal "
            "partnership, loyalty, betrayal, and the politics of long-term union."
        ),
        "typical_traits": [
            "serious about commitment and relational fairness",
            "sensitive to power imbalance or betrayal",
            "often oriented toward defining what a partnership should be",
            "can be deeply loyal and contract-minded",
            "may attract fated or politically significant unions",
        ],
        "at_best": [
            "faithful",
            "devoted",
            "principled in relationship",
            "capable of mature mutuality",
            "understands partnership as a structure, not just a mood",
        ],
        "at_worst": [
            "jealousy",
            "possessiveness",
            "rigidity around relational roles",
            "power struggles in commitment",
            "overidentifying with couplehood or betrayal narratives",
        ],
        "life_lesson": "To build sacred reciprocity without turning commitment into ownership.",
        "reaction": "This person takes partnership very seriously.",
        "shorthand": "I must define and protect the bond.",
    },

    "Vesta": {
        "symbol": "⚶",
        "category": "asteroid",
        "core_theme": "Devotion, focus, sacred work, inner flame, disciplined consecration.",
        "summary": (
            "A Vesta-dominant person often has a strong capacity for concentration, devotion, "
            "and self-contained purpose. Vesta tends to describe what a person treats as sacred, "
            "what they guard fiercely, and where they can become almost priestlike in dedication."
        ),
        "typical_traits": [
            "deep focus",
            "capacity for disciplined solitude",
            "strong private standards",
            "protective of energy, purpose, or sanctity",
            "often drawn to ritual, craft, vocation, or concentrated service",
            "can alternate between erotic intensity and celibate self-containment",
        ],
        "at_best": [
            "devoted",
            "pure in intent",
            "highly disciplined",
            "spiritually or vocationally focused",
            "capable of extraordinary concentration",
        ],
        "at_worst": [
            "rigidity",
            "self-denial",
            "isolation",
            "purity fixation",
            "burnout through overconsecration",
            "treating intensity of focus as moral superiority",
        ],
        "life_lesson": "To protect the sacred flame without sacrificing the rest of life to it.",
        "reaction": "This person is devoted to something with unusual seriousness.",
        "shorthand": "I must serve what is sacred to me.",
    },

    "Psyche": {
        "symbol": "Ψ",
        "category": "asteroid",
        "core_theme": "Soul sensitivity, intimacy of perception, longing for deep recognition, psychic receptivity.",
        "summary": (
            "A Psyche-dominant person often experiences relationships and meaning through unusually "
            "fine emotional or symbolic sensitivity. Psyche tends to describe where the soul wants "
            "to be recognized, joined, and transformed through profound contact."
        ),
        "typical_traits": [
            "deeply sensitive to emotional and symbolic nuance",
            "often romantic or soul-oriented in perception",
            "can feel psychically porous in close relationships",
            "strong longing for profound recognition or union",
            "often gifted in subtle emotional reading",
        ],
        "at_best": [
            "soulful",
            "intimate",
            "emotionally perceptive",
            "capable of profound relational depth",
        ],
        "at_worst": [
            "overidealization",
            "fragility in love",
            "projection",
            "fusion tendencies",
            "mistaking psychic intensity for compatibility",
        ],
        "life_lesson": "To seek soul-level connection without surrendering discernment.",
        "reaction": "This person is receiving more than they say.",
        "shorthand": "I must be deeply seen and psychically met.",
    },

    "Eros": {
        "symbol": "♥",
        "category": "asteroid",
        "core_theme": "Erotic vitality, creative desire, fascination, arousal, enlivening intensity.",
        "summary": (
            "A Eros-dominant person often leads with desire, fascination, creative hunger, and the "
            "animating force of attraction itself. Eros is not just sexuality; it is the principle "
            "of enlivened wanting—the current that makes life feel charged and worth pursuing."
        ),
        "typical_traits": [
            "magnetic desire nature",
            "strong attraction field",
            "creative and erotic intensity",
            "responsive to chemistry, beauty, and psychic charge",
            "often experiences longing as energizing and meaningful",
        ],
        "at_best": [
            "vital",
            "passionate",
            "creatively fertile",
            "sensually alive",
            "capable of inspiring desire and movement",
        ],
        "at_worst": [
            "obsession",
            "compulsiveness",
            "seduction without substance",
            "addiction to intensity",
            "difficulty tolerating flatness or ordinary attachment",
        ],
        "life_lesson": "To honor desire as sacred fuel without becoming enslaved to stimulation.",
        "reaction": "This person has charge.",
        "shorthand": "I must follow what enlivens and arouses me.",
    },
}


ASPECT_TYPES = {
    "chill vibes": {
        "color": "#6666ff", #violet
        "aspects": {"sextile", "trine"},
    },
    "stress/friction": {
        "color": "#b30000", #brick red
        "aspects": {"square", "opposition", "semisquare", "sesquiquadrate", "quincunx"},
    },
    "amplifying": {
        "color": "#ffff00", #aggro yellow
        "aspects": {"conjunction", "semisextile"},
    },
    "creative/technical": {
        "color": "#9966ff", #lavender
        "aspects": {"quintile", "biquintile"},
    },
}

ASPECT_FRICTION = {
    "harmonious": {
        "color": "#3333ff", #blue
        "aspects": {"sextile", "trine", "quintile", "biquintile"},
    },
    "conflicted": {
        "color": "#ff0000", #murdery red
        "aspects": {"square", "opposition", "semisquare", "sesquiquadrate", "quincunx"},
    },
    "neutral/variable": {
        "color": "#ffff66", #chill yellow
        "aspects": {"conjunction", "semisextile"},
    },
}

#not sure if this is being used at all:
ASPECT_BASE = {
    "conjunction": {"friction": 0, "support": 0, "intensity": 4},
    "opposition":  {"friction": 3, "support": 0, "intensity": 3},
    "square":      {"friction": 4, "support": 0, "intensity": 3},
    "quincunx":    {"friction": 2, "support": 0, "intensity": 2},
    "semisquare":  {"friction": 2, "support": 0, "intensity": 2},
    "sesquiquadrate": {"friction": 2, "support": 0, "intensity": 2},
    "trine":       {"friction": 0, "support": 3, "intensity": 2},
    "sextile":     {"friction": 0, "support": 2, "intensity": 1},
}

ASPECT_KEYWORDS = {
    "conjunction": [
        "working together with", "happening at the same time as", "stacking up with", "doubling down with",
        "sharing the same space as", "overlapping with", "teaming up with", "combining forces with",
        "running as one with", "showing up together with", "feeding into", "moving in lockstep with",
    ],
    "opposition": [
        "pulling against", "going back and forth with", "arguing against", "competing against",
        "negotiating against", "straining against", "counterbalancing against",
        "getting in the way of", "forcing a choice with", "meeting halfway with", "testing the limits of",
    ],
    "square": [
        "running into a wall of", "hitting resistance with", "getting blocked by", "clashing against",
        "starting fights with", "creating problems for", "forcing action against", "stressed out by",
        "made more difficult by", "conflicted by", "turning up the pressure on",
    ],
    "trine": [
        "making it easy for", "helping out", "supporting", "backing up","paving the way for",
        "getting along effortlessly with", "making progress through", "supporting",
        "stabilizing", "assisting",
    ],
    "sextile": [
        "opening doors for", "giving a chance to", "connecting people with", "starting cooperation with",
        "creating an option for", "making a useful link to", "offering help with", 
        "making opportunities for", "starting projects with", "finding workarounds for", "making introductions for",
    ],
    "quincunx": [
        "making adjustments to", "changing plans for", "rearranging", "compromising",
        "fixing mismatches with", "tweaking", "adapting to", "redoing",
        "shifting priorities with", "patching problems with", "changing approach to",
    ],
    "semisextile": [
        "making small changes to", "testing the waters of", "experimenting with", "nudging",
        "making minor fixes to", "getting used to", "warming up to",
        "adding a small component of", "fine-adjusting", "making a slight link to", "trying again with",
    ],
    "semisquare": [
        "getting irritated by", "feeling blocked by", "starting arguments with", "getting impatient with",
        "tripping over small problems with", "building annoyance with", "reacting too fast to", "snapping at",
        "making things tense with", "creating friction with", "rushing", "getting irritable with",
    ],
    "sesquiquadrate": [
        "blowing up", "overreacting to", "piling on", "exaccerbating",
        "turning stress into conflict with", "pushing too hard against", "escalating",
        "getting overwhelmed by", "forcing an issue with", "losing patience over", "going too far with",
    ],
    "quintile": [
        "cleverly handling", "fixing", "solving", "building something with",
        "improving results with", "figuring out", "inventing",
        "getting creative with", "designing", "optimizing",
    ],
    "biquintile": [
        "getting really good at", "perfecting", "sharpening", "fine-tuning",
        "dialing in", "upgrading", "mastering", "polishing",
        "making high quality", "making precise", "locking in", "raising the bar for",
    ],
    "septile": [
        "getting stuck on", "fixating on", "obsessing on", "overthinking",
        "making a weird choices about", "following a hunch about", "doubling down on", "getting hooked on",
        "acting on impulse with", "staying attached to", "chasing", "not letting go of",
    ],
    "novile": [
        "wrapping up with", "making peace with", "accepting", "settling into",
        "closing the chapter on", "finishing", "resolving", "coming to terms with",
        "processing quietly with", "moving on with", "locking in", "feeling complete with",
    ],
}

#=================== SOCIOLOGICAL STUFF

GENERATIONAL_COHORTS = [
    {
        "name": "Awakening",
        "start_year": 1701,
        "end_year": 1723,
        "global_context": "Expansion of maritime trade networks and early Enlightenment thought.",
        "asia_context": "Qing dynasty consolidation in China, Tokugawa stability in Japan, Mughal decline in India.",
        "africa_context": "Rise of centralized West African states such as the Asante Empire under Osei Tutu and the Oyo Empire at its peak; Islamic scholarly networks expand across Sahelian cities including Timbuktu, Kano, and Agadez.",
        "central_america_context": "Spanish colonial administration across the Captaincy General of Guatemala; plantation and mission systems dominate."
    },
    {
        "name": "Liberty",
        "start_year": 1724,
        "end_year": 1741,
        "global_context": "Spread of Enlightenment political philosophy.",
        "asia_context": "European trading companies expand influence in South and Southeast Asia.",
        "africa_context": "Consolidation of regional powers including Dahomey and Asante; expanding caravan trade routes linking Sahelian markets with North Africa and the Mediterranean.",
        "central_america_context": "Colonial economic expansion tied to silver trade and agricultural estates."
    },
    {
        "name": "Republican",
        "start_year": 1742,
        "end_year": 1766,
        "global_context": "Age of revolutions begins in the Atlantic world.",
        "asia_context": "British East India Company expansion following mid-18th-century conflicts in India.",
        "africa_context": "Growing influence of Islamic reform movements across the western Sahel and continued political competition among major states such as Oyo, Dahomey, and Benin.",
        "central_america_context": "Late colonial reforms and increased taxation under Bourbon administrative reforms."
    },
    {
        "name": "Compromise",
        "start_year": 1767,
        "end_year": 1791,
        "global_context": "Post-revolutionary political restructuring.",
        "asia_context": "European trade pressure increases on Qing China and Indian territories.",
        "africa_context": "Increasing religious and political reform movements in the Sahel leading toward the Fulani jihads; regional political realignments across West Africa.",
        "central_america_context": "Growing colonial tensions leading toward independence movements in the early 19th century."
    },
    {
        "name": "Transcendental",
        "start_year": 1792,
        "end_year": 1821,
        "global_context": "Romantic era intellectual movements and early industrialization.",
        "asia_context": "Growing Western economic influence in Asian ports.",
        "africa_context": "Fulani jihad movements transform Sahelian politics culminating in the creation of the Sokoto Caliphate (1804–1808), one of the largest states in 19th-century Africa.",
        "central_america_context": "Independence from Spain in 1821 and formation of early Central American republic structures."
    },
    {
        "name": "Gilded",
        "start_year": 1822,
        "end_year": 1842,
        "global_context": "Industrial revolution accelerates global trade.",
        "asia_context": "Opium Wars and treaty-port system reshape East Asian trade.",
        "africa_context": "Peak influence of the Sokoto Caliphate and other reform states such as Massina; regional trade expansion across West and East African networks.",
        "central_america_context": "Early republic instability and regional federation attempts."
    },
    {
        "name": "Progressive",
        "start_year": 1843,
        "end_year": 1859,
        "global_context": "Industrial capitalism and reform movements.",
        "asia_context": "Meiji Restoration transforms Japan; modernization attempts in China.",
        "africa_context": "Rise of powerful regional states including the Tukulor Empire and the early expansion of Samori Ture’s influence; growing Ethiopian regional consolidation.",
        "central_america_context": "Coffee economies expand; growing influence of export agriculture."
    },
    {
        "name": "Missionary",
        "start_year": 1860,
        "end_year": 1882,
        "global_context": "High imperial era.",
        "asia_context": "Rapid industrialization in Japan and reform efforts across Asia.",
        "africa_context": "Major African state-building efforts including Samori Ture’s Wassoulou Empire, Menelik II’s consolidation of Ethiopia, and the Mahdist uprising beginning in Sudan (1881).",
        "central_america_context": "Export-driven economies dominated by coffee and banana industries."
    },
    {
        "name": "Lost",
        "start_year": 1883,
        "end_year": 1900,
        "global_context": "World War I and collapse of empires.",
        "asia_context": "Nationalist movements and early modernization reforms.",
        "africa_context": "Mahdist state in Sudan and Ethiopia’s decisive victory over Italy at the Battle of Adwa (1896), one of the most significant anti-imperial victories in modern African history.",
        "central_america_context": "U.S. political and economic influence increases in the region."
    },
    {
        "name": "'Greatest'",
        "start_year": 1901,
        "end_year": 1927,
        "global_context": "Great Depression and World War II.",
        "asia_context": "Japanese expansion and major conflicts in East Asia.",
        "africa_context": "Early nationalist movements emerge; founding of the African National Congress (1912) and development of pan-African intellectual networks.",
        "central_america_context": "Economic disruption during the Great Depression and political instability."
    },
    {
        "name": "Silent",
        "start_year": 1928,
        "end_year": 1945,
        "global_context": "Postwar reconstruction and early Cold War.",
        "asia_context": "Communist revolution in China and Korean War.",
        "africa_context": "Expansion of organized anti-colonial politics across Africa and the rise of nationalist leadership that would lead independence movements after WWII.",
        "central_america_context": "Emerging Cold War influence and political restructuring."
    },
    {
        "name": "Baby Boomers",
        "start_year": 1946,
        "end_year": 1964,
        "global_context": "Post-WWII population boom and economic expansion.",
        "asia_context": "Industrial growth in East Asia and development policies across the region.",
        "africa_context": "Major independence wave including Ghana (1957), Nigeria (1960), Tanzania (1961), Algeria (1962), and Kenya (1963); early nation-building and Pan-African cooperation.",
        "central_america_context": "Agrarian reforms, political revolutions, and Cold War interventions."
    },
    {
        "name": "X",
        "start_year": 1965,
        "end_year": 1980,
        "global_context": "Late Cold War and globalization.",
        "asia_context": "Asian economic growth and China’s economic reforms.",
        "africa_context": "Post-independence state consolidation and liberation struggles in southern Africa including Angola, Mozambique, Zimbabwe, and Namibia.",
        "central_america_context": "Civil conflicts and political transitions in several countries."
    },
    {
        "name": "Millennials",
        "start_year": 1981,
        "end_year": 1996,
        "global_context": "Rise of the internet and globalization.",
        "asia_context": "Rapid economic expansion in East and Southeast Asia.",
        "africa_context": "End of apartheid in South Africa (1994), expansion of multiparty democracies across the continent, and rapid urbanization.",
        "central_america_context": "Post-conflict democratization and integration into global trade systems."
    },
    {
        "name": "Z",
        "start_year": 1997,
        "end_year": 2012,
        "global_context": "Smartphone and social-media era.",
        "asia_context": "Large-scale digital adoption and tech sector expansion.",
        "africa_context": "Rapid growth of mobile connectivity, fintech ecosystems, and youth-driven political movements across African cities.",
        "central_america_context": "Digital connectivity growth and migration pressures."
    },
    {
        "name": "Alpha",
        "start_year": 2013,
        "end_year": 2028,
        "global_context": "AI, automation, and climate policy transitions.",
        "asia_context": "Technology competition and demographic transitions.",
        "africa_context": "Early life during rapid demographic growth, large-scale urbanization, expanding digital infrastructure, and climate adaptation initiatives across Africa.",
        "central_america_context": "Climate pressures and economic migration shaping childhood environments."
    },
]

GENERATION_COLORS = {
    "Awakening": "#C9A227",   # Enlightenment amber
    "Liberty": "#2E5B8A",     # Liberty blue
    "Republican": "#A33A2B",  # Revolutionary crimson
    "Compromise": "#8A7F5A",  # Olive taupe
    "Transcendental": "#6E5A9E",  # Romantic violet
    "Gilded": "#D4AF37",      # Gilded gold
    "Progressive": "#2F7E79", # Reform teal
    "Missionary": "#7A3E48",  # Imperial maroon
    "Lost": "#6C6F73",        # Ash gray
    "'Greatest'": "#1F3A5F",    # Victory navy
    "Silent": "#7C8A99",      # Muted slate
    "Baby Boomers": "#C97A2B",           # Harvest orange
    "X": "#4E6E6A",           # Grunge teal
    "Millennials": "#F2B8C6",            # Millennial pink
    "Z": "#7B61FF",           # Digital violet
    "Alpha": "#00BFA5",       # AI mint
}



GENDER_OPTIONS = ["F", "M", "AMAB-F", "AFAB-M", "AFAB-NB", "AMAB-NB", "n/a", "?"]

GENDER_GLYPHS = {
    "M":"♂",
    "F":"♀",
    "AMAB-F":"♀",
    "AFAB-M":"♂",
    "AMAB-NB":"⚥",
    "AFAB-NB":"⚥",
    "n/a":"", #does not apply
    "?":"?", #user-selected to indicate unknown
    "":"", #blank - not yet parsed/established by user
}

SENTIMENT_OPTIONS = [ #you can reorder these, 
#but don't rename without FIRST updating the database! 
#Otherwise old names will be stored in all charts in the database.
#If you ever change "lust" to "crush", for instance, all old charts will have a value stored for "lust", not "crush".
   #pos
    "like", #friend
    "love", #love
    "lil crush", #you think they're cute
    "lust", #you're fixated
    "revere", #mentor
    "trust",
    "respect",
    "protect",
    "intriguing",
    "relatable (intellectually)",
    "relatable (fears/coping)",
    "relatable (values)",
    "relatable (interests)",
    "relatable (mannerisms)",
    "relatable (background)",
    "relatable",
    "hilarious",
#neg
    "can't trust",
    "can't respect",
    "can't forgive",
    "frustrating",
    "unreachable",
    "power struggles",
    "disappointing",
    "betrayal",
    "failed",
    "annoying",
    "creepy",
    "dislike", #enemy
    "despise", #archnemesis
]

SENTIMENT_COLORS = {
    "like": "#ff6600",
    "love": "#ff99ff",
    "lust": "#cc00cc", #ff00ff #d98cb3
    "revere": "#ffd966",
    "trust": "#00bcd4",
    "respect": "#4169e1", #990000
    "protect": "#0000ff",
    "intriguing":"#754db3",
    "relatable (intellectually)":"#33ccff",
    "relatable (fears/coping)":"#33ccff",
    "relatable (values)":"#33ccff",
    "relatable (interests)":"#33ccff",
    "relatable (mannerisms)":"#33ccff",
    "relatable (background)":"#33ccff",
    "relatable":"#33ccff",
    "hilarious":"#ffd966",
#neg
    "frustrating":"#993300",
    "unreachable":"#dbccbd",
    "power struggles":"#993333",
    "disappointing":"#9999ff",
    "betrayal":"#8000ff",
    "failed":"#cc9900",
    "annoying":"#ff1a1a",
    "creepy":"#ff6666",
    "can't trust": "#7f7f7f",
    "can't respect": "#a67c52",
    "can't forgive": "#4d4d4d",
    "dislike": "#5b0f0f",
    "despise": "#df3a3a",
 }

#Don't rename these or delete them without first taking remedial actions.
#It'll mess up your existing database.
RELATION_TYPE = [
    "self", #it's just you
    "ride or die", #structurally intertwined, Heavenly Creatures type stuff
    "core posse", #inseparable, bosom chum
    "homie", #your chum
    "mentor", #helps you understand who/what you could be, and how
    "ward", #a human in your care; you look after them as their caregiver/provider
    "lover", #ya hooked up
    "frenemy", #it's complicated
    "minor foe", #we're not cool
    "nemesis", #big problem
    "fascination", #dw, you're just stalking them
    "kin by marriage", #married into fam
    "kin by blood", #ancestors, cousins & siblings
    "colleague", #work with
    "authority", #power dynamic
    "acquaintance", #just seem em around, kinda know about them a little
    "friend of family", #(they're just around)
    "friend of friend", #(they're just around)
    "family of friend", #(they're just around)
    "your lover's ex", #(self-explanatory; here cos most people have feelings about it)
    "your friend's ex", #(self-explanatory; here cos some people have feelings about it)
    "pet", #a nonhuman creature in your care
    "only talk online", #you've only met online
    "never met", #maybe a friend of a friend you only know by reputation
    "public figure", #icon, subject to projections
    "place", #why does this require explanation? don't get philosophical on me.
    "event", #aren't we all an event, in a sense? NO. EVENTS ARE EVENTS. jk do whatever you're gonna, ya freak
]




# --------------------------------------------------
# EXPERIENCE DEFINITIONS
# --------------------------------------------------

FAMILIARITY_INDEX2 = [
    # Parasocial
    {"label": "read a book about", "base": 1, "category": "parasocial","freq": False, "duration": False},
    {"label": "read a book by", "base": 2, "category": "parasocial","freq": False, "duration": False},
    {"label": "stalked online", "base": 3, "category": "parasocial","freq": True, "duration": True},

    # Casual
    {"label": "have seen in person", "base": 2, "category": "casual", "freq": True, "duration": False},
    {"label": "chatted with", "base": 2, "category": "casual","freq": True, "duration": False},
    {"label": "hung out in person", "base": 1, "category": "casual","freq": True, "duration": True},
    {"label": "hung out alone together", "base": 4, "category": "casual","freq": True, "duration": True},

    # History
    {"label": "grew up together", "score": 5, "category": "history", "freq":False,"duration":False},
    {"label": "known since childhood", "score": 4, "category": "history", "freq":False,"duration":False},

    # Domestic
    {"label": "have been to their house", "score": 5, "category": "domestic", "freq":True,"duration":False},
    {"label": "lived together", "score": 7, "category": "domestic", "freq":False,"duration":True},

    # Romantic / Sexual
    {"label": "made out", "score": 5, "category": "romantic_sexual", "freq":False,"duration":False},
    {"label": "have seen in underwear", "score": 5, "category": "romantic_sexual", "freq":False,"duration":False},
    {"label": "have seen naked", "score": 6, "category": "romantic_sexual", "freq":False,"duration":False},
    {"label": "hooked up", "score": 6, "category": "romantic_sexual", "freq":True,"duration":False},
    {"label": "raw dogged", "score": 7, "category": "romantic_sexual", "freq":False,"duration":False},
    {"label": "are/were married", "score": 10, "category": "romantic_sexual", "freq":False,"duration":True},

    # Family integration
    {"label": "met their family", "score": 6, "category": "family_integration", "freq":True,"duration":False},
    {"label": "they met your family", "score": 6, "category": "family_integration", "freq":True,"duration":False},

    # Emotional
    {"label": "discussed life events", "score": 4, "category": "emotional", "freq":True,"duration":False},
    {"label": "discussed values", "score": 5, "category": "emotional", "freq":True,"duration":False},
    {"label": "have seen cry", "score": 5, "category": "emotional", "freq":False,"duration":False},
    {"label": "cried with", "score": 6, "category": "emotional", "freq":False,"duration":False},
    {"label": "shared secrets", "score": 7, "category": "emotional", "freq":False,"duration":False},

    # Conflict / Repair
    {"label": "had a serious argument with", "score": 5, "category": "conflict_repair", "freq":False,"duration":False},
    {"label": "overcame a serious conflict", "score": 6, "category": "conflict_repair", "freq":True,"duration":False},

    # Crisis
    {"label": "experienced emotional crisis", "score": 6, "category": "crisis", "freq":True,"duration":True},
    {"label": "experienced actual crisis", "score": 7, "category": "crisis", "freq":True,"duration":True},
    {"label": "have seen pushed to their limit", "score": 8, "category": "crisis", "freq":False,"duration":False},
    {"label": "have been sick around", "score": 6, "category": "crisis", "freq":True,"duration":True},
    {"label": "have been ugly around", "score": 6, "category": "crisis", "freq":True,"duration":True},
    {"label": "have seen intoxicated", "score": 5, "category": "crisis", "freq":True,"duration":False},

    # Shared experience
    {"label": "roadtripped", "score": 6, "category": "shared_experience", "freq":False,"duration":True},
    {"label": "worked together daily", "score": 6, "category": "shared_experience", "freq":False,"duration":True},
    {"label": "built a little project together", "score": 4, "category": "shared_experience", "freq":True,"duration":True},
    {"label": "built a big project together", "score": 7, "category": "shared_experience", "freq":True,"duration":True},

    # Responsibility
    {"label": "have depended on", "score": 7, "category": "responsibility", "freq":True,"duration":True},
    {"label": "have cared for", "score": 8, "category": "responsibility", "freq":False,"duration":True},
    {"label": "shared a bank account", "score": 9, "category": "responsibility", "freq":False,"duration":True},
    {"label": "had a child together", "score": 10, "category": "responsibility", "freq":False,"duration":True},
    {"label": "raised a child together", "score": 10, "category": "responsibility", "freq":True,"duration":True},
]


# --------------------------------------------------
# DIMINISHING RETURN MODIFIERS
# --------------------------------------------------

def experience_score(weight, frequency=1):
    """
    Diminishing returns on repeated exposure.
    """
    return weight * (1 - math.exp(-0.3 * frequency))

def frequency_modifier(freq):
    """
    Log scaling.
    First few events matter most.
    """
    if freq <= 1:
        return 1
    return 1 + math.log1p(freq) / 3


def duration_modifier(months):
    """
    Square-root scaling.
    Long time matters, but compresses.
    """
    if months <= 0:
        return 1
    return 1 + (math.sqrt(months) / 10)

def endurance_score(years_known): #how long have you known this person?
    """
    Slow logarithmic growth.
    Prevents 40 years from being 4x 10 years.
    """
    return 2 * math.log1p(years_known)


def compute_effective_score(item, freq=1, months=0):
    base = item["base"]

    f_mod = frequency_modifier(freq) if item["freq"] else 1
    d_mod = duration_modifier(months) if item["duration"] else 1

    return base * f_mod * d_mod





FAMILIARITY_INDEX = [ #default values; users should probably customize...
    {"read a book about":1},               # experienced through narrative
    {"read a book by":2},                  # experienced through art
    {"have seen in person": 2},            # minimal contact, low intimacy
    {"stalked online":3},                  # witnessed their self curation
    {"hung out in person": 3},             # casual exposure
    {"hung out alone together":4},         # one on one time, shows interest
    {"have been to their house": 5},       # mild trust
    {"grew up together":5},                # childhood friends
    {"known since childhood":4},           #
    {"made out": 5},                       # moderate physical intimacy
    {"have seen in underwear": 5},         # moderate vulnerability
    {"have seen naked": 6},                # higher vulnerability
    {"hooked up": 6},                      # moderate sexual intimacy
    {"met their family": 6},               # not everyone has family...
    {"they met your family": 6},           # not everyone has family...
    {"raw dogged": 7},                     # higher sexual intimacy / risk
    {"lived together": 7},                 # have seen daily
    {"had a child together": 6},          # maximum long-term bonding
    {"raised a child together": 10},       # extreme shared responsibility
    {"chatted with":2},                    # just basic conversation
    {"discussed life events": 4},          # moderate emotional sharing
    {"discussed values": 5},               # deeper emotional / cognitive sharing
    {"had a serious argument with": 5},    # navigated tension
    {"overcame a serious conflict": 6},    # worked it out
    {"experienced emotional crisis": 6},   # high trust, high intensity
    {"experienced actual crisis": 7},      # high trust, high intensity
    {"have seen cry": 5},                  # moderate emotional exposure
    {"cried with": 6},                     # mutual emotional vulnerability
    {"have seen intoxicated": 5},          # moderate shared risk/embarrassment
    {"roadtripped": 6},                    # high shared experience
    {"worked together daily": 6},          # know their baseline, professionally
    {"built a little project together": 4},# low-medium shared effort
    {"built a big project together": 7},   # high shared effort / dependency
    {"have depended on": 7},               # practical trust
    {"have cared for": 8},                 # caregiving intimacy
    {"have been sick around": 6},          # vulnerability, trust
    {"have been ugly around": 6},          # vulnerability, comfort
    {"have seen pushed to their limit": 8},# extreme exposure
    {"shared secrets": 7},                 # trust, cognitive intimacy
    {"shared a bank account": 9},          # high financial & trust intimacy
    {"are/were married": 10},              #there's always Vegas, but still...
]
#Familiarity penalties for kids
#Familiarity penalties for parasocial (Parasocial knowledge should have its own relative bracket: theoretical knowledge vs firsthand knowledge)

def max_familiarity_score(familiarity_index):
    """Compute the sum of all maximum familiarity points."""
    return sum(list(item.values())[0] for item in familiarity_index)

MAX_THEORETICAL_SCORE = max_familiarity_score(FAMILIARITY_INDEX)
# def normalized_familiarity_score(raw_score):
#     midpoint = 80  # where familiarity feels "serious"
#     steepness = 0.04
#     score = 10 / (1 + math.exp(-steepness * (raw_score - midpoint)))
#     return round(score, 2)

SATURATION_POINT = 80  # empirical threshold where intimacy feels complete

#this should work better
def normalized_familiarity_score(raw_score):
    score = 10 * (1 - math.exp(-raw_score / SATURATION_POINT))
    return round(score, 2)

#Not yet deployed
TIME_TOGETHER = [ #how time together is spent
    "art or music",
    "building or fixing", #known like a second skin
    "chilling", #intimately familiar
    "earning income",
    "studying or research",
    "conversing",
    "athletics",
    "games (in person)",
    "games (videogames)",
    "internet",
    "performance/entertaining",
    "media intake (watching shows/movies or book club)",
    "caregiving/stewardship",
    "group/community/family events",
    "just lurking",
    "exploring/adventuring",
    "shopping",
    "medical/healthcare"
    "drugs",
    "mentoring/advising/emotional support",
    "gossip",
    "sex",
    "schmoozing/seducing",
    "defending against",
    "debating or sparring",
    "deflecting/avoiding",
    "economic support",
    "protecting/being protected by",
    "n/a", #haven't spent time with
]

#Relation_State is not yet deployed
RELATION_STATE = [
    "active: constant",
    "active: frequent",
    "as-needed: transactional",
    "gated: hard to access",
    "inherited: fatefully bounded (work/family)" #work/family
    "distant: reluctantly estranged",
    "vague: ghosted?",
    "terminated: abruptly severed",
    "never met (parasocial)",
    "unspecified",
]

#Relation_State is not yet deployed
ALIGNMENT = [
    "gleefully malevolent", #you might love them, but they could still be a problem
    "consciously destructive",
    "enabler of enemies",
    "misguided",
    "mixed bag / irrelevant",
    "some overlapping concerns",
    "broadly supportive",
    "bloodsworn united front",
    "unspecified",
]

#tbc
SOCIAL_ROLE = [
    "Mary Ann", #useful/skillful
    "Ginger", #CHA
    "nerdy", #INT
    "outsider", #rebellious & courageous
    "shark", #athletes & business predators
    "plow-horse", #can endure
]

#enneagram (approximated)
ENNEAGRAM = {
#if sign, house, body, or nakshatra exists in this constant, add its weight within the chart to the sum of the enneagram type number. 
#Positions and aspects must be parsed differently. First, parse the position string so it's algorithmically recognizeable with actual chart positions in the given chart. Then - if take that chart's sign weight, body weight and house weight
    1:{ #sample size was 77, so that's ok, but could be better.
        "signs":{"Scorpio","Virgo","Cancer"}, #yeah, Cancer surprised me but that's what the data shows. My original guess was Virgo, Scorpio, Aquarius, Capricorn.
        "antisigns":{"Sagittarius"}, #subtract these
        "houses":{1,3,10}, #it is a h10 thing, that's legit
        "antihouses":{4,9,5}, #>5% negative correlations in the dataset of 77
        "bodies":{}, #you'd think there'd be strong saturn, but no; maybe just because maybe it's more the character of Saturn (body dynamics) than generic Saturn dominance (body weight).
        "antibodies":{},
        "nakshatras":{"Purva Phalguni","Swati","Bharani",}, #I thought Purva Ashadha would be positively represented, but it was the strongest negative correlation! Maybe this is a flaw in my qualitative data ranking...
        "antinakshatras":{}, #not including Purva Ashadha yet because I feel like maybe I made a mistake...
        "positions":{"Juno in Scorpio","Moon in H8","Moon in H1","Mercury in H3","Aquarius in H4","Sagittarius in H12","Capricorn in H1"}, #Neptune square Uranus was included, too, but since that's generational, I didn't want to  include it. Was it a fluke or not? Don't know...might imply some generations are more idealistic?
        "antipositions":{},
        "aspects":{"Moon square Pallas","Mars trine Pallas","DS trine Mars","AS sextile Pluto","AS square Sun","DS trine Pluto","Jupiter sextile MC","Chiron sextile IC","DS square Juno","DS conjunction Moon","Ketu square Mercury","Mercury trine Saturn","Moon trine Vesta","Juno sextile Mercury","Mars sextile Pallas",},
        "antiaspects":{"Neptune sextile Pluto"},
        "gates":{7,62,4,12,42,61,37,3},
        "antigates":{34,57,20,46,58,19,60,5,56,38,19,56},
        #"channels":{[24,61],},
        #"antichannels":{[20,34],[34,57],[20,57]},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#f5f5f5",
        "motivation":"Perfection, correctness",
        "description":"1s dream of a better world, which begins with themselves. Their scope for seeking the betterness of things may occupy any scale - personal (rigorous regimen to become virtuosic and/or to obliterate one's personal flaws), intimate (seeking to correct the flaws of others), or global/collective (trying to correct perceived flaws in the world and/or its systems at large).",
        "quotes":{"'I don't care if it hurts. / I want to have control. / I want a perfect body. / I want a perfect soul.' - Thom Yorke, Creep"}
        },
    2:{
        "signs":{"Libra","Capricorn","Cancer"}, #Pisces dominance were average in my meager sample of 22. Need a bigger sample, but gotta listen to the data for now.
        "antisigns":{"Gemini",},
        "houses":{11,6,}, 
        "antihouses":{},
        "bodies":{"Sun","Venus","Ceres","Chiron","Neptune"}, #Venus was the biggest indicator! But is that because they were known for being service-oriented??
        "antibodies":{"Mars",}, #moon dominange is just below avg in selection; busy looking out for #1, evidently
        "nakshatras":{"Purva Ashadha","Pushya","Shatabhisha","Punarvasu","Bharani","Uttara Bhadrapada"},
        "antinakshatras":{"Krittika","Purva Bhadrapada","Vishakha"}, #the 'bad' gems, and 'bad' pisces...hahaha
        "positions":{"Chiron in H12","Juno in H5","Ketu in H1","Neptune in H6","Rahu in H7","Venus in H11","Venus in H3","Ceres in H1","Ceres in H4","Chiron in H3","Juno in H1","Neptune in H11","Rahu in H8","Virgo in H2","Libra in H3","Mars in Cancer","Vesta in Cancer","Moon in Cancer","Moon in Pisces","Neptune in Capricorn","Pluto in Scorpio","Juno in Scorpio","Jupiter in Cancer","Pallas in Aquarius","Fortune in Capricorn","Sun in Taurus","Ceres in Aquarius","Chiron in Leo","Sun in Taurus","Vesta in Taurus","Jupiter in Libra","Moon in Virgo","Rahu in Pisces","Sun in Cancer","Sun in Capricorn","AS in Cancer","AS in Capricorn","Juno in Cancer","Pallas in Scorpio","Venus in Pisces","Scorpio in H4","Taurus in H10","Juno in H1",},
        #these were true for people working in healthcare, but not my list of 'e2s': {"Rahu in Pisces","Moon in Cancer","Chiron in Pisces","Ceres in Pisces","Mars in Pisces","Vesta in H4", "Taurus in H10","Neptune in H4","Ceres in H11"},
        "antipositions":{"Chiron in Pisces","Chiron in Aries","Taurus in H1","Venus in Libra","Gemini in H1","Uranus in Aries","Sun in Pisces","Pluto in Virgo",}, 
        #have another look at aspects for e2, cos I added a bunch and now it might have changed the data:
        "aspects":{"Ceres trine Jupiter","Ceres sextile Juno","Saturn square True Lilith","Ceres trine Moon","AS trine Juno","Ceres opposition Neptune","Ceres sextile Mercury","Ceres sextile Fortune","Juno sextile Ketu","Ketu conjunction Sun","Ketu square Neptune","Mars trine Fortune","Mars trine Rahu","Neptune square Rahu","Pallas sextile Pluto","True Lilith sextile Venus","Venus sextile Vesta","Ceres conjunction Moon",}, #wow, Neptune is super at odds with e2?? And the Moon can work cooperatively, but only if Ceres inspires it, or if Juno is involved.
        #these were aspects for healthcare workers, not e2s:{"Ceres sextile Mercury","Chiron trine Vesta","Chiron trine True Lilith","Juno trine Neptune","Mercury trine Neptune","Ketu trine Venus","Ketu square Venus"},
        "antiaspects":{},
        "gates":{58,62,50,13,45,47,52,61,17,},
        "antigates":{34,43,14,26,9,57,22,64,51,29,31,4,},
        "channels":{},
        "antichannels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#cc9900",
        "motivation":"To be useful & necessary to others",
        "description":"2s want to be indispensible to others. They need to be needed. They can only feel that they matter if others depend on them.",
        "quotes":{"'When you're weary / Feeling small / When tears are in your eyes / I will dry them all / I'm on your side. / Oh, when times get rough, / And friends just can't be found...' - Simon & Garfunkel, Bridge Over Troubled Water"},
        },
    3:{ #no actual data formally assessed & documented; purely theoretical rn based on loose past observations
        "signs":{"Libra","Scorpio","Aries","Sagittarius","Leo"}, #my initial guesses: "Leo","Capricorn","Taurus","Sagittarius","Libra". I checked "Leo dominant" and saw a lot of subtler probable 3s I'd missed because they were tasteful & well adjusted about it.
        "antisigns":{"Virgo","Pisces","Gemini"},
        "houses":{8}, #it's about power in society, I guess? Domination through community?
        "antihouses":{1}, #1 doesn't seem to need external validation.
        "bodies":{"Sun","Mars","Jupiter",},
        "antibodies":{"Mercury","Venus","Moon"},
        "nakshatras":{"Ashwini","Jyestha","Revati","Uttara Ashadha","Vishakha","Hasta"}, #original guesses: "Vishakha","Jyestha","Ashlesha","Magha",
        "antinakshatras":{"Purva Phalguni","Krittika"}, 
        "positions":{"Ketu in Capricorn","Chiron in H2","Mars in Aries","Ceres in Aries","Ketu in Sagittarius","Sun in Taurus","Scorpio in H4","Taurus in H10","Cancer in H1","Leo in H1","Aries in H10",}, #sun in Leo is not supported by the data so far, but I believe it's what I've seen in the wild, so I put it on there.
        "antipositions":{"Chiron in Pisces","Uranus in Virgo","Rahu in H1","Pluto in H12","Saturn in H3","Sun in H12","Uranus in H10","Venus in H11","Vesta in H11","Ceres in H5","Chiron in H9","Jupiter in H2","Mars in H6","Vesta in H10","Vesta in H1","Lilith in H4",},
        "aspects":{"Jupiter sextile Sun","Mercury trine Moon","Saturn trine Sun","Ketu trine Moon","Mars sextile Mercury","Moon trine Rahu","Mars sextile Sun","Moon trine Sun","Ceres square Juno","Saturn trine Uranus","Ceres square Moon","Chiron square Lilith","Ketu square Vesta","Ketu trine Sun","Mercury semisextile Venus","Mercury square Pluto","Pallas sextile Sun","AS trine Lilith","Rahu square Vesta","Juno conjunction Fortune","Ketu trine Pallas","Lilith sextile Venus","Mars opposition Fortune","Pallas conjunction Pluto","Fortune conjunction Pluto","IC sextile Vesta","IC square Mars","IC trine Venus","MC square Mars","MC trine Vesta","AS sextile Vesta","AS square Saturn",},
        "antiaspects":{},
        "gates":{50,34,9,32,5,58,42,54,},
        "antigates":{59,26,12,55,15,6,36,13,23,},
        #"channels":{},
        #"antichannels":{[23,43]},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#ffff00",
        "motivation":"Visible recognition, status and achievement",
        "description":"3s are sort of narcissist-coded, but that doesn't have to be malignant. It can result in materialism, or it could result in extreme competence. Sometimes 3s are mistaken for 1s because they appear driven by perfectionism. But rather than pursuit of perfection/ideals (e1) or competence (e5) for their own sake, 3s are driven by the pursuit of recognition for that competence. Arguably, the easier the trophies and accolades come, the less hard 3s will need to try. The point here is not the conditions of victory, but the recognition of their superiority over others; the status and attention of being president more than the power of owning the red button. They will live and die for that gold star on their paper, and the knowledge that other people know they got it.",
        "quotes":{"'There's been a lot of compromisin' / on the road to my horizon... / but I'm gonna be / where the lights are shinin' on me...' - Glen Campbell, Rhinestone Cowboy"},
        },
    4:{
        "signs":{"Aquarius","Pisces"}, #theoretically: "Pisces","Aquarius","Scorpio","Sagittarius". I found out that Aquarius dominant charts *are* the weirdest in agregate. But not all Aquarius dominant charts show it.
        "antisigns":{"Leo",},
        "houses":{1},
        "antihouses":{},
        "bodies":{}, #theoretically: "Uranus","Lilith"
        "antibodies":{},
        "nakshatras":{"Purva Bhadrapada","Shatabhisha",}, #theoretically: "Ardra","Purva Bhadrapada","Revati"
        "antinakshatras":{}, 
        "positions":{"Sun in Pisces","Rahu in Pisces","Cancer in H4","Chiron in H5","Jupiter in H6","Venus in H1","Mercury in H2","Pallas in Pisces","Pallas in Aquarius","Ceres in Pisces","Mercury in Pisces",}, #theoretically: "Mercury in Pisces","Mars in Pisces","Pluto in Scorpio","Ketu in H8"
        "antipositions":{},
        "aspects":{"Ketu sextile Vesta","Jupiter square Pallas","Moon conjunction Rahu","MC square Sun"},
        "antiaspects":{},
        "gates":{59,36,22,46,53,55,16,25,24},
        "antigates":{1,60,8,13,57,43,48,64,3,56,63,},
        "channels":{},
        "antichannels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#cc66ff",
        "motivation":"Individuality, depth of experience & authenticity",
        "description":"4s don't mind if you think they're a freak. They want a genuine experience, be it the depths of pain or pleasure. They want beauty, but see beauty and truth as inseparable, so we aren't talking Kpop symmetry and Kardashians; we're talking scar-faced midwives, Edward James Olmos' face, Bukowski poems, Philip-Lorca diCorcia photos, Disco Elysium, David Lynch and Adrienne Shelly indie flicks. They can be goth-coded, but they aren't all goths. Many seek originality and ways of distinguishing themselves from the mainstream, but that may be just a reaction to the inauthenticity of the mainstream. There's a lot of BS backstory lore on e4s by major voices in Enneagram theory who say stuff like 'e4s feel there's an essential part of themselves missing' or are driven by self-pity and similar nonsense. It's all rubbish written by people who clearly don't understand them. Like their moms. *slams door*",
        "quotes":{"'Drink up one more time / and I'll make you mine, / keep you apart, / deep in my heart / separate from the rest, / where I like you the best-- / and keep the things you forgot...' - Elliott Smith, Between the Bars","'Baby, do you understand me now? / Sometimes I feel a little mad... / Don't you know no one alive can always be an angel.../ When things go wrong, I seem to be bad.  - The Animals, Don't Let Me Be Misunderstood","Marge: Why all the black? / Homer: Why all the pearls? Why all the hair? Why anything? - The Simpsons"},
        },
    5:{
        "signs":{"Aries","Cancer","Taurus",}, #I checked, and Gemini dominant people are usually e7, not e5. e5 geminis are a minority, even though I know several 'super geminis' who are e5; they're all Saturnian Geminis; it's a different thing than standard gemini. 
        "antisigns":{"Leo","Sagittarius"},
        "houses":{3,9},
        "antihouses":{},
        "bodies":{"Uranus","Venus"}, #"Mercury","Pluto","Pallas"
        "antibodies":{"Sun","Mars","Jupiter"},
        "nakshatras":{"Bharani","Punarvasu"}, #"Swati","Anuradha","Shatabhisha","Krittika"
        "antinakshatras":{"Swati","Jyestha"}, 
        "positions":{"Mars in Capricorn","Mercury in Gemini","Mercury in Virgo","Mercury in Scorpio","Mercury in Aquarius"},
        "antipositions":{},
        "aspects":{},
        "antiaspects":{},
        "gates":{1,57,17,21,23,49,7,10,39,46,8,3,30,52,2,25,51,61},
        "antigates":{5,28,29,15,34,54,20,19,63,9,44,47,56,59,50,40,12},
        "channels":{},
        "antichannels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#669900",
        "motivation":"Knowledge & information, personal autonomy",
        "description":"5s want to understand the world, whether through a microscope or a telescope. They generally perceive themselves as on the outside, looking in at the experiment of existence. They go to great pains to ensure that their lab is protected so that their subjects (the outside world) cannot touch them, messy their lab and disrupt their experiments.",
        "quotes":{"'I'm so glad I got burned, / think of all the things we learned / from the people who are / still alive. / And believe me I'm still alive. / I'm doing science and I'm still alive.' - Portal Soundtrack, Still Alive","'There is research to be done, / and we made a neat gun / for the people who are / still alive...' - Portal soundtrack, Still Alive","'Well they gave me medication so I feel how I imagine people of average intelligence feel all the time.' - Dr. Temperance Bones, Bones"},
        },
    6:{
        "signs":{"Aries","Virgo","Capricorn"},
        "antisigns":{"Scorpio","Sagittarius"},
        "houses":{12,6,2,},
        "antihouses":{},
        "bodies":{"Sun"},
        "antibodies":{"Saturn","Jupiter"},
        "nakshatras":{"Uttara Ashadha","Bharani","Punarvasu","Shatabhisha","Pushya",},
        "antinakshatras":{"Chitra"}, 
        "positions":{"Chiron in H3","Jupiter in H3","Pallas in H10","Mars in H11","Mercury in H2","Pluto in H8","Ceres in H11","Ketu in H5","Neptune in H9","Fortune in H8","Pluto in H5","Rahu in H11","Saturn in H12","Vesta in H4","Uranus in H11","Vesta in H5","Pluto in Leo","Libra in H10","Neptune in Libra","Neptune in Virgo","Juno in Capricorn","Mars in Taurus","Pallas in Pisces","Ceres in Aries","Mercury in Virgo","Lilith in Libra","Juno in Leo",},
        "antipositions":{"Capricorn in H11","Aquarius in H12","Leo in H6","Pisces in H3","Virgo in H9","Chiron in Aries","Sun in H10","Neptune in Sagittarius","Pluto in Libra","Juno in Scorpio","Jupiter in Cancer"},
        "aspects":{"Chiron square Jupiter","Mercury conjunction Sun","Mars trine Vesta","Lilith square Vesta","Juno sextile Moon","Moon square Neptune","Mars trine Pallas","Rahu trine Saturn","Ceres square Uranus","Ketu square Lillith","Mars trine Neptune","Mercury trine Neptune","Neptune sextile Lilith","Fortune conjunction Sun","Rahu square Lillith","DS trine Jupiter","Pallas sextile Saturn","Pallas square Rahu","AS sextile Jupiter","AS trine Vesta","Ceres biquintile Jupiter","IC trine Moon","Moon quincunx Pluto","AS conjunction Lilith","AS trine Mars","AS trine Pluto"},
        "antiaspects":{"Chiron trine Neptune"},
        "gates":{12,32,40,3,11,42,54,},
        "antigates":{28,26,58,15,18,64,55,41,17},
        #"channels":{[12,22],[37,40]},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "antichannels":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#0099cc",
        "motivation":"Duty, performing perceived social role & fulfilling personal responsibilities.",
        "description":"6s are generally here to maintain their view of the status quo, upholding their recognized hierarchy, and support their tribe. This can look very different depending on who they recognize as their authority figure (leader), and who/what they believe is their tribe (which can exist at varying scales from the very personal to the very global). Independent of scale, they will expect members of their perceived tribe to fulfill their responsibilities/duties/roles within the tribe as well. In the creator of this app's opinion, there is no 'counterphobic 6' as lore suggests - just one type of 6, who is always deferential to role models, even if the early Recognized Tribal Authority was Hunter S Thompson, Charlton Heston or the Unibomber. Saying e6 is about 'security' is tautological; the entire enneagram is about how individuals seek a sense of security; e6 seeks it through tribal role participation'.",
        "quotes":{"'If I'd said that to MY daddy, he'd have...[insert reflection on one's father's archetypal behavior, intended as a model of exemplary response to the situation]' - a phrase often invoked by nearly everyone in the American South & Bible Belt.","'Three weeks from now, I will be harvesting my crops. Imagine where you will be, and it will be so. Hold the line! Stay with me! If you find yourself alone, riding in the green fields with the sun on your face, do not be troubled. For you are in Elysium, and you're already dead! Brothers, what we do in life echoes in eternity...' - Maximus, Gladiator","'Five thousand of my men are out there in the freezing mud. Three thousand of them are bloodied and cleaved. Two thousand will never leave this place. I will not believe that they fought and died for nothing.' - Maximus, Gladiator","'Sometimes I do what I want to do. The rest of the time, I do what I have to.' - Cicero, Gladiator","'You have a great name. He must kill your name before he kills you.' - Juba, Gladiator",},
        }, #"'Elephants are not purple. This is wrong.' - Dr. Temperance Bones, Bones"
    7:{
        "signs":{"Gemini","Sagittarius","Pisces"},
        "antisigns":{"Scorpio","Libra"},
        "houses":{5},
        "antihouses":{},
        "bodies":{"Jupiter","Sun"},
        "antibodies":{"Mars","Pluto"},
        "nakshatras":{"Rohini","Ashwini","Shravana","Purva Phalguni"},
        "antinakshatras":{}, 
        "positions":{"Pisces in H4","Neptune in Sagittarius","Venus in Aquarius","Venus in H3","Scorpio in H12"},
        "antipositions":{"Scorpio in H1"},
        "aspects":{},
        "antiaspects":{},
        "gates":{43,54},
        "antigates":{},
        "channels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "antichannels":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#ff33cc",
        "motivation":"Escaping adversity, embracing pleasure",
        "description":"Essentially, 7s are about a blend of hedonism and epicurianism. They are here to enjoy life, and avoid what detracts from that enjoyment.",
        "quotes":{"'Hey, I just met you / and this is crazy / but here's my number / so call me maybe...' - Carly Rae Jepsen, Call Me Maybe","'This is the day you will always remember as the day you almost caught Captain Jack Sparrow.' - Capt. Jack Sparrow, Pirates of the Caribbean","'What’s the hassle, Schmasel?' - Bugs Bunny","'Well, like the Romans always say … E pluribus uranium.' - Bugs Bunny"},
        },
    8:{
        "signs":{"Aries","Libra"}, #"Sagittarius","Leo"
        "antisigns":{},
        "houses":{10,4},
        "antihouses":{},
        "bodies":{"Mars","Pluto"},
        "antibodies":{"Neptune",},
        "nakshatras":{"Jyestha","Uttara Phalguni","Swati"}, #"Purva Bhadrapada","Krittika","Chitra"
        "antinakshatras":{}, 
        "positions":{"Moon in Aries","Chiron in Pisces","Ceres in Leo","Pallas in Cancer","Moon in H1","Pluto in H10","Ceres in H4","Vesta in H10",},
        "antipositions":{"Sagittarius in H1","Rahu in H12","Venus in H3","Taurus in H6","Capricorn in H2","Cancer in H8"},
        "aspects":{"Chiron opposition Pluto","Jupiter square Rahu","Jupiter trine Mars","Pallas sextile Saturn"},
        "antiaspects":{},
        "gates":{44,32,62,49,12,},
        "antigates":{55,24,18,58},
        "channels":{},
        "antichannels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "color":"#ff0000",
        "motivation":"Personal sovereignty, dominance, asserting control",
        "description":"3s may pursue dominance through material recognition and social status. 8s will pursue it by any means necessary. Power not for social validation, not as a conditioned social response that recognizes and values the established institutions and wishes to perform within them, but potentially outside them. Whatever it takes to be in control, or at very least to avoid being controlled by others.",
        "quotes":{"'You know the way to stop me / but you don't have the discipline. / How many nights have I prayed for this? / To let my work begin...! / First we take Manhattan... / then we take Berlin!' - Leonard Cohen, First We Take Manhattan","'They’re whispering his name across this disappearing land / But hidden in his coat is a red right hand... / You ain’t got no money? / He’ll get you some / You ain’t got no car? / He’ll get you one / You ain’t got no self-respect, you feel like an insect / Well don’t you worry buddy, cause here he comes...' - Nick Cave, Red Right Hand","'People should know when they're conquered.' - Quintus, Gladiator"},
        },
    9:{
        "signs":{"Capricorn","Cancer","Sagittarius"}, #Aries also came up
        "antisigns":{"Gemini","Leo","Aquarius","Virgo"},
        "houses":{4,5,6},
        "antihouses":{2,1,8,9},
        "bodies":{"Sun","Moon"},
        "antibodies":{"Mars","Mercury"},
        "nakshatras":{"Ardra","Dhanishta","Shatabhisha","Uttara Bhadrapada",}, #Jyestha came up, but I think they're faking it
        "antinakshatras":{"Uttara Phalguni","Swati"}, 
        "positions":{"Virgo in H4","Pisces in H10","Pisces in H4","Virgo in H10","Neptune in Scorpio","Neptune in Capricorn","Pluto in Scorpio","Uranus in Capricorn","Chiron in Taurus","Pallas in Pisces","Jupiter in Cancer","Fortune in Aquarius","Cancer in H1","Moon in Leo","Moon in Sagittarius","Neptune in Aquarius","Pluto in Sagittarius","Saturn in Taurus","Ceres in Sagittarius","Ceres in Taurus","Juno in Aquarius","Juno in Libra","Mercury in Cancer","Mercury in Libra","Moon in Aries","Saturn in Capricorn","Sun in Capricorn","Sun in Pisces","Lilith in Aries","Uranus in Aquarius","Uranus in Scorpio","Neptune in H6","Moon in H4","Fortune in H6","Pluto in H4","Uranus in H5","Chiron in H11","Chiron in H12","Mars in H4","Ketu in H9","Rahu in H3","Saturn in H3","Sun in H4","Uranus in H10","Fortune in H3","Venus in H5","Venus in H7","Vesta in H6",},#"Sun in Pisces","Sun in Libra","Sun in Virgo","Moon in Leo","Moon in Aries","Moon in Sagittarius","Mercury in Aquarius","Mercury in Cancer","Mercury in Libra","Venus in Capricorn","Venus in Aries","Mars in Leo","Mars in Libra","Mars in Pisces","Jupiter in Cancer","Saturn in Taurus","Saturn in Capricorn"},
        "antipositions":{"Neptune in Libra","Pallas in Aquarius","Pluto in Leo",},#"Sun in Taurus","Sun in Scorpio","Sun in Leo","Sun in Aquarius","Moon in Aquarius","Moon in Taurus","Moon in Gemini","Moon in Cancer","Moon in Virgo","Moon in Capricorn","Mercury in Gemini","Mercury in Scorpio","Mercury in Pisces","Mercury in Leo","Venus in Sagittarius",,"Mars in Scorpio","Mars in Capricorn","Saturn in Aquarius","Mars in Aquarius"},
        "aspects":{"Pallas trine Pluto","Chiron trine Jupiter","Juno trine Saturn","Chiron sextile Juno","Neptune sextile Pallas","Pallas square Vesta","Saturn trine Sun","Ceres opposition Jupiter","Ceres sextile Fortune","Ceres trine Moon","Chiron opposition Saturn","Juno trine Mars","Juno trine Uranus","Ketu trine Neptune","Mercury square Moon","Moon sextile Uranus","Mars trine Neptune","Moon square Sun","Neptune quincunx Sun","Neptune square Fortune","Saturn trine Venus","Ceres sextile Rahu","Ceres sextile Sun","Ceres trine Ketu","Chiron trine Fortune","Juno conjunction Mercury","Juno square Moon","Jupiter opposition Sun","Mars sextile Pluto","Fortune opposition Lilith","IC sextile Uranus","IC trine Jupiter"},
        "antiaspects":{},
        "gates":{20,5,54,18,58,26,48,63,8,9,17,30,52,55},
        "antigates":{1,44,50,6,33,43,2,60,4,42,49,7,3,24},
        #"channels":{[20,57],[18,58],[37,40],[17,62],[4,63]},
        #"antichannels":{},
        "centers":{"Root"},
        "anticenters":{"Sacral"},
        "profiles":{},
        "antiprofiles":{"1/4","4/1","2/5"},
        "authorities":{"Sacral"},
        "antiauthorities":{},
        "bazisigns":{"Snake",},
        "antibazisigns":{"Dragon","Tiger",},
        "color":"#cc99ff",
        "motivation":"Tranquility. Maintaining harmony at any cost",
        "description":"9s just want peace. They want everyone to get along. Unlike 1s, they won't generally lash out at those disrupting the peace, but will quietly brood and retreat from those who cause chaos and disharmony. If they ever choose to stand for anything, it would likely be a stand for nonviolence, a stand to end conflict. They can be hard to recognize because they often adapt & shapeshift as a means of keeping peace.",
        "quotes":{"'Well, you may say that I'm a dreamer / but I'm not the only one. / I hope someday you'll join us... / and the world can live as one.' - John Lennon, Imagine"},
        },
} #no one knows wtf Hasta wants. lol Bharani is hunger, but not in a chill or fun way. Uttara Phalguni for e2 is experimental. P. Phal is experimental for e7 but seems to fit.

ENNEAGRAM_REALMS = {
    "heart" : {"signs":{"Pisces","Cancer","Scorpio","Leo"},"houses":{4,5,7,10,}},
    "head" : {"signs":{"Aries","Virgo","Aquarius","Libra","Gemini"},"houses":{1,3,9,11}},
    "body" : {"signs":{"Capricorn","Taurus","Leo","Sagittarius","Virgo"},"houses":{2,6,8,12}},
}

ENNEAGRAM_VARIANTS = { #the scale/scope of one's focus. Gemini has no evident preference, as far as I can tell. Capricorns technically operate at any scope, but their bottom line is always sp, I think.
    "sp":{"signs":{"Taurus","Capricorn","Aries","Sagittarius","Scorpio","Virgo"},"houses":{1,2,12},"bodies":{"Moon"},"nakshatras":{},"positions":{},"aspects":{},"color":"","description":"",},
    "sx":{"signs":{"Scorpio","Pisces","Cancer","Aries","Leo","Virgo",},"houses":{4,7,8},"bodies":{},"nakshatras":{},"positions":{},"aspects":{},"color":"","description":"",},
    "so":{"signs":{"Aquarius","Leo","Libra",},"houses":
     {9,10,11},"bodies":{},"nakshatras":{},"positions":{},"aspects":
     {},"color":"","description":"",}, }

MBTI_ELEMENTS = [
{"element":"fire","E":10,"S":10,"F":5,"P":5},
{"element":"water","E":0,"S":2.5,"F":10,"P":5},
{"element":"air","E":7.5,"S":0,"F":0,"P":10},
{"element":"earth","E":2.5,"S":7.5,"F":5,"P":0},
]

#this should be moved to the analysis/human design file
AWARENESS_STREAMS = [
{"name":"sensing","type":"ajna","gates":[64,47,11,56]},
{"name":"knowing","type":"ajna","gates":[61,24,43,23]},
{"name":"understanding","type":"ajna","gates":[63,4,17,62]},

{"name":"instinct","type":"spleen","gates":[54,32,44,26]},
{"name":"intuition","type":"spleen","gates":[38,28,57,20]},
{"name":"taste","type":"spleen","gates":[58,18,48,16]},

{"name":"sensitivity","type":"solar plexus","gates":[19,49,37,40]},
{"name":"emoting","type":"solar plexus","gates":[39,55,22,12]},
{"name":"feeling","type":"solar plexus","gates":[41,30,36,35]},
]

PREDICTIONS = { #when half or more of these things are true, give the chart the trait
    "sex symbol":{
        "signs":{"Libra","Leo"}, 
        "antisigns":{"Pisces"},
        "houses":{},
        "antihouses":{},
        "bodies":{"Mercury","Mars"},
        "antibodies":{"Pluto","Uranus","Saturn"},
        "nakshatras":{"Rohini","Punarvasu","Uttara Phalguni","Ashwini",}, 
        "antinakshatras":{"Purva Ashadha"}, 
        "positions":{"Chiron in Aries","Chiron in Taurus","Juno in Sagittarius","Jupiter in Scorpio","Cancer in H1","Juno in Libra","Ketu in H1","Moon in H7","Rahu in H7","Sun in H10","Venus in H10","Ketu in H7","Mars in H7","Mercury in H11","Lilith in H11","Rahu in H1","Fortune in H5","Neptune in H5","Saturn in H7"},
        "antipositions":{"Venus in Scorpio","Venus in Aquarius"},
        "aspects":{"Chiron trine Neptune","Juno trine Moon","Chiron sextile Mars","IC square Ketu","Mars square Mercury","MC square Rahu","Ceres trine Venus","Mercury semisextile Venus","Venus square Vesta","Chiron square Moon","Juno sextile Jupiter","Juno sector Neptune","Juno sextile Sun","Ketu trine Saturn",},
        "antiaspects":{},
        "gates":{18,62,14,19,35,25,49,63,},
        "antigates":{1,44,28,41,55,36,10,29,},
        #"channels":{},
        #"antichannels":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "bazisigns":{},
        "antibazisigns":{},
        "color":"#cc99ff",
        "subheader":"",
        "description":"",
        },
}

RODDEN_RATING = [
    {"grade":"AA", "data_source":"Official testimony", "description":"Data recorded by the family or state, such as a birth certificate, birth record, baptismal certificate, or family Bible."},
    {"grade":"A", "data_source":"Undocumented Testimony", "description":"Data quoted by the person, kin, friend, or associate, often based on memory or family legend, but lacking official documentation."},
    {"grade":"B", "data_source":"Biography","description":"Data substantiated by a quote in a biography or autobiography, which is considered reliable if the quote qualifies the information."},
    {"grade":"C", "data_source":"Caution", "description":"Data with no source or an ambiguous source, often found in magazines or journals without direct links to the origin."},
    {"grade":"DD", "data_source":"Conflicting","description":"Conflicting quotes that are unqualified, indicating multiple different birth times for the same person with no way to choose between them."},
    {"grade":"X", "data_source":"Time unknown","description":"Data with no time of birth provided."},
    {"grade":"XX", "data_source":"Date unconfirmed","description":"Data without a known or confirmed date."},
]







#COLOR SPECTRUM GENERATOR:
def get_blended_color(color1, color2, color3, color4, totalsteps, getstep):
    # accepts 4 anchor colors; blends in totalsteps; returns color at getstep

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def lerp(a, b, t):
        return round(a + (b - a) * t)

    if totalsteps <= 0:
        raise ValueError("totalsteps must be > 0")

    anchors = [hex_to_rgb(c) for c in (color1, color2, color3, color4)]

    # wrap getstep so any integer works
    t = (getstep % totalsteps) / totalsteps * 4
    segment = int(t) % 4
    frac = t - segment

    a = anchors[segment]
    b = anchors[(segment + 1) % 4]

    rgb = tuple(lerp(a[i], b[i], frac) for i in range(3))
    return rgb_to_hex(rgb)


def build_spectrum(color1, color2, color3, color4, totalsteps):
    return [
        get_blended_color(color1, color2, color3, color4, totalsteps, getstep)
        for getstep in range(totalsteps)
    ]


# example
SEASONAL_PALETTE = build_spectrum(
    SEASONAL_COLORS["spring"],
    SEASONAL_COLORS["summer"],
    SEASONAL_COLORS["fall"],
    SEASONAL_COLORS["winter"],
    12,
)
#print(SEASONAL_PALETTE)
#print(get_blended_color("#ccffcc", "#ffff00", "#cc3300", "#ccccff", 12, 7))
