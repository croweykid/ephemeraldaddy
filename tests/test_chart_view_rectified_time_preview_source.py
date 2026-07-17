from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    start = APP_SOURCE.index(f"    def {name}(")
    next_start = APP_SOURCE.find("\n    def ", start + 1)
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_rectified_time_preview_only_queues_lightweight_sections():
    method = _method_source("_refresh_chart_preview")

    assert 'sections={"summary", "wheel"}' in method
    assert "refresh_time_sensitivity=False" in method
    assert "_mark_chart_analytics_sections_lucy_goosey()" in method
    assert "chart.dominant_sign_weights = _calculate_dominant_sign_weights(chart)" not in method
    assert "chart.dominant_planet_weights = _calculate_dominant_planet_weights(chart)" not in method
    assert "chart.dominant_nakshatra_weights = _calculate_dominant_nakshatra_weights(chart)" not in method


def test_chart_render_can_skip_time_sensitivity_refresh_for_live_timing_preview():
    method = _method_source("_schedule_chart_render")

    assert "refresh_time_sensitivity: bool = True" in method
    assert "refresh_time_sensitivity" in method.split("time_sensitivity_panel.refresh_for_current_chart()", 1)[0]
