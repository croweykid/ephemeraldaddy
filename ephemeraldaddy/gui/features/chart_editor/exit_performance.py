"""Chart Editor exit performance policy.

This module keeps heavy leave-Chart-Editor decisions out of ``app.py`` while the
larger ChartEditorWindow/ChartEditSession extraction is in progress.
"""

from __future__ import annotations

from collections.abc import Iterable


PREDICTION_FLUSH_BLOCKING_FIELDS = frozenset({
    "birth_data",
})


def should_block_database_view_open_for_prediction_flush(
    *,
    pending_prediction_flush: bool,
    changed_fields: Iterable[str] | None,
    active_right_panel: str | None,
) -> bool:
    """Return whether leaving Chart Editor should synchronously refresh predictions.

    Prediction cache writes can be tens of seconds of UI-thread work.  Database
    View does not need freshly materialized Chart View prediction text to become
    visible, so the default must be non-blocking.  The only defensible sync path
    is when we cannot classify the save at all *and* the user is actively in the
    Predictions panel, where an immediate cache consistency guarantee is more
    valuable than Database View open latency.
    """
    if not pending_prediction_flush:
        return False
    if active_right_panel != "predictions":
        return False
    if changed_fields is None:
        return True
    return False


def should_defer_prediction_flush_until_prediction_view(
    *,
    pending_prediction_flush: bool,
    changed_fields: Iterable[str] | None,
) -> bool:
    """Return whether prediction caches may wait until Predictions are requested.

    Birth-data and rectified-time edits mark prediction caches stale, but forcing
    DnD/OCEAN/Enneagram cache writes while opening Database View caused the
    observed multi-second-to-tens-of-seconds freeze.  Keep the stale marker so
    Prediction rendering can refresh on demand instead of blocking navigation.
    """
    if not pending_prediction_flush:
        return False
    if changed_fields is None:
        return True
    return bool(PREDICTION_FLUSH_BLOCKING_FIELDS.intersection(changed_fields))
