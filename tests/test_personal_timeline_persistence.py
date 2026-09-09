from __future__ import annotations

import threading
import time

from PySide6.QtCore import QCoreApplication

from ephemeraldaddy.gui.features.transits import personal_timeline
from ephemeraldaddy.gui.features.transits import personal_timeline_core
from ephemeraldaddy.gui.features.transits import personal_timeline_persistence as persistence


_QT_APP = QCoreApplication.instance() or QCoreApplication([])


def test_public_timeline_uses_explicit_subclass_without_core_mutation() -> None:
    assert personal_timeline.PersonalTimelineWindowWidget is not personal_timeline_core.PersonalTimelineWindowWidget
    assert issubclass(
        personal_timeline.PersonalTimelineWindowWidget,
        personal_timeline_core.PersonalTimelineWindowWidget,
    )
    assert not hasattr(
        personal_timeline_core.PersonalTimelineWindowWidget,
        "_ephemeraldaddy_persistent_cache_installed",
    )
    assert not hasattr(
        personal_timeline_core.PersonalTimelineWindowWidget,
        "_on_personal_timeline_cache_read_finished",
    )


def test_cache_read_runs_get_off_calling_thread() -> None:
    caller_ident = threading.get_ident()
    io_thread_idents: list[int] = []
    results: list[object] = []

    class _Cache:
        def get(self, chart_uid: str, fingerprint: str):
            assert chart_uid == "ABCDEF1234567890"
            assert fingerprint == "fingerprint"
            io_thread_idents.append(threading.get_ident())
            return None

        def invalidate(self, chart_uid: str) -> None:
            raise AssertionError(f"unexpected invalidation for {chart_uid}")

    worker = persistence._CacheReadWorker(
        _Cache(),  # type: ignore[arg-type]
        "ABCDEF1234567890",
        "fingerprint",
    )
    worker.finished.connect(results.append)

    thread = persistence._start_background_worker(worker)

    assert thread.wait(5000)
    assert io_thread_idents
    assert io_thread_idents[0] != caller_ident
    assert results
    result = results[0]
    assert isinstance(result, persistence.CacheReadResult)
    assert result.hit is False


def test_cache_write_runs_put_off_calling_thread() -> None:
    caller_ident = threading.get_ident()
    io_thread_idents: list[int] = []
    written: list[tuple[str, str, tuple[object, ...]]] = []
    windows = (object(), object())

    class _Cache:
        def put(
            self,
            chart_uid: str,
            fingerprint: str,
            payload_windows: tuple[object, ...],
        ) -> None:
            io_thread_idents.append(threading.get_ident())
            written.append((chart_uid, fingerprint, payload_windows))

    worker = persistence._CacheWriteWorker(
        _Cache(),  # type: ignore[arg-type]
        "ABCDEF1234567890",
        "fingerprint",
        windows,
    )

    thread = persistence._start_background_worker(worker)

    assert thread.wait(5000)
    assert io_thread_idents
    assert io_thread_idents[0] != caller_ident
    assert written == [("ABCDEF1234567890", "fingerprint", windows)]


def test_cache_read_corruption_invalidates_in_worker_thread() -> None:
    caller_ident = threading.get_ident()
    invalidation_thread_idents: list[int] = []
    results: list[object] = []

    class _Cache:
        def get(self, chart_uid: str, fingerprint: str):
            return [{"not": "a valid cached window"}]

        def invalidate(self, chart_uid: str) -> None:
            assert chart_uid == "ABCDEF1234567890"
            invalidation_thread_idents.append(threading.get_ident())

    worker = persistence._CacheReadWorker(
        _Cache(),  # type: ignore[arg-type]
        "ABCDEF1234567890",
        "fingerprint",
    )
    worker.finished.connect(results.append)

    thread = persistence._start_background_worker(worker)

    assert thread.wait(5000)
    assert invalidation_thread_idents
    assert invalidation_thread_idents[0] != caller_ident
    assert results
    result = results[0]
    assert isinstance(result, persistence.CacheReadResult)
    assert result.hit is False


def test_shutdown_waits_for_inflight_cache_job() -> None:
    completed = threading.Event()

    class _Cache:
        def put(
            self,
            chart_uid: str,
            fingerprint: str,
            payload_windows: tuple[object, ...],
        ) -> None:
            assert chart_uid == "ABCDEF1234567890"
            assert fingerprint == "fingerprint"
            time.sleep(0.05)
            completed.set()

    worker = persistence._CacheWriteWorker(
        _Cache(),  # type: ignore[arg-type]
        "ABCDEF1234567890",
        "fingerprint",
        (object(),),
    )
    thread = persistence._start_background_worker(worker)

    persistence.shutdown_personal_timeline_cache_jobs()

    assert completed.is_set()
    assert not thread.isRunning()
    assert persistence._SHUTDOWN_HOOK_INSTALLED is True
    with persistence._CACHE_JOBS_LOCK:
        assert id(thread) not in persistence._ACTIVE_CACHE_JOBS
