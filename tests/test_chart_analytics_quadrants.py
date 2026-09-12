from ephemeraldaddy.gui.features.charts.quadrants import (
    aggregate_house_values_by_quadrant,
    quadrant_for_house,
    quadrant_percentages,
)


def test_quadrant_for_house_boundaries():
    assert quadrant_for_house(1) == "I"
    assert quadrant_for_house(3) == "I"
    assert quadrant_for_house(4) == "II"
    assert quadrant_for_house(6) == "II"
    assert quadrant_for_house(7) == "III"
    assert quadrant_for_house(9) == "III"
    assert quadrant_for_house(10) == "IV"
    assert quadrant_for_house(12) == "IV"


def test_quadrant_for_house_rejects_invalid_values():
    assert quadrant_for_house(None) is None
    assert quadrant_for_house(0) is None
    assert quadrant_for_house(13) is None
    assert quadrant_for_house("nope") is None


def test_aggregate_house_values_by_quadrant():
    values = {1: 1, 2: 2.5, 4: 4, 8: 8, 12: 12, None: 99, 13: 99}
    assert aggregate_house_values_by_quadrant(values) == {
        "I": 3.5,
        "II": 4.0,
        "III": 8.0,
        "IV": 12.0,
    }


def test_quadrant_percentages_are_zero_safe_and_normalized():
    assert quadrant_percentages({}) == {"I": 0.0, "II": 0.0, "III": 0.0, "IV": 0.0}
    assert quadrant_percentages({"I": 1, "II": 1, "III": 1, "IV": 1}) == {
        "I": 25.0,
        "II": 25.0,
        "III": 25.0,
        "IV": 25.0,
    }
