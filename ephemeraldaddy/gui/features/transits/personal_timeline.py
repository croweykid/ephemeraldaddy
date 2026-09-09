"""Stable Personal Timeline import surface with cache and table integrations."""

from __future__ import annotations

import sys

from ephemeraldaddy.gui.features.transits import personal_timeline_core as _core
from ephemeraldaddy.gui.features.transits.personal_timeline_persistence import (
    install_personal_timeline_persistence,
)
from ephemeraldaddy.gui.features.transits.personal_timeline_sorting import (
    install_personal_timeline_sorting,
)

install_personal_timeline_persistence(_core)
install_personal_timeline_sorting(_core)

# Keep the long-standing module identity behavior for callers and tests that
# monkeypatch private generator helpers. The implementation module remains the
# single owner of those globals; this facade only installs integrations once.
sys.modules[__name__] = _core
