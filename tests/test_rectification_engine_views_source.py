from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIALOGUES_SOURCE = (ROOT / "ephemeraldaddy/gui/features/dialogues.py").read_text()
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_rectification_engine_codifies_all_three_views():
    assert "class RectificationView(Enum):" in DIALOGUES_SOURCE
    assert 'CRITERIA = "criteria"' in DIALOGUES_SOURCE
    assert 'RESULTS = "results"' in DIALOGUES_SOURCE
    assert 'REFINEMENT = "refinement"' in DIALOGUES_SOURCE


def test_house_refinement_is_scoped_to_current_results():
    assert 'QPushButton("Refine by House Placement")' in DIALOGUES_SOURCE
    assert 'header = QLabel("H")' in DIALOGUES_SOURCE
    assert 'QLabel("Midhaven" if body == "MC" else body)' in DIALOGUES_SOURCE
    assert "candidate_windows=refinement_windows" in DIALOGUES_SOURCE
    assert "self._ensure_refinement_angle_widgets()" in DIALOGUES_SOURCE
    assert "self._remove_refinement_angle_widgets()" in DIALOGUES_SOURCE
    assert '[("12 hrs", 720), ("1 day", 1440)]' in DIALOGUES_SOURCE
    for option in [
        '("30 min", 30)',
        '("15 min", 15)',
        '("10 min", 10)',
        '("5 min", 5)',
        '("1 min", 1)',
    ]:
        assert option in DIALOGUES_SOURCE


def test_refinement_keeps_the_current_result_location():
    assert "self.place_edit.setEnabled(not refinement_visible)" in DIALOGUES_SOURCE
    assert (
        "Location is fixed to the current result set during refinement."
        in DIALOGUES_SOURCE
    )
    assert (
        "if refining and self._active_lat is not None and self._active_lon is not None:"
        in DIALOGUES_SOURCE
    )
    assert "lat = self._active_lat" in DIALOGUES_SOURCE
    assert "lon = self._active_lon" in DIALOGUES_SOURCE


def test_selected_match_opens_as_unknown_time_with_rectification_range():
    assert "self.time_unknown_checkbox.setChecked(True)" in APP_SOURCE
    assert "self.retcon_time_checkbox.setChecked(False)" in APP_SOURCE
    assert "self.rectification_range_checkbox.setChecked(True)" in APP_SOURCE
    assert "self.rectification_range_start_edit.setTime" in APP_SOURCE
    assert "self.rectification_range_end_edit.setTime" in APP_SOURCE
