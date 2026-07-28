from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


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
