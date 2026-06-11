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


def resolve_similarities_algorithm_log_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Return the txt file path used for the running Similarities Algorithm log."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(SIMILARITIES_ALGORITHM_LOG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / SIMILARITIES_ALGORITHM_LOG_FILENAME


def _settings_payload(settings: SimilarityCalculatorSettings | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(settings, SimilarityCalculatorSettings):
        payload = asdict(settings)
    elif is_dataclass(settings):
        payload = asdict(settings)  # type: ignore[arg-type]
    elif isinstance(settings, Mapping):
        payload = dict(settings)
    elif settings is None:
        payload = asdict(SimilarityCalculatorSettings.defaults_from_comprehensive())
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
    defaults = SimilarityCalculatorSettings.defaults_from_comprehensive()
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
