from ephemeraldaddy.gui.features.charts.text_summary import (
    DRACONIC_POSITION_HEADER_ALIASES,
    POSITION_HEADER_ALIASES,
    _header_matches,
)


def test_tropical_position_header_accepts_legacy_and_qualified_forms() -> None:
    assert _header_matches("POSITIONS", POSITION_HEADER_ALIASES)
    assert _header_matches("POSITIONS (Tropical)", POSITION_HEADER_ALIASES)


def test_draconic_position_header_accepts_legacy_and_qualified_forms() -> None:
    assert _header_matches("DRACONIC POSITIONS", DRACONIC_POSITION_HEADER_ALIASES)
    assert _header_matches("POSITIONS (Draconic)", DRACONIC_POSITION_HEADER_ALIASES)


def test_tropical_qualifier_survives_standard_splitlines() -> None:
    summary = "HEADER\nPOSITIONS (Tropical)\nBody  Sign"

    assert "POSITIONS (Tropical)" in summary
    assert summary.splitlines()[1] == "POSITIONS (Tropical)"
