from ephemeraldaddy.core.sidereal import ZodiacContext
from ephemeraldaddy.gui.settings.modules.astrology import (
    load_astrology_context,
    save_astrology_context,
)


class Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, fallback=None):
        return self.values.get(key, fallback)

    def setValue(self, key, value):
        self.values[key] = value


def test_astrology_setting_defaults_to_tropical_and_round_trips_sidereal():
    settings = Settings()
    assert load_astrology_context(settings) == ZodiacContext("tropical")

    save_astrology_context(settings, ZodiacContext("sidereal", "lahiri"))
    assert load_astrology_context(settings) == ZodiacContext("sidereal", "lahiri")


def test_unknown_persisted_ayanamsha_safely_falls_back_to_lahiri():
    settings = Settings(
        {"astrology/zodiac": "sidereal", "astrology/sidereal_ayanamsha": "unknown"}
    )
    assert load_astrology_context(settings) == ZodiacContext("sidereal", "lahiri")
