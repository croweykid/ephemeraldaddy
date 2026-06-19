from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core import db


def _use_temp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")


def _chart(name: str) -> Chart:
    chart = Chart(name, datetime(1990, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")), 0.0, 0.0)
    chart.birth_place = "UTC"
    return chart


def test_reminds_me_of_resolves_name_to_stable_chart_uid(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    source_id = db.save_chart(_chart("Original Name"), birth_place="UTC")
    source_uid = db.get_chart_uid(source_id)

    assert db.find_chart_uid_by_name("original name") == source_uid

    related = _chart("Related")
    related.reminds_me_of = db.find_chart_uid_by_name("Original Name")
    related_id = db.save_chart(related, birth_place="UTC")

    loaded_related = db.load_chart(related_id)
    assert loaded_related.reminds_me_of == source_uid
    assert db.get_chart_display_name_by_uid(loaded_related.reminds_me_of) == "Original Name"

    source = db.load_chart(source_id)
    source.name = "Renamed Chart"
    db.update_chart(source_id, source, birth_place="UTC")

    assert db.load_chart(related_id).reminds_me_of == source_uid
    assert db.get_chart_display_name_by_uid(source_uid) == "Renamed Chart"
