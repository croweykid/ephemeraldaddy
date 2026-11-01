"""Qt controls for Settings > Astrology mode selection."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QButtonGroup, QLabel, QRadioButton, QVBoxLayout

from ephemeraldaddy.core.lilith_mode import LILITH_MODES
from ephemeraldaddy.core.sidereal import ZodiacContext
from ephemeraldaddy.gui.settings.modules.astrology import load_lilith_mode, save_lilith_mode


def add_astrology_mode_controls(
    layout: QVBoxLayout,
    *,
    dialog: object,
    context: ZodiacContext,
    on_changed: Callable[[ZodiacContext], None],
    on_lilith_changed: Callable[[str], None],
    settings: object,
) -> dict[str, QRadioButton]:
    layout.addWidget(QLabel("Default astrology mode:"))
    tropical = QRadioButton("Tropical")
    sidereal = QRadioButton("Sidereal (Lahiri)")
    group = QButtonGroup(dialog)
    group.setExclusive(True)
    group.addButton(tropical)
    group.addButton(sidereal)
    tropical.setChecked(context.zodiac == "tropical")
    sidereal.setChecked(context.zodiac == "sidereal")
    tropical.toggled.connect(
        lambda checked: checked and on_changed(ZodiacContext("tropical"))
    )
    sidereal.toggled.connect(
        lambda checked: checked and on_changed(ZodiacContext("sidereal", "lahiri"))
    )
    layout.addWidget(tropical)
    layout.addWidget(sidereal)
    layout.addWidget(QLabel("Sidereal calculations currently use the Lahiri ayanamsha."))

    layout.addWidget(QLabel("Select Lilith Mode:"))
    selected = load_lilith_mode(settings)
    lilith_buttons = QButtonGroup(dialog)
    lilith_buttons.setExclusive(True)
    controls = {"tropical": tropical, "sidereal": sidereal}

    def select_lilith(mode: str) -> None:
        if load_lilith_mode(settings) == mode:
            return
        save_lilith_mode(settings, mode)
        # Changing the apogee must never call the zodiac-context callback.
        # The owner coordinates derived-score invalidation and live refresh.
        on_lilith_changed(mode)

    for mode in LILITH_MODES:
        button = QRadioButton(mode)
        lilith_buttons.addButton(button)
        button.setChecked(mode == selected)
        button.toggled.connect(lambda checked, selected_mode=mode: checked and select_lilith(selected_mode))
        layout.addWidget(button)
        controls[mode] = button
    return controls
