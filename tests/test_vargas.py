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
    [
        (0, 0),   # Aries -> Aries
        (1, 9),   # Taurus -> Capricorn
        (2, 6),   # Gemini -> Libra
        (3, 3),   # Cancer -> Cancer
        (4, 0),   # Leo -> Aries
        (5, 9),   # Virgo -> Capricorn
        (6, 6),   # Libra -> Libra
        (7, 3),   # Scorpio -> Cancer
        (8, 0),   # Sagittarius -> Aries
        (9, 9),   # Capricorn -> Capricorn
        (10, 6),  # Aquarius -> Libra
        (11, 3),  # Pisces -> Cancer
    ],
)
def test_navamsha_uses_parashara_modality_starts_for_all_source_signs(
    source_sign, expected_start_sign
):
    assert int(project_longitude(source_sign * 30.0) // 30) == expected_start_sign


@pytest.mark.parametrize("segment", range(1, 9))
def test_navamsha_segment_boundaries_are_deterministic(segment):
    boundary = segment * (30.0 / 9.0)
    projected_boundary = segment * 30.0
    assert project_longitude(boundary - 1e-9) == pytest.approx(
        projected_boundary - 9e-9, abs=1e-7
    )
    assert project_longitude(boundary) == pytest.approx(projected_boundary)


def test_navamsha_wraps_at_360():
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
    assert not projected.uses_houses


def test_d9_projects_lagna_but_not_unvalidated_angles_or_part_of_fortune():
    source = SiderealChartData(
        chart_uid="PARENT01",
        ayanamsha="lahiri",
        ayanamsha_degrees=24.0,
        positions=MappingProxyType(
            {
                "Sun": 10.0,
                "AS": 20.0,
                "MC": 30.0,
                "DS": 200.0,
                "IC": 210.0,
                "Part of Fortune": 40.0,
            }
        ),
        retrogrades=MappingProxyType({"Sun": False}),
        ascendant=20.0,
        mc=30.0,
        house_cusps=tuple(float(index * 30) for index in range(12)),
        aspects=(),
        nakshatras=MappingProxyType({}),
        source_recalculation_token="token",
    )

    projected = project_varga(source)

    assert set(projected.positions) == {"Sun", "AS"}
    assert "MC" not in projected.positions
    assert "DS" not in projected.positions
    assert "IC" not in projected.positions
    assert "Part of Fortune" not in projected.positions
