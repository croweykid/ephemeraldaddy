"""Cross-consumer cache and invalidation contracts for the shared runtime."""
from __future__ import annotations
import copy
import json
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from ephemeraldaddy.analysis import trait_prediction_index as runtime
from ephemeraldaddy.analysis import trait_prediction_updates as updates
from ephemeraldaddy.analysis.trait_signatures import trait_definition_signature, chart_prediction_signature
from ephemeraldaddy.core import db, prediction_norms as norms


@pytest.fixture
def population(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'charts.db')
    paths = norms.PredictionNormPaths(tmp_path / 'source.json', tmp_path / 'official.json', tmp_path / 'personal.json', tmp_path / 'extensions.json')
    paths.selection.write_text(json.dumps({'source': 'my_database'}))
    paths.personal.write_text(json.dumps({'version': 1, 'snapshot_id': 'static', 'trait_baselines': {'uid:a': {'db_average': 50}, 'uid:b': {'db_average': 40}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    traits = [{'uid': 'a', 'name': 'Artist', 'profile': {'signs': {'Aries': 1}}}, {'uid': 'b', 'name': 'Builder', 'profile': {'signs': {'Taurus': 1}}}]
    charts = {f'RUNTIMEUID000{i}': SimpleNamespace(chart_uid=f'RUNTIMEUID000{i}', name=f'Chart {i}', dt=datetime(2000 + i, 1, 1, tzinfo=timezone.utc), lat=0., lon=0., birthtime_unknown=False, positions={'Sun': 10. * i}, houses=[], is_placeholder=False) for i in range(3)}
    conn = db._get_conn()
    with conn:
        for uid, chart in charts.items():
            conn.execute('INSERT INTO charts(chart_uid, name, datetime_iso, lat, lon, created_at) VALUES(?, ?, ?, 0, 0, ?)', (uid, chart.name, chart.dt.isoformat(), chart.dt.isoformat()))
    conn.close()
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda uids: {uid: copy.deepcopy(charts[uid]) for uid in uids if uid in charts})
    monkeypatch.setattr(db, 'load_chart_by_uid', lambda uid: copy.deepcopy(charts.get(uid)))
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    calls = []
    def scorer(chart, items, **kwargs):
        calls.append((chart.chart_uid, tuple(t['uid'] for t in items)))
        return {t['name']: 80. - int(chart.chart_uid[-1]) * 20 for t in items}
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', scorer)
    return index, traits, charts, calls, paths


def test_partial_refresh_preserves_other_trait_and_uses_static_not_cohort_mean(population):
    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    before = db.get_chart_trait_metadata('RUNTIMEUID0000')[1]
    changed = {**traits[0], 'profile': {'signs': {'Aries': 7}}}
    index.refresh_uids(charts, [changed])
    assert calls == [(uid, ('a', 'b')) for uid in charts] + [(uid, ('a',)) for uid in charts]
    assert db.get_chart_trait_metadata('RUNTIMEUID0000')[1] == before
    result = index.results_for_uids(charts, [changed, traits[1]])
    # Cohort mean is 60, authoritative DB norm is 50.
    assert result['RUNTIMEUID0000'].deviations['Artist'] == 30
    assert result['RUNTIMEUID0002'].deviations['Artist'] == -10
    conn = db._get_conn()
    assert conn.execute('SELECT COUNT(*) FROM trait_baseline_snapshots').fetchone()[0] == 0
    conn.close()


def test_cached_rankings_and_search_hydrate_and_score_zero_charts(population, monkeypatch):
    from ephemeraldaddy.analysis.trait_rankings import ranked_trait_rows
    from ephemeraldaddy.analysis.trait_search import membership_for_uids, matches_membership
    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    calls.clear()
    def forbidden(*args, **kwargs):
        raise AssertionError('Cached lookup must not hydrate charts or explain factors')
    monkeypatch.setattr(db, 'load_charts_by_uids', forbidden)
    monkeypatch.setattr(db, 'load_chart_by_uid', forbidden)
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', forbidden)
    rows = ranked_trait_rows(charts, traits[0])
    members = membership_for_uids(charts, [traits[0]])
    assert [r['chart_uid'] for r in rows] == ['RUNTIMEUID0000', 'RUNTIMEUID0001', 'RUNTIMEUID0002']
    assert matches_membership(members['RUNTIMEUID0002'], required_present=set(), excluded_present=set(), required_absent={'Artist'}, excluded_absent=set())
    assert not matches_membership(None, required_present=set(), excluded_present={'Artist'}, required_absent=set(), excluded_absent=set())
    assert not calls


@pytest.mark.parametrize('excluded', ['none', 'hidden', 'placeholder'])
def test_rankings_queues_only_requested_eligible_cells_and_selected_trait(population, monkeypatch, excluded):
    from ephemeraldaddy.analysis.trait_rankings import ranked_trait_rows

    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    untouched = db.get_chart_trait_likelihoods('RUNTIMEUID0002')
    other_trait = db.get_chart_trait_likelihoods('RUNTIMEUID0000')[1]
    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET lat=20 WHERE chart_uid IN ('RUNTIMEUID0000','RUNTIMEUID0002')")
        conn.execute("DELETE FROM chart_trait_likelihoods WHERE chart_uid='RUNTIMEUID0001' AND trait_uid='a'")
        conn.execute("DELETE FROM chart_trait_metadata WHERE chart_uid='RUNTIMEUID0001' AND trait_uid='a'")
        if excluded == 'placeholder':
            conn.execute("UPDATE charts SET is_placeholder=1 WHERE chart_uid='RUNTIMEUID0001'")
    conn.close()
    charts['RUNTIMEUID0000'].lat = charts['RUNTIMEUID0002'].lat = 20.
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    calls.clear()
    queued = []
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    scope = ['RUNTIMEUID0000', 'RUNTIMEUID0001']
    hidden = ['RUNTIMEUID0001'] if excluded == 'hidden' else []
    rows = ranked_trait_rows(scope, traits[0], hidden_uids=hidden, refresh_missing=True)
    assert [(row['chart_uid'], row['likelihood']) for row in rows] == [('RUNTIMEUID0000', 80.)]
    assert not calls
    assert len(queued) == 1
    fn, args, kwargs = queued.pop()
    expected = scope if excluded == 'none' else scope[:1]
    assert list(args[0]) == expected
    assert args[1] == [traits[0]]
    kwargs.pop('key')
    fn(*args, **kwargs)
    assert calls == [(uid, ('a',)) for uid in expected]
    assert db.get_chart_trait_likelihoods('RUNTIMEUID0002') == untouched
    assert db.get_chart_trait_likelihoods('RUNTIMEUID0000')[1] == other_trait
    ranked_trait_rows(scope, traits[0], hidden_uids=hidden, refresh_missing=True)
    assert not queued


def test_numeric_cache_reuses_each_trait_across_rename_recolor_roster_changes(population):
    index, traits, charts, calls, _ = population
    chart = charts['RUNTIMEUID0000']
    signature = chart_prediction_signature(chart)
    index.chart_likelihoods(chart, traits, chart_signature=signature)
    renamed = {**traits[0], 'name': 'Painter', 'profile': {**traits[0]['profile'], 'name': 'Painter', 'color': '#ffeeaa', 'description': 'new', 'astro_analysis': 'text', 'perceived_accuracy': 5}}
    assert trait_definition_signature(renamed) == trait_definition_signature(traits[0])
    assert index.chart_likelihoods(chart, [renamed], chart_signature=signature) == {'Painter': 80.}
    assert calls == [('RUNTIMEUID0000', ('a', 'b'))]
    assert norms.trait_norm_signature(renamed) == norms.trait_norm_signature(traits[0])


def test_partial_mixed_legacy_cache_is_readable_without_requiring_full_roster(population):
    index, traits, charts, _, _ = population
    db.upsert_chart_trait_likelihoods('RUNTIMEUID0000', [{'trait_uid': 'a', 'trait_name': 'old Artist label', 'likelihood': 77, 'trait_signature': 'legacy'}], chart_signature='old')
    result = index.results_for_uids(charts, traits, chart_signatures={'RUNTIMEUID0000': 'new'})['RUNTIMEUID0000']
    assert result.likelihoods == {'Artist': 77}
    assert result.deviations == {'Artist': 27}
    assert result.stale_chart_vector and result.stale_trait_definition


def test_static_document_is_parsed_once_and_rename_keeps_uid_reference(population, monkeypatch):
    index, traits, _, _, paths = population
    reads = []
    original = norms.json.loads
    monkeypatch.setattr(norms.json, 'loads', lambda value: (reads.append(value), original(value))[1])
    for _ in range(20):
        assert norms.trait_norm_values(traits)['Artist'] == 50
    assert len(reads) == 2  # source selection and selected population document
    changed = json.loads(paths.personal.read_text())
    changed['trait_baselines']['uid:b']['db_average'] = 21
    paths.personal.write_text(json.dumps(changed))
    before = norms.trait_norm_signature(traits[0])
    changed['trait_baselines']['uid:b']['db_average'] = 22
    paths.personal.write_text(json.dumps(changed))
    assert norms.trait_norm_signature(traits[0]) == before


def test_model_edit_refreshes_only_its_column_and_archive_delete_do_not_rescore(population, monkeypatch):
    index, traits, charts, calls, _ = population
    queued = []
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    updates.trait_changed(traits[0], change_type='definition_changed')
    assert len(queued) == 1
    fn, args, kwargs = queued.pop()
    kwargs.pop('key')
    fn(*args, **kwargs)
    assert calls == [(uid, ('a',)) for uid in charts]
    calls.clear()
    for operation in ('renamed', 'archived', 'unarchived', 'deleted'):
        updates.trait_changed(traits[0], change_type=operation)
    assert not queued and not calls
    assert not index.results_for_uids(charts, [traits[0]])


@pytest.mark.parametrize(('access', 'restart_index'), [('collection', False), ('search', True)])
def test_reactivated_edited_trait_refreshes_its_column_while_old_scores_remain_readable(population, monkeypatch, access, restart_index):
    from ephemeraldaddy.analysis.trait_search import membership_for_uids

    index, traits, charts, calls, paths = population
    index.refresh_uids(charts, traits)
    original_rows = {uid: db.get_chart_trait_likelihoods(uid) for uid in charts}
    other_metadata = {uid: db.get_chart_trait_metadata(uid)[1] for uid in charts}
    norm_document = paths.personal.read_bytes()
    if restart_index:
        index = runtime.TraitPredictionIndex()
        monkeypatch.setattr(runtime, '_INDEX', index)
    queued = []
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    updates.trait_changed(traits[0], change_type='archived')
    # Settings skips warming archived definitions. Reactivation only publishes
    # availability; the shared collector must discover the durable mismatch.
    revised = {**traits[0], 'profile': {'signs': {'Aries': 7}}}
    updates.trait_changed({'uid': 'a', 'name': 'Artist'}, change_type='unarchived')
    assert not queued
    calls.clear()

    def revised_scorer(chart, selected, **kwargs):
        calls.append((chart.chart_uid, tuple(t['uid'] for t in selected)))
        return {t['name']: 20. + int(chart.chart_uid[-1]) for t in selected}

    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', revised_scorer)
    selected = [revised, traits[1]]
    cached = index.results_for_uids(charts, selected)
    assert all(result.stale_trait_definition for result in cached.values())
    assert all(result.stale_trait_names == {'Artist'} for result in cached.values())
    if access == 'search':
        membership = membership_for_uids(charts, selected)
        assert 'artist' in membership['RUNTIMEUID0000'].above
        index.request_missing(charts, selected)
    else:
        result = index.collect(charts, selected)
        assert not result['partial']
        assert result['chart_count'] == len(charts)
        assert result['totals']['Artist'] == pytest.approx(1.8)
    assert {uid: db.get_chart_trait_likelihoods(uid) for uid in charts} == original_rows
    assert not calls
    assert len(queued) == 1
    fn, args, kwargs = queued.pop()
    assert set(args[0]) == set(charts)
    assert args[1] == (selected if access == 'search' else [revised])
    kwargs.pop('key')
    fn(*args, **kwargs)
    assert calls == [(uid, ('a',)) for uid in charts]
    refreshed = index.results_for_uids(charts, selected)
    assert [refreshed[uid].likelihoods['Artist'] for uid in charts] == [20., 21., 22.]
    assert all(not result.stale_trait_definition for result in refreshed.values())
    assert all(not result.stale_trait_names for result in refreshed.values())
    assert all('artist' in member.below for member in membership_for_uids(charts, selected).values())
    for uid in charts:
        assert db.get_chart_trait_likelihoods(uid)[1] == original_rows[uid][1]
        assert db.get_chart_trait_metadata(uid)[1] == other_metadata[uid]
    assert paths.personal.read_bytes() == norm_document

    # A subsequent availability/label change must reuse these repaired cells.
    renamed = {**revised, 'name': 'Painter', 'profile': {**revised['profile'], 'name': 'Painter', 'color': '#ffeeaa'}}
    for operation in ('archived', 'unarchived', 'renamed'):
        updates.trait_changed(renamed, change_type=operation)
    calls.clear()
    index.collect(charts, [renamed, traits[1]], calculate_missing=True)
    assert not calls and not queued


def test_collection_refreshes_only_mismatched_chart_trait_cells(population):
    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    conn = db._get_conn()
    with conn:
        conn.executemany('UPDATE chart_trait_likelihoods SET trait_signature = ? WHERE chart_uid = ? AND trait_uid = ?', [
            ('previous-definition', 'RUNTIMEUID0000', 'a'),
            ('previous-definition', 'RUNTIMEUID0001', 'b'),
        ])
    conn.close()
    # Simulate a new session without in-memory vectors masking actual work.
    index = runtime.TraitPredictionIndex()
    calls.clear()
    index.collect(charts, traits, calculate_missing=True)
    assert calls == [('RUNTIMEUID0000', ('a',)), ('RUNTIMEUID0001', ('b',))]
    assert all(not result.stale_trait_definition for result in index.results_for_uids(charts, traits).values())


def test_accuracy_review_replaces_definition_mismatches_before_ranking(population, monkeypatch):
    from ephemeraldaddy.analysis.trait_rankings import accuracy_rankings

    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    calls.clear()
    revised = {**traits[0], 'name': 'Painter', 'profile': {'signs': {'Aries': 7}}}

    def revised_scorer(chart, selected, **kwargs):
        calls.append((chart.chart_uid, tuple(t['uid'] for t in selected)))
        return {t['name']: 70. + int(chart.chart_uid[-1]) for t in selected}

    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', revised_scorer)
    ranked = accuracy_rankings(revised, lambda _: None, lambda: False)
    assert [(row['chart_uid'], row['likelihood']) for row in ranked] == [
        ('RUNTIMEUID0002', 72.), ('RUNTIMEUID0001', 71.), ('RUNTIMEUID0000', 70.),
    ]
    assert calls == [(uid, ('a',)) for uid in charts]


def test_chart_journal_ignores_tags_and_recalculates_only_astro_changed_uid(population, monkeypatch):
    index, traits, charts, _, _ = population
    monkeypatch.setattr(updates, 'list_traits', lambda **kwargs: traits)
    requested = []
    monkeypatch.setattr(index, 'request_refresh', lambda uids, selected: requested.append((set(uids), selected)))
    assert updates.synchronize_chart_changes() is False
    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET tags = 'cartoonist' WHERE chart_uid = 'RUNTIMEUID0000'")
    assert updates.synchronize_chart_changes() is False
    assert not requested
    with conn:
        conn.execute("UPDATE charts SET lat = 20 WHERE chart_uid = 'RUNTIMEUID0001'")
    assert updates.synchronize_chart_changes() is True
    assert requested[0][0] == {'RUNTIMEUID0001'}
    assert requested[0][1][:2] == traits
    assert {t['uid'] for t in requested[0][1][2:]} == {'dnd_alignment_good', 'dnd_alignment_evil', 'dnd_alignment_lawful', 'dnd_alignment_chaotic'}
    with conn:
        conn.execute("UPDATE charts SET is_placeholder = 1 WHERE chart_uid = 'RUNTIMEUID0000'")
    assert updates.synchronize_chart_changes() is False
    conn.close()


@pytest.mark.parametrize('completed_trait', [False, True])
def test_restart_recovers_only_unfinished_cells_for_astro_changed_chart(population, monkeypatch, completed_trait):
    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    unchanged = {uid: db.get_chart_trait_likelihoods(uid) for uid in ('RUNTIMEUID0000', 'RUNTIMEUID0002')}
    monkeypatch.setattr(updates, 'list_traits', lambda **kwargs: traits)
    queued = []
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    assert updates.synchronize_chart_changes() is False
    uid = 'RUNTIMEUID0001'
    charts[uid].lat = 20.
    conn = db._get_conn()
    with conn:
        conn.execute('UPDATE charts SET lat = 20 WHERE chart_uid = ?', (uid,))
    conn.close()
    db._chart_save_committed()
    assert queued
    if completed_trait:
        index.refresh_uids([uid], [traits[0]])

    # Exit before the queued refresh runs; a new session starts at the journal
    # head. Pending work must be recoverable from each durable cache cell.
    queued.clear()
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    updates._cursors.pop(str(db.DB_PATH), None)
    assert updates.synchronize_chart_changes() is False
    calls.clear()
    cached = index.results_for_uids(charts, traits)
    assert cached[uid].stale_chart_vector
    assert cached[uid].stale_trait_names == ({'Builder'} if completed_trait else {'Artist', 'Builder'})
    assert not cached['RUNTIMEUID0000'].stale_chart_vector
    assert not cached['RUNTIMEUID0002'].stale_chart_vector
    assert cached[uid].likelihoods == {'Artist': 60., 'Builder': 60.}
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    index.request_missing(charts, traits)
    fn, args, kwargs = queued.pop()
    kwargs.pop('key')
    fn(*args, **kwargs)
    assert calls == [(uid, ('b',) if completed_trait else ('a', 'b'))]
    assert all(not result.stale_chart_vector for result in index.results_for_uids(charts, traits).values())
    assert {key: db.get_chart_trait_likelihoods(key) for key in unchanged} == unchanged
    calls.clear()
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda *a: pytest.fail('Restart rehydrated completed or untouched charts'))
    index.collect(charts, traits, calculate_missing=True)
    assert not calls


@pytest.mark.parametrize('already_current', [False, True])
def test_legacy_cache_revision_is_checked_once_without_rescoring_matching_inputs(population, monkeypatch, already_current):
    index, traits, charts, calls, _ = population
    index.refresh_uids(charts, traits)
    uid = 'RUNTIMEUID0001'
    charts[uid].lat = 20.
    conn = db._get_conn()
    with conn:
        conn.execute('UPDATE charts SET lat = 20 WHERE chart_uid = ?', (uid,))
    if already_current:
        index.refresh_uids([uid], traits)
    # Simulate a database written by the previous version, with no checkpoints.
    with conn:
        for table in ('chart_trait_likelihoods', 'chart_trait_metadata'):
            conn.execute(f'ALTER TABLE {table} DROP COLUMN astro_revision')
            db._invalidate_table_columns_cache(table)
    conn.close()
    calls.clear()
    loaded = []
    original_loader = db.load_charts_by_uids
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda uids: (loaded.extend(uids), original_loader(uids))[1])
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    index.collect(charts, traits, calculate_missing=True)
    assert calls == ([] if already_current else [(uid, ('a', 'b'))])
    assert loaded == [uid]
    loaded.clear()
    index.collect(charts, traits, calculate_missing=True)
    assert not loaded


def test_legacy_import_notifies_only_inserted_cells_and_preserves_existing_scores(population, monkeypatch):
    from ephemeraldaddy.analysis import trait_cache_migration as migration

    index, traits, _, calls, _ = population
    index.refresh_uids(['RUNTIMEUID0001'], [traits[1]])
    before = db.get_chart_trait_likelihoods('RUNTIMEUID0001')
    calls.clear()
    events = []
    index.subscribe(lambda uids, trait_uids: events.append((uids, trait_uids)))
    monkeypatch.setattr(migration, '_imported', set())
    (db.DB_DIR/'.traits_distribution_likelihood_cache.json').write_text(json.dumps({
        'version': 4, 'profiles': [json.dumps(t['profile']) for t in traits],
        'profile_entries': [
            {'profile': 0, 'chart_uid': 'RUNTIMEUID0000', 'likelihood': 77.},
            {'profile': 0, 'chart_uid': 'RUNTIMEUID0000', 'likelihood': 78.},
            {'profile': 1, 'chart_uid': 'RUNTIMEUID0001', 'likelihood': 99.},
            {'profile': 0, 'chart_uid': 'MISSINGUID0000', 'likelihood': 88.},
        ],
    }))
    migration.import_legacy_trait_cache(traits)
    assert events == [(frozenset({'RUNTIMEUID0000'}), frozenset({'a'}))]
    assert db.get_chart_trait_likelihoods('RUNTIMEUID0000')[0]['likelihood'] == 77.
    assert db.get_chart_trait_likelihoods('RUNTIMEUID0001') == before
    migration.import_legacy_trait_cache(traits)
    migration._imported.clear()
    migration.import_legacy_trait_cache(traits)
    assert len(events) == 1
    assert not calls


def test_astro_edit_before_persistence_cannot_acknowledge_obsolete_scores(population, monkeypatch):
    index, traits, charts, _, _ = population
    index.refresh_uids(charts, traits)
    uid = 'RUNTIMEUID0001'
    before = db.get_chart_trait_likelihoods(uid)
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)

    def save_while_scoring(chart, selected, **kwargs):
        conn = db._get_conn()
        with conn:
            conn.execute('UPDATE charts SET lat = 20 WHERE chart_uid = ?', (uid,))
        conn.close()
        charts[uid].lat = 20.
        # The durable save happened, but its post-commit callback has not run.
        return {trait['name']: 99. for trait in selected}

    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', save_while_scoring)
    assert index.refresh_uids([uid], traits) == {}
    assert db.get_chart_trait_likelihoods(uid) == before
    assert index.results_for_uids([uid], traits)[uid].stale_chart_vector


