"""Analysis-safe wrappers for nakshatra metric calculations.

This module intentionally avoids importing GUI modules at import-time so
headless/runtime-minimal environments can still import analysis helpers.
"""

from __future__ import annotations

from ephemeraldaddy.core.interpretations import NATAL_WEIGHT
from ephemeraldaddy.core.sidereal import NAKSHATRA_NAMES, nakshatra_position_for_chart


def _fallback_dominant_nakshatra_weights(chart: object) -> dict[str, float]:
    nakshatra_names = list(NAKSHATRA_NAMES)
    weighted_counts = {name: 0.0 for name in nakshatra_names}
    positions = getattr(chart, "positions", None) or {}
    for body, lon in positions.items():
        if lon is None:
            continue
        nakshatra = nakshatra_position_for_chart(chart, str(body), float(lon)).name
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
