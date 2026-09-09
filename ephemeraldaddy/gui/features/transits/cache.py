"""Cache helpers for expensive Transit View and Personal Timeline calculations."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping

from ephemeraldaddy.core.composite import TRANSIT_ASPECT_RULES
from ephemeraldaddy.core.db import DB_DIR
from ephemeraldaddy.gui.features.retcon.transit_window import TRANSIT_WINDOW_CACHE_LIMIT


PERSONAL_TIMELINE_CACHE_SCHEMA = "ephemeraldaddy.personal-timeline-cache"
PERSONAL_TIMELINE_CACHE_SCHEMA_VERSION = 1
PERSONAL_TIMELINE_CACHE_DIR = DB_DIR / "cache" / "personal_timeline"


class TransitWindowCache:
    """Owns transit-window cache keys, cached payloads, and metrics."""

    def __init__(self, *, limit: int = TRANSIT_WINDOW_CACHE_LIMIT) -> None:
        self.limit = int(limit)
        self.results: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()
        self.metrics: dict[str, int | float] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "inflight_dedupes": 0,
            "completed_requests": 0,
        }

    def build_key(
        self,
        *,
        mode: str,
        hit_obj: Any,
        chart_dt: _dt.datetime,
        transit_location: tuple[float, float],
        mode_rules: dict[str, Any],
        scan_config: Any,
    ) -> tuple[object, ...]:
        chart_dt_utc = (
            chart_dt.astimezone(_dt.timezone.utc)
            if chart_dt.tzinfo
            else chart_dt.replace(tzinfo=_dt.timezone.utc)
        )
        rules = mode_rules.get(mode, TRANSIT_ASPECT_RULES)
        return (
            mode,
            hit_obj.a.name,
            hit_obj.aspect,
            hit_obj.b.name,
            chart_dt_utc.isoformat(),
            round(float(transit_location[0]), 4),
            round(float(transit_location[1]), 4),
            tuple(
                (asp.name, float(asp.angle_deg), float(asp.orb_deg))
                for asp in rules.aspect_types
            ),
            float(scan_config.scan_step_hours),
            float(scan_config.scan_precision_minutes),
        )

    def get(self, cache_key: tuple[object, ...]) -> dict[str, object] | None:
        cached = self.results.get(cache_key)
        if cached is None:
            self.metrics["cache_misses"] = int(self.metrics["cache_misses"]) + 1
            return None
        self.metrics["cache_hits"] = int(self.metrics["cache_hits"]) + 1
        self.results.move_to_end(cache_key)
        return dict(cached)

    def put(self, cache_key: tuple[object, ...], payload: dict[str, object]) -> None:
        self.results[cache_key] = dict(payload)
        self.results.move_to_end(cache_key)
        self.metrics["completed_requests"] = int(self.metrics["completed_requests"]) + 1
        while len(self.results) > self.limit:
            self.results.popitem(last=False)

    def record_inflight_dedupe(self) -> None:
        self.metrics["inflight_dedupes"] = int(self.metrics["inflight_dedupes"]) + 1


def _normalized_chart_uid(value: object) -> str:
    return str(value or "").strip().upper()


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _datetime_payload(value: object) -> str | None:
    if not isinstance(value, _dt.datetime):
        return None
    return value.isoformat()


def _timezone_payload(value: object) -> dict[str, object] | None:
    """Return stable timezone identity for Personal Timeline cache invalidation.

    ``datetime.isoformat()`` records only the offset at that instant. Two named
    zones can share that offset at birth while following different DST rules
    later in life, which would make their generated Timeline windows differ.
    """
    if not isinstance(value, _dt.datetime) or value.tzinfo is None:
        return None

    tzinfo = value.tzinfo
    key = getattr(tzinfo, "key", None)
    if key:
        return {"kind": "iana", "key": str(key)}

    zone = getattr(tzinfo, "zone", None)
    if zone:
        return {"kind": "named", "key": str(zone)}

    offset = value.utcoffset()
    offset_seconds = offset.total_seconds() if offset is not None else None
    return {
        "kind": "other",
        "type": f"{type(tzinfo).__module__}.{type(tzinfo).__qualname__}",
        "name": value.tzname(),
        "offset_seconds": offset_seconds,
        "display": str(tzinfo),
    }


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


def personal_timeline_fingerprint(
    chart_uid: str,
    chart: Any,
    generation_config: Mapping[str, object],
) -> str:
    """Hash only inputs that can change Personal Timeline generation.

    Non-astral chart metadata is intentionally absent. A saved change to birth
    data, timezone rules, natal positions, death bounds, or generation
    configuration produces a different fingerprint and therefore a cache miss.
    """
    positions: dict[str, float | None] = {}
    for body, longitude in sorted(
        dict(getattr(chart, "positions", {}) or {}).items(),
        key=lambda item: str(item[0]),
    ):
        positions[str(body)] = _safe_float(longitude)

    birth_datetime = getattr(chart, "dt", None)
    payload = {
        "chart_uid": _normalized_chart_uid(chart_uid),
        "birth_datetime": _datetime_payload(birth_datetime),
        "birth_timezone": _timezone_payload(birth_datetime),
        "lat": _safe_float(getattr(chart, "lat", None)),
        "lon": _safe_float(getattr(chart, "lon", None)),
        "positions": positions,
        "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
        "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
        "retcon_hour": getattr(chart, "retcon_hour", None),
        "retcon_minute": getattr(chart, "retcon_minute", None),
        "rectification_range_used": bool(
            getattr(chart, "rectification_range_used", False)
        ),
        "rectification_range_start_minute": getattr(
            chart, "rectification_range_start_minute", None
        ),
        "rectification_range_end_minute": getattr(
            chart, "rectification_range_end_minute", None
        ),
        "signs_unknown": bool(getattr(chart, "signs_unknown", False)),
        "unknown_signs": sorted(
            str(item) for item in (getattr(chart, "unknown_signs", []) or [])
        ),
        "is_deceased": bool(getattr(chart, "is_deceased", False)),
        "death_year": getattr(chart, "death_year", None),
        "death_month": getattr(chart, "death_month", None),
        "death_day": getattr(chart, "death_day", None),
        "generation": _json_safe(generation_config),
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def personal_timeline_cache_path(
    chart_uid: str,
    *,
    cache_dir: Path = PERSONAL_TIMELINE_CACHE_DIR,
) -> Path:
    normalized_uid = _normalized_chart_uid(chart_uid)
    if not normalized_uid:
        raise ValueError("Personal Timeline cache requires a Chart UID.")
    digest = hashlib.sha256(normalized_uid.encode("utf-8")).hexdigest()
    return Path(cache_dir) / f"{digest}.json"


def _serialize_personal_timeline_window(window: Any) -> dict[str, object]:
    transit = getattr(window, "transit")
    start = getattr(window, "start")
    end = getattr(window, "end")
    if not isinstance(start, _dt.datetime) or not isinstance(end, _dt.datetime):
        raise TypeError("Personal Timeline cache windows require datetime bounds.")
    return {
        "chart_uid": _normalized_chart_uid(getattr(window, "chart_uid", "")),
        "transit": {
            "transiting_body": str(getattr(transit, "transiting_body")),
            "natal_body": str(getattr(transit, "natal_body")),
            "natal_longitude": float(getattr(transit, "natal_longitude")),
            "aspect_name": str(getattr(transit, "aspect_name")),
            "aspect_angle": float(getattr(transit, "aspect_angle")),
            "orb_deg": float(getattr(transit, "orb_deg")),
        },
        "start": start.isoformat(),
        "end": end.isoformat(),
        "start_truncated": bool(getattr(window, "start_truncated", False)),
        "end_truncated": bool(getattr(window, "end_truncated", False)),
    }


class PersonalTimelineDiskCache:
    """Permanent per-chart cache for generated Personal Timeline windows."""

    def __init__(self, *, cache_dir: Path = PERSONAL_TIMELINE_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)

    def path_for(self, chart_uid: str) -> Path:
        return personal_timeline_cache_path(chart_uid, cache_dir=self.cache_dir)

    def get(
        self,
        chart_uid: str,
        fingerprint: str,
    ) -> list[dict[str, object]] | None:
        path = self.path_for(chart_uid)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("schema") != PERSONAL_TIMELINE_CACHE_SCHEMA:
            return None
        if payload.get("schema_version") != PERSONAL_TIMELINE_CACHE_SCHEMA_VERSION:
            return None
        if payload.get("chart_uid") != _normalized_chart_uid(chart_uid):
            return None
        if payload.get("fingerprint") != str(fingerprint):
            return None
        windows = payload.get("windows")
        if not isinstance(windows, list) or not all(isinstance(item, dict) for item in windows):
            return None
        return [dict(item) for item in windows]

    def put(
        self,
        chart_uid: str,
        fingerprint: str,
        windows: Iterable[Any],
    ) -> Path:
        path = self.path_for(chart_uid)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": PERSONAL_TIMELINE_CACHE_SCHEMA,
            "schema_version": PERSONAL_TIMELINE_CACHE_SCHEMA_VERSION,
            "chart_uid": _normalized_chart_uid(chart_uid),
            "fingerprint": str(fingerprint),
            "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "windows": [
                _serialize_personal_timeline_window(window) for window in windows
            ],
        }

        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.stem}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name is not None:
                try:
                    Path(temp_name).unlink()
                except OSError:
                    pass
        return path

    def invalidate(self, chart_uid: str) -> None:
        try:
            self.path_for(chart_uid).unlink()
        except FileNotFoundError:
            pass
