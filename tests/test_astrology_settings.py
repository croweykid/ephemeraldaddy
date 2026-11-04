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



def test_lilith_mode_defaults_to_osculating_and_round_trips_all_options():
    from ephemeraldaddy.core.lilith_mode import LILITH_MODES
    from ephemeraldaddy.gui.settings.modules.astrology import load_lilith_mode, save_lilith_mode

    settings = Settings()
    assert load_lilith_mode(settings) == "Osculating Lilith"
    for mode in LILITH_MODES:
        assert save_lilith_mode(settings, mode) == mode
        assert load_lilith_mode(settings) == mode
    settings.setValue("astrology/lilith_mode", "invalid")
    assert load_lilith_mode(settings) == "Osculating Lilith"


def test_implicit_lilith_settings_uses_desktop_namespace_not_qt_display_name(monkeypatch):
    """Dominance and exports must read the same setting that the dialog writes."""
    from PySide6 import QtCore
    from ephemeraldaddy.core.settings_identity import SETTINGS_APP, SETTINGS_ORG
    from ephemeraldaddy.gui.settings.modules.astrology import (
        load_lilith_mode, save_lilith_mode,
    )

    explicit_namespace = (SETTINGS_ORG, SETTINGS_APP)
    display_namespace = ("Ephemeral Daddy", "Ephemeral Daddy")
    assert explicit_namespace != display_namespace

    stored = {
        explicit_namespace: Settings(),
        display_namespace: Settings(),
    }
    save_lilith_mode(stored[explicit_namespace], "Natural Lilith")
    save_lilith_mode(stored[display_namespace], "Osculating Lilith")

    constructor_calls = []

    def make_settings(*args):
        constructor_calls.append(args)
        return stored[args]

    monkeypatch.setattr(QtCore, "QSettings", make_settings)
    assert load_lilith_mode() == "Natural Lilith"
    assert constructor_calls == [explicit_namespace]

    save_lilith_mode(stored[explicit_namespace], "Mean Lilith")
    assert load_lilith_mode() == "Mean Lilith"
    assert constructor_calls == [explicit_namespace, explicit_namespace]


def test_implicit_lilith_read_never_imports_gui_style(monkeypatch):
    """Core calculations can read Lilith preferences without QtGui/QtWidgets."""
    import builtins
    from PySide6 import QtCore
    from ephemeraldaddy.gui.settings.modules.astrology import load_lilith_mode
    from ephemeraldaddy.core.settings_identity import SETTINGS_ORG, SETTINGS_APP

    values = Settings({"astrology/lilith_mode": "Mean Lilith"})
    monkeypatch.setattr(QtCore, "QSettings", lambda *args: values)
    real_import = builtins.__import__

    def deny_gui_style(name, *args, **kwargs):
        if name == "ephemeraldaddy.gui.style":
            raise AssertionError("Settings reader imported the graphical style module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", deny_gui_style)
    assert SETTINGS_ORG == SETTINGS_APP == "EphemeralDaddy"
    assert load_lilith_mode() == "Mean Lilith"
