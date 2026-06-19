from __future__ import annotations

from datetime import datetime, timezone
import sys
from types import ModuleType

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_DIVIDER = "---------"
style_stub.blend_hex_colors = lambda color_a, _color_b, _ratio: color_a

from ephemeraldaddy.analysis.human_design import build_human_design_synastry_data_output
from ephemeraldaddy.core.human_design_system import (
    HDActivation,
    HumanDesignResult,
    defined_centers_from_active_gates,
)


def _activation(body: str, gate: int) -> HDActivation:
    return HDActivation(
        body=body,
        side="personality",
        longitude=0.0,
        gate=gate,
        line=1,
        color=1,
        tone=1,
        base=1,
        style="black",
    )


def _hd_result(gates: set[int]) -> HumanDesignResult:
    activations = tuple(_activation(f"Body {index}", gate) for index, gate in enumerate(sorted(gates), start=1))
    return HumanDesignResult(
        birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        design_utc=datetime(1999, 12, 15, tzinfo=timezone.utc),
        personality_activations=activations,
        design_activations=(),
        active_gates=frozenset(gates),
        defined_channels=(),
        defined_centers=frozenset(),
        hd_type="Reflector",
        authority="Lunar",
        profile="1/3",
        strategy="Wait a lunar cycle",
        split_definition="None",
        incarnation_cross="Unknown",
    )


def test_defined_centers_from_active_gates_uses_harmonic_channels() -> None:
    assert defined_centers_from_active_gates({64, 47}) == frozenset({"Head", "Ajna"})


def test_synastry_defined_centers_include_cross_chart_harmonic_gates() -> None:
    hd_a = _hd_result({64})
    hd_b = _hd_result({47})

    output, _position_info_map, _header_lines = build_human_design_synastry_data_output(
        hd_a,
        hd_b,
        chart_a_name="Chart A",
        chart_b_name="Chart B",
    )

    assert "Combined Defined Centers: Head, Ajna" in output
    assert "47-64" in output
