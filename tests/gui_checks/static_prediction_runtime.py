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


def test_gender_overlay_survives_worker_completion_and_next_render(app, monkeypatch, tmp_path):
    import copy
    import json
    from PySide6.QtWidgets import QWidget
    from ephemeraldaddy.core import prediction_norms as norms
    from ephemeraldaddy.gui.features.charts import trait_predictions as facade
    from ephemeraldaddy.gui.features.predictions import trait_worker
    from ephemeraldaddy.analysis.trait_prediction_results import metadata_from_vectors

    core = facade._core
    monkeypatch.setattr(runtime, '_INDEX', runtime.TraitPredictionIndex())
    paths = norms.PredictionNormPaths(tmp_path/'source.json', tmp_path/'official.json', tmp_path/'personal.json', tmp_path/'extra.json')
    paths.official.write_text(json.dumps({'version': 1, 'trait_baselines': {'uid:t': {'db_average': 50.}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    traits = [{'uid': 't', 'name': 'T', 'profile': {'genderDistribution': {
        'statisticallySignificant': True, 'percentages': {'Female': 80.},
        'databasePercentages': {'Female': 50.}, 'significantCategories': ['Female'],
    }}}]
    monkeypatch.setattr(core, 'list_traits', lambda **kwargs: traits)
    original = chart('OVERLAYUID0001')
    original.gender = 'Female'
    metadata = metadata_from_vectors(likelihoods={'T': 81.}, database_averages={'T': 50.})
    metadata['gender_criterion_traits'] = ['T']
    calculated = []
    presented = []
    prompts = []

    def calculate(value, selected, **kwargs):
        assert value is not original
        assert kwargs['include_gender']
        calculated.append(value.chart_uid)
        return copy.deepcopy(metadata)

    monkeypatch.setattr(trait_worker, 'calculate_chart_prediction', calculate)
    monkeypatch.setattr(core, '_apply_traits_prediction_metadata', lambda owner, selected, data, **kwargs: presented.append(copy.deepcopy(data)))
    monkeypatch.setattr(core, '_apply_traits_prediction_view', lambda *args, **kwargs: prompts.append(args[1]))
    owner = QWidget()
    owner.traits_prediction_label = QLabel(owner)
    owner._is_placeholder_chart = lambda value: False
    owner._predictions_use_trait_gender_distribution = True
    owner._predictions_manual_recalculation_only = True
    try:
        core.render_traits_predictions(owner, original)
        core.start_traits_prediction_calculation(owner)
        wait_for(app, lambda: bool(presented))
        wait_for(app, lambda: not owner._traits_prediction_worker_jobs)
        prompt_count = len(prompts)
        monkeypatch.setattr(core, '_start_traits_prediction_calculation', lambda *a: pytest.fail('Completed overlay started another calculation'))
        core.render_traits_predictions(owner, original)
        app.processEvents()
        assert len(prompts) == prompt_count
        assert len(presented) == 2
        assert presented[-1]['likelihoods'] == {'T': 81.}
        assert original._trait_gender_prediction_metadata_cache['metadata']['likelihoods'] == {'T': 81.}
        assert calculated == ['OVERLAYUID0001']
    finally:
        core.stop_traits_prediction_refresh_workers(owner, wait_msecs=5000)
        owner.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("other_uid", [None, "WEIRDCACHE0002"])
def test_weirdness_completion_rejects_saved_chart_changes_and_retries_only_that_uid(app, monkeypatch, other_uid):
    from ephemeraldaddy.gui.features.database_view import weirdness_sort as ui

    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    monkeypatch.setattr(ui, 'distinguishing_norm_reference', lambda: (({},), 'static'))
    first_running = threading.Event()
    release_first = threading.Event()
    emitted = threading.Event()
    calls = []
    applied = []
    parent = QObject()
    uid = 'WEIRDCACHE0001'
    row = [None] * 32
    row[15], row[30] = 0, uid
    rows_by_uid = {uid: row}
    if other_uid:
        other_row = [None] * 32
        other_row[15], other_row[30] = 0, other_uid
        rows_by_uid[other_uid] = other_row
    rows = list(rows_by_uid.values())
    metadata = {}

    def calculate(uids):
        calls.append(tuple(uids))
        if len(calls) == 1:
            first_running.set()
            release_first.wait(3)
            return {uid: 10., **({other_uid: 30.} if other_uid else {})}
        return {uid: 20.}

    monkeypatch.setattr(ui, 'refresh_weirdness_scores', calculate)
    def ready(values, signature):
        applied.append(dict(values))
        for key, score in values.items():
            rows_by_uid[key][31] = score
            metadata[key] = (ui.DISTINGUISHING_FORMULA_VERSION, signature)
        controller.request_missing(rows, metadata)

    controller = ui.WeirdnessSortController(parent, ready)
    controller.completed.connect(lambda *args: emitted.set(), Qt.DirectConnection)
    try:
        controller.request_missing(rows, metadata)
        wait_for(app, first_running.is_set)
        release_first.set()
        assert emitted.wait(3)  # Score is finished, but its GUI slot has not run.
        index.invalidate_chart(uid)
        wait_for(app, lambda: len(applied) == 2)
        assert applied == [({other_uid: 30.} if other_uid else {}), {uid: 20.}]
        assert calls == [tuple(rows_by_uid), (uid,)]
        assert row[31] == 20.
    finally:
        release_first.set()
        parent.deleteLater()
        app.processEvents()
