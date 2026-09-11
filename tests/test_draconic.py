from ephemeraldaddy.core.draconic import (
    calculate_draconic_positions,
    draconic_longitude,
    find_draconic_natal_aspects,
)


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


def test_find_draconic_natal_aspects_compares_draconic_to_natal_positions() -> None:
    draconic = {
        "Sun": 0.0,
        "Mars": 120.0,
    }
    natal = {
        "Moon": 60.0,
        "Venus": 300.0,
    }

    aspects = find_draconic_natal_aspects(
        draconic,
        natal,
        aspect_defs={"sextile": {"angle": 60.0, "orb": 0.1}},
    )

    assert aspects == [
        {
            "p1": "Sun",
            "p2": "Moon",
            "type": "sextile",
            "angle": 60.0,
            "delta": 0.0,
            "draconic_longitude": 0.0,
            "natal_longitude": 60.0,
        },
        {
            "p1": "Sun",
            "p2": "Venus",
            "type": "sextile",
            "angle": 60.0,
            "delta": 0.0,
            "draconic_longitude": 0.0,
            "natal_longitude": 300.0,
        },
        {
            "p1": "Mars",
            "p2": "Moon",
            "type": "sextile",
            "angle": 60.0,
            "delta": 0.0,
            "draconic_longitude": 120.0,
            "natal_longitude": 60.0,
        },
    ]


def test_find_draconic_natal_aspects_allows_same_body_cross_aspect() -> None:
    aspects = find_draconic_natal_aspects(
        {"Sun": 10.0},
        {"Sun": 70.0},
        aspect_defs={"sextile": {"angle": 60.0, "orb": 0.1}},
    )

    assert len(aspects) == 1
    assert aspects[0]["p1"] == "Sun"
    assert aspects[0]["p2"] == "Sun"
    assert aspects[0]["type"] == "sextile"
