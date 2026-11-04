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
