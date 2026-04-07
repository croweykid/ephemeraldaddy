"""Transit aspect window search mode settings."""

from __future__ import annotations

from dataclasses import dataclass

TRANSIT_WINDOW_ENABLE_DATE_ONLY = True
TRANSIT_WINDOW_ENABLE_DATE_TIME = False
TRANSIT_WINDOW_DATE_ONLY_STEP_HOURS = 24.0
TRANSIT_WINDOW_DATE_ONLY_PRECISION_MINUTES = 24.0 * 60.0
TRANSIT_WINDOW_DATE_TIME_STEP_HOURS = 12.0
TRANSIT_WINDOW_DATE_TIME_PRECISION_MINUTES = 15.0
TRANSIT_WINDOW_CACHE_LIMIT = 512
TRANSIT_WINDOW_VERY_FAST_BODIES = {"AS", "DS", "MC", "IC"}
TRANSIT_WINDOW_VERY_FAST_STEP_HOURS = 1.0 / 60.0
TRANSIT_WINDOW_VERY_FAST_PRECISION_MINUTES = 1.0


@dataclass(frozen=True)
class TransitWindowScanConfig:
    scan_step_hours: float
    scan_precision_minutes: float
    include_time: bool


def validate_transit_window_mode_flags() -> None:
    """Validate static transit-mode feature flags.

    Kept as an explicit function (instead of import-time side effect) so call sites can
    control exactly when validation runs.
    """
    if TRANSIT_WINDOW_ENABLE_DATE_ONLY and TRANSIT_WINDOW_ENABLE_DATE_TIME:
        raise ValueError(
            "Transit window modes are mutually exclusive: DATE_ONLY and DATE_TIME cannot both be enabled."
        )


def resolve_transit_window_scan_config() -> TransitWindowScanConfig:
    """Return scan parameters for transit-window searching."""
    validate_transit_window_mode_flags()
    if TRANSIT_WINDOW_ENABLE_DATE_ONLY:
        return TransitWindowScanConfig(
            scan_step_hours=TRANSIT_WINDOW_DATE_ONLY_STEP_HOURS,
            scan_precision_minutes=TRANSIT_WINDOW_DATE_ONLY_PRECISION_MINUTES,
            include_time=False,
        )
    return TransitWindowScanConfig(
        scan_step_hours=TRANSIT_WINDOW_DATE_TIME_STEP_HOURS,
        scan_precision_minutes=TRANSIT_WINDOW_DATE_TIME_PRECISION_MINUTES,
        include_time=True,
    )


def resolve_transit_window_scan_config_for_transit_body(
    transit_body: str,
    *,
    base_config: TransitWindowScanConfig | None = None,
) -> TransitWindowScanConfig:
    """Return scan parameters tuned for the transit body speed class."""
    config = base_config or resolve_transit_window_scan_config()
    if transit_body in TRANSIT_WINDOW_VERY_FAST_BODIES:
        return TransitWindowScanConfig(
            scan_step_hours=min(config.scan_step_hours, TRANSIT_WINDOW_VERY_FAST_STEP_HOURS),
            scan_precision_minutes=min(config.scan_precision_minutes, TRANSIT_WINDOW_VERY_FAST_PRECISION_MINUTES),
            include_time=True,
        )
    return config
