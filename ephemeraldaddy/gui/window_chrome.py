from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ephemeraldaddy.gui.style import (
    ABOUT_DIALOG_INTRO_STYLE,
    ABOUT_DIALOG_MARKDOWN_STYLESHEET,
    WINDOW_CHROME_MENU_STYLE,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QLayout, QMainWindow, QWidget

APP_DISPLAY_NAME = "Ephemeral Daddy"


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
    """Prefer native menu positioning; allow opt-in in-window menu bars on macOS."""
    if (
        sys.platform == "darwin"
        and not getattr(sys, "frozen", False)
        and os.environ.get("EPHEMERALDADDY_FORCE_IN_WINDOW_MENUBAR") == "1"
    ):
        menu_bar.setNativeMenuBar(False)


def _show_about_from_onboarding(owner: "QWidget") -> None:
    """Show About dialog content sourced from ONBOARDING.md."""
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QTextBrowser, QVBoxLayout

    onboarding_path = Path(__file__).resolve().parents[2] / "ONBOARDING.md"
    title = f"About {APP_DISPLAY_NAME}"

    if not onboarding_path.exists():
        QMessageBox.information(owner, title, "ONBOARDING.md was not found.")
        return

    content = onboarding_path.read_text(encoding="utf-8").strip()
    if not content:
        content = "ONBOARDING.md is empty."

    styled_content_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.lstrip()
        prefix_whitespace = line[: len(line) - len(stripped)]
        if stripped.startswith("Q."):
            styled_content_lines.append(
                f"{prefix_whitespace}<span class='about-question'>{stripped}</span>"
            )
        elif stripped.startswith("A."):
            styled_content_lines.append(
                f"{prefix_whitespace}<span class='about-answer'>{stripped}</span>"
            )
        else:
            styled_content_lines.append(line)
    styled_content = "\n".join(styled_content_lines)

    dialog = QDialog(owner)
    dialog.setWindowTitle(title)
    dialog.resize(720, 560)

    layout = QVBoxLayout(dialog)
    intro = QLabel("Content sourced from ONBOARDING.md")
    intro.setStyleSheet(ABOUT_DIALOG_INTRO_STYLE)
    layout.addWidget(intro)

    content_view = QTextBrowser(dialog)
    content_view.setOpenExternalLinks(True)
    content_view.document().setDefaultStyleSheet(ABOUT_DIALOG_MARKDOWN_STYLESHEET)
    content_view.setMarkdown(styled_content)
    layout.addWidget(content_view, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok, parent=dialog)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()

def _minimize_window(owner: "QWidget") -> None:
    """Minimize the provided top-level window to the taskbar/dock."""
    if hasattr(owner, "showMinimized"):
        owner.showMinimized()


def _quit_application() -> None:
    """Request a full application shutdown via QApplication."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        app.quit()


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
    menu_bar.setStyleSheet(WINDOW_CHROME_MENU_STYLE)
    menu_bar.clear()

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _bind_menu_action(app_menu, "Settings", window, "_on_open_settings", "on_open_settings")
    app_menu.addAction("About", lambda: _show_about_from_onboarding(window))
    app_menu.addAction("Minimize", lambda: _minimize_window(window))
    app_menu.addSeparator()
    app_menu.addAction(f"Exit", _quit_application)

    chart_menu = menu_bar.addMenu("Chart")
    _bind_menu_action(chart_menu, "New Chart", window, "on_new_chart")
    _bind_menu_action(chart_menu, "Export Chart", window, "on_export_chart")

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(tools_menu, "Get Personal Transit", window, "on_get_current_transits")
    _bind_menu_action(tools_menu, "Create Gemstone Chart", window, "on_create_gemstone_chartwheel")
    _bind_menu_action(tools_menu, "Interpret Astro Age", window, "on_interpret_astro_age")
    _bind_menu_action(tools_menu, "Calculate BaZi", window, "on_open_bazi_window")
    _bind_menu_action(tools_menu, "Get Human Design Chart", dialog, "_on_menu_get_human_design_info")

    # view_menu = menu_bar.addMenu("View")
    # _bind_menu_action(view_menu, "Chart Analytics", window, "on_show_chart_analytics_panel")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(help_menu, "Help", window, "_on_manage_help_overlay", "on_manage_help_overlay")


def configure_manage_dialog_chrome(dialog: "QWidget", layout: "QLayout") -> None:
    """Attach a Database View menu bar matching the requested hierarchy."""
    from PySide6.QtWidgets import QMenuBar

    dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")

    menu_bar = QMenuBar(dialog)
    _configure_menu_bar_visibility(menu_bar)
    menu_bar.setStyleSheet(WINDOW_CHROME_MENU_STYLE)

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _bind_menu_action(app_menu, "Settings", dialog, "_on_open_settings", "on_open_settings")
    app_menu.addAction("Minimize", lambda: _minimize_window(dialog))
    app_menu.addSeparator()
    app_menu.addAction(f"Exit", _quit_application)

    file_menu = menu_bar.addMenu("Database")
    import_menu = file_menu.addMenu("Import from CSV")
    _bind_menu_action(import_menu, "Import from CSV (Type 1)", dialog, "_on_import_csv_type_1")
    _bind_menu_action(import_menu, "Import from CSV (The Pattern app)", dialog, "_on_import_csv_pattern")
    _bind_menu_action(file_menu, "Export Selection to CSV", dialog, "_on_export_selected")
    _bind_menu_action(file_menu, "Backup Database", dialog, "_on_export_database")
    _bind_menu_action(file_menu, "Restore Database", dialog, "_on_import_database")
    _bind_menu_action(file_menu, "Refresh Database", dialog, "_on_force_refresh_database_analysis")
    _bind_menu_action(file_menu, "Batch Edit Entries", dialog, "_toggle_edit_panel")
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
    _bind_menu_action(tools_menu, "Open BaZi Window", dialog, "_on_menu_open_bazi_window")
    _bind_menu_action(tools_menu, "Create Gemstone Chart", dialog, "_on_menu_create_gemstone_chart")
    _bind_menu_action(tools_menu, "Get Human Design Chart", window, "on_get_human_design_info")

    view_menu = menu_bar.addMenu("View")
    _bind_menu_action(view_menu, "Chart Similarities", dialog, "_show_similarities_panel")
    _bind_menu_action(view_menu, "Database Analytics", dialog, "_show_database_analytics_panel")
    _bind_menu_action(view_menu, "Current Transits", dialog, "_show_current_transits_panel")
    _bind_menu_action(view_menu, "General Population Comparison", dialog, "_show_gen_pop_comparison_panel")
    _bind_menu_action(view_menu, "Manage Collections", dialog, "_show_manage_collections_panel")
    _bind_menu_action(view_menu, "Search Database", dialog, "_show_search_database_panel")
    _bind_menu_action(view_menu, "Database Manager", dialog, "_toggle_edit_panel")

    help_menu = menu_bar.addMenu("Help")
    _bind_menu_action(help_menu, "Help", dialog, "_on_manage_help_overlay", "on_manage_help_overlay")
    help_menu.addAction("About", lambda: _show_about_from_onboarding(dialog))

    layout.setMenuBar(menu_bar)
