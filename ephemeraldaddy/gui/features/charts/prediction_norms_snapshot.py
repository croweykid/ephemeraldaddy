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
    return {
        "key": _trait_key(trait),
        "uid": str(trait.get("uid", "") or trait.get("trait_uid", "") or "").strip(),
        "name": str(trait.get("name", "") or "").strip(),
        "profile_hash": _stable_hash(trait.get("profile", {}) or {}),
    }


def load_prediction_norms_source() -> str:
    """Return the explicitly selected population baseline source."""
    try:
        payload = json.loads(PREDICTION_NORMS_SOURCE_PATH.read_text(encoding="utf-8"))
        source = str(payload.get("source", "") or "")
    except (FileNotFoundError, TypeError, ValueError, OSError):
        source = ""
    return source if source in PREDICTION_NORMS_SOURCES else PREDICTION_NORMS_SOURCE_OFFICIAL


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


def load_prediction_norms_snapshot(
    path: Path | None = None,
    *,
    source: str | None = None,
    include_trait_extensions: bool = True,
) -> dict[str, Any]:
    """Load one population snapshot plus the explicit custom-Trait extension.

    The extension contributes only custom ``trait_baselines``. It can never
    replace population data for other predictor sections, so Official and My
    Database are never silently merged.
    """
    if path is not None:
        return _load_snapshot_file(path)
    selected = source or load_prediction_norms_source()
    population_path = prediction_norms_snapshot_path(selected)
    population = _load_snapshot_file(population_path)
    resolved = dict(population)
    extension = (
        _load_snapshot_file(PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH)
        if include_trait_extensions and selected == PREDICTION_NORMS_SOURCE_OFFICIAL
        else {}
    )
    population_rows = dict(population.get("trait_baselines", {}) or {})
    extension_rows = dict(extension.get("trait_baselines", {}) or {})
    for key, row in extension_rows.items():
        # Extensions fill custom-trait gaps; they never shadow a bundled row.
        population_rows.setdefault(key, row)
    resolved["trait_baselines"] = population_rows
    resolved["active_source"] = selected
    resolved["population_snapshot_path"] = str(population_path)
    resolved["population_snapshot_id"] = str(population.get("snapshot_id", "") or "")
    resolved["trait_extension_snapshot_id"] = str(extension.get("snapshot_id", "") or "")
    resolved["snapshot_id"] = _stable_hash(
        {
            "source": selected,
            "population": resolved["population_snapshot_id"],
            "trait_extensions": resolved["trait_extension_snapshot_id"],
        }
    )
    return resolved


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
        if str(row.get("profile_hash", "") or "") != _stable_hash(trait.get("profile", {}) or {}):
            continue
        try:
            averages[name] = float(row.get("db_average", 0.0))
        except (TypeError, ValueError):
            continue
    return averages


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


def prospective_trait_snapshot_token(
    traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None
) -> str:
    """Return the token produced after merging the requested missing traits."""
    payload = dict(snapshot or load_prediction_norms_snapshot())
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
    # A malformed/unscorable profile must not prevent independent profiles from
    # being repaired. Score separately so every omission has an explicit cause.
    for trait in traits:
        name = str(trait.get("name", "") or "").strip() or "<unnamed>"
        try:
            result = _database_trait_averages(owner, [trait], force_refresh_stale=True)
            if name not in result:
                raise RuntimeError("trait norm calculation returned no result")
            averages[name] = float(result[name])
        except Exception as exc:
            failures[name] = str(exc)
            logger.error("Trait norm reassessment failed for %s: %s", name, exc, exc_info=True)
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
