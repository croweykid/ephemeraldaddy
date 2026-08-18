from ephemeraldaddy.gui.features.chart_editor.session import ChartEditSession


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
