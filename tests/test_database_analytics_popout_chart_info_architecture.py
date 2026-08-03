from pathlib import Path


def test_popout_chart_info_presentation_lives_in_database_view_workflow_package():
    presentation_source = Path(
        "ephemeraldaddy/gui/features/database_view/analytics/popout_chart_info.py"
    ).read_text(encoding="utf-8")
    legacy_source = Path(
        "ephemeraldaddy/gui/features/charts/database_analytics.py"
    ).read_text(encoding="utf-8")

    assert "def build_database_analytics_popout_chart_info_html(" in presentation_source
    assert "build_enneagram_popout_info_html(" in presentation_source
    assert "build_database_analytics_popout_chart_info_html(" in legacy_source
    assert "Database deviation: unavailable" not in legacy_source
