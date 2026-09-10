import datetime

import pytest

from ephemeraldaddy.core import ephemeris
from ephemeraldaddy.core.body_identity import (
    CANONICAL_LILITH_BODIES,
    MEAN_LILITH,
    NATURAL_LILITH,
    OSCULATING_LILITH,
)
from ephemeraldaddy.core.interpretations import (
    BODY_SIGN_DURATION_DAYS,
    DOMINANT_BODY_MEANINGS,
    NATAL_WEIGHT,
    PLANET_COLORS,
    PLANET_GLYPHS,
    PLANET_KEYWORDS,
    PLANET_ORDER,
)


FIXED_UTC = datetime.datetime(2026, 9, 10, 13, 26, tzinfo=datetime.timezone.utc)


def test_canonical_liliths_resolve_to_distinct_fixed_swiss_ids() -> None:
    assert ephemeris.lilith_swiss_id(MEAN_LILITH) == 12
    assert ephemeris.lilith_swiss_id(OSCULATING_LILITH) == 13
    assert ephemeris.lilith_swiss_id(NATURAL_LILITH) == 21


@pytest.mark.parametrize("body", sorted(CANONICAL_LILITH_BODIES))
def test_direct_longitude_matches_swiss_ephemeris(body: str) -> None:
    dt = FIXED_UTC
    hour = dt.hour + dt.minute / 60 + dt.second / 3600
    jd = ephemeris.swe.julday(dt.year, dt.month, dt.day, hour)
    expected, _ = ephemeris.swe.calc_ut(jd, ephemeris.lilith_swiss_id(body))
    assert ephemeris.planetary_longitude(dt, body) == pytest.approx(expected[0] % 360)


def test_positions_and_retrogrades_emit_only_canonical_lilith_keys(monkeypatch) -> None:
    monkeypatch.setattr(ephemeris, "_get_skyfield_context", lambda: _fake_skyfield_context())
    positions = ephemeris.planetary_positions(FIXED_UTC, 0.0, 0.0)
    retrogrades = ephemeris.planetary_retrogrades(FIXED_UTC)
    for payload in (positions, retrogrades):
        assert CANONICAL_LILITH_BODIES <= payload.keys()
        assert not ({"Lilith", "True Lilith", "Black Moon Lilith"} & payload.keys())


def _fake_skyfield_context():
    class TimeScale:
        def from_datetime(self, value):
            return value

    class Earth:
        def at(self, value):
            raise RuntimeError("force Swiss-only path")

    return TimeScale(), Earth(), {}


def test_missing_lilith_id_never_falls_back_to_another_method(monkeypatch) -> None:
    candidates = ephemeris.LILITH_SWISS_ID_CANDIDATES[NATURAL_LILITH]
    for candidate in candidates:
        monkeypatch.delattr(ephemeris.swe, candidate, raising=False)
    assert ephemeris.lilith_swiss_id(NATURAL_LILITH) is None
    assert ephemeris.planetary_longitude(FIXED_UTC, NATURAL_LILITH) is None


def test_all_lilith_registries_are_explicit_and_rich_entries_are_independent() -> None:
    for body in CANONICAL_LILITH_BODIES:
        assert body in PLANET_ORDER
        assert body in NATAL_WEIGHT
        assert body in BODY_SIGN_DURATION_DAYS
        assert body in PLANET_COLORS
        assert body in PLANET_GLYPHS
        assert body in PLANET_KEYWORDS
        assert body in DOMINANT_BODY_MEANINGS
    assert PLANET_KEYWORDS[MEAN_LILITH] is not PLANET_KEYWORDS[OSCULATING_LILITH]
    assert PLANET_KEYWORDS[NATURAL_LILITH] is not PLANET_KEYWORDS[OSCULATING_LILITH]
    assert DOMINANT_BODY_MEANINGS[MEAN_LILITH] is not DOMINANT_BODY_MEANINGS[OSCULATING_LILITH]
