import sys
from types import ModuleType, SimpleNamespace

style_stub = ModuleType("ephemeraldaddy.gui.style")
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#c8945c"
style_stub.CHART_DATA_DIVIDER = "────────────────"
style_stub.DARK_THEME = {"background": "#111111", "foreground": "#eeeeee"}
style_stub.blend_hex_colors = lambda first, second, ratio=0.5: first
style_stub.format_chart_header = lambda *_args, **_kwargs: ""
sys.modules.setdefault("ephemeraldaddy.gui.style", style_stub)

from ephemeraldaddy.gui.features.charts.human_design_shared import (
    compute_common_human_design_aggregates,
    normalize_human_design_channel,
)


def _sort_matches(counts, total):
    return [(label, count, total) for label, count in counts.items() if count >= 2]


def test_normalize_human_design_channel_orders_numeric_gate_endpoints():
    assert normalize_human_design_channel("59-6") == "6-59"
    assert normalize_human_design_channel(" 10-20 ") == "10-20"
    assert normalize_human_design_channel("custom") == "custom"
    assert normalize_human_design_channel(" ") == ""


def test_compute_common_human_design_aggregates_extracts_each_chart_once():
    charts = [
        SimpleNamespace(key="a", profile="1/3"),
        SimpleNamespace(key="b", profile="1/3"),
        SimpleNamespace(key="c", profile="2/4"),
    ]
    profiles = {
        "a": ([1, 2], [], ["59-6"], ["Sacral"], "Generator", "Sacral"),
        "b": ([2, 3], [], ["6-59"], ["Sacral", "G"], "Generator", "Sacral"),
        "c": ([2, 4], [], ["1-8"], ["G"], "Projector", "Splenic"),
    }
    extracted = []

    def extract_profile(chart):
        extracted.append(chart.key)
        return profiles[chart.key]

    aggregates = compute_common_human_design_aggregates(
        charts,
        extract_profile=extract_profile,
        chart_profile=lambda chart: chart.profile,
        sort_matches=_sort_matches,
        defined_center_order=("Head", "Ajna", "Throat", "G", "Sacral"),
        authority_order=("Sacral", "Splenic"),
        profile_order=("1/3", "2/4"),
    )

    assert extracted == ["a", "b", "c"]
    assert aggregates.gates == [("Gate 2", 3, 3)]
    assert aggregates.channels == [("6-59", 2, 3)]
    assert aggregates.defined_centers == [("G", 2, 3), ("Sacral", 2, 3)]
    assert aggregates.authorities == [("Sacral", 2, 3)]
    assert aggregates.profiles == [("1/3", 2, 3)]
