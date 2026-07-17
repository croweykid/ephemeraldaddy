# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
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
    "unlisted_relatives",
)
RELATIVE_UIDS_FIELD = "linked_relative_uids"


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


def _normalize_relative_uids(value: object) -> list[str]:
    if isinstance(value, str):
        candidates = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        candidates = []
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        uid = _clean_chart_uid(str(candidate or ""))
        if uid is None or uid in seen:
            continue
        normalized.append(uid)
        seen.add(uid)
    return normalized


def _normalize_facts(raw: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    facts: dict[str, Any] = {
        field: _clean_multiline_text(raw.get(field, ""))
        for field in fields
    }
    facts[RELATIVE_UIDS_FIELD] = _normalize_relative_uids(raw.get(RELATIVE_UIDS_FIELD, []))
    return facts


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


def load_personal_identifiers_by_uid(chart_uid: str | None) -> dict[str, Any]:
    facts: dict[str, Any] = {field: "" for field in IDENTIFIER_FIELDS}
    facts[RELATIVE_UIDS_FIELD] = []
    normalized_uid = _clean_chart_uid(chart_uid)
    if normalized_uid is None:
        return facts
    facts.update(_normalize_facts(_load_sidecar(personal_identifiers_path()).get(normalized_uid, {}), IDENTIFIER_FIELDS))
    return facts



def load_linked_relative_uids_by_uid(chart_uid: str | None) -> list[str]:
    """Return direct and reciprocal database-relative UID links for a chart.

    Relationship links are treated as bidirectional for display: if chart A
    links chart B, chart B should also show chart A in Chart View's Material
    Facts Relationships section even when chart B has not explicitly saved the
    reverse link.
    """
    normalized_uid = _clean_chart_uid(chart_uid)
    if normalized_uid is None:
        return []

    payload = _load_sidecar(personal_identifiers_path())
    direct_uids = _normalize_relative_uids(
        payload.get(normalized_uid, {}).get(RELATIVE_UIDS_FIELD, [])
    )
    linked_uids: list[str] = []
    seen: set[str] = set()

    def add_uid(uid: str | None) -> None:
        if uid is None or uid == normalized_uid or uid in seen:
            return
        linked_uids.append(uid)
        seen.add(uid)

    for uid in direct_uids:
        add_uid(uid)

    for source_uid, facts in payload.items():
        clean_source_uid = _clean_chart_uid(source_uid)
        if clean_source_uid is None or clean_source_uid == normalized_uid:
            continue
        source_relative_uids = _normalize_relative_uids(facts.get(RELATIVE_UIDS_FIELD, []))
        if normalized_uid in source_relative_uids:
            add_uid(clean_source_uid)

    return linked_uids

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


def load_personal_identifiers(chart_id: int | None) -> dict[str, Any]:
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
