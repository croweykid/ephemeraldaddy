from PySide6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLabel

from ephemeraldaddy.gui.settings.percentage_weights import (
    update_percentage_weight_constraints,
)


def test_enabled_percentage_weights_cannot_exceed_combined_100_percent():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    checkboxes = {key: QCheckBox() for key in ("one", "two", "three")}
    spinboxes = {key: QDoubleSpinBox() for key in checkboxes}
    for checkbox in checkboxes.values():
        checkbox.setChecked(True)
    for spinbox in spinboxes.values():
        spinbox.setRange(0.0, 100.0)
    spinboxes["one"].setValue(45.0)
    spinboxes["two"].setValue(25.0)
    spinboxes["three"].setValue(30.0)
    total_label = QLabel()

    update_percentage_weight_constraints(checkboxes, spinboxes, total_label)

    assert spinboxes["one"].maximum() == 45.0
    assert spinboxes["two"].maximum() == 25.0
    assert spinboxes["three"].maximum() == 30.0
    assert "100.0%/100.0%" in total_label.text()

    spinboxes["one"].setValue(44.0)
    update_percentage_weight_constraints(checkboxes, spinboxes, total_label)
    assert spinboxes["three"].maximum() == 31.0


def test_disabled_percentage_weight_is_excluded_from_total_and_unconstrained():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    checkboxes = {key: QCheckBox() for key in ("enabled", "disabled")}
    spinboxes = {key: QDoubleSpinBox() for key in checkboxes}
    for spinbox in spinboxes.values():
        spinbox.setRange(0.0, 100.0)
        spinbox.setValue(75.0)
    checkboxes["enabled"].setChecked(True)
    total_label = QLabel()

    update_percentage_weight_constraints(checkboxes, spinboxes, total_label)

    assert spinboxes["enabled"].maximum() == 100.0
    assert spinboxes["disabled"].maximum() == 100.0
    assert total_label.text() == "75.0%/100.0%"
