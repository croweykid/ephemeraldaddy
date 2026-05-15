"""Background worker helpers for Chart View Similar Charts calculations."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from ephemeraldaddy.analysis.get_astro_twin import find_astro_twins
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.db import list_charts, load_chart
from ephemeraldaddy.gui.features.charts.similar_charts_popout import (
    load_similar_chart_candidates,
)


class SimilarChartsWorker(QObject):
    """Calculates Chart View Similar Charts matches off the GUI thread."""

    finished = Signal(str, object)
    failed = Signal(str, str, object)

    def __init__(
        self,
        *,
        request_id: str,
        chart: Chart,
        current_chart_id: int | None,
        least_similar: bool,
        algorithm_mode: str,
        custom_settings: Any,
        top_k: int = 3,
    ) -> None:
        super().__init__()
        self._request_id = request_id
        self._chart = chart
        self._current_chart_id = current_chart_id
        self._least_similar = bool(least_similar)
        self._algorithm_mode = algorithm_mode
        self._custom_settings = custom_settings
        self._top_k = int(top_k)

    def run(self) -> None:
        try:
            rows = list_charts()
            candidates = load_similar_chart_candidates(
                rows=rows,
                current_chart_id=self._current_chart_id,
                load_chart_by_id=load_chart,
            )
            if not candidates:
                self.finished.emit(
                    self._request_id,
                    {
                        "matches": [],
                        "empty_reason": "Need at least one additional saved chart that is not placeholder/hypothetical.",
                    },
                )
                return

            matches = find_astro_twins(
                self._chart,
                candidates,
                top_k=self._top_k,
                exclude_chart_id=self._current_chart_id,
                least_similar=self._least_similar,
                algorithm_mode=self._algorithm_mode,
                custom_settings=self._custom_settings,
            )
            self.finished.emit(
                self._request_id,
                {
                    "matches": matches,
                    "empty_reason": "No similar charts found.",
                },
            )
        except Exception as exc:
            self.failed.emit(self._request_id, str(exc), exc)
