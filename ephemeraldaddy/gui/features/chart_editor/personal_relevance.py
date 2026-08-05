"""Chart Editor Personal Relevance controls and metadata helpers."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QWidget

LAST_ENCOUNTER_MIN_YEAR = 1900
LAST_ENCOUNTER_MAX_YEAR = 2100


def parse_last_encounter_text(raw_value: str | None) -> int | None:
    """Return a valid Last Encounter year, or ``None`` for blank/invalid text."""
    value = (raw_value or "").strip()
    if len(value) != 4 or not value.isdigit():
        return None
    parsed = int(value)
    if not LAST_ENCOUNTER_MIN_YEAR <= parsed <= LAST_ENCOUNTER_MAX_YEAR:
        return None
    return parsed


def configure_chart_editor_personal_relevance_controls(owner: Any) -> None:
    """Create Chart Editor 1st/Last Encounter widgets on the owning window."""
    owner.year_first_encountered_edit = QLineEdit()
    owner.year_first_encountered_edit.setMaxLength(4)
    owner.year_first_encountered_edit.setPlaceholderText("Year 1st Encountered")
    owner.year_first_encountered_edit.setFixedWidth(56)
    owner.year_first_encountered_edit.setValidator(
        QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$"), owner)
    )
    owner.year_first_encountered_edit.textChanged.connect(owner._on_sentiment_metric_changed)

    owner.current_relationship_checkbox = QCheckBox("ongoing")
    owner.current_relationship_checkbox.setChecked(True)
    owner.current_relationship_checkbox.toggled.connect(
        lambda checked: owner.last_encounter_edit.setVisible(not checked)
    )
    owner.current_relationship_checkbox.toggled.connect(owner._on_sentiment_metric_changed)

    owner.last_encounter_edit = QLineEdit()
    owner.last_encounter_edit.setMaxLength(4)
    owner.last_encounter_edit.setPlaceholderText("YYYY")
    owner.last_encounter_edit.setFixedWidth(56)
    owner.last_encounter_edit.setValidator(
        QIntValidator(LAST_ENCOUNTER_MIN_YEAR, LAST_ENCOUNTER_MAX_YEAR, owner)
    )
    owner.last_encounter_edit.textChanged.connect(owner._on_sentiment_metric_changed)
    owner.last_encounter_edit.setVisible(False)


def add_chart_editor_personal_relevance_rows(owner: Any, layout: Any, *, first_row: int = 3) -> None:
    """Add Chart Editor Personal Relevance encounter rows to ``layout``."""
    layout.addWidget(QLabel("1st Encounter:"), first_row, 0)
    layout.addWidget(owner.year_first_encountered_edit, first_row, 1)

    last_encounter_row_widget = QWidget()
    last_encounter_row_layout = QHBoxLayout()
    last_encounter_row_layout.setContentsMargins(0, 0, 0, 0)
    last_encounter_row_layout.setSpacing(6)
    last_encounter_row_layout.addWidget(owner.current_relationship_checkbox)
    last_encounter_row_layout.addWidget(owner.last_encounter_edit)
    last_encounter_row_layout.addStretch(1)
    last_encounter_row_widget.setLayout(last_encounter_row_layout)
    layout.addWidget(QLabel("Last Encounter:"), first_row + 1, 0)
    layout.addWidget(last_encounter_row_widget, first_row + 1, 1)


def reset_chart_editor_last_encounter_controls(owner: Any) -> None:
    owner.current_relationship_checkbox.setChecked(True)
    owner.last_encounter_edit.setText("")
    owner.last_encounter_edit.setVisible(False)


def apply_chart_editor_last_encounter_metadata(owner: Any, chart: Any, *, is_event_chart: bool) -> None:
    chart.current_relationship = True if is_event_chart else owner.current_relationship_checkbox.isChecked()
    chart.last_encounter = (
        None
        if is_event_chart or chart.current_relationship
        else parse_last_encounter_text(owner.last_encounter_edit.text())
    )


def load_chart_editor_last_encounter_controls(owner: Any, chart: Any) -> None:
    current_relationship = bool(getattr(chart, "current_relationship", True))
    owner.current_relationship_checkbox.setChecked(current_relationship)
    owner.last_encounter_edit.setText(
        "" if getattr(chart, "last_encounter", None) is None else str(getattr(chart, "last_encounter"))
    )
    owner.last_encounter_edit.setVisible(not current_relationship)
