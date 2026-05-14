import sys
from types import ModuleType, SimpleNamespace

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"

from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_element_prevalence_counts,
    calculate_sign_prevalence_counts,
    element_prevalence_counts_from_sign_counts,
)

SIGN_STARTS = {
    "Aries": 0.0,
    "Taurus": 30.0,
    "Gemini": 60.0,
    "Cancer": 90.0,
    "Leo": 120.0,
    "Virgo": 150.0,
    "Libra": 180.0,
    "Scorpio": 210.0,
    "Sagittarius": 240.0,
    "Capricorn": 270.0,
    "Aquarius": 300.0,
    "Pisces": 330.0,
}


def lon(sign: str, degree: float = 1.0) -> float:
    return SIGN_STARTS[sign] + degree


def test_element_prevalence_matches_chart_view_position_sign_grouping():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        positions={
            "Sun": lon("Capricorn"),
            "Moon": lon("Scorpio"),
            "Mercury": lon("Aquarius"),
            "Venus": lon("Aquarius"),
            "Mars": lon("Taurus"),
            "Jupiter": lon("Aquarius"),
            "Saturn": lon("Gemini"),
            "Uranus": lon("Libra"),
            "Neptune": lon("Sagittarius"),
            "Pluto": lon("Libra"),
            "Rahu": lon("Sagittarius"),
            "Ketu": lon("Gemini"),
            "Chiron": lon("Aries"),
            "Ceres": lon("Capricorn"),
            "Pallas": lon("Capricorn"),
            "Juno": lon("Capricorn"),
            "Vesta": lon("Libra"),
            "Lilith": lon("Capricorn"),
            "Part of Fortune": lon("Pisces"),
            "AS": lon("Taurus"),
            "IC": lon("Cancer"),
            "DS": lon("Scorpio"),
            "MC": lon("Capricorn"),
        },
    )

    sign_counts = calculate_sign_prevalence_counts(chart)

    assert calculate_element_prevalence_counts(chart) == {
        "Fire": 3,
        "Earth": 8,
        "Air": 8,
        "Water": 4,
    }
    assert element_prevalence_counts_from_sign_counts(sign_counts) == {
        "Fire": 3.0,
        "Earth": 8.0,
        "Air": 8.0,
        "Water": 4.0,
    }
