"""Hidden sidecar storage for Chart View material facts.

These helpers intentionally keep personally identifying material facts outside
the main astrological SQLite database.  The files live next to ``charts.db``
and are keyed by chart id.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ephemeraldaddy.core.db import DB_PATH

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


def load_personal_identifiers(chart_id: int | None) -> dict[str, str]:
    facts = {field: "" for field in IDENTIFIER_FIELDS}
    if chart_id is None:
        return facts
    facts.update(_normalize_facts(_load_sidecar(personal_identifiers_path()).get(str(int(chart_id)), {}), IDENTIFIER_FIELDS))
    return facts


def save_personal_identifiers(chart_id: int, facts: dict[str, Any]) -> None:
    path = personal_identifiers_path()
    payload = _load_sidecar(path)
    normalized = _normalize_facts(facts, IDENTIFIER_FIELDS)
    chart_key = str(int(chart_id))
    if any(normalized.values()):
        payload[chart_key] = normalized
    else:
        payload.pop(chart_key, None)
    _save_sidecar(path, payload)
