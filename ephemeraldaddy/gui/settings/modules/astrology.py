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


# Lilith mode is independent of zodiac/ayanamsha: it selects the apogee
# representation used in scoring and user-facing chart data, not ephemeris storage.
SETTINGS_KEY_LILITH_MODE = "astrology/lilith_mode"


def load_lilith_mode(settings: object | None = None) -> str:
    from ephemeraldaddy.core.lilith_mode import normalize_lilith_mode
    if settings is None:
        from PySide6.QtCore import QSettings
        from ephemeraldaddy.core.settings_identity import SETTINGS_APP, SETTINGS_ORG

        # The desktop application deliberately uses the compact
        # EphemeralDaddy/EphemeralDaddy namespace for persisted settings.
        # Default QSettings() follows the separate Qt display-name identity.
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return normalize_lilith_mode(settings.value(SETTINGS_KEY_LILITH_MODE, "Osculating Lilith"))


def save_lilith_mode(settings: object, mode: str) -> str:
    from ephemeraldaddy.core.lilith_mode import LILITH_MODES
    if mode not in LILITH_MODES:
        raise ValueError(f"Unsupported Lilith mode: {mode!r}")
    settings.setValue(SETTINGS_KEY_LILITH_MODE, mode)
    return mode
