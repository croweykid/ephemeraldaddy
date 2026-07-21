from pathlib import Path

SOURCE = Path("ephemeraldaddy/gui/galaxy_explainer.py").read_text()


def test_guide_to_galaxy_range_worker_results_are_relayed_to_main_thread():
    refresh_source = SOURCE.split("def refresh_ranges() -> None:", 1)[1].split("calculate_button.clicked.connect", 1)[0]

    assert "class RangeResultRelay(QObject):" in refresh_source
    assert "@Slot(str, str, object, object)" in refresh_source
    assert "worker.finished.connect(relay.deliver, Qt.QueuedConnection)" in refresh_source
    assert "worker.finished.connect(handle_finished)" not in refresh_source


def test_guide_to_galaxy_keeps_result_relay_alive_until_job_finishes():
    job_source = SOURCE.split("range_job: dict[str, object | None]", 1)[1].split("def _mark_dialog_closed", 1)[0]
    finish_source = SOURCE.split("def _finish_range_job", 1)[1].split("def refresh_ranges", 1)[0]
    refresh_source = SOURCE.split("def refresh_ranges() -> None:", 1)[1].split("def handle_finished", 1)[0]

    assert '"relay": None' in job_source
    assert 'range_job["relay"] = relay' in SOURCE
    assert 'range_job["relay"] = None' in finish_source
    assert 'range_job["worker"] = worker' in refresh_source
