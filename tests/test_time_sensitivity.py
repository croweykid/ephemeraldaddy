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
        birth_date_key="01-01-2000",
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


def test_time_sensitivity_nakshatra_lookup_accepts_full_range_rows():
    from ephemeraldaddy.analysis.time_sensitivity import _get_nakshatra

    assert _get_nakshatra(24.0) == "Ashwini"
    assert _get_nakshatra(37.2) == "Bharani"


def test_compute_time_sensitivity_keeps_numeric_samples_when_human_design_fails(
    monkeypatch,
):
    from datetime import datetime
    from types import SimpleNamespace

    from ephemeraldaddy.analysis import time_sensitivity as module
    from ephemeraldaddy.analysis.time_sensitivity import compute_time_sensitivity

    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 0), lat=0.0, lon=0.0, name="Example"
    )
    numeric = {group: {"example": 1.0} for group in module.NUMERIC_GROUPS}

    monkeypatch.setattr(module, "_variant_chart", lambda source, hour, minute: source)
    monkeypatch.setattr(module, "_numeric_snapshot", lambda variant: numeric)
    monkeypatch.setattr(module, "_categorical_snapshot", lambda variant: {})
    monkeypatch.setattr(
        module,
        "_hd_snapshot",
        lambda variant: (_ for _ in ()).throw(ValueError("HD unavailable")),
    )

    result = compute_time_sensitivity(
        chart, TimeSensitivityConfig(interval_minutes=720, include_day_end=False)
    )

    assert result.sample_count == 2
    assert result.numeric_ranges["dominant_planet_weights"]["example"]["min"] == 1.0
    assert result.human_design["gates"]["always"] == []
    assert result.warnings == [
        "00:00 Human Design skipped: HD unavailable",
        "12:00 Human Design skipped: HD unavailable",
    ]


