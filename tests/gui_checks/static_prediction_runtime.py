"""Real Qt worker/lifetime checks; run in a clean process without Qt stubs."""
import threading
import time
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QObject, QThread, Qt, Slot
from PySide6.QtWidgets import QApplication, QLabel
from ephemeraldaddy.analysis import trait_prediction_index as runtime

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    assert predicate()


def chart(uid):
    return SimpleNamespace(chart_uid=uid, dt=datetime(2000,1,1,tzinfo=timezone.utc), lat=0, lon=0, birthtime_unknown=False)


def test_shared_cache_completion_is_delivered_on_gui_thread(app, monkeypatch):
    from ephemeraldaddy.gui.features.predictions.trait_updates import TraitRefreshRelay
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    parent = QObject()
    received = []
    relay = TraitRefreshRelay(parent, lambda uids, traits: received.append((uids, QThread.currentThread())))
    producer = threading.Thread(target=index._publish, args=(['ABC'], [{'uid':'t'}]))
    producer.start()
    producer.join()
    wait_for(app, lambda: received)
    assert received == [(frozenset({'ABC'}), app.thread())]
    relay.deleteLater()
    parent.deleteLater()
    app.processEvents()


def test_trait_worker_uses_copied_values_and_gui_remains_responsive(app, monkeypatch):
    from ephemeraldaddy.gui.features.predictions import trait_worker
    entered = threading.Event()
    release = threading.Event()
    seen = []
    original = chart('ABC')
    def calculate(value, traits, **kwargs):
        assert QThread.currentThread() != app.thread()
        value.name = 'worker copy'
        entered.set()
        release.wait(3)
        return {'likelihoods': {'T': 80}}
    monkeypatch.setattr(trait_worker, 'calculate_chart_prediction', calculate)
    worker = trait_worker.TraitPredictionWorker(original, [{'uid':'t', 'name':'T'}], object())
    thread = QThread()
    worker.moveToThread(thread)
    class Receiver(QObject):
        @Slot(object, object)
        def receive(self, token, value):
            seen.append((value, QThread.currentThread()))
    receiver = Receiver()
    worker.finished.connect(receiver.receive, Qt.QueuedConnection)
    worker.finished.connect(thread.quit)
    thread.started.connect(worker.run)
    thread.start()
    try:
        wait_for(app, entered.is_set)
        assert not hasattr(original, 'name')
        label = QLabel('responsive')
        label.setText('GUI heartbeat during scoring')
        app.processEvents()
        assert label.text() == 'GUI heartbeat during scoring'
        release.set()
        wait_for(app, lambda: not thread.isRunning())
        wait_for(app, lambda: seen)
        assert seen[0][1] == app.thread()
    finally:
        release.set()
        thread.quit()
        thread.wait(5000)


def test_distinguishing_presenter_rejects_previous_chart_completion(app, monkeypatch):
    from ephemeraldaddy.gui.features.predictions import distinguishing_factors as ui
    entered = threading.Event()
    release = threading.Event()
    monkeypatch.setattr(ui, 'distinguishing_norm_reference', lambda: (({},), 'static'))
    def calculate(value, *args):
        assert threading.current_thread() is not threading.main_thread()
        if value.chart_uid == 'A':
            entered.set()
            release.wait(3)
        return (value.chart_uid, 10.)
    monkeypatch.setattr(ui, '_calculate', calculate)
    label = QLabel()
    presenter = ui.DistinguishingFactorsPresenter(label)
    try:
        presenter.render(chart('A'))
        wait_for(app, entered.is_set)
        presenter.render(chart('B'))
        release.set()
        wait_for(app, lambda: label.text() == 'B')
        assert presenter._token[0] == 'B'
        presenter.render(None)
        assert label.text() == 'No chart loaded.'
    finally:
        release.set()
        label.deleteLater()
        app.processEvents()


def test_alignment_controller_rejects_old_chart_and_has_no_gui_calculation(app, monkeypatch):
    from ephemeraldaddy.gui.features.predictions import alignment_refresh as ui
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    entered = threading.Event()
    release = threading.Event()
    received = []
    parent = QObject()
    controller = ui.AlignmentRefreshController(parent)
    def calculate(value, **kwargs):
        assert threading.current_thread() is not threading.main_thread()
        if value.chart_uid == 'A':
            entered.set()
            release.wait(3)
        return {'chart': value.chart_uid}
    monkeypatch.setattr(ui, 'alignment_parts', calculate)
    try:
        controller.request(chart('A'), received.append)
        wait_for(app, entered.is_set)
        controller.request(chart('B'), received.append)
        release.set()
        wait_for(app, lambda: received)
        assert received == [{'chart': 'B'}]
    finally:
        release.set()
        index._queue.join()
        parent.deleteLater()
        app.processEvents()


