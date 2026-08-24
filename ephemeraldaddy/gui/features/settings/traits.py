"""Settings panel UI for managing locally uploaded custom traits."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.traits import (
    DEFAULT_TRAIT_COLOR,
    clear_trait_possible_score_cache,
    delete_trait,
    install_trait_file,
    list_traits,
    normalize_trait_color,
    parse_trait_file,
    rename_trait,
    set_trait_archived,
    set_trait_color,
    set_trait_description,
)


TRAIT_RECOMMENDED_WORKING_SET_LIMIT = 100


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
    traits_section = owner._add_settings_collapsible_section(
        content_layout,
        "Traits",
        fill_available_height=True,
    )
    traits_section.addWidget(
        owner._build_settings_help_label(
            "Manage custom trait profiles exported from Similarities Analysis. Uploaded traits are saved locally in ~/.ephemeraldaddy/traits and scored in Chart Editor > Predictions."
        )
    )
    owner._traits_list_widget = QListWidget()
    owner._traits_list_widget.setMinimumHeight(0)
    owner._traits_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    owner._traits_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
    traits_section.addWidget(owner._traits_list_widget, 1)

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
    owner._traits_edit_button = QPushButton("Edit JSON…")
    owner._traits_edit_button.clicked.connect(lambda _checked=False: on_trait_edit_clicked(owner))
    traits_second_button_row.addWidget(owner._traits_edit_button)

    owner._traits_reassess_unavailable_button = QPushButton("Reassess unavailable traits")
    owner._traits_reassess_unavailable_button.setToolTip(
        "Calculate DB norms only for active traits whose norm is missing or analytically outdated."
    )
    owner._traits_reassess_unavailable_button.clicked.connect(
        lambda _checked=False: on_reassess_unavailable_traits_clicked(owner)
    )
    traits_second_button_row.addWidget(owner._traits_reassess_unavailable_button)

    owner._traits_description_button = QPushButton("Add description…")
    owner._traits_description_button.clicked.connect(lambda _checked=False: on_trait_description_clicked(owner))
    traits_second_button_row.addWidget(owner._traits_description_button)
    traits_second_button_row.addStretch(1)
    traits_section.addLayout(traits_second_button_row)
    owner._traits_list_widget.itemSelectionChanged.connect(lambda: _sync_trait_action_buttons(owner))

    owner._traits_status_label = QLabel("")
    owner._traits_status_label.setWordWrap(True)
    owner._traits_status_label.setStyleSheet("color: #9a9a9a; font-style: italic; font-size: 7pt;")
    refresh_traits_settings_list(owner)


def selected_trait_item(owner: Any) -> QListWidgetItem | None:
    list_widget = getattr(owner, "_traits_list_widget", None)
    if not isinstance(list_widget, QListWidget):
        return None
    selected = list_widget.selectedItems()
    return selected[0] if selected else None


def _trait_display_name(item: QListWidgetItem) -> str:
    raw_name = item.data(Qt.UserRole + 5)
    if raw_name is not None:
        return str(raw_name)
    text = item.text()
    for suffix in (" (default, archived)", " (default)", " (archived)"):
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


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
            bundled = bool(trait.get("bundled", False))
            color = normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
            labels = []
            if bundled:
                labels.append("default")
            if archived:
                labels.append("archived")
            suffix = f" ({', '.join(labels)})" if labels else ""
            item = QListWidgetItem(f"{name}{suffix}")
            item.setData(Qt.UserRole, str(trait["path"]))
            item.setData(Qt.UserRole + 1, color)
            item.setData(Qt.UserRole + 2, archived)
            item.setData(Qt.UserRole + 3, str(trait.get("description", "")).strip())
            item.setData(Qt.UserRole + 4, bundled)
            item.setData(Qt.UserRole + 5, name)
            item.setData(Qt.UserRole + 6, str(trait.get("uid") or trait.get("trait_uid") or "").strip())
            item.setForeground(QColor(color))
            list_widget.addItem(item)
            if str(trait["path"]) == current_path:
                item.setSelected(True)
    status_label = getattr(owner, "_traits_status_label", None)
    traits = list_traits()
    count = len(traits)
    archived_count = sum(1 for trait in traits if bool(trait.get("archived", False)))
    bundled_count = sum(1 for trait in traits if bool(trait.get("bundled", False)))
    custom_count = count - bundled_count
    status_text = (
        f"{count} trait{'s' if count != 1 else ''} available "
        f"({bundled_count} bundled default, {custom_count} custom); "
        f"{archived_count} archived and excluded from Predictions. "
        f"{count} of {TRAIT_RECOMMENDED_WORKING_SET_LIMIT} traits currently defined "
        "(recommended working set)."
    )
    footer_writer = getattr(owner, "_set_settings_section_footer_note", None)
    if callable(footer_writer):
        footer_writer("Traits", status_text)
    elif isinstance(status_label, QLabel):
        status_label.setText(status_text)
    _sync_trait_action_buttons(owner)


def _refresh_trait_predictions(owner: Any) -> None:
    render_traits = getattr(owner, "_render_traits_predictions", None)
    if callable(render_traits):
        render_traits(getattr(owner, "_latest_chart", None))
    _keep_settings_dialog_foreground(owner)


def _mark_trait_definitions_changed(
    owner: Any,
    *,
    trait_names: set[str] | None = None,
    clear_likelihoods: bool = True,
) -> None:
    """Invalidate trait-derived caches after a trait definition changes."""
    clear_trait_possible_score_cache()
    if clear_likelihoods:
        clear_traits_cache = getattr(owner, "_clear_traits_distribution_analytics_cache", None)
        if callable(clear_traits_cache):
            clear_traits_cache()
        return
    if hasattr(owner, "_traits_distribution_analytics_cache"):
        owner._traits_distribution_analytics_cache = {}


def _warm_trait_definitions(owner: Any, trait_names: set[str] | None = None) -> None:
    """Calculate only selected traits and merge them into the static norm snapshot."""
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import refresh_trait_norms_snapshot

    traits = list_traits(active_only=True)
    if trait_names is not None:
        normalized = {name.casefold() for name in trait_names}
        traits = [trait for trait in traits if str(trait.get("name", "")).casefold() in normalized]
    refresh_trait_norms_snapshot(owner, traits)


def on_reassess_unavailable_traits_clicked(owner: Any) -> None:
    """Repair only missing/stale active Trait norms, never the complete snapshot."""
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
        load_prediction_norms_snapshot,
        missing_trait_norms,
        refresh_trait_norms_snapshot,
    )

    dialog_parent = _settings_dialog_for(owner)
    traits = list_traits(active_only=True)
    missing = missing_trait_norms(traits, load_prediction_norms_snapshot())
    if not missing:
        QMessageBox.information(dialog_parent, "Trait norms up to date", "All active traits already have current DB norms.")
        return
    names = [str(trait.get("name", "") or "").strip() for trait in missing]
    button = getattr(owner, "_traits_reassess_unavailable_button", None)
    if isinstance(button, QPushButton):
        button.setEnabled(False)
    try:
        refresh_trait_norms_snapshot(owner, missing)
        failures = dict(getattr(owner, "_trait_norm_refresh_failures", {}) or {})
        repaired = [name for name in names if name and name not in failures]
        message = f"Reassessed {len(names)} unavailable trait(s); {len(repaired)} repaired."
        if failures:
            message += " Failed: " + ", ".join(sorted(failures)) + ". See the terminal for details."
        QMessageBox.information(dialog_parent, "Trait norm reassessment complete", message)
        _refresh_trait_predictions(owner)
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait norm reassessment failed", str(exc))
    finally:
        if isinstance(button, QPushButton):
            button.setEnabled(True)


def _validate_trait_source_text(source_path: Path, text: str) -> None:
    """Validate edited trait source by parsing it before overwriting the installed file."""
    suffix = source_path.suffix or ".json"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=suffix, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(text)
    try:
        parse_trait_file(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


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
    _mark_trait_definitions_changed(owner, trait_names={clean_name}, clear_likelihoods=False)
    _warm_trait_definitions(owner, {clean_name})
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)
    QMessageBox.information(dialog_parent, "Trait installed", f"Trait '{clean_name}' was installed.")


def on_trait_delete_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to delete first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(
            dialog_parent,
            "Default trait protected",
            "Bundled default traits are read-only. Duplicate local traits with the same name are automatically retired instead.",
        )
        return
    trait_name = _trait_display_name(item)
    choice = QMessageBox.question(
        dialog_parent,
        "Delete trait?",
        f"Delete the trait '{trait_name}'? This cannot be undone.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if choice != QMessageBox.Yes:
        return
    trait_uid = str(item.data(Qt.UserRole + 6) or "").strip()
    try:
        from ephemeraldaddy.core import db

        db.purge_chart_trait_metadata_for_trait(trait_uid=trait_uid, trait_name=trait_name)
    except Exception as exc:
        QMessageBox.warning(
            dialog_parent,
            "Trait metadata cleanup failed",
            f"Trait metadata for '{trait_name}' could not be purged: {exc}",
        )
        return
    delete_trait(item.data(Qt.UserRole))
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import remove_trait_from_prediction_norms_snapshot

    owner._prediction_norms_snapshot_cache = remove_trait_from_prediction_norms_snapshot(
        trait_uid=trait_uid, trait_name=trait_name
    )
    _mark_trait_definitions_changed(owner, trait_names={trait_name}, clear_likelihoods=False)
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_rename_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to rename first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(dialog_parent, "Default trait protected", "Bundled default traits cannot be renamed.")
        return
    old_name = _trait_display_name(item)
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
    # Names are presentation metadata; the UID-keyed analytical profile and its
    # norm remain valid, so renaming must not trigger database rescoring.
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def _sync_trait_action_buttons(owner: Any) -> None:
    item = selected_trait_item(owner)
    archived = bool(item.data(Qt.UserRole + 2)) if item is not None else False
    bundled = bool(item.data(Qt.UserRole + 4)) if item is not None else False
    archive_button = getattr(owner, "_traits_archive_button", None)
    if isinstance(archive_button, QPushButton):
        archive_button.setText("Reactivate" if archived else "Archive")
        archive_button.setEnabled(item is not None and not bundled)
    for attr in ("_traits_delete_button", "_traits_rename_button", "_traits_recolor_button"):
        button = getattr(owner, attr, None)
        if isinstance(button, QPushButton):
            button.setEnabled(item is not None and not bundled)
    description_button = getattr(owner, "_traits_description_button", None)
    if isinstance(description_button, QPushButton):
        description_button.setEnabled(item is not None and not bundled)
    edit_button = getattr(owner, "_traits_edit_button", None)
    if isinstance(edit_button, QPushButton):
        edit_button.setEnabled(item is not None and not bundled)


def on_trait_recolor_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to recolor first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(dialog_parent, "Default trait protected", "Bundled default traits cannot be recolored.")
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
    # Color is display-only and must not invalidate likelihoods or norm baselines.
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_archive_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to archive or reactivate first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(dialog_parent, "Default trait protected", "Bundled default traits cannot be archived.")
        return
    archived = bool(item.data(Qt.UserRole + 2))
    trait_name = _trait_display_name(item)
    try:
        set_trait_archived(item.data(Qt.UserRole), not archived)
    except Exception as exc:
        action = "reactivated" if archived else "archived"
        QMessageBox.warning(dialog_parent, "Trait update failed", f"Trait could not be {action}: {exc}")
        return
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import set_trait_retired_in_prediction_norms_snapshot

    updated_trait = next(
        (trait for trait in list_traits() if str(trait.get("uid") or "") == str(item.data(Qt.UserRole + 6) or "")),
        {"uid": str(item.data(Qt.UserRole + 6) or ""), "name": trait_name},
    )
    owner._prediction_norms_snapshot_cache = set_trait_retired_in_prediction_norms_snapshot(
        updated_trait, retired=not archived
    )
    refresh_traits_settings_list(owner)
    refresh_ranking_traits = getattr(owner, "_refresh_rankings_trait_choices_after_archive", None)
    if callable(refresh_ranking_traits):
        refresh_ranking_traits(trait_name=trait_name, archived=not archived)


def on_trait_description_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to describe first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(dialog_parent, "Default trait protected", "Bundled default trait descriptions are read-only.")
        return
    trait_name = _trait_display_name(item)
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
    # Description is display-only and must not invalidate analytical caches.
    refresh_traits_settings_list(owner)
    _refresh_trait_predictions(owner)


def on_trait_edit_clicked(owner: Any) -> None:
    dialog_parent = _settings_dialog_for(owner)
    item = selected_trait_item(owner)
    if item is None:
        QMessageBox.information(dialog_parent, "No trait selected", "Select a trait to edit first.")
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(dialog_parent, "Default trait protected", "Bundled default trait JSON is read-only.")
        return

    trait_path = Path(str(item.data(Qt.UserRole)))
    trait_name = _trait_display_name(item)
    try:
        original_text = trait_path.read_text(encoding="utf-8")
    except Exception as exc:
        QMessageBox.warning(dialog_parent, "Trait edit failed", f"Trait file could not be opened: {exc}")
        return

    dialog = QDialog(dialog_parent)
    dialog.setWindowTitle(f"Edit Trait JSON - {trait_name}")
    dialog.resize(760, 620)
    layout = QVBoxLayout(dialog)

    help_label = QLabel(
        "Edit the installed trait JSON below. Save validates the file, writes it through the app, "
        "then invalidates trait-derived analytics so chart trait calculations can refresh from the new definition."
    )
    help_label.setWordWrap(True)
    help_label.setStyleSheet("color: #d8d8d8;")
    layout.addWidget(help_label)

    editor = QPlainTextEdit(dialog)
    editor.setPlainText(original_text)
    editor.setLineWrapMode(QPlainTextEdit.NoWrap)
    layout.addWidget(editor, 1)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    layout.addWidget(buttons)

    def save_changes() -> None:
        updated_text = editor.toPlainText()
        try:
            _validate_trait_source_text(trait_path, updated_text)
            trait_path.write_text(updated_text, encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(dialog, "Trait JSON invalid", f"Trait could not be saved: {exc}")
            return
        _mark_trait_definitions_changed(owner, trait_names={trait_name}, clear_likelihoods=False)
        _warm_trait_definitions(owner, {trait_name})
        refresh_traits_settings_list(owner)
        _refresh_trait_predictions(owner)
        dialog.accept()

    buttons.accepted.connect(save_changes)
    buttons.rejected.connect(dialog.reject)
    dialog.exec()
