"""Settings widgets for installing and managing local plugins."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.human_design_plugins import plugin_installations, set_plugin_enabled


def _file_browser_name() -> str:
    if sys.platform == "darwin":
        return "Finder"
    if sys.platform.startswith("win"):
        return "Explorer"
    return "File Manager"


class PluginManagerPanel(QWidget):
    """Table of installed plugins with state and file-management actions."""

    def __init__(self, owner: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner = owner
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Plugin Manager")
        heading.setStyleSheet("font-weight: bold;")
        layout.addWidget(heading)
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Plugin", "Status", "File location"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.toggle_button = QPushButton("Disable", self)
        self.toggle_button.clicked.connect(self._toggle_selected)
        actions.addWidget(self.toggle_button)
        self.open_button = QPushButton(f"Open Folder in {_file_browser_name()}", self)
        self.open_button.clicked.connect(self._open_selected_folder)
        actions.addWidget(self.open_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.refresh()

    def _selected_record(self) -> dict[str, object] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        record = item.data(Qt.UserRole) if item is not None else None
        return record if isinstance(record, dict) else None

    def refresh(self) -> None:
        records = plugin_installations()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            name_item = QTableWidgetItem(str(record["name"]))
            name_item.setData(Qt.UserRole, record)
            self.table.setItem(row, 0, name_item)
            enabled = bool(record["enabled"])
            status_item = QTableWidgetItem("✓ Enabled" if enabled else "✕ Disabled")
            status_item.setForeground(QColor("#45c96b" if enabled else "#888888"))
            self.table.setItem(row, 1, status_item)
            self.table.setItem(row, 2, QTableWidgetItem(str(record["path"])))
        if records:
            self.table.selectRow(0)
        self._sync_actions()

    def _sync_actions(self) -> None:
        record = self._selected_record()
        enabled = bool(record and record["enabled"])
        self.toggle_button.setText("Disable" if enabled else "Enable")
        self.toggle_button.setEnabled(record is not None)
        self.open_button.setEnabled(record is not None)

    def _toggle_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        try:
            set_plugin_enabled(str(record["name"]), not bool(record["enabled"]))
        except OSError as exc:
            QMessageBox.warning(self, "Plugin state could not be changed", str(exc))
            return
        self.refresh()
        callback = getattr(self._owner, "_refresh_plugins_status_labels", None)
        if callable(callback):
            callback()

    def _open_selected_folder(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        folder = Path(str(record["path"])).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


def build_plugin_manager_panel(owner: Any, parent: QWidget | None = None) -> PluginManagerPanel:
    return PluginManagerPanel(owner, parent)
