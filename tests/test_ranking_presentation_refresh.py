"""Run actual row-refresh, Rankings and Search gates without app.py's UI."""
from __future__ import annotations
import __future__
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from ephemeraldaddy.analysis import trait_prediction_index as runtime
from ephemeraldaddy.analysis import trait_prediction_updates as updates
from ephemeraldaddy.analysis.trait_rankings import ranked_trait_rows
from ephemeraldaddy.analysis.trait_signatures import trait_definition_signature
from ephemeraldaddy.core import db, prediction_norms as norms


def _method(path, name, namespace):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, 'exec', flags=__future__.annotations.compiler_flag), namespace)
    return namespace[name]


_APP = 'ephemeraldaddy/gui/app.py'
_RANKINGS = 'ephemeraldaddy/gui/ranking_panel_core.py'
_matches_trait_filters = _method('ephemeraldaddy/gui/dbv_search_panel.py', 'chart_matches_trait_filters', {})


class _RankingView:
    _refresh_charts = _method(_APP, '_refresh_charts', {'list_charts': db.list_charts})
    _refresh_visible_rankings_sections = _method(_RANKINGS, '_refresh_visible_rankings_sections', {})
    _rankings_database_chart_uids = _method(_RANKINGS, '_rankings_database_chart_uids', {'get_chart_uid_map': db.get_chart_uid_map})

    def __init__(self, trait):
        self.trait = trait
        self._chart_rows = db.list_charts()
        self._chart_cache = {}
        self._rankings_data_dirty = True
        self._active_left_panel = 'rankings'
        self._left_panel_visible = True
        self._rankings_section_expanded = {'traits': True}
        self.rendered = []
        self.refreshes = 0
        self._refresh_visible_rankings_sections()

    def _refresh_rankings_panel(self, sections):
        assert sections == {'traits'}
        self.refreshes += 1
        self.rendered = ranked_trait_rows(self._rankings_database_chart_uids(), self.trait)

    def _get_chart_for_filter(self, row):
        if row not in self._chart_cache:
            values = next(item for item in self._chart_rows if item[0] == row)
            self._chart_cache[row] = SimpleNamespace(chart_uid=values[30], name=values[1], is_placeholder=bool(values[15]))
        return self._chart_cache[row]

    def _local_row_ids_for_uids(self, uids):
        return {row[0] for row in self._chart_rows if row[30] in uids}

    _normalized_chart_uid_key = staticmethod(lambda uid: str(uid).strip().upper())
    _normalize_rankings_chart_uid = staticmethod(lambda uid: str(uid).strip().upper())
    _normalize_chart_row = staticmethod(lambda row: row)
    _is_placeholder_chart = staticmethod(lambda chart: chart.is_placeholder)
    _rebuild_hydrated_chart_identity_indexes = lambda self: None
    _refresh_collection_list_widget = lambda self: None
    _refresh_personal_transit_chart_options = lambda self: None
    _refresh_similarities_chart_options = lambda self: None
    _populate_list = lambda self, **kwargs: None


@pytest.fixture
def view(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_DIR', tmp_path)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'charts.db')
    paths = norms.PredictionNormPaths(tmp_path / 'source.json', tmp_path / 'official.json', tmp_path / 'personal.json', tmp_path / 'extension.json')
    paths.official.write_text(json.dumps({'version': 1, 'trait_baselines': {'uid:a': {'db_average': 50}}}))
    monkeypatch.setattr(norms, 'default_norm_paths', lambda: paths)
    trait = {'uid': 'a', 'name': 'Artist', 'profile': {}}
    conn = db._get_conn()
    with conn:
        conn.executemany('INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,0,0,?)', [
            (uid, name, '2000-01-01T00:00:00+00:00', '2026-01-01')
            for uid, name in [('RANKTEST000001', 'Original'), ('RANKTEST000002', 'Other')]
        ])
    conn.close()
    for uid, score in [('RANKTEST000001', 80.), ('RANKTEST000002', 60.)]:
        db.upsert_chart_trait_likelihoods(uid, [{'trait_uid': 'a', 'trait_name': 'Artist', 'likelihood': score,
                                              'trait_signature': trait_definition_signature(trait)}], chart_signature='unchanged')
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, '_INDEX', index)
    monkeypatch.setattr(runtime, 'calculate_trait_likelihoods', lambda *a, **k: pytest.fail('Presentation changes rescored Traits'))
    monkeypatch.setattr(index, 'request_refresh', lambda *a, **k: pytest.fail('Presentation changes queued a score refresh'))
    updates.synchronize_chart_changes()
    return _RankingView(trait)


def _save_display_change(statement, *values):
    conn = db._get_conn()
    with conn:
        conn.execute(statement, values)
    conn.close()
    # Match the save path consuming its score journal before Database View reloads.
    db._chart_save_committed()
    assert updates.synchronize_chart_changes() is False


