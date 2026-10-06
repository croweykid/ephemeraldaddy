from threading import Event
from types import SimpleNamespace
from datetime import datetime
import io

import pytest

from ephemeraldaddy.io.web_profile import import_service as service
from ephemeraldaddy.io.web_profile.models import BatchImportRow, ValidatedPlace
from ephemeraldaddy.io.web_profile.csv_io import export_failures


def valid_row(clock='03:04'):
    return BatchImportRow('A', 'A', '2000-01-01', clock, 'New York',
                          place=ValidatedPlace('New York', 40.7128, -74.0060), included=True)


@pytest.mark.parametrize('clock', ['03:04', 'unknown'])
def test_chart_has_public_classification_and_shared_dominance_before_save(clock):
    from ephemeraldaddy.core.chart import chart_uses_houses
    from ephemeraldaddy.gui.features.charts import metrics
    chart = service.build_chart(valid_row(clock))
    assert chart.chart_type == chart.source == 'public_db'
    assert chart.relationship_types == ['public figure']
    assert chart.auto_generated
    assert chart_uses_houses(chart) == (clock != 'unknown')
    for kind in ('sign', 'planet', 'nakshatra', 'element'):
        actual = getattr(chart, f'dominant_{kind}_weights')
        assert actual and actual == getattr(metrics, f'calculate_dominant_{kind}_weights')(chart)
    if clock == 'unknown':
        assert not chart.houses and 'AS' not in chart.positions and 'MC' not in chart.positions


def fake_chart(row):
    return SimpleNamespace(dt=datetime(2000, 1, 1), birth_place=row.birth_place,
                           birthtime_unknown=False, chart_uid='uid-' + row.name)


def test_success_is_terminal_and_never_saved_or_backed_up_again(monkeypatch):
    monkeypatch.setattr(service, 'build_chart', fake_chart)
    row = valid_row()
    saved, backups, results = [], [], []
    kwargs = dict(save=lambda chart, **kw: saved.append((chart, kw)),
                  backup=lambda **kw: backups.append(kw), on_result=results.append)
    assert service.import_rows([row], **kwargs) == (['uid-A'], [])
    assert row.imported_uid == 'uid-A' and not row.included and not row.importable
    row.included = True  # Even programmatic rechecking cannot reinsert a success.
    assert service.import_rows([row], **kwargs) == ([], [])
    assert len(saved) == len(backups) == len(results) == 1
    assert saved[0][1]['chart_type'] == 'public_db'
    stream = io.StringIO()
    export_failures([row], stream)
    assert len(stream.getvalue().splitlines()) == 1


def test_failed_save_remains_exportable_and_can_be_retried(monkeypatch):
    monkeypatch.setattr(service, 'build_chart', fake_chart)
    row = valid_row()
    def fail(*args, **kwargs): raise OSError('database locked')
    uids, failed = service.import_rows([row], save=fail, backup=lambda **kw: None)
    assert uids == [] and failed == [row] and row.imported_uid is None
    assert row.importable and not row.included and 'database locked' in row.error_text
    stream = io.StringIO()
    export_failures([row], stream)
    assert 'database locked' in stream.getvalue()
    row.included = True
    assert service.import_rows([row], save=lambda *a, **kw: None, backup=lambda **kw: None)[0] == ['uid-A']
    assert not row.save_error


def test_cancel_after_running_save_retains_success_and_skips_next_row(monkeypatch):
    monkeypatch.setattr(service, 'build_chart', fake_chart)
    first, second = valid_row(), valid_row()
    second.name = 'B'
    cancel = Event()
    saved, results = [], []
    def save(chart, **kw):
        saved.append(chart.chart_uid)
        cancel.set()
    assert service.import_rows([first, second], save=save, backup=lambda **kw: None,
                               cancel_event=cancel, on_result=results.append) == (['uid-A'], [])
    assert saved == ['uid-A'] and results == [first]
    assert first.imported_uid == 'uid-A' and second.imported_uid is None


def test_cancelled_batch_does_no_backup_or_save(monkeypatch):
    monkeypatch.setattr(service, 'build_chart', lambda row: pytest.fail('built after cancellation'))
    cancel = Event()
    cancel.set()
    assert service.import_rows([valid_row()], cancel_event=cancel,
                               backup=lambda **kw: pytest.fail('backup after cancellation')) == ([], [])


