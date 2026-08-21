from __future__ import annotations

from ephemeraldaddy.core import db


def _use_temp_database(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")
    monkeypatch.setattr(db, "_SCHEMA_READY", False)
    monkeypatch.setattr(db, "_SCHEMA_READY_DB_PATH", None)
    monkeypatch.setattr(db, "_AUTO_BACKUP_CREATED", True)
    db.init_db_once(force=True)


def test_chart_change_log_records_only_ranking_relevant_changes(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    conn = db._get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO charts(chart_uid, name, datetime_iso, lat, lon, created_at)
            VALUES('UID-ONE', 'Original', '2000-01-01T12:00:00+00:00', 1.0, 2.0, '2026-01-01T00:00:00Z')
            """
        )
    conn.close()
    added_sequence = db.latest_chart_change_sequence()
    added = db.chart_changes_since(0)
    assert [change["change_type"] for change in added] == ["added"]
    assert added[0]["session_id"] == db._DB_SESSION_ID

    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET comments = 'display only' WHERE chart_uid = 'UID-ONE'")
    conn.close()
    assert db.chart_changes_since(added_sequence) == []

    conn = db._get_conn()
    with conn:
        conn.execute(
            "UPDATE charts SET datetime_iso = '2000-01-01T13:00:00+00:00' WHERE chart_uid = 'UID-ONE'"
        )
    conn.close()
    edited = db.chart_changes_since(added_sequence)
    assert len(edited) == 1
    assert edited[0]["chart_uid"] == "UID-ONE"
    assert edited[0]["change_type"] == "astro_data_edited"
    assert edited[0]["changed_at"]

    edited_sequence = edited[0]["sequence"]
    conn = db._get_conn()
    with conn:
        conn.execute("DELETE FROM charts WHERE chart_uid = 'UID-ONE'")
    conn.close()
    deleted = db.chart_changes_since(edited_sequence)
    assert len(deleted) == 1
    assert deleted[0]["change_type"] == "deleted"
