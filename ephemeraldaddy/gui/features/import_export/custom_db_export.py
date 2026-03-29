"""Custom DB/CSV chart-property export dialog helpers."""

from __future__ import annotations

import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
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
    list_charts,
)
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_OPTIONS,
    chart_belongs_to_collection,
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

    divider = QFrame(dialog)
    divider.setFrameShape(QFrame.HLine)
    divider.setFrameShadow(QFrame.Sunken)
    layout.addWidget(divider)

    layout.addWidget(QLabel("Collections to include"))
    collections_helper_label = QLabel(
        "Select either All, or one or more specific collections."
    )
    collections_helper_label.setWordWrap(True)
    layout.addWidget(collections_helper_label)

    collections_widget = QWidget(dialog)
    collections_layout = QVBoxLayout(collections_widget)
    collections_layout.setContentsMargins(0, 0, 0, 0)
    collections_layout.setSpacing(4)
    collection_checkboxes: dict[str, QCheckBox] = {}

    for collection_label, collection_id in DEFAULT_COLLECTION_OPTIONS:
        checkbox = QCheckBox(collection_label)
        checkbox.setChecked(collection_id == DEFAULT_COLLECTION_ALL)
        collection_checkboxes[collection_id] = checkbox
        collections_layout.addWidget(checkbox)

    custom_collections = getattr(parent, "_custom_collections", {}) or {}
    for custom_collection in sorted(
        custom_collections.values(),
        key=lambda collection: collection.name.casefold(),
    ):
        checkbox = QCheckBox(custom_collection.name)
        checkbox.setChecked(False)
        collection_checkboxes[custom_collection.collection_id] = checkbox
        collections_layout.addWidget(checkbox)
    layout.addWidget(collections_widget)

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

    _collection_toggle_guard = False

    def _selected_collection_ids() -> list[str]:
        selected_ids = [
            collection_id
            for collection_id, checkbox in collection_checkboxes.items()
            if checkbox.isChecked()
        ]
        if not selected_ids:
            return [DEFAULT_COLLECTION_ALL]
        return selected_ids

    def _selected_chart_ids() -> list[int]:
        selected_ids = _selected_collection_ids()
        if DEFAULT_COLLECTION_ALL in selected_ids:
            return []
        rows = list_charts()
        selected_chart_ids: set[int] = set()
        for row in rows:
            chart_id = int(row[0])
            source = row[14] if len(row) > 14 else None
            for collection_id in selected_ids:
                if chart_belongs_to_collection(
                    collection_id,
                    chart=None,
                    source=source,
                    custom_collections=custom_collections,
                    chart_id=chart_id,
                ):
                    selected_chart_ids.add(chart_id)
                    break
        return sorted(selected_chart_ids)

    def _on_collection_checkbox_toggled(toggled_collection_id: str, checked: bool) -> None:
        nonlocal _collection_toggle_guard
        if _collection_toggle_guard:
            return
        _collection_toggle_guard = True
        try:
            all_checkbox = collection_checkboxes.get(DEFAULT_COLLECTION_ALL)
            if all_checkbox is None:
                return
            if toggled_collection_id == DEFAULT_COLLECTION_ALL and checked:
                for collection_id, checkbox in collection_checkboxes.items():
                    if collection_id != DEFAULT_COLLECTION_ALL:
                        checkbox.setChecked(False)
            elif toggled_collection_id != DEFAULT_COLLECTION_ALL and checked:
                all_checkbox.setChecked(False)
            selected_ids = _selected_collection_ids()
            if not selected_ids:
                all_checkbox.setChecked(True)
        finally:
            _collection_toggle_guard = False

    for collection_id, checkbox in collection_checkboxes.items():
        checkbox.toggled.connect(
            lambda checked, cid=collection_id: _on_collection_checkbox_toggled(cid, checked)
        )

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
        selected_chart_ids = _selected_chart_ids()
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
                    included_chart_ids=selected_chart_ids,
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
            export_chart_properties_csv(
                Path(file_path),
                selected_columns,
                included_chart_ids=selected_chart_ids,
            )
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
