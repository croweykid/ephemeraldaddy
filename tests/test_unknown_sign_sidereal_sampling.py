import datetime as dt
from types import SimpleNamespace

import ephemeraldaddy.core.sidereal as sidereal
from ephemeraldaddy.core.chart import compute_unknown_sign_positions


UTC = dt.timezone.utc


def _unknown_chart():
    return SimpleNamespace(
        birthtime_unknown=True,
        dt=dt.datetime(2000, 1, 1, 12, 0, tzinfo=UTC),
        lat=51.5074,
        lon=-0.1278,
    )


def test_unknown_sign_sampler_uses_lahiri_in_sidereal_mode(monkeypatch):
    contexts = []

    def fake_positions(_dt, _lat, _lon, context):
        contexts.append(context)
        if len(contexts) == 1:
            return {"Moon": 29.9, "Sun": 10.0}
        return {"Moon": 30.1, "Sun": 10.1}

    monkeypatch.setattr(sidereal, "planetary_positions_for_zodiac", fake_positions)

    assert compute_unknown_sign_positions(_unknown_chart(), zodiac="sidereal") == ["Moon"]
    assert len(contexts) == 2
    assert all(context.zodiac == "sidereal" for context in contexts)
    assert all(context.ayanamsha == sidereal.LAHIRI for context in contexts)


def test_unknown_sign_sampler_defaults_to_tropical(monkeypatch):
    contexts = []

    def fake_positions(_dt, _lat, _lon, context):
        contexts.append(context)
        return {"Moon": 10.0}

    monkeypatch.setattr(sidereal, "planetary_positions_for_zodiac", fake_positions)

    assert compute_unknown_sign_positions(_unknown_chart()) == []
    assert len(contexts) == 2
    assert all(context.zodiac == "tropical" for context in contexts)
    assert all(context.ayanamsha is None for context in contexts)
