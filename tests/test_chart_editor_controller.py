import logging

from ephemeraldaddy.gui.features.chart_editor.controller import ChartEditorController


def _controller(*, suppressed: bool, dirty: list[bool], events: list[str]):
    def mark_draft_dirty() -> None:
        dirty[0] = True
        events.append("dirty")

    return ChartEditorController(
        is_change_tracking_suppressed=lambda: suppressed,
        mark_draft_dirty=mark_draft_dirty,
        mark_recalculation_required=lambda: events.append("recalculate"),
        queue_lightweight_autosave=lambda: events.append("queue"),
        is_draft_dirty=lambda: dirty[0],
        current_chart_uid=lambda: "chart-uid-123",
    )


def test_lightweight_metadata_change_marks_dirty_before_queueing_autosave():
    dirty = [False]
    events: list[str] = []

    _controller(
        suppressed=False,
        dirty=dirty,
        events=events,
    ).on_lightweight_metadata_changed()

    assert dirty == [True]
    assert events == ["dirty", "queue"]


def test_programmatic_metadata_change_is_ignored():
    dirty = [False]
    events: list[str] = []

    _controller(
        suppressed=True,
        dirty=dirty,
        events=events,
    ).on_lightweight_metadata_changed()

    assert dirty == [False]
    assert events == []


def test_authoritative_change_is_dirty_and_protected_from_lightweight_save():
    dirty = [False]
    events: list[str] = []

    controller = _controller(suppressed=False, dirty=dirty, events=events)
    controller.on_authoritative_metadata_changed()
    controller.on_lightweight_metadata_changed()

    assert dirty == [True]
    assert events == ["dirty", "recalculate", "dirty", "queue"]


def test_incomplete_autosave_logs_kind_and_chart_uid(caplog):
    controller = _controller(suppressed=False, dirty=[True], events=[])

    with caplog.at_level(
        logging.WARNING,
        logger="ephemeraldaddy.gui.features.chart_editor.controller",
    ):
        controller.report_incomplete_autosave("lightweight metadata")

    assert "lightweight metadata autosave did not complete" in caplog.text
    assert "chart UID chart-uid-123" in caplog.text


def test_successful_autosave_does_not_log_warning(caplog):
    controller = _controller(suppressed=False, dirty=[False], events=[])

    with caplog.at_level(
        logging.WARNING,
        logger="ephemeraldaddy.gui.features.chart_editor.controller",
    ):
        controller.report_incomplete_autosave("metadata")

    assert not caplog.records
