from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/features/charts/database_analytics.py").read_text()


def test_database_analytics_enneagram_labels_use_compact_database_counts():
    assert 'f"e{enneagram_type} "' in SOURCE
    assert "({int(database_cache.get('enneagram_totals', {}).get(enneagram_type, 0)):,} in DB)" in SOURCE
    assert "include_count_prefixes=False" in SOURCE


def test_database_analytics_enneagram_popout_uses_standard_info_html():
    assert "build_enneagram_popout_info_html(" in SOURCE
    assert "_enneagram_type_for_database_label" in SOURCE
    assert "chart_theme_colors=CHART_THEME_COLORS" in SOURCE
    assert "highlight_color=CHART_DATA_HIGHLIGHT_COLOR" in SOURCE
