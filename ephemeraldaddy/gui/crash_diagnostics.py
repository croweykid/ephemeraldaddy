"""Crash diagnostics for native GUI failures.

Segmentation faults usually happen below Python (Qt/PySide, matplotlib's Qt
canvas, font/rendering libraries, or C extensions), so normal exception hooks do
not run.  This module installs always-on breadcrumbs that survive those faults.
"""
from __future__ import annotations

import datetime as _dt
import faulthandler
import logging
import os
import platform
import signal
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import TextIO

logger = logging.getLogger(__name__)

_CRASH_LOG_ENV = "EPHEMERALDADDY_CRASH_LOG"
_PERIODIC_DUMP_ENV = "EPHEMERALDADDY_PERIODIC_TRACEBACK_SECONDS"
_DEFAULT_DIR_NAME = "ephemeraldaddy-crash-reports"
_NATIVE_SIGNALS = (signal.SIGABRT, signal.SIGFPE, signal.SIGILL, signal.SIGSEGV)

_log_file: TextIO | None = None
_previous_excepthook = sys.excepthook
_previous_threading_excepthook = getattr(threading, "excepthook", None)
_installed = False


def _timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _default_log_path() -> Path:
    directory = Path(tempfile.gettempdir()) / _DEFAULT_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"crash-{_timestamp()}-pid{os.getpid()}.log"


def _configured_log_path() -> Path:
    configured = os.environ.get(_CRASH_LOG_ENV)
    if configured:
        path = Path(configured).expanduser()
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        path.mkdir(parents=True, exist_ok=True)
        return path / f"crash-{_timestamp()}-pid{os.getpid()}.log"
    return _default_log_path()


def _write_header(stream: TextIO) -> None:
    stream.write("EphemeralDaddy crash diagnostics\n")
    stream.write(f"started={_dt.datetime.now().isoformat(timespec='seconds')}\n")
    stream.write(f"pid={os.getpid()} executable={sys.executable!r}\n")
    stream.write(f"platform={platform.platform()} python={platform.python_version()}\n")
    stream.write(f"argv={sys.argv!r}\n")
    stream.write("\n")
    stream.flush()


def _exception_hook(exc_type: type[BaseException], exc: BaseException, tb) -> None:
    logger.critical("Unhandled exception reached sys.excepthook", exc_info=(exc_type, exc, tb))
    if _log_file is not None:
        print("\nUnhandled Python exception:", file=_log_file, flush=True)
        traceback.print_exception(exc_type, exc, tb, file=_log_file)
        _log_file.flush()
    _previous_excepthook(exc_type, exc, tb)


def _thread_exception_hook(args: threading.ExceptHookArgs) -> None:
    logger.critical(
        "Unhandled exception in thread %s",
        getattr(args.thread, "name", "<unknown>"),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    if _log_file is not None:
        print(f"\nUnhandled thread exception in {getattr(args.thread, 'name', '<unknown')}:", file=_log_file, flush=True)
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=_log_file)
        _log_file.flush()
    if _previous_threading_excepthook is not None:
        _previous_threading_excepthook(args)


def _qt_message_handler(mode, context, message: str) -> None:
    try:
        from PySide6.QtCore import QtMsgType

        level = {
            QtMsgType.QtDebugMsg: logging.DEBUG,
            QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.ERROR,
            QtMsgType.QtFatalMsg: logging.CRITICAL,
        }.get(mode, logging.ERROR)
    except Exception:
        level = logging.ERROR
    logger.log(
        level,
        "Qt message: %s (%s:%s %s)",
        message,
        getattr(context, "file", None),
        getattr(context, "line", None),
        getattr(context, "function", None),
    )


def install_crash_diagnostics(*, debug_enabled: bool = False) -> Path | None:
    """Install Python, Qt, and native-signal diagnostics for crash reports."""
    global _installed, _log_file
    if _installed:
        return Path(_log_file.name) if _log_file is not None else None
    _installed = True

    try:
        _log_file = open(_configured_log_path(), "a", encoding="utf-8", buffering=1)
        _write_header(_log_file)
    except OSError as exc:
        logger.warning("Could not open crash diagnostics log file: %s", exc)
        _log_file = None

    target = _log_file or sys.stderr
    if target is not None and not faulthandler.is_enabled():
        try:
            faulthandler.enable(file=target, all_threads=True)
        except (RuntimeError, OSError) as exc:
            # faulthandler can fail while installing its native signal stack.
            # Do not let optional crash diagnostics prevent the app from starting.
            try:
                faulthandler.disable()
            except Exception:
                pass
            logger.debug("Faulthandler unavailable for crash diagnostics: %s", exc)
    elif target is None:
        logger.debug("Faulthandler skipped because no diagnostics stream is available.")

    if _log_file is not None:
        register_signal = getattr(faulthandler, "register", None)
        if register_signal is None:
            logger.debug("Faulthandler signal registration is unavailable on this platform.")
        else:
            for native_signal in _NATIVE_SIGNALS:
                try:
                    register_signal(native_signal, file=_log_file, all_threads=True, chain=True)
                except (RuntimeError, ValueError, OSError) as exc:
                    logger.debug("Could not register faulthandler for signal %s: %s", native_signal, exc)

    sys.excepthook = _exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_exception_hook

    try:
        from PySide6.QtCore import qInstallMessageHandler

        qInstallMessageHandler(_qt_message_handler)
    except Exception as exc:
        logger.debug("Qt message diagnostics unavailable: %s", exc)

    dump_seconds = os.environ.get(_PERIODIC_DUMP_ENV)
    if dump_seconds:
        try:
            faulthandler.dump_traceback_later(float(dump_seconds), repeat=True, file=target)
        except (RuntimeError, ValueError) as exc:
            logger.warning("Could not start periodic traceback dumps: %s", exc)

    if debug_enabled and _log_file is not None:
        print(f"Crash diagnostics log: {_log_file.name}", file=sys.stderr, flush=True)
    logger.info("Crash diagnostics installed (log=%s faulthandler=%s).", getattr(_log_file, "name", None), faulthandler.is_enabled())
    return Path(_log_file.name) if _log_file is not None else None


def dump_traceback_now() -> None:
    """Write all Python thread stacks to the diagnostics log on demand."""
    target = _log_file or sys.stderr
    if target is not None:
        faulthandler.dump_traceback(file=target, all_threads=True)
