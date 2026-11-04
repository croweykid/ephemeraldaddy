"""Execute the row/filter adapters without importing the giant application UI."""
import ast
import __future__
from pathlib import Path
from types import SimpleNamespace

import pytest

APP = Path('ephemeraldaddy/gui/app.py').read_text(encoding='utf-8')


def method(name):
    tree = ast.parse(APP)
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def compiled_method(name, namespace):
    node = method(name)
    node.returns = None
    for arg in node.args.args + node.args.kwonlyargs:
        arg.annotation = None
    node = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(node, '<app adapter>', 'exec', flags=__future__.annotations.compiler_flag), namespace)
    return namespace[name]


def test_normalization_preserves_flag_and_metadata_across_repeated_calls():
    normalize = compiled_method('_normalize_chart_row', dict(_normalize_gui_source=lambda x:x, SOURCE_PERSONAL='Personal'))
    window = SimpleNamespace()
    row = [None] * 36
    row[0], row[30], row[32], row[33], row[35] = 1, 'ABC', 7, 'signature', 1
    normalized = normalize(window, row)
    assert len(normalized) == 33 and normalized[32] is True
    assert normalize(window, normalized) == normalized
    assert window._weirdness_cache_metadata_by_uid['ABC'] == (7, 'signature')
    legacy = row[:32]
    assert normalize(window, legacy)[32] is False


@pytest.mark.parametrize('mode, flag, expected', [(1,False,False),(2,True,False),(0,True,True),(1,True,True),(2,False,True)])
def test_provenance_predicate(mode, flag, expected):
    # Run the real provenance prefilter before the unchanged complex predicates.
    node = method('_chart_matches_filters')
    start = next(i for i, stmt in enumerate(node.body) if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'provenance_control' for t in stmt.targets))
    stop = next(i for i, stmt in enumerate(node.body) if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'incomplete_birthdate_state' for t in stmt.targets))
    node.body = node.body[start:stop] + [ast.Return(value=ast.Constant(True))]
    node.returns = None
    node.args.kwonlyargs=[]; node.args.kw_defaults=[]
    for arg in node.args.args: arg.annotation=None
    namespace = dict(QuadStateSlider=SimpleNamespace(MODE_EMPTY=0,MODE_TRUE=1,MODE_FALSE=2))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<provenance predicate>', 'exec'), namespace)
    window = SimpleNamespace(auto_generated_checkbox=SimpleNamespace(mode=lambda:mode))
    assert namespace['_chart_matches_filters'](window, [None]*32+[flag]) is expected


@pytest.mark.parametrize('length', [33, 36])
def test_weirdness_refresh_preserves_provenance(length):
    chart = SimpleNamespace()
    window = SimpleNamespace(
        _weirdness_norm_signature=lambda rows: 'new signature',
        _prediction_norm_metric_payloads=lambda: {},
        _get_chart_for_filter=lambda row_id: chart,
        _is_placeholder_chart=lambda chart: False,
    )
    hydrate = compiled_method('_hydrate_missing_weirdness_scores_for_sort', dict(
        _DISTINGUISHING_FORMULA_VERSION=7,
        _calculate_weirdness_score_from_metric_payloads=lambda chart, payload: (0.5, 1),
        update_chart_weirdness_score=lambda *args, **kwargs: None,
    ))
    row = [None] * length
    row[0], row[30], row[-1] = 1, 'ABC', True
    result = hydrate(window, [tuple(row)])[0]
    assert len(result) == length and result[-1] is True
    assert result[31] == 0.5
    assert window._weirdness_cache_metadata_by_uid['ABC'] == (7, 'new signature')


def test_search_control_is_connected_and_part_of_active_and_reset_paths():
    panel = Path('ephemeraldaddy/gui/dbv_search_panel.py').read_text(encoding='utf-8')
    assert 'window.auto_generated_checkbox.modeChanged.connect(window._on_filter_changed)' in panel
    assert 'window.auto_generated_checkbox.mode() == QuadStateSlider.MODE_EMPTY' in panel
    clear = ast.get_source_segment(APP, method('_clear_filters'))
    assert 'self.auto_generated_checkbox.setMode(QuadStateSlider.MODE_EMPTY)' in clear
