"""Birth-time / rectification sensitivity scanning helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.db import DB_DIR
from ephemeraldaddy.core.human_design_system import calculate_human_design
from ephemeraldaddy.core.interpretations import NAKSHATRA_RANGES, ZODIAC_NAMES

TIME_SENSITIVITY_ALGORITHM_VERSION = "time-sensitivity-v1"
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
    baseline_time: str = "12:00"
    boundary_refinement: bool = False


@dataclass(frozen=True)
class TimeSensitivityResult:
    chart_uid: str
    chart_name: str
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


def scan_times(interval_minutes: int = 30, *, include_day_end: bool = True) -> list[tuple[int, int]]:
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
        "dominant_planet_weights": {str(k): float(v) for k, v in calculate_dominant_planet_weights(chart).items()},
        "dominant_sign_weights": {str(k): float(v) for k, v in calculate_dominant_sign_weights(chart).items()},
        "dominant_house_weights": {str(k): float(v) for k, v in calculate_dominant_house_weights(chart).items()},
        "dominant_element_weights": {str(k): float(v) for k, v in calculate_dominant_element_weights(chart).items()},
        "dominant_mode_weights": {str(k): float(v) for k, v in calculate_mode_weights(chart).items()},
        "dominant_nakshatra_weights": {str(k): float(v) for k, v in calculate_dominant_nakshatra_weights(chart).items()},
    }


def _hd_snapshot(chart: Chart) -> dict[str, Any]:
    result = calculate_human_design(chart)
    activations = (*result.personality_activations, *result.design_activations)
    return {
        "gates": sorted(int(gate) for gate in result.active_gates),
        "lines": sorted(f"{int(a.gate)}.{int(a.line)}" for a in activations),
        "channels": sorted(f"{min(a, b)}-{max(a, b)}" for a, b, *_ in result.defined_channels),
        "type": str(result.hd_type or ""),
        "profile": str(result.profile or ""),
    }


def _categorical_snapshot(chart: Chart) -> dict[str, str]:
    positions = getattr(chart, "positions", {}) or {}
    return {
        "Sun sign": _sign_for_longitude(float(positions["Sun"])) if "Sun" in positions else "",
        "Moon nakshatra": _get_nakshatra(float(positions["Moon"])) if "Moon" in positions else "",
        "Ascendant": _sign_for_longitude(float(positions["AS"])) if "AS" in positions else "",
    }


def _sign_for_longitude(lon: float) -> str:
    return ZODIAC_NAMES[int((float(lon) % 360.0) // 30)]


def _get_nakshatra(lon: float) -> str:
    lon = float(lon) % 360.0
    for name, start, end in NAKSHATRA_RANGES:
        start_f = float(start) % 360.0
        end_f = float(end) % 360.0
        if start_f <= end_f:
            if start_f <= lon < end_f:
                return str(name)
        elif lon >= start_f or lon < end_f:
            return str(name)
    return str(NAKSHATRA_RANGES[-1][0])


def _percent_delta(range_delta: float, baseline: float) -> float:
    denominator = abs(float(baseline))
    if denominator <= 1e-9:
        return 0.0 if abs(range_delta) <= 1e-9 else 100.0
    return (float(range_delta) / denominator) * 100.0


def _variability_label(percent_delta: float) -> str:
    if percent_delta < 5.0:
        return "Stable"
    if percent_delta < 15.0:
        return "Mildly variable"
    if percent_delta < 35.0:
        return "Variable"
    return "Highly variable"


def _aggregate_numeric(samples: list[dict[str, Any]], baseline: dict[str, dict[str, float]]) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, float]]:
    ranges: dict[str, dict[str, dict[str, Any]]] = {}
    group_deltas: dict[str, float] = {}
    for group in NUMERIC_GROUPS:
        keys = sorted({key for sample in samples for key in sample["numeric"].get(group, {})} | set(baseline.get(group, {})))
        group_ranges: dict[str, dict[str, Any]] = {}
        max_group_delta = 0.0
        for key in keys:
            values = [(sample["time"], float(sample["numeric"].get(group, {}).get(key, 0.0))) for sample in samples]
            min_value = min(value for _time, value in values)
            max_value = max(value for _time, value in values)
            base_value = float(baseline.get(group, {}).get(key, 0.0))
            delta = max_value - min_value
            pct = _percent_delta(delta, base_value)
            max_group_delta = max(max_group_delta, pct)
            present_times = [time for time, value in values if value > 0]
            group_ranges[key] = {
                "min": round(min_value, 6),
                "max": round(max_value, 6),
                "baseline": round(base_value, 6),
                "delta": round(delta, 6),
                "percent_delta": round(pct, 2),
                "label": _variability_label(pct),
                "times_at_min": [time for time, value in values if value == min_value],
                "times_at_max": [time for time, value in values if value == max_value],
                "appears_after": present_times[0] if min_value == 0.0 and present_times else None,
            }
        ranges[group] = group_ranges
        group_deltas[group] = round(max_group_delta, 2)
    return ranges, group_deltas


def _presence_summary(samples: list[dict[str, Any]], key: str) -> dict[str, Any]:
    sample_count = len(samples)
    universe = sorted({item for sample in samples for item in sample["human_design"].get(key, [])})
    counts = {str(item): sum(1 for sample in samples if item in sample["human_design"].get(key, [])) for item in universe}
    return {
        "always": [item for item, count in counts.items() if count == sample_count],
        "sometimes": [item for item, count in counts.items() if 0 < count < sample_count],
        "presence_counts": counts,
        "sample_count": sample_count,
    }


def _distribution(samples: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sample in samples:
        value = str(sample["human_design"].get(key, "") or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_group_deltas(group_deltas: dict[str, float]) -> tuple[list[str], list[str]]:
    ordered = sorted(group_deltas.items(), key=lambda item: item[1], reverse=True)
    most = [f"{name.replace('_', ' ')} ({delta:.2f}%)" for name, delta in ordered[:3]]
    least = [f"{name.replace('_', ' ')} ({delta:.2f}%)" for name, delta in ordered[-3:]]
    return most, least


def compute_time_sensitivity(chart: Any, config: TimeSensitivityConfig | None = None) -> TimeSensitivityResult:
    """Compute sampled Time/Rectification Sensitivity ranges for one chart."""
    cfg = config or TimeSensitivityConfig()
    samples: list[dict[str, Any]] = []
    warnings: list[str] = []
    baseline_hour, baseline_minute = (int(part) for part in cfg.baseline_time.split(":", 1))
    baseline_chart = _variant_chart(chart, baseline_hour, baseline_minute)
    baseline_numeric = _numeric_snapshot(baseline_chart)

    for hour, minute in scan_times(cfg.interval_minutes, include_day_end=cfg.include_day_end):
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
            human_design = {"gates": [], "lines": [], "channels": [], "type": "", "profile": ""}

        samples.append({
            "time": label,
            "numeric": numeric,
            "human_design": human_design,
            "categorical": categorical,
        })

    if not samples:
        details = "; ".join(warnings[:5])
        suffix = f" First failures: {details}" if details else ""
        raise ValueError(f"Time Sensitivity could not produce any valid sampled charts.{suffix}")

    numeric_ranges, group_deltas = _aggregate_numeric(samples, baseline_numeric)
    most_sensitive, least_sensitive = _top_group_deltas(group_deltas)
    max_delta = max(group_deltas.values(), default=0.0)
    stability = max(0.0, 100.0 - max_delta)

    categorical_values = {
        key: [sample["categorical"].get(key, "") for sample in samples]
        for key in ("Sun sign", "Moon nakshatra", "Ascendant")
    }
    stable = [f"{key}: fixed all day ({values[0]})" for key, values in categorical_values.items() if values and len(set(values)) == 1 and values[0]]
    variable = [f"{key}: {' / '.join(dict.fromkeys(v for v in values if v))}" for key, values in categorical_values.items() if len(set(v for v in values if v)) > 1]

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

    computed_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return TimeSensitivityResult(
        chart_uid=str(getattr(chart, "chart_uid", "") or ""),
        chart_name=str(getattr(chart, "name", "") or ""),
        algorithm_version=TIME_SENSITIVITY_ALGORITHM_VERSION,
        computed_at=computed_at,
        config=asdict(cfg),
        sample_count=len(samples),
        baseline_time=cfg.baseline_time,
        overall={
            "stability_percent": round(stability, 2),
            "max_total_change_from_baseline_percent": round(max_delta, 2),
            "most_sensitive": most_sensitive,
            "least_sensitive": least_sensitive,
            "group_deltas": group_deltas,
        },
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chart_time_sensitivity_ranges (
                id INTEGER PRIMARY KEY,
                chart_uid TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                config_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(chart_uid, algorithm_version, config_hash)
            )
            """
        )


def save_time_sensitivity_result(result: TimeSensitivityResult, path: Path = TIME_SENSITIVITY_DB_PATH) -> None:
    ensure_time_sensitivity_db(path)
    payload = result_to_dict(result)
    config_json = json.dumps(result.config, sort_keys=True)
    result_json = json.dumps(payload, sort_keys=True)
    config_hash = _config_hash(result.config)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO chart_time_sensitivity_ranges (
                chart_uid, algorithm_version, config_hash, config_json, result_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chart_uid, algorithm_version, config_hash) DO UPDATE SET
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
            """,
            (result.chart_uid, result.algorithm_version, config_hash, config_json, result_json, now, now),
        )
