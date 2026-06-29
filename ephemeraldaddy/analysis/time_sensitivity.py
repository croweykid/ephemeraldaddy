"""Birth-time / rectification sensitivity scanning helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable

from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.db import DB_DIR
from ephemeraldaddy.core.human_design_system import calculate_human_design
from ephemeraldaddy.core.interpretations import (
    NAKSHATRA_RANGES,
    PLANET_ORDER,
    ZODIAC_NAMES,
)

TIME_SENSITIVITY_ALGORITHM_VERSION = "time-sensitivity-v6"
TIME_SENSITIVITY_DB_PATH = DB_DIR / "time_sensitivity.db"
NUMERIC_GROUPS = (
    "dominant_planet_weights",
    "dominant_sign_weights",
    "dominant_house_weights",
    "dominant_element_weights",
    "dominant_mode_weights",
    "dominant_nakshatra_weights",
)


@dataclass(frozen=True)
class TimeSensitivityConfig:
    interval_minutes: int = 30
    include_day_end: bool = True
    baseline_time: str | None = None
    boundary_refinement: bool = False


@dataclass(frozen=True)
class TimeSensitivityResult:
    chart_uid: str
    chart_name: str
    birth_date_key: str
    algorithm_version: str
    computed_at: str
    config: dict[str, Any]
    sample_count: int
    baseline_time: str
    overall: dict[str, Any]
    numeric_ranges: dict[str, dict[str, dict[str, Any]]]
    human_design: dict[str, Any]
    stable: list[str]
    variable: list[str]
    warnings: list[str]


def birth_date_key_for_chart(chart: Any) -> str:
    """Return the Time Sensitivity storage key for a chart birth date."""
    dt = getattr(chart, "dt", None)
    if not isinstance(dt, datetime):
        dt = getattr(chart, "dt_local", None)
    if isinstance(dt, datetime):
        return dt.strftime("%m-%d-%Y")
    birth_date = getattr(chart, "birth_date", None)
    if isinstance(birth_date, date):
        return birth_date.strftime("%m-%d-%Y")
    return ""


def scan_times(
    interval_minutes: int = 30, *, include_day_end: bool = True
) -> list[tuple[int, int]]:
    """Return local clock times sampled through the birth day."""
    interval = max(1, int(interval_minutes or 30))
    times: list[tuple[int, int]] = []
    for total_minutes in range(0, 24 * 60, interval):
        times.append((total_minutes // 60, total_minutes % 60))
    if include_day_end and times[-1] != (23, 59):
        times.append((23, 59))
    return times


def _time_label(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _variant_chart(source: Any, hour: int, minute: int) -> Chart:
    source_dt = getattr(source, "dt", None)
    if not isinstance(source_dt, datetime):
        source_dt = getattr(source, "dt_local", None)
    if not isinstance(source_dt, datetime):
        raise ValueError("Time Sensitivity requires a chart with a datetime.")
    dt_variant = source_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    variant = Chart(
        getattr(source, "name", "Hypothetical time"),
        dt_variant,
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


def _numeric_snapshot(chart: Chart) -> dict[str, dict[str, float]]:
    from ephemeraldaddy.gui.features.charts.metrics import (
        calculate_dominant_element_weights,
        calculate_dominant_house_weights,
        calculate_dominant_nakshatra_weights,
        calculate_dominant_planet_weights,
        calculate_dominant_sign_weights,
        calculate_mode_weights,
    )

    return {
        "dominant_planet_weights": {
            str(k): float(v)
            for k, v in calculate_dominant_planet_weights(chart).items()
        },
        "dominant_sign_weights": {
            str(k): float(v) for k, v in calculate_dominant_sign_weights(chart).items()
        },
        "dominant_house_weights": {
            str(k): float(v) for k, v in calculate_dominant_house_weights(chart).items()
        },
        "dominant_element_weights": {
            str(k): float(v)
            for k, v in calculate_dominant_element_weights(chart).items()
        },
        "dominant_mode_weights": {
            str(k): float(v) for k, v in calculate_mode_weights(chart).items()
        },
        "dominant_nakshatra_weights": {
            str(k): float(v)
            for k, v in calculate_dominant_nakshatra_weights(chart).items()
        },
    }


def _hd_snapshot(chart: Chart) -> dict[str, Any]:
    result = calculate_human_design(chart)
    activations = (*result.personality_activations, *result.design_activations)
    return {
        "gates": sorted(int(gate) for gate in result.active_gates),
        "lines": sorted(f"{int(a.gate)}.{int(a.line)}" for a in activations),
        "channels": sorted(
            f"{min(a, b)}-{max(a, b)}" for a, b, *_ in result.defined_channels
        ),
        "type": str(result.hd_type or ""),
        "profile": str(result.profile or ""),
    }


ANGLE_SIGN_CONFIDENCE_KEYS = ("AS", "MC", "DS", "IC")
BODY_SIGN_CONFIDENCE_KEYS = tuple(
    body for body in PLANET_ORDER if body not in ANGLE_SIGN_CONFIDENCE_KEYS
)


def _categorical_snapshot(chart: Chart) -> dict[str, Any]:
    positions = getattr(chart, "positions", {}) or {}
    body_signs = {
        key: _sign_for_longitude(float(positions[key]))
        for key in BODY_SIGN_CONFIDENCE_KEYS
        if key in positions
    }
    angle_signs = {
        key: _sign_for_longitude(float(positions[key]))
        for key in ANGLE_SIGN_CONFIDENCE_KEYS
        if key in positions
    }
    return {
        "Sun": body_signs.get("Sun", ""),
        "Nakshatra": (
            _get_nakshatra(float(positions["Moon"])) if "Moon" in positions else ""
        ),
        "AS": angle_signs.get("AS", ""),
        "body_signs": body_signs,
        "angle_signs": angle_signs,
    }


def _sign_for_longitude(lon: float) -> str:
    return ZODIAC_NAMES[int((float(lon) % 360.0) // 30)]


def _get_nakshatra(lon: float) -> str:
    lon = float(lon) % 360.0
    for (
        name,
        start_sign,
        start_deg,
        start_min,
        end_sign,
        end_deg,
        end_min,
    ) in NAKSHATRA_RANGES:
        start = _sign_degrees(start_sign, start_deg, start_min)
        end = _sign_degrees(end_sign, end_deg, end_min)
        start_f = float(start) % 360.0
        end_f = float(end) % 360.0
        if start_f <= end_f:
            if start_f <= lon < end_f:
                return str(name)
        elif lon >= start_f or lon < end_f:
            return str(name)
    return str(NAKSHATRA_RANGES[-1][0])


def _sign_degrees(sign: str, deg: int, minutes: int) -> float:
    return (ZODIAC_NAMES.index(sign) * 30.0) + float(deg) + (float(minutes) / 60.0)


def _percent_delta(range_delta: float, baseline: float) -> float:
    denominator = abs(float(baseline))
    if denominator <= 1e-9:
        return 0.0 if abs(range_delta) <= 1e-9 else 100.0
    return (float(range_delta) / denominator) * 100.0


def _variability_label(percent_delta: float) -> str:
    """Return a plain-language label for a percent-delta spread."""
    if percent_delta < 5.0:
        return "minimal"
    if percent_delta < 15.0:
        return "minor"
    if percent_delta < 35.0:
        return "medium"
    if percent_delta < 75.0:
        return "high"
    return "extreme"


def _span_label(start_time: str, end_time: str) -> str:
    return f"{start_time}–{end_time}"


def _matching_spans(
    values: list[tuple[str, float]], predicate: Callable[[float], bool]
) -> list[str]:
    spans: list[str] = []
    start: str | None = None
    previous_time: str | None = None
    for time, value in values:
        if predicate(value):
            if start is None:
                start = time
            previous_time = time
        elif start is not None and previous_time is not None:
            spans.append(_span_label(start, previous_time))
            start = None
            previous_time = None
    if start is not None and previous_time is not None:
        spans.append(_span_label(start, previous_time))
    return spans


def _transition_windows(values: list[tuple[str, float]]) -> list[str]:
    windows: list[str] = []
    for (previous_time, previous_value), (time, value) in zip(
        values, values[1:], strict=False
    ):
        if abs(value - previous_value) > 1e-9:
            windows.append(_span_label(previous_time, time))
    return windows


def _aggregate_numeric(
    samples: list[dict[str, Any]], baseline: dict[str, dict[str, float]]
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, float]]:
    ranges: dict[str, dict[str, dict[str, Any]]] = {}
    group_deltas: dict[str, float] = {}
    for group in NUMERIC_GROUPS:
        keys = sorted(
            {key for sample in samples for key in sample["numeric"].get(group, {})}
            | set(baseline.get(group, {}))
        )
        group_ranges: dict[str, dict[str, Any]] = {}
        max_group_delta = 0.0
        for key in keys:
            values = [
                (sample["time"], float(sample["numeric"].get(group, {}).get(key, 0.0)))
                for sample in samples
            ]
            min_value = min(value for _time, value in values)
            max_value = max(value for _time, value in values)
            base_value = float(baseline.get(group, {}).get(key, 0.0))
            range_delta = max_value - min_value
            max_increase = max_value - base_value
            max_decrease = min_value - base_value
            baseline_delta = max(abs(max_increase), abs(max_decrease))
            pct = _percent_delta(baseline_delta, base_value)
            max_increase_percent = _percent_delta(max_increase, base_value)
            max_decrease_percent = _percent_delta(max_decrease, base_value)
            variability_percent = max_increase_percent - max_decrease_percent
            max_group_delta = max(max_group_delta, abs(pct))
            present_times = [time for time, value in values if value > 0]
            peak_times = [time for time, value in values if value == max_value]
            trough_times = [time for time, value in values if value == min_value]
            group_ranges[key] = {
                "min": round(min_value, 6),
                "max": round(max_value, 6),
                "baseline": round(base_value, 6),
                "delta": round(range_delta, 6),
                "baseline_delta": round(baseline_delta, 6),
                "max_increase_from_baseline": round(max_increase, 6),
                "max_decrease_from_baseline": round(max_decrease, 6),
                "percent_delta": round(pct, 2),
                "max_increase_percent": round(
                    _percent_delta(max_increase, base_value), 2
                ),
                "max_decrease_percent": round(
                    _percent_delta(max_decrease, base_value), 2
                ),
                "label": _variability_label(abs(pct)),
                "times_at_min": trough_times,
                "times_at_max": peak_times,
                "peak_times": peak_times,
                "trough_times": trough_times,
                "present_spans": _matching_spans(values, lambda value: value > 0.0),
                "peak_spans": _matching_spans(values, lambda value: value == max_value),
                "trough_spans": _matching_spans(
                    values, lambda value: value == min_value
                ),
                "transition_windows": _transition_windows(values),
                "appears_after": (
                    present_times[0] if min_value == 0.0 and present_times else None
                ),
            }
        ranges[group] = group_ranges
        group_deltas[group] = round(max_group_delta, 2)
    return ranges, group_deltas


def _presence_summary(samples: list[dict[str, Any]], key: str) -> dict[str, Any]:
    sample_count = len(samples)
    universe = sorted(
        {item for sample in samples for item in sample["human_design"].get(key, [])}
    )
    counts = {
        str(item): sum(
            1 for sample in samples if item in sample["human_design"].get(key, [])
        )
        for item in universe
    }
    return {
        "always": [item for item, count in counts.items() if count == sample_count],
        "sometimes": [
            item for item, count in counts.items() if 0 < count < sample_count
        ],
        "presence_counts": counts,
        "sample_count": sample_count,
    }


def _distribution(samples: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sample in samples:
        value = str(sample["human_design"].get(key, "") or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _cumulative_weight_likelihoods(
    samples: list[dict[str, Any]], group: str
) -> dict[str, dict[str, Any]]:
    """Average every factor's weight across samples and express it as a relative share."""
    sample_count = len(samples)
    totals: dict[str, float] = {}
    for sample in samples:
        for key, value in sample["numeric"].get(group, {}).items():
            totals[str(key)] = totals.get(str(key), 0.0) + float(value)
    grand_total = sum(totals.values())
    if grand_total <= 0.0:
        return {}
    return {
        key: {
            "average_weight": round(total / sample_count, 6) if sample_count else 0.0,
            "percent": round((total / grand_total) * 100.0, 2),
        }
        for key, total in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        if total > 0.0
    }


