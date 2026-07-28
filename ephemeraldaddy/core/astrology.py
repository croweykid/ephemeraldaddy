"""Small, dependency-light primitives shared by astrology calculations."""

from __future__ import annotations

from ephemeraldaddy.core.interpretations import ZODIAC_NAMES


def sign_for_longitude(longitude: float) -> str:
    """Return the tropical zodiac sign for any longitude in degrees."""
    sign_index = int((float(longitude) % 360.0) // 30.0) % 12
    return ZODIAC_NAMES[sign_index]
