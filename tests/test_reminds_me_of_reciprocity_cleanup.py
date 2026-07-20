from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core import db
from ephemeraldaddy.core.reminds_me_of_reciprocity_cleanup import (
    ensure_existing_reminds_me_of_reciprocity,
)


def _use_temp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")


def _chart(name: str) -> Chart:
    chart = Chart(name, datetime(1990, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")), 0.0, 0.0)
    chart.birth_place = "UTC"
    return chart


def test_cleanup_adds_missing_reverse_reminds_me_of_links(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    first_id = db.save_chart(_chart("First"), birth_place="UTC")
    second_id = db.save_chart(_chart("Second"), birth_place="UTC")
    third_id = db.save_chart(_chart("Third"), birth_place="UTC")
    first_uid = db.get_chart_uid(first_id)
    second_uid = db.get_chart_uid(second_id)
    third_uid = db.get_chart_uid(third_id)

    conn = db._get_conn()
    with conn:
        conn.execute(
            "UPDATE charts SET reminds_me_of = ? WHERE id = ?",
            (db.serialize_reminds_me_of_uids([second_uid, third_uid]), first_id),
        )
        conn.execute(
            "UPDATE charts SET reminds_me_of = ? WHERE id = ?",
            (db.serialize_reminds_me_of_uids([first_uid]), third_id),
        )
    conn.close()

    report = ensure_existing_reminds_me_of_reciprocity()

    assert report.charts_scanned == 3
    assert report.charts_updated == 1
    assert report.reciprocal_links_added == 1
    assert db.parse_reminds_me_of_uids(db.load_chart(second_id).reminds_me_of) == [first_uid]
    assert db.parse_reminds_me_of_uids(db.load_chart(third_id).reminds_me_of) == [first_uid]
