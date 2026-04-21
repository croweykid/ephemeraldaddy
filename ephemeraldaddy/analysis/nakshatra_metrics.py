"""Analysis-safe wrappers for nakshatra metric calculations.

This module intentionally avoids importing GUI modules at import-time so
headless/runtime-minimal environments can still import analysis helpers.
"""

from __future__ import annotations

from ephemeraldaddy.core.interpretations import NAKSHATRA_RANGES, NATAL_WEIGHT


def _sign_degrees(sign: str, deg: int, minutes: int) -> float:
    zodiac_names = (
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    )
    sign_index = zodiac_names.index(sign)
    return (sign_index * 30.0) + deg + (minutes / 60.0)


def _get_nakshatra(lon: float) -> str:
    lon = float(lon) % 360.0
    for name, start_sign, start_deg, start_min, end_sign, end_deg, end_min in NAKSHATRA_RANGES:
        start = _sign_degrees(start_sign, start_deg, start_min)
        end = _sign_degrees(end_sign, end_deg, end_min)
        if start <= end:
            if start <= lon < end:
                return name
        else:
            if lon >= start or lon < end:
                return name
    return "Unknown"


def _fallback_dominant_nakshatra_weights(chart: object) -> dict[str, float]:
    nakshatra_names = [name for name, *_ in NAKSHATRA_RANGES]
    weighted_counts = {name: 0.0 for name in nakshatra_names}
    positions = getattr(chart, "positions", None) or {}
    for body, lon in positions.items():
        if lon is None:
            continue
        nakshatra = _get_nakshatra(float(lon))
        if nakshatra not in weighted_counts:
            continue
        weighted_counts[nakshatra] += float(NATAL_WEIGHT.get(str(body), 1.0))
    return weighted_counts


def calculate_dominant_nakshatra_weights(chart: object) -> dict[str, float]:
    """Return dominant nakshatra weights without requiring GUI imports.

    Uses the GUI metrics implementation when available; otherwise falls back to
    a lightweight, analysis-safe weighting model.
    """
    try:
        from ephemeraldaddy.gui.features.charts.metrics import (  # local import on purpose
            calculate_dominant_nakshatra_weights as _gui_calculate,
        )
    except Exception:
        return _fallback_dominant_nakshatra_weights(chart)

    return _gui_calculate(chart)

