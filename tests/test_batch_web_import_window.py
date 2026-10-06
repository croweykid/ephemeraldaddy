import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from threading import Event
from time import monotonic

import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent, Slot
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.features.import_export.batch_web_import import window as module
from ephemeraldaddy.io.web_profile.models import BatchImportRow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def spin_until(app, predicate):
    deadline = monotonic() + 5
    while not predicate() and monotonic() < deadline:
        app.processEvents()
    assert predicate()


def test_close_defers_deletion_until_inflight_lookup_returns(app, monkeypatch):
    started, release = Event(), Event()
    class Service:
        def lookup(self, seed):
            started.set()
            release.wait(5)
            return BatchImportRow(seed.name)
    monkeypatch.setattr(module, 'WebProfileLookupService', Service)
    window = module.BatchWebImportWindow()
    window.setAttribute(Qt.WA_DeleteOnClose, True)
    destroyed = []
    window.destroyed.connect(lambda: destroyed.append(True))
    window.show()
    window.names.setPlainText('A\nB')
    window.lookup()
    thread, worker = window.worker_thread, window.worker
    try:
        spin_until(app, started.is_set)
        window.lookup()
        assert window.worker_thread is thread and window.worker is worker
        assert not window.close()
        assert window.isVisible() and thread.isRunning()
        assert worker.cancel_event.is_set()
    finally:
        release.set()
        spin_until(app, lambda: window.worker_thread is None)
        app.processEvents()
    assert window.rows == []
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert destroyed == [True]


def test_location_revalidation_clears_failure_and_reuses_cache(app, monkeypatch):
    window = module.BatchWebImportWindow()
    for name in ['A', 'B']:
        window.add_row(BatchImportRow(name, name, '2000-01-01', birth_place='Here'))
    def fail(place, **kwargs): raise ValueError('temporary outage')
    monkeypatch.setattr(module, 'search_locations', fail)
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert all('could not be resolved' in row.error_text for row in window.rows)
    calls = []
    monkeypatch.setattr(module, 'search_locations', lambda place, **kwargs: (calls.append(place) or [('Here', 1, 2)]))
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert calls == ['Here']
    assert all(row.importable for row in window.rows)
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert calls == ['Here']
    window.close()


def test_owned_batch_import_is_a_separate_window(app):
    from PySide6.QtWidgets import QWidget
    owner = QWidget()
    window = module.BatchWebImportWindow(owner)
    assert window.isWindow()
    assert window.parentWidget() is owner
    assert window.owner is owner
    window.close()
    owner.close()


def test_validation_runs_off_gui_thread_and_close_waits_for_it(app, monkeypatch):
    from threading import get_ident
    from PySide6.QtCore import QTimer
    started, release = Event(), Event()
    calls, applied_threads, ticks = [], [], []
    main_thread = get_ident()
    def resolve(place, **kwargs):
        calls.append(get_ident())
        started.set()
        release.wait(5)
        return [('Canonical place', 1, 2)]
    monkeypatch.setattr(module, 'search_locations', resolve)
    class RecordingWindow(module.BatchWebImportWindow):
        @Slot(object)
        def _apply_place_result(self, result):
            applied_threads.append(get_ident())
            super()._apply_place_result(result)
    window = RecordingWindow()
    window.add_row(BatchImportRow('A', 'A', '2000-01-01', birth_place='Here'))
    window.setAttribute(Qt.WA_DeleteOnClose, True)
    window.show()
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(0)
    try:
        window.validate_all()
        spin_until(app, started.is_set)
        spin_until(app, lambda: bool(ticks))
        assert len(calls) == 1 and calls[0] != main_thread
        assert not window._action_buttons[0].isEnabled()
        worker = window.worker
        window.validate_all()
        window.lookup()
        assert window.worker is worker
        assert not window.close()
        assert worker.cancel_event.is_set()
    finally:
        release.set()
        spin_until(app, lambda: window.worker_thread is None)
        timer.stop()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert applied_threads == []


def test_validation_applies_results_on_gui_thread_and_reuses_canonical_alias(app, monkeypatch):
    from threading import get_ident
    main_thread = get_ident()
    calls, applied_threads = [], []
    monkeypatch.setattr(module, 'search_locations', lambda place, **kwargs: (calls.append(place) or [('Canonical', 1, 2)]))
    class RecordingWindow(module.BatchWebImportWindow):
        @Slot(object)
        def _apply_place_result(self, result):
            applied_threads.append(get_ident())
            super()._apply_place_result(result)
    window = RecordingWindow()
    for place in [' Here ', 'here', 'Canonical']:
        window.add_row(BatchImportRow('A', 'A', '2000-01-01', birth_place=place))
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert calls == ['Here']
    assert applied_threads == [main_thread] * 3
    assert all(row.importable and row.birth_place == 'Canonical' for row in window.rows)
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert calls == ['Here']
    window.close()


