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


def test_cultural_contribution_controls_live_in_workflow_modules():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    chart_editor_source = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/chart_editor/cultural_contribution.py"
    ).read_text()
    batch_editor_source = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/database_view/batch_editor/cultural_contribution.py"
    ).read_text()
    chart_panel_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert 'title="Cultural Contribution"' in chart_panel_source
    assert '"Perceived Cultural Contributions"' in app_source
    assert "Regardless of morality or caveats" in chart_editor_source
    assert "Is/was this a 'useful' entity, in your opinion?" in chart_editor_source
    assert '{"cultural_contribution_score": value}' in batch_editor_source
    assert "def _on_batch_cultural_contribution_apply" not in app_source
    assert "def _on_cultural_contribution_changed" not in app_source


def test_controller_exists_before_initial_caption_refresh():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    initialization = app_source.split("class MainWindow", 1)[1].split(
        "def _adjust_window_for_available_screen", 1
    )[0]

    controller_index = initialization.index(
        "self.cultural_contribution_controller = CulturalContributionController("
    )
    caption_refresh_index = initialization.index(
        "self._update_observations_relationship_subheaders()"
    )
    assert controller_index < caption_refresh_index


def test_event_conversion_clears_cultural_contribution_state():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    clear_event = app_source.split("def _clear_event_metadata_fields", 1)[1].split(
        "def _apply_chart_type_ui_state", 1
    )[0]

    assert "self.cultural_contribution_controller.clear()" in clear_event


def test_batch_refresh_reuses_already_resolved_charts():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    batch_editor_source = (
        REPO_ROOT
        / "ephemeraldaddy/gui/features/database_view/batch_editor/cultural_contribution.py"
    ).read_text()

    assert "chart for _chart_id, chart in resolved_items" in app_source
    assert "def refresh(self, charts: Iterable[Any])" in batch_editor_source
    assert "chart_for_uid" not in batch_editor_source
