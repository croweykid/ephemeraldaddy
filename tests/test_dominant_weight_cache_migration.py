import sqlite3

from ephemeraldaddy.core import db


def test_schema_v14_clears_cached_dominant_weights_for_formula_change():
    conn = sqlite3.connect(":memory:")
    db._create_charts_table(conn)
    conn.execute("PRAGMA user_version = 13")
    conn.execute(
        """
        INSERT INTO charts (
            name,
            datetime_iso,
            lat,
            lon,
            created_at,
            dominant_sign_weights,
            dominant_planet_weights,
            dominant_nakshatra_weights
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Cached Chart",
            "2000-01-01T00:00:00+00:00",
            0.0,
            0.0,
            "2026-05-14T00:00:00+00:00",
            '{"Scorpio": 1.0}',
            '{"Moon": 1.0}',
            '{"Anuradha": 1.0}',
        ),
    )

    db._ensure_schema(conn)

    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    cached_weights = conn.execute(
        """
        SELECT dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights
        FROM charts
        WHERE name = ?
        """,
        ("Cached Chart",),
    ).fetchone()

    assert user_version == db.SCHEMA_VERSION
    assert cached_weights == ("", "", "")
