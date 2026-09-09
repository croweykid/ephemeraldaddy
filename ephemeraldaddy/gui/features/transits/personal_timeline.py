"""Transitional Personal Timeline compatibility facade.

Removal milestone: delete this facade when the app.py refactor introduces an
explicit Transit-feature bootstrap/registry that installs Personal Timeline
integrations before use. Before removal, migrate window_chrome and the
`tests/test_personal_timeline*.py` callers that currently import/monkeypatch
this module to the implementation module or that registry, then verify there
are no remaining internal imports of this compatibility path.
"""

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

# TRANSITIONAL COMPATIBILITY: some current tests monkeypatch private generator
# helpers through `personal_timeline`, so preserving module identity avoids a
# second copy of those globals while the extraction settles. This alias must
# not become a permanent public interface; the removal milestone and required
# caller migration are documented in the module docstring above.
sys.modules[__name__] = _core
