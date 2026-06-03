from datetime import datetime, timezone
from types import SimpleNamespace

from ephemeraldaddy.analysis import human_design as hd_output
from ephemeraldaddy.core.human_design_system import HDActivation, HumanDesignResult
from ephemeraldaddy.gui.features.charts import human_design_analytics_panel as hd_analytics


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
    personality_sun = _activation("Sun", "personality", color=1, tone=1, gate=1)
    design_sun = _activation("Sun", "design", color=4, tone=1, gate=2)
    design_rahu = _activation("Rahu", "design", color=6, tone=4, gate=3)
    return HumanDesignResult(
        birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        design_utc=datetime(1999, 10, 5, tzinfo=timezone.utc),
        personality_activations=(personality_sun,),
        design_activations=(design_sun, design_rahu),
        active_gates=frozenset({1, 2, 3}),
        defined_channels=(),
        defined_centers=frozenset(),
        hd_type="Reflector",
        authority="Lunar",
        profile="1/1",
        strategy="Wait a lunar cycle",
        split_definition="None",
        incarnation_cross="Test Cross",
    )


def test_chart_data_environment_uses_design_rahu_color_and_tone(monkeypatch) -> None:
    monkeypatch.setattr(hd_output, "calculate_human_design", lambda _chart: _hd_result())

    output, *_ = hd_output.build_human_design_chart_data_output(
        SimpleNamespace(),
        aspect_sort="orb",
    )

    assert "Environment: Shores (Blending)" in output
    assert "Environment: Mountains" not in output


def test_analytics_design_marker_activation_is_design_rahu() -> None:
    activation = hd_analytics._design_rahu_activation(_hd_result())

    assert activation is not None
    assert activation.body == "Rahu"
    assert activation.color == 6
    assert activation.tone == 4
