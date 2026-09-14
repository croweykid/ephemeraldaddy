import datetime as dt
from types import MappingProxyType, SimpleNamespace

import pytest

from ephemeraldaddy.analysis.sidereal_astro_twin import (
    SiderealAstroTwinCandidate,
    SiderealAstroTwinMode,
    rank_sidereal_astro_twins,
)
from ephemeraldaddy.core.sidereal import SiderealChartData
from ephemeraldaddy.core.sidereal_service import SiderealCalculationRequest
from ephemeraldaddy.core.vargas import VargaChartView


def _request(uid):
    return SiderealCalculationRequest(
        uid, dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc), 0.0, 0.0, False
    )


def _d1(uid, longitude):
    return SiderealChartData(
        chart_uid=uid,
        ayanamsha="lahiri",
        ayanamsha_degrees=24.0,
        positions=MappingProxyType({"Sun": longitude}),
        retrogrades=MappingProxyType({}),
        ascendant=None,
        mc=None,
        house_cusps=None,
        aspects=(),
        nakshatras=MappingProxyType({}),
        source_recalculation_token="token",
    )


def _d9(uid, longitude):
    return VargaChartView(
        chart_uid=uid,
        zodiac="sidereal",
        ayanamsha="lahiri",
        division="D9",
        positions=MappingProxyType({"Sun": longitude}),
        retrogrades=MappingProxyType({}),
        house_cusps=None,
        aspects=(),
        source_recalculation_token="token",
    )


class Service:
    def get_or_calculate(self, request):
        return _d1(request.chart_uid, {"SUBJECT01": 1, "CAND0001": 2, "CAND0002": 3}[request.chart_uid])

    def get_varga(self, request, division):
        assert division == "D9"
        return _d9(request.chart_uid, {"SUBJECT01": 101, "CAND0001": 102, "CAND0002": 103}[request.chart_uid])


def _candidate(uid, name):
    return SiderealAstroTwinCandidate(SimpleNamespace(chart_uid=uid, name=name), _request(uid))


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (SiderealAstroTwinMode.D1_TO_D1, ("D1", "D1", 1, 2)),
        (SiderealAstroTwinMode.D9_TO_D9, ("D9", "D9", 101, 102)),
        (SiderealAstroTwinMode.D9_TO_D1, ("D9", "D1", 101, 2)),
    ],
)
def test_coordinate_consistent_modes_reuse_one_uid_corpus(mode, expected):
    observed = []

    def scorer(subject, candidate):
        observed.append((subject.division, candidate.division, subject.positions["Sun"], candidate.positions["Sun"]))
        return (1.0 if candidate.chart_uid == "CAND0001" else 0.5,)

    matches = rank_sidereal_astro_twins(
        _candidate("SUBJECT01", "Subject"),
        [_candidate("SUBJECT01", "Subject"), _candidate("CAND0002", "Two"), _candidate("CAND0001", "One")],
        service=Service(),
        mode=mode,
        scorer=scorer,
    )

    assert observed[-1] == expected
    assert [match.chart_uid for match in matches] == ["CAND0001", "CAND0002"]
    assert all(match.ayanamsha == "lahiri" for match in matches)


def test_d9_comparisons_never_inherit_parent_houses():
    parent = SimpleNamespace(
        chart_uid="SUBJECT01", name="Subject", birthtime_unknown=False,
        retcon_time_used=True, use_birth_time_data=True, houses=[10.0],
    )

    def scorer(subject, candidate):
        assert subject.division == "D9"
        assert subject.houses == []
        assert subject.birthtime_unknown
        assert not subject.retcon_time_used
        return (0.5,)

    rank_sidereal_astro_twins(
        SiderealAstroTwinCandidate(parent, _request("SUBJECT01")),
        [_candidate("CAND0001", "One")],
        service=Service(),
        mode=SiderealAstroTwinMode.D9_TO_D1,
        scorer=scorer,
    )


def test_sidereal_comparisons_discard_parent_tropical_derived_caches():
    parent = SimpleNamespace(
        chart_uid="SUBJECT01",
        name="Subject",
        dominant_planet_weights={"Sun": 999},
        dominant_nakshatra_weights={"Tropical": 999},
        _similarity_derived_cache={"stale": object()},
    )

    def scorer(subject, candidate):
        assert subject.dominant_planet_weights == {}
        assert subject.dominant_nakshatra_weights == {}
        assert subject._similarity_derived_cache == {}
        return (0.5,)

    rank_sidereal_astro_twins(
        SiderealAstroTwinCandidate(parent, _request("SUBJECT01")),
        [_candidate("CAND0001", "One")],
        service=Service(),
        scorer=scorer,
    )
