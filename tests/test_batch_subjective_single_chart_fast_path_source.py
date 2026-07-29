from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()
DB_SOURCE = Path("ephemeraldaddy/core/db.py").read_text()


def _method_source(name: str, next_name: str) -> str:
    start = APP_SOURCE.index(f"    def {name}")
    end = APP_SOURCE.index(f"    def {next_name}", start)
    return APP_SOURCE[start:end]


def test_single_sentiment_edit_uses_uid_lightweight_path():
    method = _method_source(
        "_on_batch_sentiment_toggled", "_on_batch_relationship_type_toggled"
    )
    fast_path_start = method.index("if selected_count == 1:")
    fast_path_end = method.index("        try:\n            patches_by_uid", fast_path_start)
    fast_path = method[fast_path_start:fast_path_end]
    assert "get_chart_uid(chart_id)" in fast_path
    assert "update_chart_subjective_list_by_uid" in fast_path
    assert "_calculate_dominant_sign_weights" not in method
    assert "update_chart(" not in method


def test_single_relationship_edit_uses_uid_lightweight_path():
    method = _method_source(
        "_on_batch_relationship_type_toggled",
        "_finalize_single_chart_subjective_batch_edit",
    )
    assert "if selected_count == 1:" in method
    assert 'update_chart_subjective_list_by_uid(\n                        chart_uid, "relationship_types"' in method
    assert "_finalize_single_chart_subjective_batch_edit" in method


def test_single_chart_finalize_does_not_queue_analytics_refresh():
    method = _method_source(
        "_finalize_single_chart_subjective_batch_edit",
        "_score_familiarity_from_factors",
    )
    assert "_database_metrics_preloaded_sections.difference_update" in method
    assert "refresh_metrics=False" in method
    assert "refresh_selection_state=False" in method
    assert "_update_sentiment_tally" not in method
    assert "owner._invalidate_chart_view_navigation_cache({chart_uid})" in method
    assert "expanded_affected_sections" in method
    assert "sections_to_refresh=expanded_affected_sections" in method
    assert "update_similarities=False" in method


def test_relationship_fast_path_keeps_collection_membership_current():
    method = _method_source(
        "_finalize_single_chart_subjective_batch_edit",
        "_score_familiarity_from_factors",
    )
    assert 'changed_field == "relationship_types"' in method
    assert "DEFAULT_COLLECTION_PERSONAL, DEFAULT_COLLECTION_PARASOCIAL" in method
    assert "mutable_row[24]" in method
    assert "self._chart_rows[row_index] = tuple(mutable_row)" in method
    assert (
        "self._has_active_chart_filters() or collection_membership_may_change"
        in method
    )


def test_subjective_db_writer_is_narrow_and_uid_based():
    start = DB_SOURCE.index("def update_chart_subjective_list_by_uid")
    end = DB_SOURCE.index("\ndef ", start + 5)
    method = DB_SOURCE[start:end]
    assert '"sentiments": _serialize_sentiments' in method
    assert '"relationship_types": _serialize_relationship_types' in method
    assert "WHERE UPPER(chart_uid) = ?" in method
    assert "update_chart(" not in method
    assert "_persist_chart_derived_cache" not in method


def test_batch_tag_additions_use_uid_only_metadata_writer():
    for method_name, next_name in (
        ("_on_batch_tag_item_clicked", "_parse_integer_filter_text"),
        ("_on_batch_tags_apply", "_update_batch_alignment_score_label"),
    ):
        method = _method_source(method_name, next_name)
        assert "self._selected_chart_uids()" in method
        assert "add_tag_to_charts_by_uid" in method
        assert "update_chart(" not in method
        assert "_calculate_dominant_sign_weights" not in method


def test_batch_tag_removal_never_loads_or_recalculates_charts():
    method = _method_source(
        "_on_batch_tag_remove_link_clicked", "_finalize_batch_tag_updates"
    )
    assert "self._selected_chart_uids()" in method
    assert "remove_tag_from_charts_by_uid" in method
    assert "load_chart(" not in method
    assert "update_chart(" not in method
    assert "_calculate_dominant_sign_weights" not in method


def test_tag_database_writers_only_update_tags_column():
    for function_name in (
        "add_tag_to_charts_by_uid",
        "remove_tag_from_charts_by_uid",
    ):
        start = DB_SOURCE.index(f"def {function_name}")
        end = DB_SOURCE.index("\ndef ", start + 5)
        method = DB_SOURCE[start:end]
        assert "UPDATE charts SET tags = ? WHERE chart_uid = ?" in method
        assert "_persist_chart_derived_cache" not in method
        assert "update_chart(" not in method


def test_remaining_batch_nonastral_handlers_use_general_uid_patch():
    handler_pairs = (
        ("_open_batch_familiarity_calculator", "_open_chart_familiarity_calculator"),
        ("_on_batch_sentiment_metric_assign", "_on_batch_metric_field_lucygoosey"),
        ("_on_batch_alignment_apply", "_batch_metric_widget_for_key"),
        ("_on_batch_source_selected", "_on_batch_gender_selected"),
        ("_on_batch_gender_selected", "_on_batch_birthtime_unknown_toggled"),
    )
    for method_name, next_name in handler_pairs:
        method = _method_source(method_name, next_name)
        assert "_apply_batch_nonastral_patch" in method
        assert "_calculate_dominant_sign_weights" not in method
        assert "update_chart(" not in method


def test_batch_mortality_uses_coupled_uid_writer():
    method = _method_source(
        "_on_batch_deceased_toggled", "_on_batch_mortality_state_changed"
    )
    assert "update_charts_mortality_by_uid(chart_uids, checked)" in method
    assert "cached_chart.deathtime_unknown = True" in method
    assert 'getattr(cached_chart, "death_hour", None) is None' in method
    assert 'getattr(cached_chart, "death_minute", None) is None' in method
    assert "update_chart(" not in method


def test_birthtime_batch_handler_retains_astro_recalculation_path():
    method = _method_source(
        "_on_batch_birthtime_unknown_toggled",
        "_on_batch_birthtime_unknown_state_changed",
    )
    assert "update_chart(" in method
    assert "_calculate_dominant_sign_weights" in method
    assert 'changed_fields={"birth_data"}' in method


def test_batch_from_whence_uses_general_nonastral_patch():
    source = Path("ephemeraldaddy/gui/dbv_batch_bio.py").read_text()
    method = source[source.index("def apply_batch_from_whence"):]
    assert "owner._selected_chart_uids()" in method
    assert "owner._apply_batch_nonastral_patch" in method
    assert "load_chart(" not in method
    assert "update_chart(" not in method
