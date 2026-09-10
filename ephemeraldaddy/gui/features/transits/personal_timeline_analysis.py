"""Pure analysis helpers for Personal Timeline life-event comparisons."""

from __future__ import annotations

import calendar
import datetime
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ephemeraldaddy.core.ephemeris import planetary_longitude


LIBRARY_OF_GHOSTS_SCHEMA = "library-of-ghosts.timeline-events"
SUPPORTED_LIBRARY_OF_GHOSTS_SCHEMA_VERSION = 1
DEFAULT_EXACT_PROXIMITY_DAYS = 30
DEFAULT_RANDOMIZATION_TRIALS = 2000
_EXACT_SCAN_STEP = datetime.timedelta(days=1)
_EXACT_REFINEMENT_STEPS = 18


@dataclass(frozen=True, slots=True)
class LifeEventAnchor:
    event_id: str
    name: str
    start: datetime.datetime
    end: datetime.datetime
    source_field: str
    precision: str

    @property
    def display_date(self) -> str:
        if self.precision == "year":
            return f"{self.start:%Y}"
        if self.precision == "month":
            return f"{self.start:%Y-%m}"
        if self.start == self.end:
            return f"{self.start:%Y-%m-%d %H:%M}"
        if self.start.date() == self.end.date():
            return f"{self.start:%Y-%m-%d}"
        return f"{self.start:%Y-%m-%d} – {self.end:%Y-%m-%d}"


@dataclass(frozen=True, slots=True)
class EventTransitResult:
    event: LifeEventAnchor
    transit_labels: tuple[str, ...]
    exact_hit_nearby: bool

    @property
    def overlaps_transit(self) -> bool:
        return bool(self.transit_labels)


@dataclass(frozen=True, slots=True)
class PersonalTimelineAnalysisResult:
    events: tuple[EventTransitResult, ...]
    analysis_start: datetime.datetime
    analysis_end: datetime.datetime
    background_exposure: float
    random_expected_hits: float
    exact_proximity_days: int
    randomization_trials: int

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def observed_hits(self) -> int:
        return sum(1 for item in self.events if item.overlaps_transit)

    @property
    def observed_rate(self) -> float:
        return self.observed_hits / self.event_count if self.event_count else 0.0

    @property
    def exact_proximity_hits(self) -> int:
        return sum(1 for item in self.events if item.exact_hit_nearby)

    @property
    def lift_vs_background(self) -> float | None:
        if self.background_exposure <= 0.0:
            return None
        return self.observed_rate / self.background_exposure


def _parse_iso(value: object, tzinfo: datetime.tzinfo) -> datetime.datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tzinfo)
    return parsed.astimezone(tzinfo)


