from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")


def _app_source() -> str:
    return APP_SOURCE.read_text(encoding="utf-8")


def test_death_time_defaults_to_unknown_in_chart_editor() -> None:
    source = _app_source()

    assert 'self.death_time_unknown_checkbox = QCheckBox("Unknown")' in source
    assert source.count("self.death_time_unknown_checkbox.setChecked(True)") >= 3
    assert "self.death_time_unknown_checkbox.setChecked(False)" not in source


def test_unknown_death_time_hides_time_input_like_unknown_birth_time() -> None:
    source = _app_source()

    assert "def _update_death_time_input_visibility(" in source
    assert "self._update_death_time_input_visibility\n" in source
    assert "not self.death_time_unknown_checkbox.isChecked()" in source
    assert "self.death_time_unknown_checkbox.toggled.connect(\n" in source
    assert "self.death_time_edit.setDisabled" not in source
