"""Hidden sidecar storage for Chart View material facts.

These helpers intentionally keep personally identifying material facts outside
the main astrological SQLite database.  The files live next to ``charts.db``
and are keyed by stable chart UID.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ephemeraldaddy.core.db import DB_PATH, get_chart_uid

PERSONAL_IDENTIFIERS_FILENAME = "charts.personal_identifiers.json"
IDENTIFIER_FIELDS: tuple[str, ...] = (
    "addresses",
    "emails",
    "websites",
    "phone_numbers",
)


def _sidecar_path(filename: str) -> Path:
    return DB_PATH.with_name(filename)


def personal_identifiers_path() -> Path:
    return _sidecar_path(PERSONAL_IDENTIFIERS_FILENAME)


def _load_sidecar(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _save_sidecar(path: Path, payload: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _clean_multiline_text(value: object) -> str:
    return "\n".join(
        line.strip()
        for line in str(value or "").splitlines()
        if line.strip()
    )


def _normalize_facts(raw: dict[str, Any], fields: tuple[str, ...]) -> dict[str, str]:
    return {
        field: _clean_multiline_text(raw.get(field, ""))
        for field in fields
    }


def _clean_chart_uid(chart_uid: str | None) -> str | None:
    text = str(chart_uid or "").strip().upper()
    return text or None


def _legacy_chart_id_key(chart_id: int | None) -> str | None:
    if chart_id is None:
        return None
    try:
        return str(int(chart_id))
    except (TypeError, ValueError):
        return None


def load_personal_identifiers_by_uid(chart_uid: str | None) -> dict[str, str]:
    facts = {field: "" for field in IDENTIFIER_FIELDS}
    normalized_uid = _clean_chart_uid(chart_uid)
    if normalized_uid is None:
        return facts
    facts.update(_normalize_facts(_load_sidecar(personal_identifiers_path()).get(normalized_uid, {}), IDENTIFIER_FIELDS))
    return facts


def save_personal_identifiers_by_uid(chart_uid: str | None, facts: dict[str, Any]) -> None:
    normalized_uid = _clean_chart_uid(chart_uid)
    if normalized_uid is None:
        return
    path = personal_identifiers_path()
    payload = _load_sidecar(path)
    normalized = _normalize_facts(facts, IDENTIFIER_FIELDS)
    if any(normalized.values()):
        payload[normalized_uid] = normalized
    else:
        payload.pop(normalized_uid, None)
    _save_sidecar(path, payload)


def load_personal_identifiers(chart_id: int | None) -> dict[str, str]:
    chart_uid = get_chart_uid(chart_id)
    facts = load_personal_identifiers_by_uid(chart_uid)
    legacy_key = _legacy_chart_id_key(chart_id)
    if any(facts.values()) or legacy_key is None:
        return facts
    payload = _load_sidecar(personal_identifiers_path())
    legacy_facts = _normalize_facts(payload.get(legacy_key, {}), IDENTIFIER_FIELDS)
    if any(legacy_facts.values()) and chart_uid:
        save_personal_identifiers_by_uid(chart_uid, legacy_facts)
        payload = _load_sidecar(personal_identifiers_path())
        payload.pop(legacy_key, None)
        _save_sidecar(personal_identifiers_path(), payload)
    return legacy_facts


def save_personal_identifiers(chart_id: int, facts: dict[str, Any]) -> None:
    chart_uid = get_chart_uid(chart_id)
    save_personal_identifiers_by_uid(chart_uid, facts)
    legacy_key = _legacy_chart_id_key(chart_id)
    if legacy_key is not None:
        path = personal_identifiers_path()
        payload = _load_sidecar(path)
        if legacy_key in payload:
            payload.pop(legacy_key, None)
            _save_sidecar(path, payload)