def test_superseded_queued_trait_edit_cannot_write_old_results(population, monkeypatch):
    index, traits, charts, calls, _ = population
    queued = []
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    updates.trait_changed(traits[0], change_type='definition_changed')
    updates.trait_changed({**traits[0], 'profile': {'signs': {'Aries': 2}}}, change_type='definition_changed')
    for fn, args, kwargs in queued:
        kwargs.pop('key')
        fn(*args, **kwargs)
    assert calls == [(uid, ('a',)) for uid in charts]
    rows = db.get_chart_trait_likelihoods('RUNTIMEUID0000')
    assert rows[0]['trait_signature'] == trait_definition_signature({**traits[0], 'profile': {'signs': {'Aries': 2}}})


def test_cancellation_after_scoring_writes_nothing(population):
    index, traits, charts, calls, _ = population
    result = index.refresh_uids(charts, traits, should_cancel=lambda: bool(calls))
    assert result == {}
    assert not db.get_chart_trait_likelihoods('RUNTIMEUID0000')


def test_cancellation_during_saved_input_verification_writes_nothing(population, monkeypatch):
    from ephemeraldaddy.analysis.trait_chart_prediction import calculate_chart_prediction

    _, traits, charts, _, _ = population
    cancelled = False
    chart = charts['RUNTIMEUID0000']

    def verify_saved(uid):
        nonlocal cancelled
        cancelled = True
        return copy.deepcopy(chart)

    monkeypatch.setattr(db, 'load_chart_by_uid', verify_saved)
    assert calculate_chart_prediction(chart, traits, include_evidence=False, should_cancel=lambda: cancelled) is None
    assert not db.get_chart_trait_likelihoods(chart.chart_uid)


