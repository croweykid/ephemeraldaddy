from ephemeraldaddy.gui.features.charts.aspect_sorting import sort_natal_aspects
from ephemeraldaddy.gui.style import CHART_DATA_SECTION_HEADERS


def _directed_aspect() -> dict:
    return {
        "p1": "Mars",
        "p2": "Sun",
        "type": "trine",
        "angle": 120.0,
        "delta": 0.0,
    }


def test_position_sort_can_preserve_directed_endpoints() -> None:
    result = sort_natal_aspects(
        [_directed_aspect()],
        "Position",
        preserve_endpoint_order=True,
    )
    assert result[0]["p1"] == "Mars"
    assert result[0]["p2"] == "Sun"


def test_default_position_sort_still_normalizes_symmetric_natal_endpoints() -> None:
    result = sort_natal_aspects([_directed_aspect()], "Position")
    assert result[0]["p1"] == "Sun"
    assert result[0]["p2"] == "Mars"


def test_draconic_and_tropical_headers_are_registered_for_chart_data_styling() -> None:
    assert "POSITIONS" in CHART_DATA_SECTION_HEADERS
    assert "POSITIONS (Tropical)" in CHART_DATA_SECTION_HEADERS
    assert "POSITIONS (Draconic)" in CHART_DATA_SECTION_HEADERS
    assert "ASPECTS (Draconic)" in CHART_DATA_SECTION_HEADERS
