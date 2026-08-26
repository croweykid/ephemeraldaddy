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
    assert "self.stale_indicator.setVisible(True)" in CONTROLLER_SOURCE


def test_reenabling_autocalculate_only_immediately_runs_for_multiple_charts():
    assert "if len(chart_ids) > 1:" in CONTROLLER_SOURCE
    assert "self._guarded_update_analysis(chart_ids)" in CONTROLLER_SOURCE
