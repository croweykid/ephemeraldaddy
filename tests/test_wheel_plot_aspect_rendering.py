from types import ModuleType, SimpleNamespace
import sys

import matplotlib

matplotlib.use("Agg")

import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure


style_stub = ModuleType("ephemeraldaddy.gui.style")
style_stub.DARK_THEME = {
    "background": "#111111",
    "foreground": "#eeeeee",
    "wheel_circle": "#dddddd",
    "house_line": "#555555",
}
sys.modules.setdefault("ephemeraldaddy.gui.style", style_stub)

from ephemeraldaddy.graphics.wheel_plot import (
    HOVER_LABEL_ARTIST_ZORDER,
    HOVER_LABEL_AXES_ZORDER,
    _aspect_endpoint_xy,
    draw_chart_wheel,
)


def _cartesian_aspect_axes(fig):
    axes = [ax for ax in fig.axes if ax.name == "rectilinear"]
    assert len(axes) == 1
    return axes[0]


def _hover_label_axes(fig):
    axes = [ax for ax in fig.axes if ax.get_zorder() == HOVER_LABEL_AXES_ZORDER]
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


def test_hovering_aspect_endpoint_shows_endpoint_aspect_label():
    chart = SimpleNamespace(
        name="Endpoint hover test",
        positions={"Sun": 30.0, "Moon": 90.0},
        aspects=[
            {"p1": "Sun", "p2": "Moon", "type": "sextile", "angle": 60.0, "delta": 0.0},
        ],
        birthtime_unknown=False,
    )
    fig = Figure(figsize=(4, 4))

    draw_chart_wheel(fig, chart, show_title=False)
    fig.canvas.draw()

    aspect_axes = _cartesian_aspect_axes(fig)
    endpoint_xy = _aspect_endpoint_xy(30, 0.65)
    endpoint_display_xy = aspect_axes.transData.transform(endpoint_xy)
    event = MouseEvent(
        "motion_notify_event",
        fig.canvas,
        endpoint_display_xy[0],
        endpoint_display_xy[1],
    )

    fig.canvas.callbacks.process("motion_notify_event", event)

    hover_axes = _hover_label_axes(fig)
    visible_labels = [text.get_text() for text in hover_axes.texts if text.get_visible()]
    assert any("Sun: Taurus 00°00'" in label for label in visible_labels)
    assert any("Sun Sextile Moon" in label for label in visible_labels)


def test_hover_labels_render_above_chart_glyphs_lines_and_outline():
    chart = SimpleNamespace(
        name="Hover z-order test",
        positions={"Sun": 30.0, "Moon": 90.0},
        aspects=[
            {"p1": "Sun", "p2": "Moon", "type": "sextile", "angle": 60.0, "delta": 0.0},
        ],
        birthtime_unknown=False,
    )
    fig = Figure(figsize=(4, 4))

    draw_chart_wheel(fig, chart, show_title=False)

    hover_axes = _hover_label_axes(fig)
    non_hover_axes = [ax for ax in fig.axes if ax is not hover_axes]
    assert all(hover_axes.get_zorder() > ax.get_zorder() for ax in non_hover_axes)
    assert hover_axes.texts
    assert all(text.get_zorder() == HOVER_LABEL_ARTIST_ZORDER for text in hover_axes.texts)
