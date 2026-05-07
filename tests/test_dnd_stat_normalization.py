import sys
from dataclasses import dataclass
from types import ModuleType


@dataclass
class _StubDnDStatBlock:
    raw_scores: dict
    scores: dict
    modifiers: dict


class _StubClassAxisScorer:
    @staticmethod
    def _normalize_numeric_map(values):
        return values


def _stub_clamp01(value):
    return max(0.0, min(1.0, float(value)))


stub_axes = ModuleType("ephemeraldaddy.analysis.dnd.dnd_class_axes_v2")
stub_axes.AxisFeatureSet = object
stub_axes.ClassAxisScorer = _StubClassAxisScorer
stub_axes.DnDStatBlock = _StubDnDStatBlock
stub_axes._build_axis_score_bar = lambda *_args, **_kwargs: ""
stub_axes._build_right_justified_label = lambda label, _width: label
stub_axes._clamp01 = _stub_clamp01
stub_axes.validate_axis_scores = lambda _axis_scores: None
sys.modules["ephemeraldaddy.analysis.dnd.dnd_class_axes_v2"] = stub_axes

from ephemeraldaddy.analysis.dnd.dnd_stat_calculator import _to_dnd_stat


def test_dnd_stat_normalization_anchors_average_band():
    assert _to_dnd_stat(0.0) == 5
    assert _to_dnd_stat(0.5) == 11
    assert _to_dnd_stat(1.0) == 20


def test_dnd_stat_normalization_keeps_clear_low_and_high_bands():
    assert _to_dnd_stat(0.33) < 10
    assert 10 <= _to_dnd_stat(0.5) <= 12
    assert _to_dnd_stat(0.62) > 12
