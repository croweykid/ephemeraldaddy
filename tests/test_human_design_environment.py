import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_DIVIDER = "---------"


def _blend_hex_colors(color_a: str, _color_b: str, _ratio: float) -> str:
    return color_a


style_stub.blend_hex_colors = _blend_hex_colors

from ephemeraldaddy.analysis import human_design as hd_output
from ephemeraldaddy.core.human_design_system import HDActivation, HumanDesignResult


def _activation(body: str, side: str, *, color: int, tone: int, gate: int = 1) -> HDActivation:
    return HDActivation(
        body=body,
        side=side,
        longitude=0.0,
        gate=gate,
        line=1,
        color=color,
        tone=tone,
        base=1,
        style="red" if side == "design" else "black",
    )


def _hd_result() -> HumanDesignResult:
    personality_sun = _activation("Sun", "personality", color=2, tone=1, gate=1)
    personality_rahu = _activation("Rahu", "personality", color=5, tone=5, gate=4)
    design_sun = _activation("Sun", "design", color=3, tone=3, gate=2)
    design_rahu = _activation("Rahu", "design", color=6, tone=4, gate=3)
    return HumanDesignResult(
        birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        design_utc=datetime(1999, 10, 5, tzinfo=timezone.utc),
        personality_activations=(personality_sun, personality_rahu),
        design_activations=(design_sun, design_rahu),
        active_gates=frozenset({1, 2, 3, 4}),
        defined_channels=(),
        defined_centers=frozenset(),
        hd_type="Reflector",
        authority="Lunar",
        profile="1/1",
        strategy="Wait a lunar cycle",
        split_definition="None",
        incarnation_cross="Test Cross",
    )


def test_chart_data_environment_uses_correct_variable_sources(monkeypatch) -> None:
    monkeypatch.setattr(hd_output, "calculate_human_design", lambda _chart: _hd_result())

    output, *_ = hd_output.build_human_design_chart_data_output(
        SimpleNamespace(),
        aspect_sort="orb",
    )

    assert "Environment: Shores (Blending)" in output
    assert "Perspective: Probability" in output
    assert "Motivation: Hope" in output
    assert "Digestion: Hot Thirst" in output
    assert "Environment: Mountains" not in output


def test_design_marker_activation_is_design_rahu() -> None:
    activation = hd_output._design_rahu_activation(_hd_result())

    assert activation is not None
    assert activation.body == "Rahu"
    assert activation.color == 6
    assert activation.tone == 4
