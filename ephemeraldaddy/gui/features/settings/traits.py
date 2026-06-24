"""Settings panel UI for managing locally uploaded custom traits."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)

from ephemeraldaddy.analysis.traits import delete_trait, install_trait_file, list_traits, rename_trait


def add_traits_settings_section(owner: Any, content_layout: Any) -> None:
    """Add the Settings > Traits manager section to the settings dialog."""
    traits_section = owner._add_settings_collapsible_section(content_layout, "Traits")
    traits_section.addWidget(
        owner._build_settings_help_label(
            "Manage custom trait profiles exported from Similarities Analysis. Uploaded traits are saved locally in ~/.ephemeraldaddy/traits and scored in Chart View > Predictions."
        )
    )
    owner._traits_list_widget = QListWidget()
    owner._traits_list_widget.setMinimumHeight(130)
    owner._traits_list_widget.setMaximumHeight(190)
    owner._traits_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
    traits_section.addWidget(owner._traits_list_widget)

    traits_button_row = QHBoxLayout()
    owner._traits_delete_button = QPushButton("Delete selected")
    owner._traits_delete_button.clicked.connect(lambda _checked=False: on_trait_delete_clicked(owner))
    traits_button_row.addWidget(owner._traits_delete_button)

    owner._traits_rename_button = QPushButton("Rename selected")
    owner._traits_rename_button.clicked.connect(lambda _checked=False: on_trait_rename_clicked(owner))
    traits_button_row.addWidget(owner._traits_rename_button)

    owner._traits_upload_button = QPushButton("Upload New Trait…")
    owner._traits_upload_button.clicked.connect(lambda _checked=False: on_trait_upload_clicked(owner))
    traits_button_row.addWidget(owner._traits_upload_button)
    traits_button_row.addStretch(1)
    traits_section.addLayout(traits_button_row)

    owner._traits_status_label = QLabel("")
    owner._traits_status_label.setWordWrap(True)
    owner._traits_status_label.setStyleSheet("color: #9a9a9a; font-style: italic; font-size: 7pt;")
    traits_section.addWidget(owner._traits_status_label)
    refresh_traits_settings_list(owner)


def selected_trait_item(owner: Any) -> QListWidgetItem | None:
    list_widget = getattr(owner, "_traits_list_widget", None)
    if not isinstance(list_widget, QListWidget):
        return None
    selected = list_widget.selectedItems()
    return selected[0] if selected else None


def refresh_traits_settings_list(owner: Any) -> None:
    list_widget = getattr(owner, "_traits_list_widget", None)
    if isinstance(list_widget, QListWidget):
        current_path = None
        selected = selected_trait_item(owner)
        if selected is not None:
            current_path = selected.data(Qt.UserRole)
        list_widget.clear()
        for trait in list_traits():
            item = QListWidgetItem(str(trait["name"]))
            item.setData(Qt.UserRole, str(trait["path"]))
            list_widget.addItem(item)
            if str(trait["path"]) == current_path:
                item.setSelected(True)
    status_label = getattr(owner, "_traits_status_label", None)
    if isinstance(status_label, QLabel):
        count = len(list_traits())
        status_label.setText(f"{count} trait{'s' if count != 1 else ''} installed.")


def _refresh_trait_predictions(owner: Any) -> None:
    render_traits = getattr(owner, "_render_traits_predictions", None)
    if callable(render_traits):
        render_traits(getattr(owner, "_latest_chart", None))


def on_trait_upload_clicked(owner: Any) -> None:
    file_path, _selected_filter = QFileDialog.getOpenFileName(
        owner,
        "Upload Trait File",
        "",
        "Trait files (*.json *.py);;JSON files (*.json);;Python files (*.py);;All files (*)",
    )
    if not file_path:
        return
    default_name = Path(file_path).stem
    name, accepted = QInputDialog.getText(owner, "Name new trait", "Trait name:", text=default_name)
    if not accepted:
        return
    clean_name = name.strip()
    if not clean_name:
        QMessageBox.information(owner, "Trait name required", "Enter a name for the new trait.")
        return
    try:
        install_trait_file(file_path, clean_name)
    except Exception as exc:
        QMessageBox.warning(owner, "Trait upload failed", f"Trait could not be installed: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)
    QMessageBox.information(owner, "Trait installed", f"Trait '{clean_name}' was installed.")


def on_trait_delete_clicked(owner: Any) -> None:
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(owner, "No trait selected", "Select a trait to delete first.")
        return
    trait_name = item.text()
    choice = QMessageBox.question(
        owner,
        "Delete trait?",
        f"Delete the trait '{trait_name}'? This cannot be undone.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if choice != QMessageBox.Yes:
        return
    delete_trait(item.data(Qt.UserRole))
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_rename_clicked(owner: Any) -> None:
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(owner, "No trait selected", "Select a trait to rename first.")
        return
    old_name = item.text()
    new_name, accepted = QInputDialog.getText(owner, "Rename trait", "Trait name:", text=old_name)
    if not accepted:
        return
    clean_name = new_name.strip()
    if not clean_name:
        QMessageBox.information(owner, "Trait name required", "Enter a new trait name.")
        return
    try:
        rename_trait(item.data(Qt.UserRole), clean_name)
    except Exception as exc:
        QMessageBox.warning(owner, "Trait rename failed", f"Trait could not be renamed: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)
