from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "ephemeraldaddy/gui/features/charts/batch_total_chart_export.py"


def _source() -> str:
    return SOURCE_PATH.read_text()


def _run_total_chart_export_flow_source() -> str:
    source = _source()
    start = source.index("def run_total_chart_export_flow(")
    end = source.index("def _export_single(", start)
    return source[start:end]


def test_multi_chart_export_uses_app_default_folder_without_directory_prompt():
    flow_source = _run_total_chart_export_flow_source()

    assert "BATCH_EXPORT_DIRECTORY" in flow_source
    assert "getExistingDirectory" not in flow_source
    assert "directory.mkdir(parents=True, exist_ok=True)" in flow_source


def test_multi_chart_export_shows_progress_before_export_work_begins():
    flow_source = _run_total_chart_export_flow_source()

    progress_show_index = flow_source.index("progress.show()")
    process_events_index = flow_source.index("QApplication.processEvents()")
    load_chart_index = flow_source.index("chart = load_chart(int(chart_id))")

    assert progress_show_index < process_events_index < load_chart_index
    assert "_show_loading_bar_hint(parent, progress)" in flow_source
