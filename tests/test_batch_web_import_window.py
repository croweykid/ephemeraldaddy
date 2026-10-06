import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from threading import Event
from time import monotonic

import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent
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
    thread, worker = window.lookup_thread, window.worker
    try:
        spin_until(app, started.is_set)
        window.lookup()
        assert window.lookup_thread is thread and window.worker is worker
        assert not window.close()
        assert window.isVisible() and thread.isRunning()
        assert worker.cancel_event.is_set()
    finally:
        release.set()
        spin_until(app, lambda: window.lookup_thread is None)
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
    assert all('could not be resolved' in row.error_text for row in window.rows)
    calls = []
    monkeypatch.setattr(module, 'geocode_location', lambda place: (calls.append(place) or (1, 2, 'Here')))
    window.validate_all()
    assert calls == ['Here']
    assert all(row.importable for row in window.rows)
    window.close()
