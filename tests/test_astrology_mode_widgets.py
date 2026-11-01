"""Live Settings UI regressions for independent zodiac and Lilith controls."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from ephemeraldaddy.core.sidereal import ZodiacContext
from ephemeraldaddy.gui.settings.modules.astrology import (
    load_astrology_context, load_lilith_mode, save_astrology_context,
)
from ephemeraldaddy.gui.settings.modules.astrology_widgets import add_astrology_mode_controls


class Settings:
    def __init__(self):
        self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value


def test_changing_lilith_does_not_revert_sidereal_zodiac_in_same_dialog():
    app = QApplication.instance() or QApplication([])
    widget = QWidget()
    layout = QVBoxLayout(widget)
    settings = Settings()
    zodiac_events = []
    lilith_events = []

    def on_zodiac(context):
        zodiac_events.append(context)
        save_astrology_context(settings, context)

    controls = add_astrology_mode_controls(
        layout, dialog=widget, context=load_astrology_context(settings),
        on_changed=on_zodiac, on_lilith_changed=lilith_events.append,
        settings=settings,
    )
    try:
        controls["sidereal"].setChecked(True)
        assert load_astrology_context(settings) == ZodiacContext("sidereal", "lahiri")
        controls["Natural Lilith"].setChecked(True)
        assert load_astrology_context(settings) == ZodiacContext("sidereal", "lahiri")
        assert zodiac_events == [ZodiacContext("sidereal", "lahiri")]
        assert lilith_events == ["Natural Lilith"]
        assert load_lilith_mode(settings) == "Natural Lilith"
        controls["Mean Lilith"].setChecked(True)
        assert len(zodiac_events) == 1
        assert lilith_events == ["Natural Lilith", "Mean Lilith"]
    finally:
        widget.close()
