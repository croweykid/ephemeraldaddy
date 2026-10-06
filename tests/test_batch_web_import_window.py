import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from threading import Event
from time import monotonic

import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent, Slot
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.features.import_export.batch_web_import import window as module
from ephemeraldaddy.io.web_profile.models import BatchImportRow


@pytest.fixture
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
    def fail(place): raise ValueError('temporary outage')
    monkeypatch.setattr(module, 'geocode_location', fail)
    window.validate_all()
    spin_until(app, lambda: window.worker_thread is None)
    assert all('could not be resolved' in row.error_text for row in window.rows)
    calls = []
    monkeypatch.setattr(module, 'geocode_location', lambda place: (calls.append(place) or (1, 2, 'Here')))
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
    def resolve(place):
        calls.append(get_ident())
        started.set()
        release.wait(5)
        return 1, 2, 'Canonical place'
    monkeypatch.setattr(module, 'geocode_location', resolve)
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
    monkeypatch.setattr(module, 'geocode_location', lambda place: (calls.append(place) or (1, 2, 'Canonical')))
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
    def resolve(place):
        started.set()
        release.wait(5)
        return 1, 2, 'Old canonical'
    monkeypatch.setattr(module, 'geocode_location', resolve)
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
