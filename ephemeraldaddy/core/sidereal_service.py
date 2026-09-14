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

    @classmethod
    def from_chart(cls, chart: object) -> "SiderealCalculationRequest":
        chart_uid = str(getattr(chart, "chart_uid", "") or "")
        chart_datetime = getattr(chart, "dt", None)
        if not isinstance(chart_datetime, dt.datetime):
            raise ValueError("Chart has no calculable datetime")
        retcon_used = bool(getattr(chart, "retcon_time_used", False))
        retcon_hour = getattr(chart, "retcon_hour", None)
        retcon_minute = getattr(chart, "retcon_minute", None)
        if retcon_used and retcon_hour is not None and retcon_minute is not None:
            chart_datetime = chart_datetime.replace(
                hour=int(retcon_hour), minute=int(retcon_minute), second=0, microsecond=0
            )
        use_birth_time_data = not bool(
            getattr(chart, "birthtime_unknown", False)
        ) or retcon_used
        return cls(
            chart_uid=chart_uid,
            datetime=chart_datetime,
            latitude=float(getattr(chart, "lat")),
            longitude=float(getattr(chart, "lon")),
            use_birth_time_data=use_birth_time_data,
            rectification_state={
                "retcon_time_used": retcon_used,
                "retcon_hour": retcon_hour,
                "retcon_minute": retcon_minute,
                "rectification_range_used": bool(
                    getattr(chart, "rectification_range_used", False)
                ),
                "rectification_range_start_minute": getattr(
                    chart, "rectification_range_start_minute", None
                ),
                "rectification_range_end_minute": getattr(
                    chart, "rectification_range_end_minute", None
                ),
            },
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
