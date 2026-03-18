from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QLayout, QMainWindow, QWidget

APP_DISPLAY_NAME = "EphemeralDaddy"


def _bind_menu_action(menu, label: str, window: "QWidget", *handler_names: str) -> None:
    """Attach a menu action to the first available window handler.

    This keeps startup resilient across builds where a handler may have moved
    or been renamed.
    """

    handler: Callable[..., Any] | None = None
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


def _configure_menu_bar_visibility(menu_bar) -> None:
    """Force a visible in-window menu bar on macOS interpreter launches."""
    if sys.platform == "darwin":
        menu_bar.setNativeMenuBar(False)


def configure_application_identity(app: "QApplication") -> None:
    """Set a consistent application identity shown by the OS shell and Qt."""
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setOrganizationName(APP_DISPLAY_NAME)


def configure_main_window_chrome(window: "QMainWindow") -> None:
    """Attach a top-level menu bar and app title for the main window."""
    window.setWindowTitle(f"{APP_DISPLAY_NAME} | Natal Chart Viewer")

    menu_bar = window.menuBar()
    _configure_menu_bar_visibility(menu_bar)
    menu_bar.clear()

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _bind_menu_action(app_menu, "Settings", window, "_on_open_settings", "on_open_settings")
    _bind_menu_action(app_menu, "Help", window, "_on_manage_help_overlay", "on_manage_help_overlay")
    app_menu.addSeparator()
    app_menu.addAction("Exit", window.close)

    file_menu = menu_bar.addMenu("File")
    _bind_menu_action(file_menu, "New Chart", window, "on_new_chart")
    _bind_menu_action(file_menu, "Manage Charts", window, "on_manage_charts")
    file_menu.addSeparator()
    file_menu.addAction("Exit", window.close)

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(tools_menu, "Settings", window, "_on_open_settings", "on_open_settings")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(help_menu, "Help Overlay", window, "_on_manage_help_overlay", "on_manage_help_overlay")


def configure_manage_dialog_chrome(dialog: "QWidget", layout: "QLayout") -> None:
    """Attach a menu bar for the Database View (Manage Charts dialog)."""
    from PySide6.QtWidgets import QMenuBar

    dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")

    menu_bar = QMenuBar(dialog)
    _configure_menu_bar_visibility(menu_bar)

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _bind_menu_action(app_menu, "Settings", dialog, "_on_open_settings", "on_open_settings")
    _bind_menu_action(app_menu, "Help", dialog, "_on_manage_help_overlay", "on_manage_help_overlay")
    app_menu.addSeparator()
    app_menu.addAction("Close", dialog.close)

    file_menu = menu_bar.addMenu("File")
    _bind_menu_action(file_menu, "New Chart", dialog, "_on_new_chart", "on_new_chart")
    _bind_menu_action(file_menu, "Delete Selected", dialog, "_on_delete", "on_delete")
    file_menu.addSeparator()
    _bind_menu_action(file_menu, "Export Selected to CSV", dialog, "_on_export_selected")

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(tools_menu, "Retcon Engine", dialog, "_on_retcon_engine")
    _bind_menu_action(tools_menu, "Synastry", dialog, "_on_generate_composite_chart")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(help_menu, "Help Overlay", dialog, "_on_manage_help_overlay", "on_manage_help_overlay")

    layout.setMenuBar(menu_bar)
