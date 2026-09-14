"""Application boundary for lazy Sidereal D1 snapshots and varga views."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import datetime as dt
from typing import Any, Mapping

from ephemeraldaddy.core.sidereal import (
    LAHIRI,
    SiderealChartData,
    calculate_lahiri_d1,
    source_recalculation_token,
)
from ephemeraldaddy.core.sidereal_repository import SiderealChartDataRepository
from ephemeraldaddy.core.vargas import VargaChartView, project_varga


@dataclass(frozen=True)
class SiderealCalculationRequest:
    """Astrology-relevant parent inputs for one chart UID."""

    chart_uid: str
    datetime: dt.datetime
    latitude: float
    longitude: float
    use_birth_time_data: bool
    rectification_state: Mapping[str, Any] | None = None

    def source_token(self) -> str:
        return source_recalculation_token(
            dt=self.datetime,
            latitude=self.latitude,
            longitude=self.longitude,
            use_birth_time_data=self.use_birth_time_data,
            rectification_state=self.rectification_state,
        )


@dataclass(frozen=True)
class SiderealBackfillResult:
    inspected: int
    calculated: int
    reused: int


class SiderealChartDataService:
    """Read current snapshots, rebuilding only missing or stale D1 rows."""

    def __init__(
        self,
        repository: SiderealChartDataRepository,
        *,
        calculator: Callable[..., SiderealChartData] = calculate_lahiri_d1,
    ) -> None:
        self._repository = repository
        self._calculator = calculator

    def get_or_calculate(self, request: SiderealCalculationRequest) -> SiderealChartData:
        token = request.source_token()
        current = self._repository.get(
            request.chart_uid,
            ayanamsha=LAHIRI,
            source_token=token,
        )
        if current is not None:
            return current
        calculated = self._calculator(
            chart_uid=request.chart_uid,
            dt=request.datetime,
            latitude=request.latitude,
            longitude=request.longitude,
            use_birth_time_data=request.use_birth_time_data,
            source_token=token,
            rectification_state=request.rectification_state,
        )
        normalized_request_uid = "".join(
            character
            for character in request.chart_uid.strip().upper()
            if character.isalnum()
        )[:64]
        if calculated.chart_uid != normalized_request_uid:
            raise ValueError("Sidereal calculator returned data for a different chart UID")
        if calculated.source_recalculation_token != token:
            raise ValueError("Sidereal calculator returned data for stale source inputs")
        self._repository.upsert(calculated)
        return calculated

    def get_varga(
        self, request: SiderealCalculationRequest, division: str = "D9"
    ) -> VargaChartView:
        return project_varga(self.get_or_calculate(request), division)

    def backfill(
        self,
        requests: Iterable[SiderealCalculationRequest],
        *,
        commit_batch: Callable[[], None],
        batch_size: int = 100,
        progress: Callable[[SiderealBackfillResult], None] | None = None,
    ) -> SiderealBackfillResult:
        """Idempotently populate D1 rows, committing bounded resumable batches."""

        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        inspected = calculated = reused = pending = 0
        for request in requests:
            inspected += 1
            token = request.source_token()
            if self._repository.get(request.chart_uid, source_token=token) is not None:
                reused += 1
            else:
                self.get_or_calculate(request)
                calculated += 1
                pending += 1
            if pending >= batch_size:
                commit_batch()
                pending = 0
                if progress is not None:
                    progress(SiderealBackfillResult(inspected, calculated, reused))
        if pending:
            commit_batch()
        result = SiderealBackfillResult(inspected, calculated, reused)
        if progress is not None:
            progress(result)
        return result
