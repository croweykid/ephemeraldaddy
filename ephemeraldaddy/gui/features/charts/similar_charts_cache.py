"""Session cache helpers for Similar Charts popout results."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ephemeraldaddy.analysis.get_astro_twin import normalize_similar_charts_algorithm_mode
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.db import DB_PATH

_CACHE_VERSION = "top-bottom-25-v2"


class SimilarChartsPopoutCache:
    """Bounded in-memory cache keyed by subject/settings/database signatures."""

    def __init__(self, *, max_entries: int = 20) -> None:
        self._max_entries = max(1, int(max_entries))
        self._cache: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self._lru: list[tuple[str, str, str, str]] = []

    def _database_signature(self) -> str:
        entries: list[tuple[str, int | None, int | None]] = []
        for path in (DB_PATH, Path(f"{DB_PATH}-wal")):
            try:
                stat = path.stat()
            except OSError:
                entries.append((str(path), None, None))
                continue
            entries.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
        encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _subject_signature(chart: Chart, *, subject_chart_id: int | None) -> str:
        dt_value = getattr(chart, "dt", None)
        payload = {
            "id": subject_chart_id,
            "name": str(getattr(chart, "name", "") or ""),
            "alias": str(getattr(chart, "alias", "") or ""),
            "dt": dt_value.isoformat() if dt_value is not None else None,
            "lat": round(float(getattr(chart, "lat", 0.0) or 0.0), 8),
            "lon": round(float(getattr(chart, "lon", 0.0) or 0.0), 8),
            "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
            "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
            "retcon_hour": getattr(chart, "retcon_hour", None),
            "retcon_minute": getattr(chart, "retcon_minute", None),
            "positions": sorted(
                (str(key), round(float(value), 8))
                for key, value in (getattr(chart, "positions", None) or {}).items()
            ),
            "houses": [round(float(value), 8) for value in (getattr(chart, "houses", None) or [])],
            "human_design_gates": list(getattr(chart, "human_design_gates", None) or []),
            "human_design_channels": list(getattr(chart, "human_design_channels", None) or []),
        }
        encoded = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _settings_signature(*, algorithm_mode: str, similarity_settings: Any) -> str:
        payload = {
            "algorithm_mode": normalize_similar_charts_algorithm_mode(algorithm_mode),
            "calculator": asdict(similarity_settings) if similarity_settings is not None else None,
        }
        encoded = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def build_key(
        self,
        *,
        chart: Chart,
        subject_chart_id: int | None,
        algorithm_mode: str,
        similarity_settings: Any,
    ) -> tuple[str, str, str, str]:
        return (
            self._subject_signature(chart, subject_chart_id=subject_chart_id),
            self._database_signature(),
            self._settings_signature(
                algorithm_mode=algorithm_mode,
                similarity_settings=similarity_settings,
            ),
            _CACHE_VERSION,
        )

    def get(self, key: tuple[str, str, str, str]) -> dict[str, Any] | None:
        payload = self._cache.get(key)
        if payload is None:
            return None
        if key in self._lru:
            self._lru.remove(key)
        self._lru.append(key)
        return copy.deepcopy(payload)

    def put(
        self,
        *,
        key: tuple[str, str, str, str],
        most_similar_matches: list[Any],
        least_similar_matches: list[Any],
    ) -> None:
        self._cache[key] = {
            "most_similar_matches": copy.deepcopy(list(most_similar_matches)),
            "least_similar_matches": copy.deepcopy(list(least_similar_matches)),
        }
        if key in self._lru:
            self._lru.remove(key)
        self._lru.append(key)
        while len(self._lru) > self._max_entries:
            evicted = self._lru.pop(0)
            self._cache.pop(evicted, None)
