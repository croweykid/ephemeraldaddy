"""Sidereal D1 calculation contracts.

This module deliberately contains no persistence or GUI behavior.  A sidereal
D1 is calculated data belonging to an existing chart UID, not another person.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
import hashlib
import json
import math
import threading
from types import MappingProxyType
from typing import Any, Mapping

from ephemeraldaddy.core.aspects import find_aspects
from ephemeraldaddy.core.ephemeris import planetary_positions, planetary_retrogrades, swe


LAHIRI = "lahiri"
SIDEREAL_CALCULATION_VERSION = 1
_SIDEREAL_SWE_LOCK = threading.RLock()


@dataclass(frozen=True)
class ZodiacContext:
    """Coordinate-system selection, kept separate from chart projection."""

    zodiac: str = "tropical"
    ayanamsha: str | None = None

    def __post_init__(self) -> None:
        zodiac = self.zodiac.strip().lower()
        ayanamsha = self.ayanamsha.strip().lower() if self.ayanamsha else None
        if zodiac not in {"tropical", "sidereal"}:
            raise ValueError(f"Unsupported zodiac {self.zodiac!r}")
        if zodiac == "tropical" and ayanamsha is not None:
            raise ValueError("Tropical contexts do not have an ayanamsha")
        if zodiac == "sidereal" and ayanamsha not in {LAHIRI}:
            raise ValueError(f"Unsupported sidereal ayanamsha {self.ayanamsha!r}")
        object.__setattr__(self, "zodiac", zodiac)
        object.__setattr__(self, "ayanamsha", ayanamsha)


@dataclass(frozen=True)
class NakshatraPosition:
    index: int
    name: str
    pada: int
    degrees_into_nakshatra: float


@dataclass(frozen=True)
class SiderealChartData:
    """Immutable, rebuildable Lahiri D1 snapshot for one parent chart UID."""

    chart_uid: str
    ayanamsha: str
    ayanamsha_degrees: float
    positions: Mapping[str, float]
    retrogrades: Mapping[str, bool]
    ascendant: float | None
    mc: float | None
    house_cusps: tuple[float, ...] | None
    aspects: tuple[Mapping[str, Any], ...]
    nakshatras: Mapping[str, NakshatraPosition]
    source_recalculation_token: str
    calculation_version: int = SIDEREAL_CALCULATION_VERSION


NAKSHATRA_NAMES = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
)


def _julian_day(dt: _dt.datetime) -> float:
    if dt.tzinfo is None:
        raise ValueError("Sidereal calculations require a timezone-aware datetime")
    utc = dt.astimezone(_dt.timezone.utc)
    hour = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3_600_000_000
    return float(swe.julday(utc.year, utc.month, utc.day, hour))


def _require_uid(chart_uid: str) -> str:
    uid = "".join(character for character in str(chart_uid or "").strip().upper() if character.isalnum())
    if len(uid) < 8:
        raise ValueError("chart_uid is required")
    return uid[:64]


def lahiri_ayanamsha(dt: _dt.datetime) -> float:
    """Return Swiss Ephemeris' date-sensitive Lahiri ayanamsha."""

    jd_ut = _julian_day(dt)
    with _SIDEREAL_SWE_LOCK:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        _flags, value = swe.get_ayanamsa_ex_ut(jd_ut, 0)
        return float(value) % 360.0


def nakshatra_position(longitude: float) -> NakshatraPosition:
    """Map a sidereal longitude to one of 27 nakshatras and four padas."""

    if not math.isfinite(longitude):
        raise ValueError("longitude must be finite")
    normalized = longitude % 360.0
    span = 360.0 / 27.0
    index = min(26, int(normalized / span))
    within = normalized - index * span
    pada = min(4, int(within / (span / 4.0)) + 1)
    return NakshatraPosition(index, NAKSHATRA_NAMES[index], pada, within)


def source_recalculation_token(
    *,
    dt: _dt.datetime,
    latitude: float,
    longitude: float,
    use_birth_time_data: bool,
    ayanamsha: str = LAHIRI,
    calculation_version: int = SIDEREAL_CALCULATION_VERSION,
    rectification_state: Mapping[str, Any] | None = None,
) -> str:
    """Hash only source facts capable of changing calculated sidereal data."""

    if dt.tzinfo is None:
        raise ValueError("Recalculation tokens require a timezone-aware datetime")
    payload = {
        "utc": dt.astimezone(_dt.timezone.utc).isoformat(timespec="microseconds"),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "use_birth_time_data": bool(use_birth_time_data),
        "ayanamsha": str(ayanamsha).strip().lower(),
        "calculation_version": int(calculation_version),
        "rectification_state": dict(rectification_state or {}),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sidereal_houses(
    dt: _dt.datetime, latitude: float, longitude: float
) -> tuple[tuple[float, ...], float, float]:
    jd_ut = _julian_day(dt)
    with _SIDEREAL_SWE_LOCK:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        cusps, axes = swe.houses_ex(
            jd_ut, float(latitude), float(longitude), b"P", swe.FLG_SIDEREAL
        )
    return tuple(float(value) % 360.0 for value in cusps), float(axes[0]) % 360.0, float(axes[1]) % 360.0


def calculate_lahiri_d1(
    *,
    chart_uid: str,
    dt: _dt.datetime,
    latitude: float,
    longitude: float,
    use_birth_time_data: bool,
    source_token: str | None = None,
    rectification_state: Mapping[str, Any] | None = None,
) -> SiderealChartData:
    """Calculate an immutable Lahiri D1 without mutating a parent ``Chart``."""

    uid = _require_uid(chart_uid)
    shift = lahiri_ayanamsha(dt)
    tropical = planetary_positions(dt, latitude, longitude)
    positions = {name: (float(value) - shift) % 360.0 for name, value in tropical.items()}
    house_cusps: tuple[float, ...] | None = None
    ascendant = mc = None
    if use_birth_time_data:
        house_cusps, ascendant, mc = _sidereal_houses(dt, latitude, longitude)
        positions.update({"AS": ascendant, "MC": mc, "DS": (ascendant + 180.0) % 360.0, "IC": (mc + 180.0) % 360.0})

    token = source_token or source_recalculation_token(
        dt=dt,
        latitude=latitude,
        longitude=longitude,
        use_birth_time_data=use_birth_time_data,
        rectification_state=rectification_state,
    )
    aspects = tuple(MappingProxyType(dict(aspect)) for aspect in find_aspects(positions))
    immutable_positions = MappingProxyType(positions)
    return SiderealChartData(
        chart_uid=uid,
        ayanamsha=LAHIRI,
        ayanamsha_degrees=shift,
        positions=immutable_positions,
        retrogrades=MappingProxyType(planetary_retrogrades(dt)),
        ascendant=ascendant,
        mc=mc,
        house_cusps=house_cusps,
        aspects=aspects,
        nakshatras=MappingProxyType({name: nakshatra_position(value) for name, value in positions.items()}),
        source_recalculation_token=token,
    )
