from __future__ import annotations

from pathlib import Path

from ephemeraldaddy.core import performance_metrics


def test_metrics_are_only_exported_while_enabled(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "performance_metrics_log.txt"
    monkeypatch.setattr(performance_metrics, "PERFORMANCE_METRICS_LOG_PATH", destination)
    performance_metrics.configure_performance_metrics_logging(False)

    performance_metrics.record_performance_metric("disabled.operation", 12.5)
    assert not destination.exists()

    performance_metrics.configure_performance_metrics_logging(True)
    performance_metrics.record_performance_metric(
        "chart_editor.load_to_visible",
        23.4567,
        chart_uid="TEST-UID",
    )
    performance_metrics.configure_performance_metrics_logging(False)

    content = destination.read_text(encoding="utf-8")
    assert "performance_metrics_logging\t0.000 ms" in content
    assert "chart_editor.load_to_visible\t23.457 ms" in content
    assert '"chart_uid":"TEST-UID"' in content


def test_measure_performance_records_failed_attempt(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "performance_metrics_log.txt"
    monkeypatch.setattr(performance_metrics, "PERFORMANCE_METRICS_LOG_PATH", destination)
    performance_metrics.configure_performance_metrics_logging(False)
    performance_metrics.configure_performance_metrics_logging(True)

    try:
        with performance_metrics.measure_performance("operation.failed"):
            raise RuntimeError("expected")
    except RuntimeError:
        pass
    finally:
        performance_metrics.configure_performance_metrics_logging(False)

    assert 'operation.failed' in destination.read_text(encoding="utf-8")
    assert '"status":"error"' in destination.read_text(encoding="utf-8")


def test_developer_tools_exposes_requested_performance_setting_and_tooltip() -> None:
    source = Path("ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")
    assert 'SETTINGS_KEY_PERFORMANCE_METRICS_LOGGING = "dev_tools/performance_metrics_logging"' in source
    assert "PERFORMANCE_METRICS_LOGGING_DEFAULT = False" in source
    assert "def load_performance_metrics_logging_enabled" in source
    assert 'QCheckBox("Enable Performance Metrics Logging")' in source
    assert (
        "When enabled, 'performance metrics log' file will appear locally and in "
        in source
    )
    assert ".app/.ephemeraldaddy/ and track app performance for debugging." in source
