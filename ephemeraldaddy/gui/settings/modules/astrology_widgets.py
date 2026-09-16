"""Qt controls for Settings > Astrology mode selection."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QButtonGroup, QLabel, QRadioButton, QVBoxLayout

from ephemeraldaddy.core.sidereal import ZodiacContext


def add_astrology_mode_controls(
    layout: QVBoxLayout,
    *,
    dialog: object,
    context: ZodiacContext,
    on_changed: Callable[[ZodiacContext], None],
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
    return {"tropical": tropical, "sidereal": sidereal}
