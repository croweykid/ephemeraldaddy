from pathlib import Path


def _app_source() -> str:
    return Path("ephemeraldaddy/gui/app.py").read_text()


def _popout_source() -> str:
    return Path("ephemeraldaddy/gui/features/charts/similar_charts_popout.py").read_text()


def _ranking_panel_source() -> str:
    return Path("ephemeraldaddy/gui/ranking_panel.py").read_text()


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

    assert 'hidden_chart_ids=set(self._hidden_local_row_ids_for_persistence())' in load_method
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

    assert 'hidden_chart_uids=set(self._hidden_chart_uids)' in start_method
    assert 'include_hidden_charts=bool(getattr(self, "_show_hidden_charts", False))' in start_method
    assert "hidden_chart_uids: set[str] | None = None" in worker_source
    assert "self._hidden_chart_uids =" in worker_source
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

    assert 'hidden_chart_uids = {' in ranking_method
    assert 'getattr(self, "_hidden_chart_uids", set())' in ranking_method
    assert "if chart_uid in hidden_chart_uids:" in ranking_method
    assert "_hidden_chart_uids" not in collect_method


def test_trait_rankings_are_moved_to_rankings_panel():
    database_source = _database_analytics_source()
    app_source = _app_source()
    ranking_panel_source = _ranking_panel_source()
    create_method = database_source.split("def _create_traits_database_analytics_section", 1)[1].split(
        "def _traits_distribution_display_mode", 1
    )[0]

    assert '("Trait Predictions", "trait_predictions")' in create_method
    assert '("Trait Rankings", "trait_rankings")' not in create_method
    assert 'from ephemeraldaddy.gui.ranking_panel import RankingsPanelMixin' in app_source
    assert 'class ManageChartsDialog(AspectPopoutMixin, RankingsPanelMixin, DatabaseAnalyticsChartsMixin, QDialog):' in app_source
    assert 'self.rankings_panel_button = QPushButton("🏆")' in app_source
    assert '"rankings": self.rankings_panel_scroll' in app_source
    assert '"🧬Traits"' in ranking_panel_source
    assert '"♏ Sign Dominance"' in ranking_panel_source
    assert 'self.rankings_trait_combo' in ranking_panel_source
    assert 'self.rankings_sign_combo.addItems(list(ZODIAC_NAMES))' in ranking_panel_source


def test_rankings_panel_uses_current_chart_uids_and_sequence_weight_loading():
    ranking_panel_source = _ranking_panel_source()
    uids_method = ranking_panel_source.split("def _rankings_database_chart_uids", 1)[1].split(
        "def _rankings_database_legacy_chart_ids", 1
    )[0]
    legacy_method = ranking_panel_source.split("def _rankings_database_legacy_chart_ids", 1)[1].split(
        "def _refresh_rankings_after_hidden_chart_change", 1
    )[0]
    sign_method = ranking_panel_source.split("def _refresh_sign_dominance_rankings", 1)[1]

    assert 'getattr(self, "_chart_rows", [])' in uids_method
    assert 'getattr(self, "chart_data", [])' not in uids_method
    assert 'getattr(self, "_database_metrics_cache", None)' not in uids_method
    assert 'chart_uids.add(chart_uid)' in uids_method
    assert 'get_chart_ids_by_uid(chart_uids)' in legacy_method
    assert 'normalized_chart_ids = tuple(sorted({int(chart_id) for chart_id in database_chart_ids}))' in sign_method
    assert 'load_dominant_sign_weights(list(normalized_chart_ids))' in sign_method
    assert 'chart_uids_by_id = get_chart_uid_map(normalized_chart_ids)' in sign_method
    assert 'hidden_chart_uids = {' in sign_method
    assert '"chart_uid": chart_uid' in sign_method
    assert "href='chart:{chart_uid}'" in sign_method
    assert 'for chart_id in normalized_chart_ids:' in sign_method


