from __future__ import annotations

import platform
from dataclasses import dataclass

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtWidgets import QWidget

_MIN_RESTORED_WINDOW_WIDTH = 640
_MIN_RESTORED_WINDOW_HEIGHT = 420


@dataclass(frozen=True)
class WindowPlacement:
    geometry: QRect | None
    maximized: bool


def capture_window_placement(window: QWidget) -> WindowPlacement:
    state = window.windowState()
    geometry = window.normalGeometry()
    if not geometry.isValid():
        geometry = window.geometry()
    if geometry.isValid() and (
        geometry.width() < _MIN_RESTORED_WINDOW_WIDTH
        or geometry.height() < _MIN_RESTORED_WINDOW_HEIGHT
    ):
        geometry = None

    # A minimized window can report a transient icon/taskbar-sized frame on
    # Windows. Preserve whether it was logically maximized while minimized.
    maximized = bool(state & Qt.WindowMaximized)
    if not maximized:
        maximized = window.isMaximized()

    return WindowPlacement(
        geometry=geometry if geometry.isValid() else None,
        maximized=maximized,
    )


def clear_fullscreen_and_minimized(window: QWidget) -> None:
    window.setWindowState(
        (window.windowState() & ~Qt.WindowFullScreen) & ~Qt.WindowMinimized
    )


def apply_window_placement(window: QWidget, placement: WindowPlacement) -> None:
    if (
        placement.geometry is not None
        and placement.geometry.isValid()
        and placement.geometry.width() >= _MIN_RESTORED_WINDOW_WIDTH
        and placement.geometry.height() >= _MIN_RESTORED_WINDOW_HEIGHT
    ):
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
    # Use a native top-most pulse that does not mutate Qt window flags/geometry.
    def _pulse_native_topmost() -> None:
        win_id = int(window.winId())
        if win_id == 0:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            user32.SetWindowPos(win_id, HWND_TOPMOST, 0, 0, 0, 0, flags)
            user32.SetWindowPos(win_id, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
            user32.SetForegroundWindow(win_id)
        except Exception:
            pass

        window.raise_()
        window.activateWindow()

    QTimer.singleShot(0, _pulse_native_topmost)
