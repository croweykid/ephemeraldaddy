from types import ModuleType, SimpleNamespace
import sys

import matplotlib

matplotlib.use("Agg")

import pytest
from matplotlib.figure import Figure


style_stub = ModuleType("ephemeraldaddy.gui.style")
style_stub.DARK_THEME = {
    "background": "#111111",
    "foreground": "#eeeeee",
    "wheel_circle": "#dddddd",
    "house_line": "#555555",
}
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#c8945c"
style_stub.CHART_DATA_DIVIDER = "────────────────"
style_stub.blend_hex_colors = lambda first, second, ratio=0.5: first
style_stub.format_chart_header = lambda *_args, **_kwargs: ""
sys.modules.setdefault("ephemeraldaddy.gui.style", style_stub)

from ephemeraldaddy.graphics.wheel_plot import _aspect_endpoint_xy, draw_chart_wheel


def _cartesian_aspect_axes(fig):
    axes = [ax for ax in fig.axes if ax.name == "rectilinear"]
    assert len(axes) == 1
    return axes[0]


def test_aspect_endpoint_xy_matches_clockwise_zodiac_wheel():
    radius = 0.65

    assert _aspect_endpoint_xy(0, radius) == pytest.approx((radius, 0.0))
    assert _aspect_endpoint_xy(90, radius) == pytest.approx((0.0, -radius), abs=1e-12)
    assert _aspect_endpoint_xy(180, radius) == pytest.approx((-radius, 0.0), abs=1e-12)
    assert _aspect_endpoint_xy(270, radius) == pytest.approx((0.0, radius), abs=1e-12)


def test_overlay_aspect_drawn_once_at_true_longitude_endpoints():
    chart = SimpleNamespace(
        name="Overlay endpoint test",
        positions={},
        aspects=[],
        birthtime_unknown=False,
    )
    fig = Figure(figsize=(4, 4))

    draw_chart_wheel(
        fig,
        chart,
        overlay_aspects=[{"type": "trine", "lon1_deg": 30, "lon2_deg": 120, "score": 1.0}],
        overlay_aspects_only=True,
        show_title=False,
    )

    aspect_axes = _cartesian_aspect_axes(fig)
    lines = aspect_axes.lines
    assert len(lines) == 1

    line = lines[0]
    expected_start = _aspect_endpoint_xy(30, 0.65)
    expected_end = _aspect_endpoint_xy(120, 0.65)
    assert tuple(line.get_xdata()) == pytest.approx((expected_start[0], expected_end[0]))
    assert tuple(line.get_ydata()) == pytest.approx((expected_start[1], expected_end[1]))


def test_structural_axis_tautologies_are_hidden_from_chart_wheel_aspects():
    chart = SimpleNamespace(
        name="Structural aspect test",
        positions={"AS": 0.0, "DS": 180.0, "Sun": 30.0, "Moon": 90.0},
        aspects=[
            {"p1": "AS", "p2": "DS", "type": "opposition", "angle": 180.0, "delta": 0.0},
            {"p1": "Sun", "p2": "Moon", "type": "sextile", "angle": 60.0, "delta": 0.0},
        ],
        birthtime_unknown=False,
    )
    fig = Figure(figsize=(4, 4))

    draw_chart_wheel(fig, chart, show_title=False)

    aspect_axes = _cartesian_aspect_axes(fig)
    lines = aspect_axes.lines
    assert len(lines) == 1

    line = lines[0]
    expected_start = _aspect_endpoint_xy(30, 0.65)
    expected_end = _aspect_endpoint_xy(90, 0.65)
    assert tuple(line.get_xdata()) == pytest.approx((expected_start[0], expected_end[0]))
    assert tuple(line.get_ydata()) == pytest.approx((expected_start[1], expected_end[1]))
