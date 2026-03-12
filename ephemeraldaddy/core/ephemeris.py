from skyfield.api import load, wgs84, N, E
from skyfield.framelib import ecliptic_frame  # true ecliptic & equinox of date :contentReference[oaicite:4]{index=4}
import datetime
import math
import os
from pathlib import Path
from urllib.request import urlopen
import warnings

from ephemeraldaddy.core.deps import ensure_package
_swe = ensure_package("pyswisseph")
swe = _swe

_SWE_CONFIGURED = False
_SWE_EPHE_PATH: Path | None = None
_SWE_DATA_READY = False
_SWE_ASTEROID_FILES: dict[str, tuple[set[str], tuple[str, ...]]] = {
    "seas_18.se1": (
        {"Ceres", "Pallas", "Juno", "Vesta"},
        (
            "https://www.astro.com/ftp/swisseph/ephe/seas_18.se1",
            "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1",
        ),
    ),
    "seorbel.txt": (
        {"Chiron"},
        (
            "https://www.astro.com/ftp/swisseph/ephe/seorbel.txt",
            "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seorbel.txt",
        ),
    ),
}
_SWE_WARNED_MISSING_DATA = False

def _configure_swiss_ephemeris() -> None:
    global _SWE_CONFIGURED
    global _SWE_EPHE_PATH
    if _SWE_CONFIGURED:
        return

    env_path = os.environ.get("SWEPH_PATH") or os.environ.get("EPHEMERALDADDY_SWEPH_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        swe.set_ephe_path(str(path))
        _SWE_EPHE_PATH = path
        _SWE_CONFIGURED = True
        return

    candidates = []
    swe_module_path = Path(getattr(swe, "__file__", "")).resolve()
    if swe_module_path:
        candidates.append(swe_module_path.parent / "sweph")

    candidates.append(Path.home() / ".local" / "share" / "ephemeraldaddy" / "sweph")
    candidates.append(Path(__file__).resolve().parent / "sweph")

    for path in candidates:
        if path.is_dir():
            swe.set_ephe_path(str(path))
            _SWE_EPHE_PATH = path
            _SWE_CONFIGURED = True
            return

    fallback = Path.home() / ".local" / "share" / "ephemeraldaddy" / "sweph"
    fallback.mkdir(parents=True, exist_ok=True)
    swe.set_ephe_path(str(fallback))
    _SWE_EPHE_PATH = fallback
    _SWE_CONFIGURED = True

def is_offline_mode() -> bool:
    """Stubbed offline-mode flag for future UI wiring."""
    return os.environ.get("EPHEMERALDADDY_OFFLINE_MODE", "").lower() in {"1", "true", "yes", "on"}


def _ensure_swiss_ephemeris_data(required_bodies: set[str], *, allow_download: bool = True) -> None:
    global _SWE_DATA_READY
    global _SWE_WARNED_MISSING_DATA
    if _SWE_DATA_READY:
        return
    if not required_bodies:
        _SWE_DATA_READY = True
        return
    _configure_swiss_ephemeris()
    target_dir = _SWE_EPHE_PATH
    if target_dir is None:
        target_dir = Path.home() / ".local" / "share" / "ephemeraldaddy" / "sweph"
        target_dir.mkdir(parents=True, exist_ok=True)
        swe.set_ephe_path(str(target_dir))
    missing_bodies = set(required_bodies)
    for filename, (bodies, urls) in _SWE_ASTEROID_FILES.items():
        if not required_bodies.intersection(bodies):
            continue
        target_path = target_dir / filename
        if target_path.exists():
            missing_bodies.difference_update(bodies)
            continue
        if allow_download:
            for url in urls:
                try:
                    with urlopen(url, timeout=20) as response:
                        target_path.write_bytes(response.read())
                    break
                except Exception:
                    continue
        if target_path.exists():
            missing_bodies.difference_update(bodies)

    _SWE_DATA_READY = not bool(missing_bodies)
    if missing_bodies and not _SWE_WARNED_MISSING_DATA:
        warnings.warn(
            "Swiss Ephemeris asteroid files are missing; minor-body positions may be unavailable. "
            "Set SWEPH_PATH/EPHEMERALDADDY_SWEPH_PATH to a directory containing Swiss ephemeris asteroid files.",
            RuntimeWarning,
            stacklevel=2,
        )
        _SWE_WARNED_MISSING_DATA = True


def prepare_swiss_ephemeris_data(required_bodies: set[str] | None = None) -> None:
    """Preload Swiss asteroid data readiness; safe to call from background workers."""
    if required_bodies is None:
        required_bodies = {"Chiron", "Ceres", "Pallas", "Juno", "Vesta"}
    _configure_swiss_ephemeris()
    _ensure_swiss_ephemeris_data(required_bodies, allow_download=not is_offline_mode())

ts = load.timescale()
eph = load('de421.bsp')

EARTH = eph[399] # hard-code geocenter; avoids accidentally using ID 3 :contentReference[oaicite:5]{index=5}

PLANETS = {
    "Sun": eph['sun'],
    "Moon": eph['moon'],
    "Mercury": eph['mercury'],
    "Venus": eph['venus'],
    "Mars": eph['mars'],
    "Jupiter": eph['jupiter barycenter'],
    "Saturn": eph['saturn barycenter'],
    "Uranus": eph['uranus barycenter'],
    "Neptune": eph['neptune barycenter'],
    "Pluto": eph['pluto barycenter'],
}

_SWE_PLANET_FALLBACK_IDS = {
    "Sun": ("SE_SUN", "SUN"),
    "Moon": ("SE_MOON", "MOON"),
    "Mercury": ("SE_MERCURY", "MERCURY"),
    "Venus": ("SE_VENUS", "VENUS"),
    "Mars": ("SE_MARS", "MARS"),
    "Jupiter": ("SE_JUPITER", "JUPITER"),
    "Saturn": ("SE_SATURN", "SATURN"),
    "Uranus": ("SE_URANUS", "URANUS"),
    "Neptune": ("SE_NEPTUNE", "NEPTUNE"),
    "Pluto": ("SE_PLUTO", "PLUTO"),
}

def planetary_positions(dt_aware, lat, lon):
    """
    dt_aware must be a timezone-aware datetime.
    Chart is responsible for attaching timezone.
    """
    if dt_aware.tzinfo is None:
        raise ValueError("planetary_positions expects a timezone-aware datetime")

    _configure_swiss_ephemeris()
    _ensure_swiss_ephemeris_data({"Chiron", "Ceres", "Pallas", "Juno", "Vesta"}, allow_download=not is_offline_mode())

    # t = ts.from_datetime(dt_aware)
    # #location = EARTH + wgs84.latlon(lat * N, lon * E)

    # results = {}
    # earth_at_t = EARTH.at(t)
    # for name, body in PLANETS.items():
    #     apparent = earth_at_t.observe(body).apparent()

    #     # Preferred: explicit ecliptic-of-date frame (works broadly)
    #     ecl_lat, ecl_lon, dist = apparent.frame_latlon(ecliptic_frame)

    #     # Alternative if your Skyfield is new enough:
    #     # ecl_lat, ecl_lon, dist = apparent.ecliptic_latlon(epoch='date')  :contentReference[oaicite:7]{index=7}

    #     results[name] = ecl_lon.degrees % 360.0

    dt_utc = dt_aware.astimezone(datetime.timezone.utc)
    hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)

    t = ts.from_datetime(dt_aware)
    #location = EARTH + wgs84.latlon(lat * N, lon * E)

    results = {}
    earth_at_t = None
    try:
        earth_at_t = EARTH.at(t)
    except Exception:
        # Skyfield/de421 coverage is finite; Swiss Ephemeris fallback below
        # supports broader historical/future ranges.
        earth_at_t = None

    def _swe_body_id(*names: str) -> int:
        for name in names:
            if hasattr(swe, name):
                return getattr(swe, name)
        raise AttributeError(f"Swiss Ephemeris body not available: {names[0]}")

    def _swe_body_id_optional(*names: str) -> int | None:
        for name in names:
            if hasattr(swe, name):
                return getattr(swe, name)
        return None

    def _swe_longitude(body_id: int) -> float | None:
        lon = None
        try:
            lon, _ret = swe.calc_ut(jd_ut, body_id)
        except Exception:
            lon = None

        if lon is None or not math.isfinite(lon[0]):
            try:
                lon, _ret = swe.calc_ut(jd_ut, body_id, swe.FLG_MOSEPH)
            except Exception:
                return None

        if lon is None or not math.isfinite(lon[0]):
            return None
        return lon[0] % 360.0

    for name, body in PLANETS.items():
        longitude: float | None = None
        if earth_at_t is not None:
            try:
                apparent = earth_at_t.observe(body).apparent()
                _ecl_lat, ecl_lon, _dist = apparent.frame_latlon(ecliptic_frame)
                if math.isfinite(ecl_lon.degrees):
                    longitude = ecl_lon.degrees % 360.0
            except Exception:
                longitude = None

        if longitude is None:
            fallback_names = _SWE_PLANET_FALLBACK_IDS.get(name)
            if fallback_names:
                longitude = _swe_longitude(_swe_body_id(*fallback_names))

        if longitude is not None:
            results[name] = longitude

    chiron = _swe_longitude(_swe_body_id("SE_CHIRON", "CHIRON"))
    if chiron is not None:
        results["Chiron"] = chiron
    ceres = _swe_longitude(_swe_body_id("SE_CERES", "CERES"))
    if ceres is not None:
        results["Ceres"] = ceres
    pallas = _swe_longitude(_swe_body_id("SE_PALLAS", "PALLAS"))
    if pallas is not None:
        results["Pallas"] = pallas
    juno = _swe_longitude(_swe_body_id("SE_JUNO", "JUNO"))
    if juno is not None:
        results["Juno"] = juno
    vesta = _swe_longitude(_swe_body_id("SE_VESTA", "VESTA"))
    if vesta is not None:
        results["Vesta"] = vesta
    rahu = _swe_longitude(_swe_body_id("SE_TRUE_NODE", "TRUE_NODE"))
    if rahu is not None:
        results["Rahu"] = rahu
        results["Ketu"] = (rahu + 180.0) % 360.0
    # Use Black Moon Lilith (mean apogee) only.
    mean_lilith_id = _swe_body_id_optional("SE_MEAN_APOG", "MEAN_APOG", "MEAN_APOGEE")
    mean_lilith = _swe_longitude(mean_lilith_id) if mean_lilith_id is not None else None
    if mean_lilith is not None:
        results["Lilith"] = mean_lilith

    return results


