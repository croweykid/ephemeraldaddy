"""Chart-scoped perceived-accuracy metadata.

Ratings are intentionally stored outside the astronomical chart payload. They are
subjective annotations keyed by stable chart UID, so recording or clearing one
never requires recalculating a chart.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

PerceivedAccuracyScope = Literal["modules", "properties"]
PERCEIVED_ACCURACY_VERSION = 1
_TABLE_NAME = "chart_perceived_accuracy_metadata"
_ROOT_KEY = "perceived_accuracy"
_VALID_SCOPES: frozenset[str] = frozenset({"modules", "properties"})


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_chart_uid(chart_uid: object) -> str:
    normalized = "".join(
        character
        for character in str(chart_uid or "").strip().upper()
        if character.isalnum()
    )
    if len(normalized) < 8:
        raise ValueError(f"Invalid chart UID {chart_uid!r}")
    return normalized[:64]


def _normalize_scope(scope: object) -> PerceivedAccuracyScope:
    normalized = str(scope or "").strip().lower()
    if normalized not in _VALID_SCOPES:
        raise ValueError(f"Invalid perceived-accuracy scope {scope!r}")
    return normalized  # type: ignore[return-value]


def _normalize_key(key: object) -> str:
    normalized = str(key or "").strip()
    if not normalized:
        raise ValueError("Perceived-accuracy key must not be blank")
    return normalized[:240]


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    # Import lazily so the lightweight GUI bootstrap does not pull the complete
    # database/chart stack into memory before the startup window is visible.
    from ephemeraldaddy.core.db import DB_PATH

    return Path(DB_PATH)


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
            chart_uid  TEXT PRIMARY KEY,
            payload    TEXT NOT NULL DEFAULT '{{}}',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _empty_payload() -> dict[str, Any]:
    return {
        _ROOT_KEY: {
            "modules": {},
            "properties": {},
        }
    }


def _coerce_payload(raw_payload: object) -> dict[str, Any]:
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    root = payload.get(_ROOT_KEY)
    if not isinstance(root, dict):
        root = {}
    modules = root.get("modules")
    properties = root.get("properties")
    return {
        _ROOT_KEY: {
            "modules": dict(modules) if isinstance(modules, dict) else {},
            "properties": dict(properties) if isinstance(properties, dict) else {},
        }
    }


def load_perceived_accuracy(
    chart_uid: object,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the normalized perceived-accuracy payload for one chart UID."""
    normalized_uid = _normalize_chart_uid(chart_uid)
    conn = _connect(db_path)
    try:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT payload FROM {_TABLE_NAME} WHERE chart_uid = ?",
            (normalized_uid,),
        ).fetchone()
        if row is None:
            return _empty_payload()
        try:
            decoded = json.loads(str(row[0] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            decoded = {}
        return _coerce_payload(decoded)
    finally:
        conn.close()


def get_perceived_accuracy_value(
    chart_uid: object,
    scope: PerceivedAccuracyScope,
    key: object,
    *,
    db_path: str | Path | None = None,
) -> bool | None:
    """Return True, False, or None when the target is unrated."""
    normalized_scope = _normalize_scope(scope)
    normalized_key = _normalize_key(key)
    payload = load_perceived_accuracy(chart_uid, db_path=db_path)
    record = payload[_ROOT_KEY][normalized_scope].get(normalized_key)
    if not isinstance(record, dict):
        return None
    value = record.get("value")
    return value if isinstance(value, bool) else None


def _payload_has_ratings(payload: dict[str, Any]) -> bool:
    root = payload.get(_ROOT_KEY, {})
    if not isinstance(root, dict):
        return False
    return any(bool(root.get(scope)) for scope in _VALID_SCOPES)


def _write_payload(
    chart_uid: str,
    payload: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> None:
    conn = _connect(db_path)
    try:
        with conn:
            _ensure_table(conn)
            if not _payload_has_ratings(payload):
                conn.execute(
                    f"DELETE FROM {_TABLE_NAME} WHERE chart_uid = ?",
                    (chart_uid,),
                )
                return
            updated_at = _utc_timestamp()
            conn.execute(
                f"""
                INSERT INTO {_TABLE_NAME} (chart_uid, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chart_uid) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    chart_uid,
                    json.dumps(payload, separators=(",", ":"), sort_keys=True),
                    updated_at,
                ),
            )
    finally:
        conn.close()


def toggle_perceived_accuracy(
    chart_uid: object,
    scope: PerceivedAccuracyScope,
    key: object,
    value: bool,
    *,
    version: int = PERCEIVED_ACCURACY_VERSION,
    db_path: str | Path | None = None,
) -> bool | None:
    """Toggle a perceived-accuracy rating and return its resulting state.

    Clicking the already-selected value clears the rating completely. Clearing
    removes the target entry; if it was the chart's final rating, the metadata
    row itself is deleted as well.
    """
    if not isinstance(value, bool):
        raise TypeError("Perceived-accuracy value must be a bool")
    normalized_uid = _normalize_chart_uid(chart_uid)
    normalized_scope = _normalize_scope(scope)
    normalized_key = _normalize_key(key)
    normalized_version = max(1, int(version))

    payload = load_perceived_accuracy(normalized_uid, db_path=db_path)
    ratings = payload[_ROOT_KEY][normalized_scope]
    current = ratings.get(normalized_key)
    current_value = current.get("value") if isinstance(current, dict) else None

    if isinstance(current_value, bool) and current_value is value:
        ratings.pop(normalized_key, None)
        _write_payload(normalized_uid, payload, db_path=db_path)
        return None

    ratings[normalized_key] = {
        "value": value,
        "version": normalized_version,
        "rated_at": _utc_timestamp(),
    }
    _write_payload(normalized_uid, payload, db_path=db_path)
    return value
