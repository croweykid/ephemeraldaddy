from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

# Import your existing constants
from ephemeraldaddy.core.interpretations import (
    PLANET_RULERSHIP,
    PLANET_EXALTATION,
    PLANET_DETRIMENT,
    PLANET_FALL,
    NATURAL_HOUSE_SIGNS,
    RULERSHIP_WEIGHT,
    EXALTATION_WEIGHT,
    TRIPLICITY_WEIGHT,   # <-- add this
    DETRIMENT_WEIGHT,
    FALL_WEIGHT,
)

# --- knobs you can tune (small, independent of your dignity weights) ---

# Stress contribution by aspect type (positive = more cursed, negative = relief).
ASPECT_STRESS: Dict[str, float] = {
    "square": 8.0,
    "opposition": 7.0,
    "quincunx": 7.0,
    "semisquare": 5.0,
    "sesquiquadrate": 6.0,
    "contraparallel": 5.5,
    "quindecile": 7.5,

    "trine": -3.0,
    "sextile": -2.0,
    "semisextile": -1.0,
    "quintile": -1.5,
    "biquintile": -2.0,
    "parallel": -1.5,
    "novile": -1.0,
    "binovile": -1.0,
    "trinovile": -1.0,

    "conjunction": 0.0,  # handled via planet-pair stress + dignity
}

HARD_ASPECTS = {"square", "opposition", "quincunx", "semisquare", "sesquiquadrate", "contraparallel", "quindecile"}
SOFT_ASPECTS = {k for k, v in ASPECT_STRESS.items() if v < 0}

# How much “worse” certain planets tend to behave when activated hard.
# (Independent of dignity; think volatility/constraint potential.)
PLANET_DIFFICULTY: Dict[str, float] = {
    "Sun": 0.8, "Moon": 0.8, "Mercury": 0.6, "Venus": 0.5,
    "Mars": 1.2, "Jupiter": 0.4, "Saturn": 1.3,
    "Uranus": 1.0, "Neptune": 0.9, "Pluto": 1.1,
    "Chiron": 0.8, "Rahu": 0.9, "Ketu": 0.9,
    "AS": 1.0, "MC": 0.9, "DS": 0.8, "IC": 0.8,
}

POINT_IMPORTANCE: Dict[str, float] = {
    "Sun": 1.2, "Moon": 1.2, "AS": 1.15, "MC": 1.05, "DS": 1.0, "IC": 1.0,
    "Mercury": 0.9, "Venus": 0.9, "Mars": 1.0, "Jupiter": 0.8, "Saturn": 1.1,
    "Uranus": 0.85, "Neptune": 0.85, "Pluto": 0.9, "Chiron": 0.85, "Rahu": 0.9, "Ketu": 0.9,
}

HOUSE_ANGULARITY: Dict[int, float] = {
    1: 1.15, 4: 1.15, 7: 1.15, 10: 1.15,
    2: 1.05, 5: 1.05, 8: 1.05, 11: 1.05,
    3: 0.95, 6: 0.95, 9: 0.95, 12: 0.95,
}

# Pressure tendency by house topic. Tune to taste.
HOUSE_DIFFICULTY: Dict[int, float] = {
    1: 0.0, 2: -0.2, 3: 0.0, 4: 0.0, 5: -0.3,
    6: 0.6, 7: 0.1, 8: 0.8, 9: 0.0, 10: 0.1, 11: -0.2, 12: 0.8
}

# Relief cap so “nice” aspects can’t launder a high-stress chart.
RELIEF_CAP_FRAC = 0.35  # at most 35% of total stress can be canceled
MOST_CURSED_SCORE = 100.0

@dataclass(frozen=True)
class AspectRecord:
    # Use your lowercase naming convention for aspects
    aspect: str           # e.g. "square"
    body_a: str           # e.g. "Mars" or "AS"
    sign_a: str           # e.g. "Aries"
    house_a: int          # 1..12
    body_b: str
    sign_b: str
    house_b: int
    orb_deg: float
    max_orb_deg: float
    applying: bool

ANGULAR_HOUSES = {1, 4, 7, 10}
DARK_HOUSES = {8, 12}
CORE_BODIES = {"Sun", "Moon", "AS", "MC"}

# Prefer traditional rulers if your PLANET_RULERSHIP includes modern co-rulers
RULER_PREFERENCE = ["Saturn", "Jupiter", "Mars", "Venus", "Mercury", "Moon", "Sun", "Uranus", "Neptune", "Pluto"]

