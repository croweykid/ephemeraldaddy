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
    assert "alignment_content_layout.addWidget(QLabel(\"Sexiness\"))" in source
    assert "chart.sexiness_score = 0 if is_event_chart else self.sexiness_slider.value()" in source


def test_sexiness_score_is_chart_metadata_in_db_source():
    source = (REPO_ROOT / "ephemeraldaddy/core/db.py").read_text()

    assert "sexiness_score INTEGER NOT NULL DEFAULT 0" in source
    assert "ADD COLUMN sexiness_score INTEGER NOT NULL DEFAULT 0" in source
    assert "chart.sexiness_score = _normalize_sexiness_score(sexiness_score)" in source
