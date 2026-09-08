from pathlib import Path
import sqlite3

from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart_data_fields import NONASTRAL_DATA


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fresh_database(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")
    monkeypatch.setattr(db, "_SCHEMA_READY", False)
    monkeypatch.setattr(db, "_SCHEMA_READY_DB_PATH", None)
    monkeypatch.setattr(db, "_AUTO_BACKUP_CREATED", True)
    connection = sqlite3.connect(db.DB_PATH)
    db._create_charts_table(connection)
    connection.close()


def test_cultural_contribution_is_nullable_nonastral_metadata(monkeypatch, tmp_path):
    _fresh_database(monkeypatch, tmp_path)
    columns = {
        row[1]: row for row in db._get_conn().execute("PRAGMA table_info(charts)").fetchall()
    }
    assert "cultural_contribution_score" in NONASTRAL_DATA
    assert columns["cultural_contribution_score"][3] == 0


def test_cultural_contribution_batch_patch_persists_by_uid(monkeypatch, tmp_path):
    _fresh_database(monkeypatch, tmp_path)
    connection = db._get_conn()
    connection.execute(
        "INSERT INTO charts (chart_uid, name, datetime_iso, lat, lon, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("CULTUREUID0000001", "Ada", "1815-12-10T12:00:00+00:00", 0.0, 0.0, "2026-01-01T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()

    changed = db.update_charts_nonastral_fields_by_uid(
        ["CULTUREUID0000001"], {"cultural_contribution_score": 9}
    )

    assert changed == {"CULTUREUID0000001"}
    row = db._get_conn().execute(
        "SELECT cultural_contribution_score FROM charts WHERE chart_uid = ?", ("CULTUREUID0000001",)
    ).fetchone()
    assert row[0] == 9
    chart_id = db._get_conn().execute(
        "SELECT id FROM charts WHERE chart_uid = ?", ("CULTUREUID0000001",)
    ).fetchone()[0]
    assert db.load_chart(chart_id).cultural_contribution_score == 9


def test_chart_editor_and_batch_editor_expose_cultural_contribution_controls():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    panel_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert 'title="Cultural Contribution"' in panel_source
    assert "Regardless of morality or caveats" in panel_source
    assert "Is/was this a 'useful' entity, in your opinion?" in panel_source
    assert '"Perceived Cultural Contributions"' in app_source
    assert '{"cultural_contribution_score": value}' in app_source
