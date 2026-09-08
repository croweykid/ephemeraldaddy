"""Stable public facade for Chart View Trait Predictions.

The established implementation lives in ``trait_predictions_core``. Optional
provenance/gender prediction policies are installed here so callers keep the
existing import path while new policy logic remains outside the core renderer and
outside ``app.py``.
"""

from __future__ import annotations

from ephemeraldaddy.gui.features.charts import trait_predictions_core as _core
from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    install_trait_prediction_policy as _install_trait_prediction_policy,
)

_install_trait_prediction_policy(_core)

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

del _name
