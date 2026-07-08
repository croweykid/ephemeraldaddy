from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO_ROOT / "ephemeraldaddy/gui/app.py"


def _method_source(name: str, *, end: str | None = None) -> str:
    source = APP_SOURCE.read_text()
    start = source.index(f"    def {name}")
    if end is None:
        stop = source.index("\n    def ", start + 1)
    else:
        stop = source.index(f"    def {end}", start)
    return source[start:stop]


def test_rectification_range_midpoint_is_only_used_when_effective():
    build_method = _method_source("_build_chart_from_inputs")

    assert "elif self._rectification_range_effective_from_inputs():" in build_method
    assert "qtime = self._rectification_range_midpoint_qtime()" in build_method
    assert "chart.rectification_range_used = self._rectification_range_effective_from_inputs()" in build_method


def test_rectification_range_visibility_clears_unavailable_range():
    method = _method_source("_update_time_input_visibility")

    assert "range_available = (" in method
    assert "self.time_unknown_checkbox.isChecked()" in method
    assert "not self.retcon_time_checkbox.isChecked()" in method
    assert "self.rectification_range_checkbox.setChecked(False)" in method
    assert "self.rectification_range_checkbox.setEnabled(range_available)" in method


def test_load_chart_restores_retcon_checkbox_before_range_checkbox():
    method = _method_source("load_chart_by_id")

    retcon_restore = "self.retcon_time_checkbox.setChecked(chart.retcon_time_used)"
    range_restore = "self.rectification_range_checkbox.setChecked("

    assert retcon_restore in method
    assert range_restore in method
    assert method.index(retcon_restore) < method.index(range_restore)
