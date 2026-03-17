from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QMainWindow

APP_DISPLAY_NAME = "EphemeralDaddy"


def configure_application_identity(app: "QApplication") -> None:
    """Set a consistent application identity shown by the OS shell and Qt."""
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setOrganizationName(APP_DISPLAY_NAME)


def configure_main_window_chrome(window: "QMainWindow") -> None:
    """Attach a top-level menu bar and app title for the main window."""
    window.setWindowTitle(f"{APP_DISPLAY_NAME} | Natal Chart Viewer")

    menu_bar = window.menuBar()
    menu_bar.clear()

    file_menu = menu_bar.addMenu("File")
    file_menu.addAction("New Chart", window.on_new_chart)
    file_menu.addAction("Manage Charts", window.on_manage_charts)
    file_menu.addSeparator()
    file_menu.addAction("Exit", window.close)

    tools_menu = menu_bar.addMenu("Tools")
    tools_menu.addAction("Settings", window._on_open_settings)

    help_menu = menu_bar.addMenu("Help")
    help_menu.addAction("Help Overlay", window._on_manage_help_overlay)
