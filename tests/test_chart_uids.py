import sqlite3
from datetime import datetime, timezone

import ephemeraldaddy.core.db as db


def _insert_minimal_chart(
    conn: sqlite3.Connection,
    *,
    chart_uid: str,
    name: str = "Chart",
    is_placeholder: bool = False,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO charts (
            chart_uid, name, birth_place, datetime_iso, lat, lon, is_placeholder, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chart_uid,
            name,
            "New York, USA",
            "2000-01-01T12:00:00+00:00",
            40.7128,
            -74.0060,
            1 if is_placeholder else 0,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    return int(cur.lastrowid)


def test_schema_backfills_unique_chart_uids_for_legacy_rows():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_place TEXT,
            datetime_iso TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    for name in ("One", "Two"):
        conn.execute(
            """
            INSERT INTO charts (name, birth_place, datetime_iso, lat, lon, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                "New York, USA",
                "2000-01-01T12:00:00+00:00",
                40.7128,
                -74.0060,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )

    db._ensure_schema(conn)

    columns = db._table_columns(conn, "charts")
    rows = conn.execute("SELECT chart_uid FROM charts ORDER BY id ASC").fetchall()
    assert "chart_uid" in columns
    assert len({row[0] for row in rows}) == 2
    assert all(isinstance(row[0], str) and len(row[0]) >= 8 for row in rows)


def test_append_database_preserves_non_colliding_source_chart_uid(tmp_path, monkeypatch):
    target_path = tmp_path / "target.db"
    source_path = tmp_path / "source.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", target_path)

    target_conn = db._get_conn()
    with target_conn:
        _insert_minimal_chart(target_conn, chart_uid="TARGETUID0000001", name="Target")
    target_conn.close()

    source_conn = sqlite3.connect(source_path)
    db._ensure_schema(source_conn)
    with source_conn:
        _insert_minimal_chart(source_conn, chart_uid="SOURCEUID0000001", name="Source")
    source_conn.close()

    result = db.append_database(source_path)

    assert result["imported"] == 1
    target_conn = sqlite3.connect(target_path)
    rows = target_conn.execute("SELECT name, chart_uid FROM charts ORDER BY id ASC").fetchall()
    target_conn.close()
    assert ("Source", "SOURCEUID0000001") in rows


def test_append_database_regenerates_colliding_source_chart_uid(tmp_path, monkeypatch):
    target_path = tmp_path / "target.db"
    source_path = tmp_path / "source.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", target_path)

    target_conn = db._get_conn()
    with target_conn:
        _insert_minimal_chart(target_conn, chart_uid="SHAREDUID0000001", name="Target")
    target_conn.close()

    source_conn = sqlite3.connect(source_path)
    db._ensure_schema(source_conn)
    with source_conn:
        _insert_minimal_chart(source_conn, chart_uid="SHAREDUID0000001", name="Source")
    source_conn.close()

    result = db.append_database(source_path)

    assert result["imported"] == 1
    assert result["warnings"] >= 1
    assert any("UID collided" in issue.get("error", "") for issue in result["issues"])
    target_conn = sqlite3.connect(target_path)
    rows = target_conn.execute("SELECT name, chart_uid FROM charts ORDER BY id ASC").fetchall()
    target_conn.close()
    source_uid = dict(rows)["Source"]
    assert source_uid != "SHAREDUID0000001"
    assert len(source_uid) >= 8


def test_load_chart_keeps_chart_uid_projection_aligned(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    with conn:
        chart_id = _insert_minimal_chart(
            conn,
            chart_uid="LOADUID00000001",
            name="Loadable",
            is_placeholder=True,
        )
    conn.close()

    chart = db.load_chart(chart_id)

    assert chart.chart_uid == "LOADUID00000001"
    assert chart.name == "Loadable"


def test_load_charts_batches_chart_reconstruction(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    with conn:
        first_id = _insert_minimal_chart(
            conn,
            chart_uid="BATCHUID0000001",
            name="First",
            is_placeholder=True,
        )
        second_id = _insert_minimal_chart(
            conn,
            chart_uid="BATCHUID0000002",
            name="Second",
            is_placeholder=True,
        )
    conn.close()

    charts_by_id = db.load_charts([first_id, second_id, first_id])

    assert list(charts_by_id) == [first_id, second_id]
    assert charts_by_id[first_id].chart_uid == "BATCHUID0000001"
    assert charts_by_id[second_id].name == "Second"


def test_uid_native_chart_lookup_and_loading(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    with conn:
        first_id = _insert_minimal_chart(
            conn,
            chart_uid="UIDLOOKUP000001",
            name="UID Lookup One",
            is_placeholder=True,
        )
        second_id = _insert_minimal_chart(
            conn,
            chart_uid="UIDLOOKUP000002",
            name="UID Lookup Two",
            is_placeholder=True,
        )
    conn.close()

    assert db.get_chart_id_by_uid("uidlookup000001") == first_id
    assert db.get_chart_ids_by_uid(["uidlookup000001", None, "UIDLOOKUP000002"]) == {
        "UIDLOOKUP000001": first_id,
        "UIDLOOKUP000002": second_id,
    }

    chart = db.load_chart_by_uid("uidlookup000001")
    charts_by_uid = db.load_charts_by_uids(["uidlookup000002", "uidlookup000001", "uidlookup000002"])

    assert chart.name == "UID Lookup One"
    assert chart.chart_uid == "UIDLOOKUP000001"
    assert list(charts_by_uid) == ["UIDLOOKUP000002", "UIDLOOKUP000001"]
    assert charts_by_uid["UIDLOOKUP000002"].name == "UID Lookup Two"


def test_uid_native_update_and_delete_bridge_to_existing_id_storage(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    with conn:
        first_id = _insert_minimal_chart(
            conn,
            chart_uid="UIDUPDATE000001",
            name="Before Update",
            is_placeholder=True,
        )
        second_id = _insert_minimal_chart(
            conn,
            chart_uid="UIDUPDATE000002",
            name="Delete Me",
            is_placeholder=True,
        )
        conn.execute(
            """
            INSERT INTO duplicate_exclusions (chart_id_low, chart_id_high, created_at)
            VALUES (?, ?, ?)
            """,
            (first_id, second_id, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    conn.close()

    chart = db.load_chart_by_uid("UIDUPDATE000001")
    chart.name = "After Update"
    db.update_chart_by_uid("uidupdate000001", chart, birth_place="New York, USA")

    assert db.load_chart(first_id).name == "After Update"
    assert db.load_chart_by_uid("UIDUPDATE000001").chart_uid == "UIDUPDATE000001"
    assert db.list_duplicate_exclusion_uids() == {("UIDUPDATE000001", "UIDUPDATE000002")}

    deleted = db.delete_charts_by_uids(["uidupdate000002", "unknown"])

    assert deleted == 1
    assert db.get_chart_id_by_uid("UIDUPDATE000002") is None
    assert db.list_duplicate_exclusions() == set()
    assert db.list_duplicate_exclusion_uids() == set()


def test_list_charts_projection_stays_aligned(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    with conn:
        chart_id = _insert_minimal_chart(
            conn,
            chart_uid="LISTUID00000001",
            name="Listed",
            is_placeholder=True,
        )
    conn.close()

    rows = db.list_charts()

    assert len(rows) == 1
    assert rows[0][0] == chart_id
    assert rows[0][1] == "Listed"
    assert rows[0][15] == 1


def test_table_column_cache_refreshes_when_active_schema_changes(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    db.ensure_db_ready_once()
    conn = db._get_conn()
    try:
        assert "cache_probe" not in db._table_columns(conn, "charts")
        conn.execute("ALTER TABLE charts ADD COLUMN cache_probe TEXT")
        conn.commit()
        assert "cache_probe" in db._table_columns(conn, "charts")
    finally:
        conn.close()


def test_table_column_cache_does_not_leak_to_external_database(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    source_path = tmp_path / "source.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    db.ensure_db_ready_once()
    active_conn = db._get_conn()
    try:
        assert "chart_uid" in db._table_columns(active_conn, "charts")
    finally:
        active_conn.close()

    source_conn = sqlite3.connect(source_path)
    try:
        source_conn.execute("CREATE TABLE charts (id INTEGER PRIMARY KEY, external_only TEXT)")
        source_columns = db._table_columns(source_conn, "charts")
    finally:
        source_conn.close()

    assert source_columns == {"id", "external_only"}
