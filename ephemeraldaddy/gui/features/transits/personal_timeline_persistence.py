"""Persistence adapter for Personal Timeline's generated transit windows."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

from ephemeraldaddy.gui.features.transits.cache import (
    PersonalTimelineDiskCache,
    personal_timeline_fingerprint,
)


PERSONAL_TIMELINE_CACHE_ALGORITHM_VERSION = 1

# Keep Python references to background QThread/worker pairs until each job
# finishes. The threads are intentionally not parented to the timeline window:
# closing a window should not destroy a still-running disk read/write worker.
_ACTIVE_CACHE_JOBS: dict[int, tuple[QThread, QObject]] = {}


@dataclass(frozen=True, slots=True)
class _CacheReadResult:
    hit: bool
    windows: tuple[Any, ...] = ()


class _CacheReadWorker(QObject):
    finished = Signal(object)

    def __init__(
        self,
        core: ModuleType,
        cache: PersonalTimelineDiskCache,
        chart_uid: str,
        fingerprint: str,
    ) -> None:
        super().__init__()
        self.core = core
        self.cache = cache
        self.chart_uid = str(chart_uid)
        self.fingerprint = str(fingerprint)

    @Slot()
    def run(self) -> None:
        try:
            payloads = self.cache.get(self.chart_uid, self.fingerprint)
            if payloads is None:
                result = _CacheReadResult(hit=False)
            else:
                windows = tuple(
                    _cached_window(self.core, payload, self.chart_uid)
                    for payload in payloads
                )
                result = _CacheReadResult(hit=True, windows=windows)
        except Exception:
            # A malformed/stale cache is disposable. Invalidate it in this
            # worker rather than touching disk again on the GUI thread.
            try:
                self.cache.invalidate(self.chart_uid)
            except Exception:
                pass
            result = _CacheReadResult(hit=False)
        self.finished.emit(result)


class _CacheWriteWorker(QObject):
    finished = Signal()

    def __init__(
        self,
        cache: PersonalTimelineDiskCache,
        chart_uid: str,
        fingerprint: str,
        windows: tuple[Any, ...],
    ) -> None:
        super().__init__()
        self.cache = cache
        self.chart_uid = str(chart_uid)
        self.fingerprint = str(fingerprint)
        self.windows = windows

    @Slot()
    def run(self) -> None:
        try:
            # Serialization, file write, flush, fsync, and atomic replace all
            # happen here, never in the GUI thread.
            self.cache.put(self.chart_uid, self.fingerprint, self.windows)
        except Exception:
            # Cache persistence is an optimization; a write failure must not
            # turn a successfully rendered timeline into an application error.
            pass
        self.finished.emit()


def _generation_config(core: ModuleType) -> dict[str, object]:
    """Describe every generation knob whose change must invalidate disk cache."""
    aspects = []
    for aspect in core.COMPOSITE_ASPECT_TYPES:
        aspects.append(
            {
                "name": str(aspect.name),
                "angle_deg": float(aspect.angle_deg),
                "orb_deg": min(
                    float(aspect.orb_deg),
                    float(core.PERSONAL_TRANSIT_MAX_ORB_DEG),
                ),
            }
        )
    return {
        "algorithm_version": PERSONAL_TIMELINE_CACHE_ALGORITHM_VERSION,
        "timeline_years": int(core.DEFAULT_TIMELINE_YEARS),
        "scan_step_days": int(core.DEFAULT_SCAN_STEP_DAYS),
        "boundary_refinement_steps": int(core._BOUNDARY_REFINEMENT_STEPS),
        "ephemeris_min_date": core.EPHEMERIS_MIN_DATE.isoformat(),
        "ephemeris_max_date": core.EPHEMERIS_MAX_DATE.isoformat(),
        "personal_transit_max_orb_deg": float(core.PERSONAL_TRANSIT_MAX_ORB_DEG),
        "transiting_bodies": list(core._timeline_transiting_bodies()),
        "aspects": aspects,
    }


def _cached_window(core: ModuleType, payload: dict[str, object], chart_uid: str) -> Any:
    transit_payload = payload.get("transit")
    if not isinstance(transit_payload, dict):
        raise ValueError("Cached Personal Timeline transit payload is malformed.")

    cached_uid = str(payload.get("chart_uid") or "").strip().upper()
    expected_uid = str(chart_uid or "").strip().upper()
    if cached_uid != expected_uid:
        raise ValueError("Cached Personal Timeline window belongs to another chart.")

    start = datetime.datetime.fromisoformat(str(payload["start"]))
    end = datetime.datetime.fromisoformat(str(payload["end"]))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError("Cached Personal Timeline bounds are invalid.")

    transit = core.TimelineTransitDefinition(
        transiting_body=str(transit_payload["transiting_body"]),
        natal_body=str(transit_payload["natal_body"]),
        natal_longitude=float(transit_payload["natal_longitude"]),
        aspect_name=str(transit_payload["aspect_name"]),
        aspect_angle=float(transit_payload["aspect_angle"]),
        orb_deg=float(transit_payload["orb_deg"]),
    )
    return core.PersonalTimelineWindow(
        chart_uid=expected_uid,
        transit=transit,
        start=start,
        end=end,
        start_truncated=bool(payload.get("start_truncated", False)),
        end_truncated=bool(payload.get("end_truncated", False)),
    )


def _cache_state(widget: Any, core: ModuleType) -> tuple[PersonalTimelineDiskCache, str] | None:
    cache = getattr(widget, "_personal_timeline_disk_cache", None)
    fingerprint = getattr(widget, "_personal_timeline_cache_fingerprint", None)
    if isinstance(cache, PersonalTimelineDiskCache) and isinstance(fingerprint, str):
        return cache, fingerprint

    try:
        cache = PersonalTimelineDiskCache()
        fingerprint = personal_timeline_fingerprint(
            widget.chart_uid,
            widget.chart,
            _generation_config(core),
        )
    except Exception:
        return None

    widget._personal_timeline_disk_cache = cache
    widget._personal_timeline_cache_fingerprint = fingerprint
    return cache, fingerprint


def _start_background_worker(
    worker: QObject,
    *,
    receiver: Callable[..., None] | None = None,
) -> QThread:
    """Run a cache worker in its own QThread and retain it until completion."""
    thread = QThread()
    job_id = id(thread)
    _ACTIVE_CACHE_JOBS[job_id] = (thread, worker)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    finished_signal = getattr(worker, "finished")
    if receiver is not None:
        # Explicit queued delivery keeps all widget mutations in the GUI thread.
        finished_signal.connect(receiver, Qt.QueuedConnection)

    # Cache workers own no GUI state. Request deletion/quit directly from the
    # worker thread so completion never depends on the GUI event loop being free.
    finished_signal.connect(worker.deleteLater, Qt.DirectConnection)
    finished_signal.connect(thread.quit, Qt.DirectConnection)

    def _release() -> None:
        _ACTIVE_CACHE_JOBS.pop(job_id, None)

    thread.finished.connect(_release)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


def install_personal_timeline_persistence(core: ModuleType) -> None:
    """Add transparent permanent-cache behavior without changing generator semantics."""
    widget_type = core.PersonalTimelineWindowWidget
    if bool(getattr(widget_type, "_ephemeraldaddy_persistent_cache_installed", False)):
        return

    original_start_generation = widget_type._start_generation
    original_on_finished = widget_type._on_finished
    original_close_event = widget_type.closeEvent

    def _cache_read_finished(self: Any, result: object) -> None:
        self._personal_timeline_cache_lookup_pending = False
        if bool(getattr(self, "_personal_timeline_closing", False)):
            return

        if isinstance(result, _CacheReadResult) and result.hit:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
            self._all_windows = list(result.windows)
            self.results_button.setEnabled(True)
            self._rerender_filtered()
            self.status_label.setText(
                self.status_label.text() + " Loaded from permanent per-chart cache."
            )
            return

        # Cache miss/corruption: start the existing expensive generator only
        # after the background lookup has completed.
        original_start_generation(self)

    def _start_generation_with_cache(self: Any) -> None:
        if bool(getattr(self, "_personal_timeline_cache_lookup_pending", False)):
            return

        state = _cache_state(self, core)
        if state is None:
            original_start_generation(self)
            return

        cache, fingerprint = state
        self._personal_timeline_cache_lookup_pending = True
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Checking permanent per-chart cache…")
        try:
            worker = _CacheReadWorker(core, cache, self.chart_uid, fingerprint)
            _start_background_worker(
                worker,
                receiver=self._on_personal_timeline_cache_read_finished,
            )
        except Exception:
            self._personal_timeline_cache_lookup_pending = False
            original_start_generation(self)

    def _on_finished_with_cache(self: Any, windows: object) -> None:
        thread = getattr(self, "_thread", None)
        interrupted = bool(
            thread is not None
            and callable(getattr(thread, "isInterruptionRequested", None))
            and thread.isInterruptionRequested()
        )
        original_on_finished(self, windows)
        if interrupted or bool(getattr(self, "_personal_timeline_closing", False)):
            return

        state = _cache_state(self, core)
        if state is None:
            return
        cache, fingerprint = state

        # Copying immutable window references is cheap; all expensive
        # serialization and disk I/O happens in the worker.
        cached_windows = tuple(self._all_windows)
        try:
            worker = _CacheWriteWorker(
                cache,
                self.chart_uid,
                fingerprint,
                cached_windows,
            )
            _start_background_worker(worker)
        except Exception:
            pass

    def _close_with_cache(self: Any, event: object) -> None:
        # Prevent a late cache miss from starting a new ephemeris generation
        # after the user has already closed the window. Background cache I/O
        # may finish independently and is retained by _ACTIVE_CACHE_JOBS.
        self._personal_timeline_closing = True
        original_close_event(self, event)

    widget_type._on_personal_timeline_cache_read_finished = _cache_read_finished
    widget_type._start_generation = _start_generation_with_cache
    widget_type._on_finished = _on_finished_with_cache
    widget_type.closeEvent = _close_with_cache
    widget_type._ephemeraldaddy_persistent_cache_installed = True
