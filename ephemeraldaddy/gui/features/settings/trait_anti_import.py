"""Anti-trait file import support for the Traits Property Manager."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from ephemeraldaddy.analysis import traits as trait_store


NORMAL_TO_ANTI_PROPERTY_KEYS: dict[str, str] = {
    "signs": "antisigns",
    "houses": "antihouses",
    "bodies": "antibodies",
    "elements": "antielements",
    "modes": "antimodes",
    "nakshatras": "antinakshatras",
    "positions": "antipositions",
    "aspects": "antiaspects",
    "gates": "antigates",
    "gate_lines": "antigate_lines",
    "channels": "antichannels",
    "hdtypes": "antihdtypes",
    "centers": "anticenters",
    "profiles": "antiprofiles",
    "authorities": "antiauthorities",
    "bazisigns": "antibazisigns",
}
ANTI_PROPERTY_KEYS: tuple[str, ...] = tuple(NORMAL_TO_ANTI_PROPERTY_KEYS.values())


def anti_properties_from_profile(profile: Mapping[str, Any]) -> dict[str, dict[Any, Any]]:
    """Copy ordinary weighted trait properties into their corresponding anti buckets.

    Weight signs are intentionally preserved. The scoring layer is responsible for
    treating anti buckets as antithetical evidence, so import must not negate values.
    Source ``anti*`` buckets and presentation/provenance metadata are ignored.
    """
    imported: dict[str, dict[Any, Any]] = {}
    for normal_key, anti_key in NORMAL_TO_ANTI_PROPERTY_KEYS.items():
        values = profile.get(normal_key, {})
        if isinstance(values, Mapping) and values:
            imported[anti_key] = dict(values)
    return imported


def load_anti_properties_from_file(path: str | Path) -> dict[str, dict[Any, Any]]:
    """Parse a trait/Similarities Analysis export and return ordinary properties as anti data."""
    profiles = trait_store.parse_trait_file(path)
    source_profile = next(iter(profiles.values()))
    imported = anti_properties_from_profile(source_profile)
    if not imported:
        raise ValueError("The selected file does not contain any ordinary weighted trait properties.")
    return imported


def trait_profile_has_anti_properties(profile: Mapping[str, Any]) -> bool:
    """Return whether any recognized anti-property bucket currently contains data."""
    return any(bool(profile.get(key)) for key in ANTI_PROPERTY_KEYS)


def apply_anti_properties_to_trait(
    target_path: str | Path,
    imported_anti_properties: Mapping[str, Mapping[Any, Any]],
    *,
    replace: bool,
) -> Path:
    """Append or replace anti-property buckets in one installed trait file.

    In append mode, imported values win only when the same criterion already exists
    in the same anti bucket. In replace mode, every recognized anti bucket is first
    cleared, so categories omitted by the new file do not survive from the old data.
    """
    clean_import: dict[str, dict[Any, Any]] = {}
    for anti_key, values in imported_anti_properties.items():
        if anti_key not in ANTI_PROPERTY_KEYS or not isinstance(values, Mapping):
            continue
        if values:
            clean_import[anti_key] = dict(values)
    if not clean_import:
        raise ValueError("No usable anti-properties were supplied.")

    target = Path(target_path)
    profiles = trait_store.parse_trait_file(target)
    _target_name, target_profile = next(iter(profiles.items()))

    updates: dict[str, dict[Any, Any]] = {}
    if replace:
        updates.update({anti_key: {} for anti_key in ANTI_PROPERTY_KEYS})

    for anti_key, incoming in clean_import.items():
        if replace:
            updates[anti_key] = dict(incoming)
            continue
        current = target_profile.get(anti_key, {})
        merged = dict(current) if isinstance(current, Mapping) else {}
        merged.update(incoming)
        updates[anti_key] = merged

    # Use the Trait store's canonical rewrite path so tuple channel keys, JSON-safe
    # conversion, and preserved source comments behave exactly like other Trait edits.
    return trait_store._rewrite_single_trait(target, updates)


def _find_layout_containing_widget(layout: Any, widget: Any) -> Any | None:
    """Return the nested layout that directly owns ``widget``."""
    count = getattr(layout, "count", None)
    if not callable(count):
        return None
    for index in range(count()):
        item = layout.itemAt(index)
        if item is None:
            continue
        if item.widget() is widget:
            return layout
        child_layout = item.layout()
        if child_layout is not None:
            match = _find_layout_containing_widget(child_layout, widget)
            if match is not None:
                return match
    return None


def _confirm_selected_file(parent: Any, *, file_name: str, trait_name: str) -> bool:
    prompt = QMessageBox(parent)
    prompt.setIcon(QMessageBox.Icon.Warning)
    prompt.setWindowTitle("Append anti-trait file?")
    prompt.setText(f"Add {file_name} as antithetical to {trait_name}?")
    nope_button = prompt.addButton("nope!", QMessageBox.ButtonRole.RejectRole)
    yeah_button = prompt.addButton("yeah", QMessageBox.ButtonRole.AcceptRole)
    prompt.setDefaultButton(nope_button)
    prompt.setEscapeButton(nope_button)
    prompt.exec()
    return prompt.clickedButton() is yeah_button


def _existing_anti_properties_choice(parent: Any, *, trait_name: str) -> str | None:
    prompt = QMessageBox(parent)
    prompt.setIcon(QMessageBox.Icon.Warning)
    prompt.setWindowTitle("Existing anti-properties")
    prompt.setText(f"{trait_name} already has anti- properties...")
    append_button = prompt.addButton("Append to existing", QMessageBox.ButtonRole.AcceptRole)
    replace_button = prompt.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = prompt.addButton("Agh! Never mind", QMessageBox.ButtonRole.RejectRole)
    prompt.setDefaultButton(cancel_button)
    prompt.setEscapeButton(cancel_button)
    prompt.exec()
    clicked = prompt.clickedButton()
    if clicked is append_button:
        return "append"
    if clicked is replace_button:
        return "replace"
    return None


def _sync_anti_trait_button(owner: Any) -> None:
    button = getattr(owner, "_traits_append_anti_button", None)
    if not isinstance(button, QPushButton):
        return
    item = getattr(owner, "_traits_list_widget", None)
    selected = item.selectedItems() if item is not None and callable(getattr(item, "selectedItems", None)) else []
    selected_item = selected[0] if selected else None
    bundled = bool(selected_item.data(Qt.UserRole + 4)) if selected_item is not None else False
    button.setEnabled(selected_item is not None and not bundled)


def add_anti_trait_file_button(core: ModuleType, owner: Any, traits_section: Any) -> None:
    """Insert the anti-trait import button immediately after Add Trait."""
    upload_button = getattr(owner, "_traits_upload_button", None)
    if not isinstance(upload_button, QPushButton):
        return

    owner._traits_append_anti_button = QPushButton("Append anti-trait file")
    owner._traits_append_anti_button.setToolTip(
        "append a JSON file that represents the antithesis of this trait"
    )
    owner._traits_append_anti_button.clicked.connect(
        lambda _checked=False: on_trait_append_anti_clicked(core, owner)
    )

    button_row = _find_layout_containing_widget(traits_section, upload_button)
    if button_row is None:
        traits_section.addWidget(owner._traits_append_anti_button)
    else:
        upload_index = button_row.indexOf(upload_button)
        button_row.insertWidget(upload_index + 1, owner._traits_append_anti_button)
    _sync_anti_trait_button(owner)


def on_trait_append_anti_clicked(core: ModuleType, owner: Any) -> None:
    """Import one trait/Similarities Analysis profile into the selected trait's anti-property buckets."""
    dialog_parent = core._settings_dialog_for(owner)
    item = core.selected_trait_item(owner)
    if item is None:
        QMessageBox.information(
            dialog_parent,
            "No trait selected",
            "Select a trait before appending an anti-trait file.",
        )
        return
    if bool(item.data(Qt.UserRole + 4)):
        QMessageBox.information(
            dialog_parent,
            "Default trait protected",
            "Bundled default trait JSON is read-only.",
        )
        return

    trait_name = core._trait_display_name(item)
    file_path, _selected_filter = QFileDialog.getOpenFileName(
        dialog_parent,
        "Append Anti-Trait File",
        "",
        "Trait files (*.json *.py);;JSON files (*.json);;Python files (*.py);;All files (*)",
    )
    if not file_path:
        return

    if not _confirm_selected_file(
        dialog_parent,
        file_name=Path(file_path).name,
        trait_name=trait_name,
    ):
        return

    try:
        imported = load_anti_properties_from_file(file_path)
        target_profiles = trait_store.parse_trait_file(item.data(Qt.UserRole))
        _target_name, target_profile = next(iter(target_profiles.items()))
    except Exception as exc:
        QMessageBox.warning(
            dialog_parent,
            "Anti-trait import failed",
            f"Anti-trait properties could not be read: {exc}",
        )
        return

    replace = False
    if trait_profile_has_anti_properties(target_profile):
        choice = _existing_anti_properties_choice(dialog_parent, trait_name=trait_name)
        if choice is None:
            return
        replace = choice == "replace"

    try:
        apply_anti_properties_to_trait(
            item.data(Qt.UserRole),
            imported,
            replace=replace,
        )
    except Exception as exc:
        QMessageBox.warning(
            dialog_parent,
            "Anti-trait import failed",
            f"Anti-trait properties could not be saved: {exc}",
        )
        return

    core._mark_trait_definitions_changed(owner, trait_names={trait_name}, clear_likelihoods=False)
    core._warm_trait_definitions(owner, {trait_name})
    core.refresh_traits_settings_list(owner)
    core._refresh_trait_predictions(owner)


def install_trait_anti_import(core: ModuleType) -> None:
    """Layer anti-trait import controls onto the stable Traits manager facade."""
    if bool(getattr(core, "_ephemeraldaddy_trait_anti_import_installed", False)):
        return

    original_populate = core.populate_traits_settings_layout
    original_sync = core._sync_trait_action_buttons

    def sync_with_anti_trait(owner: Any) -> None:
        original_sync(owner)
        _sync_anti_trait_button(owner)

    def populate_with_anti_trait(owner: Any, traits_section: Any) -> None:
        original_populate(owner, traits_section)
        add_anti_trait_file_button(core, owner, traits_section)

    core._sync_trait_action_buttons = sync_with_anti_trait
    core.populate_traits_settings_layout = populate_with_anti_trait
    core.on_trait_append_anti_clicked = lambda owner: on_trait_append_anti_clicked(core, owner)
    core._ephemeraldaddy_trait_anti_import_installed = True
