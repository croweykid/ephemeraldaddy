"""Window-independent coordination for incremental Chart Editor migration.

This controller accepts narrow callbacks rather than the legacy Chart Editor
window. The remaining dirty/save lifecycle can therefore migrate here without
creating another window-as-service-locator dependency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

logger = logging.getLogger(__name__)

AutosaveKind = Literal["metadata", "lightweight metadata"]


class ChartEditorController:
    """Coordinate lightweight Chart Editor changes through explicit callbacks."""

    def __init__(
        self,
        *,
        is_change_tracking_suppressed: Callable[[], bool],
        mark_draft_dirty: Callable[[], None],
        mark_recalculation_required: Callable[[], None],
        queue_lightweight_autosave: Callable[[], None],
        is_draft_dirty: Callable[[], bool],
        current_chart_uid: Callable[[], str | None],
    ) -> None:
        self._is_change_tracking_suppressed = is_change_tracking_suppressed
        self._mark_draft_dirty = mark_draft_dirty
        self._mark_recalculation_required = mark_recalculation_required
        self._queue_lightweight_autosave = queue_lightweight_autosave
        self._is_draft_dirty = is_draft_dirty
        self._current_chart_uid = current_chart_uid

    def on_lightweight_metadata_changed(self) -> None:
        """Mark flavor metadata dirty and schedule its lightweight update."""
        if self._is_change_tracking_suppressed():
            return
        self._mark_draft_dirty()
        self._queue_lightweight_autosave()

    def on_authoritative_metadata_changed(self) -> None:
        """Protect an authoritative edit from any later lightweight autosave."""
        if self._is_change_tracking_suppressed():
            return
        self._mark_draft_dirty()
        self._mark_recalculation_required()

    def report_incomplete_autosave(self, kind: AutosaveKind) -> None:
        """Make a failed autosave observable while preserving the dirty draft."""
        if not self._is_draft_dirty():
            return
        chart_uid = self._current_chart_uid() or "unknown"
        logger.warning(
            "Chart Editor %s autosave did not complete for chart UID %s; "
            "leaving draft dirty so the save prompt remains available.",
            kind,
            chart_uid,
        )
