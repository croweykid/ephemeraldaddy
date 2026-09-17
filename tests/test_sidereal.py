import datetime as dt

import pytest

from ephemeraldaddy.analysis import nakshatra_metrics
from ephemeraldaddy.core import sidereal


UTC = dt.timezone.utc


# Swiss Ephemeris 2.10 native Lahiri reference values for
# 2000-01-01 12:00:00 UTC. These are intentionally hard-coded rather than
# recomputed through EphemeralDaddy's projection path so future changes cannot
# make the implementation and its expected values drift together.
_SWISS_J2000_TROPICAL = {
    "Sun": 280.36891967534336,
    "Moon": 223.32377543840954,
    "Mercury": 271.8892750074874,
    "Venus": 241.5657983261687,
    "Mars": 327.9633133185202,
    "Jupiter": 25.253030309421764,
    "Saturn": 40.39563895600193,
}
_SWISS_J2000_LAHIRI = {
    "Sun": 256.51569718931427,
    "Moon": 199.47055295238047,
    "Mercury": 248.0360525214584,
    "Venus": 217.7125758401396,
    "Mars": 304.11009083249115,
    "Jupiter": 1.3998078233926976,
    "Saturn": 16.542416469972864,
}
_SWISS_J2000_LONDON_LAHIRI_CUSPS = (
    0.4340826001690026,
    37.308576926662056,
    58.17678964290366,
    75.7578653142555,
    95.20014903446688,
    123.8341527186856,
    180.434082600169,
    217.30857692666206,
    238.17678964290369,
    255.7578653142555,
    275.2001490344669,
    303.83415271868563,
)
_SWISS_J2000_LONDON_LAHIRI_AS = 0.4340826001690026
_SWISS_J2000_LONDON_LAHIRI_MC = 255.7578653142555


def test_lahiri_ayanamsha_is_date_sensitive_and_matches_swiss_reference():
    j2000 = sidereal.lahiri_ayanamsha(dt.datetime(2000, 1, 1, 12, tzinfo=UTC))
    recent = sidereal.lahiri_ayanamsha(dt.datetime(2025, 1, 1, 12, tzinfo=UTC))

    assert j2000 == pytest.approx(23.853222486, abs=0.000001)
    assert recent > j2000


def test_lahiri_d1_matches_swiss_native_planets_angles_and_cusps(monkeypatch):
    """Guard ED's projection against a fixed Swiss-native Lahiri fixture."""

    moment = dt.datetime(2000, 1, 1, 12, tzinfo=UTC)
    monkeypatch.setattr(
        sidereal,
        "planetary_positions",
        lambda *_: dict(_SWISS_J2000_TROPICAL),
    )
    monkeypatch.setattr(
        sidereal,
        "planetary_retrogrades",
        lambda *_: {name: False for name in _SWISS_J2000_TROPICAL},
    )

    chart = sidereal.calculate_lahiri_d1(
        chart_uid="REFERENCE01",
        dt=moment,
        latitude=51.5,
        longitude=0.0,
        uses_houses=True,
        source_token="reference-token",
    )

    assert chart.ayanamsha_degrees == pytest.approx(23.853222486, abs=1e-9)
    for body, expected in _SWISS_J2000_LAHIRI.items():
        assert chart.positions[body] == pytest.approx(expected, abs=1e-8)
    assert chart.ascendant == pytest.approx(_SWISS_J2000_LONDON_LAHIRI_AS, abs=1e-8)
    assert chart.mc == pytest.approx(_SWISS_J2000_LONDON_LAHIRI_MC, abs=1e-8)
    assert chart.house_cusps == pytest.approx(
        _SWISS_J2000_LONDON_LAHIRI_CUSPS,
        abs=1e-8,
    )


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
        chart_uid="abc12345",
        dt=moment,
        latitude=51.5,
        longitude=0.0,
        uses_houses=True,
        source_token="timed-token",
    )
    untimed = sidereal.calculate_lahiri_d1(
        chart_uid="abc12345",
        dt=moment,
        latitude=51.5,
        longitude=0.0,
        uses_houses=False,
        source_token="untimed-token",
    )

    assert timed.chart_uid == "ABC12345"
    assert timed.positions["Sun"] == pytest.approx(280.0 - timed.ayanamsha_degrees)
    assert timed.positions["AS"] == timed.ascendant == timed.house_cusps[0]
    assert timed.positions["MC"] == timed.mc
    assert timed.uses_houses
    assert untimed.ascendant is None
    assert untimed.mc is None
    assert untimed.house_cusps is None
    assert not untimed.uses_houses
    assert "AS" not in untimed.positions


