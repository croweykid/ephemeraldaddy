import ast
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.database_view.pending_refresh import (
    PendingChartChange, PendingChartRefreshSnapshot, acknowledge_refresh_snapshot,
)
from ephemeraldaddy.gui.features.controllers import main_window as module


@pytest.fixture(scope='module')
def adapter_methods():
    # Exercise the actual legacy window adapters without importing/constructing
    # the entire application and its unrelated GUI dependencies.
    tree = ast.parse(Path('ephemeraldaddy/gui/app.py').read_text())
    window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MainWindow')
    names = {'_record_manage_charts_pending_change', '_pending_manage_chart_refreshes', '_clear_pending_manage_chart_refreshes'}
    methods = [node for node in window.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    return ast.Module(body=methods, type_ignores=[])


@pytest.fixture
def environment(adapter_methods, monkeypatch):
    row_ids = {'A': 1, 'B': 2, 'C': 3}
    namespace = dict(PendingChartChange=PendingChartChange,
                     PendingChartRefreshSnapshot=PendingChartRefreshSnapshot,
                     acknowledge_refresh_snapshot=acknowledge_refresh_snapshot,
                     get_chart_id_by_uid=row_ids.get)
    exec(compile(adapter_methods, 'window-refresh-adapters', 'exec'), namespace)
    state = SimpleNamespace(
        _manage_charts_pending_changed_uids={},
        _manage_charts_full_refresh_pending=False,
        _manage_charts_full_refresh_token=None,
        _normalized_chart_uid_key=lambda uid: uid,
    )
    for name in ('_record_manage_charts_pending_change', '_pending_manage_chart_refreshes', '_clear_pending_manage_chart_refreshes'):
        setattr(state, name, MethodType(namespace[name], state))
    scheduled, refreshes, events = [], [], []
    hooks = SimpleNamespace(on_show=lambda: None, on_refresh=lambda: None)
    class Dialog:
        _chart_rows = [object()]
        def isVisible(self): return False
        def show(self): hooks.on_show()
        def _refresh_charts(self, **kwargs):
            refreshes.append(kwargs)
            hooks.on_refresh()
    class App:
        def processEvents(self):
            if events: events.pop(0)()
    monkeypatch.setattr(module, 'QTimer', SimpleNamespace(singleShot=lambda delay, callback: scheduled.append(callback)))
    monkeypatch.setattr(module, 'QApplication', SimpleNamespace(instance=lambda: App()))
    controller = module.ChartsController(
        confirm_discard_or_save=lambda: True,
        get_or_create_manage_dialog=Dialog,
        raise_manage_dialog=lambda: None,
        get_pending_changed_refreshes=state._pending_manage_chart_refreshes,
        clear_pending_changed_refreshes=state._clear_pending_manage_chart_refreshes,
    )
    timing = SimpleNamespace(phase=lambda *a, **kw: None, complete=lambda **kw: None)
    def open_view(startup=False):
        return controller.open_manage_charts(open_timing=timing, progress_callback=(lambda *a: None) if startup else None)
    return SimpleNamespace(state=state, scheduled=scheduled, refreshes=refreshes,
                           events=events, hooks=hooks, open=open_view, row_ids=row_ids)


def record(env, uid, metrics=True, deleted=False):
    env.state._record_manage_charts_pending_change(uid, refresh_metrics=metrics, deleted=deleted)
    if deleted:
        env.row_ids.pop(uid, None)


@pytest.mark.parametrize('new_metrics', [False, True])
def test_deferred_refresh_preserves_new_uid_and_later_change_to_same_uid(environment, new_metrics):
    env = environment
    record(env, 'A', metrics=False)
    env.open()
    record(env, 'A', metrics=new_metrics)
    record(env, 'B', metrics=False)
    env.scheduled.pop(0)()
    assert env.refreshes[0]['changed_ids'] == {1}
    assert not env.refreshes[0]['refresh_metrics']
    assert set(env.state._manage_charts_pending_changed_uids) == {'A', 'B'}
    env.open()
    env.scheduled.pop(0)()
    assert env.refreshes[1]['changed_ids'] == {1, 2}
    assert env.refreshes[1]['refresh_metrics'] == new_metrics
    assert not env.state._manage_charts_pending_changed_uids


def test_later_same_uid_metrics_edit_is_not_acknowledged_by_older_snapshot(environment):
    env = environment
    record(env, 'A')
    env.open()
    record(env, 'A')
    env.scheduled.pop(0)()
    assert 'A' in env.state._manage_charts_pending_changed_uids


def test_new_deletion_keeps_full_refresh_pending_after_older_full_refresh(environment):
    env = environment
    record(env, 'A', deleted=True)
    env.open()
    record(env, 'B', deleted=True)
    env.scheduled.pop(0)()
    assert env.state._manage_charts_full_refresh_pending
    assert set(env.state._manage_charts_pending_changed_uids) == {'B'}
    assert 'changed_ids' not in env.refreshes[0]
    env.open()
    env.scheduled.pop(0)()
    assert 'changed_ids' not in env.refreshes[1]
    assert not env.state._manage_charts_full_refresh_pending
    assert not env.state._manage_charts_pending_changed_uids


def test_startup_process_events_cannot_drop_new_metrics_or_deletion_work(environment):
    env = environment
    record(env, 'A', metrics=False)
    def change_during_events():
        record(env, 'A')
        record(env, 'B', deleted=True)
    env.events.append(change_during_events)
    env.open(startup=True)
    assert env.refreshes[0]['changed_ids'] == {1} and not env.refreshes[0]['refresh_metrics']
    assert set(env.state._manage_charts_pending_changed_uids) == {'A', 'B'}
    assert env.state._manage_charts_full_refresh_pending


def test_reentrant_refresh_change_stays_pending(environment):
    env = environment
    record(env, 'A')
    env.hooks.on_refresh = lambda: record(env, 'A')
    env.open()
    env.scheduled.pop(0)()
    assert 'A' in env.state._manage_charts_pending_changed_uids


@pytest.mark.parametrize('startup', [False, True])
def test_failed_refresh_does_not_acknowledge_captured_work(environment, startup):
    env = environment
    record(env, 'A', deleted=True)
    def fail(): raise RuntimeError('database unavailable')
    env.hooks.on_refresh = fail
    with pytest.raises(RuntimeError, match='database unavailable'):
        env.open(startup=startup)
        if not startup:
            env.scheduled.pop(0)()
    assert 'A' in env.state._manage_charts_pending_changed_uids
    assert env.state._manage_charts_full_refresh_pending


def test_no_refresh_branch_preserves_changes_recorded_while_showing_dialog(environment):
    env = environment
    env.hooks.on_show = lambda: record(env, 'B')
    env.open()
    assert not env.scheduled and not env.refreshes
    assert 'B' in env.state._manage_charts_pending_changed_uids
