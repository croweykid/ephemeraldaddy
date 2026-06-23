import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from ephemeraldaddy.core import backups
from ephemeraldaddy.core import db


def _sqlite(path: Path, table: str, value: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(f"CREATE TABLE {table} (value TEXT)")
        conn.execute(f"INSERT INTO {table} (value) VALUES (?)", (value,))


def _read_sqlite_value(path: Path, table: str) -> str:
    with sqlite3.connect(path) as conn:
        row = conn.execute(f"SELECT value FROM {table}").fetchone()
    return row[0]


@pytest.fixture
def package_paths(tmp_path, monkeypatch):
    db_dir = tmp_path / "data"
    db_dir.mkdir()
    paths = {
        "charts": db_dir / "charts.db",
        "photo_gallery": db_dir / "charts.photo_gallery.db",
        "time_sensitivity": db_dir / "time_sensitivity.db",
        "personal_identifiers": db_dir / "charts.personal_identifiers.json",
    }
    monkeypatch.setattr(db, "DB_DIR", db_dir)
    monkeypatch.setattr(db, "DB_PATH", paths["charts"])
    monkeypatch.setattr(backups, "TIME_SENSITIVITY_DB_PATH", paths["time_sensitivity"])
    monkeypatch.setattr(backups, "photo_gallery_path", lambda: paths["photo_gallery"])
    monkeypatch.setattr(backups, "personal_identifiers_path", lambda: paths["personal_identifiers"])
    return paths


def test_create_backup_package_includes_known_sidecars(package_paths, tmp_path):
    _sqlite(package_paths["charts"], "charts", "chart")
    _sqlite(package_paths["photo_gallery"], "photos", "photo")
    _sqlite(package_paths["time_sensitivity"], "ranges", "range")
    package_paths["personal_identifiers"].write_text('{"1": {"emails": ["a@example.com"]}}', encoding="utf-8")

    destination = backups.create_backup_package(tmp_path / "full.edbackup")

    assert destination == tmp_path / "full.edbackup"
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "data/charts.db" in names
        assert "data/charts.photo_gallery.db" in names
        assert "data/time_sensitivity.db" in names
        assert "data/charts.personal_identifiers.json" in names
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

    assert manifest["format"] == backups.BACKUP_PACKAGE_FORMAT
    components = {entry["key"]: entry for entry in manifest["components"]}
    assert set(components) == {"charts", "photo_gallery", "time_sensitivity", "personal_identifiers"}
    assert all(entry["sha256"] for entry in components.values())
    assert all(entry["size_bytes"] > 0 for entry in components.values())


def test_create_backup_package_skips_missing_optional_components(package_paths, tmp_path):
    _sqlite(package_paths["charts"], "charts", "chart")

    destination = backups.create_backup_package(tmp_path / "minimal")

    assert destination == tmp_path / "minimal.edbackup"
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

    assert "data/charts.db" in names
    assert "data/charts.photo_gallery.db" not in names
    assert [entry["key"] for entry in manifest["components"]] == ["charts"]


def test_restore_backup_package_validates_checksum(package_paths, tmp_path):
    _sqlite(package_paths["charts"], "charts", "chart")
    destination = backups.create_backup_package(tmp_path / "full.edbackup")

    tampered = tmp_path / "tampered.edbackup"
    with zipfile.ZipFile(destination) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "data/charts.db":
                payload = b"not sqlite anymore"
            target.writestr(info, payload)

    with pytest.raises(ValueError, match="Checksum mismatch"):
        backups.restore_backup_package(tampered)


def test_restore_database_supports_full_package_and_legacy_db(package_paths, tmp_path):
    _sqlite(package_paths["charts"], "charts", "original")
    _sqlite(package_paths["photo_gallery"], "photos", "photo-original")
    package_paths["personal_identifiers"].write_text('{"old": true}', encoding="utf-8")
    package = backups.create_backup_package(tmp_path / "full.edbackup")

    package_paths["charts"].unlink()
    package_paths["photo_gallery"].unlink()
    package_paths["personal_identifiers"].unlink()
    _sqlite(package_paths["charts"], "charts", "new")

    db.restore_database(package)

    assert _read_sqlite_value(package_paths["charts"], "charts") == "original"
    assert _read_sqlite_value(package_paths["photo_gallery"], "photos") == "photo-original"
    assert json.loads(package_paths["personal_identifiers"].read_text(encoding="utf-8")) == {"old": True}

    legacy = tmp_path / "legacy.db"
    _sqlite(legacy, "charts", "legacy")
    db.restore_database(legacy)

    assert _read_sqlite_value(package_paths["charts"], "charts") == "legacy"