def test_v2_static_rows_use_recorded_or_valid_exact_rectified_house_mode(population):
    index, traits, charts, _, paths = population
    from ephemeraldaddy.analysis.prediction_norms_catalog import build_trait_norm_row
    rows = {'uid:a': build_trait_norm_row(key='uid:a', uid='a', name='Artist', profile_hash='old', source='official', with_houses_scores=[20, 40], without_houses_scores=[60, 80])}
    paths.personal.write_text(json.dumps({'catalog_version': 2, 'snapshot_id': 'v2', 'sections': {'traits': {'rows': rows}}}))
    index.refresh_uids(charts, [traits[0]])
    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET birthtime_unknown = 1 WHERE chart_uid IN ('RUNTIMEUID0001', 'RUNTIMEUID0002')")
        conn.execute("UPDATE charts SET retcon_time_used = 1, retcon_hour = 3, retcon_minute = 4 WHERE chart_uid = 'RUNTIMEUID0002'")
    conn.close()
    result = index.results_for_uids(charts, [traits[0]])
    assert result['RUNTIMEUID0000'].database_averages == {'Artist': 30}
    assert result['RUNTIMEUID0001'].database_averages == {'Artist': 70}
    assert result['RUNTIMEUID0002'].database_averages == {'Artist': 30}


