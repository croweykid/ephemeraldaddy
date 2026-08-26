"""Explicit coordination for appwide top-level window routing.

This module deliberately depends on a small Database View protocol rather than either
top-level Qt window implementation.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Protocol

from ephemeraldaddy.gui.features.database_view.performance import DatabaseViewOpenTiming

logger = logging.getLogger(__name__)


def _schedule_once(delay_ms: int, callback: Callable[[], None]) -> None:
    """Schedule UI work without making Qt a module-import dependency."""
    from PySide6.QtCore import QTimer

    QTimer.singleShot(delay_ms, callback)


def _process_application_events() -> None:
    """Pump the active Qt application when startup hydration needs a repaint."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        app.processEvents()


class DatabaseViewPort(Protocol):
    """Operations needed to route to and hydrate Database View."""

    def is_database_view_visible(self) -> bool: ...
    def has_chart_rows(self) -> bool: ...
    def is_launch_foreground_complete(self) -> bool: ...
    def apply_launch_window_policy(self, *, use_topmost_pulse: bool) -> None: ...
    def refresh_for_window_open(
        self,
        *,
        refresh_metrics: bool,
        changed_chart_uids: set[str] | None = None,
        defer_metrics_refresh: bool = False,
        refresh_tag_completers: bool = False,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> None: ...


class AppwideWindowCoordinator:
    """Own top-level routing from Chart Editor to the default Database View."""

    def __init__(
        self,
        confirm_discard_or_save: Callable[[], bool],
        get_or_create_database_view: Callable[[], DatabaseViewPort],
        raise_database_view: Callable[[], None],
        get_pending_changed_refreshes: Callable[[], tuple[set[str], set[str], bool]],
        clear_pending_changed_refreshes: Callable[[], None],
        schedule_once: Callable[[int, Callable[[], None]], None] = _schedule_once,
        process_application_events: Callable[[], None] = _process_application_events,
    ) -> None:
        self._confirm_discard_or_save = confirm_discard_or_save
        self._get_or_create_database_view = get_or_create_database_view
        self._raise_database_view = raise_database_view
        self._get_pending_changed_refreshes = get_pending_changed_refreshes
        self._clear_pending_changed_refreshes = clear_pending_changed_refreshes
        self._schedule_once = schedule_once
        self._process_application_events = process_application_events

    def confirm_database_view_open(
        self,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        if progress_callback:
            progress_callback("Checking unsaved changes…", 68)
        if not self._confirm_discard_or_save():
            logger.debug("Cancelled Database View open due to unsaved-change prompt.")
            return False
        return True

    def open_database_view(
        self,
        *,
        open_timing: DatabaseViewOpenTiming,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        if progress_callback:
            progress_callback("Preparing Database View shell…", 72)
        database_view = self._get_or_create_database_view()
        open_timing.phase("dialog_shell")
        pending_metric_uids, pending_lightweight_uids, force_full_refresh = (
            self._get_pending_changed_refreshes()
        )
        pending_uids = set(pending_metric_uids) | set(pending_lightweight_uids)
        pending_refresh_metrics = bool(pending_metric_uids)
        was_visible = database_view.is_database_view_visible()
        logger.debug(
            "Opening Database View (visible=%s pending_changed_uids=%s pending_metric_uids=%s).",
            was_visible,
            len(pending_uids),
            len(pending_metric_uids),
        )

        refresh_after_show: Callable[[], None] | None = None
        refresh_reason = "none"
        if force_full_refresh:
            refresh_reason = "deleted_chart"
            def refresh_after_show() -> None:
                database_view.refresh_for_window_open(
                    refresh_metrics=True,
                    defer_metrics_refresh=progress_callback is None,
                    refresh_tag_completers=True,
                    progress_callback=progress_callback,
                )
        elif pending_uids:
            refresh_reason = "pending_changes"
            def refresh_after_show() -> None:
                database_view.refresh_for_window_open(
                    refresh_metrics=pending_refresh_metrics,
                    changed_chart_uids=pending_uids,
                    defer_metrics_refresh=pending_refresh_metrics and progress_callback is None,
                    refresh_tag_completers=pending_refresh_metrics,
                    progress_callback=progress_callback,
                )
        elif not database_view.has_chart_rows():
            refresh_reason = "initial_population"
            # First-open row/metric population is the slowest Database View step.
            # During application startup, keep it inside the loading-bar
            # interval so Database Analytics does not begin after 100%.
            def refresh_after_show() -> None:
                database_view.refresh_for_window_open(
                    refresh_metrics=True,
                    defer_metrics_refresh=progress_callback is None,
                    progress_callback=progress_callback,
                )
        if progress_callback:
            progress_callback("Showing Database View shell…", 88)
        self._clear_pending_changed_refreshes()
        use_launch_pulse = not database_view.is_launch_foreground_complete()
        if was_visible:
            database_view.apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            self._raise_database_view()
        else:
            database_view.apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            self._raise_database_view()
        open_timing.phase(
            "show_shell",
            was_visible=was_visible,
            refresh_reason=refresh_reason,
        )
        if refresh_after_show is not None:
            if progress_callback:
                # During application startup, keep the loading widget alive until
                # the first Database View population really finishes.  Previously
                # this refresh was delayed until after the shell appeared, which
                # closed the startup progress bar while the center panel was still
                # blank and busy.  Showing the shell, pumping pending paint events,
                # and then doing the initial refresh under the same progress
                # callback gives users an accurate lifeline through the slowest
                # first-open step.
                progress_callback("Loading Database rows…", 89)
                self._process_application_events()
                try:
                    refresh_after_show()
                    self._process_application_events()
                except BaseException:
                    open_timing.complete(
                        was_visible=was_visible,
                        refresh_reason=refresh_reason,
                        status="error",
                    )
                    raise
                open_timing.phase("refresh", refresh_reason=refresh_reason)
                open_timing.complete(
                    was_visible=was_visible,
                    refresh_reason=refresh_reason,
                )
                progress_callback("Database View is ready.", 99)
            else:
                # Non-startup transitions still defer the expensive refresh until
                # after the dialog has painted, preserving interactive snappiness.
                def refresh_and_record() -> None:
                    try:
                        refresh_after_show()
                    except BaseException:
                        open_timing.complete(
                            was_visible=was_visible,
                            refresh_reason=refresh_reason,
                            status="error",
                        )
                        raise
                    open_timing.phase("refresh", refresh_reason=refresh_reason)
                    open_timing.complete(
                        was_visible=was_visible,
                        refresh_reason=refresh_reason,
                    )

                self._schedule_once(0, refresh_and_record)
        else:
            open_timing.complete(
                was_visible=was_visible,
                refresh_reason=refresh_reason,
            )

        logger.debug(
            "Database View dialog foreground request complete (topmost_pulse=%s).",
            use_launch_pulse,
        )
        return True
