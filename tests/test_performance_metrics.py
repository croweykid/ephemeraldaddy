from __future__ import annotations

import ast
from pathlib import Path

from ephemeraldaddy.core import performance_metrics


def _main_window_method_source(method_name: str) -> str:
    source = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Could not find method {method_name!r}")


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


def test_chart_editor_load_records_phase_boundaries() -> None:
    load_source = _main_window_method_source("load_chart_by_uid")

    for operation in (
        "chart_editor.load.confirm_and_prepare",
        "chart_editor.load.record",
        "chart_editor.load.related_choice_snapshot",
        "chart_editor.load.material_facts",
        "chart_editor.load.form_hydration",
        "chart_editor.load.panel_activation",
        "chart_editor.load.visible",
    ):
        assert operation in load_source

    assert 'completer="reminds_me_of"' in load_source
    assert 'completer="alternate_chart"' in load_source
    assert "cache_hit=cached_chart is not None" in load_source


def test_chart_editor_render_queue_records_first_visible_phases() -> None:
    flush_source = _main_window_method_source("_flush_scheduled_chart_render")
    material_facts_source = _main_window_method_source("_load_material_facts_for_chart")

    assert "chart_editor.load.queue_wait" in flush_source
    assert 'f"chart_editor.load.{section}"' in flush_source
    assert 'section in {"summary", "wheel"}' in flush_source
    assert "chart_editor.load.visible" in flush_source
    assert "chart_editor.load.photo_gallery" in material_facts_source
