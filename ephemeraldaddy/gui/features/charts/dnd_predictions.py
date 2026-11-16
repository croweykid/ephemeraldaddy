# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Stable public facade for Fantasy RPG Predictions.

The established implementation lives in ``dnd_predictions_core``. This facade
keeps Stat Block population norms snapshot-only and queues Fantasy RPG Alignment
refreshes outside the GUI thread when its visible section renders.
"""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.gui.features.charts import dnd_predictions_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def _snapshot_only_db_norm_stat_averages(_norm_charts: Any) -> dict[str, float]:
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
        ExplicitNormRecalculationRequired,
    )

    raise ExplicitNormRecalculationRequired(
        "Fantasy RPG Stat Block requires a complete D&D stat baseline in the selected "
        "Predictions norms snapshot. Live-database fallback is disabled for this "
        "Predictions section."
    )


# DndPredictionPanelAdapter methods execute against their defining module globals.
# Replacing this one imported helper leaves Species/Class and alignment behavior
# untouched while making Stat Block fail closed if its snapshot provider returns
# no complete stored baseline.
_core._calculate_db_norm_stat_averages = _snapshot_only_db_norm_stat_averages


_CoreDndPredictionPanelAdapter = _core.DndPredictionPanelAdapter


class DndPredictionPanelAdapter(_CoreDndPredictionPanelAdapter):
    """Ensure Alignment is current whenever its visible section renders."""

    _ephemeraldaddy_alignment_auto_refresh = True

    def render(
        self,
        chart: Any | None,
        metric_panel_renderer: Any,
        visible_sections: set[str] | None = None,
    ) -> Any:
        effective_sections = set(
            visible_sections
            or {"dnd_statblock", "dnd_species", "dnd_class", "dnd_alignment"}
        )
        from ephemeraldaddy.gui.features.predictions.alignment_refresh import AlignmentRefreshController
        from PySide6.QtCore import QObject
        parent = self.owner if isinstance(self.owner, QObject) else None
        controller = parent.findChild(AlignmentRefreshController, "prediction-alignment-refresh") if parent is not None else None
        if controller is None and parent is not None:
            controller = AlignmentRefreshController(parent)
            controller.setObjectName("prediction-alignment-refresh")
        if controller is not None:
            if chart is None or self.is_placeholder_chart(chart) or "dnd_alignment" not in effective_sections:
                controller.invalidate()
            elif "dnd_alignment" in effective_sections and self.alignment_layout is not None:
                def attach(parts: dict[str, Any]) -> None:
                    chart._dnd_alignment_score_parts_cache = {
                        "chart_uid": _core._chart_prediction_cache_uid(chart),
                        "key": _core._dnd_alignment_cache_key(self.owner or self, chart),
                        "parts": parts,
                    }
                def ready(parts: dict[str, Any]) -> None:
                    attach(parts)
                    super(DndPredictionPanelAdapter, self).render(chart, metric_panel_renderer, visible_sections={"dnd_alignment"})
                cached = controller.request(chart, ready)
                if cached is not None:
                    attach(cached)
        return super().render(
            chart,
            metric_panel_renderer,
            visible_sections=visible_sections,
        )


_core.DndPredictionPanelAdapter = DndPredictionPanelAdapter

del _name