def test_cache_write_and_read_do_not_rescan_chart_uid_migration(population, monkeypatch):
    index, traits, charts, _, _ = population
    monkeypatch.setattr(db, '_ensure_chart_uids', lambda conn: pytest.fail('Hot prediction I/O scanned all chart RUNTIMEUID000s'))
    index.refresh_uids(charts, traits)
    assert len(index.results_for_uids(charts, traits)) == 3


def test_partial_cache_remains_actionable_without_claiming_existing_norms_are_missing(population):
    index, traits, charts, _, _ = population
    index.refresh_uids(['RUNTIMEUID0000'], [traits[0]])
    result = index.results_for_uids(['RUNTIMEUID0000'], traits)['RUNTIMEUID0000']
    assert result.stale_trait_definition  # Missing Builder is still calculable.
    assert result.database_averages == {'Artist': 50., 'Builder': 40.}
    assert not result.stale_db_baseline
    assert result.deviations == {'Artist': 30.}


def test_batch_repository_restricts_selected_trait_in_sql(population):
    index, traits, charts, _, _ = population
    index.refresh_uids(charts, traits)
    rows = db.get_trait_prediction_rows_by_uids(charts, ['a'], trait_names=['Artist'])
    assert len(rows) == 3
    assert all(len(entries) == 2 and {row['trait_uid'] for row in entries} == {'a'} for entries in rows.values())


