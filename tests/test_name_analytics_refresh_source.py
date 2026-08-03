from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
ANALYTICS_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/database_analytics.py"
).read_text(encoding="utf-8")


def test_name_alignment_chart_uses_full_signed_scale_and_signed_labels():
    render_source = ANALYTICS_SOURCE.split(
        "def _render_name_distribution_section", 1
    )[1].split("DATABASE_ANALYTICS_CATEGORY_TITLES", 1)[0]
    assert "axis.set_xlim(-10.8, 10.8)" in render_source
    assert 'ha="left" if value >= 0 else "right"' in render_source
    assert "axis.axvline(" in render_source


def test_chart_view_classifies_name_and_alias_edits_for_metrics_refresh():
    classifier = APP_SOURCE.split("def _chart_metadata_changed_fields", 1)[1].split(
        "def _chart_analytics_cache_token", 1
    )[0]
    refresh_gate = APP_SOURCE.split("def _database_refresh_requires_metrics", 1)[1].split(
        "def _refresh_manage_charts_in_background", 1
    )[0]
    for field in ("name", "alias"):
        assert f'"{field}": lambda value:' in classifier
        assert f'"{field}",' in refresh_gate