def planetary_retrogrades(dt_aware) -> dict[str, bool]:
    """Return retrograde flags for supported bodies at the given datetime."""
    if dt_aware.tzinfo is None:
        raise ValueError("planetary_retrogrades expects a timezone-aware datetime")

    _configure_swiss_ephemeris()
    _ensure_swiss_ephemeris_data({"Chiron", "Ceres", "Pallas", "Juno", "Vesta"}, allow_download=not is_offline_mode())

    dt_utc = dt_aware.astimezone(datetime.timezone.utc)
    hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)

    def _swe_body_id_optional(*names: str) -> int | None:
        for name in names:
            if hasattr(swe, name):
                return getattr(swe, name)
        return None

    def _swe_lon_speed(body_id: int | None) -> tuple[float, float] | None:
        if body_id is None:
            return None
        values = None
        try:
            values, _ret = swe.calc_ut(jd_ut, body_id)
        except Exception:
            values = None

        if values is None or not math.isfinite(values[0]):
            try:
                values, _ret = swe.calc_ut(jd_ut, body_id, swe.FLG_MOSEPH)
            except Exception:
                return None
        if values is None or len(values) < 4 or not math.isfinite(values[3]):
            return None
        return values[0] % 360.0, float(values[3])

    bodies = {
        "Sun": _swe_body_id_optional("SE_SUN", "SUN"),
        "Moon": _swe_body_id_optional("SE_MOON", "MOON"),
        "Mercury": _swe_body_id_optional("SE_MERCURY", "MERCURY"),
        "Venus": _swe_body_id_optional("SE_VENUS", "VENUS"),
        "Mars": _swe_body_id_optional("SE_MARS", "MARS"),
        "Jupiter": _swe_body_id_optional("SE_JUPITER", "JUPITER"),
        "Saturn": _swe_body_id_optional("SE_SATURN", "SATURN"),
        "Uranus": _swe_body_id_optional("SE_URANUS", "URANUS"),
        "Neptune": _swe_body_id_optional("SE_NEPTUNE", "NEPTUNE"),
        "Pluto": _swe_body_id_optional("SE_PLUTO", "PLUTO"),
        "Chiron": _swe_body_id_optional("SE_CHIRON", "CHIRON"),
        "Ceres": _swe_body_id_optional("SE_CERES", "CERES"),
        "Pallas": _swe_body_id_optional("SE_PALLAS", "PALLAS"),
        "Juno": _swe_body_id_optional("SE_JUNO", "JUNO"),
        "Vesta": _swe_body_id_optional("SE_VESTA", "VESTA"),
        "Rahu": _swe_body_id_optional("SE_TRUE_NODE", "TRUE_NODE"),
        "Lilith": _swe_body_id_optional("SE_MEAN_APOG", "MEAN_APOG", "MEAN_APOGEE"),
    }

    retrogrades: dict[str, bool] = {}
    for body, body_id in bodies.items():
        values = _swe_lon_speed(body_id)
        if values is None:
            continue
        _lon, speed = values
        retrogrades[body] = speed < 0
    if "Rahu" in retrogrades:
        retrogrades["Ketu"] = retrogrades["Rahu"]

    return retrogrades

def local_sidereal_time_deg(dt, lon_deg: float) -> float:
    """
    Return local apparent sidereal time at longitude `lon_deg` in DEGREES.

    dt: tz-aware datetime (UTC or with correct tzinfo)
    lon_deg: geographic longitude (positive east, negative west)
    """
    t = ts.from_datetime(dt)
    # Greenwich apparent sidereal time in hours
    gast_hours = t.gast
    # Local sidereal time in hours
    lst_hours = gast_hours + lon_deg / 15.0
    return (lst_hours * 15.0) % 360.0
