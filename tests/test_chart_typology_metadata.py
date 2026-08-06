from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.chart_data_fields import NONASTRAL_DATA


def test_typology_metadata_defaults_and_nonastral_classification():
    chart = Chart("Defaults", datetime(2000, 1, 1, 12), 0.0, 0.0, tz=ZoneInfo("UTC"))

    assert chart.enneagram_type == ["0", "0"]
    assert chart.tritype == [0, 0, 0]
    assert chart.mbti == ["?", "?", "?", "?"]
    assert {"enneagram_type", "tritype", "mbti"} <= NONASTRAL_DATA


def test_typology_metadata_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")
    chart = Chart("Typed", datetime(2000, 1, 1, 12), 0.0, 0.0, tz=ZoneInfo("UTC"))
    chart.enneagram_type = ["5", "4"]
    chart.tritype = [5, 9, 2]
    chart.mbti = ["I", "N", "f", "J"]

    chart_id = db.save_chart(chart, birth_place="UTC")
    loaded = db.load_chart(chart_id)

    assert loaded.enneagram_type == ["5", "4"]
    assert loaded.tritype == [5, 9, 2]
    assert loaded.mbti == ["I", "N", "f", "J"]


def test_observations_layout_places_emoji_portrait_after_reminds_me_of():
    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    start = source.index("        reminds_me_of_box = QFrame()")
    end = source.index("        sentiment_metrics_row = QWidget()", start)
    section = source[start:end]

    assert section.index("sentiment_relation_layout.addWidget(reminds_me_of_box)") < section.index(
        "setup_chart_view_emoji_portrait_section(self, sentiment_relation_layout)"
    )
