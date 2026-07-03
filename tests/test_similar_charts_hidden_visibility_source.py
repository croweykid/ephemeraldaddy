from pathlib import Path


def _app_source() -> str:
    return Path("ephemeraldaddy/gui/app.py").read_text()


def _popout_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/similar_charts_popout.py").read_text()


def _worker_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/similar_charts_worker.py").read_text()


def test_similar_charts_candidates_skip_hidden_charts_unless_show_hidden_enabled():
    source = _popout_source()
    method = source.split("def load_similar_chart_candidates", 1)[1].split(
        "def format_similar_chart_name_parts_html", 1
    )[0]

    assert "hidden_chart_ids: set[int] | None = None" in method
    assert "include_hidden_charts: bool = True" in method
    assert "if not include_hidden_charts and chart_id in hidden_ids:" in method
    assert "continue" in method.split("if not include_hidden_charts and chart_id in hidden_ids:", 1)[1]


def test_similar_charts_app_passes_current_hidden_chart_visibility_to_candidates():
    source = _app_source()
    load_method = source.split("def _load_similar_chart_candidates", 1)[1].split(
        "def _similar_charts_visible_candidate_rows", 1
    )[0]
    visible_rows_method = source.split("def _similar_charts_visible_candidate_rows", 1)[1].split(
        "def _similar_charts_popout_database_row_signatures", 1
    )[0]
    popout_method = source.split("def _show_similar_charts_popout", 1)[1].split(
        "def _export_similar_charts_popout_share", 1
    )[0]

    assert 'hidden_chart_ids=set(getattr(self, "_hidden_chart_ids", set()))' in load_method
    assert 'include_hidden_charts=bool(getattr(self, "_show_hidden_charts", False))' in load_method
    assert 'if getattr(self, "_show_hidden_charts", False):' in visible_rows_method
    assert 'if chart_id not in hidden_chart_ids:' in visible_rows_method
    assert "chart_rows = self._similar_charts_visible_candidate_rows(chart_rows)" in popout_method
    assert popout_method.index("chart_rows = self._similar_charts_visible_candidate_rows(chart_rows)") < popout_method.index("row_signatures =")


def test_chart_view_similar_charts_worker_receives_hidden_chart_visibility():
    app_source = _app_source()
    start_method = app_source.split("def _start_similar_charts_worker", 1)[1].split(
        "def _forget_similar_charts_worker_job", 1
    )[0]
    worker_source = _worker_source()

    assert 'hidden_chart_ids=set(getattr(self, "_hidden_chart_ids", set()))' in start_method
    assert 'include_hidden_charts=bool(getattr(self, "_show_hidden_charts", False))' in start_method
    assert "hidden_chart_ids: set[int] | None = None" in worker_source
    assert "self._hidden_chart_ids = set(hidden_chart_ids or set())" in worker_source
    assert "include_hidden_charts=self._include_hidden_charts" in worker_source
    assert "load_charts_by_ids=load_charts" in worker_source


def _astro_twin_source() -> str:
    return Path("ephemeraldaddy/analysis/get_astro_twin.py").read_text()


def _database_analytics_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/database_analytics.py").read_text()


def test_find_astro_twins_can_filter_hidden_candidates_before_scoring():
    source = _astro_twin_source()
    method = source.split("def find_astro_twins", 1)[1].split("def ", 1)[0]

    assert "hidden_chart_ids: set[int] | None = None" in method
    assert "include_hidden_charts: bool = False" in method
    assert "hidden_ids = {int(chart_id) for chart_id in (hidden_chart_ids or set())}" in method
    assert "if not include_hidden_charts and int(chart_id) in hidden_ids:" in method
    assert "continue" in method.split("if not include_hidden_charts and int(chart_id) in hidden_ids:", 1)[1]


def test_trait_prediction_rankings_skip_hidden_charts_but_keep_aggregate_cache_scope():
    source = _database_analytics_source()
    ranking_method = source.split("def _traits_distribution_chart_rankings", 1)[1].split(
        "@staticmethod\n    def _render_traits_distribution_rankings_html", 1
    )[0]
    collect_method = source.split("def _collect_traits_distribution_analytics", 1)[1].split(
        "def _render_traits_distribution_section", 1
    )[0]

    assert 'hidden_chart_ids = {int(chart_id) for chart_id in getattr(self, "_hidden_chart_ids", set())}' in ranking_method
    assert "if int(chart_id) in hidden_chart_ids:" in ranking_method
    assert "continue" in ranking_method.split("if int(chart_id) in hidden_chart_ids:", 1)[1]
    assert "_hidden_chart_ids" not in collect_method


def test_trait_predictions_and_rankings_are_separate_dropdown_modes():
    source = _database_analytics_source()
    create_method = source.split("def _create_traits_database_analytics_section", 1)[1].split(
        "def _traits_distribution_display_mode", 1
    )[0]
    dropdown_handler = _app_source().split("def _on_analysis_chart_dropdown_changed", 1)[1].split(
        "if chart_key == \"human_design\":", 1
    )[0]

    assert '("Trait Predictions", "trait_predictions")' in create_method
    assert '("Trait Rankings", "trait_rankings")' in create_method
    assert "self.traits_distribution_rank_container = QWidget()" in create_method
    assert "self._sync_traits_distribution_display_mode()" in create_method
    assert 'if chart_key == "traits_distribution":' in dropdown_handler
    assert '"manage_charts/traits_distribution_mode"' in dropdown_handler


def test_hiding_current_trait_ranking_members_refreshes_cached_top_ten():
    analytics_source = _database_analytics_source()
    refresh_method = analytics_source.split(
        "def _refresh_traits_distribution_rankings_after_hidden_chart_change", 1
    )[1].split("def _on_traits_distribution_rank_trait_changed", 1)[0]
    render_method = analytics_source.split("def _render_traits_distribution_section", 1)[1].split(
        "def _render_enneagram_section", 1
    )[0]
    app_source = _app_source()
    hide_method = app_source.split("def _hide_selected_charts", 1)[1].split("def _unhide_selected_charts", 1)[0]

    assert "_traits_distribution_current_ranked_chart_ids" in refresh_method
    assert "set(hidden_chart_ids) & set(current_ranked_ids)" in refresh_method
    assert "self._refresh_traits_distribution_rankings_from_cached_context()" in refresh_method
    assert "self._traits_distribution_rank_context =" in render_method
    assert "self._traits_distribution_current_ranked_chart_ids" in render_method
    assert "_refresh_traits_distribution_rankings_after_hidden_chart_change" in hide_method
