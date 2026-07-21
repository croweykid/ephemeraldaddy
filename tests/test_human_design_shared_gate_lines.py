import sys
import types
from types import SimpleNamespace

hd_reference_stub = types.ModuleType("ephemeraldaddy.analysis.human_design_reference")
hd_reference_stub.canonicalize_hd_authority_label = lambda value: value
sys.modules.setdefault("ephemeraldaddy.analysis.human_design_reference", hd_reference_stub)

from ephemeraldaddy.gui.features.charts.human_design_shared import compute_common_human_design_aggregates


def _extract(chart):
    return (
        chart.gates,
        [],
        [],
        [],
        "",
        "",
    )


def _profile(_chart):
    return ""


def _sort_matches(counts, total):
    return [(label, count, total) for label, count in counts.items() if count >= 2]


def test_common_gate_lines_are_counted_by_overlapping_gate_line():
    charts = [
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 1)]),
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 1), (42, 6)]),
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 6)]),
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 4)]),
    ]

    aggregates = compute_common_human_design_aggregates(
        charts,
        extract_profile=_extract,
        chart_profile=_profile,
        sort_matches=_sort_matches,
        defined_center_order=(),
        authority_order=(),
        profile_order=(),
    )

    assert aggregates.gates == [("Gate 42", 4, 4)]
    assert aggregates.gate_lines == [("42.1", 2, 4), ("42.6", 2, 4)]


def test_common_gate_lines_can_be_empty_when_shared_gates_have_unique_lines():
    charts = [
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 1)]),
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 2)]),
        SimpleNamespace(gates=[42], human_design_gate_lines=[(42, 4)]),
    ]

    aggregates = compute_common_human_design_aggregates(
        charts,
        extract_profile=_extract,
        chart_profile=_profile,
        sort_matches=_sort_matches,
        defined_center_order=(),
        authority_order=(),
        profile_order=(),
    )

    assert aggregates.gates == [("Gate 42", 3, 3)]
    assert aggregates.gate_lines == []
