"""Utilities for logging Similar Charts algorithm setting revisions."""

from __future__ import annotations

import datetime as _datetime
import html
import json
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ephemeraldaddy.analysis.get_astro_twin import (
    SIMILARITY_COMPONENT_KEYS,
    SimilarityCalculatorSettings,
    normalize_astro_twin_demographic_match_mode,
    normalize_similar_charts_algorithm_mode,
    similarity_algorithm_settings_snapshot,
)
from ephemeraldaddy.core.feedback_prediction_fields import (
    perceived_similarity_feedback,
    require_classified_similarity_accuracy_observation,
)

_PLACEMENT_WEIGHTED_ALL_OR_NOTHING_COMPONENTS = frozenset({
    "placement",
    "distribution",
    "inner_planet_placement",
    "outer_planet_placement",
})
_RESTORABLE_DEMOGRAPHIC_MODES = frozenset({
    "none",
    "sex",
    "opposite_sex",
    "gender",
    "opposite_gender",
})

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


def _scorer_snapshot_from_logged_settings(
    mode: str,
    logged_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Convert a Settings-dialog snapshot into the scorer a mode actually used."""
    if logged_snapshot is None:
        return None
    if mode in {"default", "custom"}:
        return dict(logged_snapshot)

    raw_settings = logged_snapshot.get("settings")
    settings_values = dict(raw_settings) if isinstance(raw_settings, Mapping) else {}
    if not settings_values:
        settings_values["placement_weighting_mode"] = logged_snapshot.get(
            "placement_weighting_mode", ""
        )
        for factor in logged_snapshot.get("selected_factors", []):
            if not isinstance(factor, Mapping):
                continue
            key = str(factor.get("factor", ""))
            if key:
                settings_values[f"use_{key}"] = bool(factor.get("enabled", False))
                settings_values[f"weight_{key}"] = float(factor.get("weight", 0.0))
    known_fields = SimilarityCalculatorSettings.__dataclass_fields__
    settings = SimilarityCalculatorSettings(
        **{key: value for key, value in settings_values.items() if key in known_fields}
    )
    scorer_settings = similarity_algorithm_settings_snapshot(mode, settings)
    return build_similarity_algorithm_snapshot(mode, scorer_settings)


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


def _snapshot_setting(snapshot: Mapping[str, Any], key: str) -> object:
    settings = snapshot.get("settings")
    if isinstance(settings, Mapping) and key in settings:
        return settings.get(key)
    return snapshot.get(key)


def _experiment_variant_key(
    scorer_key: str,
    snapshot: Mapping[str, Any],
) -> str:
    """Include population filters in every reproducible scorer identity."""
    demographic_value = _snapshot_setting(snapshot, "demographic_match_mode")
    demographic_mode = (
        normalize_astro_twin_demographic_match_mode(demographic_value)
        if demographic_value is not None
        else "unknown"
    )
    return json.dumps(
        {"scorer": scorer_key, "demographic_match_mode": demographic_mode},
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
        raw_score, unavailable = perceived_similarity_feedback(record)
        try:
            score = None if unavailable else float(raw_score)
        except (TypeError, ValueError):
            score = None
        for pair_key in pair_keys:
            scores[pair_key] = score if score is None or 0.0 <= score <= 100.0 else None
    return scores


def aggregate_similarity_algorithm_accuracy(
    path: str | os.PathLike[str] | None = None,
    *,
    relationship_path: str | os.PathLike[str] | None = None,
    include_v2: bool = False,
) -> list[dict[str, Any]]:
    """Rank algorithms while retrofitting legacy log and relationship data in memory.

    The default return shape preserves the legacy v1 scorer: user-reported
    perceived similarity is compared directly with the algorithm's predicted
    percentage.  When ``include_v2`` is true, rows also include independent v2
    top-25 and bottom-25 averages.  V2 ignores blank/n/a responses and scores
    each algorithm by the user's average perceived similarity in its own top
    and bottom 25 ranked results for each source chart; the two findings are
    intentionally not combined.
    """
    log_path = resolve_similarities_algorithm_log_path(path)
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    relationship_scores = _current_relationship_scores(relationship_path)
    logged_snapshots = _logged_algorithm_snapshots(content)
    observations: dict[tuple[str, str, str], tuple[float | None, float | None, dict[str, Any] | None, int | None, str | None]] = {}
    observations_by_pair: dict[str, set[tuple[str, str, str]]] = {}
    custom_variant_order: dict[str, int] = {}
    default_variant_order: dict[str, int] = {}
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
        raw_perceived, not_applicable = perceived_similarity_feedback(payload)
        if not_applicable:
            perceived: float | None = None
            predicted: float | None = None
        else:
            try:
                perceived = float(raw_perceived)
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
            logged_snapshot = _snapshot_preceding_observation(
                logged_snapshots, mode, marker_index
            )
            # Settings-close records captured the editable slider model, not
            # necessarily the selected mode's scorer. Normalize fixed and
            # derived modes exactly as the calculation path does (for example,
            # Big 3 is exclusively Big 3 at weight 1.0).
            snapshot = _scorer_snapshot_from_logged_settings(mode, logged_snapshot)
        # Keep observations separate whenever editable settings change the
        # effective scorer; otherwise a ranking row could average incompatible
        # algorithms and retain an arbitrary snapshot for its apply action.
        variant_key = ""
        if mode in {"custom", "default"} and snapshot is not None:
            variant_key = _experiment_variant_key(
                similarity_custom_scoring_signature(snapshot),
                snapshot,
            )
        elif mode == "comprehensive" and snapshot is not None:
            placement_mode = str(snapshot.get("placement_weighting_mode") or "").strip()
            variant_key = _experiment_variant_key(placement_mode, snapshot)
        elif mode == "all_or_nothing" and snapshot is not None:
            snapshot_settings = snapshot.get("settings")
            if isinstance(snapshot_settings, Mapping):
                criterion = str(
                    snapshot_settings.get("all_or_nothing_component") or ""
                ).strip()
                scorer_identity: dict[str, str] = {"criterion": criterion}
                if criterion in _PLACEMENT_WEIGHTED_ALL_OR_NOTHING_COMPONENTS:
                    scorer_identity["placement_weighting_mode"] = str(
                        snapshot.get("placement_weighting_mode") or ""
                    ).strip()
                variant_key = _experiment_variant_key(
                    json.dumps(
                        scorer_identity,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    snapshot,
                )
        elif snapshot is not None:
            variant_key = _experiment_variant_key(
                normalize_similar_charts_algorithm_mode(mode),
                snapshot,
            )
        if mode == "custom" and variant_key not in custom_variant_order:
            custom_variant_order[variant_key] = len(custom_variant_order) + 1
        if mode == "default" and variant_key not in default_variant_order:
            default_variant_order[variant_key] = len(default_variant_order) + 1
        pair_key = _accuracy_pair_key(payload)
        observation_key = pair_key or f"legacy-offset:{marker_index}"
        composite_key = (mode, variant_key, observation_key)
        ranking_position = None
        try:
            if payload.get("ranking_position") is not None:
                ranking_position = int(payload.get("ranking_position"))
        except (TypeError, ValueError):
            ranking_position = None
        raw_uids = payload.get("chart_uids")
        subject_uid = None
        if isinstance(raw_uids, list) and raw_uids:
            raw_subject_uid = str(raw_uids[0] or "").strip()
            if raw_subject_uid:
                subject_uid = raw_subject_uid.upper()
        observations[composite_key] = (perceived, predicted, snapshot, ranking_position, subject_uid)
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
            _perceived, predicted, snapshot, ranking_position, subject_uid = observations[composite_key]
            observations[composite_key] = (relationship_scores[pair_key], predicted, snapshot, ranking_position, subject_uid)
    totals: dict[tuple[str, str], list[float]] = {}
    snapshots: dict[tuple[str, str], dict[str, Any] | None] = {}
    v2_groups: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
    for (mode, variant_key, observation_key), (perceived, predicted, snapshot, ranking_position, subject_uid) in observations.items():
        if perceived is not None and ranking_position is not None and subject_uid:
            v2_groups.setdefault((mode, variant_key, subject_uid), []).append((ranking_position, perceived))
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
    if include_v2:
        v2_totals: dict[tuple[str, str], dict[str, list[float] | int]] = {}
        for (mode, variant_key, _subject_uid), ranked_scores in v2_groups.items():
            ordered = [score for _position, score in sorted(ranked_scores, key=lambda item: item[0])]
            top_scores = ordered[:25]
            bottom_scores = ordered[-25:]
            key = (mode, variant_key)
            bucket = v2_totals.setdefault(key, {"top": [], "bottom": [], "charts": 0})
            if top_scores:
                bucket["top"].append(sum(top_scores) / len(top_scores))  # type: ignore[union-attr]
            if bottom_scores:
                bucket["bottom"].append(sum(bottom_scores) / len(bottom_scores))  # type: ignore[union-attr]
            bucket["charts"] = int(bucket["charts"]) + 1
        for row in ranked:
            key = (row["algorithm_mode"], row["_variant_key"])
            bucket = v2_totals.get(key, {"top": [], "bottom": [], "charts": 0})
            top_values = list(bucket["top"])  # type: ignore[arg-type]
            bottom_values = list(bucket["bottom"])  # type: ignore[arg-type]
            row["v2_top_25_average"] = (sum(top_values) / len(top_values)) if top_values else None
            row["v2_top_25_chart_count"] = len(top_values)
            row["v2_bottom_25_average"] = (sum(bottom_values) / len(bottom_values)) if bottom_values else None
            row["v2_bottom_25_chart_count"] = len(bottom_values)
    ranked.sort(key=lambda row: (-row["average_accuracy"], -row["sample_count"], row["algorithm_mode"], row["_variant_key"]))
    for row in ranked:
        if row["algorithm_mode"] == "custom":
            row["display_name"] = f"Custom {custom_variant_order[row['_variant_key']]}"
        elif row["algorithm_mode"] == "default" and row["_variant_key"]:
            row["display_name"] = f"Default {default_variant_order[row['_variant_key']]}"
        elif row["algorithm_mode"] == "comprehensive" and row["_variant_key"]:
            row_snapshot = row.get("algorithm_snapshot")
            placement = row_snapshot.get("placement_weighting_mode") if isinstance(row_snapshot, Mapping) else ""
            placement_name = str(placement).replace("_", " ").title()
            row["display_name"] = f"Comprehensive — {placement_name}"
        elif row["algorithm_mode"] == "all_or_nothing" and row["_variant_key"]:
            row_snapshot = row.get("algorithm_snapshot")
            row_settings = row_snapshot.get("settings") if isinstance(row_snapshot, Mapping) else None
            criterion = row_settings.get("all_or_nothing_component") if isinstance(row_settings, Mapping) else ""
            placement = row_snapshot.get("placement_weighting_mode") if isinstance(row_snapshot, Mapping) else ""
            criterion_name = str(criterion).replace("_", " ").title()
            placement_name = str(placement).replace("_", " ").title()
            row["display_name"] = (
                f"All Or Nothing — {criterion_name} ({placement_name})"
                if str(criterion) in _PLACEMENT_WEIGHTED_ALL_OR_NOTHING_COMPONENTS
                else f"All Or Nothing — {criterion_name}"
            )
        row.pop("_variant_key", None)
    return ranked


def append_similarity_accuracy_observation(
    *,
    algorithm_mode: object,
    predicted_percent: float,
    perceived_similarity_score: int | None = None,
    perceived_similarity_not_applicable: bool | None = None,
    user_reported_accuracy: int | None = None,
    not_applicable: bool | None = None,
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
    if perceived_similarity_score is None:
        perceived_similarity_score = user_reported_accuracy
    if perceived_similarity_not_applicable is None:
        perceived_similarity_not_applicable = bool(not_applicable)
    payload = {
        "timestamp_utc": timestamp.astimezone(_datetime.timezone.utc).isoformat(timespec="seconds"),
        "chart_uids": [str(chart_1_uid or ""), str(chart_2_uid or "")],
        "algorithm_mode": normalize_similar_charts_algorithm_mode(algorithm_mode),
        "predicted_percent": max(0.0, min(100.0, float(predicted_percent))),
        "ranking_position": int(ranking_position) if ranking_position is not None else None,
        "perceived_similarity_score": perceived_similarity_score,
        "perceived_similarity_not_applicable": bool(perceived_similarity_not_applicable),
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
    ranked = aggregate_similarity_algorithm_accuracy(include_v2=True) if rows is None else rows
    if not ranked:
        return "Algorithm accuracy ranking\nNo algorithm-linked accuracy scores have been recorded yet."
    lines = ["Algorithm accuracy ranking", "Average accuracy across recorded chart-pair rankings:"]
    for index, row in enumerate(ranked, start=1):
        mode = str(row.get("display_name") or row.get("algorithm_mode", "unknown")).replace("_", " ").title()
        average = float(row.get("average_accuracy", 0.0))
        count = int(row.get("sample_count", 0))
        top_average = row.get("v2_top_25_average")
        bottom_average = row.get("v2_bottom_25_average")
        v2_text = ""
        if top_average is not None or bottom_average is not None:
            top_text = "—" if top_average is None else f"{float(top_average):.1f}%"
            bottom_text = "—" if bottom_average is None else f"{float(bottom_average):.1f}%"
            v2_text = f"; v2 top 25 {top_text}; bottom 25 {bottom_text}"
        lines.append(f"{index}. {mode} — {average:.1f}% average (n={count}) v1 legacy{v2_text}")
    return "\n".join(lines)


def format_similarity_algorithm_accuracy_ranking_html(
    rows: list[Mapping[str, Any]] | None = None,
    *,
    expanded_rows: set[int] | None = None,
    highlight_color: str,
    factor_weight_color: Callable[[float, float], str] | None = None,
) -> str:
    """Return the interactive Research ranking as compact, safe rich text."""
    ranked = aggregate_similarity_algorithm_accuracy(include_v2=True) if rows is None else rows
    expanded_rows = expanded_rows or set()
    parts = [
        f'<div style="font-weight:600; color:{html.escape(highlight_color)}; font-size:14px;">'
        "Algorithm Accuracy Ranking</div>"
    ]
    if not ranked:
        parts.append("<div>No algorithm-linked accuracy scores have been recorded yet.</div>")
        return "".join(parts)
    parts.append(
        '<div style="margin:2px 0 6px 0;">Accuracy Scorer v2 compares each algorithm\'s '
        'average user scores in the top 25 and bottom 25 results per source chart; '
        'n/a and blank responses are ignored.</div>'
    )
    parts.append(
        '<table cellspacing="0" cellpadding="3" style="width:100%; border-collapse:collapse;">'
        '<tr><th align="left">Algorithm</th><th align="right">v1 legacy</th>'
        '<th align="right">v2 top 25</th><th align="right">v2 bottom 25</th>'
        '<th align="center">Use</th></tr>'
    )
    for index, row in enumerate(ranked, start=1):
        name = str(row.get("display_name") or row.get("algorithm_mode", "unknown")).replace("_", " ").title()
        algorithm_mode = str(row.get("algorithm_mode") or "").strip().lower()
        snapshot = row.get("algorithm_snapshot")
        snapshot_details_available = (
            isinstance(snapshot, Mapping)
            and bool(snapshot.get("details_available", True))
        )
        snapshot_factors = snapshot.get("selected_factors") if isinstance(snapshot, Mapping) else None
        snapshot_placement_mode = (
            snapshot.get("placement_weighting_mode")
            if isinstance(snapshot, Mapping)
            else None
        )
        factor_snapshot_available = (
            snapshot_details_available
            and isinstance(snapshot_factors, list)
            and bool(snapshot_placement_mode)
        )
        snapshot_settings = snapshot.get("settings") if isinstance(snapshot, Mapping) else None
        demographic_snapshot_available = (
            isinstance(snapshot_settings, Mapping)
            and str(snapshot_settings.get("demographic_match_mode") or "")
            in _RESTORABLE_DEMOGRAPHIC_MODES
        )
        all_or_nothing_snapshot_available = (
            isinstance(snapshot_settings, Mapping)
            and bool(snapshot_settings.get("all_or_nothing_component"))
        )
        all_or_nothing_criterion = (
            str(snapshot_settings.get("all_or_nothing_component") or "")
            if isinstance(snapshot_settings, Mapping)
            else ""
        )
        if all_or_nothing_criterion in _PLACEMENT_WEIGHTED_ALL_OR_NOTHING_COMPONENTS:
            all_or_nothing_snapshot_available = (
                all_or_nothing_snapshot_available and bool(snapshot_placement_mode)
            )
        can_apply = (
            (
                algorithm_mode not in {"custom", "default"}
                or factor_snapshot_available
            )
            and (
                algorithm_mode != "comprehensive"
                or (
                    snapshot_details_available
                    and bool(snapshot_placement_mode)
                )
            )
            and (
                algorithm_mode != "all_or_nothing"
                or all_or_nothing_snapshot_available
            )
            and algorithm_mode not in {"generic_astro", "database_distinction"}
            and demographic_snapshot_available
        )
        average = float(row.get("average_accuracy", 0.0))
        count = int(row.get("sample_count", 0))
        top_average = row.get("v2_top_25_average")
        bottom_average = row.get("v2_bottom_25_average")
        top_count = int(row.get("v2_top_25_chart_count", 0))
        bottom_count = int(row.get("v2_bottom_25_chart_count", 0))
        top_text = "—" if top_average is None else f"{float(top_average):.1f}% (charts={top_count})"
        bottom_text = "—" if bottom_average is None else f"{float(bottom_average):.1f}% (charts={bottom_count})"
        if can_apply:
            use_cell = (
                '<td align="center"><span style="border:1px solid #666666; padding:2px 5px;">'
                f'<a href="use:{index - 1}" style="text-decoration:none;">use this</a>'
                '</span></td>'
            )
        else:
            if algorithm_mode == "all_or_nothing":
                unavailable_reason = "The selected criterion is unavailable for this legacy observation."
            elif algorithm_mode in {"default", "comprehensive"}:
                unavailable_reason = "Exact scorer settings are unavailable for this legacy observation."
            elif algorithm_mode in {"generic_astro", "database_distinction"}:
                unavailable_reason = "The historical placement settings are unavailable for this fixed scorer."
            elif not demographic_snapshot_available:
                unavailable_reason = "The historical demographic filter is unavailable for this observation."
            else:
                unavailable_reason = "Exact custom settings are unavailable for this legacy observation."
            if isinstance(snapshot, Mapping):
                unavailable_reason = str(
                    snapshot.get("details_unavailable_reason") or unavailable_reason
                )
            use_cell = (
                '<td align="center"><span style="color:#777777;" title="'
                f'{html.escape(unavailable_reason, quote=True)}">unavailable</span></td>'
            )
        parts.append(
            f'<tr><td>{index}. <a href="algorithm:{index - 1}">{html.escape(name)}</a></td>'
            f'<td align="right">{average:.1f}% (n={count})</td>'
            f'<td align="right">{html.escape(top_text)}</td>'
            f'<td align="right">{html.escape(bottom_text)}</td>'
            f'{use_cell}</tr>'
        )
        if index - 1 not in expanded_rows:
            continue
        detail_fragments: list[str] = []
        if isinstance(snapshot, Mapping):
            if not bool(snapshot.get("details_available", True)):
                detail_fragments.append(
                    html.escape(
                        str(snapshot.get("details_unavailable_reason") or "Exact factor weights are unavailable.")
                    )
                )
            else:
                placement = str(snapshot.get("placement_weighting_mode", "") or "").replace("_", " ").title()
                if placement and placement != "Not Applicable":
                    detail_fragments.append(html.escape(f"Placement weighting: {placement}"))
                factors = snapshot.get("selected_factors")
                if isinstance(factors, list):
                    enabled_factors = [
                        factor
                        for factor in factors
                        if isinstance(factor, Mapping) and bool(factor.get("enabled", False))
                    ]
                    maximum_weight = max(
                        (float(factor.get("weight", 0.0)) for factor in enabled_factors),
                        default=0.0,
                    )
                    for factor in enabled_factors:
                        weight = float(factor.get("weight", 0.0))
                        label = str(factor.get("factor", "")).replace("_", " ").title()
                        factor_text = html.escape(f"{label}: {weight:g} (on)")
                        if factor_weight_color is not None:
                            color = str(factor_weight_color(weight, maximum_weight) or "").strip()
                            if color:
                                factor_text = (
                                    f'<span style="color:{html.escape(color, quote=True)};">'
                                    f"{factor_text}</span>"
                                )
                        detail_fragments.append(factor_text)
                    if not enabled_factors:
                        detail_fragments.append("No enabled factors.")
        if not detail_fragments:
            detail_fragments.append("Exact settings unavailable for this legacy observation.")
        parts.append(
            '<tr><td colspan="5"><div style="margin:3px 0 5px 18px; padding:5px 7px; border-left:2px solid '
            f'{html.escape(highlight_color)}; font-size:11px;">'
            + "<br>".join(detail_fragments)
            + "</div></td></tr>"
        )
    parts.append("</table>")
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
