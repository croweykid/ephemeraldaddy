# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Shared static norm snapshots for Chart View Predictions.

The snapshot is the fast path for Predictions panels: expensive database-wide
baseline work is done only when the user explicitly refreshes norms, while Chart
View reads the persisted baseline vectors as static until then.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Mapping

from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_STAT_PREDICTORS
from ephemeraldaddy.analysis.traits import list_traits, trait_uid_for_profile
from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores
from ephemeraldaddy.core import db

logger = logging.getLogger(__name__)

PREDICTION_NORMS_SNAPSHOT_VERSION = 1
PREDICTION_NORMS_SNAPSHOT_FILENAME = ".prediction_norms_snapshot.json"
PREDICTION_NORMS_SNAPSHOT_PATH = db.DB_DIR / PREDICTION_NORMS_SNAPSHOT_FILENAME
DND_STAT_KEYS: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def _stable_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _chart_uid(chart: Any) -> str:
    for attr in ("uid", "UID", "chart_uid", "permanent_uid"):
        value = str(getattr(chart, attr, "") or "").strip().upper()
        if value:
            return value
    return ""


def _trait_key(trait: Mapping[str, Any]) -> str:
    uid = str(trait.get("uid", "") or trait.get("trait_uid", "") or "").strip()
    if uid:
        return f"uid:{uid}"
    try:
        profile_uid = trait_uid_for_profile(trait.get("profile", {}) or {})
    except Exception:
        profile_uid = ""
    if profile_uid:
        return f"profile:{profile_uid}"
    return f"name:{str(trait.get('name', '') or '').strip().casefold()}"


def _trait_payload(trait: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "key": _trait_key(trait),
        "uid": str(trait.get("uid", "") or trait.get("trait_uid", "") or "").strip(),
        "name": str(trait.get("name", "") or "").strip(),
        "profile_hash": _stable_hash(trait.get("profile", {}) or {}),
    }


def prediction_norms_snapshot_path() -> Path:
    return PREDICTION_NORMS_SNAPSHOT_PATH


def load_prediction_norms_snapshot(path: Path | None = None) -> dict[str, Any]:
    snapshot_path = path or PREDICTION_NORMS_SNAPSHOT_PATH
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Skipped corrupt Predictions norms snapshot %s: %s", snapshot_path, exc, exc_info=True)
        return {}
    if not isinstance(payload, dict) or payload.get("version") != PREDICTION_NORMS_SNAPSHOT_VERSION:
        return {}
    return payload


