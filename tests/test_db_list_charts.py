from datetime import datetime, timezone

import ephemeraldaddy.core.db as db


def test_list_charts_returns_saved_chart_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = db._get_conn()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """
            INSERT INTO charts (
                name,
                alias,
                gender,
                datetime_iso,
                birth_place,
                lat,
                lon,
                created_at,
                chart_type,
                birth_month,
                birth_day,
                birth_year
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Example Chart",
                "Example Alias",
                "unknown",
                "2000-01-01T12:00:00+00:00",
                "New York, USA",
                40.7128,
                -74.0060,
                created_at,
                db.CHART_TYPE_PERSONAL,
                1,
                1,
                2000,
            ),
        )
    conn.close()

    rows = db.list_charts()

    assert len(rows) == 1
    row = rows[0]
    assert row[1] == "Example Chart"
    assert row[2] == "Example Alias"
    assert row[14] == db.CHART_TYPE_PERSONAL
    assert row[17:] == (1, 1, 2000)
