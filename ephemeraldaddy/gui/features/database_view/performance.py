"""Migration-stable performance instrumentation for Database View workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from ephemeraldaddy.core.performance_metrics import record_performance_metric


DATABASE_VIEW_OPEN_TO_VISIBLE_METRIC = "database_view.open_to_visible"


@dataclass(slots=True)
class DatabaseViewOpenTiming:
    """Track one Database View open without depending on Qt or a window class.

    Keeping the timing at the workflow boundary means the legacy dialog can be
    renamed or moved without changing the metric name or its completion rules.
    """

    started_at: float = field(default_factory=lambda: perf_counter())
    recorder: Callable[..., None] = record_performance_metric
    _completed: bool = field(default=False, init=False)

    def complete(
        self,
        *,
        was_visible: bool,
        refresh_reason: str,
        status: str = "ok",
    ) -> None:
        """Record the duration once; repeated completion signals are harmless."""

        if self._completed:
            return
        self._completed = True
        self.recorder(
            DATABASE_VIEW_OPEN_TO_VISIBLE_METRIC,
            (perf_counter() - self.started_at) * 1000.0,
            status=status,
            was_visible=was_visible,
            refresh_reason=refresh_reason,
        )