def test_failures_csv_loads_rows_without_overwriting_edits_or_requesting_profiles(app, tmp_path, monkeypatch):
    from ephemeraldaddy.io.web_profile.csv_io import export_failures
    path = tmp_path / 'failures.csv'
    row = BatchImportRow('A', 'A', '2000-01-01', '03:04', 'Here', biography='Edited bio', sources=['https://example.com/source'])
    export_failures([row], path)
    monkeypatch.setattr(module.QFileDialog, 'getOpenFileName', lambda *args: (str(path), 'CSV'))
    monkeypatch.setattr(module, 'WebProfileLookupService', lambda: pytest.fail('Reload requested a profile'))
    window = module.BatchWebImportWindow()
    window.load_csv()
    assert len(window.rows) == 1
    restored = window.rows[0]
    assert (restored.birth_date, restored.birth_time, restored.birth_place) == ('2000-01-01', '03:04', 'Here')
    window.table.item(0, 6).setText('More repairs')
    window.table.item(0, 5).setText('https://example.com/repaired-source')
    window.lookup()
    assert window.worker is None
    window._sync()
    assert restored.biography == 'More repairs'
    assert restored.sources == ['https://example.com/repaired-source']
    window.close()


def test_stale_location_result_does_not_overwrite_new_place(app, monkeypatch):
    started, release = Event(), Event()
    def resolve(place, **kwargs):
        started.set()
        release.wait(5)
        return [('Old canonical', 1, 2)]
    monkeypatch.setattr(module, 'search_locations', resolve)
    window = module.BatchWebImportWindow()
    window.add_row(BatchImportRow('A', 'A', '2000-01-01', birth_place='Old'))
    try:
        window.validate_all()
        spin_until(app, started.is_set)
        window.table.item(0, 4).setText('New')
    finally:
        release.set()
        spin_until(app, lambda: window.worker_thread is None)
    window._sync()
    assert window.rows[0].birth_place == 'New'
    assert window.rows[0].place is None
    window.close()


def test_lookup_worker_restores_csv_fields_without_calling_providers(monkeypatch):
    from ephemeraldaddy.io.web_profile.models import BatchImportSeed
    seeds = [BatchImportSeed('A', birth_date='2000-01-01', birth_place='Here',
                             biography='Preserved', sources=('https://example.com',), restored=True)]
    calls = []
    monkeypatch.setattr(module, 'WebProfileLookupService', lambda: calls.append(True))
    worker = module._LookupWorker(seeds)
    rows, finished = [], []
    worker.result.connect(rows.append)
    worker.finished.connect(lambda: finished.append(True))
    worker.run()
    assert calls == [] and finished == [True]
    assert len(rows) == 1 and rows[0].birth_date == '2000-01-01'
    assert rows[0].biography == 'Preserved' and rows[0].sources == ['https://example.com']


def test_ambiguous_places_require_choice_and_reuse_only_chosen_coordinates(app, monkeypatch):
    calls = []
    def search(place, **kwargs):
        assert kwargs == dict(limit=7, allow_online=True)
        calls.append(place)
        return [('Springfield North', 1, 2), ('Springfield South', 3, 4)]
    monkeypatch.setattr(module, 'search_locations', search)
    window = module.BatchWebImportWindow()
    for name in ['A', 'B']:
        window.add_row(BatchImportRow(name, name, '2000-01-01', birth_place='Springfield'))
    window.validate_all()
    spin_until(app, lambda: window._place_dialog is not None)
    assert window._busy and all(not row.importable for row in window.rows)
    dialog = window._place_dialog
    from PySide6.QtWidgets import QComboBox
    dialog.findChild(QComboBox).setCurrentIndex(1)
    dialog.accept()
    spin_until(app, lambda: not window._busy)
    assert calls == ['Springfield']
    assert all(row.place.latitude == 3 and row.place.longitude == 4 for row in window.rows)
    assert all(row.importable for row in window.rows)
    window.validate_all()
    spin_until(app, lambda: not window._busy)
    assert calls == ['Springfield'] and window._place_dialog is None
    window.close()


def test_selected_place_validation_can_decline_then_choose_on_retry(app, monkeypatch):
    monkeypatch.setattr(module, 'search_locations', lambda place, **kw: [('North', 1, 2), ('South', 3, 4)])
    window = module.BatchWebImportWindow()
    for name in ['A', 'B']:
        window.add_row(BatchImportRow(name, name, '2000-01-01', birth_place='Here'))
    window.table.selectRow(1)
    window.validate_selected()
    spin_until(app, lambda: window._place_dialog is not None)
    window._place_dialog.reject()
    spin_until(app, lambda: not window._busy)
    assert window.rows[0].place is None and window.rows[1].place is None
    assert 'selection required' in window.rows[1].error_text
    window.validate_selected()
    spin_until(app, lambda: window._place_dialog is not None)
    window._place_dialog.accept()
    spin_until(app, lambda: not window._busy)
    assert not window.rows[0].importable and window.rows[1].importable
    window.close()


