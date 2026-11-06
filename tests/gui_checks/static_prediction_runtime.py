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


@pytest.fixture
def cached_population(tmp_path, monkeypatch):
    import copy
    import json
    from ephemeraldaddy.core import db, prediction_norms as norms
    from ephemeraldaddy.analysis import traits as definitions

    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'charts.db')
    paths = norms.PredictionNormPaths(tmp_path/'source.json', tmp_path/'official.json', tmp_path/'personal.json', tmp_path/'extra.json')
    paths.official.write_text(json.dumps({'version': 1, 'trait_baselines': {'uid:t': {'db_average': 50.}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    traits = [{'uid': 't', 'name': 'T', 'profile': {'signs': {'Aries': 1}}}]
    monkeypatch.setattr(definitions, 'list_traits', lambda **kwargs: traits)
    charts = {uid: chart(uid) for uid in ('REVIEWFIX0001', 'REVIEWFIX0002')}
    charts['REVIEWFIX0001'].name, charts['REVIEWFIX0002'].name = 'Alpha', 'Beta'
    charts['REVIEWFIX0002'].lat = 10.
    conn = db._get_conn()
    with conn:
        for uid, value in charts.items():
            conn.execute('INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,?,0,?)',
                         (uid, value.name, value.dt.isoformat(), value.lat, '2026-01-01'))
    conn.close()
    monkeypatch.setattr(db, 'load_chart_by_uid', lambda uid: copy.deepcopy(charts.get(uid)))
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda uids: {uid: copy.deepcopy(charts[uid]) for uid in uids if uid in charts})
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', lambda value, selected, **kwargs: {t['name']: 80. - value.lat for t in selected})
    index.refresh_uids(charts, traits)
    return index, traits, charts


@pytest.mark.parametrize('stale_source', ['astro_data', 'definition'])
def test_rankings_repairs_present_but_stale_scores_after_restart(app, monkeypatch, cached_population, stale_source):
    import json
    from PySide6.QtWidgets import QWidget
    from ephemeraldaddy.core import db
    from ephemeraldaddy.gui import ranking_panel_core as ui

    _, traits, charts = cached_population
    monkeypatch.setattr(ui, 'list_traits', lambda **kwargs: traits)
    uid = 'REVIEWFIX0001'
    if stale_source == 'astro_data':
        charts[uid].lat = 30.
        conn = db._get_conn()
        with conn:
            conn.execute('UPDATE charts SET lat=30 WHERE chart_uid=?', (uid,))
        conn.close()
    else:
        traits[0]['profile']['signs']['Aries'] = 2
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    calls, states = [], []
    entered, release = threading.Event(), threading.Event()
    def score(value, selected, **kwargs):
        assert QThread.currentThread() != app.thread()
        calls.append(value.chart_uid)
        entered.set()
        release.wait(3)
        return {'T': 80. - value.lat if stale_source == 'astro_data' else 40. + value.lat}
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', score)
    ids = db.get_chart_ids_by_uid(charts)

    class View(QWidget, ui.RankingsPanelMixin):
        _rankings_database_chart_uids = lambda self: tuple(charts)
        _rankings_database_legacy_chart_ids = lambda self, uids: set(ids.values())
        _sync_rankings_trait_combo = lambda self: 'T'
        _traits_distribution_chart_uid_by_id = lambda self: {row: key for key, row in ids.items()}
        _traits_distribution_chart_tokens = lambda self: {key: 'current' for key in charts}
        _traits_distribution_signature = lambda self, selected: tuple((t['name'], '#ffffff', json.dumps(t['profile'])) for t in selected)
        def _render_rankings_traits_html(self, name, rows, **kwargs):
            states.append(([(r['name'], r['likelihood']) for r in rows], kwargs['cache_warmed']))
            return repr(states[-1])

    owner = View()
    owner.rankings_traits_label = QLabel(owner)
    owner._rankings_section_expanded = {'traits': True}
    owner._traits_distribution_chart_likelihood_cache = {}
    try:
        owner._refresh_rankings_panel({'traits'})
        wait_for(app, entered.is_set)
        assert states[0] == ([('Alpha', 80.), ('Beta', 70.)], False)
        release.set()
        expected = [('Beta', 70.), ('Alpha', 50.)] if stale_source == 'astro_data' else [('Beta', 50.), ('Alpha', 40.)]
        wait_for(app, lambda: states and states[-1] == (expected, True))
        assert calls == ([uid] if stale_source == 'astro_data' else list(charts))
        assert owner._rankings_trait_likelihood_cache_complete(chart_uids_by_id={row:key for key,row in ids.items()}, trait_signature=(), selected_trait_name='T')
    finally:
        release.set()
        owner._stop_rankings_trait_worker(wait_msecs=5000)
        owner.deleteLater()
        app.processEvents()


@pytest.mark.parametrize('race', ['unchanged', 'birth_edit', 'newer_score'])
def test_distinguishing_write_rejects_birth_save_after_saved_input_check(app, monkeypatch, cached_population, race):
    import copy
    from ephemeraldaddy.core import db
    from ephemeraldaddy.gui.features.predictions import distinguishing_factors as ui

    _, _, charts = cached_population
    uid = 'REVIEWFIX0001'
    db.update_chart_weirdness_score_by_uid(uid, 101., formula_version=ui.DISTINGUISHING_FORMULA_VERSION, norm_signature='static')
    monkeypatch.setattr(ui, 'calculate_weirdness_score_from_metric_payloads', lambda *a: (100., 6))
    monkeypatch.setattr(ui, 'build_distinguishing_factors_html', lambda *a, **k: 'calculated')
    def saved_input(value):
        saved = copy.deepcopy(charts[value])
        if race != 'unchanged':
            conn = db._get_conn()
            with conn:
                conn.execute('UPDATE charts SET lat=20 WHERE chart_uid=?', (uid,))
                if race == 'newer_score':
                    conn.execute("UPDATE charts SET weirdness_score=900, weirdness_formula_version=99, weirdness_norm_signature='newer' WHERE chart_uid=?", (uid,))
            conn.close()
        return saved
    monkeypatch.setattr(db, 'load_chart_by_uid', saved_input)
    assert ui._pool.submit(ui._calculate, copy.deepcopy(charts[uid]), ({},), 'static', False).result(timeout=5) == ('calculated', 100.)
    conn = db._get_conn()
    row = conn.execute('SELECT weirdness_score,weirdness_formula_version,weirdness_norm_signature FROM charts WHERE chart_uid=?', (uid,)).fetchone()
    conn.close()
    expected = {'unchanged': (100., ui.DISTINGUISHING_FORMULA_VERSION, 'static'),
                'birth_edit': (101., None, None), 'newer_score': (900., 99, 'newer')}
    assert row == expected[race]


def test_analytics_legacy_import_refreshes_rankings_after_commit_on_gui_thread(app, monkeypatch, cached_population, tmp_path):
    import json
    from PySide6.QtWidgets import QWidget, QVBoxLayout
    from ephemeraldaddy.core import db
    from ephemeraldaddy.analysis import trait_cache_migration as migration
    from ephemeraldaddy.gui.features.charts import database_analytics as ui

    index, traits, charts = cached_population
    monkeypatch.setattr(ui, 'list_traits', lambda **kwargs: traits)
    conn = db._get_conn()
    with conn:
        conn.execute('DELETE FROM chart_trait_likelihoods')
        conn.execute('DELETE FROM chart_trait_metadata')
    conn.close()
    (tmp_path/'.traits_distribution_likelihood_cache.json').write_text(json.dumps({
        'version': 4, 'profiles': [json.dumps(traits[0]['profile'])],
        'profile_entries': [{'profile': 0, 'chart_uid': uid, 'likelihood': 89. - i*10} for i, uid in enumerate(charts)],
    }))
    entered, release = threading.Event(), threading.Event()
    original_import = migration.import_legacy_trait_cache
    def delayed_import(*args):
        entered.set()
        release.wait(3)
        original_import(*args)
    monkeypatch.setattr(migration, 'import_legacy_trait_cache', delayed_import)
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', lambda *a, **k: pytest.fail('Legacy display recalculated Traits'))
    deliveries = []
    class View(QWidget, ui.DatabaseAnalyticsChartsMixin):
        _traits_distribution_display_mode = lambda self: 'trait_rankings'
        _sync_traits_distribution_rank_combo = lambda self, selected: 'T'
        _sync_traits_distribution_display_mode = lambda self: None
        _clear_layout = lambda self, layout: None
        _build_dominant_planet_chart = lambda self, **kwargs: QWidget(self)
        _build_analysis_export_rows = lambda self, **kwargs: []
        def _refresh_traits_distribution_rankings_from_cached_context(self):
            deliveries.append(QThread.currentThread())
            super()._refresh_traits_distribution_rankings_from_cached_context()
    owner = View()
    owner.traits_distribution_rank_label = QLabel(owner)
    owner.traits_distribution_subheader_label = QLabel(owner)
    owner.traits_distribution_chart_layout = QVBoxLayout(owner)
    owner._analysis_chart_export_rows = {}
    try:
        owner._render_traits_distribution_section(chart_ids=[], database_chart_ids=set(db.get_chart_ids_by_uid(charts).values()), loaded_charts=0, should_refresh=lambda section: True)
        wait_for(app, entered.is_set)
        assert 'No non-placeholder charts' in owner.traits_distribution_rank_label.text()
        release.set()
        wait_for(app, lambda: 'Alpha' in owner.traits_distribution_rank_label.text())
        assert '89.0%' in owner.traits_distribution_rank_label.text()
        assert deliveries == [app.thread()]
        index._queue.join()
        owner._load_traits_distribution_likelihood_cache()
        index._queue.join()
        index._publish(charts, [{'uid': 'unrelated', 'name': 'Unrelated'}])
        app.processEvents()
        assert deliveries == [app.thread()]
    finally:
        release.set()
        index._queue.join()
        owner.deleteLater()
        app.processEvents()


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


@pytest.mark.parametrize('draft_kind', ['without_uid', 'new_uid', 'birth_edit', 'gender_without_evidence'])
def test_draft_trait_results_survive_worker_completion_and_next_render(app, monkeypatch, tmp_path, draft_kind):
    import copy
    import json
    from PySide6.QtWidgets import QWidget
    from ephemeraldaddy.core import db, prediction_norms as norms
    from ephemeraldaddy.analysis import trait_evidence
    from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature, trait_definition_signature
    from ephemeraldaddy.gui.features.charts import trait_predictions as facade

    core = facade._core
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'charts.db')
    paths = norms.PredictionNormPaths(tmp_path/'source.json', tmp_path/'official.json', tmp_path/'personal.json', tmp_path/'extra.json')
    paths.official.write_text(json.dumps({'version': 1, 'trait_baselines': {'uid:t': {'db_average': 50.}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    traits = [{'uid': 't', 'name': 'T', 'profile': {'signs': {'Aries': 1}}}]
    monkeypatch.setattr(core, 'list_traits', lambda **kwargs: traits)
    uid = '' if draft_kind == 'without_uid' else 'DRAFTTRAIT001'
    original = chart(uid)
    saved = copy.deepcopy(original) if draft_kind == 'birth_edit' else None
    if saved is not None:
        conn = db._get_conn()
        with conn:
            conn.execute('INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,0,0,?)',
                         (uid, 'Saved', original.dt.isoformat(), '2026-01-01'))
        conn.close()
        db.upsert_chart_trait_likelihoods(uid, [{'trait_uid': 't', 'trait_name': 'T', 'likelihood': 62.,
                                               'trait_signature': trait_definition_signature(traits[0])}],
                                         chart_signature=chart_prediction_signature(original))
        original.lat = 12.
    monkeypatch.setattr(db, 'load_chart_by_uid', lambda value: copy.deepcopy(saved))
    before = db.get_chart_trait_likelihoods(uid) if uid else []
    calculated, presented, prompts, actions = [], [], [], []

    def calculate(value, selected, **kwargs):
        assert value is not original
        assert QThread.currentThread() != app.thread()
        calculated.append((value.chart_uid, value.lat))
        return {'T': 83.}

    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', calculate)
    monkeypatch.setattr(trait_evidence, '_ensure_trait_matches', lambda *a: {'T': {'positive': ['Sun in Aries']}})
    monkeypatch.setattr(core, '_apply_traits_prediction_metadata', lambda owner, selected, data, **kwargs: presented.append(copy.deepcopy(data)))
    monkeypatch.setattr(core, '_apply_traits_prediction_view', lambda *args, **kwargs: prompts.append(args[1]))
    owner = QWidget()
    owner.traits_prediction_label = QLabel(owner)
    owner._is_placeholder_chart = lambda value: False
    owner._predictions_use_trait_gender_distribution = draft_kind == 'gender_without_evidence'
    owner._predictions_manual_recalculation_only = True
    owner._set_prediction_header_action = lambda section, state: actions.append(state)
    try:
        core.render_traits_predictions(owner, original)
        core.start_traits_prediction_calculation(owner)
        wait_for(app, lambda: presented and presented[-1]['likelihoods'] == {'T': 83.})
        wait_for(app, lambda: not owner._traits_prediction_worker_jobs)
        assert (db.get_chart_trait_likelihoods(uid) if uid else []) == before
        prompt_count, result_count = len(prompts), len(presented)
        monkeypatch.setattr(index, 'results_for_uids', lambda *a, **k: pytest.fail('Completed draft fell back to persisted scores'))
        monkeypatch.setattr(core, '_start_traits_prediction_calculation', lambda *a: pytest.fail('Completed draft started another calculation'))
        for _ in range(2):
            core.render_traits_predictions(owner, original)
            app.processEvents()
        assert len(prompts) == prompt_count
        assert len(presented) == result_count + 2
        assert presented[-1]['likelihoods'] == {'T': 83.}
        assert presented[-1]['factor_matches'] == {'T': {'positive': ['Sun in Aries']}}
        assert actions[-1] == 'up_to_date'
        assert calculated == [(uid, original.lat)]
    finally:
        core.stop_traits_prediction_refresh_workers(owner, wait_msecs=5000)
        owner.deleteLater()
        app.processEvents()


def test_trait_receiver_rejects_draft_changed_after_work_started(app, monkeypatch, tmp_path):
    import json
    from PySide6.QtWidgets import QWidget
    from ephemeraldaddy.core import prediction_norms as norms
    from ephemeraldaddy.analysis.trait_prediction_metadata_cache import trait_metadata_cache_key
    from ephemeraldaddy.gui.features.charts import trait_predictions as facade

    core = facade._core
    paths = norms.PredictionNormPaths(tmp_path/'source.json', tmp_path/'official.json', tmp_path/'personal.json', tmp_path/'extra.json')
    paths.official.write_text(json.dumps({'version': 1, 'trait_baselines': {'uid:t': {'db_average': 50.}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    traits = [{'uid': 't', 'name': 'T', 'profile': {}}]
    original, owner, token = chart(''), QWidget(), object()
    owner._traits_prediction_render_token = token
    receiver = core._TraitPredictionsRefreshReceiver(owner, 'view', token, traits, chart=original,
                                                     metadata_cache_key=trait_metadata_cache_key(original, traits))
    rendered = []
    monkeypatch.setattr(core, 'render_traits_predictions', lambda owner, value: rendered.append(value))
    monkeypatch.setattr(core, '_apply_traits_prediction_metadata', lambda *a, **k: pytest.fail('Obsolete draft result was displayed'))
    try:
        original.lat = 12.
        receiver.handle_finished(token, {'likelihoods': {'T': 83.}})
        assert rendered == [original]
        assert not hasattr(original, '_trait_prediction_metadata_cache')
    finally:
        owner.deleteLater()
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
