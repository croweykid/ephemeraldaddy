import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from zoneinfo import ZoneInfo

from ephemeraldaddy.core import human_design_system as hds


def _install_gui_style_stub():
    style_stub = sys.modules.get("ephemeraldaddy.gui.style")
    if style_stub is None:
        style_stub = ModuleType("ephemeraldaddy.gui.style")
        sys.modules["ephemeraldaddy.gui.style"] = style_stub
    style_stub.CHART_DATA_DIVIDER = "---------"
    style_stub.blend_hex_colors = lambda color_a, _color_b, _ratio: color_a


def _minimal_human_design_result(birth_utc):
    activation = hds.HDActivation(
        body="Sun",
        side="personality",
        longitude=0.0,
        gate=1,
        line=1,
        color=1,
        tone=1,
        base=1,
        style="black",
    )
    earth_activation = hds.HDActivation(
        body="Earth",
        side="personality",
        longitude=0.0,
        gate=2,
        line=1,
        color=1,
        tone=1,
        base=1,
        style="black",
    )
    design_activation = hds.HDActivation(
        body="Sun",
        side="design",
        longitude=0.0,
        gate=3,
        line=1,
        color=1,
        tone=1,
        base=1,
        style="red",
    )
    design_earth_activation = hds.HDActivation(
        body="Earth",
        side="design",
        longitude=0.0,
        gate=4,
        line=1,
        color=1,
        tone=1,
        base=1,
        style="red",
    )
    return hds.HumanDesignResult(
        birth_utc=birth_utc,
        design_utc=birth_utc,
        personality_activations=(activation, earth_activation),
        design_activations=(design_activation, design_earth_activation),
        active_gates=frozenset({1, 2, 3, 4}),
        defined_channels=(),
        defined_centers=frozenset(),
        hd_type="Reflector",
        authority="Lunar",
        profile="1/1",
        strategy="Wait",
        split_definition="None",
        incarnation_cross="Test Cross",
    )


def test_calculate_human_design_uses_rectified_time_when_enabled(monkeypatch):
    captured_birth_utcs = []

    def fake_body_longitudes(moment):
        captured_birth_utcs.append(moment)
        return {body: 0.0 for body in hds.HD_BODIES}

    monkeypatch.setattr(hds, "_body_longitudes", fake_body_longitudes)
    monkeypatch.setattr(hds, "_solve_design_utc", lambda birth_utc, _sun_longitude: birth_utc)
    monkeypatch.setattr(hds, "_mandala_components", lambda _longitude: (1, 1, 1, 1, 1))
    monkeypatch.setattr(hds, "_resolve_type", lambda _centers, _channels: "Reflector")
    monkeypatch.setattr(hds, "_resolve_authority", lambda _hd_type, _centers, _channels: "Lunar")
    monkeypatch.setattr(hds, "_resolve_strategy", lambda _hd_type: "Wait")
    monkeypatch.setattr(hds, "_split_definition", lambda _channels: "None")
    monkeypatch.setattr(hds, "_resolve_incarnation_cross", lambda _p_sun, _p_earth, _d_sun, _d_earth: "Test Cross")

    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        retcon_time_used=True,
        retcon_hour=23,
        retcon_minute=59,
    )

    result = hds.calculate_human_design(chart)

    assert result.birth_utc == datetime(2000, 1, 1, 23, 59, tzinfo=timezone.utc)
    assert captured_birth_utcs[0] == datetime(2000, 1, 1, 23, 59, tzinfo=timezone.utc)


def test_calculate_human_design_relocalizes_rectified_time_for_dst_boundary(monkeypatch):
    captured_birth_utcs = []

    def fake_body_longitudes(moment):
        captured_birth_utcs.append(moment)
        return {body: 0.0 for body in hds.HD_BODIES}

    monkeypatch.setattr(
        hds,
        "timezone_from_latlon",
        lambda _lat, _lon: (ZoneInfo("America/New_York"), True),
    )
    monkeypatch.setattr(hds, "_body_longitudes", fake_body_longitudes)
    monkeypatch.setattr(hds, "_solve_design_utc", lambda birth_utc, _sun_longitude: birth_utc)
    monkeypatch.setattr(hds, "_mandala_components", lambda _longitude: (1, 1, 1, 1, 1))
    monkeypatch.setattr(hds, "_resolve_type", lambda _centers, _channels: "Reflector")
    monkeypatch.setattr(hds, "_resolve_authority", lambda _hd_type, _centers, _channels: "Lunar")
    monkeypatch.setattr(hds, "_resolve_strategy", lambda _hd_type: "Wait")
    monkeypatch.setattr(hds, "_split_definition", lambda _channels: "None")
    monkeypatch.setattr(hds, "_resolve_incarnation_cross", lambda _p_sun, _p_earth, _d_sun, _d_earth: "Test Cross")

    chart = SimpleNamespace(
        dt=datetime.fromisoformat("2024-03-10T12:00:00-04:00"),
        lat=40.7128,
        lon=-74.0060,
        retcon_time_used=True,
        retcon_hour=1,
        retcon_minute=30,
    )

    result = hds.calculate_human_design(chart)

    assert result.birth_utc == datetime(2024, 3, 10, 6, 30, tzinfo=timezone.utc)
    assert captured_birth_utcs[0] == datetime(2024, 3, 10, 6, 30, tzinfo=timezone.utc)


