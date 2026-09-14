import datetime as dt

import pytest

from ephemeraldaddy.core import sidereal


UTC = dt.timezone.utc


def test_lahiri_ayanamsha_is_date_sensitive_and_matches_swiss_reference():
    j2000 = sidereal.lahiri_ayanamsha(dt.datetime(2000, 1, 1, 12, tzinfo=UTC))
    recent = sidereal.lahiri_ayanamsha(dt.datetime(2025, 1, 1, 12, tzinfo=UTC))

    assert j2000 == pytest.approx(23.853222486, abs=0.000001)
    assert recent > j2000


def test_sidereal_state_does_not_change_subsequent_tropical_swiss_results():
    moment = dt.datetime(2000, 1, 1, 12, tzinfo=UTC)
    julian_day = sidereal.swe.julday(2000, 1, 1, 12.0)
    before = sidereal.swe.calc_ut(julian_day, sidereal.swe.SUN)[0][0]

    sidereal.lahiri_ayanamsha(moment)

    after = sidereal.swe.calc_ut(julian_day, sidereal.swe.SUN)[0][0]
    assert after == before


def test_calculate_lahiri_d1_uses_matching_sidereal_angles_and_untimed_policy(monkeypatch):
    moment = dt.datetime(2000, 1, 1, 12, tzinfo=UTC)
    monkeypatch.setattr(sidereal, "planetary_positions", lambda *_: {"Sun": 280.0})
    monkeypatch.setattr(sidereal, "planetary_retrogrades", lambda *_: {"Sun": False})

    timed = sidereal.calculate_lahiri_d1(
        chart_uid="abc12345", dt=moment, latitude=51.5, longitude=0.0, use_birth_time_data=True
    )
    untimed = sidereal.calculate_lahiri_d1(
        chart_uid="abc12345", dt=moment, latitude=51.5, longitude=0.0, use_birth_time_data=False
    )

    assert timed.chart_uid == "ABC12345"
    assert timed.positions["Sun"] == pytest.approx(280.0 - timed.ayanamsha_degrees)
    assert timed.positions["AS"] == timed.ascendant == timed.house_cusps[0]
    assert timed.positions["MC"] == timed.mc
    assert untimed.ascendant is None
    assert untimed.mc is None
    assert untimed.house_cusps is None
    assert "AS" not in untimed.positions


def test_source_token_ignores_person_data_but_tracks_astrology_inputs():
    moment = dt.datetime(2020, 5, 1, tzinfo=UTC)
    base = dict(dt=moment, latitude=1.0, longitude=2.0, use_birth_time_data=True)
    token = sidereal.source_recalculation_token(**base)

    assert token == sidereal.source_recalculation_token(**base)
    assert token != sidereal.source_recalculation_token(**{**base, "longitude": 2.1})
    # Notes/tags/photos are intentionally absent from the token contract.


@pytest.mark.parametrize(
    ("longitude", "name", "pada"),
    [(0.0, "Ashwini", 1), (3 + 20 / 60, "Ashwini", 2), (359.999, "Revati", 4)],
)
def test_nakshatra_boundaries(longitude, name, pada):
    result = sidereal.nakshatra_position(longitude)
    assert result.name == name
    assert result.pada == pada


def test_zodiac_context_rejects_collapsed_or_unsupported_configuration():
    assert sidereal.ZodiacContext("sidereal", "Lahiri").ayanamsha == "lahiri"
    with pytest.raises(ValueError):
        sidereal.ZodiacContext("tropical", "lahiri")
