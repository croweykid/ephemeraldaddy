from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QMainWindow

APP_DISPLAY_NAME = "EphemeralDaddy"


def _bind_menu_action(menu, label: str, window: "QMainWindow", *handler_names: str) -> None:
    """Attach a menu action to the first available window handler.

    This keeps startup resilient across builds where a handler may have moved
    or been renamed.
    """

    handler: Callable | None = None
    for name in handler_names:
        candidate = getattr(window, name, None)
        if callable(candidate):
            handler = candidate
            break

    if handler is None:
        action = menu.addAction(label)
        action.setEnabled(False)
        return

    menu.addAction(label, handler)


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
    _bind_menu_action(file_menu, "New Chart", window, "on_new_chart")
    _bind_menu_action(file_menu, "Manage Charts", window, "on_manage_charts")
    file_menu.addSeparator()
    file_menu.addAction("Exit", window.close)

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(tools_menu, "Settings", window, "_on_open_settings", "on_open_settings")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(
        help_menu,
        "Help Overlay",
        window,
        "_on_manage_help_overlay",
        "on_manage_help_overlay",
    )