def test_import_persists_public_type_relationships_and_dominance(tmp_path, monkeypatch):
    import json
    import sqlite3
    from ephemeraldaddy.core import db
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'charts.db')
    row = valid_row('unknown')
    uids, failures = service.import_rows([row], backup=lambda **kw: None)
    assert uids == [row.imported_uid] and not failures
    with sqlite3.connect(db.DB_PATH) as connection:
        stored = connection.execute('SELECT chart_type, relationship_types, dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights, birthtime_unknown FROM charts WHERE chart_uid = ?', (row.imported_uid,)).fetchone()
    assert stored[0] == 'public_db' and db.parse_tags(stored[1]) == ['public figure']
    assert all(json.loads(value) for value in stored[2:5])
    assert stored[5] == 1


def test_cache_write_failure_rolls_back_insert_and_retry_saves_once(tmp_path, monkeypatch):
    import sqlite3
    from ephemeraldaddy.core import db
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'charts.db')
    chart = service.build_chart(valid_row('unknown'))
    original_uid = getattr(chart, 'chart_uid', None)
    monkeypatch.setattr(service, 'build_chart', lambda row: chart)
    writer = db._write_chart_derived_cache
    def fail_after_cache_write(conn, chart_id, chart):
        writer(conn, chart_id, chart)
        # The insert and cache are visible in this transaction only.
        assert conn.execute('SELECT count(*) FROM charts').fetchone()[0] == 1
        assert getattr(chart, 'chart_uid', None) == original_uid
        raise sqlite3.OperationalError('cache write interrupted')
    monkeypatch.setattr(db, '_write_chart_derived_cache', fail_after_cache_write)
    row = valid_row('unknown')
    assert service.import_rows([row], backup=lambda **kw: None) == ([], [row])
    assert row.imported_uid is None and 'cache write interrupted' in row.save_error
    assert getattr(chart, 'chart_uid', None) == original_uid
    with sqlite3.connect(db.DB_PATH) as conn:
        assert conn.execute('SELECT count(*) FROM charts').fetchone()[0] == 0
    monkeypatch.setattr(db, '_write_chart_derived_cache', writer)
    row.included = True
    assert service.import_rows([row], backup=lambda **kw: None) == ([row.imported_uid], [])
    assert row.imported_uid and row.imported_uid == chart.chart_uid
    with sqlite3.connect(db.DB_PATH) as conn:
        uid, signature = conn.execute('SELECT chart_uid, derived_birth_data_signature FROM charts').fetchone()
        assert uid == row.imported_uid and signature
        assert conn.execute('SELECT count(*) FROM charts').fetchone()[0] == 1


def test_failed_backup_aborts_before_building_or_saving(monkeypatch):
    monkeypatch.setattr(service, 'build_chart', lambda row: pytest.fail('built after failed backup'))
    def fail(**kw): raise OSError('backup unavailable')
    row = valid_row()
    with pytest.raises(OSError, match='backup unavailable'):
        service.import_rows([row], backup=fail)
    assert row.imported_uid is None and row.included


@pytest.mark.parametrize('clock', [
    '12:00+00:00', '12:00-05:00', '12:00Z', '12:00:00', '12:00:00.5',
    '1200', '12', '1:00', '24:00', '12:60',
])
def test_import_rejects_birth_times_outside_local_hh_mm(clock, monkeypatch):
    row = valid_row(clock)
    monkeypatch.setattr(service, 'Chart', lambda *a, **kw: pytest.fail('constructed an invalid clock'))
    assert 'Birth time is invalid.' in row.validation_errors()
    with pytest.raises(ValueError, match='Birth time is invalid'):
        service.build_chart(row)
    assert service.import_rows([row], backup=lambda **kw: pytest.fail('backed up invalid row')) == ([], [])


@pytest.mark.parametrize('clock', ['00:00', '23:59', '', 'unknown', 'UNKNOWN'])
def test_batch_accepts_valid_local_times_and_unknown(clock):
    assert valid_row(clock).importable
