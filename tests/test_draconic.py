from ephemeraldaddy.core.draconic import calculate_draconic_positions, draconic_longitude


def test_draconic_longitude_places_north_node_at_zero_aries() -> None:
    assert draconic_longitude(123.5, 123.5) == 0.0


def test_draconic_longitude_wraps_across_zero_aries() -> None:
    assert draconic_longitude(5.0, 20.0) == 345.0
    assert draconic_longitude(10.0, 350.0) == 20.0


def test_calculate_draconic_positions_rotates_every_known_position() -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 200.0,
        "Rahu": 350.0,
        "Ketu": 170.0,
        "AS": 40.0,
        "Unknown": None,
    }

    result = calculate_draconic_positions(positions)

    assert result == {
        "Sun": 20.0,
        "Moon": 210.0,
        "Rahu": 0.0,
        "Ketu": 180.0,
        "AS": 50.0,
    }


def test_calculate_draconic_positions_requires_north_node() -> None:
    assert calculate_draconic_positions({"Sun": 10.0}) == {}
