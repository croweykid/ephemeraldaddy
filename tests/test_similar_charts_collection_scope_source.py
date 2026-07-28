from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()
POPOUT_SOURCE = Path("ephemeraldaddy/gui/features/charts/similar_charts_popout.py").read_text()


def _show_popout_source() -> str:
    return APP_SOURCE.split("    def _show_similar_charts_popout(", 1)[1].split(
        "    def _export_similar_charts_popout_share", 1
    )[0]


def test_collection_scope_is_applied_before_cache_signatures_and_scoring():
    source = _show_popout_source()

    scope_position = source.index("allowed_collection_uids = chart_uids_in_collection(")
    signature_position = source.index("row_signatures = self._similar_charts_popout_database_row_signatures(")
    scoring_position = source.index("most_similar_matches = find_astro_twins(")

    assert scope_position < signature_position < scoring_position
    assert "chart_rows = [\n                row\n                for row in chart_rows" in source


def test_scoped_candidates_still_flow_through_normal_algorithm_and_demographic_settings():
    source = _show_popout_source()
    scoring_call = source.split("most_similar_matches = find_astro_twins(", 1)[1].split(
        "raise_if_progress_canceled(progress)", 1
    )[0]

    assert "candidates" in scoring_call
    assert "algorithm_mode=algorithm_mode" in scoring_call
    assert 'custom_settings=getattr(self, "_similarity_calculator_settings", None)' in scoring_call


def test_collection_scope_is_not_a_post_ranking_slice():
    source = _show_popout_source()
    first_scoring_position = source.index("most_similar_matches = find_astro_twins(")

    assert "allowed_collection_uids" not in source[first_scoring_position:]


def test_custom_collection_membership_is_reloaded_before_scoping_candidates():
    source = _show_popout_source()
    reload_position = source.index(
        "self._custom_collections = self._load_custom_collections_from_settings()"
    )
    membership_position = source.index("allowed_collection_uids = chart_uids_in_collection(")

    assert reload_position < membership_position


def test_collection_selector_options_reload_manage_charts_edits():
    method = APP_SOURCE.split("    def _similar_chart_collection_options(", 1)[1].split(
        "    def _on_similar_chart_popout_collection_changed", 1
    )[0]

    assert "if not hasattr" not in method
    assert "self._custom_collections = self._load_custom_collections_from_settings()" in method


def test_replaced_popout_is_destroyed_when_collection_change_closes_it():
    builder = POPOUT_SOURCE.split("def build_similar_charts_popout_dialog(", 1)[1]

    assert "dialog.setAttribute(Qt.WA_DeleteOnClose, True)" in builder


def test_collection_change_closes_old_dialog_only_after_replacement_succeeds():
    method = APP_SOURCE.split(
        "    def _on_similar_chart_popout_collection_changed", 1
    )[1].split("    def _load_custom_collections_from_settings", 1)[0]

    replacement_position = method.index("replacement = self._show_similar_charts_popout(")
    success_position = method.index("if replacement is not None:")
    close_position = method.index("dialog.close()")
    assert replacement_position < success_position < close_position
    assert "QSignalBlocker(collection_dropdown)" in method
    assert "collection_dropdown.setCurrentIndex(previous_index)" in method


def test_collection_membership_loading_uses_normal_individual_fallback():
    source = _show_popout_source()
    membership_loader = source.split("collection_candidates = load_similar_chart_candidates(", 1)[1].split(
        "collection_charts_by_id = dict(collection_candidates)", 1
    )[0]

    assert "load_chart_by_id=load_chart" in membership_loader
    assert "load_charts_by_ids=load_charts" in membership_loader
