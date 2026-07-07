from __future__ import annotations

import datetime as dt
from typing import Callable

from ephemeraldaddy.core.ephemeris import planetary_positions
from ephemeraldaddy.core.interpretations import ZODIAC_NAMES

RETCON_BODIES = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Rahu",
    "Ketu",
    "Lilith",
]

# Bodies that move slowly enough for decade-level pruning.
SLOW_RETCON_BODIES = {
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Rahu",
    "Ketu",
    "Lilith",
}


def zodiac_sign_for_longitude(longitude: float) -> str:
    sign_idx = int((longitude % 360.0) // 30.0)
    return ZODIAC_NAMES[sign_idx]


def _build_decade_windows(start_dt: dt.datetime, end_dt: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
    windows: list[tuple[dt.datetime, dt.datetime]] = []
    decade_year = (start_dt.year // 10) * 10
    while decade_year <= end_dt.year:
        decade_start = start_dt.replace(
            year=decade_year,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        decade_end = start_dt.replace(
            year=decade_year + 9,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        window_start = max(start_dt, decade_start)
        window_end = min(end_dt, decade_end)
        if window_start <= window_end:
            windows.append((window_start, window_end))
        decade_year += 10
    return windows


def _decade_window_matches_slow_criteria(
    window_start: dt.datetime,
    window_end: dt.datetime,
    required_slow_signs: dict[str, str],
    lat: float,
    lon: float,
    should_cancel_cb: Callable[[], bool] | None,
) -> bool:
    if not required_slow_signs:
        return True

    matched: dict[str, bool] = {body: False for body in required_slow_signs}
    current = window_start
    # monthly-ish samples are enough for slow-body pruning and much cheaper than full scans
    sample_step = dt.timedelta(days=30)

    while current <= window_end:
        if should_cancel_cb is not None and should_cancel_cb():
            return False
        positions = planetary_positions(current, lat, lon)
        for body, expected_sign in required_slow_signs.items():
            lon_value = positions.get(body)
            if lon_value is None:
                continue
            if zodiac_sign_for_longitude(lon_value) == expected_sign:
                matched[body] = True
        if all(matched.values()):
            return True
        current += sample_step

    return all(matched.values())


def _candidate_search_windows(
    start_dt: dt.datetime,
    end_dt: dt.datetime,
    required_signs: dict[str, str],
    lat: float,
    lon: float,
    should_cancel_cb: Callable[[], bool] | None,
) -> list[tuple[dt.datetime, dt.datetime]]:
    slow_required = {
        body: sign for body, sign in required_signs.items() if body in SLOW_RETCON_BODIES
    }
    if not slow_required:
        return [(start_dt, end_dt)]

    windows: list[tuple[dt.datetime, dt.datetime]] = []
    for window_start, window_end in _build_decade_windows(start_dt, end_dt):
        if should_cancel_cb is not None and should_cancel_cb():
            break
        if _decade_window_matches_slow_criteria(
            window_start,
            window_end,
            slow_required,
            lat,
            lon,
            should_cancel_cb,
        ):
            windows.append((window_start, window_end))
    return windows


def search_retcon_candidates(
    required_signs: dict[str, str],
    start_dt: dt.datetime,
    end_dt: dt.datetime,
    lat: float,
    lon: float,
    *,
    step_minutes: int = 60,
    max_results: int = 100,
    progress_cb: Callable[[int, int], None] | None = None,
    match_cb: Callable[[dict[str, object]], None] | None = None,
    should_cancel_cb: Callable[[], bool] | None = None,
) -> list[dict[str, object]]:
    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise ValueError("search_retcon_candidates expects timezone-aware datetimes")
    if end_dt < start_dt:
        raise ValueError("end_dt must be on or after start_dt")
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")

    required = {
        body: sign
        for body, sign in required_signs.items()
        if body in RETCON_BODIES and sign in ZODIAC_NAMES
    }
    if not required:
        return []

    search_windows = _candidate_search_windows(
        start_dt,
        end_dt,
        required,
        lat,
        lon,
        should_cancel_cb,
    )
    if not search_windows:
        return []

    step = dt.timedelta(minutes=step_minutes)
    total = sum(int((window_end - window_start) // step) + 1 for window_start, window_end in search_windows)

    results: list[dict[str, object]] = []
    index = 0
    for window_start, window_end in search_windows:
        current = window_start
        while current <= window_end and len(results) < max_results:
            if should_cancel_cb is not None and should_cancel_cb():
                return results
            positions = planetary_positions(current, lat, lon)
            is_match = True
            matched_positions: dict[str, float] = {}
            for body, expected_sign in required.items():
                lon_value = positions.get(body)
                if lon_value is None:
                    is_match = False
                    break
                if zodiac_sign_for_longitude(lon_value) != expected_sign:
                    is_match = False
                    break
                matched_positions[body] = float(lon_value)

            if is_match:
                match = {
                    "datetime": current,
                    "positions": matched_positions,
                }
                results.append(match)
                if match_cb is not None:
                    match_cb(match)

            index += 1
            if progress_cb is not None and total > 0:
                progress_cb(index, total)
            current += step

    return results