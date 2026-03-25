from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QRect
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
