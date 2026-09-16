"""Application boundary for lazy Sidereal D1 snapshots and varga views."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import datetime as dt
from typing import Any

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
    """Canonical parent-chart inputs required for one Sidereal D1 snapshot."""

    chart_uid: str
    datetime: dt.datetime
    latitude: float
    longitude: float
    uses_houses: bool
    canonical_astro_token: tuple[Any, ...]

    def source_token(self) -> str:
        return source_recalculation_token(
            canonical_astro_token=self.canonical_astro_token,
        )

    @classmethod
    def from_chart(cls, chart: object) -> "SiderealCalculationRequest":
        """Build from ED's canonical time gate and ASTRO_DATA invalidation token."""

        from ephemeraldaddy.core.chart import _effective_chart_datetime, chart_uses_houses
        from ephemeraldaddy.core.chart_data_fields import astro_data_recalculation_token

        chart_uid = str(getattr(chart, "chart_uid", "") or "")
        base_datetime = getattr(chart, "dt", None)
        if not isinstance(base_datetime, dt.datetime):
            raise ValueError("Chart has no calculable datetime")

        uses_houses = chart_uses_houses(chart)
        calculation_datetime = (
            _effective_chart_datetime(chart) if uses_houses else base_datetime
        )
        if not isinstance(calculation_datetime, dt.datetime):
            raise ValueError("Chart has no effective calculation datetime")

        canonical_token = astro_data_recalculation_token(
            chart,
            chart_uses_houses_value=uses_houses,
        )
        return cls(
            chart_uid=chart_uid,
            datetime=calculation_datetime,
            latitude=float(getattr(chart, "lat")),
            longitude=float(getattr(chart, "lon")),
            uses_houses=uses_houses,
            canonical_astro_token=canonical_token,
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
            uses_houses=request.uses_houses,
            source_token=token,
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
