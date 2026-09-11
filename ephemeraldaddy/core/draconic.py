"""Draconic zodiac position and cross-aspect helpers.

Draconic longitudes rotate the natal zodiac so the natal North Node (Rahu)
is 0° Aries. The transformation changes zodiac longitude while preserving
the chart's internal angular relationships. House membership is preserved
because house cusps rotate by the same offset, even though the cusps' zodiac
signs/degrees change in the Draconic reference frame.
"""

from __future__ import annotations

from collections.abc import Mapping

from ephemeraldaddy.core.aspects import ASPECT_DEFS


def draconic_longitude(longitude: float, north_node_longitude: float) -> float:
    """Return *longitude* rotated so *north_node_longitude* becomes 0° Aries."""
    return (float(longitude) - float(north_node_longitude)) % 360.0


def calculate_draconic_positions(
    positions: Mapping[str, float | None],
    *,
    north_node_key: str = "Rahu",
) -> dict[str, float]:
    """Return Draconic longitudes for all known positions.

    EphemeralDaddy's canonical North Node key is ``Rahu``. Entries with an
    unknown longitude are omitted. A missing North Node cannot define a
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


def _angular_diff(a: float, b: float) -> float:
    """Return the smallest absolute angular separation between two longitudes."""
    diff = abs(float(a) - float(b)) % 360.0
    return min(diff, 360.0 - diff)


def find_draconic_natal_aspects(
    draconic_positions: Mapping[str, float | None],
    natal_positions: Mapping[str, float | None],
    *,
    aspect_defs: Mapping[str, Mapping[str, float]] = ASPECT_DEFS,
) -> list[dict[str, object]]:
    """Return directed Draconic -> natal/tropical cross-aspects.

    These are deliberately *not* aspects among Draconic positions themselves.
    A whole-chart Draconic rotation preserves every natal internal aspect, so
    Draconic-to-Draconic aspects would merely duplicate the natal aspect table.

    Each result keeps the base body names in ``p1`` and ``p2`` and records the
    two source longitudes separately. The caller is responsible for labeling
    ``p1`` as Draconic and ``p2`` as natal/tropical in presentation.
    """
    aspects: list[dict[str, object]] = []
    for draconic_body, draconic_lon in draconic_positions.items():
        if draconic_lon is None:
            continue
        for natal_body, natal_lon in natal_positions.items():
            if natal_lon is None:
                continue
            separation = _angular_diff(float(draconic_lon), float(natal_lon))
            for aspect_type, config in aspect_defs.items():
                target = float(config["angle"])
                orb = float(config["orb"])
                delta = separation - target
                if abs(delta) <= orb:
                    aspects.append(
                        {
                            "p1": str(draconic_body),
                            "p2": str(natal_body),
                            "type": str(aspect_type),
                            "angle": separation,
                            "delta": delta,
                            "draconic_longitude": float(draconic_lon) % 360.0,
                            "natal_longitude": float(natal_lon) % 360.0,
                        }
                    )
                    break
    return aspects
