import sys
from types import ModuleType, SimpleNamespace

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"

from ephemeraldaddy.gui.features.charts.metrics import calculate_house_prevalence_counts


def test_house_prevalence_excludes_angle_positions_from_raw_placement_counts():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        houses=[degree * 30.0 for degree in range(12)],
        positions={
            # Angle positions should not count as listed body/point placements.
            "AS": 5.0,
            "IC": 95.0,
            "DS": 185.0,
            "MC": 275.0,
            # Non-angle placements should count once in their resolved houses.
            "Saturn": 35.0,
            "Ketu": 55.0,
            "Moon": 155.0,
            "Uranus": 160.0,
            "Pluto": 170.0,
            "Vesta": 175.0,
            "Neptune": 185.0,
            "Rahu": 215.0,
            "Lilith": 225.0,
            "Pallas": 245.0,
            "Juno": 255.0,
            "Sun": 275.0,
            "Mercury": 285.0,
            "Venus": 295.0,
            "Ceres": 298.0,
            "Jupiter": 305.0,
            "Part of Fortune": 325.0,
            "Chiron": 335.0,
            "Mars": 345.0,
        },
    )

    assert calculate_house_prevalence_counts(chart) == {
        1: 0,
        2: 2,
        3: 0,
        4: 0,
        5: 0,
        6: 4,
        7: 1,
        8: 2,
        9: 2,
        10: 4,
        11: 2,
        12: 2,
    }