def test_v2_catalog_conversion_preserves_existing_predictor_sections(population):
    from ephemeraldaddy.analysis.prediction_norms_catalog import legacy_prediction_snapshot_to_catalog
    from ephemeraldaddy.core.prediction_norms import _legacy_projection
    original = {'version': 1, 'trait_baselines': {'uid:a': {'db_average': 50.}}, 'enneagram_type_raw_averages': {'1': 30}, 'enneagram_definition_signature': 'definition', 'distinguishing_metric_payloads': [{'groups': {}}], 'dnd_stat_raw_averages': {'STR': 42.}, 'theme_family_raw_averages': {'The Hero': 3.}}
    projected = _legacy_projection(legacy_prediction_snapshot_to_catalog(original))
    assert norms.trait_norm_values([{'uid':'a', 'name':'Artist'}], projected) == {'Artist':50.}
    for key in ('enneagram_type_raw_averages', 'enneagram_definition_signature', 'distinguishing_metric_payloads', 'dnd_stat_raw_averages', 'theme_family_raw_averages'):
        assert projected[key] == original[key]


def test_prediction_engines_import_without_qt_or_app():
    import subprocess
    result = subprocess.run([sys.executable, '-c', 'import sys; import ephemeraldaddy.analysis.trait_prediction_index; import ephemeraldaddy.analysis.trait_chart_prediction; import ephemeraldaddy.analysis.distinguishing_factors; import ephemeraldaddy.analysis.dnd.alignment_predictions; assert not any(n.startswith("PySide6") or n.startswith("ephemeraldaddy.gui") for n in sys.modules)'], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('mode', ['both', 'with_houses', 'without_houses', 'legacy'])
def test_accuracy_review_accepts_each_available_static_norm_mode(population, mode):
    from ephemeraldaddy.analysis.prediction_norms_catalog import build_trait_norm_row
    from ephemeraldaddy.analysis.trait_rankings import accuracy_rankings

    index, traits, charts, calls, paths = population
    if mode != 'legacy':
        row = build_trait_norm_row(
            key='uid:a', uid='a', name='Artist', profile_hash='old', source='official',
            with_houses_scores=[20, 40] if mode != 'without_houses' else [],
            without_houses_scores=[60, 80] if mode != 'with_houses' else [],
        )
        paths.personal.write_text(json.dumps({
            'catalog_version': 2, 'snapshot_id': 'accuracy-v2',
            'sections': {'traits': {'rows': {'uid:a': row}}},
        }))
    unknown_uids = ('RUNTIMEUID0001',) if mode == 'both' else tuple(charts) if mode == 'without_houses' else ()
    conn = db._get_conn()
    with conn:
        for uid in unknown_uids:
            charts[uid].birthtime_unknown = True
            conn.execute('UPDATE charts SET birthtime_unknown = 1 WHERE chart_uid = ?', (uid,))
    conn.close()
    index.refresh_uids(charts, [traits[0]])
    calls.clear()
    progress = []
    ranked = accuracy_rankings(traits[0], progress.append, lambda: False)
    expected = {
        'both': [('RUNTIMEUID0000', 50.), ('RUNTIMEUID0002', 10.)],
        'with_houses': [('RUNTIMEUID0000', 50.), ('RUNTIMEUID0001', 30.), ('RUNTIMEUID0002', 10.)],
        'without_houses': [('RUNTIMEUID0000', 10.)],
        'legacy': [('RUNTIMEUID0000', 30.), ('RUNTIMEUID0001', 10.)],
    }
    assert [(row['chart_uid'], row['deviation']) for row in ranked] == expected[mode]
    assert progress[-1] == 97.
    assert not calls


def test_accuracy_review_rejects_norms_without_a_usable_distribution(population):
    from ephemeraldaddy.analysis.prediction_norms_catalog import build_trait_norm_row
    from ephemeraldaddy.analysis.trait_rankings import accuracy_rankings

    _, traits, _, calls, paths = population
    row = build_trait_norm_row(
        key='uid:a', uid='a', name='Artist', profile_hash='old', source='official',
        with_houses_scores=[], without_houses_scores=[],
    )
    paths.personal.write_text(json.dumps({
        'catalog_version': 2, 'snapshot_id': 'empty-v2',
        'sections': {'traits': {'rows': {'uid:a': row}}},
    }))
    with pytest.raises(ValueError, match='Stored DB norm unavailable'):
        accuracy_rankings(traits[0], lambda _: None, lambda: False)
    assert not calls


@pytest.mark.parametrize('changed_input', ['gender', 'astro_data', 'trait_model', 'norm_row'])
def test_gender_overlay_cache_rejects_changed_request_inputs(population, changed_input):
    from ephemeraldaddy.analysis.trait_gender import gender_prediction_cache_key, retain_gender_prediction_metadata

    _, traits, charts, _, paths = population
    chart = charts['RUNTIMEUID0000']
    chart.gender = 'Female'
    selected = [traits[0]]
    signature = gender_prediction_cache_key(chart, selected)
    metadata = {'likelihoods': {'Artist': 81.}, 'gender_criterion_traits': ['Artist']}
    if changed_input == 'gender':
        chart.gender = 'Male'
    elif changed_input == 'astro_data':
        chart.lat = 25.
    elif changed_input == 'trait_model':
        traits[0]['profile']['signs']['Aries'] = 3
    else:
        payload = json.loads(paths.personal.read_text())
        payload['trait_baselines']['uid:a']['db_average'] = 30.
        paths.personal.write_text(json.dumps(payload))
    assert not retain_gender_prediction_metadata(chart, selected, metadata, expected_signature=signature)
    assert not hasattr(chart, '_trait_gender_prediction_metadata_cache')
    assert not db.get_chart_trait_likelihoods(chart.chart_uid)


@pytest.mark.parametrize('changed_input', ['uid', 'astro_data', 'trait_model', 'norm_row', 'roster', 'label'])
def test_completed_chart_metadata_rejects_changed_inputs(population, changed_input):
    from ephemeraldaddy.analysis.trait_prediction_metadata_cache import (
        cached_trait_prediction_metadata, retain_trait_prediction_metadata, trait_metadata_cache_key,
    )

    _, traits, charts, calls, paths = population
    chart = charts['RUNTIMEUID0000']
    selected = [traits[0]]
    signature = trait_metadata_cache_key(chart, selected)
    metadata = {'likelihoods': {'Artist': 83.}}
    assert retain_trait_prediction_metadata(chart, selected, metadata, expected_signature=signature)
    assert cached_trait_prediction_metadata(chart, selected) == metadata
    if changed_input == 'uid':
        chart.chart_uid = 'RUNTIMEUID0001'
    elif changed_input == 'astro_data':
        chart.lat = 20.
    elif changed_input == 'trait_model':
        traits[0]['profile']['signs']['Aries'] = 7
    elif changed_input == 'norm_row':
        payload = json.loads(paths.personal.read_text())
        payload['trait_baselines']['uid:a']['db_average'] = 30.
        paths.personal.write_text(json.dumps(payload))
    elif changed_input == 'roster':
        selected.append(traits[1])
    else:
        traits[0]['name'] = 'Painter'
    assert cached_trait_prediction_metadata(chart, selected) is None
    assert not retain_trait_prediction_metadata(chart, selected, metadata, expected_signature=signature)
    assert not calls
    assert not db.get_chart_trait_likelihoods(chart.chart_uid)


def test_completed_chart_metadata_isolated_from_display_edits_and_mutation(population):
    from ephemeraldaddy.analysis.trait_prediction_metadata_cache import (
        cached_trait_prediction_metadata, retain_trait_prediction_metadata, trait_metadata_cache_key,
    )

    _, traits, charts, calls, _ = population
    chart = charts['RUNTIMEUID0000']
    metadata = {'likelihoods': {'Artist': 83.}, 'factor_matches': {'Artist': {'positive': ['Sun in Aries']}}}
    signature = trait_metadata_cache_key(chart, traits)
    assert retain_trait_prediction_metadata(chart, traits, metadata, expected_signature=signature)
    metadata['likelihoods']['Artist'] = 0.
    display_copy = cached_trait_prediction_metadata(chart, traits)
    assert display_copy['likelihoods'] == {'Artist': 83.}
    display_copy['factor_matches']['Artist']['positive'].clear()
    chart.name, chart.tags, chart.notes, chart.gender = 'Renamed', ['cartoonist'], 'notes', 'Female'
    traits[0]['profile'].update(color='#ffeeaa', description='A description')
    assert trait_metadata_cache_key(chart, traits) == signature
    assert cached_trait_prediction_metadata(chart, traits)['factor_matches'] == {'Artist': {'positive': ['Sun in Aries']}}
    assert not calls


def test_gender_overlay_cannot_replace_base_chart_metadata(population):
    from ephemeraldaddy.analysis.trait_prediction_metadata_cache import (
        cached_trait_prediction_metadata, retain_trait_prediction_metadata, trait_metadata_cache_key,
    )

    _, traits, charts, _, _ = population
    chart = charts['RUNTIMEUID0000']
    signature = trait_metadata_cache_key(chart, traits)
    base = {'likelihoods': {'Artist': 83.}}
    assert retain_trait_prediction_metadata(chart, traits, base, expected_signature=signature)
    overlay = {'likelihoods': {'Artist': 90.}, 'gender_criterion_traits': ['Artist']}
    assert not retain_trait_prediction_metadata(chart, traits, overlay, expected_signature=signature)
    assert cached_trait_prediction_metadata(chart, traits) == base
