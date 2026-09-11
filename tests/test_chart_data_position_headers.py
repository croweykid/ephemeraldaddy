from ephemeraldaddy.gui.features.charts.text_summary import (
    DRACONIC_POSITION_HEADER_ALIASES,
    POSITION_HEADER_ALIASES,
    _ChartSummaryText,
    _header_matches,
)


def test_tropical_position_header_accepts_legacy_and_qualified_forms() -> None:
    assert _header_matches("POSITIONS", POSITION_HEADER_ALIASES)
    assert _header_matches("POSITIONS (Tropical)", POSITION_HEADER_ALIASES)


def test_draconic_position_header_accepts_legacy_and_qualified_forms() -> None:
    assert _header_matches("DRACONIC POSITIONS", DRACONIC_POSITION_HEADER_ALIASES)
    assert _header_matches("POSITIONS (Draconic)", DRACONIC_POSITION_HEADER_ALIASES)


def test_chart_summary_displays_tropical_but_preserves_legacy_splitline_header() -> None:
    summary = _ChartSummaryText("HEADER\nPOSITIONS (Tropical)\nBody  Sign")

    assert "POSITIONS (Tropical)" in summary
    assert summary.splitlines()[1] == "POSITIONS"
