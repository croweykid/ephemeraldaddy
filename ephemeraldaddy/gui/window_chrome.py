from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
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


def _show_about_from_onboarding(owner: "QWidget") -> None:
    """Show About dialog content sourced from ONBOARDING.md."""
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QPlainTextEdit, QVBoxLayout

    onboarding_path = Path(__file__).resolve().parents[2] / "ONBOARDING.md"
    title = f"About {APP_DISPLAY_NAME}"

    if not onboarding_path.exists():
        QMessageBox.information(owner, title, "ONBOARDING.md was not found.")
        return

    content = onboarding_path.read_text(encoding="utf-8").strip()
    if not content:
        content = "ONBOARDING.md is empty."

    dialog = QDialog(owner)
    dialog.setWindowTitle(title)
    dialog.resize(720, 560)

    layout = QVBoxLayout(dialog)
    intro = QLabel("Content sourced from ONBOARDING.md")
    intro.setStyleSheet("font-weight: 600;")
    layout.addWidget(intro)

    content_view = QPlainTextEdit(dialog)
    content_view.setReadOnly(True)
    content_view.setPlainText(content)
    layout.addWidget(content_view, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok, parent=dialog)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()


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
    """Attach a Database View menu bar matching the requested hierarchy."""
    from PySide6.QtWidgets import QMenuBar

    dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")

    menu_bar = QMenuBar(dialog)
    _configure_menu_bar_visibility(menu_bar)

    file_menu = menu_bar.addMenu("Database")
    import_menu = file_menu.addMenu("Import from CSV")
    _bind_menu_action(import_menu, "Import from CSV (Type 1)", dialog, "_on_import_csv_type_1")
    _bind_menu_action(import_menu, "Import from CSV (The Pattern app)", dialog, "_on_import_csv_pattern")
    _bind_menu_action(file_menu, "Export Selection to CSV", dialog, "_on_export_selected")
    _bind_menu_action(file_menu, "Backup Database", dialog, "_on_export_database")
    _bind_menu_action(file_menu, "Restore Database", dialog, "_on_import_database")
    _bind_menu_action(file_menu, "Refresh Database", dialog, "_on_force_refresh_database_analysis")
    file_menu.addSeparator()
    _bind_menu_action(file_menu, "Settings", dialog, "_on_open_settings", "on_open_settings")

    charts_menu = menu_bar.addMenu("Charts")
    _bind_menu_action(charts_menu, "New chart", dialog, "_on_new_chart", "on_new_chart")
    _bind_menu_action(charts_menu, "Edit chart", dialog, "_on_edit_chart_from_menu")
    _bind_menu_action(charts_menu, "Delete chart(s)", dialog, "_on_delete", "on_delete")
    _bind_menu_action(charts_menu, "Synastry Chart", dialog, "_on_generate_composite_chart")
    _bind_menu_action(charts_menu, "Personal Transit Chart", dialog, "_on_generate_personal_transit_for_selected_chart")
    _bind_menu_action(charts_menu, "Get Personal Transit", dialog, "_on_menu_get_personal_transit")
    _bind_menu_action(charts_menu, "Export Chart as MD/TXT", dialog, "_on_menu_export_chart")

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(tools_menu, "Retcon Engine", dialog, "_on_retcon_engine")
    _bind_menu_action(tools_menu, "Interpret Astro Age", dialog, "_on_menu_interpret_astro_age")
    _bind_menu_action(tools_menu, "Create Gemstone Chart", dialog, "_on_menu_create_gemstone_chart")

    view_menu = menu_bar.addMenu("View")
    _bind_menu_action(view_menu, "Chart Similarities", dialog, "_show_similarities_panel")
    _bind_menu_action(view_menu, "Database Analytics", dialog, "_show_database_analytics_panel")
    _bind_menu_action(view_menu, "Current Transits", dialog, "_show_current_transits_panel")
    _bind_menu_action(view_menu, "General Population Comparison", dialog, "_show_gen_pop_comparison_panel")
    _bind_menu_action(view_menu, "Manage Collections", dialog, "_show_manage_collections_panel")
    _bind_menu_action(view_menu, "Search Database", dialog, "_show_search_database_panel")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(help_menu, "Help", dialog, "_on_manage_help_overlay", "on_manage_help_overlay")
    help_menu.addAction("About", lambda: _show_about_from_onboarding(dialog))

    layout.setMenuBar(menu_bar)
