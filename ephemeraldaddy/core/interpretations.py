from __future__ import annotations

import datetime
import math

from ephemeraldaddy.gui.style import DARK_THEME


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

#Here for reference but not imported to any other file.
OUTER_PLANETS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}  # slow / structural
INNER_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars"}       # fast / personal
ANGLES = {"AS", "DS", "MC", "IC"}

PERSONAL = INNER_PLANETS | ANGLES

NODES = {"Rahu", "Ketu"}
ASTEROIDS = {"Vesta", "Ceres", "Juno", "Pallas", "Lilith"}
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

SLOW_TRANSIT_BODIES = OUTER_PLANETS | NODES | ASTEROIDS
FAST_TRANSIT_BODIES = {"Sun","Mercury", "Venus", "Mars"}  # Sun, Moon, Mercury, Venus, Mars
VERY_FAST_TRANSIT_BODIES = {"Moon"}


NATAL_WEIGHT = { #aka NATAL_WEIGHT - use for calculating sign/planet/house/element dominance
    "Sun": 10,
    "Moon": 10,
    "AS": 10,
    "MC": 9,
    "IC": 7, #maybe 8
    "DS": 7, #maybe 8
    "Mercury": 7,
    "Venus": 7,
    "Mars": 7,
    "Jupiter": 6,
    "Saturn": 6,
    "Uranus": 6,
    "Neptune": 6,
    "Pluto": 6,
    "Rahu": 4,
    "Ketu": 4,
    "Chiron": 2,
    "Ceres": 2,
    "Lilith": 2,
    "Juno": 2,
    "Vesta": 2,
    "Pallas": 2,
    "Part of Fortune": 1,
}

# Back-compat alias used by aspect scoring helpers.
POSITION_WEIGHTS = NATAL_WEIGHT

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
    if planet_weights:
        p1_weight = float(planet_weights.get(p1, NATAL_WEIGHT.get(p1, 1)))
        p2_weight = float(planet_weights.get(p2, NATAL_WEIGHT.get(p2, 1)))
    else:
        p1_weight = float(NATAL_WEIGHT.get(p1, 1))
        p2_weight = float(NATAL_WEIGHT.get(p2, 1))
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

# PLANET_RULERSHIP_CLASSICAL = {
#     "Sun": {"Leo"},
#     "Moon": {"Cancer"},
#     "Mercury": {"Gemini", "Virgo"},
#     "Venus": {"Taurus", "Libra"},
#     "Mars": {"Aries","Scorpio"},
#     "Jupiter": {"Sagittarius","Pisces"},
#     "Saturn": {"Capricorn","Aquarius"},
# }

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
    "Earth": "#049534", #was #2e6b42
    "Air": "#999900", #was #8b73a3, #66527a
    "Water": "#5f5f8f", #was 2d2d5c
}

