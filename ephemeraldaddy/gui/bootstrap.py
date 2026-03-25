"""Lightweight GUI bootstrapper.

Shows a minimal loading widget before importing the heavy `ephemeraldaddy.gui.app`
module so users get immediate visual feedback during cold starts.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE


def _ensure_frozen_paths() -> None:
    """Add common frozen-app library paths before importing Qt.

    Some Windows distributions place packaged modules beneath `_internal`; this
    keeps imports resilient even if the bootloader path setup is incomplete.
    """
    if not getattr(sys, "frozen", False):
        return

    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        candidates.extend([base, base / "_internal"])

    exe_dir = Path(sys.executable).resolve().parent
    candidates.extend([exe_dir, exe_dir / "_internal"])

    for candidate in candidates:
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)


def _build_bootstrap_loading_widget():
    from PySide6.QtCore import QCoreApplication, QEventLoop, Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

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

    return _BootstrapLoadingWidget

def main() -> None:
    _ensure_frozen_paths()

    from PySide6.QtWidgets import QApplication
    BootstrapLoadingWidget = _build_bootstrap_loading_widget()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    loading = BootstrapLoadingWidget()
    loading.show()
    loading.update_status("Loading application modules…", 15)

    from ephemeraldaddy.gui import app as gui_app

    loading.update_status("Initializing main window…", 35)
    gui_app.main(startup_loading=loading)


if __name__ == "__main__":
    main()
