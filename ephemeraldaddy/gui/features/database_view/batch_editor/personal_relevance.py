"""Database View Batch Editor Personal Relevance controls."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget

from ephemeraldaddy.gui.features.chart_editor.personal_relevance import (
    LAST_ENCOUNTER_MAX_YEAR,
    LAST_ENCOUNTER_MIN_YEAR,
    parse_last_encounter_text,
)


def build_batch_last_encounter_controls(window: Any, layout: Any, *, row: int = 4) -> None:
    """Add Batch Editor Last Encounter controls and store widget refs on ``window``."""
    window.batch_current_relationship_checkbox = QCheckBox("ongoing")
    window.batch_current_relationship_checkbox.setChecked(True)
    window.batch_current_relationship_checkbox.toggled.connect(
        lambda checked: on_batch_last_encounter_ongoing_toggled(window, checked)
    )
    window.batch_current_relationship_checkbox.toggled.connect(
        lambda _checked: window._on_batch_metric_field_lucygoosey("last_encounter")
    )

    window.batch_last_encounter_edit = QLineEdit()
    window.batch_last_encounter_edit.setPlaceholderText("blank")
    window.batch_last_encounter_edit.setMaxLength(4)
    window.batch_last_encounter_edit.setFixedWidth(56)
    window.batch_last_encounter_edit.setValidator(
        QIntValidator(LAST_ENCOUNTER_MIN_YEAR, LAST_ENCOUNTER_MAX_YEAR, window)
    )
    window.batch_last_encounter_edit.setVisible(False)
    window.batch_last_encounter_edit.textEdited.connect(
        lambda _text: window._on_batch_metric_field_lucygoosey("last_encounter")
    )

    window.batch_last_encounter_apply_button = QPushButton("Apply")
    window.batch_last_encounter_apply_button.clicked.connect(
        lambda: on_batch_last_encounter_apply(window)
    )

    batch_last_encounter_widget = QWidget()
    batch_last_encounter_layout = QHBoxLayout()
    batch_last_encounter_layout.setContentsMargins(0, 0, 0, 0)
    batch_last_encounter_layout.setSpacing(6)
    batch_last_encounter_layout.addWidget(window.batch_current_relationship_checkbox)
    batch_last_encounter_layout.addWidget(window.batch_last_encounter_edit)
    batch_last_encounter_layout.addStretch(1)
    batch_last_encounter_widget.setLayout(batch_last_encounter_layout)

    layout.addWidget(QLabel("💭Last Encounter"), row, 0)
    layout.addWidget(batch_last_encounter_widget, row, 1)
    layout.addWidget(window.batch_last_encounter_apply_button, row, 2)


def set_batch_last_encounter_state(
    window: Any,
    current_values: list[bool],
    last_values: list[int | None],
    *,
    preserve_lucygoosey: bool = False,
) -> None:
    if not current_values:
        window.batch_current_relationship_checkbox.setChecked(True)
        window.batch_last_encounter_edit.setText("")
        window.batch_last_encounter_edit.setVisible(False)
        window._set_batch_metric_lucygoosey_state("last_encounter", False)
        return
    if preserve_lucygoosey and window._batch_metric_lucygoosey.get("last_encounter", False):
        return

    first_current = bool(current_values[0])
    first_last = last_values[0] if last_values else None
    window._batch_metric_programmatic_update = True
    window.batch_current_relationship_checkbox.blockSignals(True)
    window.batch_last_encounter_edit.blockSignals(True)
    window.batch_current_relationship_checkbox.setChecked(first_current)
    window.batch_last_encounter_edit.setText("" if first_last is None else str(first_last))
    window.batch_last_encounter_edit.setVisible(not first_current)
    window.batch_last_encounter_edit.blockSignals(False)
    window.batch_current_relationship_checkbox.blockSignals(False)
    window._batch_metric_programmatic_update = False
    window._set_batch_metric_lucygoosey_state("last_encounter", False)

    if len(set(current_values)) > 1 or len({value for value in last_values}) > 1:
        tooltip = "Selected charts have mixed last encounter values. Applying will overwrite all selected charts."
    else:
        tooltip = ""
    window.batch_current_relationship_checkbox.setToolTip(tooltip)
    window.batch_last_encounter_edit.setToolTip(tooltip)


def reset_batch_last_encounter_state(window: Any) -> None:
    window.batch_current_relationship_checkbox.setChecked(True)
    window.batch_last_encounter_edit.setText("")
    window.batch_last_encounter_edit.setToolTip("")
    window.batch_last_encounter_edit.setVisible(False)


def on_batch_last_encounter_ongoing_toggled(window: Any, checked: bool) -> None:
    window.batch_last_encounter_edit.setVisible(not checked)


def on_batch_last_encounter_apply(window: Any) -> None:
    current_relationship = window.batch_current_relationship_checkbox.isChecked()
    last_encounter = (
        None
        if current_relationship
        else parse_last_encounter_text(window.batch_last_encounter_edit.text())
    )
    patch = {
        "current_relationship": current_relationship,
        "last_encounter": last_encounter,
    }
    display_value = "ongoing" if current_relationship else (last_encounter or "blank")
    chart_uids = window._selected_chart_uids()
    chart_ids = window._local_row_ids_for_uids(chart_uids)
    if not chart_ids:
        QMessageBox.information(
            window,
            "No charts selected",
            "Psst...Select one or more charts before applying batch edits.",
        )
        window._update_batch_edit_state()
        return
    if not window._confirm_batch_edit(f"Set last encounter to {display_value} for", len(chart_ids)):
        window._update_batch_edit_state()
        return
    try:
        window._apply_batch_nonastral_patch(chart_uids, patch)
    except Exception as exc:
        QMessageBox.critical(
            window,
            "Batch edit error",
            f"*sepukkus* Couldn't update the selected charts:\n{exc}",
        )
        return
    changed_ids = set(chart_ids)
    window._update_sentiment_tally(
        show_progress=True,
        changed_ids=changed_ids,
        changed_fields={"current_relationship", "last_encounter"},
    )
    window._set_batch_metric_lucygoosey_state("last_encounter", False)
    window._update_batch_edit_state()
    window._refresh_filters_after_batch_edit(changed_ids)
