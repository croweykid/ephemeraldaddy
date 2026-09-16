# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Stable public facade for Fantasy RPG Predictions.

The established implementation lives in ``dnd_predictions_core``. This facade
keeps Stat Block population norms snapshot-only and makes Fantasy RPG Alignment
self-refreshing whenever its visible section is rendered.
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
        if (
            "dnd_alignment" in effective_sections
            and self.alignment_layout is not None
            and chart is not None
            and not self.is_placeholder_chart(chart)
        ):
            try:
                self.cache_alignment_metadata(chart)
            except Exception as exc:  # pragma: no cover - defensive UI path
                _core.logger.warning(
                    "Automatic Fantasy RPG Alignment calculation failed: %s",
                    exc,
                    exc_info=True,
                )
        return super().render(
            chart,
            metric_panel_renderer,
            visible_sections=visible_sections,
        )


_core.DndPredictionPanelAdapter = DndPredictionPanelAdapter

del _name
