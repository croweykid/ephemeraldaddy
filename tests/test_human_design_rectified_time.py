from datetime import datetime, timezone
from types import SimpleNamespace

from ephemeraldaddy.core import human_design_system as hds


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
