from pathlib import Path

from ephemeraldaddy.core import db


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_sexiness_score_normalizes_to_signed_slider_range():
    assert db._normalize_sexiness_score(None) == 0
    assert db._normalize_sexiness_score("whatever") == 0
    assert db._normalize_sexiness_score(-99) == -10
    assert db._normalize_sexiness_score(7) == 7
    assert db._normalize_sexiness_score(99) == 10


def test_chart_view_sexiness_slider_lives_with_alignment_panel_source():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "self.sexiness_slider = AlignmentEmojiSlider()" in source
    controller_source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert "owner.sexiness_section_box = sexiness_box" in controller_source
    assert "chart.sexiness_score = 0 if is_event_chart else self.sexiness_slider.value()" in source


def test_sexiness_score_is_chart_metadata_in_db_source():
    source = (REPO_ROOT / "ephemeraldaddy/core/db.py").read_text()

    assert "sexiness_score INTEGER NOT NULL DEFAULT 0" in source
    assert "ADD COLUMN sexiness_score INTEGER NOT NULL DEFAULT 0" in source
    assert "chart.sexiness_score = _normalize_sexiness_score(sexiness_score)" in source


def test_sexiness_module_is_hidden_by_default_and_configurable():
    visibility_source = (REPO_ROOT / "ephemeraldaddy/gui/visibility.py").read_text()
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "\"chart_view.sexiness\": False" in visibility_source
    assert "Show Sexiness (Subjective Notes)" in app_source
    assert "def _sync_chart_view_sexiness_visibility" in app_source


def test_chart_view_resets_sexiness_before_loading_chart_metadata():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "self._set_sexiness_score_state(0)\n        self._set_sexiness_score_state(getattr(chart, \"sexiness_score\", 0) or 0)" in source
    assert "self.chart_info_output.clear()\n        self._set_sexiness_score_state(0)" in source
