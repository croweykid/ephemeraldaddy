# ephemeraldaddy/io/geocode.py
#from ephemeraldaddy.core.deps import ensure_package #commented out to localize search to offline.

import os
import logging
import uuid
from functools import partial
from threading import Lock

from typing import List, Tuple
#from geopy.geocoders import Nominatim
#from geopy.extra.rate_limiter import RateLimiter

#_geopy = ensure_package("geopy")
#Nominatim = _geopy.geocoders.Nominatim
#_geocoder = Nominatim(user_agent="ephemeraldaddy")
#_geocode_rl = RateLimiter(_geocoder.geocode, min_delay_seconds=1)

from ephemeraldaddy.core.deps import ensure_package
from ephemeraldaddy.analysis.birthplace import (
    BirthplaceLocality, gazetteer_label, locality_from_address,
)
from ephemeraldaddy.io.local_gazetteer import (
    local_geocode_location,
    local_search_locations,
    resolve_search_sources,
)
from ephemeraldaddy.io.web_profile.pacing import pace_remote_request, check_remote_request_cancelled

_geolocator = None
_geolocator_lock = Lock()
logger = logging.getLogger(__name__)


class LocationLookupError(Exception):
    """Raised when a birth location string cannot be resolved to coordinates."""
    pass


def _new_lookup_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_geolocator():
    global _geolocator
    with _geolocator_lock:
        if _geolocator is None:
            _geopy = ensure_package("geopy")
            from geopy.extra.rate_limiter import RateLimiter
            locator = _geopy.geocoders.Nominatim(user_agent="ephemeraldaddy")
            def request(method, *args, **kwargs):
                check_remote_request_cancelled()
                return method(*args, **kwargs)
            # Forward search and background reverse repair share one process
            # gate, even when they run in independent windows/lookup workers.
            gate = RateLimiter(request, min_delay_seconds=1, max_retries=0,
                               swallow_exceptions=False)
            locator.geocode = partial(gate, locator.geocode)
            locator.reverse = partial(gate, locator.reverse)
            _geolocator = locator
    return _geolocator


def _online_geocode(query: str):
    lookup_id = _new_lookup_id("geocode_online")
    geolocator = _get_geolocator()
    try:
        pace_remote_request()
        loc = geolocator.geocode(query, addressdetails=True)
    except Exception as exc:
        logger.exception(
            "Online geocode lookup failed (id=%s query=%r): %s",
            lookup_id,
            query,
            exc,
        )
        raise LocationLookupError(f"Birth location lookup failed for {query!r}") from exc

    if loc is None:
        logger.info("Online geocode returned no result (id=%s query=%r).", lookup_id, query)
        raise LocationLookupError(f"Birth location not found for {query!r}")

    label = _location_locality(loc).label
    if not label:
        raise LocationLookupError(f"No locality metadata found for {query!r}")
    return loc.latitude, loc.longitude, label


def _location_locality(location):
    address = (getattr(location, "raw", None) or {}).get("address")
    if isinstance(address, dict):
        return locality_from_address(address)
    # addressdetails is required. A provider's display_name is not locality data.
    return BirthplaceLocality()


def locality_for_coordinates(latitude: float, longitude: float):
    """Resolve an existing coordinate to its containing locality, not a POI.

    zoom=10 requests a city-level result. Never use a nearest gazetteer city,
    which can silently move a rural birthplace into another municipality.
    """
    if os.environ.get("EPHEMERALDADDY_GAZETTEER_ONLY", "").lower() in {"1", "true", "yes"}:
        raise LocationLookupError("Online locality resolution is disabled.")
    pace_remote_request()
    location = _get_geolocator().reverse(
        (latitude, longitude), exactly_one=True, addressdetails=True, zoom=10,
    )
    if location is None:
        raise LocationLookupError("No locality found for the saved birth coordinates.")
    locality = _location_locality(location)
    if not locality.city or not locality.country:
        raise LocationLookupError("The saved birth coordinates have no confirmed city and country.")
    return locality

def geocode_location(query: str):
    """
    Given a string like 'Chicago, IL, USA', return (lat, lon, display_name).

    Raises LocationLookupError if geocoding fails.
    """
    local = local_geocode_location(query)
    if local is not None:
        latitude, longitude, label = local
        return latitude, longitude, gazetteer_label(label)

    if os.environ.get("EPHEMERALDADDY_GAZETTEER_ONLY", "").lower() in {"1", "true", "yes"}:
        raise LocationLookupError(
            "Birth location not found in local gazetteer. "
            "Set EPHEMERALDADDY_GAZETTEER_ONLY=0 to enable online search."
        )

    return _online_geocode(query)

def _online_search_enabled() -> bool:
    return os.environ.get("EPHEMERALDADDY_GAZETTEER_SEARCH_ONLINE", "").lower() in {
        "1",
        "true",
        "yes",
    }

def search_locations(query: str, limit: int = 5, *, allow_online: bool | None = None) -> List[Tuple[str, float, float]]:
    """
    Return up to `limit` candidate locations for a free-text query.

    Each item: (label, lat, lon)
    allow_online overrides the search preference, while gazetteer-only mode
    still prevents online requests.
    """
    q = (query or "").strip()
    if not q:
        return []
    lookup_id = _new_lookup_id("search_locations")
    logger.debug("Location search started (id=%s query=%r limit=%s).", lookup_id, q, limit)

    sources = resolve_search_sources()
    online_enabled = _online_search_enabled() if allow_online is None else allow_online
    results: List[Tuple[str, float, float]] = []

    if "local" in sources:
        results = [(gazetteer_label(label), lat, lon)
                   for label, lat, lon in local_search_locations(q, limit=limit)]
        if results or not online_enabled:
            logger.debug(
                "Location search resolved via local source (id=%s result_count=%s).",
                lookup_id,
                len(results),
            )
            return results

    if "online" not in sources or not online_enabled:
        logger.debug("Location search had no online fallback (id=%s).", lookup_id)
        return []

    geocoder = _get_geolocator()
    # Local hits and disabled online fallbacks never consume a pacing slot.
    pace_remote_request()
    try:
        matches = geocoder.geocode(q, exactly_one=False, addressdetails=True, limit=limit)
    except Exception as exc:
        logger.exception(
            "Location search online query failed (id=%s query=%r): %s",
            lookup_id,
            q,
            exc,
        )
        return []
    if not matches:
        logger.info("Location search returned no matches (id=%s query=%r).", lookup_id, q)
        return []

    logger.debug("Location search resolved via online source (id=%s result_count=%s).", lookup_id, len(matches))
    return [(label, result.latitude, result.longitude) for result in matches
            if (label := _location_locality(result).label)]
