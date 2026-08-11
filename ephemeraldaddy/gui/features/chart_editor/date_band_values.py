"""Pure value handling for optional timeline dates and proportional bands."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

UNKNOWN_PORTION = 0.30


def parse_optional_datetime(day: str, month: str, year: str, time_text: str) -> dt.datetime | None:
    values = tuple(value.strip() for value in (day, month, year, time_text))
    if not any(values):
        return None
    if not all(values):
        raise ValueError("Enter DD, MM, YYYY and TT:TT, or leave every field blank.")
    try:
        return dt.datetime.strptime(" ".join(values), "%d %m %Y %H:%M")
    except ValueError as exc:
        raise ValueError("Date/time must be a real DD MM YYYY and 24-hour TT:TT value.") from exc


def normalized_optional_datetime(value: dt.datetime | None) -> str:
    return "" if value is None else value.strftime("%Y-%m-%dT%H:%M")


@dataclass(frozen=True)
class DateBandGeometry:
    beginning: float
    peak: float
    end: float
    beginning_unknown: bool
    peak_unknown: bool
    end_unknown: bool


def date_band_geometry(
    beginning: dt.datetime | None,
    peak: dt.datetime | None,
    end: dt.datetime | None,
) -> DateBandGeometry:
    if beginning and peak and end and beginning <= peak <= end:
        duration = (end - beginning).total_seconds()
        peak_position = 0.5 if duration == 0 else (peak - beginning).total_seconds() / duration
        return DateBandGeometry(0.0, peak_position, 1.0, False, False, False)
    if beginning and peak and beginning <= peak and end is None:
        return DateBandGeometry(0.0, 1.0 - UNKNOWN_PORTION, 1.0, False, False, True)
    if peak and end and peak <= end and beginning is None:
        return DateBandGeometry(0.0, UNKNOWN_PORTION, 1.0, True, False, False)
    if beginning and end and beginning <= end and peak is None:
        return DateBandGeometry(0.0, 0.5, 1.0, False, True, False)
    return DateBandGeometry(0.0, 0.5, 1.0, beginning is None, peak is None, end is None)
