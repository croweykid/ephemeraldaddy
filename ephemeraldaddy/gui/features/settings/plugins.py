"""Settings panels for installing and managing local plugins."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ephemeraldaddy.analysis.human_design_plugins import (
    install_plugin_file,
    plugin_installation_rows,
    recognized_plugin_names,
    set_plugin_enabled,
)


def add_plugins_settings_panels(owner: Any, section_layout: QVBoxLayout) -> None:
    """Build separate upload and installed-plugin manager panels."""
    upload_panel = QGroupBox("Upload Panel")
    upload_layout = QVBoxLayout(upload_panel)
    upload_layout.addWidget(
        owner._build_settings_help_label(
            "Install recognized local supplements. Installed plugins remain local and extend "
            "app-native descriptions when enabled."
        )
    )
    owner._plugins_upload_button = QPushButton("Upload Plugin File…")
    owner._plugins_upload_button.clicked.connect(lambda _checked=False: on_plugin_upload_clicked(owner))
    upload_layout.addWidget(owner._plugins_upload_button, alignment=Qt.AlignLeft)
    section_layout.addWidget(upload_panel)

    manager_panel = QGroupBox("Plugin Manager")
    manager_layout = QVBoxLayout(manager_panel)
    manager_layout.addWidget(QLabel("Currently installed:"))
    owner._plugins_table = QTableWidget(0, 5)
    owner._plugins_table.setHorizontalHeaderLabels(
        ["Plugin Name", "Status", "File Location", "Enable / Disable", "Install Folder"]
    )
    owner._plugins_table.setEditTriggers(QTableWidget.NoEditTriggers)
    owner._plugins_table.setSelectionBehavior(QTableWidget.SelectRows)
    owner._plugins_table.verticalHeader().setVisible(False)
    header = owner._plugins_table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setSectionResizeMode(0, header.ResizeToContents)
    header.setSectionResizeMode(1, header.ResizeToContents)
    header.setSectionResizeMode(2, header.Stretch)
    header.setSectionResizeMode(3, header.ResizeToContents)
    manager_layout.addWidget(owner._plugins_table)
    owner._plugins_empty_label = QLabel("No plugins are currently installed.")
    owner._plugins_empty_label.setStyleSheet("color: #9a9a9a; font-style: italic;")
    manager_layout.addWidget(owner._plugins_empty_label)
    section_layout.addWidget(manager_panel, 1)
    refresh_plugins_table(owner)


def _folder_button_text() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Open Folder in Finder"
    if system == "Windows":
        return "Open Folder in Explorer"
    return "Open Folder in File Manager"


def refresh_plugins_table(owner: Any) -> None:
    table = getattr(owner, "_plugins_table", None)
    if not isinstance(table, QTableWidget):
        return
    rows = plugin_installation_rows()
    table.setRowCount(len(rows))
    for row_index, record in enumerate(rows):
        name = str(record["name"])
        enabled = bool(record["enabled"])
        path = Path(record["path"])
        table.setItem(row_index, 0, QTableWidgetItem(name))
        status_item = QTableWidgetItem("✓ Enabled" if enabled else "✕ Disabled")
        status_item.setForeground(Qt.green if enabled else Qt.gray)
        table.setItem(row_index, 1, status_item)
        table.setItem(row_index, 2, QTableWidgetItem(str(path)))
        toggle_button = QPushButton("Disable" if enabled else "Enable")
        toggle_button.clicked.connect(
            lambda _checked=False, plugin_name=name, new_state=not enabled: toggle_plugin(
                owner, plugin_name, new_state
            )
        )
        table.setCellWidget(row_index, 3, toggle_button)
        folder_button = QPushButton(_folder_button_text())
        folder_button.clicked.connect(
            lambda _checked=False, plugin_path=path: open_plugin_folder(owner, plugin_path)
        )
        table.setCellWidget(row_index, 4, folder_button)
    table.setVisible(bool(rows))
    empty_label = getattr(owner, "_plugins_empty_label", None)
    if isinstance(empty_label, QLabel):
        empty_label.setVisible(not rows)
    recognized = recognized_plugin_names()
    installed_names = {str(row["name"]) for row in rows}
    available = [name for name in recognized if name not in installed_names]
    footer_writer = getattr(owner, "_set_settings_section_footer_note", None)
    if callable(footer_writer):
        footer_writer(
            "Plugins",
            "Plugins available to upload: " + (", ".join(available) if available else "none"),
        )


def toggle_plugin(owner: Any, name: str, enabled: bool) -> None:
    try:
        set_plugin_enabled(name, enabled)
    except OSError as exc:
        QMessageBox.warning(owner, "Plugin update failed", f"Plugin state could not be changed: {exc}")
        return
    refresh_plugins_table(owner)


def open_plugin_folder(owner: Any, plugin_path: Path) -> None:
    folder = plugin_path.parent
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
        QMessageBox.warning(owner, "Folder unavailable", f"Could not open the plugin folder:\n{folder}")


def on_plugin_upload_clicked(owner: Any) -> None:
    file_path, _selected_filter = QFileDialog.getOpenFileName(
        owner, "Upload Plugin File", "", "JSON files (*.json);;All files (*)"
    )
    if not file_path:
        return
    recognized = recognized_plugin_names()
    if Path(file_path).name not in recognized:
        QMessageBox.information(
            owner,
            "Plugin not recognized",
            "Plugin not recognized. Currently recognized plugins: " + ", ".join(recognized),
        )
        return
    try:
        install_plugin_file(file_path)
    except (OSError, ValueError) as exc:
        QMessageBox.warning(owner, "Plugin install failed", f"Plugin could not be installed: {exc}")
        return
    refresh_plugins_table(owner)
    QMessageBox.information(
        owner,
        "Plugin installed",
        "Plugin installed and enabled. Advanced descriptions will now appear in Chart Info! when clicked.",
    )
