from threading import Event, get_ident
from time import monotonic

import pytest
from PySide6.QtCore import QObject, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.features.database_view import birthplace_repair


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def spin(app, predicate):
    deadline = monotonic() + 5
    while not predicate() and monotonic() < deadline:
        app.processEvents()
    assert predicate()


def test_repair_runs_off_gui_thread_and_delivers_changes_on_gui(app, monkeypatch):
    threads, received = [], []
    def repair(resolve, **kwargs):
        threads.append(get_ident())
        kwargs["on_changed"]({"UID"})
        return {"UID"}
    monkeypatch.setattr(birthplace_repair.db, "repair_birthplace_localities", repair)
    owner = QObject()
    controller = birthplace_repair.BirthplaceRepairController(
        owner, lambda uids: received.append((uids, get_ident())),
    )
    gui_thread = get_ident()
    controller.request()
    spin(app, lambda: not controller._running)
    assert threads and threads[0] != gui_thread
    assert received == [({"UID"}, gui_thread)]
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_destroying_owner_cancels_inflight_repair_without_destroying_native_thread(app, monkeypatch):
    started, release, exited = Event(), Event(), Event()
    cancellations = []
    def repair(resolve, **kwargs):
        cancellations.append(kwargs["cancel_event"])
        started.set()
        release.wait(5)
        assert kwargs["cancel_event"].is_set()
        exited.set()
        return set()
    monkeypatch.setattr(birthplace_repair.db, "repair_birthplace_localities", repair)
    owner = QObject()
    controller = birthplace_repair.BirthplaceRepairController(
        owner, lambda uids: pytest.fail("Published after window deletion"),
    )
    controller.request()
    try:
        spin(app, started.is_set)
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        assert cancellations[0].is_set()
    finally:
        release.set()
        spin(app, exited.is_set)
