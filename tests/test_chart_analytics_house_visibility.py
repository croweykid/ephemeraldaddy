from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.section_availability import (
    is_chart_analysis_section_available,
)


def _uses_houses(chart: object) -> bool:
    return bool(getattr(chart, "chart_uses_houses", False))


def test_houses_section_follows_current_chart_house_availability():
    chart = SimpleNamespace(chart_uses_houses=False)

    assert not is_chart_analysis_section_available(
        "dominant_houses", chart, uses_houses=_uses_houses
    )

    chart.chart_uses_houses = True

    assert is_chart_analysis_section_available(
        "dominant_houses", chart, uses_houses=_uses_houses
    )


def test_other_sections_and_empty_chart_remain_available():
    untimed_chart = SimpleNamespace(chart_uses_houses=False)

    assert is_chart_analysis_section_available(
        "dominant_signs", untimed_chart, uses_houses=_uses_houses
    )
    assert is_chart_analysis_section_available(
        "dominant_houses", None, uses_houses=_uses_houses
    )
