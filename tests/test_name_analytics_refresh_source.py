import re
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


def test_name_score_dropdown_combines_mean_median_and_mode_series():
    render_source = ANALYTICS_SOURCE.split(
        "def _render_name_distribution_section", 1
    )[1].split("DATABASE_ANALYTICS_CATEGORY_TITLES", 1)[0]
    name_panel_source = APP_SOURCE.split(
        '"👤Names",', 1
    )[1].split("# Keep the usual Tags section", 1)[0]

    assert '("Alignment Score", "alignment_score")' in name_panel_source
    assert '("Social Score", "social_score")' in name_panel_source
    assert '(f"mean_{score_prefix}", "Mean",' in render_source
    assert '(f"median_{score_prefix}", "Median",' in render_source
    assert '(f"mode_{score_prefix}", "Mode",' in render_source
    assert 'axis.legend(' in render_source
    assert 'export_labels.append(f"{label} — {metric_label}")' in render_source
    assert "for metric_name, metric_label, _color in metric_names" in render_source


def test_name_chart_height_scales_with_every_rendered_label_without_a_cap():
    height_source = ANALYTICS_SOURCE.split(
        "def _name_distribution_chart_height", 1
    )[1].split("def _render_name_distribution_section", 1)[0]
    render_source = ANALYTICS_SOURCE.split(
        "def _render_name_distribution_section", 1
    )[1].split("DATABASE_ANALYTICS_CATEGORY_TITLES", 1)[0]

    assert "label_count * label_row_height" in height_source
    assert "min(" not in height_source
    assert "max(" not in height_source
    assert render_source.count("self._name_distribution_chart_height(len(labels))") == 2

    row_height = float(re.search(r"label_row_height = ([\d.]+)", height_source).group(1))
    axis_space = float(re.search(r"axes_vertical_space = ([\d.]+)", height_source).group(1))
    assert axis_space + row_height >= 2.8
    assert axis_space + (100 * row_height) > axis_space + (10 * row_height)


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


def test_name_analytics_interface_and_export_matching_are_uid_first():
    render_source = ANALYTICS_SOURCE.split(
        "def _render_name_distribution_section", 1
    )[1].split("DATABASE_ANALYTICS_CATEGORY_TITLES", 1)[0]
    matching_source = ANALYTICS_SOURCE.split(
        "def _analysis_matching_charts", 1
    )[1].split("def _analysis_matching_chart_names", 1)[0]
    assert "chart_uids: Iterable[str]" in render_source
    assert "database_chart_uids: Iterable[str]" in render_source
    assert "_get_chart_for_filter_by_uid" in render_source
    assert "_get_chart_for_filter(int(" not in render_source
    assert 'chart_key == "name_distribution"' in matching_source
    assert "chart_has_name_token(" in matching_source
    assert "stopwords=name_stopwords" in matching_source


def test_name_distribution_is_hidden_from_gen_pop_without_a_name_baseline():
    hidden_sections = APP_SOURCE.split(
        "GEN_POP_HIDDEN_DATABASE_METRIC_SECTIONS", 1
    )[1].split("SIMILAR_CHARTS_EXPORT_FORMAT_KEY", 1)[0]
    assert '"name_distribution"' in hidden_sections


def test_social_score_inputs_refresh_the_name_ranking():
    dependencies = ANALYTICS_SOURCE.split(
        "DATABASE_METRICS_SUBJECTIVE_SECTION_DEPENDENCIES", 1
    )[1].split("def database_metrics_sections_for_changed_fields", 1)[0]
    for field in (
        "social_score",
        "positive_sentiment_intensity",
        "negative_sentiment_intensity",
        "familiarity",
    ):
        assert re.search(
            rf'"{field}": frozenset\(\s*'
            r'\{"alignment_summary", "name_distribution"\}\s*\)',
            dependencies,
        )


def test_chart_and_batch_edit_paths_emit_social_score_input_changes():
    classifier = APP_SOURCE.split("def _chart_metadata_changed_fields", 1)[1].split(
        "def _chart_analytics_cache_token", 1
    )[0]
    batch_assign = APP_SOURCE.split(
        "def _on_batch_sentiment_metric_assign", 1
    )[1].split("def _on_batch_metric_field_lucygoosey", 1)[0]
    refresh_gate = APP_SOURCE.split(
        "def _database_refresh_requires_metrics", 1
    )[1].split("def _refresh_manage_charts_in_background", 1)[0]
    for field in (
        "positive_sentiment_intensity",
        "negative_sentiment_intensity",
        "familiarity",
    ):
        assert f'"{field}": lambda value:' in classifier
        assert f'"{field}",' in refresh_gate
    assert "metric_sections = {metric_attr}" in batch_assign
    assert 'changed_fields={"familiarity"}' in APP_SOURCE


def test_grouped_export_labels_still_match_the_base_name_token():
    matching_source = ANALYTICS_SOURCE.split(
        "def _analysis_matching_charts", 1
    )[1].split("def _analysis_matching_chart_names", 1)[0]
    assert 'r"\\s+—\\s+(?:Mean|Median|Mode)$"' in matching_source
