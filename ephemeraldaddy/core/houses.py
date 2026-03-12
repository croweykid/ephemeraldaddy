# ephemeraldaddy/core/houses.py

from __future__ import annotations

import math
import datetime as _dt
from datetime import timezone as _tz

from ephemeraldaddy.core.deps import ensure_package

# Swiss Ephemeris via pyswisseph
_swe = ensure_package("pyswisseph")
swe = _swe

# Mean obliquity of the ecliptic at J2000 (good enough for natal work)
_OBLIQUITY_DEG = 23.4392911


def _wrap360(deg: float) -> float:
    return deg % 360.0

def _wrap2pi(rad: float) -> float:
    return rad % (2.0 * math.pi)


def _deg2rad(deg: float) -> float:
    return math.radians(deg)


def _rad2deg(rad: float):
    return math.degrees(rad)

def _normalize_angle_rad(rad: float) -> float:
    """Return rad wrapped to (-pi, pi]."""
    return math.atan2(math.sin(rad), math.cos(rad))

# ---------------------------------------------------------------------------
# PORPHYRY (from RAMC) – useful as a fallback / comparison
# ---------------------------------------------------------------------------

def _ascendant_longitude(ramc_deg: float, lat_deg: float) -> float:
    """
    Ascendant from RAMC (local sidereal time in degrees) and latitude.

    Uses the standard form:

        y = -cos(θ)
        x =  sin(θ)·cos(ε) + tan(φ)·sin(ε)
        λ0 = atan2(y, x)

    and then flips to the eastern intersection if needed.
    """
    eps = _deg2rad(_OBLIQUITY_DEG)
    phi = _deg2rad(lat_deg)
    theta = _deg2rad(ramc_deg)

    y = -math.cos(theta)
    x = math.sin(theta) * math.cos(eps) + math.tan(phi) * math.sin(eps)

    lam = _rad2deg(math.atan2(y, x))
    lam = _wrap360(lam)

    # Pick the eastern intersection of ecliptic & horizon
    if lam < 180.0:
        lam += 180.0
    else:
        lam -= 180.0

    return _wrap360(lam)


def _ramc_to_ecliptic_long(ramc_deg: float) -> float:
    """
    Convert RA on the meridian (RAMC, in degrees) to ecliptic longitude of the MC:

        tan λ = tan α / cos ε
    """
    eps = _deg2rad(_OBLIQUITY_DEG)
    alpha = _deg2rad(ramc_deg)

    lam = math.atan2(math.sin(alpha) / math.cos(eps), math.cos(alpha))
    return _wrap360(_rad2deg(lam))


def _ecliptic_ra_dec(lam_rad: float):
    """Return (right ascension, declination) for ecliptic longitude lam (lat=0)."""
    ε = _deg2rad(_OBLIQUITY_DEG)

    sin_lam = math.sin(lam_rad)
    cos_lam = math.cos(lam_rad)

    # Equatorial conversion
    ra = math.atan2(sin_lam * math.cos(ε), cos_lam)
    dec = math.asin(sin_lam * math.sin(ε))

    return _wrap2pi(ra), dec


def _semi_diurnal_arc(dec_rad: float, lat_rad: float):
    """Return H0 (semi-diurnal arc) in radians, or None if circumpolar/undefined."""
    arg = -math.tan(lat_rad) * math.tan(dec_rad)
    if arg < -1.0 or arg > 1.0:
        return None
    return math.acos(arg)


def _hour_angle(ra_rad: float, ramc_rad: float) -> float:
    """Hour angle of a body with RA ra at RAMC ramc, wrapped to (-pi, pi]."""
    return _normalize_angle_rad(ramc_rad - ra_rad)


def _subdivide_arc(start_deg: float, end_deg: float, n_parts: int, index: int) -> float:
    """
    Subdivide the arc from start_deg → end_deg into n_parts,
    and return the point at position `index` (1..n_parts-1),
    moving forward in zodiacal direction.
    """
    start = _wrap360(start_deg)
    end = _wrap360(end_deg)

    delta = (end - start) % 360.0
    step = delta / n_parts
    return _wrap360(start + step * index)


