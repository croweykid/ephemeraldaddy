from ephemeraldaddy.analysis.time_sensitivity import (
    TimeSensitivityConfig,
    TimeSensitivityResult,
    save_time_sensitivity_result,
    scan_times,
)


def test_scan_times_includes_half_hours_plus_day_end():
    times = scan_times(30)

    assert len(times) == 49
    assert times[:3] == [(0, 0), (0, 30), (1, 0)]
    assert times[-1] == (23, 59)


def test_save_time_sensitivity_result_uses_sidecar_sqlite(tmp_path):
    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        algorithm_version="time-sensitivity-v1",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=49,
        baseline_time="12:00",
        overall={"stability_percent": 100.0},
        numeric_ranges={},
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )
    db_path = tmp_path / "time_sensitivity.db"

    save_time_sensitivity_result(result, db_path)

    assert db_path.exists()
