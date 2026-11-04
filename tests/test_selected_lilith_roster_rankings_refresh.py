"""Behavioral tests for Lilith mode's rankings and roster refresh.

Extract only the callback from app.py so this test does not import the GUI
application or require a display server.
"""

import ast
from pathlib import Path
from types import SimpleNamespace


SOURCE = Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"


def _callback():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    methods = [
        child
        for owner in tree.body if isinstance(owner, ast.ClassDef)
        for child in owner.body
        if isinstance(child, ast.FunctionDef)
        and child.name == "_on_selected_lilith_mode_changed"
    ]
    assert len(methods) == 1
    body = ast.Module(body=[methods[0]], type_ignores=[])
    events = []
    namespace = {
        "MainWindow": type("MainWindow", (), {}),
        "save_lilith_mode": lambda settings, mode: events.append(("save", mode)),
        "invalidate_all_dominant_weight_caches": lambda: events.append(("sqlite",)),
    }
    exec(compile(ast.fix_missing_locations(body), str(SOURCE), "exec"), namespace)
    return namespace["_on_selected_lilith_mode_changed"], events


def _fake_window(events, *, visible, active, filters, collapsed=False):
    def refresh_rankings():
        events.append(("rankings", window._rankings_data_dirty))
        if window._rankings_data_dirty:
            window._rankings_data_dirty = False

    window = SimpleNamespace(
        _settings=object(),
        _chart_cache={"old": "scores"},
        _rankings_data_dirty=False,
        _database_metrics_preloaded_sections={"signs"},
        _database_metrics_background_preload_sections={"planets"},
        _left_panel_visible=visible,
        _active_left_panel=active,
        _invalidate_database_metrics_cache=lambda: events.append(("metrics",)),
        _clear_similar_charts_popout_cache=lambda: events.append(("similarity_cache",)),
        _has_active_astrological_filters=lambda: filters,
        _on_filter_changed=lambda: events.append(("filter_refresh",)),
        _owner_window=lambda: None,
        _is_left_panel_collapsed=lambda: collapsed,
        _refresh_visible_rankings_sections=refresh_rankings,
    )
    return window


def test_active_rankings_recalculates_after_changing_lilith():
    callback, events = _callback()
    window = _fake_window(events, visible=True, active="rankings", filters=False)
    callback(window, "Natural Lilith")
    assert ("rankings", True) in events
    assert window._rankings_data_dirty is False  # Successful visible refresh.
    assert not window._chart_cache
    assert not window._database_metrics_preloaded_sections
    assert not window._database_metrics_background_preload_sections
    assert ("filter_refresh",) not in events


def test_hidden_rankings_remains_dirty_and_active_search_reapplies():
    callback, events = _callback()
    window = _fake_window(events, visible=False, active="rankings", filters=True)
    callback(window, "Mean Lilith")
    assert window._rankings_data_dirty is True
    assert ("filter_refresh",) in events
    assert all(event[0] != "rankings" for event in events)
    assert events.index(("filter_refresh",)) < len(events)


def test_collapsed_rankings_keeps_dirty_state_and_refreshes_search():
    callback, events = _callback()
    window = _fake_window(events, visible=True, active="rankings", filters=True, collapsed=True)
    callback(window, "Osculating Lilith")
    assert window._rankings_data_dirty is True
    assert ("filter_refresh",) in events
    assert all(event[0] != "rankings" for event in events)


def test_unrelated_search_without_astrological_filter_does_not_repopulate():
    callback, events = _callback()
    window = _fake_window(events, visible=False, active="rankings", filters=False)
    callback(window, "Natural Lilith")
    assert ("filter_refresh",) not in events
    assert window._rankings_data_dirty is True
