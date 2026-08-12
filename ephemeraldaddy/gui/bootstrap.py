"""Lightweight GUI bootstrapper.

Shows a minimal loading widget before importing the heavy `ephemeraldaddy.gui.app`
module so users get immediate visual feedback during cold starts.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.application_identity import (
    APP_DISPLAY_NAME,
    configure_pre_qapplication_identity,
    configure_qapplication_identity,
)
from ephemeraldaddy.gui.icons import get_app_icon_path
from ephemeraldaddy.gui.startup import StartupLoadingWidget


def main() -> None:
    # Native shells determine identity when QApplication (and, on some Linux
    # desktops, its first window) is created. Configure it before the splash.
    configure_pre_qapplication_identity()

    # Must be set before creating QApplication; otherwise Qt prints a runtime warning.
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        # Best-effort guard for older Qt/PySide versions.
        pass

    app = QApplication.instance()
    if app is None:
        app = QApplication([APP_DISPLAY_NAME, *sys.argv[1:]])
    configure_qapplication_identity(app)

    icon_path = get_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    loading = StartupLoadingWidget()
    if icon_path:
        loading.setWindowIcon(QIcon(icon_path))
    loading.show()
    loading.update_status("Loading application modules…", 15)

    from ephemeraldaddy.gui import app as gui_app

    loading.update_status("Initializing main window…", 35)
    gui_app.main(startup_loading=loading)


if __name__ == "__main__":
    main()
