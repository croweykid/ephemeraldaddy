"""Settings panel UI for managing locally uploaded custom traits."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ephemeraldaddy.analysis.traits import (
    DEFAULT_TRAIT_COLOR,
    delete_trait,
    install_trait_file,
    list_traits,
    normalize_trait_color,
    rename_trait,
    set_trait_archived,
    set_trait_color,
    set_trait_description,
)


def _settings_dialog_for(owner: Any) -> QWidget:
    """Return the Settings dialog when it is available, otherwise the owner window."""
    dialog = getattr(owner, "_settings_dialog", None)
    return dialog if isinstance(dialog, QWidget) else owner


def _keep_settings_dialog_foreground(owner: Any) -> None:
    """Keep Settings above Chart View after trait edits refresh predictions."""
    dialog = getattr(owner, "_settings_dialog", None)
    if not isinstance(dialog, QWidget) or not dialog.isVisible():
        return

    def raise_dialog() -> None:
        if dialog.isVisible():
            dialog.raise_()
            dialog.activateWindow()
            dialog.setFocus(Qt.ActiveWindowFocusReason)

    QTimer.singleShot(0, raise_dialog)


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

    owner._traits_recolor_button = QPushButton("Recolor")
    owner._traits_recolor_button.clicked.connect(lambda _checked=False: on_trait_recolor_clicked(owner))
    traits_button_row.addWidget(owner._traits_recolor_button)

    owner._traits_archive_button = QPushButton("Archive")
    owner._traits_archive_button.clicked.connect(lambda _checked=False: on_trait_archive_clicked(owner))
    traits_button_row.addWidget(owner._traits_archive_button)

    owner._traits_upload_button = QPushButton("Add Trait…")
    owner._traits_upload_button.clicked.connect(lambda _checked=False: on_trait_upload_clicked(owner))
    traits_button_row.addWidget(owner._traits_upload_button)
    traits_button_row.addStretch(1)
    traits_section.addLayout(traits_button_row)

    traits_second_button_row = QHBoxLayout()
    owner._traits_description_button = QPushButton("Add description…")
    owner._traits_description_button.clicked.connect(lambda _checked=False: on_trait_description_clicked(owner))
    traits_second_button_row.addWidget(owner._traits_description_button)
    traits_second_button_row.addStretch(1)
    traits_section.addLayout(traits_second_button_row)
    owner._traits_list_widget.itemSelectionChanged.connect(lambda: _sync_trait_action_buttons(owner))

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
            name = str(trait["name"])
            archived = bool(trait.get("archived", False))
            color = normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
            item = QListWidgetItem(f"{name} {'(archived)' if archived else ''}".strip())
            item.setData(Qt.UserRole, str(trait["path"]))
            item.setData(Qt.UserRole + 1, color)
            item.setData(Qt.UserRole + 2, archived)
            item.setData(Qt.UserRole + 3, str(trait.get("description", "")).strip())
            item.setForeground(QColor(color))
            list_widget.addItem(item)
            if str(trait["path"]) == current_path:
                item.setSelected(True)
    status_label = getattr(owner, "_traits_status_label", None)
    if isinstance(status_label, QLabel):
        traits = list_traits()
        count = len(traits)
        archived_count = sum(1 for trait in traits if bool(trait.get("archived", False)))
        status_label.setText(
            f"{count} trait{'s' if count != 1 else ''} installed; "
            f"{archived_count} archived and excluded from Predictions."
        )
    _sync_trait_action_buttons(owner)


def _refresh_trait_predictions(owner: Any) -> None:
    render_traits = getattr(owner, "_render_traits_predictions", None)
    if callable(render_traits):
        render_traits(getattr(owner, "_latest_chart", None))
    _keep_settings_dialog_foreground(owner)


def on_trait_upload_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    file_path, _selected_filter = QFileDialog.getOpenFileName(
        dialog_parent,
        "Upload Trait File",
        "",
        "Trait files (*.json *.py);;JSON files (*.json);;Python files (*.py);;All files (*)",
    )
    if not file_path:
        return
    default_name = Path(file_path).stem
    name, accepted = QInputDialog.getText(dialog_parent, "Name new trait", "Trait name:", text=default_name)
    if not accepted:
        return
    clean_name = name.strip()
    if not clean_name:
        QMessageBox.information(dialog_parent, "Trait name required", "Enter a name for the new trait.")
        return
    color = QColorDialog.getColor(QColor(DEFAULT_TRAIT_COLOR), dialog_parent, "Choose trait color")
    if not color.isValid():
        return
    try:
        install_trait_file(file_path, clean_name, color=color.name())
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait upload failed", f"Trait could not be installed: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)
    QMessageBox.information(dialog_parent, "Trait installed", f"Trait '{clean_name}' was installed.")


def on_trait_delete_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to delete first.")
        return
    trait_name = item.text()
    choice = QMessageBox.question(
        dialog_parent,
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
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to rename first.")
        return
    old_name = item.text()
    new_name, accepted = QInputDialog.getText(dialog_parent, "Rename trait", "Trait name:", text=old_name)
    if not accepted:
        return
    clean_name = new_name.strip()
    if not clean_name:
        QMessageBox.information(dialog_parent, "Trait name required", "Enter a new trait name.")
        return
    try:
        rename_trait(item.data(Qt.UserRole), clean_name)
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait rename failed", f"Trait could not be renamed: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def _sync_trait_action_buttons(owner: Any) -> None:
    item = selected_trait_item(owner)
    archived = bool(item.data(Qt.UserRole + 2)) if item is not None else False
    archive_button = getattr(owner, "_traits_archive_button", None)
    if isinstance(archive_button, QPushButton):
        archive_button.setText("Reactivate" if archived else "Archive")
    description_button = getattr(owner, "_traits_description_button", None)
    if isinstance(description_button, QPushButton):
        description_button.setEnabled(item is not None)


def on_trait_recolor_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to recolor first.")
        return
    current_color = normalize_trait_color(str(item.data(Qt.UserRole + 1) or DEFAULT_TRAIT_COLOR))
    color = QColorDialog.getColor(QColor(current_color), dialog_parent, "Choose trait color")
    if not color.isValid():
        return
    try:
        set_trait_color(item.data(Qt.UserRole), color.name())
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait recolor failed", f"Trait could not be recolored: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_archive_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to archive or reactivate first.")
        return
    archived = bool(item.data(Qt.UserRole + 2))
    try:
        set_trait_archived(item.data(Qt.UserRole), not archived)
    except Exception as exc:
        action = "reactivated" if archived else "archived"
        QMessageBox.warning(dialog_parent, "Trait update failed", f"Trait could not be {action}: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_description_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to describe first.")
        return
    trait_name = item.text().replace(" (archived)", "")
    current_description = str(item.data(Qt.UserRole + 3) or "")
    description, accepted = QInputDialog.getMultiLineText(
        dialog_parent,
        "Add trait description",
        f"Description for {trait_name}:",
        current_description,
    )
    if not accepted:
        return
    try:
        set_trait_description(item.data(Qt.UserRole), description)
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait update failed", f"Trait description could not be saved: {exc}")
        return
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)
