"""Utilities for logging Similar Charts algorithm setting revisions."""

from __future__ import annotations

import datetime as _datetime
import html
import json
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from ephemeraldaddy.analysis.get_astro_twin import (
    SIMILARITY_COMPONENT_KEYS,
    SimilarityCalculatorSettings,
    normalize_similar_charts_algorithm_mode,
)
from ephemeraldaddy.core.feedback_prediction_fields import (
    require_classified_similarity_accuracy_observation,
)

SIMILARITIES_ALGORITHM_LOG_PATH_ENV = "EPHEMERALDADDY_SIMILARITIES_ALGORITHM_LOG_PATH"
SIMILARITIES_ALGORITHM_LOG_FILENAME = "similarities_algorithm_log.txt"
_LOG_ENTRY_HEADER_RE = re.compile(r"^=== Similarities Algorithm Change #\d+ ===$", re.MULTILINE)
_ACCURACY_PAYLOAD_MARKER = "Perceived accuracy payload:\n"
_CURRENT_SETTINGS_MARKER = "Current settings upon close:\n"


def _logged_algorithm_snapshots(content: str) -> dict[str, list[tuple[int, dict[str, Any]]]]:
    """Return complete settings snapshots, in log order, for each mode.

    Accuracy observations written before ``algorithm_snapshot`` was added to
    their payload still share this file with the Settings close records.  Those
    records contain the exact snapshot, so they are a better compatibility
    source than treating every older observation as unknowable.
    """
    snapshots: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    decoder = json.JSONDecoder()
    cursor = 0
    while True:
        marker_index = content.find(_CURRENT_SETTINGS_MARKER, cursor)
        if marker_index < 0:
            break
        payload_start = marker_index + len(_CURRENT_SETTINGS_MARKER)
        try:
            value, end_offset = decoder.raw_decode(content[payload_start:])
        except json.JSONDecodeError:
            cursor = payload_start
            continue
        cursor = payload_start + end_offset
        if not isinstance(value, Mapping):
            continue
        mode = normalize_similar_charts_algorithm_mode(value.get("algorithm_mode"))
        snapshots.setdefault(mode, []).append((marker_index, dict(value)))
    return snapshots


def _snapshot_preceding_observation(
    snapshots: Mapping[str, list[tuple[int, dict[str, Any]]]],
    mode: str,
    observation_offset: int,
) -> dict[str, Any] | None:
    """Return the settings active when a legacy observation was recorded."""
    preceding = [
        snapshot
        for snapshot_offset, snapshot in snapshots.get(mode, [])
        if snapshot_offset < observation_offset
    ]
    return preceding[-1] if preceding else None


def resolve_similarities_algorithm_log_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Return the txt file path used for the running Similarities Algorithm log."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(SIMILARITIES_ALGORITHM_LOG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / SIMILARITIES_ALGORITHM_LOG_FILENAME


def _accuracy_pair_key(payload: Mapping[str, Any]) -> str | None:
    uids = payload.get("chart_uids")
    if isinstance(uids, list) and len(uids) >= 2 and all(str(uid or "").strip() for uid in uids[:2]):
        return "|".join(f"uid:{uid}" for uid in sorted(str(uid).strip().upper() for uid in uids[:2]))
    pair = payload.get("chart_1_compared_with_chart_2")
    if isinstance(pair, Mapping):
        ids = []
        for name in ("chart_1", "chart_2"):
            chart = pair.get(name)
            if not isinstance(chart, Mapping):
                return None
            try:
                ids.append(int(chart.get("id")))
            except (TypeError, ValueError):
                return None
        return "|".join(f"id:{chart_id}" for chart_id in sorted(ids))
    return None


