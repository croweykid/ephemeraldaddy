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


def test_multiple_reminds_me_of_uids_are_serialized_and_parsed(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    first_id = db.save_chart(_chart("First"), birth_place="UTC")
    second_id = db.save_chart(_chart("Second"), birth_place="UTC")
    first_uid = db.get_chart_uid(first_id)
    second_uid = db.get_chart_uid(second_id)

    related = _chart("Related")
    related.reminds_me_of = db.serialize_reminds_me_of_uids([first_uid, second_uid, first_uid])
    related_id = db.save_chart(related, birth_place="UTC")

    loaded_related = db.load_chart(related_id)
    assert db.parse_reminds_me_of_uids(loaded_related.reminds_me_of) == [first_uid, second_uid]


def test_append_database_preserves_multiple_reminds_me_of_uids(monkeypatch, tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", source_path)
    source_id = db.save_chart(_chart("Source"), birth_place="UTC")
    other_id = db.save_chart(_chart("Other Source"), birth_place="UTC")
    source_uid = db.get_chart_uid(source_id)
    other_uid = db.get_chart_uid(other_id)
    related = _chart("Related")
    related.reminds_me_of = db.serialize_reminds_me_of_uids([source_uid, other_uid])
    db.save_chart(related, birth_place="UTC")

    monkeypatch.setattr(db, "DB_PATH", target_path)
    target_existing_id = db.save_chart(_chart("Target Existing"), birth_place="UTC")
    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET chart_uid = ? WHERE id = ?", (source_uid, target_existing_id))
    conn.close()

    result = db.append_database(source_path)

    assert result["imported"] == 3
    imported_source_uid = db.find_chart_uid_by_name("Source")
    imported_other_uid = db.find_chart_uid_by_name("Other Source")
    imported_related = next(
        chart
        for chart_id, name, *_rest in db.list_charts()
        if name == "Related"
        for chart in [db.load_chart(chart_id)]
    )
    assert db.parse_reminds_me_of_uids(imported_related.reminds_me_of) == [
        imported_source_uid,
        imported_other_uid,
    ]
    assert source_uid not in db.parse_reminds_me_of_uids(imported_related.reminds_me_of)
