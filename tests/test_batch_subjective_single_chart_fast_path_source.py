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
    fast_path_end = method.index("        try:\n            for chart_id in chart_ids:")
    fast_path = method[method.index("if selected_count == 1:"):fast_path_end]
    assert "get_chart_uid(chart_id)" in fast_path
    assert "update_chart_subjective_list_by_uid" in fast_path
    assert "_calculate_dominant_sign_weights" not in fast_path
    assert "load_chart(" not in fast_path


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
