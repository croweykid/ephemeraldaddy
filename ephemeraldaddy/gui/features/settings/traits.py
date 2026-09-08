"""Stable public facade for the Traits settings manager.

The existing file-management UI lives in ``traits_manager``. Trait Predictions
policy controls are layered here so the manager stays focused on Trait files and
the public import path remains unchanged.
"""

from __future__ import annotations

from ephemeraldaddy.gui.features.settings import traits_manager as _core
from ephemeraldaddy.gui.features.settings.trait_prediction_policy import (
    install_trait_prediction_settings as _install_trait_prediction_settings,
)

_install_trait_prediction_settings(_core)

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

del _name