def porphyry_houses(ramc_deg: float, latitude_deg: float) -> list[float]:
    """
    Porphyry quadrant houses (NOT Placidus).

    - Uses true Ascendant and MC based on RAMC, latitude, and obliquity.
    - Divides each quadrant (Asc→IC, IC→Desc, Desc→MC, MC→Asc)
      into three equal parts in ecliptic longitude.

    Returns:
        [1st, 2nd, ..., 12th] in ecliptic longitude degrees.
    """
    ramc = _wrap360(ramc_deg)

    # Primary axes
    mc = _ramc_to_ecliptic_long(ramc)               # 10th house cusp
    ic = _wrap360(mc + 180.0)                       # 4th house cusp

    asc = _ascendant_longitude(ramc, latitude_deg)  # 1st house cusp
    desc = _wrap360(asc + 180.0)                    # 7th house cusp

    cusps = [0.0] * 12

    # Anchor cusps
    cusps[0] = asc   # 1st
    cusps[3] = ic    # 4th
    cusps[6] = desc  # 7th
    cusps[9] = mc    # 10th

    # Quadrant Asc → IC: houses 1, 2, 3, 4
    cusps[1] = _subdivide_arc(asc, ic, 3, 1)  # 2nd
    cusps[2] = _subdivide_arc(asc, ic, 3, 2)  # 3rd

    # Quadrant IC → Desc: houses 4, 5, 6, 7
    cusps[4] = _subdivide_arc(ic, desc, 3, 1)  # 5th
    cusps[5] = _subdivide_arc(ic, desc, 3, 2)  # 6th

    # Quadrant Desc → MC: houses 7, 8, 9, 10
    cusps[7] = _subdivide_arc(desc, mc, 3, 1)  # 8th
    cusps[8] = _subdivide_arc(desc, mc, 3, 2)  # 9th

    # Quadrant MC → Asc: houses 10, 11, 12, 1
    cusps[10] = _subdivide_arc(mc, asc, 3, 1)  # 11th
    cusps[11] = _subdivide_arc(mc, asc, 3, 2)  # 12th

    return cusps


# ---------------------------------------------------------------------------
# REAL PLACIDUS via Swiss Ephemeris
# ---------------------------------------------------------------------------

def _placidus_cusps_and_axes(
    dt_aware: _dt.datetime, lat_deg: float, lon_deg: float
) -> tuple[list[float], dict[str, float]]:
    """
    Return Placidus house cusps and primary angles (Asc/MC).
    """
    if dt_aware.tzinfo is None:
        raise ValueError("placidus_houses expects a tz-aware datetime")

    # Convert to UTC for Swiss
    dt_utc = dt_aware.astimezone(_tz.utc)

    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day

    hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )

    jd_ut = swe.julday(y, m, d, hour)

    # Swiss longitude is "east positive", same convention you use.
    cusps, ascmc = swe.houses(jd_ut, lat_deg, lon_deg, b"P")

 # cusps is usually 1-based (cusps[1]..cusps[12]), but some builds return 0-based
    if len(cusps) >= 13:
        indices = range(1, 13)
    else:
        indices = range(0, 12)
    cusp_list = [_wrap360(cusps[i]) for i in indices]

    axes: dict[str, float] = {}
    if len(ascmc) > 0:
        axes["AS"] = _wrap360(ascmc[0])
    if len(ascmc) > 1:
        axes["MC"] = _wrap360(ascmc[1])

    return cusp_list, axes


def placidus_houses(dt_aware: _dt.datetime, lat_deg: float, lon_deg: float) -> list[float]:
    """
    True Placidus cusps using Swiss Ephemeris (pyswisseph).

    dt_aware: timezone-aware datetime (any timezone, will be converted to UTC)
    lat_deg:  geographic latitude (positive north)
    lon_deg:  geographic longitude (positive east, negative west – Skyfield style)

    Returns:
        [cusp1, cusp2, ..., cusp12] in ecliptic longitude degrees, 0–360.
    """
    cusps, _ = _placidus_cusps_and_axes(dt_aware, lat_deg, lon_deg)
    return cusps


def placidus_axes(dt_aware: _dt.datetime, lat_deg: float, lon_deg: float) -> dict[str, float]:
    """
    Return primary chart angles (Ascendant + Midheaven) in ecliptic longitude degrees.
    """
    _, axes = _placidus_cusps_and_axes(dt_aware, lat_deg, lon_deg)
    return axes


def placidus_houses_and_axes(
    dt_aware: _dt.datetime,
    lat_deg: float,
    lon_deg: float,
) -> tuple[list[float], dict[str, float]]:
    """Return both Placidus cusps and primary axes from a single Swiss call."""
    return _placidus_cusps_and_axes(dt_aware, lat_deg, lon_deg)