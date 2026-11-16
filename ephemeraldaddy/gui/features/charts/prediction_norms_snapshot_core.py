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
from ephemeraldaddy.analysis.trait_reviews import without_trait_reviews
from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores
from ephemeraldaddy.core import db

logger = logging.getLogger(__name__)

PREDICTION_NORMS_SNAPSHOT_VERSION = 1
PREDICTION_NORMS_SNAPSHOT_FILENAME = ".prediction_norms_snapshot.json"
PREDICTION_NORMS_SNAPSHOT_PATH = db.DB_DIR / PREDICTION_NORMS_SNAPSHOT_FILENAME
PREDICTION_NORMS_TRAIT_EXTENSIONS_FILENAME = ".prediction_norms_trait_extensions.json"
PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH = db.DB_DIR / PREDICTION_NORMS_TRAIT_EXTENSIONS_FILENAME
PREDICTION_NORMS_SOURCE_FILENAME = ".prediction_norms_source.json"
PREDICTION_NORMS_SOURCE_PATH = db.DB_DIR / PREDICTION_NORMS_SOURCE_FILENAME
PREDICTION_NORMS_SOURCE_OFFICIAL = "official"
PREDICTION_NORMS_SOURCE_MY_DATABASE = "my_database"
PREDICTION_NORMS_SOURCES = (
    PREDICTION_NORMS_SOURCE_OFFICIAL,
    PREDICTION_NORMS_SOURCE_MY_DATABASE,
)
OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[3] / "analysis" / "default_prediction_norms.json"
)
DND_STAT_KEYS: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


class ExplicitNormRecalculationRequired(RuntimeError):
    """Raised when code attempts a whole-database norm rebuild implicitly."""


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
    from ephemeraldaddy.analysis.trait_signatures import trait_definition_signature
    return {"key": _trait_key(trait), "uid": str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
            "name": str(trait.get("name") or "").strip(), "profile_hash": trait_definition_signature(trait)}


def load_prediction_norms_source() -> str:
    from ephemeraldaddy.core.prediction_norms import PredictionNormPaths, selected_norm_source
    return selected_norm_source(PredictionNormPaths(PREDICTION_NORMS_SOURCE_PATH, OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH, PREDICTION_NORMS_SNAPSHOT_PATH, PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH))


def save_prediction_norms_source(source: str) -> str:
    """Persist source selection without modifying either population snapshot."""
    normalized = str(source or "").strip().lower()
    if normalized not in PREDICTION_NORMS_SOURCES:
        raise ValueError(f"Unsupported Predictions norms source: {source!r}")
    PREDICTION_NORMS_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTION_NORMS_SOURCE_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"source": normalized}, indent=2), encoding="utf-8")
    temporary.replace(PREDICTION_NORMS_SOURCE_PATH)
    return normalized


def prediction_norms_snapshot_path(source: str | None = None) -> Path:
    """Resolve exactly one population-baseline path (never an overlay)."""
    selected = source or load_prediction_norms_source()
    if selected == PREDICTION_NORMS_SOURCE_OFFICIAL:
        return OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH
    if selected == PREDICTION_NORMS_SOURCE_MY_DATABASE:
        return PREDICTION_NORMS_SNAPSHOT_PATH
    raise ValueError(f"Unsupported Predictions norms source: {selected!r}")


def _load_snapshot_file(snapshot_path: Path) -> dict[str, Any]:
    from ephemeraldaddy.core.prediction_norms import read_snapshot_file
    return read_snapshot_file(snapshot_path)


def load_prediction_norms_snapshot(path: Path | None = None, *, source: str | None = None, include_trait_extensions: bool = True) -> dict[str, Any]:
    """Compatibility facade over the GUI-free, shared static reference reader."""
    from ephemeraldaddy.core.prediction_norms import PredictionNormPaths, load_prediction_norms_snapshot as read
    if path is not None:
        return _load_snapshot_file(path)
    return read(paths=PredictionNormPaths(PREDICTION_NORMS_SOURCE_PATH,
        OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH, PREDICTION_NORMS_SNAPSHOT_PATH,
        PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH), source=source,
        include_trait_extensions=include_trait_extensions)


def prediction_norms_source_metadata(source: str | None = None) -> dict[str, Any]:
    """Describe the selected population source for Settings without scanning charts."""
    selected = source or load_prediction_norms_source()
    path = prediction_norms_snapshot_path(selected)
    payload = _load_snapshot_file(path)
    return {
        "source": selected,
        "label": "Official" if selected == PREDICTION_NORMS_SOURCE_OFFICIAL else "My Database",
        "path": str(path),
        "available": bool(payload),
        "created_at": str(payload.get("created_at", "") or ""),
        "chart_count": int(payload.get("chart_count", 0) or 0),
        "snapshot_id": str(payload.get("snapshot_id", "") or ""),
    }


