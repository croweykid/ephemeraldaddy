"""Background coordinator for persistent HD electrochemistry norms."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock, Thread

from ephemeraldaddy.analysis.human_design_electrochemistry_norms import (
    HD_ELECTROCHEMISTRY_NORMS_CACHE_FILENAME,
    HumanDesignElectrochemistryNorms,
    calculate_human_design_electrochemistry_norms,
    electrochemistry_chart_tokens,
    electrochemistry_norms_freshness,
    load_human_design_electrochemistry_norms,
    save_human_design_electrochemistry_norms,
)
from ephemeraldaddy.core.db import get_db_path, list_human_design_synastry_candidates

logger = logging.getLogger(__name__)

_lock = Lock()
_norms: HumanDesignElectrochemistryNorms | None = None
_loaded = False
_building = False
_checked_revision: int | None = None


def _cache_path() -> Path:
    return get_db_path().parent / HD_ELECTROCHEMISTRY_NORMS_CACHE_FILENAME


def current_human_design_electrochemistry_norms() -> HumanDesignElectrochemistryNorms | None:
    """Return the last persisted/built snapshot without blocking."""
    global _loaded, _norms
    with _lock:
        if not _loaded:
            _norms = load_human_design_electrochemistry_norms(_cache_path())
            _loaded = True
        return _norms


def human_design_electrochemistry_norms_are_building() -> bool:
    with _lock:
        return _building


def request_human_design_electrochemistry_norms(database_revision: int) -> bool:
    """Check freshness and, when needed, build norms on one daemon worker.

    A stale snapshot remains readable while the worker runs. The worker is
    revision-coalesced, so ordinary panel rerenders do not rescan the database.
    """
    global _building, _checked_revision
    current_human_design_electrochemistry_norms()
    normalized_revision = int(database_revision)
    with _lock:
        if _building or _checked_revision == normalized_revision:
            return False
        _building = True
        _checked_revision = normalized_revision
    Thread(
        target=_check_and_rebuild,
        name="hd-electrochemistry-norms",
        daemon=True,
    ).start()
    return True


def _check_and_rebuild() -> None:
    global _building, _checked_revision, _norms
    try:
        candidates = list_human_design_synastry_candidates()
        current_tokens = electrochemistry_chart_tokens(candidates)
        with _lock:
            saved_norms = _norms
        should_rebuild = saved_norms is None
        if saved_norms is not None:
            freshness = electrochemistry_norms_freshness(
                saved_norms.chart_tokens,
                current_tokens,
            )
            should_rebuild = freshness.requires_refresh
        if should_rebuild:
            rebuilt = calculate_human_design_electrochemistry_norms(candidates)
            latest_candidates = list_human_design_synastry_candidates()
            if electrochemistry_chart_tokens(latest_candidates) != current_tokens:
                # Do not let a snapshot calculated from an older population
                # overwrite the cache after edits made during the long pass.
                with _lock:
                    _checked_revision = None
                return
            save_human_design_electrochemistry_norms(_cache_path(), rebuilt)
            with _lock:
                _norms = rebuilt
    except Exception:
        with _lock:
            _checked_revision = None
        logger.exception("Unable to refresh Human Design electrochemistry norms")
    finally:
        with _lock:
            _building = False
