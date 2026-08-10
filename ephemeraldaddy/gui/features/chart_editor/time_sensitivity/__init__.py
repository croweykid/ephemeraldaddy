"""Pure public API for Chart Editor fine-tune time-sensitivity calculations.

Qt controller and HTML presentation exports intentionally remain in their
own modules so calculation consumers do not acquire GUI import costs.
"""

from .hourly_scan import (
    FineTuneHourlyScanRequest,
    FineTuneHourlyScanResult,
    FineTuneSnapshot,
    FineTuneTransition,
    TransitionSection,
    compute_fine_tune_hourly_scan,
    fine_tune_calculation_signature,
    fine_tune_hour_sample_minutes,
)

__all__ = [
    "FineTuneHourlyScanRequest",
    "FineTuneHourlyScanResult",
    "FineTuneSnapshot",
    "FineTuneTransition",
    "TransitionSection",
    "compute_fine_tune_hourly_scan",
    "fine_tune_calculation_signature",
    "fine_tune_hour_sample_minutes",
]
