"""Read the selected static population reference without scanning charts.

The legacy Settings facade supplies paths explicitly; headless prediction
consumers use the same paths and reader. Generation is deliberately absent.
"""

from __future__ import annotations

import copy
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ephemeraldaddy.analysis.trait_signatures import stable_hash


@dataclass(frozen=True)
class PredictionNormPaths:
    selection: Path
    official: Path
    personal: Path
    trait_extensions: Path


def default_norm_paths() -> PredictionNormPaths:
    from ephemeraldaddy.core.db import DB_DIR

    return PredictionNormPaths(
        DB_DIR / ".prediction_norms_source.json",
        Path(__file__).resolve().parents[1] / "analysis/default_prediction_norms.json",
        DB_DIR / ".prediction_norms_snapshot.json",
        DB_DIR / ".prediction_norms_trait_extensions.json",
    )


_lock = threading.RLock()
_documents: dict[Path, tuple[tuple[int, int] | None, dict[str, Any]]] = {}
_resolved: dict[tuple[Any, ...], dict[str, Any]] = {}


def _token(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except FileNotFoundError:
        return None


def _read_document(path: Path) -> dict[str, Any]:
    token = _token(path)
    with _lock:
        cached = _documents.get(path)
        if cached is not None and cached[0] == token:
            return cached[1]
        try:
            value = json.loads(path.read_text(encoding="utf-8")) if token is not None else {}
        except (OSError, ValueError):
            value = {}
        value = value if isinstance(value, dict) else {}
        _documents[path] = (token, value)
        if len(_documents) > 32:
            _documents.pop(next(iter(_documents)))
        return value


def read_snapshot_file(path: Path) -> dict[str, Any]:
    value = _read_document(path)
    if value.get("version") != 1 and value.get("catalog_version") != 2:
        return {}
    return copy.deepcopy(value)


def selected_norm_source(paths: PredictionNormPaths | None = None) -> str:
    paths = paths or default_norm_paths()
    source = _read_document(paths.selection).get("source", "official")
    return source if source in {"official", "my_database"} else "official"


def _legacy_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Expose the existing v1 contract for both packaged catalog generations."""
    result = dict(payload)
    sections = payload.get("sections", {})
    if payload.get("catalog_version") == 2 and isinstance(sections, Mapping):
        traits = sections.get("traits", {})
        if isinstance(traits, Mapping):
            result.setdefault("trait_baselines", traits.get("rows", {}))
        result.setdefault("chart_count", payload.get("provenance", {}).get("chart_count", 0))
        for section, aliases in (
            ("enneagram", {"type_raw_averages": "enneagram_type_raw_averages", "definition_signature": "enneagram_definition_signature"}),
            ("fantasy_rpg", {"stat_raw_averages": "dnd_stat_raw_averages", "alignment_trait_keys": "dnd_alignment_trait_keys"}),
            ("distinguishing_factors", {"metric_payloads": "distinguishing_metric_payloads"}),
        ):
            data = sections.get(section, {})
            if isinstance(data, Mapping):
                rows = data.get("rows", {})
                if isinstance(rows, Mapping):
                    for old, new in aliases.items():
                        if old in rows or new in rows or new in data:
                            result.setdefault(new, rows.get(old, rows.get(new, data.get(new))))
    return result


def _snapshot(paths: PredictionNormPaths, source: str, include_extensions: bool) -> dict[str, Any]:
    population_path = paths.official if source == "official" else paths.personal
    use_extensions = include_extensions and source == "official"
    key = (paths, source, include_extensions, _token(population_path), _token(paths.trait_extensions) if use_extensions else None)
    with _lock:
        if key in _resolved:
            return _resolved[key]
        raw = _read_document(population_path)
        population = _legacy_projection(raw) if raw.get("version") == 1 or raw.get("catalog_version") == 2 else {}
        extension = _read_document(paths.trait_extensions) if use_extensions else {}
        result = dict(population)
        rows = dict(population.get("trait_baselines", {}) or {})
        for uid, row in (extension.get("trait_baselines", {}) or {}).items():
            rows.setdefault(uid, row)
        result.update(
            trait_baselines=rows, active_source=source,
            population_snapshot_path=str(population_path),
            population_snapshot_id=str(population.get("snapshot_id", "")),
            trait_extension_snapshot_id=str(extension.get("snapshot_id", "")),
        )
        result["snapshot_id"] = stable_hash({
            "source": source, "population": result["population_snapshot_id"],
            "trait_extensions": result["trait_extension_snapshot_id"],
        })
        _resolved[key] = result
        while len(_resolved) > 8:
            _resolved.pop(next(iter(_resolved)))
        return result


def load_prediction_norms_snapshot(*, paths: PredictionNormPaths | None = None, source: str | None = None, include_trait_extensions: bool = True) -> dict[str, Any]:
    paths = paths or default_norm_paths()
    source = source or selected_norm_source(paths)
    if source not in {"official", "my_database"}:
        raise ValueError(f"Unsupported Predictions norms source: {source!r}")
    return copy.deepcopy(_snapshot(paths, source, include_trait_extensions))


def trait_norm_values(traits: list[dict[str, Any]], snapshot: Mapping[str, Any] | None = None, *, include_houses: bool | None = None) -> dict[str, float]:
    # A legacy row's full-profile hash includes labels/color/description. Its
    # stable UID remains authoritative; changing presentation cannot revoke it.
    if snapshot is None:
        paths = default_norm_paths()
        snapshot = _snapshot(paths, selected_norm_source(paths), True)
    rows = snapshot.get("trait_baselines", {})
    result = {}
    for trait in traits:
        uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
        name = str(trait.get("name") or "").strip()
        row = rows.get(f"uid:{uid}") if uid else None
        if row is None:
            row = rows.get(f"name:{name.casefold()}")
        if not isinstance(row, Mapping):
            continue
        try:
            raw_value = row.get("db_average", row.get("legacy_db_average"))
            if raw_value is None and include_houses is not None:
                mode = "with_houses" if include_houses else "without_houses"
                distribution = row.get("distributions", {}).get(mode, {})
                if distribution.get("sample_size", 0) > 0:
                    raw_value = distribution.get("mean")
            value = float(raw_value)
        except (KeyError, ValueError, TypeError):
            continue
        if math.isfinite(value):
            result[name] = value
    return result


def trait_norm_signature(trait: Mapping[str, Any], snapshot: Mapping[str, Any] | None = None) -> str:
    snapshot = snapshot if snapshot is not None else prediction_norms_reference()
    return stable_hash({"uid": trait.get("uid") or trait.get("trait_uid"),
        "values": [list(trait_norm_values([dict(trait)], snapshot, include_houses=mode).values()) for mode in (False, True)]})


def prediction_norms_reference() -> Mapping[str, Any]:
    """Borrow the loaded reference for read-only numerical work (no JSON copy)."""
    from types import MappingProxyType
    paths = default_norm_paths()
    return MappingProxyType(_snapshot(paths, selected_norm_source(paths), True))


_distinguishing_references: dict[int, tuple[tuple[dict[str, Any], ...], str]] = {}


def distinguishing_norm_reference() -> tuple[tuple[dict[str, Any], ...], str]:
    """Return only the static Distinguishing Factors section and its identity."""
    paths = default_norm_paths()
    snapshot = _snapshot(paths, selected_norm_source(paths), True)
    with _lock:
        key = id(snapshot)
        if key not in _distinguishing_references:
            payloads = tuple(value for value in snapshot.get('distinguishing_metric_payloads', ()) if isinstance(value, dict))
            _distinguishing_references[key] = (payloads, stable_hash(payloads))
            if len(_distinguishing_references) > 8:
                _distinguishing_references.pop(next(iter(_distinguishing_references)))
        return _distinguishing_references[key]