def _fallback_partial_date_interval(
    value: dict[str, Any],
    tzinfo: datetime.tzinfo,
) -> tuple[datetime.datetime, datetime.datetime, str] | None:
    """Read older Library of Ghosts to_dict() output when explicit bounds are absent."""
    raw = str(value.get("raw") or "").strip()
    precision = str(value.get("precision") or "").strip().lower()
    if not raw:
        return None

    if precision == "year":
        match = re.fullmatch(r"\d{1,4}", raw)
        if not match:
            return None
        year = int(raw)
        return (
            datetime.datetime(year, 1, 1, tzinfo=tzinfo),
            datetime.datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=tzinfo),
            "year",
        )

    if precision == "month":
        for pattern in ("%B %Y", "%b %Y", "%Y-%m", "%Y/%m"):
            try:
                parsed = datetime.datetime.strptime(raw, pattern)
            except ValueError:
                continue
            last_day = calendar.monthrange(parsed.year, parsed.month)[1]
            return (
                datetime.datetime(parsed.year, parsed.month, 1, tzinfo=tzinfo),
                datetime.datetime(
                    parsed.year,
                    parsed.month,
                    last_day,
                    23,
                    59,
                    59,
                    999999,
                    tzinfo=tzinfo,
                ),
                "month",
            )
        return None

    normalized = raw.replace("T", " ")
    patterns = (
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%d %B %Y %H:%M",
        "%d %b %Y %H:%M",
        "%B %d, %Y %H:%M",
        "%b %d, %Y %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    )
    for pattern in patterns:
        try:
            parsed = datetime.datetime.strptime(normalized, pattern).replace(tzinfo=tzinfo)
        except ValueError:
            continue
        if "%H:%M" in pattern or precision == "minute":
            return parsed, parsed, "minute"
        return (
            parsed,
            parsed.replace(hour=23, minute=59, second=59, microsecond=999999),
            precision or "day",
        )
    return None


def _event_date_interval(
    event_date: object,
    tzinfo: datetime.tzinfo,
) -> tuple[datetime.datetime, datetime.datetime, str] | None:
    if not isinstance(event_date, dict) or bool(event_date.get("unknown")):
        return None
    value = event_date.get("value")
    if not isinstance(value, dict):
        return None

    earliest = _parse_iso(value.get("earliest"), tzinfo)
    latest = _parse_iso(value.get("latest"), tzinfo)
    precision = str(value.get("precision") or "").strip().lower() or "unknown"
    if earliest is not None and latest is not None and latest >= earliest:
        return earliest, latest, precision
    return _fallback_partial_date_interval(value, tzinfo)


def event_anchor_from_dict(
    event: dict[str, Any],
    tzinfo: datetime.tzinfo,
) -> LifeEventAnchor | None:
    """Prefer peak, then begin, then end as the event's analytical anchor.

    A long event's full begin-to-end span would create its own opportunity-density
    problem. Peak is therefore the strongest anchor when supplied; otherwise we
    retain the uncertainty interval of the best available dated field.
    """
    for field in ("peak", "begin", "end"):
        interval = _event_date_interval(event.get(field), tzinfo)
        if interval is None:
            continue
        start, end, precision = interval
        return LifeEventAnchor(
            event_id=str(event.get("id") or ""),
            name=str(event.get("name") or "Untitled event"),
            start=start,
            end=end,
            source_field=field,
            precision=precision,
        )
    return None


def load_life_event_json(path: Path, tzinfo: datetime.tzinfo) -> list[LifeEventAnchor]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        schema = payload.get("schema")
        if schema not in (None, LIBRARY_OF_GHOSTS_SCHEMA):
            raise ValueError(f"Unsupported timeline JSON schema: {schema}")
        version = payload.get("schema_version")
        if version not in (None, SUPPORTED_LIBRARY_OF_GHOSTS_SCHEMA_VERSION):
            raise ValueError(
                f"Unsupported Library of Ghosts timeline schema version: {version}"
            )
        events = payload.get("events")
    else:
        events = payload
    if not isinstance(events, list):
        raise ValueError("Expected an event list or an object containing an 'events' list.")

    anchors = [
        anchor
        for item in events
        if isinstance(item, dict)
        if (anchor := event_anchor_from_dict(item, tzinfo)) is not None
    ]
    if not anchors:
        raise ValueError("The JSON contains no events with usable peak, begin, or end dates.")
    return anchors


def intervals_overlap(
    first_start: datetime.datetime,
    first_end: datetime.datetime,
    second_start: datetime.datetime,
    second_end: datetime.datetime,
) -> bool:
    return first_start <= second_end and second_start <= first_end


def merged_transit_intervals(
    windows: Iterable[Any],
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    clipped: list[tuple[datetime.datetime, datetime.datetime]] = []
    for window in windows:
        left = max(start, window.start)
        right = min(end, window.end)
        if right >= left:
            clipped.append((left, right))
    clipped.sort(key=lambda item: item[0])

    merged: list[list[datetime.datetime]] = []
    for left, right in clipped:
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        elif right > merged[-1][1]:
            merged[-1][1] = right
    return [(left, right) for left, right in merged]


def covered_fraction(
    intervals: Iterable[tuple[datetime.datetime, datetime.datetime]],
    start: datetime.datetime,
    end: datetime.datetime,
) -> float:
    total = max(0.0, (end - start).total_seconds())
    if total <= 0.0:
        return 0.0
    covered = sum(max(0.0, (right - left).total_seconds()) for left, right in intervals)
    return min(1.0, covered / total)


def _known_death_datetime(chart: Any, tzinfo: datetime.tzinfo) -> datetime.datetime | None:
    if not bool(getattr(chart, "is_deceased", False)):
        return None
    try:
        year = int(getattr(chart, "death_year", None) or 0)
    except (TypeError, ValueError):
        return None
    if year <= 0:
        return None
    try:
        month = int(getattr(chart, "death_month", None) or 0)
    except (TypeError, ValueError):
        month = 0
    try:
        day = int(getattr(chart, "death_day", None) or 0)
    except (TypeError, ValueError):
        day = 0
    if not 1 <= month <= 12:
        month, day = 12, 31
    else:
        last_day = calendar.monthrange(year, month)[1]
        if not 1 <= day <= last_day:
            day = last_day
    return datetime.datetime(year, month, day, 23, 59, 59, tzinfo=tzinfo)


def analysis_lifespan(chart: Any) -> tuple[datetime.datetime, datetime.datetime]:
    birth = getattr(chart, "dt", None)
    if not isinstance(birth, datetime.datetime) or birth.tzinfo is None:
        raise ValueError("The selected chart needs a timezone-aware birth datetime.")
    death = _known_death_datetime(chart, birth.tzinfo)
    end = death or datetime.datetime.now(tz=birth.tzinfo)
    if end <= birth:
        raise ValueError("The chart does not have a positive elapsed lifespan to analyze.")
    return birth, end


def _event_transit_windows(event: LifeEventAnchor, windows: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(
        window
        for window in windows
        if intervals_overlap(event.start, event.end, window.start, window.end)
    )


def _signed_longitude_delta(longitude: float, target: float) -> float:
    return ((float(longitude) - float(target) + 180.0) % 360.0) - 180.0


def _exact_targets(transit: Any) -> tuple[float, ...]:
    natal = float(transit.natal_longitude) % 360.0
    angle = float(transit.aspect_angle) % 360.0
    first = (natal + angle) % 360.0
    second = (natal - angle) % 360.0
    return (first,) if abs(_signed_longitude_delta(first, second)) < 1e-9 else (first, second)


def _refine_exact_crossing(
    left: datetime.datetime,
    right: datetime.datetime,
    body: str,
    target: float,
) -> datetime.datetime | None:
    left_lon = planetary_longitude(left, body)
    right_lon = planetary_longitude(right, body)
    if left_lon is None or right_lon is None:
        return None
    left_delta = _signed_longitude_delta(float(left_lon), target)
    right_delta = _signed_longitude_delta(float(right_lon), target)
    if abs(left_delta) < 1e-7:
        return left
    if abs(right_delta) < 1e-7:
        return right
    if left_delta * right_delta > 0 or abs(left_delta - right_delta) >= 180.0:
        return None

    for _ in range(_EXACT_REFINEMENT_STEPS):
        middle = left + ((right - left) / 2)
        longitude = planetary_longitude(middle, body)
        if longitude is None:
            return None
        middle_delta = _signed_longitude_delta(float(longitude), target)
        if abs(middle_delta) < 1e-7:
            return middle
        if left_delta * middle_delta <= 0 and abs(left_delta - middle_delta) < 180.0:
            right = middle
            right_delta = middle_delta
        else:
            left = middle
            left_delta = middle_delta
    return left + ((right - left) / 2)


def window_has_exact_hit_between(
    window: Any,
    start: datetime.datetime,
    end: datetime.datetime,
) -> bool:
    left_bound = max(window.start, start)
    right_bound = min(window.end, end)
    if right_bound < left_bound:
        return False

    body = str(window.transit.transiting_body)
    for target in _exact_targets(window.transit):
        previous = left_bound
        previous_lon = planetary_longitude(previous, body)
        if previous_lon is None:
            continue
        previous_delta = _signed_longitude_delta(float(previous_lon), target)
        if abs(previous_delta) < 1e-7:
            return True

        while previous < right_bound:
            current = min(right_bound, previous + _EXACT_SCAN_STEP)
            current_lon = planetary_longitude(current, body)
            if current_lon is None:
                break
            current_delta = _signed_longitude_delta(float(current_lon), target)
            if abs(current_delta) < 1e-7:
                return True
            if (
                previous_delta * current_delta < 0
                and abs(previous_delta - current_delta) < 180.0
                and _refine_exact_crossing(previous, current, body, target) is not None
            ):
                return True
            previous = current
            previous_delta = current_delta
    return False


def event_has_exact_hit_nearby(
    event: LifeEventAnchor,
    windows: Iterable[Any],
    *,
    proximity_days: int,
) -> bool:
    margin = datetime.timedelta(days=max(0, int(proximity_days)))
    start = event.start - margin
    end = event.end + margin
    for window in windows:
        if intervals_overlap(start, end, window.start, window.end) and window_has_exact_hit_between(
            window, start, end
        ):
            return True
    return False


def randomized_expected_hits(
    events: Iterable[LifeEventAnchor],
    merged_intervals: list[tuple[datetime.datetime, datetime.datetime]],
    analysis_start: datetime.datetime,
    analysis_end: datetime.datetime,
    *,
    trials: int,
    seed_text: str,
) -> float:
    events = tuple(events)
    if not events or trials <= 0:
        return 0.0
    span_seconds = max(0.0, (analysis_end - analysis_start).total_seconds())
    if span_seconds <= 0.0:
        return 0.0

    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    total_hits = 0
    for _ in range(trials):
        trial_hits = 0
        for event in events:
            duration = max(0.0, (event.end - event.start).total_seconds())
            max_offset = max(0.0, span_seconds - duration)
            offset = rng.random() * max_offset if max_offset > 0 else 0.0
            random_start = analysis_start + datetime.timedelta(seconds=offset)
            random_end = min(
                analysis_end,
                random_start + datetime.timedelta(seconds=duration),
            )
            if any(
                intervals_overlap(random_start, random_end, left, right)
                for left, right in merged_intervals
            ):
                trial_hits += 1
        total_hits += trial_hits
    return total_hits / float(trials)


def analyze_personal_timeline(
    chart_uid: str,
    chart: Any,
    transit_windows: Iterable[Any],
    life_events: Iterable[LifeEventAnchor],
    *,
    exact_proximity_days: int = DEFAULT_EXACT_PROXIMITY_DAYS,
    randomization_trials: int = DEFAULT_RANDOMIZATION_TRIALS,
) -> PersonalTimelineAnalysisResult:
    analysis_start, analysis_end = analysis_lifespan(chart)
    windows = tuple(
        window
        for window in transit_windows
        if intervals_overlap(window.start, window.end, analysis_start, analysis_end)
    )
    events = tuple(
        event
        for event in life_events
        if intervals_overlap(event.start, event.end, analysis_start, analysis_end)
    )
    merged = merged_transit_intervals(windows, analysis_start, analysis_end)
    exposure = covered_fraction(merged, analysis_start, analysis_end)

    event_results: list[EventTransitResult] = []
    for event in events:
        matching_windows = _event_transit_windows(event, windows)
        labels = tuple(sorted({window.transit.label for window in matching_windows}))
        exact_nearby = event_has_exact_hit_nearby(
            event,
            windows,
            proximity_days=exact_proximity_days,
        )
        event_results.append(
            EventTransitResult(
                event=event,
                transit_labels=labels,
                exact_hit_nearby=exact_nearby,
            )
        )

    expected = randomized_expected_hits(
        events,
        merged,
        analysis_start,
        analysis_end,
        trials=randomization_trials,
        seed_text=f"{str(chart_uid).upper()}:{len(events)}:{len(windows)}:{exact_proximity_days}",
    )
    return PersonalTimelineAnalysisResult(
        events=tuple(event_results),
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        background_exposure=exposure,
        random_expected_hits=expected,
        exact_proximity_days=int(exact_proximity_days),
        randomization_trials=int(randomization_trials),
    )