def _enable_trait_search(view, monkeypatch):
    from ephemeraldaddy.analysis import traits

    monkeypatch.setattr(traits, 'list_traits', lambda **kwargs: [view.trait])
    # Completion delivery is covered by real Qt tests. Run the queued index work
    # explicitly here so score/hydration assertions also cover request_missing.
    view._trait_search_refresh_relay = object()
    queued = []
    index = runtime.global_trait_prediction_index()
    monkeypatch.setattr(index, 'enqueue', lambda fn, *args, **kwargs: queued.append((fn, args, kwargs)))
    monkeypatch.setattr(db, 'load_charts_by_uids', lambda *a, **k: pytest.fail('Warm Search hydrated charts'))
    monkeypatch.setattr(db, 'load_chart_by_uid', lambda *a, **k: pytest.fail('Warm Search hydrated a chart'))

    def populate(**kwargs):
        view.search_uids = {
            row[30] for row in view._chart_rows
            if not row[15] and _matches_trait_filters(
                view, view._get_chart_for_filter(row[0]),
                required_present_traits={'Artist'}, excluded_present_traits=set(),
                required_absent_traits=set(), excluded_absent_traits=set(),
            )
        }

    monkeypatch.setattr(view, '_populate_list', populate)
    populate()
    return queued


def _drain_missing(queued, expected_uids):
    assert len(queued) == 1
    fn, args, kwargs = queued.pop()
    assert set(args[0]) == expected_uids
    kwargs.pop('key')
    fn(*args, **kwargs)


@pytest.mark.parametrize('initial_placeholder', [True, False])
def test_search_membership_tracks_eligibility_without_rescoring(view, monkeypatch, initial_placeholder):
    uid = 'RANKTEST000001'
    saved = db.get_chart_trait_likelihoods(uid)
    _save_display_change('UPDATE charts SET is_placeholder = ? WHERE chart_uid = ?', int(initial_placeholder), uid)
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    revision = runtime.global_trait_prediction_index().revision
    queued = _enable_trait_search(view, monkeypatch)

    for step, placeholder in enumerate((initial_placeholder, not initial_placeholder, initial_placeholder)):
        if step:
            _save_display_change('UPDATE charts SET is_placeholder = ? WHERE chart_uid = ?', int(placeholder), uid)
            view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
        expected = {'RANKTEST000002'} | (set() if placeholder else {uid})
        assert view.search_uids == expected
        assert set(view._trait_search_membership[1]) == expected
        _drain_missing(queued, expected)
        assert runtime.global_trait_prediction_index().revision == revision
        assert db.get_chart_trait_likelihoods(uid) == saved


def test_placeholder_exclusion_and_reactivation_refresh_visible_rankings_without_scores(view):
    saved = db.get_chart_trait_likelihoods('RANKTEST000001')
    assert [row['name'] for row in view.rendered] == ['Original', 'Other']
    _save_display_change("UPDATE charts SET is_placeholder = 1 WHERE chart_uid = 'RANKTEST000001'")
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    assert [row['name'] for row in view.rendered] == ['Other']
    _save_display_change("UPDATE charts SET is_placeholder = 0 WHERE chart_uid = 'RANKTEST000001'")
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    assert [row['name'] for row in view.rendered] == ['Original', 'Other']
    assert view.refreshes == 3
    assert db.get_chart_trait_likelihoods('RANKTEST000001') == saved


def test_name_change_refreshes_labels_using_unchanged_scores(view):
    saved = db.get_chart_trait_likelihoods('RANKTEST000001')
    _save_display_change("UPDATE charts SET name = 'Renamed' WHERE chart_uid = 'RANKTEST000001'")
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    assert [row['name'] for row in view.rendered] == ['Renamed', 'Other']
    assert view.refreshes == 2
    assert db.get_chart_trait_likelihoods('RANKTEST000001') == saved


def test_hidden_rankings_defer_display_refresh_until_revealed(view):
    view._left_panel_visible = False
    _save_display_change("UPDATE charts SET name = 'Renamed' WHERE chart_uid = 'RANKTEST000001'")
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    assert view.refreshes == 1
    assert view._rankings_data_dirty
    view._left_panel_visible = True
    view._refresh_visible_rankings_sections()
    assert [row['name'] for row in view.rendered] == ['Renamed', 'Other']
    assert not view._rankings_data_dirty


def test_tags_and_unmodified_rows_do_not_refresh_rankings_or_search_membership(view, monkeypatch):
    queued = _enable_trait_search(view, monkeypatch)
    _drain_missing(queued, {'RANKTEST000001', 'RANKTEST000002'})
    membership = view._trait_search_membership
    _save_display_change("UPDATE charts SET tags = 'cartoonist' WHERE chart_uid = 'RANKTEST000001'")
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    view._refresh_charts(refresh_metrics=False, refresh_tag_completers=False)
    assert view.refreshes == 1
    assert not view._rankings_data_dirty
    assert view._trait_search_membership is membership
    assert not queued
