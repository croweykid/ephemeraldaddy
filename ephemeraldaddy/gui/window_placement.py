from __future__ import annotations

import platform
from dataclasses import dataclass

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class WindowPlacement:
    geometry: QRect | None
    maximized: bool


def capture_window_placement(window: QWidget) -> WindowPlacement:
    geometry = window.normalGeometry()
    if not geometry.isValid():
        geometry = window.geometry()
    return WindowPlacement(
        geometry=geometry if geometry.isValid() else None,
        maximized=window.isMaximized(),
    )


def clear_fullscreen_and_minimized(window: QWidget) -> None:
    window.setWindowState(
        (window.windowState() & ~Qt.WindowFullScreen) & ~Qt.WindowMinimized
    )


def apply_window_placement(window: QWidget, placement: WindowPlacement) -> None:
    if placement.geometry is not None and placement.geometry.isValid():
        window.setGeometry(placement.geometry)
    clear_fullscreen_and_minimized(window)
    if placement.maximized:
        window.showMaximized()
    else:
        window.showNormal()


def bring_window_to_front(window: QWidget, *, use_topmost_pulse: bool = True) -> None:
    """Best-effort foreground activation across platforms."""
    window.raise_()
    window.activateWindow()

    if platform.system() != "Windows" or not use_topmost_pulse:
        return

    # Windows focus-stealing prevention can ignore activateWindow() on startup.
    # Pulse top-most briefly so the first app window reliably appears in front.
    was_visible = window.isVisible()
    window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    if was_visible:
        window.show()
    window.raise_()
    window.activateWindow()

    def _clear_topmost() -> None:
        window.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        if was_visible:
            window.show()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(0, _clear_topmost)