def test_source_token_extends_canonical_astro_token_with_sidereal_context():
    canonical = ("2020-05-01T00:00:00+00:00", 1.0, 2.0, False)
    token = sidereal.source_recalculation_token(canonical_astro_token=canonical)

    assert token == sidereal.source_recalculation_token(canonical_astro_token=canonical)
    assert token != sidereal.source_recalculation_token(
        canonical_astro_token=("2020-05-01T00:00:00+00:00", 1.0, 2.1, False)
    )
    assert token != sidereal.source_recalculation_token(
        canonical_astro_token=canonical,
        calculation_version=sidereal.SIDEREAL_CALCULATION_VERSION + 1,
    )


@pytest.mark.parametrize(
    ("longitude", "name", "pada"),
    [(0.0, "Ashwini", 1), (3 + 20 / 60, "Ashwini", 2), (359.999, "Revati", 4)],
)
def test_nakshatra_boundaries(longitude, name, pada):
    result = sidereal.nakshatra_position(longitude)
    assert result.name == name
    assert result.pada == pada


def test_nakshatra_exact_second_sector_boundary_is_bharani():
    assert sidereal.nakshatra_position(13 + 20 / 60).name == "Bharani"


def test_tropical_and_lahiri_shifted_longitudes_resolve_to_same_nakshatra():
    moment = dt.datetime(2000, 1, 1, 12, tzinfo=UTC)
    tropical_longitude = 24.0
    shift = sidereal.lahiri_ayanamsha(moment)

    tropical = sidereal.nakshatra_position_for_zodiac(
        tropical_longitude,
        context=sidereal.ZodiacContext("tropical"),
        dt=moment,
    )
    projected = sidereal.nakshatra_position_for_zodiac(
        tropical_longitude - shift,
        context=sidereal.ZodiacContext("sidereal", "lahiri"),
    )

    assert tropical == projected
    assert projected.name == "Ashwini"


def test_sidereal_analytics_use_precomputed_chart_nakshatras():
    class SiderealAnalyticsChart:
        zodiac = "sidereal"
        ayanamsha = "lahiri"
        positions = {"Sun": 0.0}
        nakshatras = {
            "Sun": sidereal.NakshatraPosition(0, "Ashwini", 1, 0.0),
        }

    weights = nakshatra_metrics._fallback_dominant_nakshatra_weights(
        SiderealAnalyticsChart()
    )

    assert weights["Ashwini"] > 0
    assert weights["Uttara Bhadrapada"] == 0


def test_tropical_unknown_time_chart_uses_available_date_for_ayanamsha():
    chart = type(
        "UnknownTimeChart",
        (),
        {
            "dt": dt.datetime(2000, 1, 1, 12, tzinfo=UTC),
            "birthtime_unknown": True,
            "retcon_time_used": False,
            "positions": {"Moon": 24.0},
            "zodiac": "tropical",
        },
    )()

    assert sidereal.nakshatra_position_for_chart(chart, "Moon").name == "Ashwini"


def test_zodiac_context_rejects_collapsed_or_unsupported_configuration():
    assert sidereal.ZodiacContext("sidereal", "Lahiri").ayanamsha == "lahiri"
    with pytest.raises(ValueError):
        sidereal.ZodiacContext("tropical", "lahiri")
