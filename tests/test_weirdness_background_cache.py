"""A chart save must win over a Weirdness worker's older input snapshot."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from ephemeraldaddy.analysis import weirdness_cache as runtime
from ephemeraldaddy.core import db


@pytest.fixture
def population(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'charts.db')
    charts = {uid: SimpleNamespace(chart_uid=uid, dt=datetime(2000, 1, 1, tzinfo=timezone.utc), lat=lat, lon=0., birthtime_unknown=False, is_placeholder=False)
              for uid, lat in [('WEIRDCACHE0001', 0.), ('WEIRDCACHE0002', 10.)]}
    conn = db._get_conn()
    with conn:
        for uid, chart in charts.items():
            conn.execute('INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,?,0,?)',
                         (uid, uid, chart.dt.isoformat(), chart.lat, chart.dt.isoformat()))
    conn.close()
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda uids: {uid: copy.deepcopy(charts[uid]) for uid in uids if uid in charts})
    monkeypatch.setattr(runtime, 'distinguishing_norm_reference', lambda: (({},), 'static'))
    monkeypatch.setattr(runtime, 'calculate_weirdness_score_from_metric_payloads', lambda chart, payloads: (100. + chart.lat, 6))
    return charts


def score_row(uid):
    conn = db._get_conn()
    try:
        return conn.execute('SELECT weirdness_score, weirdness_formula_version, weirdness_norm_signature FROM charts WHERE chart_uid=?', (uid,)).fetchone()
    finally:
        conn.close()


def test_birth_edit_during_calculation_preserves_newer_score_and_drops_delivery(population, monkeypatch):
    uid = 'WEIRDCACHE0001'
    def calculate(chart, payloads):
        if chart.chart_uid == uid:
            conn = db._get_conn()
            with conn:
                conn.execute('UPDATE charts SET lat = 20 WHERE chart_uid=?', (uid,))
                conn.execute("UPDATE charts SET weirdness_score=900, weirdness_formula_version=99, weirdness_norm_signature='newer' WHERE chart_uid=?", (uid,))
            conn.close()
        return 100. + chart.lat, 6
    monkeypatch.setattr(runtime, 'calculate_weirdness_score_from_metric_payloads', calculate)
    result = runtime.refresh_weirdness_scores(population)
    assert result == {'WEIRDCACHE0002': 110.}
    assert score_row(uid) == (900., 99, 'newer')


def test_unchanged_and_identical_cached_scores_are_both_delivered(population):
    expected = {'WEIRDCACHE0001': 100., 'WEIRDCACHE0002': 110.}
    assert runtime.refresh_weirdness_scores(population) == expected
    assert runtime.refresh_weirdness_scores(population) == expected


def test_birth_edit_after_score_commit_invalidates_only_that_charts_metadata(population):
    runtime.refresh_weirdness_scores(population)
    other_before = score_row('WEIRDCACHE0002')
    conn = db._get_conn()
    with conn:
        conn.execute('UPDATE charts SET birthtime_unknown=1 WHERE chart_uid=?', ('WEIRDCACHE0001',))
    conn.close()
    assert score_row('WEIRDCACHE0001') == (100., None, None)
    assert score_row('WEIRDCACHE0002') == other_before


def test_tag_save_keeps_weirdness_validity(population):
    runtime.refresh_weirdness_scores(population)
    before = score_row('WEIRDCACHE0001')
    conn = db._get_conn()
    with conn:
        conn.execute("UPDATE charts SET tags='cartoonist', name='Renamed' WHERE chart_uid=?", ('WEIRDCACHE0001',))
    conn.close()
    assert score_row('WEIRDCACHE0001') == before


def test_guarded_writer_rejects_a_save_but_preserves_legacy_no_change_result(population):
    uid = 'WEIRDCACHE0001'
    revision = db.chart_astro_revisions([uid])[uid]
    args = {'formula_version': runtime.DISTINGUISHING_FORMULA_VERSION, 'norm_signature': 'static'}
    assert db.update_chart_weirdness_score_by_uid(uid, 100., expected_astro_revision=revision, **args)
    assert db.update_chart_weirdness_score_by_uid(uid, 100., expected_astro_revision=revision, **args)
    assert not db.update_chart_weirdness_score_by_uid(uid, 100., **args)
    conn = db._get_conn()
    with conn:
        conn.execute('UPDATE charts SET lon=12 WHERE chart_uid=?', (uid,))
    conn.close()
    assert not db.update_chart_weirdness_score_by_uid(uid, 99., expected_astro_revision=revision, **args)
    assert score_row(uid) == (100., None, None)
