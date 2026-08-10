"""Pure calculation model for Chart Editor fine-tune hourly scans.

The broad Time Sensitivity scan answers how much a chart changes over a day.
This module instead produces a chronological micro ephemeris for one hour.
It intentionally has no Qt dependency so calculation can run in a worker.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Literal

from ephemeraldaddy.analysis.time_sensitivity import _get_nakshatra
from ephemeraldaddy.core.aspect_display import display_aspect_key
from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.human_design_system import calculate_human_design
from ephemeraldaddy.core.interpretations import PLANET_ORDER, ZODIAC_NAMES, aspect_orb_factor


class TransitionSection(StrEnum):
    SIGN_CHANGES = "Sign Changes"
    HOUSE_CHANGES = "House Changes"
    ASPECT_CHANGES = "Aspect Changes"
    NAKSHATRA_CHANGES = "Nakshatra Changes"
    HD_GATE_LINE_CHANGES = "HD Gate/Line Changes"


@dataclass(frozen=True)
class FineTuneHourlyScanRequest:
    """UID-first request for a single local-clock hour."""

    chart_uid: str
    start_hour: int
    resolution_minutes: Literal[1, 5]
    refine_changed_brackets: bool = True

    def __post_init__(self) -> None:
        if not self.chart_uid.strip():
            raise ValueError("Fine Tune Hourly Scan requires a chart UID.")
        if not 0 <= self.start_hour <= 23:
            raise ValueError("Fine Tune Hourly Scan hour must be between 0 and 23.")
        if self.resolution_minutes not in (1, 5):
            raise ValueError("Fine Tune Hourly Scan resolution must be 1 or 5 minutes.")


AspectKey = tuple[tuple[str, str], str]


@dataclass(frozen=True)
class FineTuneSnapshot:
    minute_offset: int
    time_label: str
    body_signs: Mapping[str, str]
    angle_signs: Mapping[str, str]
    cusp_signs: Mapping[int, str]
    body_houses: Mapping[str, int]
    relevant_aspects: Mapping[AspectKey, float]
    nakshatras: Mapping[str, str]
    hd_gate_lines: Mapping[tuple[str, str], tuple[int, int]]


@dataclass(frozen=True)
class FineTuneTransition:
    minute_offset: int
    time_label: str
    section: TransitionSection
    subject: str
    previous_value: str
    current_value: str
    status: str = "changed"


@dataclass(frozen=True)
class FineTuneHourlyScanResult:
    chart_uid: str
    start_hour: int
    resolution_minutes: int
    displayed_sample_count: int
    refined_sample_count: int
    uses_houses: bool
    transitions: tuple[FineTuneTransition, ...]
    warnings: tuple[str, ...] = ()


def fine_tune_hour_sample_minutes(resolution_minutes: Literal[1, 5]) -> tuple[int, ...]:
    """Return displayed sample offsets for the half-open interval ``[hour, hour+1)``."""
    if resolution_minutes not in (1, 5):
        raise ValueError("Fine Tune Hourly Scan resolution must be 1 or 5 minutes.")
    return tuple(range(0, 60, resolution_minutes))


def _sign(longitude: float) -> str:
    return ZODIAC_NAMES[int((float(longitude) % 360.0) // 30.0)]


def _house_for_longitude(cusps: Sequence[float], longitude: float) -> int | None:
    if len(cusps) < 12:
        return None
    value = float(longitude) % 360.0
    for index, start in enumerate(cusps[:12]):
        end = float(cusps[(index + 1) % 12]) % 360.0
        start = float(start) % 360.0
        if start <= end:
            inside = start <= value < end
        else:
            inside = value >= start or value < end
        if inside:
            return index + 1
    return None


def _snapshot(
    chart: Any,
    minute_offset: int,
    *,
    uses_houses: bool,
) -> FineTuneSnapshot:
    positions = getattr(chart, "positions", {}) or {}
    angle_names = frozenset({"AS", "DS", "MC", "IC"})
    body_signs = {
        body: _sign(positions[body])
        for body in PLANET_ORDER
        if body in positions and body not in angle_names
    }
    angle_signs = (
        {angle: _sign(positions[angle]) for angle in angle_names if angle in positions}
        if uses_houses
        else {}
    )
    houses = tuple(getattr(chart, "houses", ()) or ()) if uses_houses else ()
    cusp_signs = {index + 1: _sign(cusp) for index, cusp in enumerate(houses[:12])}
    body_houses = {
        body: house
        for body in body_signs
        if (house := _house_for_longitude(houses, positions[body])) is not None
    }

    relevant_aspects: dict[AspectKey, float] = {}
    for aspect in getattr(chart, "aspects", ()) or ():
        key = display_aspect_key(
            aspect,
            use_houses=uses_houses,
            known_positions=positions,
        )
        if key is None:
            continue
        factor = float(aspect_orb_factor(dict(aspect)))
        if factor > 0.0:
            relevant_aspects[key] = factor

    nakshatras = {
        body: _get_nakshatra(float(positions[body]))
        for body in body_signs
        if body in positions
    }
    hd = calculate_human_design(chart)
    hd_gate_lines = {
        (activation.side, activation.body): (int(activation.gate), int(activation.line))
        for activation in (*hd.personality_activations, *hd.design_activations)
    }
    return FineTuneSnapshot(
        minute_offset=minute_offset,
        time_label=_time_label(chart),
        body_signs=body_signs,
        angle_signs=angle_signs,
        cusp_signs=cusp_signs,
        body_houses=body_houses,
        relevant_aspects=relevant_aspects,
        nakshatras=nakshatras,
        hd_gate_lines=hd_gate_lines,
    )


def _time_label(chart: Any) -> str:
    value = getattr(chart, "dt", None)
    if not isinstance(value, datetime):
        value = getattr(chart, "dt_local", None)
    if not isinstance(value, datetime):
        raise ValueError("Fine Tune Hourly Scan requires chart datetime metadata.")
    return value.strftime("%H:%M")


def _variant_at(source: Any, moment: datetime) -> Chart:
    variant = Chart(
        getattr(source, "name", "Hypothetical time"),
        moment,
        float(getattr(source, "lat")),
        float(getattr(source, "lon")),
        tz=getattr(source, "_explicit_tz", None),
        alias=getattr(source, "alias", None),
        from_whence=getattr(source, "from_whence", None),
    )
    variant.birthtime_unknown = False
    variant.retcon_time_used = False
    variant.chart_uid = str(getattr(source, "chart_uid", "") or "")
    return variant


def _mapping_changes(
    previous: Mapping[Any, Any],
    current: Mapping[Any, Any],
    *,
    snapshot: FineTuneSnapshot,
    section: TransitionSection,
    label: Callable[[Any], str] = str,
) -> list[FineTuneTransition]:
    changes: list[FineTuneTransition] = []
    for key in sorted(previous.keys() & current.keys(), key=str):
        if previous[key] == current[key]:
            continue
        changes.append(
            FineTuneTransition(
                minute_offset=snapshot.minute_offset,
                time_label=snapshot.time_label,
                section=section,
                subject=label(key),
                previous_value=str(previous[key]),
                current_value=str(current[key]),
            )
        )
    return changes


def transitions_between(
    previous: FineTuneSnapshot, current: FineTuneSnapshot
) -> tuple[FineTuneTransition, ...]:
    changes = _mapping_changes(
        previous.body_signs,
        current.body_signs,
        snapshot=current,
        section=TransitionSection.SIGN_CHANGES,
    )
    changes.extend(
        _mapping_changes(
            previous.angle_signs,
            current.angle_signs,
            snapshot=current,
            section=TransitionSection.HOUSE_CHANGES,
        )
    )
    changes.extend(
        _mapping_changes(
            previous.cusp_signs,
            current.cusp_signs,
            snapshot=current,
            section=TransitionSection.HOUSE_CHANGES,
            label=lambda house: f"H{house} cusp",
        )
    )
    changes.extend(
        _mapping_changes(
            previous.body_houses,
            current.body_houses,
            snapshot=current,
            section=TransitionSection.HOUSE_CHANGES,
            label=lambda body: f"{body} house",
        )
    )

    old_aspects = previous.relevant_aspects
    new_aspects = current.relevant_aspects
    for key in sorted(old_aspects.keys() - new_aspects.keys(), key=str):
        changes.append(_aspect_transition(current, key, "relevant", "moved out of relevance"))
    for key in sorted(new_aspects.keys() - old_aspects.keys(), key=str):
        changes.append(_aspect_transition(current, key, "not relevant", "moved into relevance"))

    changes.extend(
        _mapping_changes(
            previous.nakshatras,
            current.nakshatras,
            snapshot=current,
            section=TransitionSection.NAKSHATRA_CHANGES,
        )
    )
    for key in sorted(previous.hd_gate_lines.keys() & current.hd_gate_lines.keys()):
        old_gate, old_line = previous.hd_gate_lines[key]
        new_gate, new_line = current.hd_gate_lines[key]
        if (old_gate, old_line) == (new_gate, new_line):
            continue
        side, body = key
        changes.append(
            FineTuneTransition(
                minute_offset=current.minute_offset,
                time_label=current.time_label,
                section=TransitionSection.HD_GATE_LINE_CHANGES,
                subject=f"{side.title()} {body}",
                previous_value=f"Gate {old_gate}.{old_line}",
                current_value=f"Gate {new_gate}.{new_line}",
            )
        )
    return tuple(changes)


def _aspect_transition(
    snapshot: FineTuneSnapshot,
    key: AspectKey,
    previous_value: str,
    current_value: str,
) -> FineTuneTransition:
    (left, right), aspect_type = key
    return FineTuneTransition(
        minute_offset=snapshot.minute_offset,
        time_label=snapshot.time_label,
        section=TransitionSection.ASPECT_CHANGES,
        subject=f"{left} {aspect_type.replace('_', ' ')} {right}",
        previous_value=previous_value,
        current_value=current_value,
        status=current_value,
    )


def compute_fine_tune_hourly_scan(
    chart: Any,
    request: FineTuneHourlyScanRequest,
    *,
    variant_factory: Callable[[Any, datetime], Any] = _variant_at,
) -> FineTuneHourlyScanResult:
    """Compute transitions for one hour, refining changed five-minute brackets."""
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip()
    if chart_uid != request.chart_uid:
        raise ValueError("Fine Tune Hourly Scan request does not match the active chart UID.")
    uses_houses = bool(chart_uses_houses(chart))
    cache: dict[int, FineTuneSnapshot] = {}
    warnings: list[str] = []

    source_dt = getattr(chart, "dt", None)
    if not isinstance(source_dt, datetime):
        source_dt = getattr(chart, "dt_local", None)
    if not isinstance(source_dt, datetime):
        raise ValueError("Fine Tune Hourly Scan requires a chart with a datetime.")
    hour_start = source_dt.replace(hour=request.start_hour, minute=0, second=0, microsecond=0)

    def sample(offset: int) -> FineTuneSnapshot:
        if offset in cache:
            return cache[offset]
        moment = hour_start + timedelta(minutes=offset)
        variant = variant_factory(chart, moment)
        cache[offset] = _snapshot(variant, offset, uses_houses=uses_houses)
        return cache[offset]

    displayed_offsets = fine_tune_hour_sample_minutes(request.resolution_minutes)
    coarse_offsets = (*displayed_offsets, 60)
    transitions: list[FineTuneTransition] = []
    for start, end in zip(coarse_offsets, coarse_offsets[1:]):
        before = sample(start)
        after = sample(end)
        coarse_changes = transitions_between(before, after)
        if not coarse_changes:
            continue
        if request.resolution_minutes == 5 and request.refine_changed_brackets:
            previous = before
            for offset in range(start + 1, end + 1):
                current = sample(offset)
                transitions.extend(transitions_between(previous, current))
                previous = current
        else:
            transitions.extend(coarse_changes)

    section_order = {section: index for index, section in enumerate(TransitionSection)}
    transitions.sort(
        key=lambda item: (item.minute_offset, section_order[item.section], item.subject)
    )
    return FineTuneHourlyScanResult(
        chart_uid=chart_uid,
        start_hour=request.start_hour,
        resolution_minutes=request.resolution_minutes,
        displayed_sample_count=len(displayed_offsets),
        refined_sample_count=max(0, len(cache) - len(set(coarse_offsets))),
        uses_houses=uses_houses,
        transitions=tuple(transitions),
        warnings=tuple(warnings),
    )
