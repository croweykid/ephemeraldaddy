"""Public Personal Timeline window integration.

The calculation/base-widget implementation remains in ``personal_timeline_core``
while this module explicitly owns the user-facing window composition: permanent
cache lifecycle, sortable headers, and the opener used by window chrome. No
``sys.modules`` aliasing or runtime class mutation is used here.
"""

from __future__ import annotations

from typing import Any, Iterable

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QMessageBox, QWidget

from ephemeraldaddy.core.db import load_chart_by_uid
from ephemeraldaddy.gui.features.transits import personal_timeline_core as _core
from ephemeraldaddy.gui.features.transits import personal_timeline_sorting as _sorting
from ephemeraldaddy.gui.features.transits.personal_timeline_persistence import (
    CacheReadResult,
    PersonalTimelinePersistenceController,
)


# Explicit public surface. Generator-internal tests should import
# personal_timeline_core directly rather than depending on module-identity tricks.
TimelineTransitDefinition = _core.TimelineTransitDefinition
PersonalTimelineWindow = _core.PersonalTimelineWindow
PersonalTimelineSelectionError = _core.PersonalTimelineSelectionError
generate_personal_timeline = _core.generate_personal_timeline
DEFAULT_TIMELINE_YEARS = _core.DEFAULT_TIMELINE_YEARS
DEFAULT_SCAN_STEP_DAYS = _core.DEFAULT_SCAN_STEP_DAYS


class PersonalTimelineWindowWidget(_core.PersonalTimelineWindowWidget):
    """Integrated Personal Timeline window with explicit cache/sort ownership."""

    def __init__(
        self,
        chart_uid: str,
        chart: Any,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(chart_uid, chart, parent=parent)

        # Sorting is ordinary instance behavior, not installed onto the base
        # class. Cache lookup may already be in flight, but its GUI callback is
        # queued and therefore cannot render before construction returns.
        self._personal_timeline_sort_column: int | None = None
        self._personal_timeline_sort_order = Qt.AscendingOrder
        header = self.tree.header()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self._on_personal_timeline_header_clicked)

    def _persistence_controller(self) -> PersonalTimelinePersistenceController:
        controller = getattr(self, "_personal_timeline_persistence", None)
        if isinstance(controller, PersonalTimelinePersistenceController):
            return controller
        controller = PersonalTimelinePersistenceController(self.chart_uid, self.chart)
        self._personal_timeline_persistence = controller
        return controller

    def _start_generation(self) -> None:
        """Resolve permanent cache asynchronously before expensive generation."""
        if bool(getattr(self, "_personal_timeline_cache_lookup_pending", False)):
            return

        controller = self._persistence_controller()
        if not controller.available:
            super()._start_generation()
            return

        self._personal_timeline_cache_lookup_pending = True
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Checking permanent per-chart cache…")
        try:
            started = controller.start_read(self._on_personal_timeline_cache_read_finished)
        except Exception:
            started = False
        if not started:
            self._personal_timeline_cache_lookup_pending = False
            super()._start_generation()

    @Slot(object)
    def _on_personal_timeline_cache_read_finished(self, result: object) -> None:
        self._personal_timeline_cache_lookup_pending = False
        if bool(getattr(self, "_personal_timeline_closing", False)):
            return

        if isinstance(result, CacheReadResult) and result.hit:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
            self._all_windows = list(result.windows)
            self.results_button.setEnabled(True)
            self._rerender_filtered()
            self.status_label.setText(
                self.status_label.text() + " Loaded from permanent per-chart cache."
            )
            return

        # Miss or corrupt/stale cache: use the existing generation worker.
        super()._start_generation()

    def _on_finished(self, windows: object) -> None:
        thread = getattr(self, "_thread", None)
        interrupted = bool(
            thread is not None
            and callable(getattr(thread, "isInterruptionRequested", None))
            and thread.isInterruptionRequested()
        )

        super()._on_finished(windows)
        if interrupted or bool(getattr(self, "_personal_timeline_closing", False)):
            return

        # Copying immutable window references is cheap. Serialization and all
        # disk I/O happen inside the persistence controller's worker thread.
        try:
            self._persistence_controller().start_write(tuple(self._all_windows))
        except Exception:
            pass

    def _populate(self, windows: Iterable[_core.PersonalTimelineWindow]) -> None:
        sorted_windows = _sorting._sorted_timeline_windows(_core, self, windows)
        super()._populate(sorted_windows)

    def _on_personal_timeline_header_clicked(self, column: int) -> None:
        _sorting._header_clicked(_core, self, int(column))

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        # A late cache miss must not start a new ephemeris calculation after the
        # user has closed the window. Process-owned cache jobs may finish safely
        # and are drained during application shutdown.
        self._personal_timeline_closing = True
        super().closeEvent(event)


def open_personal_timeline_for_window(
    owner: QWidget,
) -> PersonalTimelineWindowWidget | None:
    """Open the integrated timeline for the authoritative selected Chart UID."""
    try:
        chart_uid = _core._selected_chart_uid_for_owner(owner)
    except PersonalTimelineSelectionError as exc:
        QMessageBox.information(owner, "Personal Timeline", str(exc))
        return None

    try:
        chart = load_chart_by_uid(chart_uid)
    except Exception as exc:
        QMessageBox.warning(
            owner,
            "Personal Timeline",
            f"Could not load Chart UID {chart_uid}: {exc}",
        )
        return None

    timeline = PersonalTimelineWindowWidget(chart_uid, chart, parent=owner)
    open_windows = getattr(owner, "_personal_timeline_windows", None)
    if not isinstance(open_windows, list):
        open_windows = []
        setattr(owner, "_personal_timeline_windows", open_windows)
    open_windows.append(timeline)

    def _release(*_args: object) -> None:
        if timeline in open_windows:
            open_windows.remove(timeline)

    timeline.destroyed.connect(_release)
    timeline.show()
    timeline.raise_()
    timeline.activateWindow()
    return timeline


__all__ = [
    "DEFAULT_SCAN_STEP_DAYS",
    "DEFAULT_TIMELINE_YEARS",
    "PersonalTimelineSelectionError",
    "PersonalTimelineWindow",
    "PersonalTimelineWindowWidget",
    "TimelineTransitDefinition",
    "generate_personal_timeline",
    "open_personal_timeline_for_window",
]
