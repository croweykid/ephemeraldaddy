"""Timing-edit autosave policy for Chart Editor.

Rectified-time and unknown-time controls can invalidate expensive astronomical
payloads.  Keep their live preview debounced and keep formal persistence behind
Save/Discard rather than launching a full recalculation autosave while the user
is still editing.
"""

from __future__ import annotations


def timing_edits_should_start_recalculating_autosave() -> bool:
    """Return whether timing previews should also start full autosave.

    The current performance policy is intentionally conservative: timing edits
    mark the draft dirty and refresh the lightweight preview after a pause, but
    they do not start a background/timeout save that rebuilds and persists the
    whole chart.  Users can still explicitly save; navigation presents the
    normal Save/Discard prompt.
    """

    return False