def sign_rulers(sign: str) -> set[str]:
    return {p for p, signs in PLANET_RULERSHIP.items() if sign in signs}

def pick_primary_ruler(sign: str) -> Optional[str]:
    rulers = sign_rulers(sign)
    if not rulers:
        return None
    for p in RULER_PREFERENCE:
        if p in rulers:
            return p
    return sorted(rulers)[0]

def is_tight(orb_deg: float, threshold: float = 1.0) -> bool:
    return orb_deg <= threshold

def hard_aspect_hit(rec: AspectRecord) -> bool:
    return rec.aspect.lower() in HARD_ASPECTS

def involves(rec: AspectRecord, body: str) -> bool:
    return rec.body_a == body or rec.body_b == body

def other_body(rec: AspectRecord, body: str) -> str:
    return rec.body_b if rec.body_a == body else rec.body_a

def collect_positions(aspects: Iterable[AspectRecord]) -> Dict[str, Tuple[str, int]]:
    """
    Best-effort: infer each body's (sign, house) from any record mentioning it.
    Assumes consistency across records.
    """
    pos: Dict[str, Tuple[str, int]] = {}
    for r in aspects:
        if r.body_a not in pos:
            pos[r.body_a] = (r.sign_a, r.house_a)
        if r.body_b not in pos:
            pos[r.body_b] = (r.sign_b, r.house_b)
    return pos


def orb_multiplier(orb_deg: float, max_orb_deg: float) -> float:
    """Exact=1.0, near max orb ~0.25 (smooth falloff)."""
    if max_orb_deg <= 0:
        return 1.0
    x = max(0.0, min(orb_deg, max_orb_deg)) / max_orb_deg
    return 0.25 + 0.75 * (math.cos(x * math.pi / 2) ** 2)


def planet_dignity_score(planet: str, sign: str, house: Optional[int] = None) -> float:
    """
    Uses YOUR constants/weights to produce a raw dignity score.
    Positive = more resourced/competent; negative = more compromised.
    """
    score = 0.0

    # domicile/rulership (your modern rulership map)
    if sign in PLANET_RULERSHIP.get(planet, set()):
        score += float(RULERSHIP_WEIGHT)

    # exaltation / fall (your sign+degree maps; ignore degree unless you want it later)
    ex = PLANET_EXALTATION.get(planet)
    if ex and ex.get("sign") == sign:
        score += float(EXALTATION_WEIGHT)

    if sign in PLANET_DETRIMENT.get(planet, set()):
        score += float(DETRIMENT_WEIGHT)

    fall = PLANET_FALL.get(planet)
    if fall and fall.get("sign") == sign:
        score += float(FALL_WEIGHT)

    # optional: natural-house-sign competence bonus (you already hinted at this in prior logic)
    if house is not None:
        nat = NATURAL_HOUSE_SIGNS.get(house)
        if nat and nat == sign:
            score += float(0.6 * TRIPLICITY_WEIGHT)  # mild bonus; uses your scale

    return score


def dignity_multiplier(aspect: str, dign_a: float, dign_b: float) -> float:
    """
    Convert raw dignity scores (your big weights) into a small multiplier.
    Hard aspects: good dignity reduces harm; bad dignity increases harm.
    Soft aspects: bad dignity reduces how helpful the aspect actually is.
    """
    # squash to roughly [-1, +1] by tanh
    # typical raw range with your weights is like [-9..+9]ish, tanh handles that.
    d = math.tanh((dign_a + dign_b) / 10.0)

    if aspect in HARD_ASPECTS or aspect == "conjunction":
        # d=+1 => ~0.80, d=-1 => ~1.20
        return 1.0 - 0.20 * d
    if aspect in SOFT_ASPECTS:
        # d=-1 => ~1.15 (soft aspect helps less, so "relief magnitude" shrinks)
        # implemented by scaling toward zero: multiplier >1 makes negative numbers less negative? no.
        # so we return <1 when dignity is bad, >1 when dignity is good.
        return 1.0 + 0.15 * d
    return 1.0


def planet_pair_stress(body_a: str, body_b: str, aspect: str) -> float:
    """
    Extra stress from the pair itself. Conjunctions are where this matters most.
    """
    da = PLANET_DIFFICULTY.get(body_a, 0.7)
    db = PLANET_DIFFICULTY.get(body_b, 0.7)
    base = (da + db) / 2.0

    if aspect == "conjunction":
        return 3.0 * base
    if aspect in HARD_ASPECTS:
        return 1.2 * base
    if aspect in SOFT_ASPECTS:
        return -0.6 * (1.0 - base)
    return 0.0


