# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Background worker helpers for Chart View Similar Charts calculations."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from ephemeraldaddy.analysis.get_astro_twin import find_astro_twins
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.db import get_chart_id_by_uid, get_chart_ids_by_uid, list_charts, load_chart, load_charts
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
        current_chart_uid: str | None,
        least_similar: bool,
        algorithm_mode: str,
        custom_settings: Any,
        hidden_chart_uids: set[str] | None = None,
        include_hidden_charts: bool = True,
        top_k: int = 3,
    ) -> None:
        super().__init__()
        self._request_id = request_id
        self._chart = chart
        self._current_chart_uid = str(current_chart_uid or "").strip().upper() or None
        self._least_similar = bool(least_similar)
        self._algorithm_mode = algorithm_mode
        self._custom_settings = custom_settings
        self._hidden_chart_uids = {str(uid).strip().upper() for uid in (hidden_chart_uids or set()) if str(uid).strip()}
        self._include_hidden_charts = bool(include_hidden_charts)
        self._top_k = int(top_k)
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:
        try:
            rows = list_charts()
            current_chart_id = get_chart_id_by_uid(self._current_chart_uid)
            hidden_chart_ids = set(get_chart_ids_by_uid(self._hidden_chart_uids).values())
            candidates = load_similar_chart_candidates(
                rows=rows,
                current_chart_id=current_chart_id,
                load_chart_by_id=load_chart,
                load_charts_by_ids=load_charts,
                hidden_chart_ids=hidden_chart_ids,
                include_hidden_charts=self._include_hidden_charts,
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
                exclude_chart_id=current_chart_id,
                least_similar=self._least_similar,
                algorithm_mode=self._algorithm_mode,
                custom_settings=self._custom_settings,
                should_cancel=self._should_cancel,
            )
            if self._should_cancel():
                self.finished.emit(
                    self._request_id,
                    {
                        "matches": [],
                        "empty_reason": "Similar chart calculation canceled safely.",
                        "canceled": True,
                    },
                )
                return
            self.finished.emit(
                self._request_id,
                {
                    "matches": matches,
                    "empty_reason": "No similar charts found.",
                },
            )
        except Exception as exc:
            self.failed.emit(self._request_id, str(exc), exc)