BAZI_ELEMENTS = {
    "wood": "#cccc00",
    "water": "#3333ff",
    "earth": "#009900",
    "fire": "#ff3300",
    "metal": "#669999",
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
    "Rahu": "#fffff0", #"ivory" - formerly #355A55 smoky teal, but we needed readability
    "Ketu": "#dcdcdc", #"gainsboro" - formerly #5A4A52 ash-violet, but we needed readability
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
    "Earth":"#339966", #slightly bluish green
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
    "quincunx":    "white",
    "semisquare":  "azure",
    "sesquiquadrate": "grey",
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
    "Jyeshtha": ("Mercury", PLANET_COLORS["Mercury"]),
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
        "archetypes": "The Comedian (sun), serial killer (moon, also sun/moon/asc), MMA (mars), lesser scream queens (all Ketu, but Mula is #1 by far)",
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
        "archetypes": "Artemis, serial killer (asc). Few millionaires/billionaires (moon).",
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
        "archetypes": "Ugly curse - beast needs love to heal/become beautiful (mostly male trope). #3 richest moon. #3 in ugly duckling glow up plots. Alt kids & offbeat beatnics.",
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
        "archetypes": "MMA (mars), occultist, lesser scream queens (all Ketu, but Mula is #1 by far)",
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
        "archetypes": "MMA (moon). #1 in ugly duckling glow up plots. Dr. Jekyl & Mr. Hyde / The Mask: Dangerous extremes finding profound balance (split personality, evil alternate self). Often begin with repressed \"nice person\" energy that tries to quarantine all their darkest impulses (which eventually emerge). Wild child / borderline PD.",
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
        "archetypes": "Tiger blood, killer instinct. Richest (moon). Show-off / bombastic.",
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
        "archetypes": "Belle, destroys/transforms the monster. Occult. To face & destroy artifice, to penetrate the mask, The Final Girl (lone survivor due to superior intelligence & resourcefulness), subdues the beast, The Strength card, superego beats the id, always the virgin, uses a fire poker, the beast often becomes obsessed with the mula",
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
        "archetypes": "Purification, the purge, black metal; funny moon. 2nd most artistic/creative.",
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
        "archetypes": "Least combative mars placement.",
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
        "archetypes": "Kali the Destroyer; serial killer & MMA (moon). #4 occultist (dom). Femme fatales. Ugly duckling glow up plots. Outsiders.",
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
        "verbs": ["curating narrative via", "impersonating", "absorbing", "joking about", "strategically re/framing", "evading", "adapting to", "editing", "charming", "cleverly navigating", "mimicking", "bypassing",],
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
            "self-contained","steady","skilled","quietly masterful",""
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
            "in an emotionally rich way", "alively", "creatively", "in a free-spirited way",
            "intensely", "originally", "surprisingly", "expressively", "rebelliously",
            "generatively", "charismatically", "in a self-redefining way",
        ],
        "worst_adverbs": [
            "in a disordered way", "unstably", "in a self-destructive way", "impulsively",
            "in a volatile way", "in an attention-seeking way", "recklessly",
            "in an overexposed way", "inconsistently", "messily", "in an ungrounded way",
            "dramatically", "explosively", "provocatively", "in a fractured way", "combustively",
        ],
        "profile":"wxnder",
        "verbs": ["distorting", "challening", "combusting", "reinventing", "disrupting", "electrifying", "exposing", "bleeding", "reclaiming", "detonating", "amplifying", "iconifying",],
        "core":"Drives toward freedom. Reinvents self to stay uncaged.",
        "strategy":"Identity through transformation. Expresses tension by breaking molds.",
        "function":"Must stay free. Tension magnet, not by intention—but because their aliveness offends the script. Can burn bridges to escape commitment. Emotionally catalytic.",
        "behavior": ["Can’t be held still.","Shifts shape with emotion and time.","Often lionized for what breaks them.",],
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
        "core":"Social engineer. Designs emotional space without centering self.",
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
        "strategy":"Carries both illumination and dissonance. Resists simplicity. ay implode from inner tension. Truth and distortion bleed together. Spiritually resonant. Subtly defiant. Embedded in culture’s nerve endings.",
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

# Example access:
# sign = "scorpio"
# one_sign_adverb = random.choice(SIGN_TRAITS[sign]["best_adverbs"])

