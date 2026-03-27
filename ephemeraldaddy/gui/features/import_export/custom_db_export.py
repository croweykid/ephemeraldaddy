"""Custom DB/CSV chart-property export dialog helpers."""

from __future__ import annotations

import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.db import (
    export_chart_properties_csv,
    export_database_with_chart_property_selection,
    list_chart_export_properties,
)


def open_custom_db_export_dialog(parent: QWidget) -> None:
    properties = list_chart_export_properties()
    if not properties:
        QMessageBox.information(
            parent,
            "No chart properties",
            "No chart properties are currently available for export.",
        )
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle("Custom DB Export")
    dialog.setMinimumSize(520, 600)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    layout.addWidget(QLabel("Export format"))
    format_row = QHBoxLayout()
    db_radio = QRadioButton("Database (.db)")
    csv_radio = QRadioButton("CSV (.csv)")
    db_radio.setChecked(True)
    format_row.addWidget(db_radio)
    format_row.addWidget(csv_radio)
    format_row.addStretch(1)
    layout.addLayout(format_row)

    helper_label = QLabel(
        "Select which chart properties to include.\n"
        "For DB exports, locked fields (🔒) are required by the app."
    )
    helper_label.setWordWrap(True)
    layout.addWidget(helper_label)

    properties_scroll = QScrollArea(dialog)
    properties_scroll.setWidgetResizable(True)
    properties_widget = QWidget()
    properties_layout = QVBoxLayout(properties_widget)
    properties_layout.setContentsMargins(6, 6, 6, 6)
    properties_layout.setSpacing(6)
    properties_scroll.setWidget(properties_widget)
    layout.addWidget(properties_scroll)

    checkboxes: dict[str, QCheckBox] = {}
    for prop in properties:
        column = str(prop.get("column", "")).strip()
        if not column:
            continue
        label_text = str(prop.get("label", column))
        checkbox = QCheckBox(label_text)
        checkbox.setChecked(True)
        checkboxes[column] = checkbox
        properties_layout.addWidget(checkbox)
    properties_layout.addStretch(1)

    button_row = QHBoxLayout()
    select_all_button = QPushButton("Select all")
    select_minimum_button = QPushButton("Select minimum")
    button_row.addWidget(select_all_button)
    button_row.addWidget(select_minimum_button)
    button_row.addStretch(1)
    cancel_button = QPushButton("Cancel")
    export_button = QPushButton("Export")
    button_row.addWidget(cancel_button)
    button_row.addWidget(export_button)
    layout.addLayout(button_row)

    def _refresh_lock_state() -> None:
        db_mode = db_radio.isChecked()
        helper_label.setText(
            "Select which chart properties to include.\n"
            "For DB exports, locked fields (🔒) are required by the app."
            if db_mode
            else "Select any properties to include in CSV export."
        )
        for prop in properties:
            column = str(prop.get("column", "")).strip()
            checkbox = checkboxes.get(column)
            if checkbox is None:
                continue
            locked_for_db = bool(prop.get("locked_for_db"))
            display_label = str(prop.get("label", column))
            if locked_for_db and db_mode:
                checkbox.setText(f"🔒 {display_label}")
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
            else:
                checkbox.setText(display_label)
                checkbox.setEnabled(True)

    def _select_all_properties() -> None:
        for checkbox in checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def _select_minimum_properties() -> None:
        for prop in properties:
            column = str(prop.get("column", "")).strip()
            checkbox = checkboxes.get(column)
            if checkbox is None:
                continue
            checkbox.setChecked(bool(prop.get("locked_for_db")))

    def _run_custom_export() -> None:
        selected_columns = [
            column for column, checkbox in checkboxes.items() if checkbox.isChecked()
        ]
        if not selected_columns:
            QMessageBox.warning(
                dialog,
                "No properties selected",
                "Select at least one property to export.",
            )
            return

        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        if db_radio.isChecked():
            file_path, _ = QFileDialog.getSaveFileName(
                dialog,
                "Export custom database",
                f"ephemeraldaddy_db_custom_export_{timestamp}.db",
                "Database Files (*.db)",
            )
            if not file_path:
                return
            if not file_path.lower().endswith(".db"):
                file_path = f"{file_path}.db"
            try:
                export_database_with_chart_property_selection(
                    Path(file_path),
                    selected_columns,
                )
            except Exception as exc:
                QMessageBox.critical(
                    dialog,
                    "Custom export failed",
                    f"Could not export custom database:\n{exc}",
                )
                return
            QMessageBox.information(
                dialog,
                "Export complete",
                f"Custom database export saved to:\n{file_path}",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Export custom CSV",
            f"ephemeraldaddy_db_custom_export_{timestamp}.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"
        try:
            export_chart_properties_csv(Path(file_path), selected_columns)
        except Exception as exc:
            QMessageBox.critical(
                dialog,
                "Custom export failed",
                f"Could not export custom CSV:\n{exc}",
            )
            return
        QMessageBox.information(
            dialog,
            "Export complete",
            f"Custom CSV export saved to:\n{file_path}",
        )

    db_radio.toggled.connect(_refresh_lock_state)
    select_all_button.clicked.connect(_select_all_properties)
    select_minimum_button.clicked.connect(_select_minimum_properties)
    cancel_button.clicked.connect(dialog.reject)
    export_button.clicked.connect(_run_custom_export)
    _refresh_lock_state()
    dialog.exec()
