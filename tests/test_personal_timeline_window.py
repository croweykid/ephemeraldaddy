from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, Callable

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.features.transits import personal_timeline_persistence as persistence
from ephemeraldaddy.gui.features.transits import personal_timeline_sorting as sorting
from ephemeraldaddy.gui.features.transits import personal_timeline_window as timeline


# These are real QWidget integration tests, so establish a QApplication before
# constructing PersonalTimelineWindowWidget. If another test suite has already
# installed a bare QCoreApplication, the QWidget-specific tests are skipped
# rather than attempting to replace Qt's process singleton.
_EXISTING_QT_APP = QCoreApplication.instance()
if _EXISTING_QT_APP is None:
    _QT_APP: QCoreApplication | None = QApplication([])
elif isinstance(_EXISTING_QT_APP, QApplication):
    _QT_APP = _EXISTING_QT_APP
else:
    _QT_APP = None

UTC = datetime.timezone.utc
CHART_UID = "ABC12345DEF67890"


@pytest.fixture
def chart() -> SimpleNamespace:
    return SimpleNamespace(
        name="Timeline Test",
        chart_uid=CHART_UID,
        dt=datetime.datetime(2000, 1, 1, 12, 0, tzinfo=UTC),
        positions={"Sun": 280.0, "Saturn": 17.0},
    )


@pytest.fixture
def fake_persistence(monkeypatch: pytest.MonkeyPatch):
    class FakePersistenceController:
        instances: list["FakePersistenceController"] = []
        available = True
        read_result = True

        def __init__(self, chart_uid: str, chart: Any) -> None:
            self.chart_uid = chart_uid
            self.chart = chart
            self.read_calls = 0
            self.read_receiver: Callable[[object], None] | None = None
            self.write_calls: list[tuple[object, ...]] = []
            type(self).instances.append(self)

        def start_read(self, receiver: Callable[[object], None]) -> bool:
            self.read_calls += 1
            self.read_receiver = receiver
            return bool(type(self).read_result)

        def start_write(self, windows) -> bool:
            self.write_calls.append(tuple(windows))
            return True

    monkeypatch.setattr(
        timeline,
        "PersonalTimelinePersistenceController",
        FakePersistenceController,
    )
    return FakePersistenceController


@pytest.fixture
def fallback_generation_calls(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    calls: list[object] = []

    def _record_generation(self) -> None:
        calls.append(self)

    monkeypatch.setattr(
        timeline._PersonalTimelineWindowBase,
        "_start_generation",
        _record_generation,
    )
    return calls


def _require_qapplication() -> QApplication:
    if not isinstance(_QT_APP, QApplication):
        pytest.skip("QApplication unavailable because a bare QCoreApplication already exists")
    return _QT_APP


def _new_window(chart: SimpleNamespace) -> timeline.PersonalTimelineWindowWidget:
    _require_qapplication()
    return timeline.PersonalTimelineWindowWidget(CHART_UID, chart)


def _close_window(widget: timeline.PersonalTimelineWindowWidget) -> None:
    widget._thread = None
    widget.close()
    widget.deleteLater()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()


def test_database_selection_uid_is_authoritative() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["abc12345def67890"],
        _latest_chart=SimpleNamespace(chart_uid="SHOULDNOTWIN1234"),
    )

    assert timeline._selected_chart_uid_for_owner(owner) == "ABC12345DEF67890"


def test_database_selection_requires_exactly_one_uid() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["AAAAAAAABBBBBBBB", "CCCCCCCCDDDDDDDD"]
    )

    with pytest.raises(timeline.PersonalTimelineSelectionError):
        timeline._selected_chart_uid_for_owner(owner)


def test_chart_view_navigation_uid_is_authoritative() -> None:
    owner = SimpleNamespace(
        _current_chart_uid_for_navigation=lambda: "abc12345def67890",
        _latest_chart=SimpleNamespace(chart_uid="SHOULDNOTWIN1234"),
    )

    assert timeline._selected_chart_uid_for_owner(owner) == CHART_UID


def test_integrated_window_owns_persistence_and_sorting_explicitly() -> None:
    cls = timeline.PersonalTimelineWindowWidget

    # These methods are ordinary class definitions on the explicit window owner.
    # Their presence must not depend on importing an installer in a particular order.
    for method_name in (
        "_start_generation",
        "_on_personal_timeline_cache_read_finished",
        "_on_finished",
        "_populate",
        "_on_personal_timeline_header_clicked",
        "closeEvent",
    ):
        assert method_name in cls.__dict__
        assert cls.__dict__[method_name].__module__ == timeline.__name__

    assert not hasattr(persistence, "install_personal_timeline_persistence")
    assert not hasattr(sorting, "install_personal_timeline_sorting")


def test_integrated_window_starts_cache_lookup_during_construction(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    try:
        controller = fake_persistence.instances[-1]
        assert controller.chart_uid == CHART_UID
        assert controller.read_calls == 1
        assert controller.read_receiver is not None
        assert widget._personal_timeline_cache_lookup_pending is True
        assert fallback_generation_calls == []
    finally:
        _close_window(widget)


def test_cache_hit_renders_without_starting_generation(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    try:
        controller = fake_persistence.instances[-1]
        assert controller.read_receiver is not None
        rendered: list[tuple[object, ...]] = []
        cached_window = object()
        widget._rerender_filtered = lambda: rendered.append(tuple(widget._all_windows))  # type: ignore[method-assign]

        controller.read_receiver(
            persistence.CacheReadResult(hit=True, windows=(cached_window,))
        )

        assert widget._personal_timeline_cache_lookup_pending is False
        assert widget._all_windows == [cached_window]
        assert rendered == [(cached_window,)]
        assert widget.results_button.isEnabled()
        assert fallback_generation_calls == []
        assert "Loaded from permanent per-chart cache." in widget.status_label.text()
    finally:
        _close_window(widget)


def test_cache_miss_starts_generation_exactly_once(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    try:
        controller = fake_persistence.instances[-1]
        assert controller.read_receiver is not None

        controller.read_receiver(persistence.CacheReadResult(hit=False))

        assert widget._personal_timeline_cache_lookup_pending is False
        assert fallback_generation_calls == [widget]
    finally:
        _close_window(widget)


def test_successful_generation_schedules_exactly_one_cache_write(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    try:
        controller = fake_persistence.instances[-1]
        generated_window = object()
        widget._rerender_filtered = lambda: None  # type: ignore[method-assign]

        widget._on_finished([generated_window])

        assert controller.write_calls == [(generated_window,)]
        assert fallback_generation_calls == []
    finally:
        _close_window(widget)


def test_interrupted_or_failed_generation_never_schedules_cache_write(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    try:
        controller = fake_persistence.instances[-1]
        widget._rerender_filtered = lambda: None  # type: ignore[method-assign]
        widget._thread = SimpleNamespace(isInterruptionRequested=lambda: True)  # type: ignore[assignment]

        widget._on_finished([object()])
        widget._on_failed("synthetic generation failure")

        assert controller.write_calls == []
        assert fallback_generation_calls == []
    finally:
        _close_window(widget)


def test_close_during_cache_lookup_blocks_late_generation(
    chart: SimpleNamespace,
    fake_persistence,
    fallback_generation_calls: list[object],
) -> None:
    widget = _new_window(chart)
    controller = fake_persistence.instances[-1]
    assert controller.read_receiver is not None

    widget.close()
    assert widget._personal_timeline_closing is True

    controller.read_receiver(persistence.CacheReadResult(hit=False))

    assert widget._personal_timeline_cache_lookup_pending is False
    assert fallback_generation_calls == []
    widget.deleteLater()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
