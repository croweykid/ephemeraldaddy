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

    output, position_info_map, *_ = hd_output.build_human_design_chart_data_output(
        SimpleNamespace(),
        aspect_sort="orb",
    )

    assert "Environment: Shores  — Artificial" in output
    assert "Environment: Shores  — Artificial (Tone 4)" not in output
    assert "Perspective: Probability" in output
    assert "Motivation: Hope" in output
    assert "Digestion: Thirst  — Hot" in output
    assert "Digestion: Thirst  — Hot (Tone 3)" not in output
    assert "Environment: Mountains" not in output

    property_values = [
        entry.get("property_value")
        for entries in position_info_map.values()
        for entry in entries
        if entry.get("kind") == "hd_property"
    ]
    assert "Shores  — Artificial (Tone 4)" in property_values
    assert "Thirst  — Hot (Tone 3)" in property_values


def test_design_marker_activation_is_design_rahu() -> None:
    activation = hd_output._design_rahu_activation(_hd_result())

    assert activation is not None
    assert activation.body == "Rahu"
    assert activation.color == 6
    assert activation.tone == 4


def test_activation_display_values_marks_multiple_color_tone_base_changes_unknown() -> None:
    current = _activation("Sun", "personality", color=1, tone=1, gate=24)
    midnight = _activation("Sun", "personality", color=1, tone=1, gate=24)
    noon = _activation("Sun", "personality", color=2, tone=2, gate=17)
    late = _activation("Sun", "personality", color=1, tone=3, gate=14)
    midnight = HDActivation(**{**midnight.__dict__, "line": 5, "base": 1})
    noon = HDActivation(**{**noon.__dict__, "line": 3, "base": 2})
    late = HDActivation(**{**late.__dict__, "line": 2, "base": 3})

    gl_text, color_text, tone_text, base_text = hd_output._activation_display_values(
        current,
        (midnight, noon, late),
    )

    assert gl_text == "24.5->17.3->14.2"
    assert color_text == "?"
    assert tone_text == "?"
    assert base_text == "?"


def test_activation_display_values_shows_single_color_tone_base_change() -> None:
    current = _activation("Moon", "personality", color=5, tone=1, gate=1)
    midnight = _activation("Moon", "personality", color=5, tone=1, gate=1)
    noon = _activation("Moon", "personality", color=5, tone=1, gate=1)
    late = _activation("Moon", "personality", color=6, tone=4, gate=43)
    midnight = HDActivation(**{**midnight.__dict__, "line": 2, "base": 3})
    noon = HDActivation(**{**noon.__dict__, "line": 2, "base": 3})
    late = HDActivation(**{**late.__dict__, "line": 6, "base": 4})

    gl_text, color_text, tone_text, base_text = hd_output._activation_display_values(
        current,
        (midnight, noon, late),
    )

    assert gl_text == "1.2->43.6"
    assert color_text == "5->6"
    assert tone_text == "1->4"
    assert base_text == "3->4"


def test_positions_lines_render_unknown_variant_fields_without_clickable_value_errors() -> None:
    current = HDActivation(**{**_activation("Sun", "personality", color=1, tone=1, gate=24).__dict__, "line": 5, "base": 1})
    midnight = HDActivation(**{**current.__dict__, "color": 1, "tone": 1, "base": 1})
    noon = HDActivation(**{**current.__dict__, "gate": 17, "line": 3, "color": 2, "tone": 2, "base": 2})
    late = HDActivation(**{**current.__dict__, "gate": 14, "line": 2, "color": 1, "tone": 3, "base": 3})
    base_result = HumanDesignResult(
        birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        design_utc=datetime(1999, 10, 5, tzinfo=timezone.utc),
        personality_activations=(current,),
        design_activations=(),
        active_gates=frozenset({24}),
        defined_channels=(),
        defined_centers=frozenset(),
        hd_type="Reflector",
        authority="Lunar",
        profile="5/1",
        strategy="Wait a lunar cycle",
        split_definition="None",
        incarnation_cross="Test Cross",
    )
    midnight_result = HDActivation(**{**midnight.__dict__})
    noon_result = HDActivation(**{**noon.__dict__})
    late_result = HDActivation(**{**late.__dict__})

    lines, info_map = hd_output._build_hd_positions_lines(
        base_result,
        time_variant_results=(
            HumanDesignResult(**{**base_result.__dict__, "personality_activations": (midnight_result,)}),
            HumanDesignResult(**{**base_result.__dict__, "personality_activations": (noon_result,)}),
            HumanDesignResult(**{**base_result.__dict__, "personality_activations": (late_result,)}),
        ),
    )

    assert any("24.5->17.3->14.2" in line and "?" in line for line in lines)
    assert any(entry.get("kind") == "hd_gate_line" for entries in info_map.values() for entry in entries)