def test_rankings_links_use_chart_uids_for_navigation_targets():
    app_source = _app_source()
    ranking_panel_source = _ranking_panel_source()
    database_source = _database_analytics_source()
    app_link_method = app_source.split("def _on_similar_chart_link_activated", 1)[1].split(
        "def _on_similar_chart_popout_link_activated", 1
    )[0]
    rankings_refresh = ranking_panel_source.split("def _refresh_rankings_panel", 1)[1].split(
        "def _refresh_sign_dominance_rankings", 1
    )[0]
    renderer = database_source.split("def _render_traits_distribution_rankings_html", 1)[1].split(
        "def _collect_traits_distribution_analytics", 1
    )[0]
    link_handler = database_source.split("def _on_traits_distribution_rank_chart_link_activated", 1)[1].split(
        "@staticmethod", 1
    )[0]

    assert 'target_chart_uid = self._normalized_chart_uid_key(normalized_target)' in app_link_method
    assert 'database_chart_uids = tuple(' in rankings_refresh
    assert 'get_chart_uid_map(database_chart_ids).values()' in rankings_refresh
    assert 'chart_uids=database_chart_uids' in rankings_refresh
    assert 'chart_ids=database_chart_ids' not in rankings_refresh
    assert 'chart_uid = str(row.get("chart_uid", "") or "").strip()' in renderer
    assert 'chart_target = chart_uid' in renderer
    assert 'open_link(normalized_target, transition_to_chart_view=True)' in link_handler


def test_trait_rankings_default_to_database_until_manual_rank_selected():
    source = _database_analytics_source()
    create_method = source.split("def _create_traits_database_analytics_section", 1)[1].split(
        "def _traits_distribution_display_mode", 1
    )[0]
    click_method = source.split("def _on_traits_distribution_rank_selected_clicked", 1)[1].split(
        "def _sync_traits_distribution_rank_combo", 1
    )[0]
    render_method = source.split("def _render_traits_distribution_section", 1)[1].split(
        "def _render_enneagram_section", 1
    )[0]

    assert 'QPushButton("rank selected")' in create_method
    assert "_traits_distribution_latest_selected_chart_uids" in click_method
    assert "_traits_distribution_manual_rank_chart_uids = current_selection" in click_method
    assert 'rankings_mode = self._traits_distribution_display_mode() == "trait_rankings"' in render_method
    assert "if rankings_mode and manual_rank_ids:" in render_method
    assert "selection_analytics = self._collect_traits_distribution_analytics" in render_method.split(
        "if rankings_mode and manual_rank_ids:", 1
    )[1]
    assert "elif rankings_mode:" in render_method
    assert "selection_analytics = copy.deepcopy(database_analytics)" in render_method.split("elif rankings_mode:", 1)[1]
    assert "ranking_scope_uids = database_rank_uids" in render_method
    assert 'ranking_scope_label = "the database"' in render_method
    assert 'ranking_scope_label = "the manually ranked selection"' in render_method
    assert "rank_selected_button.setEnabled(has_current_selection or bool(manual_rank_ids))" in render_method
    assert '"rank selected" if has_current_selection else "show database"' in render_method


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

    assert "_traits_distribution_current_ranked_chart_uids" in refresh_method
    assert "hidden_uids & set(current_ranked_uids)" in refresh_method
    rankings_panel_source = _ranking_panel_source()
    rankings_refresh_method = rankings_panel_source.split(
        "def _refresh_rankings_after_hidden_chart_change", 1
    )[1].split("def _sync_rankings_trait_combo", 1)[0]

    assert "self._refresh_traits_distribution_rankings_from_cached_context()" in refresh_method
    assert "self._traits_distribution_rank_context =" in render_method
    assert "self._traits_distribution_current_ranked_chart_uids" in render_method
    assert "_refresh_traits_distribution_rankings_after_hidden_chart_change" in hide_method
    assert "_refresh_rankings_after_hidden_chart_change" in hide_method
    assert 'getattr(self, "_active_left_panel", None) != "rankings"' in rankings_refresh_method
    assert "self._refresh_rankings_panel()" in rankings_refresh_method


def test_sign_dominance_rankings_expand_for_cross_sign_top_20_memberships():
    ranking_panel_source = _ranking_panel_source()
    sign_method = ranking_panel_source.split("def _refresh_sign_dominance_rankings", 1)[1]

    assert "SIGN_COLORS" in ranking_panel_source
    assert "ZODIAC_SIGNS" in ranking_panel_source
    assert "sign_top_20_memberships" in sign_method
    assert "for row in sign_ranked_rows[:20]:" in sign_method
    assert "rows[:20]" in sign_method
    assert "shared_top_20_ranks" in sign_method
    assert "deepest_shared_rank = max(shared_top_20_ranks, default=0)" in sign_method
    assert "display_limit = min(20, max(10 + shared_top_20_count, deepest_shared_rank))" in sign_method
    assert "rows[:display_limit]" in sign_method
    assert "glyph_html" in sign_method
