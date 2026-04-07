"""Lightweight GUI bootstrapper.

Shows a minimal loading widget before importing the heavy `ephemeraldaddy.gui.app`
module so users get immediate visual feedback during cold starts.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.startup import StartupLoadingWidget


def main() -> None:
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
        app = QApplication(sys.argv)

    loading = StartupLoadingWidget()
    loading.show()
    loading.update_status("Loading application modules…", 15)
    # `bootstrap` already provides our preferred startup identity/window
    # behavior, so avoid app.py's macOS re-exec path (which can interrupt
    # splash progress on interpreter launches).
    os.environ.setdefault("EPHEMERALDADDY_APPNAME_REEXEC", "1")

    from ephemeraldaddy.gui import app as gui_app

    loading.update_status("Initializing main window…", 35)
    gui_app.main(startup_loading=loading)


if __name__ == "__main__":
    main()