def test_close_during_place_choice_finishes_without_a_running_thread(app, monkeypatch):
    monkeypatch.setattr(module, 'search_locations', lambda place, **kw: [('North', 1, 2), ('South', 3, 4)])
    window = module.BatchWebImportWindow()
    window.show()
    window.add_row(BatchImportRow('A', 'A', '2000-01-01', birth_place='Here'))
    window.validate_all()
    spin_until(app, lambda: window._place_dialog is not None)
    assert not window.close()
    spin_until(app, lambda: not window.isVisible())
    assert window.worker_thread is None and not window._busy


@pytest.mark.parametrize('close_during_save', [False, True])
def test_import_is_backgrounded_applies_on_gui_and_locks_success(app, monkeypatch, close_during_save):
    from threading import get_ident
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget
    from ephemeraldaddy.io.web_profile.models import ValidatedPlace
    main = get_ident()
    started, release = Event(), Event()
    calls, applied, refreshed, ticks = [], [], [], []
    class Owner(QWidget):
        def _refresh_charts(self, **kw): refreshed.append((get_ident(), kw))
    owner = Owner()
    class Window(module.BatchWebImportWindow):
        def _apply_import_result(self, result):
            applied.append(get_ident())
            super()._apply_import_result(result)
    def importing(rows, *, cancel_event, progress, on_result):
        calls.append(get_ident())
        started.set()
        release.wait(5)
        row = rows[0]
        row.imported_uid = 'saved-uid'
        row.included = False
        on_result(row)
        return ['saved-uid'], []
    monkeypatch.setattr(module, 'import_rows', importing)
    monkeypatch.setattr(module.QMessageBox, 'information', lambda *a: None)
    monkeypatch.setattr(module.QMessageBox, 'warning', lambda *a: pytest.fail('unexpected import error'))
    window = Window(owner)
    row = BatchImportRow('A', 'A', '2000-01-01', birth_place='Here', place=ValidatedPlace('Here', 1, 2))
    window.add_row(row)
    window.table.item(0, 0).setCheckState(Qt.Checked)
    window.show()
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(0)
    try:
        window.do_import()
        spin_until(app, started.is_set)
        spin_until(app, lambda: bool(ticks))
        assert calls[0] != main and row.imported_uid is None
        window.do_import()
        assert len(calls) == 1
        if close_during_save:
            assert not window.close()
            assert window.worker.cancel_event.is_set()
    finally:
        release.set()
        spin_until(app, lambda: window.worker_thread is None)
        timer.stop()
    assert applied == [main, main]
    assert refreshed == [(main, dict(changed_uids={'saved-uid'}))]
    assert window.rows[0].imported_uid == 'saved-uid'
    assert not window.table.item(0, 0).flags() & Qt.ItemIsEnabled
    window.table.item(0, 0).setCheckState(Qt.Checked)
    window.do_import()
    assert len(calls) == 1
    window.close()
    owner.close()


def test_real_chart_import_and_database_save_run_safely_in_worker(app, tmp_path, monkeypatch):
    from threading import get_ident
    import sqlite3
    from ephemeraldaddy.core import db
    from ephemeraldaddy.io.web_profile import import_service
    from ephemeraldaddy.io.web_profile.models import ValidatedPlace
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'charts.db')
    threads = []
    def importing(rows, **kwargs):
        threads.append(get_ident())
        return import_service.import_rows(rows, backup=lambda **kw: None, **kwargs)
    monkeypatch.setattr(module, 'import_rows', importing)
    monkeypatch.setattr(module.QMessageBox, 'information', lambda *a: None)
    monkeypatch.setattr(module.QMessageBox, 'warning', lambda *a: pytest.fail('real import failed'))
    window = module.BatchWebImportWindow()
    window.add_row(BatchImportRow('A', 'A', '2000-01-01', 'unknown', 'New York',
                                 place=ValidatedPlace('New York', 40.7128, -74.0060)))
    window.table.item(0, 0).setCheckState(Qt.Checked)
    window.do_import()
    spin_until(app, lambda: not window._busy)
    assert threads and threads[0] != get_ident()
    assert window.rows[0].imported_uid is not None
    with sqlite3.connect(db.DB_PATH) as conn:
        assert conn.execute('SELECT count(*) FROM charts').fetchone()[0] == 1
    window.do_import()
    assert len(threads) == 1
    window.close()
