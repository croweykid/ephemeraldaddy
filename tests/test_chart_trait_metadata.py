import sqlite3
from datetime import datetime, timezone

import ephemeraldaddy.core.db as db


def _insert_chart(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        INSERT INTO charts (
            chart_uid, name, birth_place, datetime_iso, lat, lon, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TRAITUID0000001",
            "Trait Chart",
            "New York, USA",
            "2000-01-01T12:00:00+00:00",
            40.7128,
            -74.0060,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    return int(cur.lastrowid)


def test_get_chart_trait_metadata_returns_mapping_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")

    conn = db._get_conn()
    with conn:
        chart_id = _insert_chart(conn)
    conn.close()

    db.upsert_chart_trait_metadata(
        chart_id,
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
    )

    rows = db.get_chart_trait_metadata(chart_id)

    assert rows == [
        {
            "trait_name": "Adventurous",
            "direction": "above",
            "likelihood": 0.75,
            "db_average": 0.5,
            "deviation": 0.25,
            "trait_signature": "trait-signature",
            "norm_signature": "norm-signature",
            "updated_at": rows[0]["updated_at"],
        }
    ]