def test_calculate_human_design_uses_chart_datetime_when_rectified_time_disabled(monkeypatch):
    captured_birth_utcs = []

    def fake_body_longitudes(moment):
        captured_birth_utcs.append(moment)
        return {body: 0.0 for body in hds.HD_BODIES}

    monkeypatch.setattr(hds, "_body_longitudes", fake_body_longitudes)
    monkeypatch.setattr(hds, "_solve_design_utc", lambda birth_utc, _sun_longitude: birth_utc)
    monkeypatch.setattr(hds, "_mandala_components", lambda _longitude: (1, 1, 1, 1, 1))
    monkeypatch.setattr(hds, "_resolve_type", lambda _centers, _channels: "Reflector")
    monkeypatch.setattr(hds, "_resolve_authority", lambda _hd_type, _centers, _channels: "Lunar")
    monkeypatch.setattr(hds, "_resolve_strategy", lambda _hd_type: "Wait")
    monkeypatch.setattr(hds, "_split_definition", lambda _channels: "None")
    monkeypatch.setattr(hds, "_resolve_incarnation_cross", lambda _p_sun, _p_earth, _d_sun, _d_earth: "Test Cross")

    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        retcon_time_used=False,
        retcon_hour=23,
        retcon_minute=59,
    )

    result = hds.calculate_human_design(chart)

    assert result.birth_utc == datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert captured_birth_utcs[0] == datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_human_design_output_keeps_unknown_time_variants_when_houses_are_not_used(monkeypatch):
    _install_gui_style_stub()
    from ephemeraldaddy.analysis import human_design as hd_output

    hd_result = _minimal_human_design_result(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
    variant_results = (
        _minimal_human_design_result(datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc)),
        _minimal_human_design_result(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)),
        _minimal_human_design_result(datetime(2000, 1, 1, 23, 59, tzinfo=timezone.utc)),
    )
    captured_variant_results = []

    monkeypatch.setattr(hd_output, "calculate_human_design", lambda _chart: hd_result)
    monkeypatch.setattr(hd_output, "chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(hd_output, "_time_variant_human_design_results", lambda _chart: variant_results)

    def fake_build_positions_lines(_hd_result, *, time_variant_results=None):
        captured_variant_results.append(time_variant_results)
        return ["POSITIONS"], {}

    monkeypatch.setattr(hd_output, "_build_hd_positions_lines", fake_build_positions_lines)

    hd_output.build_human_design_chart_data_output(SimpleNamespace(), aspect_sort="orb")

    assert captured_variant_results == [variant_results]


def test_human_design_output_suppresses_unknown_time_variants_when_houses_are_used(monkeypatch):
    _install_gui_style_stub()
    from ephemeraldaddy.analysis import human_design as hd_output

    hd_result = _minimal_human_design_result(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
    captured_variant_results = []

    monkeypatch.setattr(hd_output, "calculate_human_design", lambda _chart: hd_result)
    monkeypatch.setattr(hd_output, "chart_uses_houses", lambda _chart: True)
    monkeypatch.setattr(
        hd_output,
        "_time_variant_human_design_results",
        lambda _chart: (_ for _ in ()).throw(AssertionError("variants should not be computed")),
    )

    def fake_build_positions_lines(_hd_result, *, time_variant_results=None):
        captured_variant_results.append(time_variant_results)
        return ["POSITIONS"], {}

    monkeypatch.setattr(hd_output, "_build_hd_positions_lines", fake_build_positions_lines)

    hd_output.build_human_design_chart_data_output(SimpleNamespace(), aspect_sort="orb")

    assert captured_variant_results == [None]