def _dominance_likelihoods(
    samples: list[dict[str, Any]], group: str
) -> dict[str, dict[str, Any]]:
    """Count which weighted factor is dominant in each sampled chart."""
    counts: dict[str, float] = {}
    sample_count = len(samples)
    for sample in samples:
        weights = {
            str(key): float(value)
            for key, value in sample["numeric"].get(group, {}).items()
        }
        if not weights:
            continue
        max_value = max(weights.values())
        if max_value <= 0.0:
            continue
        dominant_keys = [
            key
            for key, value in weights.items()
            if abs(float(value) - max_value) <= 1e-9
        ]
        if not dominant_keys:
            continue
        split_count = 1.0 / len(dominant_keys)
        for key in dominant_keys:
            counts[key] = counts.get(key, 0.0) + split_count
    return {
        key: {
            "count": round(count, 4),
            "percent": (
                round((count / sample_count) * 100.0, 2) if sample_count else 0.0
            ),
        }
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    }


def _modal_stability(values: Iterable[str]) -> float:
    clean_values = [str(value) for value in values if str(value)]
    if not clean_values:
        return 0.0
    counts: dict[str, int] = {}
    for value in clean_values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts.values()) / len(clean_values)


def _average_factor_stability(
    samples: list[dict[str, Any]], category: str, keys: Iterable[str]
) -> float | None:
    scores = []
    for key in keys:
        values = [
            sample["categorical"].get(category, {}).get(key, "") for sample in samples
        ]
        if any(values):
            scores.append(_modal_stability(values))
    if not scores:
        return None
    return sum(scores) / len(scores)