def save_prediction_norms_snapshot(payload: dict[str, Any], path: Path | None = None) -> None:
    snapshot_path = path or PREDICTION_NORMS_SNAPSHOT_PATH
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = snapshot_path.with_suffix(f"{snapshot_path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(snapshot_path)


def _writable_trait_norms_path() -> Path:
    """Return the modular Trait store for the active population source."""
    if load_prediction_norms_source() == PREDICTION_NORMS_SOURCE_OFFICIAL:
        return PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH
    return PREDICTION_NORMS_SNAPSHOT_PATH


def remove_trait_from_prediction_norms_snapshot(
    *, trait_uid: str = "", trait_name: str = "", path: Path | None = None
) -> dict[str, Any]:
    """Remove one deleted trait without rebuilding unrelated norm baselines."""
    snapshot_path = path or _writable_trait_norms_path()
    snapshot = _load_snapshot_file(snapshot_path)
    rows = snapshot.get("trait_baselines", {}) if isinstance(snapshot, dict) else {}
    if not snapshot or not isinstance(rows, dict):
        return snapshot
    normalized_uid = str(trait_uid or "").strip()
    normalized_name = str(trait_name or "").strip().casefold()
    if normalized_uid:
        removed_keys = {
            key
            for key, row in rows.items()
            if isinstance(row, dict)
            and str(row.get("uid", "") or "").strip() == normalized_uid
        }
    else:
        removed_keys = {
            key
            for key, row in rows.items()
            if isinstance(row, dict)
            and normalized_name
            and str(row.get("name", "") or "").strip().casefold() == normalized_name
        }
    if not removed_keys:
        return snapshot
    snapshot["trait_baselines"] = {key: row for key, row in rows.items() if key not in removed_keys}
    retired = snapshot.get("retired_trait_keys", [])
    snapshot["retired_trait_keys"] = [key for key in retired if key not in removed_keys]
    snapshot["snapshot_id"] = _stable_hash(
        {"previous": snapshot.get("snapshot_id", ""), "removed_trait_keys": sorted(removed_keys)}
    )
    save_prediction_norms_snapshot(snapshot, snapshot_path)
    return snapshot if path is not None else load_prediction_norms_snapshot()


def set_trait_retired_in_prediction_norms_snapshot(
    trait: Mapping[str, Any], *, retired: bool, path: Path | None = None
) -> dict[str, Any]:
    """Toggle one trait's scan eligibility while retaining its calculated norm."""
    snapshot_path = path or _writable_trait_norms_path()
    snapshot = _load_snapshot_file(snapshot_path)
    if not snapshot:
        return snapshot
    key = _trait_key(trait)
    retired_keys = {str(value) for value in snapshot.get("retired_trait_keys", [])}
    if retired:
        retired_keys.add(key)
    else:
        retired_keys.discard(key)
    snapshot["retired_trait_keys"] = sorted(retired_keys)
    save_prediction_norms_snapshot(snapshot, snapshot_path)
    return snapshot if path is not None else load_prediction_norms_snapshot()


def prediction_norms_snapshot_token(owner: Any | None = None) -> str:
    from ephemeraldaddy.core.prediction_norms import prediction_norms_reference
    payload = prediction_norms_reference()
    if payload:
        return str(payload.get("snapshot_id") or payload.get("norm_signature") or "prediction_norm_snapshot:present")
    return "prediction_norm_snapshot:missing"


def trait_snapshot_averages(traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None) -> dict[str, float]:
    """Read mode-agnostic availability summaries; scoring selects its own mode."""
    from ephemeraldaddy.core.prediction_norms import trait_norm_preflight_values
    return trait_norm_preflight_values(traits, snapshot)


def missing_trait_norms(
    traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Return active traits absent from the snapshot or changed analytically."""
    averages = trait_snapshot_averages(traits, snapshot)
    return [
        trait
        for trait in traits
        if str(trait.get("name", "") or "").strip() not in averages
    ]


def trait_norm_unavailability_reasons(traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None) -> dict[str, str]:
    available = trait_snapshot_averages(traits, snapshot)
    return {trait["name"]: "no stored DB norm exists for this trait UID" for trait in traits if trait["name"] not in available}


def prospective_trait_snapshot_token(
    traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None
) -> str:
    """Return the token produced after merging the requested missing traits."""
    from ephemeraldaddy.core.prediction_norms import prediction_norms_reference
    payload = dict(snapshot if snapshot is not None else prediction_norms_reference())
    missing = missing_trait_norms(traits, payload)
    current_token = str(payload.get("snapshot_id", "") or "")
    if not missing:
        return current_token
    local_token = _stable_hash(
        {
            "previous": current_token,
            "updated_trait_keys": sorted(_trait_key(trait) for trait in missing),
        }
    )
    return _stable_hash(
        {
            "source": payload.get("active_source", load_prediction_norms_source()),
            "population": payload.get("population_snapshot_id", ""),
            "trait_extensions": local_token,
        }
    )


def dnd_stat_snapshot_averages(snapshot: Mapping[str, Any] | None = None) -> dict[str, float]:
    from ephemeraldaddy.core.prediction_norms import prediction_norms_reference
    payload = dict(snapshot if snapshot is not None else prediction_norms_reference())
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


def refresh_prediction_norms_snapshot(
    owner: Any, *, user_initiated: bool = False
) -> dict[str, Any]:
    """Rebuild the complete shared Predictions norm snapshot on explicit request."""
    if not user_initiated:
        raise ExplicitNormRecalculationRequired(
            "Whole-database prediction norms can only be rebuilt by the explicit "
            "Recalculate DB Norms action."
        )
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
        from ephemeraldaddy.analysis.traits import calculate_trait_likelihoods
        totals = {trait["name"]: 0.0 for trait in group_traits}
        for chart in charts:
            for name, value in calculate_trait_likelihoods(chart, group_traits).items():
                totals[name] += value
        averages = {name: total / len(charts) for name, total in totals.items()} if charts else {}
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
    from ephemeraldaddy.analysis.distinguishing_factors import distinguishing_metric_payload_for_chart
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
        "distinguishing_metric_payloads": [
            distinguishing_metric_payload_for_chart(chart)
            for chart in charts
        ],
    }
    # A manual rebuild creates/replaces My Database only. The bundled Official
    # catalog and the user's explicit source selection are independent.
    save_prediction_norms_snapshot(snapshot, PREDICTION_NORMS_SNAPSHOT_PATH)
    resolved_snapshot = load_prediction_norms_snapshot(
        source=PREDICTION_NORMS_SOURCE_MY_DATABASE
    )
    try:
        setattr(owner, "_prediction_norms_snapshot_cache", resolved_snapshot)
        setattr(owner, "_prediction_norms_revision", int(getattr(owner, "_prediction_norms_revision", 0) or 0) + 1)
    except Exception:
        pass
    return resolved_snapshot


def refresh_trait_norms_snapshot(owner: Any, traits: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate and merge only the supplied traits into the static snapshot.

    This is the mutation path for a newly added or analytically edited custom
    trait. Existing trait and predictor baselines remain untouched.
    """
    if not traits:
        return load_prediction_norms_snapshot()
    from ephemeraldaddy.gui.features.charts.trait_predictions import _database_trait_averages

    averages: dict[str, float] = {}
    failures: dict[str, str] = {}
    # Score the complete set in one chart traversal. Missing results are still
    # recorded independently so one unscorable profile does not hide the norms
    # successfully produced for its peers.
    try:
        result = _database_trait_averages(
            owner,
            traits,
            force_refresh_stale=True,
            allow_partial=True,
        )
    except Exception as exc:
        result = {}
        logger.error("Trait norm reassessment failed: %s", exc, exc_info=True)
        for trait in traits:
            name = str(trait.get("name", "") or "").strip() or "<unnamed>"
            failures[name] = str(exc)
    else:
        for trait in traits:
            name = str(trait.get("name", "") or "").strip() or "<unnamed>"
            if name not in result:
                failures[name] = (
                    "no average was returned; the profile could not be scored against the persisted chart set"
                )
                logger.error("Trait norm reassessment returned no result for %s", name)
                continue
            try:
                averages[name] = float(result[name])
            except (TypeError, ValueError) as exc:
                failures[name] = str(exc)
                logger.error("Trait norm reassessment returned an invalid result for %s: %s", name, exc)
    try:
        owner._trait_norm_refresh_failures = failures
    except Exception:
        pass
    combined_snapshot = load_prediction_norms_snapshot()
    snapshot_path = _writable_trait_norms_path()
    snapshot = _load_snapshot_file(snapshot_path)
    if not snapshot:
        snapshot = {
            "version": PREDICTION_NORMS_SNAPSHOT_VERSION,
            "snapshot_id": "",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "chart_count": len(_owner_chart_uids(owner)),
            "snapshot_kind": "custom_trait_extensions",
            "norm_signature": "custom_trait_extensions",
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
        {"previous": combined_snapshot.get("snapshot_id", ""), "updated_trait_keys": sorted(changed_keys)}
    )
    snapshot["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_prediction_norms_snapshot(snapshot, snapshot_path)
    try:
        owner._prediction_norms_snapshot_cache = load_prediction_norms_snapshot()
        owner._prediction_norms_revision = int(getattr(owner, "_prediction_norms_revision", 0) or 0) + 1
    except Exception:
        pass
    return load_prediction_norms_snapshot()
