"""Coordinate-aware projection helpers for transient chart samples.

These helpers are intentionally non-persisting. They are for hypothetical
charts (for example Time Sensitivity samples) that need to use the same
Tropical/Sidereal coordinate lens as the active Chart Editor without creating
or updating a persisted Sidereal D1 row.
"""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.core.aspects import find_aspects
from ephemeraldaddy.core.ephemeris import planetary_retrogrades
from ephemeraldaddy.core.sidereal import (
    LAHIRI,
    ZodiacContext,
    _sidereal_houses,
    planetary_positions_for_zodiac,
    nakshatra_position,
)


def zodiac_context_for_chart(
    chart: Any,
    *,
    zodiac: str | None = None,
    ayanamsha: str | None = None,
) -> ZodiacContext:
    """Resolve a validated coordinate context from explicit values or a chart."""

    selected_zodiac = str(
        zodiac if zodiac is not None else getattr(chart, "zodiac", "tropical")
        or "tropical"
    ).strip().lower()
    selected_ayanamsha = (
        ayanamsha if ayanamsha is not None else getattr(chart, "ayanamsha", None)
    )
    if selected_zodiac == "tropical":
        selected_ayanamsha = None
    elif selected_zodiac == "sidereal" and not selected_ayanamsha:
        selected_ayanamsha = LAHIRI
    return ZodiacContext(selected_zodiac, selected_ayanamsha)


def apply_transient_zodiac_context(
    chart: Any,
    context: ZodiacContext,
    *,
    uses_houses: bool = True,
) -> Any:
    """Project a transient ``Chart`` into ``context`` without persistence.

    Tropical ``Chart`` construction already supplies Tropical positions and
    house geometry, so that path only receives explicit context labels.
    Sidereal samples rebuild positions, aspects, and (when requested) Placidus
    house/angle geometry through Swiss Ephemeris' Lahiri sidereal mode.
    """

    if context.zodiac == "tropical":
        chart.zodiac = "tropical"
        chart.division = "D1"
        chart.ayanamsha = None
        chart.nakshatras = {}
        return chart

    dt = getattr(chart, "dt", None)
    lat = getattr(chart, "lat", None)
    lon = getattr(chart, "lon", None)
    if dt is None or lat is None or lon is None:
        raise ValueError("Sidereal transient projection requires datetime and coordinates.")

    positions = planetary_positions_for_zodiac(
        dt,
        float(lat),
        float(lon),
        context,
    )
    houses: tuple[float, ...] = ()
    if uses_houses:
        houses, ascendant, mc = _sidereal_houses(dt, float(lat), float(lon))
        positions.update(
            {
                "AS": ascendant,
                "MC": mc,
                "DS": (ascendant + 180.0) % 360.0,
                "IC": (mc + 180.0) % 360.0,
            }
        )

    chart.positions = positions
    chart.retrogrades = planetary_retrogrades(dt)
    chart.houses = list(houses)
    chart.housesPo = []
    chart.aspects = find_aspects(positions)
    chart.zodiac = context.zodiac
    chart.division = "D1"
    chart.ayanamsha = context.ayanamsha
    chart.nakshatras = {
        body: nakshatra_position(longitude)
        for body, longitude in positions.items()
    }

    modal_distribution = getattr(chart, "_modal_distribution", None)
    if callable(modal_distribution):
        chart.modal_distribution = modal_distribution()
    return chart
