from __future__ import annotations

from collections.abc import Callable

from ephemeraldaddy.gui.features.windowing import appwide_window_coordinator as windowing


class _TimingRecorder:
    def __init__(self) -> None:
        self.phases: list[tuple[str, dict[str, object]]] = []
        self.completions: list[dict[str, object]] = []

    def phase(self, name: str, **details: object) -> None:
        self.phases.append((name, details))

    def complete(self, **details: object) -> None:
        self.completions.append(details)


class _DatabaseView:
    def __init__(self) -> None:
        self.refreshes: list[dict[str, object]] = []
        self.launch_pulses: list[bool] = []

    def is_database_view_visible(self) -> bool:
        return False

    def has_chart_rows(self) -> bool:
        return True

    def is_launch_foreground_complete(self) -> bool:
        return False

    def apply_launch_window_policy(self, *, use_topmost_pulse: bool) -> None:
        self.launch_pulses.append(use_topmost_pulse)

    def refresh_for_window_open(self, **request: object) -> None:
        self.refreshes.append(request)


def test_coordinator_preserves_uids_until_database_view_boundary() -> None:
    database_view = _DatabaseView()
    timing = _TimingRecorder()
    raised: list[bool] = []
    cleared: list[bool] = []
    deferred: list[Callable[[], None]] = []
    coordinator = windowing.AppwideWindowCoordinator(
        confirm_discard_or_save=lambda: True,
        get_or_create_database_view=lambda: database_view,
        raise_database_view=lambda: raised.append(True),
        get_pending_changed_refreshes=lambda: ({"METRIC-UID"}, {"ROW-UID"}, False),
        clear_pending_changed_refreshes=lambda: cleared.append(True),
        schedule_once=lambda _delay, callback: deferred.append(callback),
    )

    assert coordinator.open_database_view(open_timing=timing) is True
    assert database_view.launch_pulses == [True]
    assert raised == [True]
    assert cleared == [True]
    assert len(deferred) == 1

    deferred[0]()

    assert database_view.refreshes == [
        {
            "refresh_metrics": True,
            "changed_chart_uids": {"METRIC-UID", "ROW-UID"},
            "defer_metrics_refresh": True,
            "refresh_tag_completers": True,
            "progress_callback": None,
        }
    ]
    assert timing.completions == [
        {
            "was_visible": False,
            "refresh_reason": "pending_changes",
        }
    ]
