from pathlib import Path


SOURCE = Path("ephemeraldaddy/gui/features/charts/database_analytics.py").read_text(encoding="utf-8")


def test_traits_distribution_partial_render_schedules_warm_refresh():
    schedule_method = SOURCE.split("def _schedule_traits_distribution_warm_refresh", 1)[1].split(
        "def _render_traits_distribution_section", 1
    )[0]
    render_method = SOURCE.split("def _render_traits_distribution_section", 1)[1].split(
        "def _render_enneagram_section", 1
    )[0]
    assert "_traits_distribution_warm_refresh_scheduled" in schedule_method
    assert "QTimer.singleShot(750, _refresh)" in schedule_method
    assert 'sections_to_refresh={"traits_distribution"}' in schedule_method
    assert "if database_partial:" in render_method
    assert "self._schedule_traits_distribution_warm_refresh()" in render_method
