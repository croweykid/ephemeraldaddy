from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.quadrants import (
    aggregate_house_values_by_quadrant,
    build_quadrant_export_rows,
    build_quadrant_info_html,
    draw_quadrants,
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
    assert quadrant_for_house(1.9) is None
    assert quadrant_for_house(True) is None


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


def test_untimed_quadrants_render_message_and_do_not_export():
    from matplotlib.figure import Figure

    chart = SimpleNamespace(birthtime_unknown=True, retcon_time_used=False)
    ax = Figure().subplots()

    draw_quadrants(SimpleNamespace(), ax, chart)

    assert [text.get_text() for text in ax.texts] == [
        "Sorry, quadrants cannot be calculated without birth time. :("
    ]
    assert build_quadrant_export_rows(chart, "quadrant_prevalence") == []


def test_quadrant_export_rows_follow_active_mode(monkeypatch):
    import ephemeraldaddy.gui.features.charts.quadrants as quadrants

    chart = SimpleNamespace(birthtime_unknown=False, retcon_time_used=False)
    monkeypatch.setattr(
        quadrants,
        "calculate_dominant_quadrant_weights",
        lambda _chart: {"I": 1.25, "II": 2.25, "III": 3.25, "IV": 3.25},
    )

    rows = build_quadrant_export_rows(chart, "dominant_quadrants")

    assert rows == [
        ["QI", "Personal Identity", "H1–H3", 1.2, 12.5],
        ["QII", "Personal Expression", "H4–H6", 2.2, 22.5],
        ["QIII", "Social Identity", "H7–H9", 3.2, 32.5],
        ["QIV", "Social Expression", "H10–H12", 3.2, 32.5],
    ]


def test_quadrant_signature_connects_clockwise_and_includes_breakdown(monkeypatch):
    from matplotlib.figure import Figure
    import ephemeraldaddy.gui.features.charts.quadrants as quadrants

    chart = SimpleNamespace(birthtime_unknown=False, retcon_time_used=False)
    monkeypatch.setattr(
        quadrants,
        "calculate_house_prevalence_counts",
        lambda _chart: {1: 1, 4: 2, 7: 3, 10: 4},
    )
    ax = Figure().subplots()

    draw_quadrants(SimpleNamespace(), ax, chart, interactive=True)

    signature = ax.lines[0]
    assert list(zip(signature.get_xdata(), signature.get_ydata(), strict=True)) == [
        (-0.1, -0.1),
        (0.2, -0.2),
        (0.3, 0.3),
        (-0.4, 0.4),
        (-0.1, -0.1),
    ]
    assert "QIV  4 · 40%" in ax.texts[-1].get_text()
    assert {artist.get_gid() for artist in [*ax.lines, *ax.texts]} >= {
        "quadrant:I", "quadrant:II", "quadrant:III", "quadrant:IV"
    }
