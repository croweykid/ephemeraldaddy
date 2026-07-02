import sqlite3
from datetime import datetime, timezone

import ephemeraldaddy.core.db as db


def _insert_chart(conn: sqlite3.Connection) -> tuple[int, str]:
    chart_uid = "TRAITUID0000001"
    cur = conn.execute(
        """
        INSERT INTO charts (
            chart_uid, name, birth_place, datetime_iso, lat, lon, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chart_uid,
            "Trait Chart",
            "New York, USA",
            "2000-01-01T12:00:00+00:00",
            40.7128,
            -74.0060,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    return int(cur.lastrowid), chart_uid


def test_get_chart_trait_metadata_returns_mapping_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")

    conn = db._get_conn()
    with conn:
        _chart_id, chart_uid = _insert_chart(conn)
    conn.close()

    db.upsert_chart_trait_metadata(
        chart_uid,
        [
            {
                "trait_name": "Adventurous",
                "direction": "above",
                "likelihood": 0.75,
                "db_average": 0.5,
                "deviation": 0.25,
            }
        ],
        trait_signature="trait-signature",
        norm_signature="norm-signature",
        chart_signature="chart-signature",
    )

    rows = db.get_chart_trait_metadata(chart_uid)

    assert rows == [
        {
            "trait_name": "Adventurous",
            "direction": "above",
            "likelihood": 0.75,
            "db_average": 0.5,
            "deviation": 0.25,
            "trait_signature": "trait-signature",
            "norm_signature": "norm-signature",
            "chart_signature": "chart-signature",
            "updated_at": rows[0]["updated_at"],
        }
    ]


def test_chart_trait_metadata_migrates_legacy_chart_id_rows_to_uid(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")

    conn = db._get_conn()
    with conn:
        chart_id, chart_uid = _insert_chart(conn)
        conn.execute("DROP TABLE chart_trait_metadata")
        conn.execute(
            """
            CREATE TABLE chart_trait_metadata (
                chart_id          INTEGER NOT NULL,
                trait_name        TEXT NOT NULL,
                direction         TEXT NOT NULL,
                likelihood        REAL NOT NULL,
                db_average        REAL NOT NULL,
                deviation         REAL NOT NULL,
                trait_signature   TEXT NOT NULL,
                norm_signature    TEXT NOT NULL,
                updated_at        TEXT NOT NULL,
                PRIMARY KEY (chart_id, trait_name)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO chart_trait_metadata (
                chart_id, trait_name, direction, likelihood, db_average,
                deviation, trait_signature, norm_signature, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chart_id, "Grounded", "below", 44.0, 50.0, -6.0, "old-traits", "old-norm", "2026-01-01T00:00:00"),
        )
        db._create_chart_trait_metadata_table(conn)
    conn.close()

    assert db.get_chart_trait_metadata(chart_uid)[0]["trait_name"] == "Grounded"


def test_list_charts_exposes_chart_uid_for_uid_based_cache_signatures(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")

    conn = db._get_conn()
    with conn:
        _chart_id, chart_uid = _insert_chart(conn)
    conn.close()

    rows = db.list_charts()

    assert rows[0][-1] == chart_uid