def save_prediction_norms_snapshot(payload: dict[str, Any], path: Path | None = None) -> None:
    snapshot_path = path or PREDICTION_NORMS_SNAPSHOT_PATH
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = snapshot_path.with_suffix(f"{snapshot_path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(snapshot_path)


def remove_trait_from_prediction_norms_snapshot(
    *, trait_uid: str = "", trait_name: str = "", path: Path | None = None
) -> dict[str, Any]:
    """Remove one deleted trait without rebuilding unrelated norm baselines."""
    snapshot = load_prediction_norms_snapshot(path)
    rows = snapshot.get("trait_baselines", {}) if isinstance(snapshot, dict) else {}
    if not snapshot or not isinstance(rows, dict):
        return snapshot
    normalized_uid = str(trait_uid or "").strip()
    normalized_name = str(trait_name or "").strip().casefold()
    removed_keys = {
        key
        for key, row in rows.items()
        if isinstance(row, dict)
        and (
            (normalized_uid and str(row.get("uid", "") or "").strip() == normalized_uid)
            or (normalized_name and str(row.get("name", "") or "").strip().casefold() == normalized_name)
        )
    }
    if not removed_keys:
        return snapshot
    snapshot["trait_baselines"] = {key: row for key, row in rows.items() if key not in removed_keys}
    retired = snapshot.get("retired_trait_keys", [])
    snapshot["retired_trait_keys"] = [key for key in retired if key not in removed_keys]
    snapshot["snapshot_id"] = _stable_hash(
        {"previous": snapshot.get("snapshot_id", ""), "removed_trait_keys": sorted(removed_keys)}
    )
    save_prediction_norms_snapshot(snapshot, path)
    return snapshot


def set_trait_retired_in_prediction_norms_snapshot(
    trait: Mapping[str, Any], *, retired: bool, path: Path | None = None
) -> dict[str, Any]:
    """Toggle one trait's scan eligibility while retaining its calculated norm."""
    snapshot = load_prediction_norms_snapshot(path)
    if not snapshot:
        return snapshot
    key = _trait_key(trait)
    retired_keys = {str(value) for value in snapshot.get("retired_trait_keys", [])}
    if retired:
        retired_keys.add(key)
    else:
        retired_keys.discard(key)
    snapshot["retired_trait_keys"] = sorted(retired_keys)
    save_prediction_norms_snapshot(snapshot, path)
    return snapshot


def prediction_norms_snapshot_token(owner: Any | None = None) -> str:
    payload = load_prediction_norms_snapshot()
    if payload:
        return str(payload.get("snapshot_id") or payload.get("norm_signature") or "prediction_norm_snapshot:present")
    return "prediction_norm_snapshot:missing"


def trait_snapshot_averages(traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None) -> dict[str, float]:
    payload = dict(snapshot or load_prediction_norms_snapshot())
    rows = payload.get("trait_baselines", {}) if isinstance(payload, dict) else {}
    if not isinstance(rows, dict):
        return {}
    averages: dict[str, float] = {}
    for trait in traits:
        name = str(trait.get("name", "") or "").strip()
        if not name:
            continue
        row = rows.get(_trait_key(trait))
        if not isinstance(row, dict):
            continue
        try:
            averages[name] = float(row.get("db_average", 0.0))
        except (TypeError, ValueError):
            continue
    return averages


def dnd_stat_snapshot_averages(snapshot: Mapping[str, Any] | None = None) -> dict[str, float]:
    payload = dict(snapshot or load_prediction_norms_snapshot())
    rows = payload.get("dnd_stat_raw_averages", {}) if isinstance(payload, dict) else {}
    if not isinstance(rows, dict):
        return {}
    averages: dict[str, float] = {}
    for key in DND_STAT_KEYS:
        if key not in rows:
            return {}
        try:
            averages[key] = float(rows[key])
        except (TypeError, ValueError):
            return {}
    return averages if len(averages) == len(DND_STAT_KEYS) else {}


def _owner_chart_uids(owner: Any) -> tuple[str, ...]:
    if hasattr(owner, "_prediction_norm_rows"):
        rows = owner._prediction_norm_rows()
    else:
        rows = list(db.list_charts())
    chart_uids: set[str] = set()
    missing_uid_row_ids: list[int] = []
    for row in rows or []:
        values = tuple(row) if isinstance(row, (list, tuple)) else row
        raw_uid = ""
        try:
            raw_uid = str(values[30] or "")
        except Exception:
            raw_uid = ""
        chart_uid = raw_uid.strip().upper()
        if chart_uid:
            chart_uids.add(chart_uid)
            continue
        try:
            missing_uid_row_ids.append(int(values[0]))
        except Exception:
            continue
    if missing_uid_row_ids:
        chart_uids.update(
            str(uid).strip().upper()
            for uid in db.get_chart_uid_map(missing_uid_row_ids).values()
            if str(uid or "").strip()
        )
    return tuple(sorted(chart_uids))


def _load_norm_charts(owner: Any) -> list[Any]:
    chart_uids = _owner_chart_uids(owner)
    try:
        charts_by_uid = db.load_charts_by_uids(chart_uids)
    except Exception:
        charts_by_uid = {}
    is_placeholder = getattr(owner, "_is_placeholder_chart", None)
    charts: list[Any] = []
    for chart_uid in chart_uids:
        chart = charts_by_uid.get(chart_uid)
        if chart is None:
            continue
        if callable(is_placeholder) and is_placeholder(chart):
            continue
        if not _chart_uid(chart):
            continue
        charts.append(chart)
    return charts


def refresh_prediction_norms_snapshot(owner: Any) -> dict[str, Any]:
    """Rebuild the complete shared Predictions norm snapshot on explicit request."""
    charts = _load_norm_charts(owner)
    traits = list_traits(active_only=True)
    try:
        from ephemeraldaddy.gui.features.charts.dnd_predictions import _dnd_alignment_trait_items

        dnd_alignment_traits = _dnd_alignment_trait_items()
    except Exception:
        logger.exception("Could not include Fantasy RPG alignment traits in Predictions norms snapshot.")
        dnd_alignment_traits = []

    trait_baselines: dict[str, dict[str, Any]] = {}
    trait_groups = (
        ("custom_trait", traits),
        ("dnd_alignment", dnd_alignment_traits),
    )
    for source, group_traits in trait_groups:
        if not group_traits:
            continue
        from ephemeraldaddy.gui.features.charts.trait_predictions import _database_trait_averages

        averages = _database_trait_averages(owner, group_traits, force_refresh_stale=True)
        for trait in group_traits:
            name = str(trait.get("name", "") or "").strip()
            if not name or name not in averages:
                continue
            payload = _trait_payload(trait)
            trait_baselines[payload["key"]] = {
                **payload,
                "source": source,
                "db_average": float(averages[name]),
            }

    dnd_stat_totals = {key: 0.0 for key in DND_STAT_KEYS}
    dnd_stat_count = 0
    for chart in charts:
        raw_scores = calculate_weighted_criteria_scores(chart, predictors=DND_STAT_PREDICTORS)
        for key in DND_STAT_KEYS:
            dnd_stat_totals[key] += float(raw_scores.get(key, 0.0))
        dnd_stat_count += 1
    dnd_stat_raw_averages = (
        {key: dnd_stat_totals[key] / float(dnd_stat_count) for key in DND_STAT_KEYS}
        if dnd_stat_count
        else {}
    )

    chart_uids = tuple(sorted(_chart_uid(chart) for chart in charts if _chart_uid(chart)))
    norm_signature = _stable_hash({"chart_uids": chart_uids})
    snapshot = {
        "version": PREDICTION_NORMS_SNAPSHOT_VERSION,
        "snapshot_id": _stable_hash({
            "version": PREDICTION_NORMS_SNAPSHOT_VERSION,
            "chart_uids": chart_uids,
            "traits": sorted(trait_baselines),
            "created_seed": time.time(),
        }),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chart_count": len(charts),
        "norm_signature": norm_signature,
        "trait_baselines": trait_baselines,
        "retired_trait_keys": [],
        "dnd_alignment_trait_keys": [str(trait.get("name", "") or "") for trait in dnd_alignment_traits],
        "dnd_stat_raw_averages": dnd_stat_raw_averages,
    }
    save_prediction_norms_snapshot(snapshot)
    try:
        setattr(owner, "_prediction_norms_snapshot_cache", snapshot)
        setattr(owner, "_prediction_norms_revision", int(getattr(owner, "_prediction_norms_revision", 0) or 0) + 1)
    except Exception:
        pass
    return snapshot


def refresh_trait_norms_snapshot(owner: Any, traits: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate and merge only the supplied traits into the static snapshot.

    This is the mutation path for a newly added or analytically edited custom
    trait. Existing trait and predictor baselines remain untouched.
    """
    if not traits:
        return load_prediction_norms_snapshot()
    from ephemeraldaddy.gui.features.charts.trait_predictions import _database_trait_averages

    averages = _database_trait_averages(owner, traits, force_refresh_stale=True)
    snapshot = load_prediction_norms_snapshot()
    if not snapshot:
        snapshot = {
            "version": PREDICTION_NORMS_SNAPSHOT_VERSION,
            "snapshot_id": "",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "chart_count": len(_owner_chart_uids(owner)),
            "norm_signature": "custom_prediction_norms",
            "trait_baselines": {},
            "retired_trait_keys": [],
            "dnd_alignment_trait_keys": [],
            "dnd_stat_raw_averages": {},
        }
    rows = snapshot.setdefault("trait_baselines", {})
    changed_keys: list[str] = []
    for trait in traits:
        name = str(trait.get("name", "") or "").strip()
        if not name or name not in averages:
            continue
        payload = _trait_payload(trait)
        rows[payload["key"]] = {
            **payload,
            "source": "custom_trait",
            "db_average": float(averages[name]),
        }
        changed_keys.append(payload["key"])
    if not changed_keys:
        return snapshot
    snapshot["snapshot_id"] = _stable_hash(
        {"previous": snapshot.get("snapshot_id", ""), "updated_trait_keys": sorted(changed_keys)}
    )
    snapshot["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_prediction_norms_snapshot(snapshot)
    try:
        owner._prediction_norms_snapshot_cache = snapshot
        owner._prediction_norms_revision = int(getattr(owner, "_prediction_norms_revision", 0) or 0) + 1
    except Exception:
        pass
    return snapshot
