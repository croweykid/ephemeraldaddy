# ephemeraldaddy/io/geocode.py
#from ephemeraldaddy.core.deps import ensure_package #commented out to localize search to offline.

import os
import logging
import uuid

from typing import List, Tuple
#from geopy.geocoders import Nominatim
#from geopy.extra.rate_limiter import RateLimiter

#_geopy = ensure_package("geopy")
#Nominatim = _geopy.geocoders.Nominatim
#_geocoder = Nominatim(user_agent="ephemeraldaddy")
#_geocode_rl = RateLimiter(_geocoder.geocode, min_delay_seconds=1)

from ephemeraldaddy.core.deps import ensure_package
from ephemeraldaddy.io.local_gazetteer import (
    local_geocode_location,
    local_search_locations,
    resolve_search_sources,
)

_geolocator = None
logger = logging.getLogger(__name__)


class LocationLookupError(Exception):
    """Raised when a birth location string cannot be resolved to coordinates."""
    pass


def _new_lookup_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_geolocator():
    global _geolocator
    if _geolocator is None:
        _geopy = ensure_package("geopy")
        _geolocator = _geopy.geocoders.Nominatim(user_agent="ephemeraldaddy")
    return _geolocator


def _online_geocode(query: str):
    lookup_id = _new_lookup_id("geocode_online")
    geolocator = _get_geolocator()
    try:
        loc = geolocator.geocode(query)
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

    return loc.latitude, loc.longitude, loc.address

def geocode_location(query: str):
    """
    Given a string like 'Chicago, IL, USA', return (lat, lon, display_name).

    Raises LocationLookupError if geocoding fails.
    """
    local = local_geocode_location(query)
    if local is not None:
        return local

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

def search_locations(query: str, limit: int = 5) -> List[Tuple[str, float, float]]:
    """
    Return up to `limit` candidate locations for a free-text query.

    Each item: (label, lat, lon)
    """
    q = (query or "").strip()
    if not q:
        return []
    lookup_id = _new_lookup_id("search_locations")
    logger.debug("Location search started (id=%s query=%r limit=%s).", lookup_id, q, limit)

    sources = resolve_search_sources()
    results: List[Tuple[str, float, float]] = []

    if "local" in sources:
        results = local_search_locations(q, limit=limit)
        if results or not _online_search_enabled():
            logger.debug(
                "Location search resolved via local source (id=%s result_count=%s).",
                lookup_id,
                len(results),
            )
            return results

    if "online" not in sources or not _online_search_enabled():
        logger.debug("Location search had no online fallback (id=%s).", lookup_id)
        return []

    geocoder = _get_geolocator()
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
    return [(r.address, r.latitude, r.longitude) for r in matches]
