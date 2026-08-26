"""Application diagnostics with quiet and terminal-visible reporting modes."""
from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class ErrorReportingMode(str, Enum):
    QUIET = "quiet"
    DEBUG = "debug"


DEFAULT_ERROR_REPORTING_MODE = ErrorReportingMode.QUIET
DIAGNOSTICS_LOG_PATH = Path.home() / ".ephemeraldaddy" / "diagnostics" / "app.log"

_FORMAT = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
_file_handler: RotatingFileHandler | None = None
_terminal_handler: logging.StreamHandler | None = None
_mode = DEFAULT_ERROR_REPORTING_MODE


def normalize_error_reporting_mode(value: object) -> ErrorReportingMode:
    if isinstance(value, ErrorReportingMode):
        return value
    normalized = str(value or "").strip().lower()
    if normalized == ErrorReportingMode.DEBUG.value:
        return ErrorReportingMode.DEBUG
    return ErrorReportingMode.QUIET


def configure_error_reporting(
    mode: ErrorReportingMode | str,
    *,
    log_path: Path | None = None,
) -> ErrorReportingMode:
    """Configure durable diagnostics and optional terminal traceback output."""
    global _file_handler, _terminal_handler, _mode
    _mode = normalize_error_reporting_mode(mode)
    app_logger = logging.getLogger("ephemeraldaddy")
    app_logger.setLevel(logging.DEBUG if _mode is ErrorReportingMode.DEBUG else logging.INFO)
    environment_debug_enabled = any(
        str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}
        for name in ("EPHEMERALDADDY_DEBUG", "EPHEMERALDADDY_DEBUG_STARTUP")
    )
    app_logger.propagate = _mode is ErrorReportingMode.QUIET and environment_debug_enabled

    if _file_handler is None:
        destination = Path(log_path or DIAGNOSTICS_LOG_PATH).expanduser()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                destination,
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        except OSError:
            logging.getLogger(__name__).exception(
                "Could not initialize application diagnostics file at %s", destination
            )
        else:
            handler.setLevel(logging.WARNING)
            handler.setFormatter(_FORMAT)
            app_logger.addHandler(handler)
            _file_handler = handler

    if _mode is ErrorReportingMode.DEBUG and _terminal_handler is None:
        terminal = logging.StreamHandler(sys.stderr)
        terminal.setLevel(logging.DEBUG)
        terminal.setFormatter(_FORMAT)
        app_logger.addHandler(terminal)
        _terminal_handler = terminal
    elif _mode is ErrorReportingMode.QUIET and _terminal_handler is not None:
        app_logger.removeHandler(_terminal_handler)
        _terminal_handler.close()
        _terminal_handler = None
    return _mode


def error_reporting_mode() -> ErrorReportingMode:
    return _mode


def report_recoverable_error(
    logger: logging.Logger,
    event: str,
    *,
    exc: BaseException | None = None,
    **context: Any,
) -> None:
    """Record a recoverable integrity error, adding tracebacks only in Debug mode."""
    details = " ".join(
        f"{key}={value!r}" for key, value in sorted(context.items()) if value is not None
    )
    message = f"event={event}" + (f" {details}" if details else "")
    logger.error(
        message,
        exc_info=(type(exc), exc, exc.__traceback__)
        if exc is not None and _mode is ErrorReportingMode.DEBUG
        else None,
    )
