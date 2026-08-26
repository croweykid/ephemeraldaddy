import logging

from ephemeraldaddy.core import diagnostics


def _reset_handlers() -> None:
    app_logger = logging.getLogger("ephemeraldaddy")
    for handler in (diagnostics._terminal_handler, diagnostics._file_handler):
        if handler is not None:
            app_logger.removeHandler(handler)
            handler.close()
    diagnostics._terminal_handler = None
    diagnostics._file_handler = None
    diagnostics._mode = diagnostics.DEFAULT_ERROR_REPORTING_MODE
    app_logger.propagate = True


def test_quiet_reporting_writes_file_without_terminal(tmp_path, capsys):
    _reset_handlers()
    log_path = tmp_path / "app.log"
    try:
        diagnostics.configure_error_reporting("quiet", log_path=log_path)
        diagnostics.report_recoverable_error(
            logging.getLogger("ephemeraldaddy.test"),
            "cache_rejected",
            chart_uid="TESTUID12345678",
        )
        assert "cache_rejected" in log_path.read_text(encoding="utf-8")
        assert capsys.readouterr().err == ""
    finally:
        _reset_handlers()


def test_debug_reporting_adds_terminal_traceback(tmp_path, capsys):
    _reset_handlers()
    try:
        diagnostics.configure_error_reporting("debug", log_path=tmp_path / "app.log")
        try:
            raise ValueError("broken payload")
        except ValueError as exc:
            diagnostics.report_recoverable_error(
                logging.getLogger("ephemeraldaddy.test"),
                "cache_rejected",
                exc=exc,
                field="derived_positions",
            )
        terminal = capsys.readouterr().err
        assert "event=cache_rejected" in terminal
        assert "ValueError: broken payload" in terminal
    finally:
        _reset_handlers()


def test_normalize_error_reporting_mode_preserves_enum_values():
    assert (
        diagnostics.normalize_error_reporting_mode(diagnostics.ErrorReportingMode.DEBUG)
        is diagnostics.ErrorReportingMode.DEBUG
    )
    assert (
        diagnostics.normalize_error_reporting_mode(diagnostics.ErrorReportingMode.QUIET)
        is diagnostics.ErrorReportingMode.QUIET
    )


def test_quiet_reporting_preserves_environment_debug_propagation(
    tmp_path, monkeypatch
):
    _reset_handlers()
    monkeypatch.setenv("EPHEMERALDADDY_DEBUG_STARTUP", "1")
    try:
        diagnostics.configure_error_reporting("quiet", log_path=tmp_path / "app.log")
        assert logging.getLogger("ephemeraldaddy").propagate is True
    finally:
        _reset_handlers()


def test_quiet_reporting_does_not_propagate_without_environment_debug(
    tmp_path, monkeypatch
):
    _reset_handlers()
    monkeypatch.delenv("EPHEMERALDADDY_DEBUG", raising=False)
    monkeypatch.delenv("EPHEMERALDADDY_DEBUG_STARTUP", raising=False)
    try:
        diagnostics.configure_error_reporting("quiet", log_path=tmp_path / "app.log")
        assert logging.getLogger("ephemeraldaddy").propagate is False
    finally:
        _reset_handlers()
