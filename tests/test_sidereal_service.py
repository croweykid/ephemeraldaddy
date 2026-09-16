import datetime as dt
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ephemeraldaddy.core.sidereal_service import (
    SiderealCalculationRequest,
    SiderealChartDataService,
)
from tests.test_sidereal_repository import _database, _snapshot
from ephemeraldaddy.core.sidereal_repository import SiderealChartDataRepository


def _request(longitude=2.0):
    return SiderealCalculationRequest(
        chart_uid="PARENT01",
        datetime=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
        latitude=1.0,
        longitude=longitude,
        uses_houses=False,
        canonical_astro_token=("test", longitude, False),
    )


def test_from_chart_uses_range_midpoint_without_enabling_houses():
    chart = SimpleNamespace(
        chart_uid="PARENT01",
        dt=dt.datetime(2020, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
        birth_place="Test",
        lat=1.0,
        lon=2.0,
        birthtime_unknown=True,
        retcon_time_used=False,
        retcon_hour=None,
        retcon_minute=None,
        rectification_range_used=True,
        rectification_range_start_minute=8 * 60 + 10,
        rectification_range_end_minute=8 * 60 + 50,
    )

    request = SiderealCalculationRequest.from_chart(chart)

    assert not request.uses_houses
    assert (request.datetime.hour, request.datetime.minute) == (8, 30)
    assert request.source_token()


def test_service_reuses_current_row_and_rebuilds_stale_row():
    connection = _database()
    repository = SiderealChartDataRepository(connection)
    request = _request()
    current = replace(_snapshot(), source_recalculation_token=request.source_token())
    repository.upsert(current)
    calculator = Mock(return_value=current)
    service = SiderealChartDataService(repository, calculator=calculator)

    assert service.get_or_calculate(request) == current
    calculator.assert_not_called()

    stale_request = _request(longitude=2.1)
    rebuilt = replace(_snapshot(), source_recalculation_token=stale_request.source_token())
    calculator.return_value = rebuilt
    assert service.get_or_calculate(stale_request) == rebuilt
    calculator.assert_called_once()


def test_backfill_is_batched_resumable_and_skips_current_rows():
    connection = _database()
    repository = SiderealChartDataRepository(connection)
    first = _request()
    repository.upsert(replace(_snapshot(), source_recalculation_token=first.source_token()))
    second = _request(longitude=3.0)
    calculator = Mock(
        return_value=replace(_snapshot(), source_recalculation_token=second.source_token())
    )
    commits = Mock()
    service = SiderealChartDataService(repository, calculator=calculator)

    result = service.backfill([first, second], commit_batch=commits, batch_size=1)

    assert (result.inspected, result.reused, result.calculated) == (2, 1, 1)
    commits.assert_called_once()


def test_service_rejects_calculator_output_for_stale_source_inputs():
    connection = _database()
    repository = SiderealChartDataRepository(connection)
    service = SiderealChartDataService(repository, calculator=Mock(return_value=_snapshot()))

    with pytest.raises(ValueError, match="stale source inputs"):
        service.get_or_calculate(_request())

    assert repository.get("PARENT01") is None
