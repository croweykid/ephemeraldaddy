"""Separate-process animated startup frame shown behind the load bar."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.startup_animation import StartupAnimationFrame


class StartupAnimationWindow(StartupAnimationFrame):
    """Shared animated frame hosted in a separate process."""

    def __init__(self, *, x: int, y: int, width: int, height: int) -> None:
        super().__init__(None)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowStaysOnBottomHint, True)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setGeometry(x, y, width, height)


def main() -> int:
    if len(sys.argv) != 5:
        return 1
    try:
        x, y, width, height = (int(arg) for arg in sys.argv[1:])
    except ValueError:
        return 1
    app = QApplication([])
    window = StartupAnimationWindow(x=x, y=y, width=width, height=height)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
