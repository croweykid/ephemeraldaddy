import datetime as dt
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from ephemeraldaddy.analysis import time_sensitivity
from ephemeraldaddy.analysis.time_sensitivity import (
    TIME_SENSITIVITY_ALGORITHM_VERSION,
    TimeSensitivityConfig,
    TimeSensitivityResult,
    load_time_sensitivity_result_for_chart,
    save_time_sensitivity_result,
)
from ephemeraldaddy.gui.features.chart_editor.time_sensitivity import hourly_scan


UTC = dt.timezone.utc
_SWISS_J2000_LONDON_LAHIRI_AS = 0.4340826001690026
_SWISS_J2000_LONDON_LAHIRI_MC = 255.7578653142555
_SWISS_J2000_LONDON_LAHIRI_SUN = 256.51569718931427
_SWISS_J2000_LONDON_LAHIRI_CUSPS = (
    0.4340826001690026,
    37.308576926662056,
    58.17678964290366,
    75.7578653142555,
    95.20014903446688,
    123.8341527186856,
    180.434082600169,
    217.30857692666206,
    238.17678964290369,
    255.7578653142555,
    275.2001490344669,
    303.83415271868563,
)


def _source_chart(*, zodiac="sidereal", ayanamsha="lahiri"):
    return SimpleNamespace(
        name="Reference",
        chart_uid="REFERENCE01",
        dt=dt.datetime(2000, 1, 1, 12, 0, tzinfo=UTC),
        dt_local=dt.datetime(2000, 1, 1, 12, 0),
        lat=51.5,
        lon=0.0,
        birthtime_unknown=False,
        retcon_time_used=False,
        rectification_range_used=False,
        zodiac=zodiac,
        ayanamsha=ayanamsha if zodiac == "sidereal" else None,
        division="D1",
        _explicit_tz=UTC,
        alias=None,
        from_whence=None,
    )


def _assert_lahiri_reference(variant):
    assert variant.zodiac == "sidereal"
    assert variant.ayanamsha == "lahiri"
    assert variant.positions["Sun"] == pytest.approx(
        _SWISS_J2000_LONDON_LAHIRI_SUN, abs=1e-8
    )
    assert variant.positions["AS"] == pytest.approx(
        _SWISS_J2000_LONDON_LAHIRI_AS, abs=1e-8
    )
    assert variant.positions["MC"] == pytest.approx(
        _SWISS_J2000_LONDON_LAHIRI_MC, abs=1e-8
    )
    assert tuple(variant.houses) == pytest.approx(
        _SWISS_J2000_LONDON_LAHIRI_CUSPS, abs=1e-8
    )


def test_broad_time_sensitivity_variant_uses_native_sidereal_geometry():
    variant = time_sensitivity._variant_chart(_source_chart(), 12, 0)

    _assert_lahiri_reference(variant)


def test_fine_tune_variant_uses_native_sidereal_geometry():
    source = _source_chart()
    variant = hourly_scan._variant_at(source, source.dt)

    _assert_lahiri_reference(variant)


def test_time_sensitivity_config_resolves_active_coordinate_context():
    tropical = _source_chart(zodiac="tropical", ayanamsha=None)
    sidereal = _source_chart()

    tropical_config = time_sensitivity._resolved_config(tropical)
    sidereal_config = time_sensitivity._resolved_config(sidereal)

    # None/None is deliberately retained as the backward-compatible Tropical
    # cache identity; Sidereal must always be explicit so the rows cannot collide.
    assert (tropical_config.zodiac, tropical_config.ayanamsha) == (None, None)
    assert (sidereal_config.zodiac, sidereal_config.ayanamsha) == (
        "sidereal",
        "lahiri",
    )
    assert time_sensitivity._config_hash(
        asdict(tropical_config)
    ) != time_sensitivity._config_hash(asdict(sidereal_config))


def test_tropical_cache_hash_matches_pre_context_config_shape():
    current = asdict(TimeSensitivityConfig())
    legacy = dict(current)
    legacy.pop("zodiac")
    legacy.pop("ayanamsha")

    assert time_sensitivity._config_hash(current) == time_sensitivity._config_hash(
        legacy
    )


def test_time_sensitivity_cache_separates_tropical_and_sidereal_same_uid(tmp_path):
    tropical = _source_chart(zodiac="tropical", ayanamsha=None)
    sidereal = _source_chart()
    db_path = tmp_path / "time_sensitivity.db"

    def result_for(chart, marker):
        config = time_sensitivity._resolved_config(chart, TimeSensitivityConfig())
        return TimeSensitivityResult(
            chart_uid=chart.chart_uid,
            chart_name=chart.name,
            birth_date_key="01-01-2000",
            algorithm_version=TIME_SENSITIVITY_ALGORITHM_VERSION,
            computed_at="2026-09-16T00:00:00Z",
            config=asdict(config),
            sample_count=1,
            baseline_time="12:00",
            overall={"marker": marker},
            numeric_ranges={},
            human_design={},
            stable=[],
            variable=[],
            warnings=[],
        )

    save_time_sensitivity_result(result_for(tropical, "tropical"), db_path)
    save_time_sensitivity_result(result_for(sidereal, "sidereal"), db_path)

    tropical_loaded = load_time_sensitivity_result_for_chart(
        tropical, TimeSensitivityConfig(), db_path
    )
    sidereal_loaded = load_time_sensitivity_result_for_chart(
        sidereal, TimeSensitivityConfig(), db_path
    )

    assert tropical_loaded is not None
    assert sidereal_loaded is not None
    assert tropical_loaded.overall["marker"] == "tropical"
    assert sidereal_loaded.overall["marker"] == "sidereal"


def test_v11_cache_is_invalidated_after_nakshatra_algorithm_change(tmp_path):
    chart = _source_chart(zodiac="tropical", ayanamsha=None)
    config = time_sensitivity._resolved_config(chart, TimeSensitivityConfig())
    db_path = tmp_path / "time_sensitivity.db"
    stale = TimeSensitivityResult(
        chart_uid=chart.chart_uid,
        chart_name=chart.name,
        birth_date_key="01-01-2000",
        algorithm_version="time-sensitivity-v11",
        computed_at="2026-09-16T00:00:00Z",
        config=asdict(config),
        sample_count=1,
        baseline_time="12:00",
        overall={"marker": "stale fixed-range nakshatras"},
        numeric_ranges={},
        human_design={},
        stable=[],
        variable=[],
        warnings=[],
    )
    save_time_sensitivity_result(stale, db_path)

    assert TIME_SENSITIVITY_ALGORITHM_VERSION == "time-sensitivity-v12"
    assert load_time_sensitivity_result_for_chart(
        chart, TimeSensitivityConfig(), db_path
    ) is None


def test_fine_tune_signature_invalidates_when_coordinate_context_changes():
    chart = _source_chart(zodiac="tropical", ayanamsha=None)
    tropical_signature = hourly_scan.fine_tune_calculation_signature(chart)

    chart.zodiac = "sidereal"
    chart.ayanamsha = "lahiri"
    sidereal_signature = hourly_scan.fine_tune_calculation_signature(chart)

    assert tropical_signature != sidereal_signature
