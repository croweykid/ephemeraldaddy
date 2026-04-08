"""Shared startup/loading UI primitives for GUI entrypoints."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import subprocess
import sys

from PySide6.QtCore import QCoreApplication, QEventLoop, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE


@runtime_checkable
class StartupProgress(Protocol):
    """Protocol used by the startup cockpit to report launch progress."""

    def show(self) -> None: ...

    def close(self) -> None: ...

    def update_status(self, message: str, progress: int) -> None: ...


class StartupLoadingWidget(QWidget):
    """Small splash-like loading surface shown while the app initializes."""

    def __init__(self) -> None:
        # Use splash-screen window semantics to avoid OS-level "tool window"
        # taskbar/alt-tab flashing during startup (especially noticeable on Windows).
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setWindowTitle("Starting EphemeralDaddy")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._animation_process: subprocess.Popen | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        self.setLayout(layout)

        title = QLabel("Ephemeral Daddy will be with you shortly…")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(title)

        self._status_label = QLabel("Bootstrapping UI modules…")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._status_label.setStyleSheet("color: #efe9ff; font-size: 12px;")
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(5)
        self._progress.setStyleSheet(
            "QProgressBar {"
            "  border: 1px solid #47345d;"
            "  border-radius: 4px;"
            "  color: #efe9ff;"
            "  background-color: #0e0b12;"
            "  text-align: center;"
            "  min-height: 14px;"
            "}"
            "QProgressBar::chunk {"
            "  background-color: #9933ff;"
            "}"
        )
        layout.addWidget(self._progress)

        self.setFixedWidth(360)
        self.adjustSize()
        self._center_on_primary_screen()
        self._start_animation_process()

    def _center_on_primary_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        screen_rect = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen_rect.center())
        self.move(frame.topLeft())

    def update_status(self, message: str, progress: int) -> None:
        self._status_label.setText(message)
        self._progress.setValue(min(max(progress, 0), 100))
        self.raise_()
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._start_animation_process()
        self.raise_()
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)

    def _start_animation_process(self) -> None:
        if self._animation_process is not None:
            return
        geometry = self.frameGeometry()
        args = [
            sys.executable,
            "-m",
            "ephemeraldaddy.gui.startup_animation_process",
            str(geometry.x()),
            str(geometry.y()),
            str(geometry.width()),
            str(geometry.height()),
        ]
        try:
            self._animation_process = subprocess.Popen(args)
        except Exception:
            self._animation_process = None

    def _stop_animation_process(self) -> None:
        if self._animation_process is None:
            return
        process = self._animation_process
        self._animation_process = None
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=0.3)
        except subprocess.TimeoutExpired:
            process.kill()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_animation_process()
        super().closeEvent(event)
