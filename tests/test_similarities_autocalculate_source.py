from pathlib import Path


CONTROLLER_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/similarities/controller.py"
).read_text(encoding="utf-8")


def test_autocalculate_control_and_tooltip_live_in_similarity_controller():
    assert 'QLabel("Autocalculate")' in CONTROLLER_SOURCE
    assert 'self.autocalculate_toggle = QCheckBox("ON")' in CONTROLLER_SOURCE
    assert (
        "Begin similarities analysis whenever more than 1 chart is selected"
        in CONTROLLER_SOURCE
    )
    assert 'toggle.setText("ON" if self.autocalculate_enabled else "OFF")' in CONTROLLER_SOURCE


def test_disabled_autocalculate_preserves_analysis_and_marks_stale_selection():
    assert "if not self.autocalculate_enabled and not self._force_calculation:" in CONTROLLER_SOURCE
    assert "signature != self._last_calculated_selection" in CONTROLLER_SOURCE
    assert "self.stale_indicator.setVisible(stale)" in CONTROLLER_SOURCE
    assert "self._refresh_pair_controls(chart_ids)" in CONTROLLER_SOURCE


def test_reenabling_autocalculate_refreshes_for_every_selection_count():
    toggled_handler = CONTROLLER_SOURCE.split(
        "def _on_autocalculate_toggled", 1
    )[1].split("def calculate_pair_similarity", 1)[0]
    assert "if len(chart_ids)" not in toggled_handler
    assert "self._guarded_update_analysis(chart_ids)" in CONTROLLER_SOURCE
