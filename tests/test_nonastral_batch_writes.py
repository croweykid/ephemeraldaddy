import sqlite3

import pytest

from ephemeraldaddy.core import db


def _database(tmp_path, monkeypatch):
    path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", path)
    connection = sqlite3.connect(path)
    db._create_charts_table(connection)
    with connection:
        connection.execute(
            """
            INSERT INTO charts (
                chart_uid, name, datetime_iso, lat, lon, created_at,
                dominant_sign_weights, human_design_type, bazi_day_pillar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "NONASTRAL0000001",
                "Before",
                "2000-01-01T12:00:00+00:00",
                1.0,
                2.0,
                "2026-01-01T00:00:00+00:00",
                '{"Aries": 1.0}',
                "Generator",
                "Wood Dragon",
            ),
        )
    connection.close()
    return path


def test_general_nonastral_patch_preserves_astro_and_derived_data(tmp_path, monkeypatch):
    path = _database(tmp_path, monkeypatch)
    changed = db.update_charts_nonastral_fields_by_uid(
        {"NONASTRAL0000001"},
        {
            "familiarity": 7,
            "familiarity_factors": ["frequent contact", "shared history"],
            "gender": "nonbinary",
        },
    )
    assert changed == {"NONASTRAL0000001"}
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT familiarity, familiarity_factors, gender,
                   dominant_sign_weights, human_design_type, bazi_day_pillar
            FROM charts WHERE chart_uid = ?
            """,
            ("NONASTRAL0000001",),
        ).fetchone()
    assert row == (
        7,
        "frequent contact, shared history",
        "nonbinary",
        '{"Aries": 1.0}',
        "Generator",
        "Wood Dragon",
    )


def test_general_nonastral_patch_rejects_astro_and_protected_fields(tmp_path, monkeypatch):
    _database(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        db.update_charts_nonastral_fields_by_uid(
            {"NONASTRAL0000001"}, {"birth_place": "Elsewhere"}
        )
    with pytest.raises(ValueError):
        db.update_charts_nonastral_fields_by_uid(
            {"NONASTRAL0000001"}, {"chart_uid": "REPLACEMENT00001"}
        )
