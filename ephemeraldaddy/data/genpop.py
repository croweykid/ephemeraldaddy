"""General-population astrological baselines.

This module starts with CDC-backed Sun sign birth distributions, then derives
aggregated Sun sign norms and approximate Mercury/Venus sign norms by sampling
planetary positions for the same calendar years.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
import calendar
from functools import lru_cache
from pathlib import Path
import re
from typing import Dict

from ephemeraldaddy.data.age_distribution_estimator import discrete_age_distribution


SIGN_ORDER = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

OUTER_PLANETS = (
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)


GEN_POP_ACTUAL_GENDER_BASELINE_PERCENTAGES: dict[str, float | None] = {
    "F": 0.4938,
    "M": 0.4995,
    "AFAB-M": None,
    "AMAB-F": None,
    "AFAB-NB": None,
    "AMAB-NB": None,
}

SUN_SIGN_BIRTHS = {  # from CDC natality files
    1988: {
        "Aries": {"count": 311169, "percent": 7.95},
        "Taurus": {"count": 327140, "percent": 8.36},
        "Gemini": {"count": 331229, "percent": 8.46},
        "Cancer": {"count": 360283, "percent": 9.21},
        "Leo": {"count": 350428, "percent": 8.95},
        "Virgo": {"count": 357449, "percent": 9.13},
        "Libra": {"count": 331243, "percent": 8.46},
        "Scorpio": {"count": 315503, "percent": 8.06},
        "Sagittarius": {"count": 313411, "percent": 8.01},
        "Capricorn": {"count": 290166, "percent": 7.41},
        "Aquarius": {"count": 310206, "percent": 7.93},
        "Pisces": {"count": 315559, "percent": 8.06},
    },
    1969: {
        "Aries": {"count": 142272, "percent": 7.91},
        "Taurus": {"count": 143705, "percent": 7.99},
        "Gemini": {"count": 148206, "percent": 8.24},
        "Cancer": {"count": 161814, "percent": 8.99},
        "Leo": {"count": 161629, "percent": 8.98},
        "Virgo": {"count": 159056, "percent": 8.84},
        "Libra": {"count": 154017, "percent": 8.56},
        "Scorpio": {"count": 149980, "percent": 8.33},
        "Sagittarius": {"count": 150288, "percent": 8.35},
        "Capricorn": {"count": 139171, "percent": 7.73},
        "Aquarius": {"count": 144353, "percent": 8.02},
        "Pisces": {"count": 145027, "percent": 8.06},
    },
    1979: {
        "Aries": {"count": 250822, "percent": 7.88},
        "Taurus": {"count": 257606, "percent": 8.09},
        "Gemini": {"count": 263886, "percent": 8.29},
        "Cancer": {"count": 285839, "percent": 8.98},
        "Leo": {"count": 290140, "percent": 9.11},
        "Virgo": {"count": 289266, "percent": 9.08},
        "Libra": {"count": 273155, "percent": 8.58},
        "Scorpio": {"count": 264786, "percent": 8.32},
        "Sagittarius": {"count": 259429, "percent": 8.15},
        "Capricorn": {"count": 241278, "percent": 7.58},
        "Aquarius": {"count": 252342, "percent": 7.92},
        "Pisces": {"count": 255834, "percent": 8.03},
    },
    1985: {
        "Aries": {"count": 302767, "percent": 8.04},
        "Taurus": {"count": 312306, "percent": 8.29},
        "Gemini": {"count": 320591, "percent": 8.51},
        "Cancer": {"count": 339111, "percent": 9.01},
        "Leo": {"count": 337330, "percent": 8.96},
        "Virgo": {"count": 339052, "percent": 9.01},
        "Libra": {"count": 321718, "percent": 8.54},
        "Scorpio": {"count": 305810, "percent": 8.12},
        "Sagittarius": {"count": 301491, "percent": 8.01},
        "Capricorn": {"count": 282611, "percent": 7.51},
        "Aquarius": {"count": 298520, "percent": 7.93},
        "Pisces": {"count": 303747, "percent": 8.07},
    },
}


def _sign_for_longitude(longitude: float) -> str:
    return SIGN_ORDER[int((longitude % 360.0) // 30.0)]


def _aggregate_sun_sign_distribution() -> dict[str, dict[str, float]]:
    counts = {sign: 0 for sign in SIGN_ORDER}
    for year_distribution in SUN_SIGN_BIRTHS.values():
        for sign, details in year_distribution.items():
            counts[sign] += int(details["count"])

    total = sum(counts.values())
    return {
        sign: {
            "count": counts[sign],
            "percent": round((counts[sign] / total) * 100.0, 4),
        }
        for sign in SIGN_ORDER
    }


def _daily_planet_longitude_provider():
    """Return a callable(year, month, day, planet_name) -> longitude degrees.

    Tries Swiss Ephemeris first, then falls back to Skyfield with the local DE421
    ephemeris file bundled in the repository.
    """

    try:
        import swisseph as swe

        body_map = {
            "Mercury": swe.MERCURY,
            "Venus": swe.VENUS,
            "Saturn": swe.SATURN,
            "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO,
        }

        def get_longitude(year: int, month: int, day: int, planet_name: str) -> float:
            jd_ut = swe.julday(year, month, day, 12.0)
            values, _ = swe.calc_ut(jd_ut, body_map[planet_name])
            return float(values[0])

        return get_longitude
    except Exception:
        from skyfield.api import load

        ts = load.timescale()
        eph_path = Path(__file__).resolve().parents[2] / "de421.bsp"
        eph = load(str(eph_path))
        earth = eph["earth"]
        body_map = {
            "Mercury": eph["mercury"],
            "Venus": eph["venus"],
            "Saturn": eph["saturn barycenter"],
            "Uranus": eph["uranus barycenter"],
            "Neptune": eph["neptune barycenter"],
            "Pluto": eph["pluto barycenter"],
        }

        def get_longitude(year: int, month: int, day: int, planet_name: str) -> float:
            t = ts.utc(year, month, day, 12)
            _lat, lon, _distance = earth.at(t).observe(body_map[planet_name]).apparent().ecliptic_latlon(epoch="date")
            return float(lon.degrees)

        return get_longitude

def _coerce_day_key_to_mmdd(raw_key: object) -> str:
    """Normalize an MM-DD/day-of-year key into MM-DD form."""

    if isinstance(raw_key, str) and re.fullmatch(r"\d{2}-\d{2}", raw_key):
        return raw_key

    if isinstance(raw_key, int) or (isinstance(raw_key, str) and raw_key.isdigit()):
        day_of_year = int(raw_key)
        if not 1 <= day_of_year <= 366:
            raise ValueError(f"Day-of-year key out of range: {raw_key!r}")
        target_date = date(2000, 1, 1) + timedelta(days=day_of_year - 1)
        return target_date.strftime("%m-%d")

    raise ValueError(f"Unsupported day key format: {raw_key!r}")


def _load_daily_birth_weight_maps() -> dict[bool, dict[str, float]]:
    """Load and normalize empirical daily birth weights.

    Source: ``ephemeraldaddy/data/compiled/births_per_day.json``.
    If Feb 29 is absent, it is inferred as the arithmetic mean of Feb 28 and Mar 1.
    Returns maps keyed by ``calendar.isleap(year)`` (False -> non-leap, True -> leap).
    """

    births_path = Path(__file__).resolve().parent / "compiled" / "births_per_day.json"
    try:
        loaded = json.loads(births_path.read_text())
    except Exception as exc:
        raise RuntimeError(
            f"Unable to load daily birth weights from {births_path}: {exc}"
        ) from exc

    if isinstance(loaded, dict) and isinstance(loaded.get("weights"), dict):
        raw_weights = loaded["weights"]
    else:
        raw_weights = loaded
    if not isinstance(raw_weights, dict):
        raise RuntimeError(f"Daily birth weights in {births_path} must be a JSON object.")

    mmdd_weights: dict[str, float] = {}
    for raw_key, raw_value in raw_weights.items():
        mmdd_key = _coerce_day_key_to_mmdd(raw_key)
        mmdd_weights[mmdd_key] = float(raw_value)

    if "02-29" not in mmdd_weights:
        mmdd_weights["02-29"] = (mmdd_weights["02-28"] + mmdd_weights["03-01"]) / 2.0

    non_leap_raw = {k: v for k, v in mmdd_weights.items() if k != "02-29"}
    non_leap_total = sum(non_leap_raw.values())
    leap_total = sum(mmdd_weights.values())

    if non_leap_total <= 0.0 or leap_total <= 0.0:
        raise RuntimeError("Daily birth weights must sum to a positive value.")

    non_leap_weights = {k: v / non_leap_total for k, v in non_leap_raw.items()}
    leap_weights = {k: v / leap_total for k, v in mmdd_weights.items()}

    assert abs(sum(non_leap_weights.values()) - 1.0) < 1e-12
    assert abs(sum(leap_weights.values()) - 1.0) < 1e-12

    return {False: non_leap_weights, True: leap_weights}

def estimate_inner_planet_sign_distribution() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Estimate Mercury/Venus sign prevalence weighted by observed yearly births.

    Method:
      1) For each CDC year in ``SUN_SIGN_BIRTHS``, spread that year's births across
         each calendar day using empirical day-of-year weights from
      2) Sample Mercury and Venus longitude at 12:00 UTC each day.
      3) Bin longitudes into zodiac signs and convert to percentages.
    """

    get_longitude = _daily_planet_longitude_provider()
    daily_weight_maps = _load_daily_birth_weight_maps()
    results: Dict[str, Dict[str, float]] = {
        "Mercury": {sign: 0.0 for sign in SIGN_ORDER},
        "Venus": {sign: 0.0 for sign in SIGN_ORDER},
    }

    for year, year_distribution in SUN_SIGN_BIRTHS.items():
        yearly_births = sum(int(v["count"]) for v in year_distribution.values())
        daily_weights = daily_weight_maps[calendar.isleap(year)]
        allocated_births = 0.0

        day_cursor = date(year, 1, 1)
        year_end = date(year + 1, 1, 1)
        while day_cursor < year_end:
            day_key = day_cursor.strftime("%m-%d")
            births_for_day = yearly_births * daily_weights[day_key]
            allocated_births += births_for_day
            for planet_name in ("Mercury", "Venus"):
                longitude = get_longitude(day_cursor.year, day_cursor.month, day_cursor.day, planet_name)
                sign = _sign_for_longitude(longitude)
                results[planet_name][sign] += births_for_day
            day_cursor += timedelta(days=1)

        assert abs(allocated_births - yearly_births) < 1e-6

    output: Dict[str, Dict[str, Dict[str, float]]] = {}
    for planet_name, sign_counts in results.items():
        total = sum(sign_counts.values())
        assert abs(sum((sign_counts[sign] / total) * 100.0 for sign in SIGN_ORDER) - 100.0) < 1e-9
        output[planet_name] = {
            sign: {
                "count": round(sign_counts[sign]),
                "percent": round((sign_counts[sign] / total) * 100.0, 4),
            }
            for sign in SIGN_ORDER
        }
    return output


