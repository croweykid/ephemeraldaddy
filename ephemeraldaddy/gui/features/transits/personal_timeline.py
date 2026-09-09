"""Stable Personal Timeline import surface with permanent-cache integration."""

from __future__ import annotations

import sys

from ephemeraldaddy.gui.features.transits import personal_timeline_core as _core
from ephemeraldaddy.gui.features.transits.personal_timeline_persistence import (
    install_personal_timeline_persistence,
)

install_personal_timeline_persistence(_core)

# Keep the long-standing module identity behavior for callers and tests that
# monkeypatch private generator helpers. The implementation module remains the
# single owner of those globals; this facade only installs persistence once.
sys.modules[__name__] = _core
