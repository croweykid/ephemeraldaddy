"""Opt-in, low-overhead performance timing export for local diagnostics."""

from __future__ import annotations

import datetime as dt
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Iterator, Mapping


PERFORMANCE_METRICS_LOG_FILENAME = "performance_metrics_log.txt"
PERFORMANCE_METRICS_LOG_PATH = (
    Path.home() / ".ephemeraldaddy" / PERFORMANCE_METRICS_LOG_FILENAME
)

_enabled = False
_write_lock = threading.Lock()


def configure_performance_metrics_logging(enabled: bool) -> None:
    """Enable or disable metrics export for the running process."""

    global _enabled
    _enabled = bool(enabled)
    if _enabled:
        record_performance_metric("performance_metrics_logging", 0.0, status="enabled")


def performance_metrics_logging_enabled() -> bool:
    return _enabled


def resolve_performance_metrics_log_path() -> Path:
    """Return the stable per-user destination used by source and .app builds."""

    return PERFORMANCE_METRICS_LOG_PATH


def record_performance_metric(
    operation: str,
    elapsed_ms: float,
    **details: object,
) -> None:
    """Append one tab-separated timing result when metrics export is enabled."""

    if not _enabled:
        return
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
    safe_operation = str(operation).strip().replace("\t", " ").replace("\n", " ")
    details_json = json.dumps(details, sort_keys=True, default=str, separators=(",", ":"))
    line = f"{timestamp}\t{safe_operation}\t{float(elapsed_ms):.3f} ms\t{details_json}\n"
    destination = resolve_performance_metrics_log_path()
    try:
        with _write_lock:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("a", encoding="utf-8") as handle:
                handle.write(line)
    except OSError:
        # Diagnostics must never make an app workflow fail.
        return


@contextmanager
def measure_performance(
    operation: str,
    details: Mapping[str, object] | None = None,
) -> Iterator[None]:
    """Measure a block and export its duration, including failed attempts."""

    if not _enabled:
        yield
        return
    started_at = perf_counter()
    status = "ok"
    try:
        yield
    except BaseException:
        status = "error"
        raise
    finally:
        record_performance_metric(
            operation,
            (perf_counter() - started_at) * 1000.0,
            status=status,
            **dict(details or {}),
        )
