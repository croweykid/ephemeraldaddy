from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class WindowPlacement:
    geometry: QRect | None
    maximized: bool


def _screen_for_geometry(geometry: QRect | None) -> QScreen | None:
    if geometry is not None and geometry.isValid():
        screen = QGuiApplication.screenAt(geometry.center())
        if screen is not None:
            return screen
    return QGuiApplication.primaryScreen()


def _minimum_width(window: QWidget) -> int:
    hint_width = window.minimumSizeHint().width()
    if hint_width > 0:
        return max(window.minimumWidth(), hint_width)
    return window.minimumWidth()


def _minimum_height(window: QWidget) -> int:
    hint_height = window.minimumSizeHint().height()
    if hint_height > 0:
        return max(window.minimumHeight(), hint_height)
    return window.minimumHeight()


def _clamp_geometry_to_screen(window: QWidget, geometry: QRect) -> QRect:
    screen = _screen_for_geometry(geometry)
    if screen is None:
        return geometry

    available = screen.availableGeometry()
    min_width = max(1, _minimum_width(window))
    min_height = max(1, _minimum_height(window))
    width = min(max(geometry.width(), min_width), available.width())
    height = min(max(geometry.height(), min_height), available.height())
    x = max(available.left(), min(geometry.x(), available.right() - width + 1))
    y = max(available.top(), min(geometry.y(), available.bottom() - height + 1))
    return QRect(x, y, width, height)


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
    geometry = placement.geometry if placement.geometry is not None and placement.geometry.isValid() else None
    screen = _screen_for_geometry(geometry)
    if placement.maximized:
        if geometry is not None and screen is not None:
            available = screen.availableGeometry()
            top_left = QPoint(
                max(available.left(), min(geometry.x(), available.right())),
                max(available.top(), min(geometry.y(), available.bottom())),
            )
            window.move(top_left)
        elif screen is not None:
            window.move(screen.availableGeometry().topLeft())
    elif geometry is not None:
        window.setGeometry(_clamp_geometry_to_screen(window, geometry))

    clear_fullscreen_and_minimized(window)
    if placement.maximized:
        window.showMaximized()
    else:
        window.showNormal()
