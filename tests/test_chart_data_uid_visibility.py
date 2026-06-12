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


def _chart(uid: str = "UID123ABC") -> SimpleNamespace:
    return SimpleNamespace(
        name="UID Test",
        alias="",
        dt=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        birthtime_unknown=False,
        retcon_time_used=False,
        birth_place="New York, USA",
        lat=40.7128,
        lon=-74.0060,
        chart_uid=uid,
        positions={},
        houses=[],
        aspects=[],
        retrogrades={},
    )


def test_chart_uid_is_hidden_from_chart_data_output_by_default():
    summary, _position_info, _aspect_info, _species_info = format_chart_text(_chart())

    assert "Chart ID:" not in summary


def test_chart_uid_displays_between_place_and_positions_when_enabled():
    summary, _position_info, _aspect_info, _species_info = format_chart_text(
        _chart("ABCDEF123456"),
        show_chart_uid=True,
    )
    lines = summary.splitlines()

    place_index = next(index for index, line in enumerate(lines) if line.startswith("Place:"))
    chart_id_index = lines.index("Chart ID: ABCDEF123456")
    positions_index = lines.index("POSITIONS")

    assert place_index < chart_id_index < positions_index
