# ephemeraldaddy/core/aspects.py

from __future__ import annotations
from typing import Dict, List


# angle (deg) and max orb (deg) for each aspect
ASPECT_DEFS = {
    "conjunction": {"angle": 0, "orb": 8},
    "semisextile": {"angle": 30, "orb": 2},
    "semisquare": {"angle": 45, "orb": 2},
    "sextile":     {"angle": 60, "orb": 6},
    "quintile":    {"angle": 72, "orb": 2},
    "square":      {"angle": 90, "orb": 7},
    "trine":       {"angle": 120, "orb": 8},
    "sesquiquadrate": {"angle": 135, "orb": 2},
    "biquintile":  {"angle": 144, "orb": 2},
    "quincunx": {"angle": 150, "orb": 3},
    "opposition":  {"angle": 180, "orb": 8},
}


def _angular_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two longitudes in degrees."""
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def find_aspects(positions: Dict[str, float]) -> List[dict]:
    """
    Given a dict {body: ecliptic_longitude_deg}, return a list of aspects.
    Each aspect = {
        "p1": "Mars",
        "p2": "Venus",
        "type": "trine",
        "angle": 119.8,   # actual separation
        "delta": -0.2,    # angle - exact_angle (negative = applying)
    }
    """
    bodies = list(positions.items())
    aspects: List[dict] = []

    for i in range(len(bodies)):
        name1, lon1 = bodies[i]
        for j in range(i + 1, len(bodies)):
            name2, lon2 = bodies[j]
            sep = _angular_diff(lon1, lon2)

            for asp_type, cfg in ASPECT_DEFS.items():
                target = cfg["angle"]
                orb = cfg["orb"]
                if abs(sep - target) <= orb:
                    aspects.append(
                        {
                            "p1": name1,
                            "p2": name2,
                            "type": asp_type,
                            "angle": sep,
                            "delta": sep - target,
                        }
                    )
                    break

    return aspects
