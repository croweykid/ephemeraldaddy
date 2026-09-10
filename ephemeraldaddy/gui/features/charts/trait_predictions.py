"""Stable public facade for Chart View Trait Predictions.

The established implementation lives in ``trait_predictions_core``. Optional
provenance/gender prediction policies, source-sample display markers, and the
semantic Themes Predictions extension are installed here so callers keep the
existing import path while new policy/UI logic remains outside the core
renderer and outside ``app.py``.
"""

from __future__ import annotations

from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot as _prediction_norms_snapshot
from ephemeraldaddy.gui.features.charts import trait_predictions_core as _core
from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    install_trait_prediction_policy as _install_trait_prediction_policy,
)
from ephemeraldaddy.gui.features.charts.trait_sample_markers import (
    install_trait_sample_markers as _install_trait_sample_markers,
)
from ephemeraldaddy.gui.features.charts.theme_predictions import (
    install_theme_predictions as _install_theme_predictions,
)

_install_trait_prediction_policy(_core)
_install_trait_sample_markers(_core)
# Theme population baselines are first-class data in prediction_norms_snapshot;
# prevent the legacy extension hook from wrapping/recalculating them a second time.
_prediction_norms_snapshot._ephemeraldaddy_theme_norms_installed = True
_install_theme_predictions(_core)

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

del _name
