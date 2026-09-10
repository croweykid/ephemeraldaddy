# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Stable public facade for Fantasy RPG Predictions.

The established implementation lives in ``dnd_predictions_core``. This facade
changes only Stat Block population norms: Chart View must use the selected
persisted Predictions norms snapshot and must never fall back to a live database
scan when that snapshot section is unavailable.
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

del _name
