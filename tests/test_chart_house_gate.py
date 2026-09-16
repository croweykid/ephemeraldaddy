import datetime as dt
from types import SimpleNamespace

from ephemeraldaddy.core.chart import _effective_chart_datetime, chart_uses_houses


UTC = dt.timezone.utc
BASE_DT = dt.datetime(2020, 1, 1, 12, 34, tzinfo=UTC)


def _chart(**overrides):
    values = {
        "dt": BASE_DT,
        "birthtime_unknown": False,
        "retcon_time_used": False,
        "retcon_hour": None,
        "retcon_minute": None,
        "rectification_range_used": False,
        "rectification_range_start_minute": None,
        "rectification_range_end_minute": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_known_birth_time_enables_houses_and_uses_recorded_time():
    chart = _chart()

    assert chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) == BASE_DT


def test_unknown_birth_time_without_rectification_disables_houses():
    chart = _chart(birthtime_unknown=True)

    assert not chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) is None


def test_valid_exact_rectification_enables_houses_and_overrides_time():
    chart = _chart(
        birthtime_unknown=True,
        retcon_time_used=True,
        retcon_hour=8,
        retcon_minute=17,
    )

    assert chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) == BASE_DT.replace(
        hour=8, minute=17, second=0, microsecond=0
    )


def test_invalid_exact_rectification_does_not_enable_houses():
    chart = _chart(
        birthtime_unknown=True,
        retcon_time_used=True,
        retcon_hour=25,
        retcon_minute=0,
    )

    assert not chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) is None


def test_valid_rectification_range_enables_houses_and_uses_midpoint():
    chart = _chart(
        birthtime_unknown=True,
        rectification_range_used=True,
        rectification_range_start_minute=8 * 60 + 10,
        rectification_range_end_minute=8 * 60 + 50,
    )

    assert chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) == BASE_DT.replace(
        hour=8, minute=30, second=0, microsecond=0
    )


def test_invalid_rectification_range_does_not_enable_houses():
    chart = _chart(
        birthtime_unknown=True,
        rectification_range_used=True,
        rectification_range_start_minute=None,
        rectification_range_end_minute=8 * 60 + 50,
    )

    assert not chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) is None


def test_exact_rectification_wins_when_exact_and_range_flags_both_exist():
    chart = _chart(
        birthtime_unknown=True,
        retcon_time_used=True,
        retcon_hour=9,
        retcon_minute=5,
        rectification_range_used=True,
        rectification_range_start_minute=8 * 60,
        rectification_range_end_minute=10 * 60,
    )

    assert chart_uses_houses(chart)
    assert _effective_chart_datetime(chart) == BASE_DT.replace(
        hour=9, minute=5, second=0, microsecond=0
    )
