"""Typology editor for Database View's Batch Editor workflow."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from ephemeraldaddy.gui.features.database_view.batch_editor.typology import (
    TypologyPatch,
    typology_patch_for_chart,
)
from ephemeraldaddy.gui.features.database_view.typology_selection import (
    MIXED,
    summarize_typology_selection,
)


@dataclass(frozen=True)
class BatchTypologyCallbacks:
    """Explicit Database View dependencies used by the typology editor."""

    selected_chart_uids: Callable[[], Iterable[str]]
    chart_for_uid: Callable[[str], Any]
    apply_patches: Callable[[Mapping[str, TypologyPatch]], set[int]]
    confirm: Callable[[str, int], bool]
    on_applied: Callable[[set[int]], None]


class BatchTypologyEditor(QWidget):
    """Own the Batch Editor controls and apply lifecycle for typology metadata."""

    def __init__(self, callbacks: BatchTypologyCallbacks, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._callbacks = callbacks
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        enneagram_layout = QGridLayout()
        enneagram_layout.addWidget(QLabel("Enneagram type"), 0, 0)
        enneagram_layout.addWidget(QLabel("Wing"), 0, 1)
        self.enneagram_inputs = tuple(self._integer_input() for _ in range(2))
        for column, edit in enumerate(self.enneagram_inputs):
            enneagram_layout.addWidget(edit, 1, column)
        layout.addLayout(enneagram_layout)

        layout.addWidget(QLabel("Enneagram tritype"))
        tritype_layout = QHBoxLayout()
        self.tritype_inputs = tuple(self._integer_input() for _ in range(3))
        for edit in self.tritype_inputs:
            tritype_layout.addWidget(edit)
        layout.addLayout(tritype_layout)

        layout.addWidget(QLabel("MBTI"))
        mbti_layout = QHBoxLayout()
        self.mbti_combos: tuple[QComboBox, ...] = tuple(
            self._mbti_combo(choices)
            for choices in (
                ("I", "i", "x", "e", "E"),
                ("S", "s", "x", "n", "N"),
                ("T", "t", "x", "f", "F"),
                ("J", "j", "x", "p", "P"),
            )
        )
        for combo in self.mbti_combos:
            mbti_layout.addWidget(combo)
        layout.addLayout(mbti_layout)

        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply typology")
        apply_button.clicked.connect(self.apply)
        button_layout.addWidget(apply_button)
        clear_selected_button = QPushButton("Clear selected typology")
        clear_selected_button.clicked.connect(self.clear_selected_typology)
        button_layout.addWidget(clear_selected_button)
        layout.addLayout(button_layout)

    def _integer_input(self) -> QLineEdit:
        edit = QLineEdit(self)
        edit.setValidator(QIntValidator(1, 9, edit))
        edit.setPlaceholderText("unchanged")
        edit.textEdited.connect(lambda _text, field=edit: self._set_mixed_input(field, False))
        return edit

    def _mbti_combo(self, choices: tuple[str, ...]) -> QComboBox:
        combo = QComboBox(self)
        combo.addItem("—", None)
        for choice in choices:
            combo.addItem(choice, choice)
        combo.currentIndexChanged.connect(
            lambda _index, field=combo: self._on_mbti_combo_changed(field)
        )
        return combo

    def clear(self) -> None:
        for edit in (*self.enneagram_inputs, *self.tritype_inputs):
            edit.clear()
            edit.setPlaceholderText("unchanged")
            self._set_mixed_input(edit, False)
        for combo in self.mbti_combos:
            mixed_index = combo.findText("mixed")
            if mixed_index >= 0:
                combo.removeItem(mixed_index)
            self._set_mixed_combo(combo, False)
            combo.setCurrentIndex(0)

    def update_from_charts(self, charts: Iterable[Any]) -> None:
        """Display values shared by the selection and italic mixed placeholders."""
        summary = summarize_typology_selection(charts)
        if summary is None:
            self.clear()
            return
        for edit, value in zip(
            (*self.enneagram_inputs, *self.tritype_inputs),
            (*summary.enneagram, *summary.tritype),
        ):
            edit.blockSignals(True)
            edit.clear()
            if value is MIXED:
                edit.setPlaceholderText("mixed")
                self._set_mixed_input(edit, True)
            else:
                edit.setPlaceholderText("unchanged")
                self._set_mixed_input(edit, False)
                if value is not None:
                    edit.setText(str(value))
            edit.blockSignals(False)
        for combo, value in zip(self.mbti_combos, summary.mbti):
            combo.blockSignals(True)
            mixed_index = combo.findText("mixed")
            if mixed_index >= 0:
                combo.removeItem(mixed_index)
            self._set_mixed_combo(combo, value is MIXED)
            if value is MIXED:
                combo.insertItem(0, "mixed", None)
                font = combo.itemData(0, Qt.FontRole)
                if font is None:
                    font = combo.font()
                font.setItalic(True)
                combo.setItemData(0, font, Qt.FontRole)
                combo.setCurrentIndex(0)
            else:
                index = combo.findData(value) if value is not None else combo.findData(None)
                combo.setCurrentIndex(max(0, index))
            combo.blockSignals(False)

    @staticmethod
    def _set_mixed_input(edit: QLineEdit, mixed: bool) -> None:
        font = edit.font()
        font.setItalic(mixed)
        edit.setFont(font)

    @staticmethod
    def _set_mixed_combo(combo: QComboBox, mixed: bool) -> None:
        """Style the collapsed value as well as the mixed popup item."""
        font = combo.font()
        font.setItalic(mixed)
        combo.setFont(font)

    def _on_mbti_combo_changed(self, combo: QComboBox) -> None:
        """Clear stale mixed styling once the user chooses a concrete value."""
        if combo.currentText() != "mixed":
            self._set_mixed_combo(combo, False)

    def apply(self) -> None:
        chart_uids = tuple(dict.fromkeys(self._callbacks.selected_chart_uids()))
        if not chart_uids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            return
        enneagram = tuple(self._input_value(edit) for edit in self.enneagram_inputs)
        tritype = tuple(self._input_value(edit) for edit in self.tritype_inputs)
        mbti = tuple(combo.currentData() for combo in self.mbti_combos)
        if not any((*enneagram, *tritype, *mbti)):
            QMessageBox.information(self, "No typology changes", "Enter at least one typology value.")
            return
        if not self._callbacks.confirm("update typology for", len(chart_uids)):
            return

        patches = {
            chart_uid: typology_patch_for_chart(
                self._callbacks.chart_for_uid(chart_uid),
                enneagram_values=enneagram,
                tritype_values=tritype,
                mbti_values=mbti,
            )
            for chart_uid in chart_uids
        }
        try:
            changed_ids = self._callbacks.apply_patches(patches)
        except Exception as exc:
            QMessageBox.critical(self, "Batch edit error", f"Could not update typology:\n{exc}")
            return
        self._callbacks.on_applied(changed_ids)

    def clear_selected_typology(self) -> None:
        """Explicitly remove assigned typology from every selected chart."""
        chart_uids = tuple(dict.fromkeys(self._callbacks.selected_chart_uids()))
        if not chart_uids:
            QMessageBox.information(
                self,
                "No charts selected",
                "Select one or more charts before applying batch edits.",
            )
            return
        if not self._callbacks.confirm("clear typology for", len(chart_uids)):
            return
        patch: TypologyPatch = {
            "enneagram_type": [0, 0],
            "tritype": [0, 0, 0],
            "mbti": ["?", "?", "?", "?"],
        }
        try:
            changed_ids = self._callbacks.apply_patches(
                {chart_uid: dict(patch) for chart_uid in chart_uids}
            )
        except Exception as exc:
            QMessageBox.critical(self, "Batch edit error", f"Could not clear typology:\n{exc}")
            return
        self.clear()
        self._callbacks.on_applied(changed_ids)

    @staticmethod
    def _input_value(edit: QLineEdit) -> int | None:
        return int(edit.text()) if edit.text().strip() else None