def _dominance_confidence(overall: dict[str, Any]) -> float | None:
    dominance = overall.get("dominance_likelihoods", {})
    scores: list[float] = []
    for group in (
        "dominant_planet_weights",
        "dominant_sign_weights",
        "dominant_element_weights",
        "dominant_mode_weights",
        "dominant_nakshatra_weights",
    ):
        group_values = dominance.get(group, {})
        if group_values:
            scores.append(
                max(float(item.get("percent", 0.0)) for item in group_values.values())
                / 100.0
            )
    if not scores:
        return None
    return sum(scores) / len(scores)


def _group_delta_confidence(
    overall: dict[str, Any], groups: Iterable[str]
) -> float | None:
    group_deltas = overall.get("group_deltas", {})
    scores = [
        max(0.0, min(100.0, 100.0 - float(group_deltas[group]))) / 100.0
        for group in groups
        if group in group_deltas
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _presence_stability(summary: dict[str, Any]) -> float | None:
    universe = set(summary.get("always", [])) | set(summary.get("sometimes", []))
    if not universe:
        return None
    return len(summary.get("always", [])) / len(universe)


def _human_design_confidence(
    samples: list[dict[str, Any]], hd: dict[str, Any]
) -> float | None:
    scores: list[float] = []
    type_score = _modal_stability(
        sample["human_design"].get("type", "") for sample in samples
    )
    if type_score > 0.0:
        scores.append(type_score)
    profile_score = _modal_stability(
        sample["human_design"].get("profile", "") for sample in samples
    )
    if profile_score > 0.0:
        scores.append(profile_score)
    for key in ("gates", "channels", "lines"):
        presence_score = _presence_stability(hd.get(key, {}))
        if presence_score is not None:
            scores.append(presence_score)
    if not scores:
        return None
    return sum(scores) / len(scores)


def _ascertainment_confidence(
    samples: list[dict[str, Any]], overall: dict[str, Any], hd: dict[str, Any]
) -> dict[str, Any]:
    """Estimate how much useful chart information survives an unknown birth time."""
    components: list[tuple[str, float, float]] = []

    body_score = _average_factor_stability(
        samples, "body_signs", BODY_SIGN_CONFIDENCE_KEYS
    )
    if body_score is not None:
        components.append(("planetary sign stability", 0.45, body_score))

    angle_score = _average_factor_stability(
        samples, "angle_signs", ANGLE_SIGN_CONFIDENCE_KEYS
    )
    if angle_score is not None:
        components.append(("angle sign stability", 0.10, angle_score))

    zodiacal_score = _group_delta_confidence(
        overall,
        (
            "dominant_element_weights",
            "dominant_mode_weights",
            "dominant_nakshatra_weights",
        ),
    )
    if zodiacal_score is not None:
        components.append(("element/mode/nakshatra stability", 0.15, zodiacal_score))

    hd_score = _human_design_confidence(samples, hd)
    if hd_score is not None:
        components.append(("human design stability", 0.15, hd_score))

    dominance_score = _dominance_confidence(overall)
    if dominance_score is not None:
        components.append(("dominance consistency", 0.10, dominance_score))

    stability_score = (
        max(0.0, min(100.0, float(overall.get("stability_percent", 0.0)))) / 100.0
    )
    components.append(("weighted-score stability", 0.05, stability_score))

    total_weight = sum(weight for _name, weight, _score in components)
    confidence = (
        sum(weight * score for _name, weight, score in components) / total_weight
        if total_weight
        else 0.0
    )
    variable_body_count = sum(
        1
        for key in BODY_SIGN_CONFIDENCE_KEYS
        if len(
            {
                sample["categorical"].get("body_signs", {}).get(key, "")
                for sample in samples
                if sample["categorical"].get("body_signs", {}).get(key, "")
            }
        )
        > 1
    )
    return {
        "percent": round(max(0.0, min(100.0, confidence * 100.0)), 2),
        "components": {
            name: round(score * 100.0, 2) for name, _weight, score in components
        },
        "variable_body_sign_count": variable_body_count,
        "description": "Relative confidence in chart facts that remain ascertainable across sampled birth times.",
    }


def _top_group_deltas(group_deltas: dict[str, float]) -> tuple[list[str], list[str]]:
    ordered = sorted(group_deltas.items(), key=lambda item: item[1], reverse=True)
    most = [f"{name.replace('_', ' ')} ({delta:.2f}%)" for name, delta in ordered[:3]]
    least = [f"{name.replace('_', ' ')} ({delta:.2f}%)" for name, delta in ordered[-3:]]
    return most, least


def _baseline_time_for_chart(
    chart: Any, configured_baseline_time: str | None
) -> tuple[int, int, str, str]:
    if configured_baseline_time:
        hour, minute = (int(part) for part in configured_baseline_time.split(":", 1))
        return hour, minute, _time_label(hour, minute), "configured time"

    use_rectified_time = bool(getattr(chart, "retcon_time_used", False))
    if not chart_uses_houses(chart) and not use_rectified_time:
        return 12, 0, "12:00", "noon fallback"

    if use_rectified_time:
        dt = getattr(chart, "dt", None)
        fallback_hour = int(dt.hour) if isinstance(dt, datetime) else 12
        fallback_minute = int(dt.minute) if isinstance(dt, datetime) else 0
        hour = int(
            getattr(chart, "retcon_hour", fallback_hour)
            if getattr(chart, "retcon_hour", None) is not None
            else fallback_hour
        )
        minute = int(
            getattr(chart, "retcon_minute", fallback_minute)
            if getattr(chart, "retcon_minute", None) is not None
            else fallback_minute
        )
        return hour, minute, _time_label(hour, minute), "rectified time"

    dt = getattr(chart, "dt", None)
    if not isinstance(dt, datetime):
        dt = getattr(chart, "dt_local", None)
    if isinstance(dt, datetime):
        return (
            int(dt.hour),
            int(dt.minute),
            _time_label(int(dt.hour), int(dt.minute)),
            "current chart time",
        )
    return 12, 0, "12:00", "noon fallback"


def compute_time_sensitivity(
    chart: Any, config: TimeSensitivityConfig | None = None
) -> TimeSensitivityResult:
    """Compute sampled Time/Rectification Sensitivity ranges for one chart."""
    cfg = config or TimeSensitivityConfig()
    samples: list[dict[str, Any]] = []
    warnings: list[str] = []
    baseline_hour, baseline_minute, baseline_time, baseline_source = (
        _baseline_time_for_chart(chart, cfg.baseline_time)
    )
    baseline_chart = _variant_chart(chart, baseline_hour, baseline_minute)
    baseline_numeric = _numeric_snapshot(baseline_chart)

    for hour, minute in scan_times(
        cfg.interval_minutes, include_day_end=cfg.include_day_end
    ):
        label = _time_label(hour, minute)
        try:
            variant = _variant_chart(chart, hour, minute)
            numeric = _numeric_snapshot(variant)
            categorical = _categorical_snapshot(variant)
        except Exception as exc:  # keep user-visible scan failures localized
            warnings.append(f"{label}: {exc}")
            continue

        try:
            human_design = _hd_snapshot(variant)
        except Exception as exc:
            warnings.append(f"{label} Human Design skipped: {exc}")
            human_design = {
                "gates": [],
                "lines": [],
                "channels": [],
                "type": "",
                "profile": "",
            }

        samples.append(
            {
                "time": label,
                "numeric": numeric,
                "human_design": human_design,
                "categorical": categorical,
            }
        )

    if not samples:
        details = "; ".join(warnings[:5])
        suffix = f" First failures: {details}" if details else ""
        raise ValueError(
            f"Time Sensitivity could not produce any valid sampled charts.{suffix}"
        )

    numeric_ranges, group_deltas = _aggregate_numeric(samples, baseline_numeric)
    most_sensitive, least_sensitive = _top_group_deltas(group_deltas)
    max_delta = max(group_deltas.values(), default=0.0)
    stability = max(0.0, 100.0 - max_delta)

    categorical_sources = {
        "Sun sign": "Sun",
        "Moon nakshatra": "Nakshatra",
        "Ascendant": "AS",
    }
    categorical_values = {
        label: [sample["categorical"].get(source_key, "") for sample in samples]
        for label, source_key in categorical_sources.items()
    }
    stable = [
        f"{key}: stable all day ({values[0]})"
        for key, values in categorical_values.items()
        if values and len(set(values)) == 1 and values[0]
    ]
    variable = [
        f"{key}: {' / '.join(dict.fromkeys(v for v in values if v))}"
        for key, values in categorical_values.items()
        if len(set(v for v in values if v)) > 1
    ]

    hd = {
        "gates": _presence_summary(samples, "gates"),
        "lines": _presence_summary(samples, "lines"),
        "channels": _presence_summary(samples, "channels"),
        "type_distribution": _distribution(samples, "type"),
        "profile_distribution": _distribution(samples, "profile"),
    }
    if len(hd["type_distribution"]) == 1:
        stable.append(f"HD Type: {next(iter(hd['type_distribution']))} all day")
    else:
        variable.append("HD Type: " + " / ".join(hd["type_distribution"].keys()))

    overall = {
        "stability_percent": round(stability, 2),
        "max_total_change_from_baseline_percent": round(max_delta, 2),
        "most_sensitive": most_sensitive,
        "least_sensitive": least_sensitive,
        "group_deltas": group_deltas,
        "dominance_likelihoods": {
            group: _dominance_likelihoods(samples, group)
            for group in (
                "dominant_planet_weights",
                "dominant_sign_weights",
                "dominant_element_weights",
                "dominant_mode_weights",
                "dominant_nakshatra_weights",
            )
        },
        "cumulative_weight_likelihoods": {
            group: _cumulative_weight_likelihoods(samples, group)
            for group in (
                "dominant_planet_weights",
                "dominant_sign_weights",
                "dominant_element_weights",
                "dominant_mode_weights",
                "dominant_nakshatra_weights",
            )
        },
        "baseline_source": baseline_source,
    }
    overall["ascertainment_confidence"] = _ascertainment_confidence(
        samples, overall, hd
    )

    computed_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return TimeSensitivityResult(
        chart_uid=str(getattr(chart, "chart_uid", "") or ""),
        chart_name=str(getattr(chart, "name", "") or ""),
        birth_date_key=birth_date_key_for_chart(chart),
        algorithm_version=TIME_SENSITIVITY_ALGORITHM_VERSION,
        computed_at=computed_at,
        config=asdict(cfg),
        sample_count=len(samples),
        baseline_time=baseline_time,
        overall=overall,
        numeric_ranges=numeric_ranges,
        human_design=hd,
        stable=stable,
        variable=variable,
        warnings=warnings,
    )


def result_to_dict(result: TimeSensitivityResult) -> dict[str, Any]:
    return asdict(result)


def _config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ensure_time_sensitivity_db(path: Path = TIME_SENSITIVITY_DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chart_time_sensitivity_ranges (
                id INTEGER PRIMARY KEY,
                chart_uid TEXT NOT NULL,
                birth_date_key TEXT NOT NULL DEFAULT '',
                algorithm_version TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                config_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(chart_uid, algorithm_version, config_hash)
            )
            """)
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(chart_time_sensitivity_ranges)"
            ).fetchall()
        }
        if "birth_date_key" not in columns:
            conn.execute(
                "ALTER TABLE chart_time_sensitivity_ranges ADD COLUMN birth_date_key TEXT NOT NULL DEFAULT ''"
            )
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_time_sensitivity_birth_date_config
            ON chart_time_sensitivity_ranges(birth_date_key, algorithm_version, config_hash)
            WHERE birth_date_key != ''
            """)


def save_time_sensitivity_result(
    result: TimeSensitivityResult, path: Path = TIME_SENSITIVITY_DB_PATH
) -> None:
    ensure_time_sensitivity_db(path)
    payload = result_to_dict(result)
    config_json = json.dumps(result.config, sort_keys=True)
    result_json = json.dumps(payload, sort_keys=True)
    config_hash = _config_hash(result.config)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    storage_chart_uid = result.chart_uid or f"date:{result.birth_date_key}"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            DELETE FROM chart_time_sensitivity_ranges
            WHERE (birth_date_key != '' AND birth_date_key = ? AND algorithm_version = ? AND config_hash = ?)
               OR (chart_uid != '' AND chart_uid = ? AND algorithm_version = ? AND config_hash = ?)
            """,
            (
                result.birth_date_key,
                result.algorithm_version,
                config_hash,
                result.chart_uid,
                result.algorithm_version,
                config_hash,
            ),
        )
        conn.execute(
            """
            INSERT INTO chart_time_sensitivity_ranges (
                chart_uid, birth_date_key, algorithm_version, config_hash, config_json, result_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                storage_chart_uid,
                result.birth_date_key,
                result.algorithm_version,
                config_hash,
                config_json,
                result_json,
                now,
                now,
            ),
        )