def similarity_custom_scoring_signature(snapshot: Mapping[str, Any]) -> str:
    """Return identity from only the settings consumed by Custom scoring."""
    factors = snapshot.get("selected_factors")
    canonical_factors = []
    if isinstance(factors, list):
        canonical_factors = [
            {
                "factor": str(factor.get("factor", "")),
                "enabled": bool(factor.get("enabled", False)),
                "weight": round(float(factor.get("weight", 0.0)), 6),
            }
            for factor in factors
            if isinstance(factor, Mapping)
        ]
    return json.dumps(
        {
            "placement_weighting_mode": str(snapshot.get("placement_weighting_mode", "")),
            "selected_factors": canonical_factors,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _current_relationship_scores(
    relationship_path: str | os.PathLike[str] | None,
) -> dict[str, float | None]:
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        resolve_chart_similarity_relationships_path,
    )

    try:
        payload = json.loads(
            resolve_chart_similarity_relationships_path(relationship_path).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}
    relationships = payload.get("relationships", {}) if isinstance(payload, Mapping) else {}
    scores: dict[str, float | None] = {}
    if not isinstance(relationships, Mapping):
        return scores
    for record in relationships.values():
        if not isinstance(record, Mapping):
            continue
        pair_keys: list[str] = []
        uids = record.get("chart_uids")
        if isinstance(uids, list) and len(uids) >= 2 and all(str(uid or "").strip() for uid in uids[:2]):
            pair_keys.append("|".join(f"uid:{uid}" for uid in sorted(str(uid).strip().upper() for uid in uids[:2])))
        ids = record.get("chart_ids")
        if isinstance(ids, list) and len(ids) >= 2:
            try:
                pair_keys.append("|".join(f"id:{chart_id}" for chart_id in sorted(int(value) for value in ids[:2])))
            except (TypeError, ValueError):
                pass
        try:
            score = None if bool(record.get("not_applicable", False)) else float(record.get("user_reported_accuracy"))
        except (TypeError, ValueError):
            score = None
        for pair_key in pair_keys:
            scores[pair_key] = score if score is None or 0.0 <= score <= 100.0 else None
    return scores


def aggregate_similarity_algorithm_accuracy(
    path: str | os.PathLike[str] | None = None,
    *,
    relationship_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Rank algorithms while retrofitting legacy log and relationship data in memory."""
    log_path = resolve_similarities_algorithm_log_path(path)
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    relationship_scores = _current_relationship_scores(relationship_path)
    logged_snapshots = _logged_algorithm_snapshots(content)
    observations: dict[tuple[str, str, str], tuple[float | None, float | None, dict[str, Any] | None]] = {}
    observations_by_pair: dict[str, set[tuple[str, str, str]]] = {}
    custom_variant_order: dict[str, int] = {}
    decoder = json.JSONDecoder()
    cursor = 0
    active_mode: str | None = None
    while True:
        marker_index = content.find(_ACCURACY_PAYLOAD_MARKER, cursor)
        if marker_index < 0:
            break
        mode_lines = re.findall(r"^Algorithm mode:\s*(\S.*?)\s*$", content[cursor:marker_index], re.MULTILINE)
        if mode_lines:
            active_mode = normalize_similar_charts_algorithm_mode(mode_lines[-1])
        payload_start = marker_index + len(_ACCURACY_PAYLOAD_MARKER)
        try:
            payload, end_offset = decoder.raw_decode(content[payload_start:])
        except json.JSONDecodeError:
            cursor = payload_start
            continue
        cursor = payload_start + end_offset
        if not isinstance(payload, Mapping):
            continue
        not_applicable = bool(payload.get("not_applicable", False))
        if not_applicable:
            perceived: float | None = None
            predicted: float | None = None
        else:
            try:
                perceived = float(payload.get("user_reported_accuracy"))
                predicted = float(payload.get("predicted_percent"))
            except (TypeError, ValueError):
                continue
            if not (0.0 <= perceived <= 100.0 and 0.0 <= predicted <= 100.0):
                continue
        raw_mode = payload.get("algorithm_mode") or payload.get("ranking_algorithm") or active_mode
        if not str(raw_mode or "").strip():
            continue
        mode = normalize_similar_charts_algorithm_mode(raw_mode)
        snapshot_value = payload.get("algorithm_snapshot")
        snapshot = dict(snapshot_value) if isinstance(snapshot_value, Mapping) else None
        if snapshot is None:
            # The prediction and its scorer are historical facts: use the
            # matching settings that preceded this observation, never a later
            # revision of the same mode.  The user's perceived score is handled
            # separately below and intentionally *does* follow later edits.
            snapshot = _snapshot_preceding_observation(logged_snapshots, mode, marker_index)
        # Custom is an experiment rather than one stable algorithm. Its settings
        # signature therefore forms part of the observation identity.
        variant_key = ""
        if mode == "custom" and snapshot is not None:
            variant_key = similarity_custom_scoring_signature(snapshot)
        if mode == "custom" and variant_key not in custom_variant_order:
            custom_variant_order[variant_key] = len(custom_variant_order) + 1
        pair_key = _accuracy_pair_key(payload)
        observation_key = pair_key or f"legacy-offset:{marker_index}"
        composite_key = (mode, variant_key, observation_key)
        observations[composite_key] = (perceived, predicted, snapshot)
        if pair_key:
            observations_by_pair.setdefault(pair_key, set()).add(composite_key)
    # USER_FEEDBACK belongs to the chart pair, independently of every
    # algorithm prediction.  It is the user's current ground truth: if they
    # revise A/B from 80% to 65%, all historical predictions must be evaluated
    # against 65%.  The relationship score therefore replaces the cached
    # payload value for every algorithm and settings variant that predicted the
    # pair. APP_PREDICTIONS (the percentage and its snapshot) remain fixed in
    # history. Keep these formal provenance classes separate when this schema
    # grows; their distinction is more important than their shared log record.
    for pair_key, composite_keys in observations_by_pair.items():
        if pair_key not in relationship_scores:
            continue
        for composite_key in composite_keys:
            if composite_key not in observations:
                continue
            _perceived, predicted, snapshot = observations[composite_key]
            observations[composite_key] = (relationship_scores[pair_key], predicted, snapshot)
    totals: dict[tuple[str, str], list[float]] = {}
    snapshots: dict[tuple[str, str], dict[str, Any] | None] = {}
    for (mode, variant_key, _pair_key), (perceived, predicted, snapshot) in observations.items():
        if perceived is not None and predicted is not None:
            accuracy = max(0.0, 100.0 - abs(predicted - perceived))
            key = (mode, variant_key)
            totals.setdefault(key, []).append(accuracy)
            if snapshot is not None:
                snapshots[key] = snapshot
    ranked = [
        {
            "algorithm_mode": mode,
            "average_accuracy": sum(scores) / len(scores),
            "sample_count": len(scores),
            **({"algorithm_snapshot": snapshots[(mode, variant_key)]} if (mode, variant_key) in snapshots else {}),
            "_variant_key": variant_key,
        }
        for (mode, variant_key), scores in totals.items()
    ]
    ranked.sort(key=lambda row: (-row["average_accuracy"], -row["sample_count"], row["algorithm_mode"], row["_variant_key"]))
    for row in ranked:
        if row["algorithm_mode"] == "custom":
            row["display_name"] = f"Custom {custom_variant_order[row['_variant_key']]}"
        row.pop("_variant_key", None)
    return ranked


def append_similarity_accuracy_observation(
    *,
    algorithm_mode: object,
    predicted_percent: float,
    user_reported_accuracy: int | None,
    not_applicable: bool,
    chart_1_uid: str | None,
    chart_2_uid: str | None,
    ranking_position: int | None = None,
    algorithm_snapshot: Mapping[str, Any] | None = None,
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
        "algorithm_snapshot": dict(algorithm_snapshot) if algorithm_snapshot is not None else None,
    }
    require_classified_similarity_accuracy_observation(payload)
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
        mode = str(row.get("display_name") or row.get("algorithm_mode", "unknown")).replace("_", " ").title()
        average = float(row.get("average_accuracy", 0.0))
        count = int(row.get("sample_count", 0))
        lines.append(f"{index}. {mode} — {average:.1f}% average (n={count})")
    return "\n".join(lines)


def format_similarity_algorithm_accuracy_ranking_html(
    rows: list[Mapping[str, Any]] | None = None,
    *,
    expanded_rows: set[int] | None = None,
    highlight_color: str,
) -> str:
    """Return the interactive Research ranking as compact, safe rich text."""
    ranked = aggregate_similarity_algorithm_accuracy() if rows is None else rows
    expanded_rows = expanded_rows or set()
    parts = [
        f'<div style="font-weight:600; color:{html.escape(highlight_color)}; font-size:14px;">'
        "Algorithm accuracy ranking</div>"
    ]
    if not ranked:
        parts.append("<div>No algorithm-linked accuracy scores have been recorded yet.</div>")
        return "".join(parts)
    parts.append("<div>Average accuracy across recorded chart-pair rankings:</div>")
    for index, row in enumerate(ranked, start=1):
        name = str(row.get("display_name") or row.get("algorithm_mode", "unknown")).replace("_", " ").title()
        average = float(row.get("average_accuracy", 0.0))
        count = int(row.get("sample_count", 0))
        parts.append(
            f'<div style="margin-top:4px;">{index}. <a href="algorithm:{index - 1}">{html.escape(name)}</a>'
            f" — {average:.1f}% average (n={count})</div>"
        )
        if index - 1 not in expanded_rows:
            continue
        snapshot = row.get("algorithm_snapshot")
        detail_lines: list[str] = []
        if isinstance(snapshot, Mapping):
            if not bool(snapshot.get("details_available", True)):
                detail_lines.append(
                    str(snapshot.get("details_unavailable_reason") or "Exact factor weights are unavailable.")
                )
            else:
                placement = str(snapshot.get("placement_weighting_mode", "") or "").replace("_", " ").title()
                if placement and placement != "Not Applicable":
                    detail_lines.append(f"Placement weighting: {placement}")
                factors = snapshot.get("selected_factors")
                if isinstance(factors, list):
                    for factor in factors:
                        if isinstance(factor, Mapping):
                            state = "on" if bool(factor.get("enabled", False)) else "off"
                            label = str(factor.get("factor", "")).replace("_", " ").title()
                            detail_lines.append(f"{label}: {float(factor.get('weight', 0.0)):g} ({state})")
        if not detail_lines:
            detail_lines.append("Exact settings unavailable for this legacy observation.")
        parts.append(
            '<div style="margin:3px 0 5px 18px; padding:5px 7px; border-left:2px solid '
            f'{html.escape(highlight_color)}; font-size:11px;">'
            + "<br>".join(html.escape(line) for line in detail_lines)
            + "</div>"
        )
    return "".join(parts)


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
    details_available = bool(payload.pop("details_available", True))
    details_unavailable_reason = str(payload.pop("details_unavailable_reason", "") or "")
    # The combined-dominance fields are constructor compatibility inputs only;
    # scoring consumes the four granular dominance components instead.
    payload.pop("use_combined_dominance", None)
    payload.pop("weight_combined_dominance", None)
    selected_factors = [
        {
            "factor": key,
            "enabled": bool(payload.get(f"use_{key}", False)),
            "weight": round(float(payload.get(f"weight_{key}", 0.0)), 6),
        }
        for key in SIMILARITY_COMPONENT_KEYS
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
        "details_available": details_available,
        "details_unavailable_reason": details_unavailable_reason,
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
