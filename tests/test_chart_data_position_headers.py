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


def test_position_row_coloring_accepts_qualified_position_sections() -> None:
    from ephemeraldaddy.gui.features.charts.chart_data_output import _is_position_row_color_section

    assert _is_position_row_color_section("POSITIONS")
    assert _is_position_row_color_section("POSITIONS (Tropical)")
    assert _is_position_row_color_section("POSITIONS (Draconic)")
    assert _is_position_row_color_section("UNCERTAIN TIME VARIANTS")
    assert not _is_position_row_color_section("ASPECTS")


def test_draconic_node_refresh_uses_rectified_effective_datetime(monkeypatch) -> None:
    import datetime
    from types import SimpleNamespace

    from ephemeraldaddy.gui.features.charts import text_summary

    official_dt = datetime.datetime(2000, 1, 2, 10, 15, tzinfo=datetime.timezone.utc)
    chart = SimpleNamespace(
        dt=official_dt,
        lat=40.0,
        lon=-74.0,
        birthtime_unknown=False,
        retcon_time_used=True,
        retcon_hour=14,
        retcon_minute=37,
        use_birth_time_data=True,
    )
    captured = {}

    def fake_planetary_positions(dt, lat, lon):
        captured["dt"] = dt
        captured["lat"] = lat
        captured["lon"] = lon
        return {"Rahu": 123.0}

    monkeypatch.setattr(text_summary, "planetary_positions", fake_planetary_positions)
    result = text_summary._planetary_positions_at_effective_chart_time(chart)

    assert result == {"Rahu": 123.0}
    assert captured["dt"] == official_dt.replace(hour=14, minute=37, second=0, microsecond=0)
    assert captured["lat"] == 40.0
    assert captured["lon"] == -74.0
