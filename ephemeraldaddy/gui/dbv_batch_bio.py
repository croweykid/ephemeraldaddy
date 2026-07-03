"""Bio batch-edit helpers for Database View's right-side Batch Editor panel."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from ephemeraldaddy.core.db import load_chart, update_chart


def build_batch_bio_section(
    owner: Any,
    add_collapsible_section: Callable[[str], tuple[QWidget, QVBoxLayout]],
    source_options: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    gender_options: list[str] | tuple[str, ...],
    quad_state_slider_class: type,
) -> QWidget:
    """Build the Batch Editor Biographical section and wire its updaters."""
    bio_section, bio_section_layout = add_collapsible_section("👤Biographical")

    bio_metadata_layout = QGridLayout()
    bio_metadata_layout.setContentsMargins(0, 0, 0, 0)
    bio_metadata_layout.setColumnStretch(1, 1)

    chart_type_label = QLabel("Chart Type:")
    chart_type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    owner.batch_source_combo = QComboBox()
    owner.batch_source_combo.addItem("Mixed / unchanged", "")
    for source_option_label, source_option_value in source_options:
        owner.batch_source_combo.addItem(source_option_label, source_option_value)
    owner.batch_source_combo.currentIndexChanged.connect(owner._on_batch_source_selected)
    bio_metadata_layout.addWidget(chart_type_label, 0, 0)
    bio_metadata_layout.addWidget(owner.batch_source_combo, 0, 1)

    gender_label = QLabel("Gender:")
    gender_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    owner.batch_gender_combo = QComboBox()
    owner.batch_gender_combo.addItem("Mixed / unchanged", "")
    owner.batch_gender_combo.addItem("blank", "__blank__")
    for gender_option in gender_options:
        owner.batch_gender_combo.addItem(gender_option, gender_option)
    owner.batch_gender_combo.currentIndexChanged.connect(owner._on_batch_gender_selected)
    bio_metadata_layout.addWidget(gender_label, 1, 0)
    bio_metadata_layout.addWidget(owner.batch_gender_combo, 1, 1)
    bio_section_layout.addLayout(bio_metadata_layout)

    owner.batch_birthtime_unknown_checkbox = quad_state_slider_class("birthtime unknown")
    owner.batch_birthtime_unknown_checkbox.modeChanged.connect(owner._on_batch_birthtime_unknown_state_changed)
    bio_section_layout.addWidget(owner.batch_birthtime_unknown_checkbox)

    owner.batch_deceased_checkbox = quad_state_slider_class("💀deceased")
    owner.batch_deceased_checkbox.modeChanged.connect(owner._on_batch_mortality_state_changed)
    bio_section_layout.addWidget(owner.batch_deceased_checkbox)

    bio_from_row = QHBoxLayout()
    bio_from_row.addWidget(QLabel("From"))

    owner.batch_from_whence_input = QLineEdit()
    owner.batch_from_whence_input.setPlaceholderText("band, show, movie, organization…")
    bio_from_row.addWidget(owner.batch_from_whence_input, 1)

    batch_from_whence_button = QPushButton("Update")
    batch_from_whence_button.clicked.connect(lambda: apply_batch_from_whence(owner))
    bio_from_row.addWidget(batch_from_whence_button)

    bio_section_layout.addLayout(bio_from_row)
    owner._bind_batch_enter_apply(owner.batch_from_whence_input, batch_from_whence_button.click)
    return bio_section


def set_batch_from_whence_state(owner: Any, from_whence_values: list[str]) -> None:
    """Reflect the selected charts' From values in the Batch Editor Bio field."""
    if not hasattr(owner, "batch_from_whence_input"):
        return
    owner.batch_from_whence_input.blockSignals(True)
    try:
        if len(set(from_whence_values)) == 1:
            owner.batch_from_whence_input.setText(from_whence_values[0])
            owner.batch_from_whence_input.setToolTip("")
        else:
            owner.batch_from_whence_input.setText("")
            owner.batch_from_whence_input.setToolTip(
                "Selected charts have mixed From values. Updating will overwrite all selected charts."
            )
    finally:
        owner.batch_from_whence_input.blockSignals(False)


def clear_batch_from_whence_state(owner: Any) -> None:
    """Clear the Batch Editor Bio field state."""
    if not hasattr(owner, "batch_from_whence_input"):
        return
    owner.batch_from_whence_input.setText("")
    owner.batch_from_whence_input.setToolTip("")


def apply_batch_from_whence(owner: Any) -> None:
    """Apply the Batch Editor Bio From value to all selected charts."""
    chart_ids = owner._selected_chart_ids()
    if not chart_ids:
        QMessageBox.information(
            owner,
            "No charts selected",
            "Select one or more charts before applying batch edits.",
        )
        owner._update_batch_edit_state()
        return

    from_value = owner.batch_from_whence_input.text().strip()
    selected_count = len(chart_ids)
    display_value = from_value or "blank"
    action_label = f"Set From to '{display_value}' for"
    if not owner._confirm_batch_edit(action_label, selected_count):
        owner._update_batch_edit_state()
        return

    try:
        for chart_id in chart_ids:
            chart = load_chart(chart_id)
            chart.from_whence = from_value or None
            update_chart(
                chart_id,
                chart,
                retcon_time_used=getattr(chart, "retcon_time_used", False),
            )
            owner._chart_cache[chart_id] = chart
    except Exception as exc:
        QMessageBox.critical(
            owner,
            "Batch edit error",
            f"Could not update selected charts' From values:\n{exc}",
        )
        return

    changed_ids = set(chart_ids)
    owner._update_batch_edit_state()
    owner._refresh_filters_after_batch_edit(changed_ids)
