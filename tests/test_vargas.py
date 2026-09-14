from types import MappingProxyType

import pytest

from ephemeraldaddy.core.sidereal import SiderealChartData
from ephemeraldaddy.core.vargas import VARGA_RULES, project_longitude, project_varga


def test_only_explicitly_validated_varga_rules_are_exposed():
    assert set(VARGA_RULES) == {"D9"}
    assert VARGA_RULES["D9"].name == "Navamsha"
    with pytest.raises(ValueError):
        project_longitude(10.0, "D10")


@pytest.mark.parametrize(
    ("source_sign", "expected_start_sign"),
    [(0, 0), (1, 9), (2, 6), (3, 3), (4, 0), (5, 9)],
)
def test_navamsha_uses_parashara_modality_starts(source_sign, expected_start_sign):
    assert int(project_longitude(source_sign * 30.0) // 30) == expected_start_sign


def test_navamsha_segment_boundary_is_deterministic():
    boundary = 30.0 / 9.0
    assert project_longitude(boundary - 1e-9) == pytest.approx(30.0 - 9e-9, abs=1e-7)
    assert project_longitude(boundary) == pytest.approx(30.0)
    assert project_longitude(360.0) == pytest.approx(0.0)


def test_varga_retains_parent_uid_and_retrograde_state_without_persistence():
    source = SiderealChartData(
        chart_uid="PARENT01",
        ayanamsha="lahiri",
        ayanamsha_degrees=24.0,
        positions=MappingProxyType({"Mercury": 10.0}),
        retrogrades=MappingProxyType({"Mercury": True}),
        ascendant=None,
        mc=None,
        house_cusps=None,
        aspects=(),
        nakshatras=MappingProxyType({}),
        source_recalculation_token="token",
    )

    projected = project_varga(source)

    assert projected.chart_uid == source.chart_uid
    assert projected.retrogrades == source.retrogrades
    assert projected.house_cusps is None