def test_aggregate_numeric_reports_delta_from_baseline_not_full_span():
    from ephemeraldaddy.analysis import time_sensitivity as module

    samples = [
        {"time": "00:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "12:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "23:59", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
    ]
    for sample, value in zip(samples, (10.0, 20.0, 30.0), strict=True):
        sample["numeric"]["dominant_planet_weights"]["example"] = value
    baseline = {group: {} for group in module.NUMERIC_GROUPS}
    baseline["dominant_planet_weights"]["example"] = 20.0

    ranges, group_deltas = module._aggregate_numeric(samples, baseline)
    payload = ranges["dominant_planet_weights"]["example"]

    assert payload["delta"] == 20.0
    assert payload["baseline_delta"] == 10.0
    assert payload["percent_delta"] == 50.0
    assert payload["max_decrease_percent"] == -50.0
    assert payload["max_increase_percent"] == 50.0
    assert payload["variability_percent"] == 100.0
    assert payload["label"] == "extreme"
    assert payload["peak_times"] == ["23:59"]
    assert group_deltas["dominant_planet_weights"] == 50.0


def test_aggregate_numeric_reports_most_likely_weight_from_sample_mode():
    from ephemeraldaddy.analysis import time_sensitivity as module

    samples = [
        {"time": "00:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "06:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "12:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "18:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
    ]
    for sample, value in zip(samples, (4.0, 9.0, 9.0, 2.0), strict=True):
        sample["numeric"]["dominant_planet_weights"]["example"] = value
    baseline = {group: {} for group in module.NUMERIC_GROUPS}
    baseline["dominant_planet_weights"]["example"] = 4.0

    ranges, _group_deltas = module._aggregate_numeric(samples, baseline)
    mode = ranges["dominant_planet_weights"]["example"]["most_likely_weight"]

    assert mode["available"] is True
    assert mode["weight"] == 9.0
    assert mode["count"] == 2
    assert mode["percent"] == 50.0
    assert mode["times"] == ["06:00", "12:00"]
    assert mode["spans"] == ["06:00–12:00"]


def test_aggregate_numeric_marks_tied_weight_modes_unavailable():
    from ephemeraldaddy.analysis import time_sensitivity as module

    samples = [
        {"time": "00:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "06:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "12:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
    ]
    for sample, value in zip(samples, (4.0, 9.0, 2.0), strict=True):
        sample["numeric"]["dominant_planet_weights"]["example"] = value
    baseline = {group: {} for group in module.NUMERIC_GROUPS}
    baseline["dominant_planet_weights"]["example"] = 4.0

    ranges, _group_deltas = module._aggregate_numeric(samples, baseline)
    mode = ranges["dominant_planet_weights"]["example"]["most_likely_weight"]

    assert mode["available"] is False
    assert mode["reason"] == "multimodal"
    assert mode["weight"] is None
    assert mode["count"] == 1
    assert mode["percent"] == 33.33
    assert mode["tied_weights"] == [2.0, 4.0, 9.0]


def test_baseline_time_for_chart_prefers_current_or_rectified_time():
    from datetime import datetime
    from types import SimpleNamespace

    from ephemeraldaddy.analysis import time_sensitivity as module

    known_time = SimpleNamespace(
        dt=datetime(2000, 1, 1, 8, 30), birthtime_unknown=False, retcon_time_used=False
    )
    unknown_time = SimpleNamespace(
        dt=datetime(2000, 1, 1, 8, 30), birthtime_unknown=True, retcon_time_used=False
    )
    rectified_time = SimpleNamespace(
        dt=datetime(2000, 1, 1, 8, 30),
        birthtime_unknown=True,
        retcon_time_used=True,
        retcon_hour=14,
        retcon_minute=45,
    )

    assert module._baseline_time_for_chart(known_time, None) == (
        8,
        30,
        "08:30",
        "current chart time",
    )
    assert module._baseline_time_for_chart(unknown_time, None) == (
        12,
        0,
        "12:00",
        "noon fallback",
    )
    assert module._baseline_time_for_chart(rectified_time, None) == (
        14,
        45,
        "14:45",
        "rectified time",
    )


def test_time_sensitivity_result_loads_by_birth_date_not_chart_uid(tmp_path):
    from datetime import datetime
    from types import SimpleNamespace

    from ephemeraldaddy.analysis.time_sensitivity import (
        load_time_sensitivity_result_for_chart,
    )

    config = TimeSensitivityConfig(interval_minutes=30, include_day_end=True)
    result = TimeSensitivityResult(
        chart_uid="FIRST",
        chart_name="First",
        birth_date_key="04-05-2001",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=config.__dict__,
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

    other_chart = SimpleNamespace(dt=datetime(2001, 4, 5, 8, 30), chart_uid="SECOND")

    loaded = load_time_sensitivity_result_for_chart(other_chart, config, db_path)

    assert loaded is not None
    assert loaded.chart_uid == "FIRST"
    assert loaded.birth_date_key == "04-05-2001"


def test_aggregate_numeric_reports_sampled_time_spans_and_transition_windows():
    from ephemeraldaddy.analysis import time_sensitivity as module

    samples = [
        {"time": "00:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "00:30", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "01:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
    ]
    for sample, value in zip(samples, (0.0, 3.0, 3.0), strict=True):
        sample["numeric"]["dominant_planet_weights"]["example"] = value
    baseline = {group: {} for group in module.NUMERIC_GROUPS}
    baseline["dominant_planet_weights"]["example"] = 0.0

    ranges, _group_deltas = module._aggregate_numeric(samples, baseline)
    payload = ranges["dominant_planet_weights"]["example"]

    assert payload["present_spans"] == ["00:30–01:00"]
    assert payload["peak_spans"] == ["00:30–01:00"]
    assert payload["transition_windows"] == ["00:00–00:30"]


def test_save_time_sensitivity_does_not_delete_other_empty_uid_dates(tmp_path):
    config = TimeSensitivityConfig(interval_minutes=30, include_day_end=True)
    first = TimeSensitivityResult(
        chart_uid="",
        chart_name="First",
        birth_date_key="04-05-2001",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=config.__dict__,
        sample_count=49,
        baseline_time="12:00",
        overall={"stability_percent": 100.0},
        numeric_ranges={},
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )
    second = TimeSensitivityResult(
        chart_uid="",
        chart_name="Second",
        birth_date_key="04-06-2001",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=config.__dict__,
        sample_count=49,
        baseline_time="12:00",
        overall={"stability_percent": 99.0},
        numeric_ranges={},
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )
    db_path = tmp_path / "time_sensitivity.db"

    save_time_sensitivity_result(first, db_path)
    save_time_sensitivity_result(second, db_path)

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        dates = [
            row[0]
            for row in conn.execute(
                "SELECT birth_date_key FROM chart_time_sensitivity_ranges ORDER BY birth_date_key"
            )
        ]

    assert dates == ["04-05-2001", "04-06-2001"]


def test_time_sensitivity_html_color_codes_deltas_and_links_factors():
    import pytest

    panel_module = pytest.importorskip(
        "ephemeraldaddy.gui.features.charts.time_sensitivity_panel",
        exc_type=ImportError,
    )
    format_time_sensitivity_result_html = (
        panel_module.format_time_sensitivity_result_html
    )

    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=2,
        baseline_time="12:00",
        overall={
            "stability_percent": 50.0,
            "max_total_change_from_baseline_percent": 50.0,
        },
        numeric_ranges={
            "dominant_sign_weights": {
                "Aries": {
                    "min": 1.0,
                    "max": 3.0,
                    "baseline": 1.0,
                    "delta": 2.0,
                    "percent_delta": 200.0,
                    "max_decrease_percent": 0.0,
                    "max_increase_percent": 200.0,
                    "label": "Highly variable",
                    "peak_times": ["12:00"],
                },
                "Taurus": {
                    "min": 1.0,
                    "max": 1.5,
                    "baseline": 1.0,
                    "delta": 0.5,
                    "percent_delta": 50.0,
                    "max_decrease_percent": 0.0,
                    "max_increase_percent": 50.0,
                    "label": "Variable",
                    "peak_times": ["00:00"],
                },
            },
            "dominant_element_weights": {
                "Fire": {
                    "min": 0.0,
                    "max": 2.0,
                    "baseline": 1.0,
                    "delta": 2.0,
                    "percent_delta": 100.0,
                    "max_decrease_percent": -100.0,
                    "max_increase_percent": 100.0,
                    "label": "Highly variable",
                    "peak_times": ["23:59"],
                },
            },
        },
        human_design={
            "gates": {"always": [1], "sometimes": [2], "sample_count": 2},
            "lines": {"always": ["1.1"], "sometimes": [], "sample_count": 2},
            "channels": {"always": [], "sometimes": [], "sample_count": 2},
            "type_distribution": {"Generator": 2},
            "profile_distribution": {"1/3": 2},
        },
        stable=[],
        variable=[],
        warnings=[],
    )

    html = format_time_sensitivity_result_html(result)

    assert "distinguishing-factor:sign:Aries" in html
    assert "distinguishing-factor:element:Fire" in html
    assert "distinguishing-factor:gate:1" in html
    assert "distinguishing-factor:gate-line:1:1" in html
    assert "color:#b7ff00" in html
    assert "color:#7a0000" in html
    assert "text-decoration: underline" not in html
    assert "underline dotted" not in html


def test_time_sensitivity_html_colors_min_and_max_against_separate_peer_scales():
    import pytest

    panel_module = pytest.importorskip(
        "ephemeraldaddy.gui.features.charts.time_sensitivity_panel",
        exc_type=ImportError,
    )
    format_time_sensitivity_result_html = (
        panel_module.format_time_sensitivity_result_html
    )

    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=2,
        baseline_time="12:00",
        overall={
            "stability_percent": 50.0,
            "max_total_change_from_baseline_percent": 50.0,
        },
        numeric_ranges={
            "dominant_sign_weights": {
                "Aries": {
                    "min": 1.0,
                    "max": 3.0,
                    "baseline": 1.0,
                    "delta": 2.0,
                    "percent_delta": 200.0,
                    "max_decrease_percent": 0.0,
                    "max_increase_percent": 200.0,
                    "label": "Highly variable",
                    "peak_times": ["12:00"],
                },
                "Taurus": {
                    "min": 2.0,
                    "max": 2.5,
                    "baseline": 2.0,
                    "delta": 0.5,
                    "percent_delta": 25.0,
                    "max_decrease_percent": 0.0,
                    "max_increase_percent": 25.0,
                    "label": "Variable",
                    "peak_times": ["00:00"],
                },
            },
        },
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )

    html = format_time_sensitivity_result_html(result)
    taurus_item = html[html.index("Taurus") : html.index("Taurus") + 500]

    assert "<span style='color:#b7ff00;'>2.00</span>" in taurus_item
    assert "<span style='color:#7a0000;'>2.50</span>" in taurus_item


def test_body_sign_confidence_keys_follow_planet_order_without_angles():
    from ephemeraldaddy.analysis.time_sensitivity import (
        ANGLE_SIGN_CONFIDENCE_KEYS,
        BODY_SIGN_CONFIDENCE_KEYS,
    )
    from ephemeraldaddy.core.interpretations import PLANET_ORDER

    expected = tuple(
        body for body in PLANET_ORDER if body not in ANGLE_SIGN_CONFIDENCE_KEYS
    )

    assert BODY_SIGN_CONFIDENCE_KEYS == expected


def test_categorical_snapshot_includes_extended_body_signs():
    from types import SimpleNamespace

    from ephemeraldaddy.analysis.time_sensitivity import _categorical_snapshot

    chart = SimpleNamespace(
        positions={
            "Neptune": 330.0,
            "Rahu": 0.0,
            "Ketu": 180.0,
            "Chiron": 30.0,
            "Ceres": 60.0,
            "Pallas": 90.0,
            "Juno": 120.0,
            "Vesta": 150.0,
            "Lilith": 210.0,
            "Part of Fortune": 240.0,
        }
    )

    body_signs = _categorical_snapshot(chart)["body_signs"]

    assert body_signs["Neptune"] == "Pisces"
    assert body_signs["Rahu"] == "Aries"
    assert body_signs["Ketu"] == "Libra"
    assert body_signs["Chiron"] == "Taurus"
    assert body_signs["Ceres"] == "Gemini"
    assert body_signs["Pallas"] == "Cancer"
    assert body_signs["Juno"] == "Leo"
    assert body_signs["Vesta"] == "Virgo"
    assert body_signs["Lilith"] == "Scorpio"
    assert body_signs["Part of Fortune"] == "Sagittarius"


def test_time_sensitivity_confidence_uses_ascertainment_percent_and_bright_green_scale():
    import pytest

    panel_module = pytest.importorskip(
        "ephemeraldaddy.gui.features.charts.time_sensitivity_panel",
        exc_type=ImportError,
    )

    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=2,
        baseline_time="12:00",
        overall={
            "stability_percent": 0.0,
            "ascertainment_confidence": {"percent": 42.5},
        },
        numeric_ranges={},
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )

    assert panel_module._confidence_percent(result) == 42.5
    assert panel_module._confidence_color(0) == "#7a0000"
    assert panel_module._confidence_color(100) == "#00ff00"


def test_time_sensitivity_popout_factor_info_shows_min_max_peak_and_trench():
    import pytest

    panel_module = pytest.importorskip(
        "ephemeraldaddy.gui.features.charts.time_sensitivity_panel",
        exc_type=ImportError,
    )

    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v2",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=2,
        baseline_time="12:00",
        overall={},
        numeric_ranges={
            "dominant_nakshatra_weights": {
                "Ashwini": {
                    "min": 2.0,
                    "max": 7.0,
                    "most_likely_weight": {"weight": 5.0, "count": 3, "percent": 75.0},
                    "trough_times": ["00:30"],
                    "peak_times": ["23:30"],
                },
            },
        },
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )

    html = panel_module._time_sensitivity_factor_info_html(
        result, "dominant_nakshatra_weights", "Ashwini"
    )

    assert "Ashwini" in html
    assert "Min dominance" in html
    assert "2" in html
    assert "Most likely weight" in html
    assert "5" in html
    assert "Max dominance" in html
    assert "7" in html
    assert "Trench time" in html
    assert "00:30" in html
    assert "Peak time" in html
    assert "23:30" in html


def test_time_sensitivity_popout_charts_include_all_numeric_factor_click_targets():
    from pathlib import Path

    source = Path(
        "ephemeraldaddy/gui/features/charts/time_sensitivity_panel.py"
    ).read_text()

    assert '"dominant_planet_weights": "Dominant Body Weight Distribution"' in source
    assert '"dominant_sign_weights": "Dominant Sign Weight Distribution"' in source
    assert (
        '"dominant_element_weights": "Dominant Element Weight Distribution"' in source
    )
    assert '"dominant_house_weights": "Dominant House Weight Distribution"' in source
    assert '"dominant_mode_weights": "Dominant Mode Weight Distribution"' in source
    assert (
        '"dominant_nakshatra_weights": "Dominant Nakshatra Weight Distribution"'
        in source
    )
    assert 'setattr(bar, "_time_sensitivity_factor", label)' in source
    assert 'setattr(tick_label, "_time_sensitivity_factor", label)' in source
    assert "_install_factor_click(ax, clickable_artists, on_factor_click)" in source


def test_time_sensitivity_chart_canvases_forward_wheel_events_to_parent_scroll_area():
    from pathlib import Path

    source = Path(
        "ephemeraldaddy/gui/features/charts/time_sensitivity_panel.py"
    ).read_text()

    assert "class TimeSensitivityFigureCanvas(FigureCanvas):" in source
    assert "def wheelEvent(self, event: object) -> None" in source
    assert "scroll_area.verticalScrollBar()" in source
    assert "event.accept()" in source
    assert "canvas = TimeSensitivityFigureCanvas(figure)" in source


def test_time_sensitivity_popout_captures_rendered_result_for_factor_clicks():
    from pathlib import Path

    source = Path(
        "ephemeraldaddy/gui/features/charts/time_sensitivity_panel.py"
    ).read_text()
    popout_source = source.split("def _show_likelihood_popout", 1)[1]

    assert "result = self._last_result" in popout_source
    assert "if result is None:" in popout_source
    assert (
        "_time_sensitivity_factor_info_html(result, group_key, label)" in popout_source
    )
    assert (
        "_draw_likelihood_chart(ax, result, group_key, on_factor_click=show_factor_info)"
        in popout_source
    )
    assert (
        "_time_sensitivity_factor_info_html(self._last_result, group_key, label)"
        not in popout_source
    )


def test_ascertainment_confidence_values_stable_planet_signs_over_volatile_scores():
    from ephemeraldaddy.analysis.time_sensitivity import _ascertainment_confidence

    samples = [
        {
            "human_design": {"type": "Generator", "profile": "1/3"},
            "categorical": {
                "body_signs": {
                    "Sun": "Aries",
                    "Moon": "Taurus",
                    "Mercury": "Gemini",
                    "Venus": "Cancer",
                    "Mars": "Leo",
                    "Jupiter": "Virgo",
                    "Saturn": "Libra",
                    "Uranus": "Scorpio",
                    "Neptune": "Sagittarius",
                    "Pluto": "Capricorn",
                },
                "angle_signs": {"AS": "Aries", "MC": "Cancer"},
            },
        },
        {
            "human_design": {"type": "Generator", "profile": "1/3"},
            "categorical": {
                "body_signs": {
                    "Sun": "Aries",
                    "Moon": "Taurus",
                    "Mercury": "Gemini",
                    "Venus": "Cancer",
                    "Mars": "Leo",
                    "Jupiter": "Virgo",
                    "Saturn": "Libra",
                    "Uranus": "Scorpio",
                    "Neptune": "Sagittarius",
                    "Pluto": "Capricorn",
                },
                "angle_signs": {"AS": "Libra", "MC": "Capricorn"},
            },
        },
    ]
    overall = {
        "stability_percent": 0.0,
        "group_deltas": {
            "dominant_element_weights": 0.0,
            "dominant_mode_weights": 0.0,
            "dominant_nakshatra_weights": 0.0,
        },
        "dominance_likelihoods": {
            "dominant_planet_weights": {"Sun": {"percent": 100.0}},
            "dominant_sign_weights": {"Aries": {"percent": 100.0}},
            "dominant_element_weights": {"Fire": {"percent": 100.0}},
            "dominant_mode_weights": {"Cardinal": {"percent": 100.0}},
            "dominant_nakshatra_weights": {"Ashwini": {"percent": 100.0}},
        },
    }
    hd = {
        "gates": {"always": [1], "sometimes": [2]},
        "lines": {"always": ["1.1"], "sometimes": []},
        "channels": {"always": ["1-8"], "sometimes": []},
    }

    confidence = _ascertainment_confidence(samples, overall, hd)

    assert confidence["percent"] > 70.0
    assert confidence["components"]["planetary sign stability"] == 100.0
    assert confidence["components"]["angle sign stability"] == 50.0
    assert confidence["components"]["human design stability"] == 90.0
    assert confidence["components"]["element/mode/nakshatra stability"] == 100.0


def test_aggregate_numeric_records_weight_samples_for_scatterplot_tooltips():
    from ephemeraldaddy.analysis import time_sensitivity as module

    samples = [
        {"time": "00:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
        {"time": "12:00", "numeric": {group: {} for group in module.NUMERIC_GROUPS}},
    ]
    for sample, value in zip(samples, (4.0, 9.0), strict=True):
        sample["numeric"]["dominant_planet_weights"]["example"] = value
    baseline = {group: {} for group in module.NUMERIC_GROUPS}
    baseline["dominant_planet_weights"]["example"] = 4.0

    ranges, _group_deltas = module._aggregate_numeric(samples, baseline)

    assert ranges["dominant_planet_weights"]["example"]["weight_samples"] == [
        {"time": "00:00", "weight": 4.0},
        {"time": "12:00", "weight": 9.0},
    ]


def test_time_sensitivity_scatter_points_use_sample_times_as_hover_labels():
    import pytest

    panel_module = pytest.importorskip(
        "ephemeraldaddy.gui.features.charts.time_sensitivity_panel",
        exc_type=ImportError,
    )

    result = TimeSensitivityResult(
        chart_uid="CHARTUID",
        chart_name="Example",
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v9",
        computed_at="2026-06-20T00:00:00Z",
        config=TimeSensitivityConfig().__dict__,
        sample_count=2,
        baseline_time="12:00",
        overall={},
        numeric_ranges={
            "dominant_sign_weights": {
                "Aries": {
                    "min": 1.0,
                    "max": 2.75,
                    "weight_samples": [
                        {"time": "00:00", "weight": 1.5},
                        {"time": "12:00", "weight": 2.75},
                    ],
                }
            }
        },
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )

    x_values, y_values, labels, times = panel_module._sampled_weight_points(
        result, "dominant_sign_weights", ["Aries"]
    )

    assert x_values == [0.0, 0.0]
    assert y_values == [1.5, 2.75]
    assert times == ["00:00", "12:00"]
    assert labels == ["Aries\n00:00 • 1.5", "Aries\n12:00 • 2.75"]
