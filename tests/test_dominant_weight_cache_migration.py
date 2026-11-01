import sqlite3

from ephemeraldaddy.core import db


def _insert_cached_chart(conn: sqlite3.Connection, name: str) -> None:
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
            name,
            "2000-01-01T00:00:00+00:00",
            0.0,
            0.0,
            "2026-05-14T00:00:00+00:00",
            '{"Scorpio": 1.0}',
            '{"Moon": 1.0}',
            '{"Anuradha": 1.0}',
        ),
    )


def _cached_weights(conn: sqlite3.Connection, name: str) -> tuple[str, str, str]:
    return conn.execute(
        """
        SELECT dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights
        FROM charts
        WHERE name = ?
        """,
        (name,),
    ).fetchone()


def test_schema_v14_clears_cached_dominant_weights_for_formula_change():
    conn = sqlite3.connect(":memory:")
    db._create_charts_table(conn)
    conn.execute("PRAGMA user_version = 13")
    _insert_cached_chart(conn, "Cached Chart")

    db._ensure_schema(conn)

    user_version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert user_version == db.SCHEMA_VERSION
    assert _cached_weights(conn, "Cached Chart") == ("", "", "")


def test_schema_v16_clears_cached_dominant_weights_for_sign_formula_change():
    conn = sqlite3.connect(":memory:")
    db._create_charts_table(conn)
    conn.execute("PRAGMA user_version = 15")
    _insert_cached_chart(conn, "Sign Formula Cache")

    db._ensure_schema(conn)

    user_version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert user_version == db.SCHEMA_VERSION
    assert _cached_weights(conn, "Sign Formula Cache") == ("", "", "")


def test_schema_v22_then_v23_invalidates_all_dominance_weights():
    conn = sqlite3.connect(":memory:")
    db._create_charts_table(conn)
    conn.execute("PRAGMA user_version = 21")
    _insert_cached_chart(conn, "Nakshatra Formula Cache")

    db._ensure_schema(conn)

    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert _cached_weights(conn, "Nakshatra Formula Cache") == ("", "", "")



def test_schema_v23_clears_all_stale_dominance_caches_but_not_positions():
    conn = sqlite3.connect(":memory:")
    db._create_charts_table(conn)
    conn.execute("PRAGMA user_version = 22")
    _insert_cached_chart(conn, "Legacy Mode")
    conn.execute(
        "UPDATE charts SET dominant_element_weights = ?, dominant_mode = ?, modal_distribution = ?, derived_positions = ?",
        ('{"Fire":2}', "fixed", '{"fixed":1}', '{"Mean Lilith":15}'),
    )
    db._ensure_schema(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 23
    assert _cached_weights(conn, "Legacy Mode") == ("", "", "")
    assert conn.execute(
        "SELECT dominant_element_weights, dominant_mode, modal_distribution, derived_positions FROM charts"
    ).fetchone() == ("", None, "", '{"Mean Lilith":15}')