PLANET_KEYWORDS = {
    "Sun": {
        "nouns": [
            "leadership", "decisions", "self-expression", "confidence", "focus", "presence",
            "direction", "authority", "organization", "responsibility", "visibility", "results",
        ],
        "verbs": [
            "leading", "feeling confident about", "expressing", "taking charge of", "setting goals with", "choosing",
            "focusing on", "showing up with", "exuding", "directing", "organizing", "finishing",
        ],
        "verbsonly": [
            "leading", "feeling confident", "expressing", "taking charge", "setting goals", "choosing",
            "focusing", "showing up", "exuding", "directing", "organizing", "finishing",
        ],
    },
    "Moon": {
        "nouns": [
            "reactivity","fears","feelings", "moods", "comfort", "rest", "needs", "home life",
            "memory", "care", "check-ins", "safety", "support", "recovery",
        ],
        "verbs": [
            "instinctually reacting to","experiencing emotion as", "noticing the moods of", "being nourished by", "seeking comfort from", "caring for","finding comfort in","seeking security from",
            "remembering", "checking in with", "settling down with", "protecting", "recharging with","feeling most comfortable with","experiencing subconscious as",
        ],
        "verbsonly": [
            "instinctually reacting","experiencing emotion", "noticing moods", "reacting", "seeking comfort", "caring","seeking security","finding comfort",
            "remembering", "checking in", "settling down", "protecting", "recharging","seeking familiarity","experiencing subconscious"
        ],
    },
    "Mercury": {
        "nouns": [
            "thinking","thought","mental processes","thoughts", "words", "questions", "data", "messages", "information",
            "writing", "reading", "plans", "notes", "details","communication",
        ],
        "verbs": [
            "thinking of", "talking about", "asking about", "answering", "writing", "reading",
            "explaining", "learning about", "planning with", "sorting", "editing", "messaging",
        ],
        "verbsonly": [
            "thinking", "talking", "asking", "answering", "writing", "reading",
            "explaining", "learning", "planning", "sorting", "editing", "messaging",
        ],
    },
    "Venus": {
        "nouns": [
            "interactions", "likes", "choices", "pleasures", "connections", "romances", "relationships",
            "sharing", "style", "spending", "savings", "values", "appreciation","enjoyments",
        ],
        "verbs": [
            "socializing with","liking", "adoring", "reveling in", "choosing", "enjoying", "connecting with", "flirting with", "dating by way of","attraction to","engaging with others as",
            "sharing", "decorating", "reveling in the beauty of", "appreciating", "savoring", "valuing","socializing by way of","making an art out of","interpreting femininity as",
        ],
        "verbsonly": [
            "socializing","liking", "adoring", "reveling", "choosing", "enjoying", "connecting", "flirting", "dating","attraction","engaging with others",
            "sharing", "decorating", "reveling in beauty", "appreciating", "savoring", "valuing","socializing","interpreting femininity",
        ],
    },
    "Mars": {
        "nouns": [
            "energy","drive","motivation","actions", "movement", "effort", "competition", "conflict", "training",
            "workouts", "risks", "projects", "repairs", "driving", "finishes",
        ],
        "verbs": [
            "directing energy toward","acting upon", "moving with", "pushing back against", "competing in the arena of","getting motivated by", "arguing with", "training",
            "working out with", "taking risks with", "building", "fixing", "being driven by", "finishing","interpreting masculinity as",
        ],
        "verbsonly": [
            "directing energy","taking action", "moving", "pushing back", "competing", "arguing","being motivated", "training",
            "working out", "taking risks", "building", "fixing", "being driven", "finishing","interpreting masculinity",
        ],
    },
    "Jupiter": {
        "nouns": [
            "learning", "teaching", "travel", "attempts", "exploration", "groups",
            "advice", "study", "publishing", "promotion", "investments", "growth",
        ],
        "verbs": [
            "teaching", "learning from", "traveling with", "trying", "exploring", "joining",
            "advising", "studying", "publishing", "promoting", "investing in", "expanding",
        ],
        "verbsonly": [
            "teaching", "learning from", "traveling", "trying", "exploring", "joining",
            "advising", "studying", "publishing", "promoting", "investing", "expanding",
        ],
    },
    "Saturn": {
        "nouns": [
            "elders","burdens","commitments", "budgets", "savings", "schedules", "obligations", "practice","duties","responsibilities",
            "maintenance", "limits", "habits", "rules","institutions","orthodoxy","restrictions","limitations"
        ],
        "verbs": [
            "working on", "budgeting", "obligated to", "scheduling", "committing", "practicing",
            "reviewing", "testing", "maintaining", "limiting","restricted by", "building habits", "following rules for",
        ],
        "verbsonly": [
            "working", "budgeting", "saving", "scheduling", "committing", "practicing",
            "reviewing", "testing", "maintaining", "limiting","being restricted", "building habits", "following rules",
        ],
    },
    "Uranus": {
        "nouns": [
            "iconoclasm","unpredictability","glitches", "shocking behavior", "novelty", "experiments", "rebellion","futurism",
            "disruption", "pattern breaks", "innovation", "customization", "rule challenges", "surprises","heresy","counterculture",
        ],
        "verbs": [
            "changing", "updating", "replacing", "switching", "experimenting", "improvising",
            "restarting", "breaking patterns with", "innovating", "customizing", "challenging rules", "surprising",
        ],
        "verbsonly": [
            "changing", "updating", "replacing", "switching", "experimenting", "improvising",
            "restarting", "breaking patterns", "innovating", "customizing", "challenging rules", "surprising",
        ],
    },
    "Neptune": {
        "nouns": [
            "imagination", "daydreams", "relaxation", "escapes", "avoidance", "guesses",
            "trust", "doubt", "ideals", "misunderstandings", "music", "distractions",
        ],
        "verbs": [
            "imagining", "daydreaming about", "relaxing with", "escaping from", "avoiding", "finding poetry in",
            "trusting in", "doubting", "idealizing", "misunderstanding", "vibing out with", "getting distracted by",
        ],
        "verbsonly": [
            "imagining", "daydreaming", "relaxing", "escaping", "avoiding", "finding poetry",
            "trusting", "doubting", "idealizing", "misunderstanding", "vibing out", "getting distracted",
        ],
    },
    "Pluto": {
        "nouns": [
            "research", "deep dives", "control", "forced resets","sex","death","metamorphosis","violent transitions","power dynamics"
            "sudden endings", "fresh starts", "obsession", "fixations", "confrontations", "rebuilds",
        ],
        "verbs": [
            "researching", "investigating", "tracking", "controlling", "testing the limits of", "resetting",
            "cutting off", "starting over with", "insisting on", "obsessing over", "confronting", "rebuilding",
        ],
        "verbsonly": [
            "researching", "investigating", "tracking", "controlling", "testing limits", "resetting",
            "cutting off", "starting over", "insisting", "obsessing", "confronting", "rebuilding",
        ],
    },
    "Chiron": {
        "nouns": [
            "pain points", "hard talks", "help", "support", "lessons", "recovery",
            "mistakes", "practice", "coaching", "adaptation", "confidence", "reframed perspectives",
        ],
        "verbs": [
            "noticing pain points in", "talking through", "getting help with", "helping others with", "teaching with",
            "learning from mistakes with", "practicing on", "coaching", "adapting to", "building confidence with", "reframing", "recovering",
        ],
        "verbsonly": [
            "noticing pain points", "resolving", "getting help", "helping others", "teaching",
            "learning from mistakes", "practicing", "coaching", "adapting", "building confidence", "reframing", "recovering",
        ],
    },
    "Ceres": {
        "nouns": [
            "food", "meals", "shopping", "supplies", "cleaning", "hosting",
            "gardens", "lunches", "budgets", "stock checks", "care", "support",
        ],
        "verbs": [
            "feeding", "cooking", "shopping", "providing", "cleaning", "hosting",
            "gardening", "budgeting", "caring for","nurturing others with", "providing support with",
        ],
        "verbsonly": [
            "feeding", "cooking", "shopping", "providing", "cleaning", "hosting",
            "gardening", "budgeting", "caring","nurturing others", "providing support",
        ],
    },
    "Pallas": {
        "nouns": [
            "plans", "strategy", "solutions", "patterns", "designs", "systems",
            "priorities", "maps", "negotiations", "advice", "risks", "next steps",
        ],
        "verbs": [
            "planning", "strategizing", "problem-solving", "noticing patterns", "designing", "organizing",
            "prioritizing", "mapping", "negotiating", "advising", "spotting risky",
        ],
        "verbsonly": [
            "planning", "strategizing", "problem-solving", "noticing patterns", "designing", "organizing",
            "prioritizing", "mapping", "negotiating", "advising", "spotting risky",
        ],
    },
    "Juno": {
        "nouns": [
            "commitment", "partnership", "negotiation", "boundaries", "agreements", "responsibilities",
            "promises", "fairness", "expectations", "loyalty", "cooperation", "accountability",
        ],
        "verbs": [
            "committing to", "partnering with", "negotiating with", "setting boundaries with", "making agreements with", "sharing responsibilities with",
            "keeping promises to", "insisting on fairness with regard to", "checking expectations with", "choosing loyalty to", "cooperating with",
        ],
        "verbsonly": [
            "committing", "partnering", "negotiating", "setting boundaries", "making agreements", "sharing responsibilities",
            "keeping promises", "insisting on fairness", "checking expectations", "choosing loyalty", "cooperating",
        ],
    },
    "Vesta": {
        "nouns": [
            "focus", "practice", "training", "study", "solo work", "routines",
            "standards", "discipline", "distractions", "breaks", "time", "promises",
        ],
        "verbs": [
            "focusing on", "practicing", "training", "studying", "working alone with", "sticking to routines with",
            "maintaining standards of", "showing discipline with", "limiting distractions with", "protecting time with", "keeping a promise with",
        ],
        "verbsonly": [
            "focusing", "practicing", "training", "studying", "working alone", "sticking to routines",
            "maintaining standards", "showing discipline", "limiting distractions", "protecting time", "keeping a promise",
        ],
    },
    "Rahu": {
        "nouns": [
            "more", "chases", "effort", "shortcuts", "chances", "attention",
            "trends", "purchases", "climbs", "networking", "competition", "limits",
        ],
        "verbs": [
            "wanting more in terms of", "chasing", "trying harder with", "taking shortcuts with", "taking chances with", "seeking attention of",
            "copying trends with", "buying", "climbing", "networking", "competing via", "pushing limits of",
        ],
        "verbsonly": [
            "wanting more", "chasing", "trying harder", "taking shortcuts", "taking chances", "seeking attention",
            "copying trends", "buying", "climbing", "networking", "competing", "pushing limits",
        ],
    },
    "Ketu": {
        "nouns": [
            "letting go", "quits", "walkaways", "simplicity", "cutbacks", "distance",
            "endings", "decluttering", "no's", "dropped habits", "unsubscribes", "priority resets",
        ],
        "verbs": [
            "letting go of", "quitting", "walking away from", "simplifying", "cutting back on", "detaching from",
            "ending", "decluttering", "saying no to", "unsubscribing from",
        ],
        "verbsonly": [
            "letting go", "quitting", "walking away", "simplifying", "cutting back", "detaching",
            "ending", "decluttering", "saying no", "unsubscribing",
        ],
    },
    "Lilith": {
        "nouns": [
            "no's", "refusals", "call-outs", "pushback", "boundaries", "defiance",
            "no apologies", "expectations", "distance", "firmness", "limit tests", "taboos",
        ],
        "verbs": [
            "saying no to", "refusing", "calling out", "pushing back", "setting boundaries",
            "not apologizing for", "challenging expectations about", "keeping distance from", "standing firm with", "testing limits of", "breaking taboos with",
        ],
        "verbsonly": [
            "saying no", "refusing", "calling out", "pushing back", "setting boundaries",
            "not apologizing", "challenging expectations", "keeping distance", "standing firm", "testing limits", "breaking taboos",
        ],
    },
    "Part of Fortune": {
        "nouns": [
            "luck", "opportunities", "connections", "breaks", "timing",
            "advantages", "benefits", "wins", "thriving", "rhythm", "solutions", "results",
        ],
        "verbs": [
            "getting lucky with", "finding opportunities with", "meeting the right people with", "landing a break with", "being in the right place for",
            "taking advantage of", "benefiting", "winning", "thriving with", "finding a groove among", "making it work with", "getting results from",
        ],
        "verbsonly": [
            "getting lucky", "finding opportunities", "meeting the right people", "landing a break", "being in the right place",
            "taking advantage", "benefiting", "winning", "thriving", "finding a niche", "making it work", "getting results",
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
    },
}


HOUSE_KEYWORDS = { #Areas of Life
    1: [ #the visible incarnation point
        "lifeforce","health","one's body", "one's appearance", "one's identity", "one's name", "one's evident personality", "identity", "physical presence","voice",
        "first impression", "self presentation", "personal style", "attitude", "approach", "confidence", "self","physical embodiment","surface vitality","signature",
    ],
    2: [ #what one can keep, count, chew and/or rely upon
        "riches","money", "income", "budget", "savings", "spending", "possessions","what-one-can-keep","hoard","reserves","appetite","resources for sustained continuity",
        "food", "resources", "skills", "values", "comfort", "security",
    ],
    3: [ #immediate signal ecology
        "kindred","short journeys","messages", "texts", "emails", "calls", "conversations", "neighbors","voyages","rendezvous","short journeys","domestic travel","casual omens","pattern recognition",
        "siblings","errands", "calendar", "notes", "information","data","exchanges","dialogues","correspondence","exchange of information","gossip","intelligence","relay systems","crossings","routes",
        "missives","cousins","neighbors","brethren","research","studies","analysis","investigation","communication", #'short' journeys are relative to the time period. In the 21st century, that probably means domestic travel vs international travel; in the 18th century, maybe it meant visits to the neighboring towns. In the 24th century, if we make it that far, maybe it'll mean travel within the solar system, but never outside of it.
    ],
    4: [ #origin chamber / buried basement
        "home life", "family", "house", "childhood","real estate","antiquities","antiques","gardens","vintage items","abode","dwelling place",
        "domestic security", "belonging", "home base","agriculture","ancestral legacy","domestic sovereignty","ancestry",
        "private life", "a sense of belonging", "personal property", "the kitchen", "bedroom", "the past","home","property","buried history", "foundation stones", "the cellar", "old bloodlines", "the underground root system",
        #final end of all things, the querent’s father, his patrimony
    ],
    5: [ #self-expression under witness
        "children","dating", "romance", "flirtation", "fun", "party", "hobbies", "games","seduction","applause","favored offspring","risk for pleasure","presentations",
        "art", "performance", "play", "creativity", "attention", "kids","theatre",
    ],
    6: [ #maintenance
        "daily obligations","daily tasks", "labor","daily grind","maintenance tasks","schedule", "mundane tasks", "habits", "health","work",
        "diet", "healthiness", "routine", "coworkers", "service", "repetitive duties","upkeep","useful competence","correction","quiet competence",
    ],
    7: [ #the formal Other
        "marriage(s)","partner", "relationship", "partnership(s)", "binding contracts","devotion","public enemies","alliances","witness","rival",
        "clients", "collaboration", "negotiation", "interpersonal commitments","legal contracts","codependency","counterpart","spouse",
    ],
    8: [ #consequences after contract
        "death","debt", "taxes", "other people's money", "exchanges with others","shared resources", "loans", "insurance","forbidden knowledge","taboos", "control","irreversible exchange",
        "power", "boundaries", "crises", "intimacy","sexuality","sex","calamities","existential upheavals","entanglement","fear", "mortality","mergers","shared resources","transactional consequences",
        "forbidden archives", "occult initiation", "bondage of consequence", "energetic residue", "ancestral debt", "threshold events","dependency","blood price","extraction",
    ],
    9: [ #meaning found at distance
        "international journeys","travel abroad","foreign adventures","college","canonical texts","sanctioned truth","doctrine","dogma","pilgrimage","worldview architecture","paradigms",
        "religion", "beliefs","philosophy","law","ideology","foreign cultures",  #'long' journeys are relative to the time period. In the 21st century, that probably means international travel vs domestic - or maybe even travel into space (haven't checked astronaut charts)?; in the 18th century, maybe it meant cross-country treks and/or sea voyages. In the 24th century, if we make it that far, maybe it'll mean travel outside of the solar system rather than staying within it.
    ],
    10: [ #the public summit
        "honor","career(s)", "bosses", "titles & honors", "reputation","public role","fame","visible competence","rank","public office","legacy",
        "public image", "public goals", "lifelong undertakings","life achievements", "authority","public status", "responsibility to the community","civic burden","renown",
    ],
    11: [ #distributed belonging
        "friends", "groups", "community", "teams", "networks", "followers","collective aspiration","patrons","affiliations","cohorts",
        "audience", "events", "plans", "causes", "collaborators", "future","social systems","social networks","audience blocs",
    ],
    12: [ #that which withdraws from ordinary visibility
        "isolation","hidden suffering","seclusion","confinement","prisons","sleep","going off the grid","dreams","hospitals","erasure","captivity","ostracization","closet skeletons","delusion","madness","hidden enemies","things misplaced by time","unseen costs",
        "retreat", "the subconscious", "imprisonment", "lingering illness", "escape","lamentation","exile", "rest", "backstage","hidden things","banishment","lost things","forgotten things","dissolution of identity boundaries","burnout","rest","withdrawal",
    ],
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

GENERATIONAL_COHORTS = [
    {
        "name": "Awakening Generation",
        "start_year": 1701,
        "end_year": 1723,
        "global_context": "Expansion of maritime trade networks and early Enlightenment thought.",
        "asia_context": "Qing dynasty consolidation in China, Tokugawa stability in Japan, Mughal decline in India.",
        "africa_context": "Rise of centralized West African states such as the Asante Empire under Osei Tutu and the Oyo Empire at its peak; Islamic scholarly networks expand across Sahelian cities including Timbuktu, Kano, and Agadez.",
        "central_america_context": "Spanish colonial administration across the Captaincy General of Guatemala; plantation and mission systems dominate."
    },
    {
        "name": "Liberty Generation",
        "start_year": 1724,
        "end_year": 1741,
        "global_context": "Spread of Enlightenment political philosophy.",
        "asia_context": "European trading companies expand influence in South and Southeast Asia.",
        "africa_context": "Consolidation of regional powers including Dahomey and Asante; expanding caravan trade routes linking Sahelian markets with North Africa and the Mediterranean.",
        "central_america_context": "Colonial economic expansion tied to silver trade and agricultural estates."
    },
    {
        "name": "Republican Generation",
        "start_year": 1742,
        "end_year": 1766,
        "global_context": "Age of revolutions begins in the Atlantic world.",
        "asia_context": "British East India Company expansion following mid-18th-century conflicts in India.",
        "africa_context": "Growing influence of Islamic reform movements across the western Sahel and continued political competition among major states such as Oyo, Dahomey, and Benin.",
        "central_america_context": "Late colonial reforms and increased taxation under Bourbon administrative reforms."
    },
    {
        "name": "Compromise Generation",
        "start_year": 1767,
        "end_year": 1791,
        "global_context": "Post-revolutionary political restructuring.",
        "asia_context": "European trade pressure increases on Qing China and Indian territories.",
        "africa_context": "Increasing religious and political reform movements in the Sahel leading toward the Fulani jihads; regional political realignments across West Africa.",
        "central_america_context": "Growing colonial tensions leading toward independence movements in the early 19th century."
    },
    {
        "name": "Transcendental Generation",
        "start_year": 1792,
        "end_year": 1821,
        "global_context": "Romantic era intellectual movements and early industrialization.",
        "asia_context": "Growing Western economic influence in Asian ports.",
        "africa_context": "Fulani jihad movements transform Sahelian politics culminating in the creation of the Sokoto Caliphate (1804–1808), one of the largest states in 19th-century Africa.",
        "central_america_context": "Independence from Spain in 1821 and formation of early Central American republic structures."
    },
    {
        "name": "Gilded Generation",
        "start_year": 1822,
        "end_year": 1842,
        "global_context": "Industrial revolution accelerates global trade.",
        "asia_context": "Opium Wars and treaty-port system reshape East Asian trade.",
        "africa_context": "Peak influence of the Sokoto Caliphate and other reform states such as Massina; regional trade expansion across West and East African networks.",
        "central_america_context": "Early republic instability and regional federation attempts."
    },
    {
        "name": "Progressive Generation",
        "start_year": 1843,
        "end_year": 1859,
        "global_context": "Industrial capitalism and reform movements.",
        "asia_context": "Meiji Restoration transforms Japan; modernization attempts in China.",
        "africa_context": "Rise of powerful regional states including the Tukulor Empire and the early expansion of Samori Ture’s influence; growing Ethiopian regional consolidation.",
        "central_america_context": "Coffee economies expand; growing influence of export agriculture."
    },
    {
        "name": "Missionary Generation",
        "start_year": 1860,
        "end_year": 1882,
        "global_context": "High imperial era.",
        "asia_context": "Rapid industrialization in Japan and reform efforts across Asia.",
        "africa_context": "Major African state-building efforts including Samori Ture’s Wassoulou Empire, Menelik II’s consolidation of Ethiopia, and the Mahdist uprising beginning in Sudan (1881).",
        "central_america_context": "Export-driven economies dominated by coffee and banana industries."
    },
    {
        "name": "Lost Generation",
        "start_year": 1883,
        "end_year": 1900,
        "global_context": "World War I and collapse of empires.",
        "asia_context": "Nationalist movements and early modernization reforms.",
        "africa_context": "Mahdist state in Sudan and Ethiopia’s decisive victory over Italy at the Battle of Adwa (1896), one of the most significant anti-imperial victories in modern African history.",
        "central_america_context": "U.S. political and economic influence increases in the region."
    },
    {
        "name": "Greatest Generation",
        "start_year": 1901,
        "end_year": 1927,
        "global_context": "Great Depression and World War II.",
        "asia_context": "Japanese expansion and major conflicts in East Asia.",
        "africa_context": "Early nationalist movements emerge; founding of the African National Congress (1912) and development of pan-African intellectual networks.",
        "central_america_context": "Economic disruption during the Great Depression and political instability."
    },
    {
        "name": "Silent Generation",
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
        "name": "Generation X",
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
        "name": "Generation Z",
        "start_year": 1997,
        "end_year": 2012,
        "global_context": "Smartphone and social-media era.",
        "asia_context": "Large-scale digital adoption and tech sector expansion.",
        "africa_context": "Rapid growth of mobile connectivity, fintech ecosystems, and youth-driven political movements across African cities.",
        "central_america_context": "Digital connectivity growth and migration pressures."
    },
    {
        "name": "Generation Alpha",
        "start_year": 2013,
        "end_year": 2028,
        "global_context": "AI, automation, and climate policy transitions.",
        "asia_context": "Technology competition and demographic transitions.",
        "africa_context": "Early life during rapid demographic growth, large-scale urbanization, expanding digital infrastructure, and climate adaptation initiatives across Africa.",
        "central_america_context": "Climate pressures and economic migration shaping childhood environments."
    },
]

#=================== SOCIOLOGICAL STUFF

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
    "relatable",
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
    "relatable":"#993300",
#neg
    "can't trust": "#7f7f7f",
    "can't respect": "#a67c52",
    "can't forgive": "#4d4d4d",
    "dislike": "#5b0f0f",
    "despise": "#df3a3a",
    "power struggles":"#993333",
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
ENNEAGRAM = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
]

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