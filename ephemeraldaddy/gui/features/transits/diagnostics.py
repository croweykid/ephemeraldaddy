"""Terminal diagnostics for Personal Transit chart inputs."""

from __future__ import annotations

import copy
import datetime
import logging
from collections.abc import Callable, Mapping
from typing import Any

from ephemeraldaddy.core.aspects import find_aspects
from ephemeraldaddy.core.chart import apply_time_specific_metadata_policy
from ephemeraldaddy.core.ephemeris import planetary_positions, planetary_retrogrades

logger = logging.getLogger(__name__)

DERIVED_FIELDS = ("positions", "retrogrades", "houses", "housesPo", "aspects")
POSITION_TOLERANCE_DEGREES = 1.0 / 60.0


def _effective_datetime(chart: Any) -> datetime.datetime | None:
    moment = getattr(chart, "dt", None)
    if not isinstance(moment, datetime.datetime):
        return None
    if bool(getattr(chart, "retcon_time_used", False)):
        hour = getattr(chart, "retcon_hour", None)
        minute = getattr(chart, "retcon_minute", None)
        if hour is not None and minute is not None:
            moment = moment.replace(
                hour=int(hour), minute=int(minute), second=0, microsecond=0
            )
    return moment


def _fresh_derived_snapshot(chart: Any) -> dict[str, Any]:
    """Recalculate the persisted derived fields without mutating the loaded chart."""
    moment = _effective_datetime(chart)
    if moment is None:
        raise ValueError("chart has no effective datetime")
    fresh_chart = copy.deepcopy(chart)
    fresh_chart.positions = planetary_positions(moment, fresh_chart.lat, fresh_chart.lon)
    fresh_chart.retrogrades = planetary_retrogrades(moment)
    apply_time_specific_metadata_policy(fresh_chart)
    add_fortune = getattr(fresh_chart, "_add_part_of_fortune", None)
    if callable(add_fortune):
        add_fortune()
    fresh_chart.aspects = find_aspects(fresh_chart.positions)
    return {field: copy.deepcopy(getattr(fresh_chart, field, None)) for field in DERIVED_FIELDS}


def _angular_difference(stored: Any, fresh: Any) -> float | None:
    try:
        difference = abs(float(stored) - float(fresh)) % 360.0
    except (TypeError, ValueError):
        return None
    return min(difference, 360.0 - difference)


def _log_mapping(field: str, stored: Any, fresh: Any) -> int:
    stored_map = stored if isinstance(stored, Mapping) else {}
    fresh_map = fresh if isinstance(fresh, Mapping) else {}
    mismatches = 0
    for key in sorted(set(stored_map) | set(fresh_map), key=str):
        stored_value = stored_map.get(key)
        fresh_value = fresh_map.get(key)
        if field == "positions":
            difference = _angular_difference(stored_value, fresh_value)
            match = difference is not None and difference <= POSITION_TOLERANCE_DEGREES
            detail = "None" if difference is None else f"{difference:.6f}°"
        else:
            match = stored_value == fresh_value
            detail = "n/a"
        mismatches += int(not match)
        logger.info(
            "Personal transit derived-cache row: field=%s key=%s stored=%r fresh=%r "
            "difference=%s match=%s",
            field,
            key,
            stored_value,
            fresh_value,
            detail,
            match,
        )
    return mismatches


def _log_sequence(field: str, stored: Any, fresh: Any) -> int:
    stored_sequence = list(stored or [])
    fresh_sequence = list(fresh or [])
    match = stored_sequence == fresh_sequence
    logger.info(
        "Personal transit derived-cache row: field=%s stored=%r fresh=%r match=%s",
        field,
        stored_sequence,
        fresh_sequence,
        match,
    )
    return int(not match)


def log_natal_derived_cache_diagnostic(
    natal_chart: Any,
    *,
    snapshot_builder: Callable[[Any], dict[str, Any]] = _fresh_derived_snapshot,
) -> None:
    """Log every loaded derived-cache field beside a fresh recalculation."""
    moment = _effective_datetime(natal_chart)
    identity = (
        f"chart_uid={getattr(natal_chart, 'chart_uid', None)} "
        f"chart={getattr(natal_chart, 'name', '')!r}"
    )
    try:
        fresh = snapshot_builder(natal_chart)
    except Exception:
        logger.exception(
            "Personal transit derived-cache diagnostic failed: %s effective_datetime=%r",
            identity,
            None if moment is None else moment.isoformat(),
        )
        return

    logger.info(
        "Personal transit derived-cache diagnostic started: %s effective_datetime=%s",
        identity,
        None if moment is None else moment.isoformat(),
    )
    mismatch_counts: dict[str, int] = {}
    for field in DERIVED_FIELDS:
        stored_value = getattr(natal_chart, field, None)
        fresh_value = fresh.get(field)
        if field in {"positions", "retrogrades"}:
            mismatch_counts[field] = _log_mapping(field, stored_value, fresh_value)
        else:
            mismatch_counts[field] = _log_sequence(field, stored_value, fresh_value)
    logger.info(
        "Personal transit derived-cache diagnostic completed: %s mismatch_counts=%s "
        "cache_mismatch=%s",
        identity,
        mismatch_counts,
        any(mismatch_counts.values()),
    )
