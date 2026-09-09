"""Persistence infrastructure for Personal Timeline generated transit windows.

This module owns cache workers and application-shutdown coordination. It does
not mutate PersonalTimelineWindowWidget or install callbacks at import time.
"""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from PySide6.QtCore import QCoreApplication, QObject, QThread, Qt, Signal, Slot

from ephemeraldaddy.gui.features.transits import personal_timeline_core as core
from ephemeraldaddy.gui.features.transits.cache import (
    PersonalTimelineDiskCache,
    personal_timeline_fingerprint,
)


PERSONAL_TIMELINE_CACHE_ALGORITHM_VERSION = 1

# Cache jobs intentionally outlive an individual Personal Timeline window. They
# are process-owned instead: the application waits for every in-flight job from
# aboutToQuit before Qt teardown can destroy a running QThread.
_ACTIVE_CACHE_JOBS: dict[int, tuple[QThread, QObject]] = {}
_CACHE_JOBS_LOCK = threading.RLock()
_SHUTDOWN_HOOK_INSTALLED = False


@dataclass(frozen=True, slots=True)
class CacheReadResult:
    hit: bool
    windows: tuple[Any, ...] = ()


class _CacheReadWorker(QObject):
    finished = Signal(object)

    def __init__(
        self,
        cache: PersonalTimelineDiskCache,
        chart_uid: str,
        fingerprint: str,
        timeline_tzinfo: datetime.tzinfo,
    ) -> None:
        super().__init__()
        self.cache = cache
        self.chart_uid = str(chart_uid)
        self.fingerprint = str(fingerprint)
        self.timeline_tzinfo = timeline_tzinfo

    @Slot()
    def run(self) -> None:
        try:
            payloads = self.cache.get(self.chart_uid, self.fingerprint)
            if payloads is None:
                result = CacheReadResult(hit=False)
            else:
                windows = tuple(
                    _cached_window(
                        payload,
                        self.chart_uid,
                        self.timeline_tzinfo,
                    )
                    for payload in payloads
                )
                result = CacheReadResult(hit=True, windows=windows)
        except Exception:
            # A malformed/stale cache is disposable. Invalidate it in this
            # worker rather than touching disk again on the GUI thread.
            try:
                self.cache.invalidate(self.chart_uid)
            except Exception:
                pass
            result = CacheReadResult(hit=False)
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


def _generation_config() -> dict[str, object]:
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


def _restore_cached_datetime(
    raw_value: object,
    timeline_tzinfo: datetime.tzinfo,
) -> datetime.datetime:
    """Restore one cached endpoint using the chart's timezone rule set.

    ISO strings preserve the endpoint's UTC offset but not an IANA timezone
    identity. ``fromisoformat`` therefore yields a fixed-offset timezone. Convert
    that instant back into the chart's original tzinfo so DST-aware arithmetic,
    midpoint calculations, and duration semantics match freshly generated
    Personal Timeline windows.
    """
    restored = datetime.datetime.fromisoformat(str(raw_value))
    if restored.tzinfo is None:
        raise ValueError("Cached Personal Timeline bounds must include an offset.")
    return restored.astimezone(timeline_tzinfo)


def _cached_window(
    payload: dict[str, object],
    chart_uid: str,
    timeline_tzinfo: datetime.tzinfo,
) -> Any:
    transit_payload = payload.get("transit")
    if not isinstance(transit_payload, dict):
        raise ValueError("Cached Personal Timeline transit payload is malformed.")

    cached_uid = str(payload.get("chart_uid") or "").strip().upper()
    expected_uid = str(chart_uid or "").strip().upper()
    if cached_uid != expected_uid:
        raise ValueError("Cached Personal Timeline window belongs to another chart.")

    start = _restore_cached_datetime(payload["start"], timeline_tzinfo)
    end = _restore_cached_datetime(payload["end"], timeline_tzinfo)
    if end < start:
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


def _ensure_shutdown_hook() -> None:
    """Install one process-level wait hook before any cache QThread starts."""
    global _SHUTDOWN_HOOK_INSTALLED
    if _SHUTDOWN_HOOK_INSTALLED:
        return
    app = QCoreApplication.instance()
    if app is None:
        return
    app.aboutToQuit.connect(
        shutdown_personal_timeline_cache_jobs,
        Qt.DirectConnection,
    )
    _SHUTDOWN_HOOK_INSTALLED = True


