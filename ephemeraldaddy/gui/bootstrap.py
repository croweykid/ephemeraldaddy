"""Lightweight GUI bootstrapper.

Shows a minimal loading widget before importing the heavy `ephemeraldaddy.gui.app`
module so users get immediate visual feedback during cold starts.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QEventLoop, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget
from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE


class _BootstrapLoadingWidget(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowTitle("Starting EphemeralDaddy")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet(
            "QWidget { background-color: #141218; color: #efe9ff; }"
            "QLabel { color: #efe9ff; font-size: 12px; }"
            "QProgressBar {"
            "  border: 1px solid #47345d;"
            "  border-radius: 4px;"
            "  background-color: #0e0b12;"
            "  text-align: center;"
            "  min-height: 14px;"
            "}"
            "QProgressBar::chunk {"
            "  background-color: #9933ff;"
            "}"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        self.setLayout(layout)

        title = QLabel("Ephemeral Daddy will be with you shortly…")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(title)

        self._status_label = QLabel("Bootstrapping UI modules…")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(5)
        layout.addWidget(self._progress)

        self.setFixedWidth(360)
        self.adjustSize()
        self._center_on_primary_screen()

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
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)


def main() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    loading = _BootstrapLoadingWidget()
    loading.show()
    loading.update_status("Loading application modules…", 15)

    from ephemeraldaddy.gui import app as gui_app

    loading.update_status("Initializing main window…", 35)
    gui_app.main(startup_loading=loading)


if __name__ == "__main__":
    main()
