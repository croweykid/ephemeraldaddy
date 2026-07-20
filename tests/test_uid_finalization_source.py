from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
DB_SOURCE = (REPO_ROOT / "ephemeraldaddy/core/db.py").read_text()


def _method_source(source: str, name: str) -> str:
    start = source.index(f"def {name}")
    next_def = source.find("\ndef ", start + 1)
    next_class = source.find("\nclass ", start + 1)
    candidates = [index for index in (next_def, next_class) if index != -1]
    end = min(candidates) if candidates else len(source)
    return source[start:end]


def _indented_method_source(source: str, name: str) -> str:
    start = source.index(f"    def {name}")
    next_method = source.find("\n    def ", start + 1)
    end = next_method if next_method != -1 else len(source)
    return source[start:end]


def test_uid_finalization_migration_is_schema_versioned_and_marked():
    assert "SCHEMA_VERSION = 20" in DB_SOURCE
    assert 'UID_FINALIZATION_MIGRATION_KEY = "chart_uid_finalization_v1"' in DB_SOURCE
    assert "CREATE TABLE IF NOT EXISTS app_migrations" in DB_SOURCE
    ensure_schema = _method_source(DB_SOURCE, "_ensure_schema")
    assert "finalize_chart_uid_migration(conn)" in ensure_schema
    assert "PRAGMA user_version = 20" in ensure_schema


def test_database_view_loads_selected_chart_by_uid_when_available():
    populate_source = APP_SOURCE.split("item = QListWidgetItem(label)", 1)[1].split(
        "is_hypothetical = _chart_row_is_hypothetical", 1
    )[0]
    assert "item.setData(Qt.UserRole + 2" in populate_source
    load_source = _indented_method_source(APP_SOURCE, "_load_chart_from_item")
    assert "chart_uid = str(item.data(Qt.UserRole + 2)" in load_source
    assert "parent.load_chart_by_uid(chart_uid)" in load_source
