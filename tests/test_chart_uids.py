import sqlite3
from datetime import datetime, timezone

import ephemeraldaddy.core.db as db


def _insert_minimal_chart(conn: sqlite3.Connection, *, chart_uid: str, name: str = "Chart") -> int:
    cur = conn.execute(
        """
        INSERT INTO charts (chart_uid, name, birth_place, datetime_iso, lat, lon, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chart_uid,
            name,
            "New York, USA",
            "2000-01-01T12:00:00+00:00",
            40.7128,
            -74.0060,
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