def estimate_outer_planet_sign_distribution_from_age(
    user_age: float,
    *,
    as_of: date | None = None,
    min_age: int = 0,
    max_age: int = 110,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Estimate outer-planet sign prevalence from age-conditioned network probabilities.

    We map the age distribution model (``P(alter_age | user_age)``) into a
    birth-year-weighted planet-sign distribution. This can be used as a control
    for "likely chart elements" in the user's social graph.
    """

    reference_date = as_of or date.today()
    age_bins = discrete_age_distribution(
        float(user_age),
        bin_width=1,
        min_age=min_age,
        max_age=max_age,
    )
    if not age_bins:
        return {planet: {sign: {"count": 0, "percent": 0.0} for sign in SIGN_ORDER} for planet in OUTER_PLANETS}

    year_weights: dict[int, float] = {}
    for age, probability in age_bins:
        birth_year = reference_date.year - int(age)
        year_weights[birth_year] = year_weights.get(birth_year, 0.0) + float(probability)

    get_longitude = _daily_planet_longitude_provider()

    @lru_cache(maxsize=None)
    def _sign_for_day(year: int, month: int, day: int, planet_name: str) -> str:
        longitude = get_longitude(year, month, day, planet_name)
        return _sign_for_longitude(longitude)

    weighted_sign_mass: Dict[str, Dict[str, float]] = {
        planet: {sign: 0.0 for sign in SIGN_ORDER}
        for planet in OUTER_PLANETS
    }

    for birth_year, year_weight in year_weights.items():
        days_in_year = 366 if calendar.isleap(birth_year) else 365
        for month in range(1, 13):
            month_days = calendar.monthrange(birth_year, month)[1]
            month_weight = year_weight * (month_days / days_in_year)
            sample_day = min(15, month_days)
            for planet_name in OUTER_PLANETS:
                sign = _sign_for_day(birth_year, month, sample_day, planet_name)
                weighted_sign_mass[planet_name][sign] += month_weight

    output: Dict[str, Dict[str, Dict[str, float]]] = {}
    for planet_name, sign_weights in weighted_sign_mass.items():
        total = sum(sign_weights.values())
        output[planet_name] = {
            sign: {
                "count": round(sign_weights[sign] * 1_000_000),
                "percent": round((sign_weights[sign] / total) * 100.0, 4) if total > 0 else 0.0,
            }
            for sign in SIGN_ORDER
        }
    return output


def estimate_chart_element_control_distribution(
    user_age: float,
    *,
    as_of: date | None = None,
    min_age: int = 0,
    max_age: int = 110,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Build a combined sign-distribution control for likely natal chart elements."""

    chart_control: Dict[str, Dict[str, Dict[str, float]]] = {
        "Sun": SUN_SIGN_DISTRIBUTION_AGGREGATED,
        "Mercury": INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED["Mercury"],
        "Venus": INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED["Venus"],
    }
    chart_control.update(
        estimate_outer_planet_sign_distribution_from_age(
            user_age,
            as_of=as_of,
            min_age=min_age,
            max_age=max_age,
        )
    )
    return chart_control


# My manual counts based on 1988, 1985, 1979, 1969 US gov't data:
# SUN_SIGN_DISTRIBUTION_AGGREGATED = {
#     "Aries":       {"count": 1007030, "percent": 7.95},
#     "Taurus":      {"count": 1040757, "percent": 8.22},
#     "Gemini":      {"count": 1063912, "percent": 8.40},
#     "Cancer":      {"count": 1147047, "percent": 9.06},
#     "Leo":         {"count": 1139527, "percent": 9.00},
#     "Virgo":       {"count": 1144823, "percent": 9.04},
#     "Libra":       {"count": 1080133, "percent": 8.53},
#     "Scorpio":     {"count": 1036079, "percent": 8.18},
#     "Sagittarius": {"count": 1024619, "percent": 8.09},
#     "Capricorn":   {"count": 953226,  "percent": 7.53},
#     "Aquarius":    {"count": 1005421, "percent": 7.94},
#     "Pisces":      {"count": 1020167, "percent": 8.06},
# }

SUN_SIGN_DISTRIBUTION_AGGREGATED = _aggregate_sun_sign_distribution()

# Computed with `estimate_inner_planet_sign_distribution()`.
# Values are checked in so they can be consumed without ephemeris calculations.
# Daily weighting uses empirical per-day birth weights from births_per_day.json.
INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED = {
    "Mercury": {
        "Aries": {
            "count": 1302439,
            "percent": 10.2856
        },
        "Taurus": {
            "count": 534473,
            "percent": 4.2208
        },
        "Gemini": {
            "count": 1322267,
            "percent": 10.4422
        },
        "Cancer": {
            "count": 593571,
            "percent": 4.6875
        },
        "Leo": {
            "count": 1620719,
            "percent": 12.7991
        },
        "Virgo": {
            "count": 651911,
            "percent": 5.1483
        },
        "Libra": {
            "count": 1452277,
            "percent": 11.4689
        },
        "Scorpio": {
            "count": 982118,
            "percent": 7.756
        },
        "Sagittarius": {
            "count": 1342180,
            "percent": 10.5994
        },
        "Capricorn": {
            "count": 768319,
            "percent": 6.0676
        },
        "Aquarius": {
            "count": 1321448,
            "percent": 10.4357
        },
        "Pisces": {
            "count": 771019,
            "percent": 6.0889
        }
    },
    "Venus": {
        "Aries": {
            "count": 2301056,
            "percent": 18.1719
        },
        "Taurus": {
            "count": 980818,
            "percent": 7.7457
        },
        "Gemini": {
            "count": 1891904,
            "percent": 14.9407
        },
        "Cancer": {
            "count": 1094918,
            "percent": 8.6468
        },
        "Leo": {
            "count": 953931,
            "percent": 7.5334
        },
        "Virgo": {
            "count": 889478,
            "percent": 7.0244
        },
        "Libra": {
            "count": 855904,
            "percent": 6.7592
        },
        "Scorpio": {
            "count": 866507,
            "percent": 6.843
        },
        "Sagittarius": {
            "count": 947307,
            "percent": 7.4811
        },
        "Capricorn": {
            "count": 510264,
            "percent": 4.0296
        },
        "Aquarius": {
            "count": 482740,
            "percent": 3.8123
        },
        "Pisces": {
            "count": 887915,
            "percent": 7.012
        }
    }
}