def test_alignment_controller_survives_recreated_adapters_and_reuses_completed_parts(app, monkeypatch):
    from ephemeraldaddy.gui.features.charts import dnd_predictions as facade
    from ephemeraldaddy.gui.features.predictions import alignment_refresh as ui
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    parent = QObject()
    entered = threading.Event()
    release = threading.Event()
    calculated = []
    rendered = []
    def calculate(value, **kwargs):
        calculated.append(value.chart_uid)
        if value.chart_uid == 'A':
            entered.set()
            release.wait(3)
        return {'good': {'chart': value.chart_uid}}
    monkeypatch.setattr(ui, 'alignment_parts', calculate)
    monkeypatch.setattr(facade._CoreDndPredictionPanelAdapter, 'render', lambda self, value, renderer, **kwargs: rendered.append((value.chart_uid, getattr(value, '_dnd_alignment_score_parts_cache', None))))
    def adapter():
        value = facade.DndPredictionPanelAdapter.__new__(facade.DndPredictionPanelAdapter)
        value.owner = parent
        value.alignment_layout = object()
        value.is_placeholder_chart = lambda chart: False
        return value
    try:
        adapter().render(chart('A'), None, {'dnd_alignment'})
        wait_for(app, entered.is_set)
        adapter().render(chart('B'), None, {'dnd_alignment'})
        release.set()
        wait_for(app, lambda: len(rendered) == 3)
        assert [uid for uid, _ in rendered] == ['A', 'B', 'B']
        assert len(parent.findChildren(ui.AlignmentRefreshController)) == 1
        adapter().render(chart('B'), None, {'dnd_alignment'})
        assert rendered[-1][1]['parts'] == {'good': {'chart': 'B'}}
        assert calculated == ['A', 'B']
    finally:
        release.set()
        index._queue.join()
        parent.deleteLater()
        app.processEvents()


def test_returning_to_completed_alignment_rejects_another_chart_still_in_flight(app, monkeypatch):
    from ephemeraldaddy.gui.features.charts import dnd_predictions as facade
    from ephemeraldaddy.gui.features.predictions import alignment_refresh as ui

    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    parent = QObject()
    entered_b = threading.Event()
    release_b = threading.Event()
    rendered = []
    delivered = []

    def calculate(value, **kwargs):
        if value.chart_uid == 'B':
            entered_b.set()
            release_b.wait(3)
        return {'good': {'chart': value.chart_uid}}

    monkeypatch.setattr(ui, 'alignment_parts', calculate)
    monkeypatch.setattr(
        facade._CoreDndPredictionPanelAdapter, 'render',
        lambda self, value, renderer, **kwargs: rendered.append(
            (value.chart_uid, getattr(value, '_dnd_alignment_score_parts_cache', None))
        ),
    )

    def render(uid):
        adapter = facade.DndPredictionPanelAdapter.__new__(facade.DndPredictionPanelAdapter)
        adapter.owner = parent
        adapter.alignment_layout = object()
        adapter.is_placeholder_chart = lambda value: False
        adapter.render(chart(uid), None, {'dnd_alignment'})

    class Receiver(QObject):
        @Slot(object, object)
        def receive(self, token, parts):
            delivered.append(parts['good']['chart'])

    receiver = Receiver()
    controller = ui.AlignmentRefreshController(parent)
    controller.setObjectName('prediction-alignment-refresh')
    controller.completed.connect(receiver.receive, Qt.QueuedConnection)
    try:
        render('A')
        wait_for(app, lambda: delivered == ['A'])
        render('B')
        wait_for(app, entered_b.is_set)
        render('A')
        assert rendered[-1][1]['parts'] == {'good': {'chart': 'A'}}
        frame_count = len(rendered)
        release_b.set()
        wait_for(app, lambda: delivered == ['A', 'B'])
        assert len(rendered) == frame_count
        assert all(payload['parts']['good']['chart'] == uid for uid, payload in rendered if payload)
    finally:
        release_b.set()
        index._queue.join()
        parent.deleteLater()
        app.processEvents()
