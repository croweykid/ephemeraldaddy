from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/prediction_norms_snapshot.py"
).read_text(encoding="utf-8")
DB_INFO_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/controllers/db_info.py"
).read_text(encoding="utf-8")
RUNTIME_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/theme_prediction_runtime.py"
).read_text(encoding="utf-8")


def test_database_norm_refresh_reports_completed_work_and_terminal_status():
    assert "progress_callback: Callable[[int, int, str], None]" in SNAPSHOT_SOURCE
    assert 'f"[Prediction Norms] {completed}/{total}: {message}"' in SNAPSHOT_SOURCE
    assert "print(line, flush=True)" in SNAPSHOT_SOURCE
    assert "for chart_index, chart in enumerate(charts, start=1)" in SNAPSHOT_SOURCE
    assert '"Database norms recalculation complete"' in SNAPSHOT_SOURCE


def test_developer_tool_uses_shared_determinate_progress_dialog():
    refresh = DB_INFO_SOURCE.split("def _refresh_prediction_norms", 1)[1].split(
        "def add_prediction_norms_recalculation_tool", 1
    )[0]
    assert "create_app_loading_progress(" in refresh
    assert "progress_callback=update_progress" in refresh
    assert "float(completed) / float(total) * 100.0" in refresh
    assert "update_app_loading_progress(progress, message, percent)" in refresh
    assert "close_app_loading_progress(progress)" in refresh


def test_theme_refresh_wrapper_forwards_progress_callback():
    assert "progress_callback=progress_callback" in RUNTIME_SOURCE
