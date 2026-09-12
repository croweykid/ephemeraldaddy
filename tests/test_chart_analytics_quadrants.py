from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.quadrants import (
    aggregate_house_values_by_quadrant,
    build_quadrant_info_html,
    install_quadrants_owner_reset_hook,
    quadrant_for_house,
    quadrant_percentages,
)


def test_quadrant_for_house_boundaries():
    assert quadrant_for_house(1) == "I"
    assert quadrant_for_house(3) == "I"
    assert quadrant_for_house(4) == "II"
    assert quadrant_for_house(6) == "II"
    assert quadrant_for_house(7) == "III"
    assert quadrant_for_house(9) == "III"
    assert quadrant_for_house(10) == "IV"
    assert quadrant_for_house(12) == "IV"


def test_quadrant_for_house_rejects_invalid_values():
    assert quadrant_for_house(None) is None
    assert quadrant_for_house(0) is None
    assert quadrant_for_house(13) is None
    assert quadrant_for_house("nope") is None


def test_aggregate_house_values_by_quadrant():
    values = {1: 1, 2: 2.5, 4: 4, 8: 8, 12: 12, None: 99, 13: 99}
    assert aggregate_house_values_by_quadrant(values) == {
        "I": 3.5,
        "II": 4.0,
        "III": 8.0,
        "IV": 12.0,
    }


def test_quadrant_percentages_are_zero_safe_and_normalized():
    assert quadrant_percentages({}) == {"I": 0.0, "II": 0.0, "III": 0.0, "IV": 0.0}
    assert quadrant_percentages({"I": 1, "II": 1, "III": 1, "IV": 1}) == {
        "I": 25.0,
        "II": 25.0,
        "III": 25.0,
        "IV": 25.0,
    }


def test_quadrant_info_exposes_house_range_and_axis_meaning():
    html = build_quadrant_info_html("IV")

    assert "Quadrant IV" in html
    assert "Social Expression" in html
    assert "Houses 10–12" in html
    assert "Social / Public" in html
    assert "Self-Directed" in html


def test_common_chart_display_reset_also_clears_quadrants():
    calls: list[object] = []
    quadrant_layout = object()
    old_canvas = object()

    def clear_chart_displays():
        calls.append("common-reset")

    def clear_layout_widgets(layout):
        calls.append(layout)

    owner = SimpleNamespace(
        quadrants_chart_container_layout=quadrant_layout,
        quadrants_canvas=old_canvas,
        _clear_chart_displays=clear_chart_displays,
        _clear_layout_widgets=clear_layout_widgets,
    )
    controller = SimpleNamespace(_owner=owner)

    install_quadrants_owner_reset_hook(controller)
    owner._clear_chart_displays()

    assert calls == ["common-reset", quadrant_layout]
    assert owner.quadrants_canvas is None


def test_quadrants_reset_hook_is_idempotent():
    calls: list[str] = []

    def clear_chart_displays():
        calls.append("common-reset")

    owner = SimpleNamespace(
        quadrants_chart_container_layout=None,
        quadrants_canvas=object(),
        _clear_chart_displays=clear_chart_displays,
        _clear_layout_widgets=lambda _layout: None,
    )
    controller = SimpleNamespace(_owner=owner)

    install_quadrants_owner_reset_hook(controller)
    install_quadrants_owner_reset_hook(controller)
    owner._clear_chart_displays()

    assert calls == ["common-reset"]
    assert owner.quadrants_canvas is None
