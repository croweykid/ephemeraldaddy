"""Utilities for logging Similar Charts algorithm setting revisions."""

from __future__ import annotations

import datetime as _datetime
import json
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from ephemeraldaddy.analysis.get_astro_twin import (
    SimilarityCalculatorSettings,
    normalize_similar_charts_algorithm_mode,
)

SIMILARITIES_ALGORITHM_LOG_PATH_ENV = "EPHEMERALDADDY_SIMILARITIES_ALGORITHM_LOG_PATH"
SIMILARITIES_ALGORITHM_LOG_FILENAME = "similarities_algorithm_log.txt"
_LOG_ENTRY_HEADER_RE = re.compile(r"^=== Similarities Algorithm Change #\d+ ===$", re.MULTILINE)
_ACCURACY_PAYLOAD_MARKER = "Perceived accuracy payload:\n"


def resolve_similarities_algorithm_log_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Return the txt file path used for the running Similarities Algorithm log."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(SIMILARITIES_ALGORITHM_LOG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / SIMILARITIES_ALGORITHM_LOG_FILENAME


def aggregate_similarity_algorithm_accuracy(
    path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Rank algorithms from perceived-accuracy payloads in the algorithm log."""
    log_path = resolve_similarities_algorithm_log_path(path)
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    totals: dict[str, list[float]] = {}
    decoder = json.JSONDecoder()
    cursor = 0
    while True:
        marker_index = content.find(_ACCURACY_PAYLOAD_MARKER, cursor)
        if marker_index < 0:
            break
        payload_start = marker_index + len(_ACCURACY_PAYLOAD_MARKER)
        try:
            payload, end_offset = decoder.raw_decode(content[payload_start:])
        except json.JSONDecodeError:
            cursor = payload_start
            continue
        cursor = payload_start + end_offset
        if not isinstance(payload, Mapping) or bool(payload.get("not_applicable", False)):
            continue
        try:
            perceived = float(payload.get("user_reported_accuracy"))
        except (TypeError, ValueError):
            continue
        if not 0.0 <= perceived <= 100.0:
            continue
        raw_mode = payload.get("algorithm_mode")
        if not str(raw_mode or "").strip():
            continue
        mode = normalize_similar_charts_algorithm_mode(raw_mode)
        totals.setdefault(mode, []).append(perceived)
    ranked = [
        {"algorithm_mode": mode, "average_accuracy": sum(scores) / len(scores), "sample_count": len(scores)}
        for mode, scores in totals.items()
    ]
    return sorted(ranked, key=lambda row: (-row["average_accuracy"], -row["sample_count"], row["algorithm_mode"]))


def append_similarity_accuracy_observation(
    *,
    algorithm_mode: object,
    predicted_percent: float,
    user_reported_accuracy: int | None,
    not_applicable: bool,
    chart_1_uid: str | None,
    chart_2_uid: str | None,
    ranking_position: int | None = None,
    path: str | os.PathLike[str] | None = None,
    timestamp: _datetime.datetime | None = None,
) -> Path:
    """Append one algorithm-linked perceived-accuracy result to the existing log."""
    log_path = resolve_similarities_algorithm_log_path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = timestamp or _datetime.datetime.now(_datetime.timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=_datetime.timezone.utc)
    payload = {
        "timestamp_utc": timestamp.astimezone(_datetime.timezone.utc).isoformat(timespec="seconds"),
        "chart_uids": [str(chart_1_uid or ""), str(chart_2_uid or "")],
        "algorithm_mode": normalize_similar_charts_algorithm_mode(algorithm_mode),
        "predicted_percent": max(0.0, min(100.0, float(predicted_percent))),
        "ranking_position": int(ranking_position) if ranking_position is not None else None,
        "user_reported_accuracy": user_reported_accuracy,
        "not_applicable": bool(not_applicable),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("=== Similarity Perceived Accuracy ===\n")
        handle.write(_ACCURACY_PAYLOAD_MARKER)
        handle.write(json.dumps(payload, indent=2, sort_keys=True))
        handle.write("\n\n")
    return log_path


def format_similarity_algorithm_accuracy_ranking(
    rows: list[Mapping[str, Any]] | None = None,
) -> str:
    """Return concise Research-tab text for aggregate algorithm results."""
    ranked = aggregate_similarity_algorithm_accuracy() if rows is None else rows
    if not ranked:
        return "Algorithm accuracy ranking\nNo algorithm-linked accuracy scores have been recorded yet."
    lines = ["Algorithm accuracy ranking", "Average accuracy across recorded chart-pair rankings:"]
    for index, row in enumerate(ranked, start=1):
        mode = str(row.get("algorithm_mode", "unknown")).replace("_", " ").title()
        average = float(row.get("average_accuracy", 0.0))
        count = int(row.get("sample_count", 0))
        lines.append(f"{index}. {mode} — {average:.1f}% average (n={count})")
    return "\n".join(lines)


def _settings_payload(settings: SimilarityCalculatorSettings | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(settings, SimilarityCalculatorSettings):
        payload = asdict(settings)
    elif is_dataclass(settings):
        payload = asdict(settings)  # type: ignore[arg-type]
    elif isinstance(settings, Mapping):
        payload = dict(settings)
    elif settings is None:
        payload = asdict(SimilarityCalculatorSettings.defaults_for_default_mode())
    else:
        payload = {
            key: getattr(settings, key)
            for key in dir(settings)
            if key.startswith(("use_", "weight_")) or key in {"placement_weighting_mode", "all_or_nothing_component"}
        }
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key.startswith("use_"):
            normalized[key] = bool(value)
        elif key.startswith("weight_"):
            normalized[key] = round(float(value), 6)
        else:
            normalized[key] = value
    defaults = SimilarityCalculatorSettings.defaults_for_default_mode()
    normalized["placement_weighting_mode"] = str(
        normalized.get("placement_weighting_mode")
        or defaults.placement_weighting_mode
    )
    normalized["all_or_nothing_component"] = str(
        normalized.get("all_or_nothing_component")
        or defaults.all_or_nothing_component
    )
    return normalized


def build_similarity_algorithm_snapshot(
    algorithm_mode: object,
    settings: SimilarityCalculatorSettings | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a stable, comparable snapshot of Similar Charts scoring settings."""
    payload = _settings_payload(settings)
    enabled_components: dict[str, bool] = {}
    weights_by_component: dict[str, float] = {}
    for key, value in payload.items():
        if key.startswith("use_"):
            enabled_components[key.removeprefix("use_")] = bool(value)
        elif key.startswith("weight_"):
            weights_by_component[key.removeprefix("weight_")] = round(float(value), 6)
    component_keys = sorted(set(enabled_components) | set(weights_by_component))
    selected_factors = [
        {
            "factor": key,
            "enabled": bool(enabled_components.get(key, False)),
            "weight": round(float(weights_by_component.get(key, 0.0)), 6),
        }
        for key in component_keys
    ]
    selected_total = round(
        sum(row["weight"] for row in selected_factors if row["enabled"]),
        6,
    )
    return {
        "algorithm_mode": normalize_similar_charts_algorithm_mode(algorithm_mode),
        "placement_weighting_mode": str(payload.get("placement_weighting_mode") or ""),
        "selected_total": selected_total,
        "selected_factors": selected_factors,
        "settings": payload,
    }


def similarity_algorithm_snapshots_changed(
    opening_snapshot: Mapping[str, Any] | None,
    current_snapshot: Mapping[str, Any] | None,
) -> bool:
    """Return True when scoring settings differ between Settings open and close."""
    if opening_snapshot is None or current_snapshot is None:
        return False
    return dict(opening_snapshot) != dict(current_snapshot)


def _next_log_version(log_path: Path) -> int:
    if not log_path.exists():
        return 1
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return 1
    return len(_LOG_ENTRY_HEADER_RE.findall(content)) + 1


def append_similarity_algorithm_change_log(
    *,
    opening_snapshot: Mapping[str, Any],
    current_snapshot: Mapping[str, Any],
    path: str | os.PathLike[str] | None = None,
    timestamp: _datetime.datetime | None = None,
) -> Path:
    """Append the current Similarities Algorithm settings to the running txt log."""
    log_path = resolve_similarities_algorithm_log_path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    version = _next_log_version(log_path)
    if timestamp is None:
        timestamp = _datetime.datetime.now(_datetime.timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=_datetime.timezone.utc)
    timestamp_text = timestamp.astimezone(_datetime.timezone.utc).isoformat(timespec="seconds")

    selected_factors = current_snapshot.get("selected_factors", [])
    factor_lines = []
    if isinstance(selected_factors, list):
        for row in selected_factors:
            if not isinstance(row, Mapping):
                continue
            factor_lines.append(
                "- {factor}: enabled={enabled} weight={weight:.6f}".format(
                    factor=str(row.get("factor", "")),
                    enabled=bool(row.get("enabled", False)),
                    weight=float(row.get("weight", 0.0)),
                )
            )
    if not factor_lines:
        factor_lines.append("- none")

    entry = "\n".join(
        [
            f"=== Similarities Algorithm Change #{version} ===",
            f"Timestamp (UTC): {timestamp_text}",
            f"Algorithm mode: {current_snapshot.get('algorithm_mode', '')}",
            f"Placement weighting mode: {current_snapshot.get('placement_weighting_mode', '')}",
            f"Selected weight total: {float(current_snapshot.get('selected_total', 0.0)):.6f}",
            "Selected factors:",
            *factor_lines,
            "Opening snapshot:",
            json.dumps(dict(opening_snapshot), indent=2, sort_keys=True),
            "Current settings upon close:",
            json.dumps(dict(current_snapshot), indent=2, sort_keys=True),
            "",
        ]
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)
        handle.write("\n")
    return log_path
