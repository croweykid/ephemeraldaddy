"""Persistent global astrology-mode preferences without Qt widget ownership."""

from __future__ import annotations

from ephemeraldaddy.core.sidereal import LAHIRI, ZodiacContext


SETTINGS_KEY_ZODIAC = "astrology/zodiac"
SETTINGS_KEY_SIDEREAL_AYANAMSHA = "astrology/sidereal_ayanamsha"


def load_astrology_context(settings: object) -> ZodiacContext:
    zodiac = str(settings.value(SETTINGS_KEY_ZODIAC, "tropical")).strip().lower()
    if zodiac != "sidereal":
        return ZodiacContext("tropical")
    ayanamsha = str(
        settings.value(SETTINGS_KEY_SIDEREAL_AYANAMSHA, LAHIRI)
    ).strip().lower()
    try:
        return ZodiacContext("sidereal", ayanamsha)
    except ValueError:
        return ZodiacContext("sidereal", LAHIRI)


def save_astrology_context(settings: object, context: ZodiacContext) -> None:
    settings.setValue(SETTINGS_KEY_ZODIAC, context.zodiac)
    if context.zodiac == "sidereal":
        settings.setValue(SETTINGS_KEY_SIDEREAL_AYANAMSHA, context.ayanamsha)
