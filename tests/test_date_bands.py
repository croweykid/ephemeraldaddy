import datetime as dt

import pytest

from ephemeraldaddy.gui.features.chart_editor.date_band_values import (
    UNKNOWN_PORTION,
    date_band_geometry,
    normalized_optional_datetime,
    parse_optional_datetime,
)


def test_optional_datetime_is_blank_or_normalized() -> None:
    assert parse_optional_datetime("", "", "", "") is None
    value = parse_optional_datetime("09", "02", "2024", "23:07")
    assert value == dt.datetime(2024, 2, 9, 23, 7)
    assert normalized_optional_datetime(value) == "2024-02-09T23:07"


@pytest.mark.parametrize(
    "parts",
    [("09", "", "2024", "23:07"), ("31", "02", "2024", "12:00"), ("01", "01", "2024", "24:00")],
)
def test_partial_or_invalid_optional_datetime_is_rejected(parts) -> None:
    with pytest.raises(ValueError):
        parse_optional_datetime(*parts)


def test_known_dates_preserve_actual_peak_proportion() -> None:
    beginning = dt.datetime(2024, 1, 1)
    peak = dt.datetime(2024, 1, 3)
    end = dt.datetime(2024, 1, 9)
    geometry = date_band_geometry(beginning, peak, end)
    assert geometry.peak == pytest.approx(0.25)
    assert not any((geometry.beginning_unknown, geometry.peak_unknown, geometry.end_unknown))


def test_unknown_outer_intervals_reserve_thirty_percent() -> None:
    peak = dt.datetime(2024, 2, 1)
    end = dt.datetime(2024, 3, 1)
    left = date_band_geometry(None, peak, end)
    right = date_band_geometry(peak, end, None)
    assert left.peak == UNKNOWN_PORTION
    assert right.peak == 1.0 - UNKNOWN_PORTION
    assert left.beginning_unknown
    assert right.end_unknown


def test_unknown_peak_uses_centered_thirty_percent_region() -> None:
    geometry = date_band_geometry(dt.datetime(2024, 1, 1), None, dt.datetime(2024, 2, 1))
    assert geometry.peak == 0.5
    assert geometry.peak_unknown
