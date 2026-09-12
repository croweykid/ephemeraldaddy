"""Stable public facade for Chart View Trait Predictions.

The established implementation lives in ``trait_predictions_core``. Optional
provenance/gender prediction policies, signed factor-evidence sections,
source-sample display markers, and the semantic Themes Predictions extension
are installed here so callers keep the existing import path while new policy/UI
logic remains outside the core renderer and outside ``app.py``.
"""

from __future__ import annotations

from ephemeraldaddy.gui.features.charts import theme_predictions as _theme_predictions
from ephemeraldaddy.gui.features.charts import trait_predictions_core as _core
from ephemeraldaddy.gui.features.charts.theme_chart_info import (
    install_theme_chart_info as _install_theme_chart_info,
)
from ephemeraldaddy.gui.features.charts.trait_factor_sections import (
    install_trait_factor_sections as _install_trait_factor_sections,
)
from ephemeraldaddy.gui.features.charts.trait_prediction_context import (
    install_trait_prediction_context as _install_trait_prediction_context,
)
from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    install_trait_prediction_policy as _install_trait_prediction_policy,
)
from ephemeraldaddy.gui.features.charts.trait_sample_markers import (
    install_trait_sample_markers as _install_trait_sample_markers,
)
from ephemeraldaddy.gui.features.charts.theme_prediction_runtime import (
    install_theme_prediction_runtime as _install_theme_prediction_runtime,
)
from ephemeraldaddy.gui.features.charts.theme_predictions import (
    install_theme_predictions as _install_theme_predictions,
)

_install_trait_prediction_policy(_core)
_install_trait_prediction_context(_core)
_install_trait_sample_markers(_core)
_install_trait_factor_sections(_core)
_install_theme_predictions(_core)
_install_theme_prediction_runtime(_theme_predictions)
_install_theme_chart_info(_theme_predictions)

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

del _name
