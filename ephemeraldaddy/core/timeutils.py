# ephemeraldaddy/core/timeutils.py
from ephemeraldaddy.core.deps import ensure_package
import datetime as _dt
from zoneinfo import ZoneInfo

_timezonefinder = ensure_package("timezonefinder")
TimezoneFinder = _timezonefinder.TimezoneFinder

_tf = TimezoneFinder()


def timezone_from_latlon(lat: float, lon: float) -> tuple[ZoneInfo, bool]:
    """
    Given latitude and longitude, return (ZoneInfo, inferred_ok).

    inferred_ok == False means: could not infer a local timezone, used UTC instead.
    """
    try:
        name = _tf.timezone_at(lat=lat, lng=lon)
    except Exception:
        name = None

    if not name:
        return ZoneInfo("UTC"), False

    return ZoneInfo(name), True


def localize_naive_datetime(dt_local: _dt.datetime, lat: float, lon: float):
    """
    Given a naive datetime and coordinates, attach the best timezone we can.

    Returns (tz_aware_datetime, inferred_ok).
    """
    if dt_local.tzinfo is not None:
        return dt_local, True

    tz, inferred_ok = timezone_from_latlon(lat, lon)
    return dt_local.replace(tzinfo=tz), inferred_ok

# ephemeraldaddy/core/timeutils.py  (add this at the end)

from skyfield.api import load

_ts = load.timescale()


def local_sidereal_time(dt_aware: _dt.datetime, lon_deg: float) -> float:
    """
    Return local sidereal time in DEGREES for a given aware datetime and longitude.

    dt_aware: timezone-aware datetime (will be converted to UTC for Skyfield)
    lon_deg: geographic longitude in degrees (east positive, west negative)

    LST = GAST + longitude, all in degrees, wrapped to [0, 360).
    """
    if dt_aware.tzinfo is None:
        raise ValueError("local_sidereal_time requires a timezone-aware datetime")

    # Skyfield wants UTC
    dt_utc = dt_aware.astimezone(_dt.timezone.utc)

    t = _ts.from_datetime(dt_utc)

    # Skyfield gives Greenwich apparent sidereal time in HOURS
    gast_hours = t.gast
    gast_deg = (gast_hours * 15.0) % 360.0

    lst_deg = (gast_deg + lon_deg) % 360.0
    return lst_deg

