from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "ephemeraldaddy/gui/features/charts/batch_total_chart_export.py"


def _source() -> str:
    return SOURCE_PATH.read_text()


def _run_total_chart_export_flow_source() -> str:
    source = _source()
    start = source.index("def run_total_chart_export_flow(")
    end = source.index("def _choose_batch_export_directory(", start)
    return source[start:end]


def _choose_batch_export_directory_source() -> str:
    source = _source()
    start = source.index("def _choose_batch_export_directory(")
    end = source.index("def _export_single(", start)
    return source[start:end]


def test_multi_chart_export_prompts_for_directory_without_default_export_folder():
    flow_source = _run_total_chart_export_flow_source()

    assert "BATCH_EXPORT_DIRECTORY" not in _source()
    assert "_choose_batch_export_directory(parent)" in flow_source
    assert "QFileDialog.getExistingDirectory" not in flow_source
    assert "QFileDialog.DontUseNativeDialog" in _source()
    assert "directory.mkdir(parents=True, exist_ok=True)" not in flow_source


def test_multi_chart_export_shows_progress_before_export_work_begins():
    flow_source = _run_total_chart_export_flow_source()

    directory_prompt_index = flow_source.index("_choose_batch_export_directory(parent)")
    progress_show_index = flow_source.index("progress.show()")
    helper_source = _choose_batch_export_directory_source()
    process_events_index = helper_source.index("QApplication.processEvents()")
    load_chart_index = flow_source.index("chart = load_chart(int(chart_id))")

    assert directory_prompt_index < progress_show_index < load_chart_index
    assert process_events_index < helper_source.index("dialog.exec()")
    assert "_show_loading_bar_hint(parent, progress)" in flow_source
    assert "LoadingMessageRotator" in _source()
    assert "progress.set_message(loading_messages.next())" in flow_source


def test_multi_chart_confirmation_accept_role_continues_to_directory_prompt():
    source = _source()

    assert "box.buttonRole(box.clickedButton()) == QMessageBox.AcceptRole" in source
    assert "box.clickedButton() is ok" not in source
    assert "setInformativeText" not in source


def test_batch_export_directory_dialog_sets_non_native_option_first():
    helper_source = _choose_batch_export_directory_source()

    constructor_index = helper_source.index('dialog = QFileDialog(parent, "Export Total Charts")')
    non_native_index = helper_source.index("dialog.setOption(QFileDialog.DontUseNativeDialog, True)")
    file_mode_index = helper_source.index("dialog.setFileMode(QFileDialog.Directory)")
    show_dirs_index = helper_source.index("dialog.setOption(QFileDialog.ShowDirsOnly, True)")
    label_index = helper_source.index("dialog.setLabelText")

    assert constructor_index < non_native_index < file_mode_index < show_dirs_index < label_index


def test_background_export_ui_slots_run_on_gui_thread_without_self_waiting():
    source = _source()

    assert "worker.progress.connect(_on_progress, Qt.QueuedConnection)" in source
    assert "worker.failed.connect(_on_failed, Qt.QueuedConnection)" in source
    assert "worker.finished.connect(_on_finished, Qt.QueuedConnection)" in source
    assert "thread.wait()" not in source
    assert "thread.finished.connect(worker.deleteLater)" in source
    assert "thread.finished.connect(thread.deleteLater)" in source
