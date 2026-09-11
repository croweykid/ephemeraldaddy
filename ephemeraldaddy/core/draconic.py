"""Draconic zodiac position helpers.

Draconic longitudes rotate the natal zodiac so the natal North Node (Rahu)
is 0° Aries.  The transformation changes zodiac longitude while preserving
the chart's internal angular relationships and house placements.
"""

from __future__ import annotations

from collections.abc import Mapping


def draconic_longitude(longitude: float, north_node_longitude: float) -> float:
    """Return *longitude* rotated so *north_node_longitude* becomes 0° Aries."""
    return (float(longitude) - float(north_node_longitude)) % 360.0


def calculate_draconic_positions(
    positions: Mapping[str, float | None],
    *,
    north_node_key: str = "Rahu",
) -> dict[str, float]:
    """Return Draconic longitudes for all known positions.

    EphemeralDaddy's canonical North Node key is ``Rahu``.  Entries with an
    unknown longitude are omitted.  A missing North Node cannot define a
    Draconic reference frame, so an empty mapping is returned.
    """
    north_node_longitude = positions.get(north_node_key)
    if north_node_longitude is None:
        return {}

    return {
        str(body): draconic_longitude(longitude, north_node_longitude)
        for body, longitude in positions.items()
        if longitude is not None
    }