def chart_cursedness(aspects: Iterable[AspectRecord]) -> Dict[str, float]:
    stress_total = 0.0
    relief_total = 0.0
    hard_hits = 0
    core_hits = 0  # luminaries + angles

    CORE_BODIES = {"Sun", "Moon", "AS", "MC"}

    for rec in aspects:
        asp = rec.aspect.lower()
        base = ASPECT_STRESS.get(asp, 0.0)
        om = orb_multiplier(rec.orb_deg, rec.max_orb_deg)
        am = 1.10 if rec.applying else 1.0

        imp = (POINT_IMPORTANCE.get(rec.body_a, 0.8) + POINT_IMPORTANCE.get(rec.body_b, 0.8)) / 2.0

        h_amp = (HOUSE_ANGULARITY.get(rec.house_a, 1.0) + HOUSE_ANGULARITY.get(rec.house_b, 1.0)) / 2.0
        h_diff = (HOUSE_DIFFICULTY.get(rec.house_a, 0.0) + HOUSE_DIFFICULTY.get(rec.house_b, 0.0)) / 2.0
        topic_bump = 1.0 + 0.25 * h_diff

        dign_a = planet_dignity_score(rec.body_a, rec.sign_a, rec.house_a)
        dign_b = planet_dignity_score(rec.body_b, rec.sign_b, rec.house_b)
        dm = dignity_multiplier(asp, dign_a, dign_b)

        pair = planet_pair_stress(rec.body_a, rec.body_b, asp)

        contrib = (base + pair) * om * am * imp * h_amp * topic_bump * dm

        if contrib >= 0:
            stress_total += contrib
        else:
            relief_total += contrib

        if asp in HARD_ASPECTS:
            hard_hits += 1
            if (rec.body_a in CORE_BODIES) or (rec.body_b in CORE_BODIES):
                core_hits += 1

    # cap relief
    relief_cap = -RELIEF_CAP_FRAC * stress_total
    relief_capped = max(relief_total, relief_cap)

    total = max(0.0, stress_total + relief_capped)

    # extra tax: hard hits on Sun/Moon/AS/MC matter disproportionately for “felt cursed”
    total += 1.5 * core_hits

    return {
        "total": round(total, 2),
        "stress": round(stress_total, 2),
        "relief": round(relief_capped, 2),
        "hard_aspects": float(hard_hits),
        "core_hard_hits": float(core_hits),
    }

def chart_cursedness_max(aspects: Iterable[AspectRecord]) -> float:
    stress_total = 0.0
    relief_total = 0.0
    core_hits = 0

    CORE_BODIES = {"Sun", "Moon", "AS", "MC"}

    for rec in aspects:
        asp = rec.aspect.lower()
        base = ASPECT_STRESS.get(asp, 0.0)
        om = 1.0
        am = 1.10

        imp = (
            POINT_IMPORTANCE.get(rec.body_a, 0.8)
            + POINT_IMPORTANCE.get(rec.body_b, 0.8)
        ) / 2.0

        h_amp = (
            HOUSE_ANGULARITY.get(rec.house_a, 1.0)
            + HOUSE_ANGULARITY.get(rec.house_b, 1.0)
        ) / 2.0
        h_diff = (
            HOUSE_DIFFICULTY.get(rec.house_a, 0.0)
            + HOUSE_DIFFICULTY.get(rec.house_b, 0.0)
        ) / 2.0
        topic_bump = 1.0 + 0.25 * h_diff

        if asp in HARD_ASPECTS or asp == "conjunction":
            dm = 1.20
        elif asp in SOFT_ASPECTS:
            dm = 0.85
        else:
            dm = 1.0

        pair = planet_pair_stress(rec.body_a, rec.body_b, asp)

        contrib = (base + pair) * om * am * imp * h_amp * topic_bump * dm

        if contrib >= 0:
            stress_total += contrib
        else:
            relief_total += contrib

        if asp in HARD_ASPECTS:
            if (rec.body_a in CORE_BODIES) or (rec.body_b in CORE_BODIES):
                core_hits += 1

    relief_cap = -RELIEF_CAP_FRAC * stress_total
    relief_capped = max(relief_total, relief_cap)

    total = max(0.0, stress_total + relief_capped)
    total += 1.5 * core_hits
    return total
