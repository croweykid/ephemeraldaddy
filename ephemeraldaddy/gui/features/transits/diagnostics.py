"""Terminal diagnostics for Personal Transit chart inputs."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Callable

from ephemeraldaddy.core.ephemeris import planetary_longitude

logger = logging.getLogger(__name__)


def log_natal_saturn_position_diagnostic(
    natal_chart: Any,
    *,
    longitude_lookup: Callable[[datetime.datetime, str], float | None] = planetary_longitude,
) -> None:
    """Compare Personal Transit's loaded Saturn longitude with a fresh value."""
    stored_value = (getattr(natal_chart, "positions", None) or {}).get("Saturn")
    effective_datetime = getattr(natal_chart, "dt", None)
    if not isinstance(effective_datetime, datetime.datetime):
        logger.warning(
            "Personal transit Saturn diagnostic unavailable: chart_uid=%s chart=%r "
            "stored_longitude=%r effective_datetime=%r",
            getattr(natal_chart, "chart_uid", None),
            getattr(natal_chart, "name", ""),
            stored_value,
            effective_datetime,
        )
        return

    if bool(getattr(natal_chart, "retcon_time_used", False)):
        retcon_hour = getattr(natal_chart, "retcon_hour", None)
        retcon_minute = getattr(natal_chart, "retcon_minute", None)
        if retcon_hour is not None and retcon_minute is not None:
            effective_datetime = effective_datetime.replace(
                hour=int(retcon_hour),
                minute=int(retcon_minute),
                second=0,
                microsecond=0,
            )

    try:
        fresh_value = longitude_lookup(effective_datetime, "Saturn")
    except Exception:
        logger.exception(
            "Personal transit Saturn diagnostic failed: chart_uid=%s chart=%r "
            "stored_longitude=%r effective_datetime=%s",
            getattr(natal_chart, "chart_uid", None),
            getattr(natal_chart, "name", ""),
            stored_value,
            effective_datetime.isoformat(),
        )
        return

    difference = None
    if stored_value is not None and fresh_value is not None:
        raw_difference = abs(float(stored_value) - float(fresh_value)) % 360.0
        difference = min(raw_difference, 360.0 - raw_difference)
    logger.info(
        "Personal transit Saturn diagnostic: chart_uid=%s chart=%r "
        "effective_datetime=%s stored_longitude=%s fresh_longitude=%s "
        "difference_degrees=%s cache_mismatch=%s",
        getattr(natal_chart, "chart_uid", None),
        getattr(natal_chart, "name", ""),
        effective_datetime.isoformat(),
        "None" if stored_value is None else f"{float(stored_value):.6f}",
        "None" if fresh_value is None else f"{float(fresh_value):.6f}",
        "None" if difference is None else f"{difference:.6f}",
        difference is None or difference > (1.0 / 60.0),
    )
