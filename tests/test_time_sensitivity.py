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


def test_compute_time_sensitivity_keeps_numeric_samples_when_human_design_fails(monkeypatch):
    from datetime import datetime
    from types import SimpleNamespace

    from ephemeraldaddy.analysis import time_sensitivity as module
    from ephemeraldaddy.analysis.time_sensitivity import compute_time_sensitivity

    chart = SimpleNamespace(dt=datetime(2000, 1, 1, 12, 0), lat=0.0, lon=0.0, name="Example")
    numeric = {group: {"example": 1.0} for group in module.NUMERIC_GROUPS}

    monkeypatch.setattr(module, "_variant_chart", lambda source, hour, minute: source)
    monkeypatch.setattr(module, "_numeric_snapshot", lambda variant: numeric)
    monkeypatch.setattr(module, "_categorical_snapshot", lambda variant: {})
    monkeypatch.setattr(module, "_hd_snapshot", lambda variant: (_ for _ in ()).throw(ValueError("HD unavailable")))

    result = compute_time_sensitivity(chart, TimeSensitivityConfig(interval_minutes=720, include_day_end=False))

    assert result.sample_count == 2
    assert result.numeric_ranges["dominant_planet_weights"]["example"]["min"] == 1.0
    assert result.human_design["gates"]["always"] == []
    assert result.warnings == [
        "00:00 Human Design skipped: HD unavailable",
        "12:00 Human Design skipped: HD unavailable",
    ]