def load_time_sensitivity_result_for_chart(
    chart: Any,
    config: TimeSensitivityConfig | None = None,
    path: Path = TIME_SENSITIVITY_DB_PATH,
) -> TimeSensitivityResult | None:
    """Load the most recent saved Time Sensitivity result for a chart's MM-DD-YYYY birth date."""
    birth_date_key = birth_date_key_for_chart(chart)
    if not birth_date_key or not path.exists():
        return None
    cfg = config or TimeSensitivityConfig()
    ensure_time_sensitivity_db(path)
    config_hash = _config_hash(asdict(cfg))
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            """
            SELECT result_json
            FROM chart_time_sensitivity_ranges
            WHERE birth_date_key = ?
              AND algorithm_version = ?
              AND config_hash = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (birth_date_key, TIME_SENSITIVITY_ALGORITHM_VERSION, config_hash),
        ).fetchone()
        if row is None and path != TIME_SENSITIVITY_DB_PATH:
            row = conn.execute(
                """
                SELECT result_json
                FROM chart_time_sensitivity_ranges
                WHERE birth_date_key = ?
                  AND config_hash = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (birth_date_key, config_hash),
            ).fetchone()
    if row is None:
        return None
    payload = json.loads(str(row[0]))
    payload.setdefault("birth_date_key", birth_date_key)
    return TimeSensitivityResult(**payload)
