from types import SimpleNamespace

from ephemeraldaddy.gui.features.chart_editor.session import (
    ChartEditSession,
    ChartTimeContext,
)


def test_begin_normalizes_uid_and_copies_authoritative_values():
    source = {"name": "Ada"}
    session = ChartEditSession()

    session.begin(chart_uid=" chart-uid-123 ", authoritative_values=source)
    source["name"] = "Changed elsewhere"

    assert session.active_chart_uid == "CHART-UID-123"
    assert session.authoritative_values == {"name": "Ada"}
    assert session.draft_values == {"name": "Ada"}
    assert not session.is_dirty


def test_authoritative_change_requires_recalculation():
    session = ChartEditSession(authoritative_values={"birth_place": "Paris"})

    session.set_draft_value("birth_place", "London", kind="authoritative")

    assert session.dirty_fields == {"birth_place"}
    assert session.recalculation_required


def test_lightweight_change_does_not_require_recalculation():
    session = ChartEditSession(authoritative_values={"biography": "Old"})

    session.set_draft_value("biography", "New")

    assert session.dirty_fields == {"biography"}
    assert not session.recalculation_required


def test_reverting_value_clears_that_dirty_field():
    session = ChartEditSession(authoritative_values={"name": "Ada"})
    session.set_draft_value("name", "Grace")

    session.set_draft_value("name", "Ada")

    assert not session.is_dirty


def test_reverting_last_authoritative_value_clears_recalculation_requirement():
    session = ChartEditSession(authoritative_values={"birth_place": "Paris"})
    session.set_draft_value("birth_place", "London", kind="authoritative")

    session.set_draft_value("birth_place", "Paris", kind="authoritative")

    assert not session.recalculation_required
    assert not session.authoritative_dirty_fields


def test_reverting_one_authoritative_value_preserves_other_recalculation_reason():
    session = ChartEditSession(
        authoritative_values={"birth_place": "Paris", "birth_date": "1900-01-01"}
    )
    session.set_draft_value("birth_place", "London", kind="authoritative")
    session.set_draft_value("birth_date", "1901-01-01", kind="authoritative")

    session.set_draft_value("birth_place", "Paris", kind="authoritative")

    assert session.recalculation_required
    assert session.authoritative_dirty_fields == {"birth_date"}


def test_legacy_recalculation_bridge_tracks_an_explicit_reason():
    session = ChartEditSession()

    session.require_recalculation(True)
    assert session.recalculation_required
    assert session.authoritative_dirty_fields == {"legacy-unspecified"}

    session.require_recalculation(False)
    assert not session.recalculation_required
    assert not session.authoritative_dirty_fields


def test_identity_update_normalizes_uid_without_resetting_draft():
    session = ChartEditSession(authoritative_values={"name": "Ada"})
    session.set_draft_value("name", "Grace")

    session.set_active_chart_uid(" chart-123 ")

    assert session.active_chart_uid == "CHART-123"
    assert session.draft_values == {"name": "Grace"}


def test_mark_clean_accepts_draft_and_resets_recalculation():
    session = ChartEditSession(authoritative_values={"birth_date": "1900-01-01"})
    session.set_draft_value("birth_date", "1901-01-01", kind="authoritative")

    session.mark_clean()

    assert session.authoritative_values == {"birth_date": "1901-01-01"}
    assert not session.is_dirty
    assert not session.recalculation_required


def test_discard_restores_authoritative_snapshot():
    session = ChartEditSession(authoritative_values={"notes": "Saved"})
    session.set_draft_value("notes", "Draft")

    session.discard()

    assert session.draft_values == {"notes": "Saved"}
    assert not session.is_dirty


def test_new_session_has_no_chart_uid():
    session = ChartEditSession(active_chart_uid="  ")

    assert session.active_chart_uid is None


def test_successful_save_owns_result_and_accumulates_lifecycle_state():
    session = ChartEditSession(authoritative_values={"notes": "Old"})
    session.set_draft_value("notes", "New")

    result = session.record_successful_save(
        changed_fields={"notes"},
        recalculated=False,
        changed_chart_data=True,
        prediction_flush_required=True,
    )

    assert result.changed_fields == frozenset({"notes"})
    assert not result.recalculated
    assert session.last_save_result is result
    assert session.saved_changes_since_load
    assert session.prediction_flush_pending
    assert not session.is_dirty
    assert session.authoritative_values == {"notes": "New"}


def test_later_lightweight_save_does_not_clear_accumulated_save_impact():
    session = ChartEditSession()
    session.record_successful_save(
        changed_fields=None,
        recalculated=True,
        changed_chart_data=True,
        prediction_flush_required=True,
    )

    session.record_successful_save(
        changed_fields=set(),
        recalculated=False,
        changed_chart_data=False,
        prediction_flush_required=False,
    )

    assert session.last_save_result is not None
    assert session.last_save_result.changed_fields == frozenset()
    assert session.saved_changes_since_load
    assert session.prediction_flush_pending


def test_begin_resets_save_lifecycle_and_prediction_flush_can_complete():
    session = ChartEditSession()
    session.record_successful_save(
        changed_fields={"birth_data"},
        recalculated=True,
        changed_chart_data=True,
        prediction_flush_required=True,
    )
    session.mark_prediction_flush_complete()

    assert not session.prediction_flush_pending

    session.begin(chart_uid="next-chart")

    assert session.last_save_result is None
    assert not session.saved_changes_since_load
    assert not session.prediction_flush_pending


def test_time_context_distinguishes_authoritative_and_provisional_time():
    authoritative = ChartTimeContext(
        birth_time_unknown=False,
        chart_uses_houses=True,
    )
    rectified = ChartTimeContext(
        birth_time_unknown=True,
        rectified_time_enabled=True,
        chart_uses_houses=True,
    )
    unknown = ChartTimeContext(
        birth_time_unknown=True,
        chart_uses_houses=False,
    )

    assert authoritative.has_authoritative_birth_time
    assert not authoritative.uses_provisional_time
    assert not rectified.has_authoritative_birth_time
    assert rectified.uses_provisional_time
    assert rectified.chart_uses_houses
    assert not unknown.has_authoritative_birth_time
    assert not unknown.uses_provisional_time
    assert not unknown.chart_uses_houses

    ranged_known_time = ChartTimeContext(
        birth_time_unknown=False,
        rectification_range_enabled=True,
        chart_uses_houses=True,
    )
    assert ranged_known_time.uses_provisional_time
    assert not ranged_known_time.has_authoritative_birth_time


def test_begin_and_save_flow_replace_time_context_explicitly():
    loaded_context = ChartTimeContext(
        birth_time_unknown=True,
        rectification_range_enabled=True,
        chart_uses_houses=True,
    )
    saved_context = ChartTimeContext(
        birth_time_unknown=False,
        chart_uses_houses=True,
    )
    session = ChartEditSession()

    session.begin(chart_uid="chart-1", time_context=loaded_context)
    session.set_time_context(saved_context)

    assert session.time_context is saved_context


def test_time_context_from_chart_preserves_unknown_rectified_house_semantics():
    chart = SimpleNamespace(
        birthtime_unknown=True,
        retcon_time_used=True,
        rectification_range_used=False,
        is_placeholder=False,
    )

    context = ChartTimeContext.from_chart(chart)

    assert context.birth_time_unknown
    assert context.rectified_time_enabled
    assert not context.rectification_range_enabled
    assert context.chart_uses_houses
    assert context.uses_provisional_time
    assert not context.has_authoritative_birth_time