def shutdown_personal_timeline_cache_jobs() -> None:
    """Wait for every in-flight cache worker before Qt application teardown.

    Cache reads/writes are deliberately allowed to finish rather than being
    terminated mid-file. This guarantees that interpreter/Qt teardown cannot
    destroy a still-running QThread and that an atomic cache write either
    completes or remains untouched.
    """
    current_thread = QThread.currentThread()
    while True:
        with _CACHE_JOBS_LOCK:
            jobs = list(_ACTIVE_CACHE_JOBS.values())
        running = [
            thread
            for thread, _worker in jobs
            if thread is not current_thread and thread.isRunning()
        ]
        if not running:
            break
        for thread in running:
            thread.wait()

    with _CACHE_JOBS_LOCK:
        stale_ids = [
            job_id
            for job_id, (thread, _worker) in _ACTIVE_CACHE_JOBS.items()
            if not thread.isRunning()
        ]
        for job_id in stale_ids:
            _ACTIVE_CACHE_JOBS.pop(job_id, None)


def _start_background_worker(
    worker: QObject,
    *,
    receiver: Callable[..., None] | None = None,
) -> QThread:
    """Run one cache worker in a process-owned QThread until completion."""
    _ensure_shutdown_hook()
    app = QCoreApplication.instance()
    thread = QThread(app) if app is not None else QThread()
    job_id = id(thread)
    with _CACHE_JOBS_LOCK:
        _ACTIVE_CACHE_JOBS[job_id] = (thread, worker)

    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    finished_signal = getattr(worker, "finished")
    if receiver is not None:
        # Explicit queued delivery keeps all widget mutations in the GUI thread.
        finished_signal.connect(receiver, Qt.QueuedConnection)

    # Cache workers own no GUI state. Quit directly from the worker thread so
    # thread completion does not depend on the GUI event loop being free.
    finished_signal.connect(worker.deleteLater, Qt.DirectConnection)
    finished_signal.connect(thread.quit, Qt.DirectConnection)

    def _release() -> None:
        with _CACHE_JOBS_LOCK:
            _ACTIVE_CACHE_JOBS.pop(job_id, None)

    thread.finished.connect(_release, Qt.DirectConnection)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


class PersonalTimelinePersistenceController:
    """Explicit cache owner composed by the public Personal Timeline window."""

    def __init__(
        self,
        chart_uid: str,
        chart: Any,
        *,
        cache: PersonalTimelineDiskCache | None = None,
    ) -> None:
        self.chart_uid = str(chart_uid or "").strip().upper()
        self.chart = chart
        self.cache = cache or PersonalTimelineDiskCache()

        birth_datetime = getattr(chart, "dt", None)
        self.timeline_tzinfo: datetime.tzinfo | None = (
            birth_datetime.tzinfo
            if isinstance(birth_datetime, datetime.datetime)
            and birth_datetime.tzinfo is not None
            else None
        )

        self.fingerprint: str | None
        try:
            self.fingerprint = personal_timeline_fingerprint(
                self.chart_uid,
                self.chart,
                _generation_config(),
            )
        except Exception:
            self.fingerprint = None

    @property
    def available(self) -> bool:
        return bool(self.chart_uid and self.fingerprint and self.timeline_tzinfo)

    def start_read(self, receiver: Callable[[object], None]) -> bool:
        if (
            not self.available
            or self.fingerprint is None
            or self.timeline_tzinfo is None
        ):
            return False
        worker = _CacheReadWorker(
            self.cache,
            self.chart_uid,
            self.fingerprint,
            self.timeline_tzinfo,
        )
        _start_background_worker(worker, receiver=receiver)
        return True

    def start_write(self, windows: Iterable[Any]) -> bool:
        if not self.available or self.fingerprint is None:
            return False
        worker = _CacheWriteWorker(
            self.cache,
            self.chart_uid,
            self.fingerprint,
            tuple(windows),
        )
        _start_background_worker(worker)
        return True
