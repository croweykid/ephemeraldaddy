from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame  # true ecliptic & equinox of date :contentReference[oaicite:4]{index=4}
import datetime
import math
import os
import shutil
import sys
from pathlib import Path
from urllib.request import urlopen
import warnings

from ephemeraldaddy.core.deps import ensure_package
_swe = ensure_package("pyswisseph")
swe = _swe

_SWE_CONFIGURED = False
_SWE_EPHE_PATH: Path | None = None
_SWE_READY_BODIES: set[str] = set()
_SWE_ASTEROID_FILES: dict[str, tuple[set[str], tuple[str, ...]]] = {
    "seas_18.se1": (
        {"Ceres", "Pallas", "Juno", "Vesta"},
        (
            "https://www.astro.com/ftp/swisseph/ephe/seas_18.se1",
            "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1",
        ),
    ),
    # Some distributions ship Chiron orbital data as ``seorbel.se1`` while
    # others use ``seorbel.txt``; support either name.
    "seorbel.se1": (
        {"Chiron"},
        (
            "https://www.astro.com/ftp/swisseph/ephe/seorbel.se1",
            "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seorbel.se1",
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
    bundled_data = Path(__file__).resolve().parents[1] / "data"
    candidates.append(bundled_data)
    candidates.append(Path(__file__).resolve().parent / "sweph")
    candidates.append(Path.home() / ".local" / "share" / "ephemeraldaddy" / "sweph")
    if swe_module_path:
        candidates.append(swe_module_path.parent / "sweph")

    def _has_asteroid_files(path: Path) -> bool:
        if not path.is_dir():
            return False
        expected = {name.lower() for name in _SWE_ASTEROID_FILES}
        present = {entry.name.lower() for entry in path.iterdir() if entry.is_file()}
        return bool(expected.intersection(present))

    selected_path: Path | None = None
    for path in candidates:
        if _has_asteroid_files(path):
            selected_path = path
            break
    if selected_path is None:
        for path in candidates:
            if path.is_dir():
                selected_path = path
                break

    if selected_path is not None:
        swe.set_ephe_path(str(selected_path))
        _SWE_EPHE_PATH = selected_path
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
    global _SWE_READY_BODIES
    global _SWE_WARNED_MISSING_DATA
    if required_bodies.issubset(_SWE_READY_BODIES):
        return
    if not required_bodies:
        return
    _configure_swiss_ephemeris()
    target_dir = _SWE_EPHE_PATH
    if target_dir is None:
        target_dir = Path.home() / ".local" / "share" / "ephemeraldaddy" / "sweph"
        target_dir.mkdir(parents=True, exist_ok=True)
        swe.set_ephe_path(str(target_dir))
    missing_bodies = set(required_bodies)
    available_files = {path.name.lower() for path in target_dir.iterdir() if path.is_file()}

    for filename, (bodies, urls) in _SWE_ASTEROID_FILES.items():
        if not required_bodies.intersection(bodies):
            continue
        if filename.lower() in available_files:
            missing_bodies.difference_update(bodies)
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

    _SWE_READY_BODIES.update(required_bodies.difference(missing_bodies))
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

_TS = None
_EPH = None
_EARTH = None
_PLANETS = None
_SKYFIELD_LOADER = None


def _get_ephemeraldaddy_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "EphemeralDaddy"
    if os.name == "darwin":
        return Path.home() / "Library" / "Application Support" / "EphemeralDaddy"
    return Path.home() / ".local" / "share" / "ephemeraldaddy"


def _iter_de421_source_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        candidates.append(Path(bundled_root) / "de421.bsp")

    candidates.append(Path(__file__).resolve().parents[2] / "de421.bsp")
    candidates.append(Path.cwd() / "de421.bsp")
    return tuple(candidates)


def _get_skyfield_loader() -> Loader:
    global _SKYFIELD_LOADER
    if _SKYFIELD_LOADER is not None:
        return _SKYFIELD_LOADER

    override = os.environ.get("EPHEMERALDADDY_SKYFIELD_PATH")
    data_dir = Path(override).expanduser() if override else (_get_ephemeraldaddy_data_dir() / "skyfield")
    data_dir.mkdir(parents=True, exist_ok=True)

    target_de421 = data_dir / "de421.bsp"
    if not target_de421.exists():
        for candidate in _iter_de421_source_candidates():
            if candidate.exists():
                try:
                    shutil.copyfile(candidate, target_de421)
                    break
                except Exception:
                    continue

    _SKYFIELD_LOADER = Loader(str(data_dir))
    return _SKYFIELD_LOADER


def _get_skyfield_context():
    """Lazily load heavy Skyfield resources on first use."""
    global _TS, _EPH, _EARTH, _PLANETS
    loader = _get_skyfield_loader()
    if _TS is None:
        _TS = loader.timescale()
    if _EPH is None:
        _EPH = loader("de421.bsp")
    if _EARTH is None:
        _EARTH = _EPH[399]  # hard-code geocenter; avoids accidentally using ID 3
    if _PLANETS is None:
        _PLANETS = {
            "Sun": _EPH["sun"],
            "Moon": _EPH["moon"],
            "Mercury": _EPH["mercury"],
            "Venus": _EPH["venus"],
            "Mars": _EPH["mars"],
            "Jupiter": _EPH["jupiter barycenter"],
            "Saturn": _EPH["saturn barycenter"],
            "Uranus": _EPH["uranus barycenter"],
            "Neptune": _EPH["neptune barycenter"],
            "Pluto": _EPH["pluto barycenter"],
        }
    return _TS, _EARTH, _PLANETS

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

_SWE_NAMED_BODY_IDS = {
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
    "Chiron": ("SE_CHIRON", "CHIRON"),
    "Ceres": ("SE_CERES", "CERES"),
    "Pallas": ("SE_PALLAS", "PALLAS"),
    "Juno": ("SE_JUNO", "JUNO"),
    "Vesta": ("SE_VESTA", "VESTA"),
    "Rahu": ("SE_TRUE_NODE", "TRUE_NODE"),
}

LILITH_CALCULATION_MEAN = "mean"
LILITH_CALCULATION_TRUE = "true"
_LILITH_CALCULATION_MODE = LILITH_CALCULATION_MEAN


def _normalize_lilith_calculation_mode(mode: str | None) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in {LILITH_CALCULATION_MEAN, LILITH_CALCULATION_TRUE}:
        return normalized
    return LILITH_CALCULATION_MEAN


def set_lilith_calculation_mode(mode: str | None) -> str:
    global _LILITH_CALCULATION_MODE
    normalized = _normalize_lilith_calculation_mode(mode)
    _LILITH_CALCULATION_MODE = normalized
    return normalized


def get_lilith_calculation_mode() -> str:
    return _LILITH_CALCULATION_MODE


def get_lilith_display_name(mode: str | None = None) -> str:
    normalized_mode = _normalize_lilith_calculation_mode(mode or _LILITH_CALCULATION_MODE)
    if normalized_mode == LILITH_CALCULATION_TRUE:
        return "True Lilith"
    return "Black Moon Lilith"


def _lilith_swe_id_names(mode: str | None = None) -> tuple[str, ...]:
    normalized_mode = _normalize_lilith_calculation_mode(mode or _LILITH_CALCULATION_MODE)
    if normalized_mode == LILITH_CALCULATION_TRUE:
        # Osculating ("true") lunar apogee.
        return ("SE_OSCU_APOG", "OSCU_APOG", "OSCU_APOGEE")
    # Mean lunar apogee.
    return ("SE_MEAN_APOG", "MEAN_APOG", "MEAN_APOGEE")


def planetary_longitude(dt_aware: datetime.datetime, body_name: str) -> float | None:
    """
    Fast Swiss-Ephemeris-only longitude lookup for a single named body.

    Returns ``None`` when the body is unsupported or no finite longitude
    could be resolved for the timestamp.
    """
    if dt_aware.tzinfo is None:
        raise ValueError("planetary_longitude expects a timezone-aware datetime")

    normalized_name = str(body_name or "").strip()
    if not normalized_name:
        return None
    if normalized_name == "Ketu":
        rahu = planetary_longitude(dt_aware, "Rahu")
        return None if rahu is None else (rahu + 180.0) % 360.0

    if normalized_name == "Lilith":
        names = _lilith_swe_id_names()
    else:
        names = _SWE_NAMED_BODY_IDS.get(normalized_name)
    if not names:
        return None

    _configure_swiss_ephemeris()
    _ensure_swiss_ephemeris_data({normalized_name}, allow_download=not is_offline_mode())

    dt_utc = dt_aware.astimezone(datetime.timezone.utc)
    hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)

    body_id = None
    for candidate in names:
        if hasattr(swe, candidate):
            body_id = getattr(swe, candidate)
            break
    if body_id is None:
        return None

    lon = None
    try:
        lon, _ret = swe.calc_ut(jd_ut, body_id)
    except Exception:
        lon = None

    if lon is None or not math.isfinite(lon[0]):
        try:
            lon, _ret = swe.calc_ut(jd_ut, body_id, swe.FLG_MOSEPH)
        except Exception:
            lon = None

    if lon is None or not math.isfinite(lon[0]):
        return None
    return float(lon[0]) % 360.0

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

    ts, earth, planets = _get_skyfield_context()
    t = ts.from_datetime(dt_aware)
    #location = EARTH + wgs84.latlon(lat * N, lon * E)

    results = {}
    earth_at_t = None
    try:
        earth_at_t = earth.at(t)
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

    for name, body in planets.items():
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
    lilith_id = _swe_body_id_optional(*_lilith_swe_id_names())
    lilith = _swe_longitude(lilith_id) if lilith_id is not None else None
    if lilith is not None:
        results["Lilith"] = lilith

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
        "Lilith": _swe_body_id_optional(*_lilith_swe_id_names()),
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
    ts, _earth, _planets = _get_skyfield_context()
    t = ts.from_datetime(dt)
    # Greenwich apparent sidereal time in hours
    gast_hours = t.gast
    # Local sidereal time in hours
    lst_hours = gast_hours + lon_deg / 15.0
    return (lst_hours * 15.0) % 360.0
