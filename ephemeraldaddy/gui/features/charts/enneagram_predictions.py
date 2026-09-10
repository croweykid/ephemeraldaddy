# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Stable public facade for Enneagram Predictions.

The established renderer/scorer lives in ``enneagram_predictions_core``. This
facade changes only the Chart View population-baseline source: runtime panel
calculations must consume the selected persisted Predictions norms snapshot.
"""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.gui.features.charts import enneagram_predictions_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def _snapshot_database_norm_averages(
    self: Any,
    _norm_charts: Any,
) -> dict[int, float]:
    from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
        ExplicitNormRecalculationRequired,
        enneagram_type_snapshot_averages,
        load_prediction_norms_snapshot,
    )

    snapshot = load_prediction_norms_snapshot()
    stored_definition_signature = str(
        snapshot.get("enneagram_definition_signature", "") or ""
    )
    current_definition_signature = _core._enneagram_definition_signature()
    if not stored_definition_signature:
        raise ExplicitNormRecalculationRequired(
            "Enneagram Predictions require a stored Enneagram baseline in the selected "
            "Predictions norms snapshot."
        )
    if stored_definition_signature != current_definition_signature:
        raise ExplicitNormRecalculationRequired(
            "The selected Enneagram Predictions baseline was calculated for different "
            "Enneagram scoring definitions. Recalculate DB Norms before recalculating "
            "this prediction."
        )

    averages = enneagram_type_snapshot_averages(snapshot)
    if len(averages) != 9:
        raise ExplicitNormRecalculationRequired(
            "Enneagram Predictions require a complete stored 1-9 baseline in the "
            "selected Predictions norms snapshot."
        )
    return averages


_core.EnneagramPredictionPanelAdapter._database_norm_averages = (
    _snapshot_database_norm_averages
)

del _name
