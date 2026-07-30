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
    assert 'display_body = "Midhaven" if body == "MC" else body' in DIALOGUES_SOURCE
    assert "candidate_datetimes=refinement_candidates" in DIALOGUES_SOURCE


def test_selected_match_opens_as_unknown_time_with_rectification_range():
    assert "self.time_unknown_checkbox.setChecked(True)" in APP_SOURCE
    assert "self.retcon_time_checkbox.setChecked(False)" in APP_SOURCE
    assert "self.rectification_range_checkbox.setChecked(True)" in APP_SOURCE
    assert "self.rectification_range_start_edit.setTime" in APP_SOURCE
    assert "self.rectification_range_end_edit.setTime" in APP_SOURCE
