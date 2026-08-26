"""Shared constraints for Settings percentage-weight editors."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QLabel

from ephemeraldaddy.gui.style import COLOR_ACCENT_SUCCESS


def update_percentage_weight_constraints(
    checkboxes: Mapping[str, QCheckBox],
    spinboxes: Mapping[str, QDoubleSpinBox],
    total_label: QLabel,
) -> None:
    """Cap each enabled weight at the share remaining from a 100% total."""
    for key, spinbox in spinboxes.items():
        checkbox = checkboxes.get(key)
        if checkbox is None:
            continue
        if checkbox.isChecked():
            other_enabled_total = sum(
                float(other_spinbox.value())
                for other_key, other_spinbox in spinboxes.items()
                if other_key != key
                and checkboxes.get(other_key) is not None
                and checkboxes[other_key].isChecked()
            )
            maximum = max(0.0, 100.0 - other_enabled_total)
        else:
            maximum = 100.0
        spinbox.setMaximum(round(maximum, 1))

    enabled_total = sum(
        float(spinboxes[key].value())
        for key, checkbox in checkboxes.items()
        if checkbox.isChecked() and key in spinboxes
    )
    total_text = f"{enabled_total:.1f}%/100.0%"
    if abs(enabled_total - 100.0) < 0.000_001:
        total_text += f'<br><span style="color: {COLOR_ACCENT_SUCCESS};">100%</span>'
    total_label.setText(total_text)
