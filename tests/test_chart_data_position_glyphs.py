import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"
style_stub.CHART_DATA_DIVIDER = "---------"
style_stub.format_chart_header = lambda _key, *, birth_place, lat, lon: f"Place: {birth_place} | {lat:.4f}, {lon:.4f}"
style_stub.blend_hex_colors = lambda first, second, ratio=0.5: first

from ephemeraldaddy.gui.features.charts.text_summary import format_chart_text


def _chart(*, birthtime_unknown: bool = False, retcon_time_used: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        name="Glyph Test",
        alias="",
        dt=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        birthtime_unknown=birthtime_unknown,
        retcon_time_used=retcon_time_used,
        birth_place="New York, USA",
        lat=40.7128,
        lon=-74.0060,
        positions={
            "Sun": 125.0,      # Leo: rulership
            "Moon": 35.0,      # Taurus: exaltation
            "Mercury": 250.0,  # Sagittarius: detriment
            "Saturn": 5.0,     # Aries: fall
            "Venus": 132.0,    # 5th house in this fixture: planetary joy
        },
        houses=[0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        aspects=[],
        retrogrades={},
    )


def _position_line(summary: str, body: str) -> str:
    return next(line for line in summary.splitlines() if body in line)


def test_chart_data_positions_prefix_signs_with_dignity_and_debility_glyphs():
    summary, _position_info, _aspect_info, _species_info = format_chart_text(_chart())

    assert "↑↑Leo" in _position_line(summary, "Sun")
    assert "↑Taurus" in _position_line(summary, "Moon")
    assert "↓Sagittarius" in _position_line(summary, "Mercury")
    assert "↓↓Aries" in _position_line(summary, "Saturn")


def test_chart_data_positions_prefix_joy_house_when_houses_are_available():
    summary, _position_info, _aspect_info, _species_info = format_chart_text(_chart())

    assert "💞H5" in _position_line(summary, "Venus")


def test_chart_data_positions_do_not_show_joy_house_without_houses_or_rectified_time():
    summary, _position_info, _aspect_info, _species_info = format_chart_text(_chart(birthtime_unknown=True))

    assert "💞H5" not in summary
    assert "↑↑Leo" in _position_line(summary, "Sun")
