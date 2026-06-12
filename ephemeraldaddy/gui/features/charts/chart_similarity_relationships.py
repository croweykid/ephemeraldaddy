"""Persistent user-scored similarity relationships between chart pairs."""

from __future__ import annotations

import datetime as _datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

CHART_SIMILARITY_RELATIONSHIPS_PATH_ENV = "EPHEMERALDADDY_CHART_SIMILARITY_RELATIONSHIPS_PATH"
CHART_SIMILARITY_RELATIONSHIPS_FILENAME = "chart_similarity_relationships.json"
_LEGACY_SIMILARITIES_ALGORITHM_LOG_PATH_ENV = "EPHEMERALDADDY_SIMILARITIES_ALGORITHM_LOG_PATH"
_LEGACY_SIMILARITIES_ALGORITHM_LOG_FILENAME = "similarities_algorithm_log.txt"


def resolve_chart_similarity_relationships_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Return the independent JSON file path for user-scored chart relationships."""
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(CHART_SIMILARITY_RELATIONSHIPS_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / CHART_SIMILARITY_RELATIONSHIPS_FILENAME


def _coerce_chart_uid(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    normalized = "".join(character for character in text if character.isalnum())
    return normalized or None


def chart_similarity_relationship_key(
    *,
    chart_1_id: int | None,
    chart_2_id: int | None,
    chart_1_uid: str | None = None,
    chart_2_uid: str | None = None,
) -> str:
    """Return the stable chart-pair key for user-perceived similarity.

    New relationship records prefer immutable chart UIDs. Integer IDs remain
    supported for legacy logs and for UI alias lookups during migration.
    """

    first_uid = _coerce_chart_uid(chart_1_uid)
    second_uid = _coerce_chart_uid(chart_2_uid)
    if first_uid and second_uid:
        first, second = sorted((first_uid, second_uid))
        return f"uid:{first}|uid:{second}"

    def _id_token(value: int | None) -> str:
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return "unknown"

    raw_first = _id_token(chart_1_id)
    raw_second = _id_token(chart_2_id)
    if raw_first != "unknown" and raw_second != "unknown":
        first, second = sorted((raw_first, raw_second), key=int)
    else:
        first, second = raw_first, raw_second
    return f"{first}|{second}"


def _coerce_chart_id(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _utc_timestamp(timestamp: _datetime.datetime | None = None) -> str:
    if timestamp is None:
        timestamp = _datetime.datetime.now(_datetime.timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=_datetime.timezone.utc)
    return timestamp.astimezone(_datetime.timezone.utc).isoformat(timespec="seconds")


def _score_value(user_reported_accuracy: int | None, not_applicable: bool) -> int | None:
    if not_applicable or user_reported_accuracy is None:
        return None
    score = int(user_reported_accuracy)
    if not 0 <= score <= 100:
        raise ValueError("user_reported_accuracy must be an integer from 0 to 100")
    return score


def _empty_relationship_file() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "description": "User-scored perceived similarity relationships between stable chart UIDs, with legacy integer IDs retained as metadata.",
        "relationships": {},
    }


def _read_relationship_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_relationship_file()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_relationship_file()
    if not isinstance(payload, dict):
        return _empty_relationship_file()
    relationships = payload.get("relationships")
    if not isinstance(relationships, dict):
        payload["relationships"] = {}
    payload.setdefault("schema_version", 1)
    return payload


def save_chart_similarity_relationship(
    *,
    chart_1_id: int | None,
    chart_1_name: str,
    chart_2_id: int | None,
    chart_2_name: str,
    chart_1_uid: str | None = None,
    chart_2_uid: str | None = None,
    user_reported_accuracy: int | None = None,
    not_applicable: bool,
    path: str | os.PathLike[str] | None = None,
    timestamp: _datetime.datetime | None = None,
) -> Path:
    """Persist the user's perceived-similarity relationship for a pair of charts."""
    relationships_path = resolve_chart_similarity_relationships_path(path)
    relationships_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_relationship_file(relationships_path)
    relationships = payload.setdefault("relationships", {})
    if not isinstance(relationships, dict):
        relationships = {}
        payload["relationships"] = relationships

    first_id = _coerce_chart_id(chart_1_id)
    second_id = _coerce_chart_id(chart_2_id)
    first_uid = _coerce_chart_uid(chart_1_uid)
    second_uid = _coerce_chart_uid(chart_2_uid)
    key = chart_similarity_relationship_key(
        chart_1_id=first_id,
        chart_2_id=second_id,
        chart_1_uid=first_uid,
        chart_2_uid=second_uid,
    )
    legacy_key = chart_similarity_relationship_key(chart_1_id=first_id, chart_2_id=second_id)
    if key != legacy_key:
        relationships.pop(legacy_key, None)
    score = _score_value(user_reported_accuracy, bool(not_applicable))
    timestamp_text = _utc_timestamp(timestamp)
    user_knows_similarity = bool(score is not None and not not_applicable)
    del chart_1_name, chart_2_name

    relationships[key] = {
        "relationship_key": key,
        "chart_uids": [first_uid, second_uid] if first_uid and second_uid else [],
        "chart_ids": [first_id, second_id],
        "user_knows_similarity": user_knows_similarity,
        "user_perceived_similarity_score": score,
        "user_reported_accuracy": score,
        "not_applicable": bool(not_applicable),
        "updated_at_utc": timestamp_text,
    }
    payload["schema_version"] = 2
    payload["updated_at_utc"] = timestamp_text

    temporary_path = relationships_path.with_suffix(relationships_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(relationships_path)
    return relationships_path

def migrate_chart_similarity_relationship_file_to_chart_uids(
    *,
    chart_id_to_uid: Mapping[int, str],
    path: str | os.PathLike[str] | None = None,
) -> Path:
    """Rewrite existing relationship JSON records from integer keys to UID keys.

    Integer chart IDs are retained as metadata and lookup aliases, but the stored
    relationship key becomes UID-backed when both chart IDs can be resolved.
    """
    relationships_path = resolve_chart_similarity_relationships_path(path)
    payload = _read_relationship_file(relationships_path)
    relationships = payload.setdefault("relationships", {})
    if not isinstance(relationships, dict):
        relationships = {}
        payload["relationships"] = relationships

    normalized_map = {
        int(chart_id): uid
        for chart_id, raw_uid in chart_id_to_uid.items()
        if (uid := _coerce_chart_uid(raw_uid))
    }
    migrated: dict[str, Any] = {}
    changed = False
    for original_key, raw_state in relationships.items():
        if not isinstance(raw_state, Mapping):
            migrated[str(original_key)] = raw_state
            continue
        state = dict(raw_state)
        chart_ids = state.get("chart_ids") if isinstance(state.get("chart_ids"), list) else []
        first_id = _coerce_chart_id(chart_ids[0]) if len(chart_ids) > 0 else None
        second_id = _coerce_chart_id(chart_ids[1]) if len(chart_ids) > 1 else None
        first_uid = _coerce_chart_uid((state.get("chart_uids") or [None, None])[0]) if isinstance(state.get("chart_uids"), list) and len(state.get("chart_uids") or []) > 0 else None
        second_uid = _coerce_chart_uid((state.get("chart_uids") or [None, None])[1]) if isinstance(state.get("chart_uids"), list) and len(state.get("chart_uids") or []) > 1 else None
        first_uid = first_uid or (normalized_map.get(first_id) if first_id is not None else None)
        second_uid = second_uid or (normalized_map.get(second_id) if second_id is not None else None)
        new_key = chart_similarity_relationship_key(
            chart_1_id=first_id,
            chart_2_id=second_id,
            chart_1_uid=first_uid,
            chart_2_uid=second_uid,
        )
        if first_uid and second_uid:
            state["chart_uids"] = [first_uid, second_uid]
        state["relationship_key"] = new_key
        if new_key != original_key or state != raw_state:
            changed = True
        migrated[new_key if new_key != "unknown|unknown" else str(original_key)] = state

    if changed:
        relationships_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp_text = _utc_timestamp()
        payload["schema_version"] = 2
        payload["relationships"] = migrated
        payload["updated_at_utc"] = timestamp_text
        temporary_path = relationships_path.with_suffix(relationships_path.suffix + ".tmp")
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary_path.replace(relationships_path)
    return relationships_path


def _resolve_legacy_algorithm_log_path(path: str | os.PathLike[str] | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get(_LEGACY_SIMILARITIES_ALGORITHM_LOG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".ephemeraldaddy" / _LEGACY_SIMILARITIES_ALGORITHM_LOG_FILENAME


def _legacy_relationship_from_payload(payload: Mapping[str, Any]) -> tuple[str, dict[str, Any]] | None:
    pair = payload.get("chart_1_compared_with_chart_2", {})
    if not isinstance(pair, Mapping):
        return None
    chart_1 = pair.get("chart_1", {})
    chart_2 = pair.get("chart_2", {})
    if not isinstance(chart_1, Mapping) or not isinstance(chart_2, Mapping):
        return None
    first_id = _coerce_chart_id(chart_1.get("id"))
    second_id = _coerce_chart_id(chart_2.get("id"))
    key = chart_similarity_relationship_key(chart_1_id=first_id, chart_2_id=second_id)
    not_applicable = bool(payload.get("not_applicable", False))
    raw_score = payload.get("user_reported_accuracy")
    try:
        score = _score_value(raw_score if raw_score is not None else None, not_applicable)
    except (TypeError, ValueError):
        score = None
    state = {
        "relationship_key": key,
        "chart_uids": [],
        "chart_ids": [first_id, second_id],
        "user_knows_similarity": bool(score is not None and not not_applicable),
        "user_perceived_similarity_score": score,
        "user_reported_accuracy": score,
        "not_applicable": not_applicable,
        "updated_at_utc": str(payload.get("timestamp_utc") or ""),
        "source": "legacy_similarities_algorithm_log",
    }
    return key, state


def _load_legacy_similarity_relationship_states(
    path: str | os.PathLike[str] | None = None,
) -> dict[str, dict[str, Any]]:
    legacy_path = _resolve_legacy_algorithm_log_path(path)
    if not legacy_path.exists():
        return {}
    try:
        content = legacy_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    states: dict[str, dict[str, Any]] = {}
    decoder = json.JSONDecoder()
    marker = "Perceived accuracy payload:\n"
    cursor = 0
    while True:
        marker_index = content.find(marker, cursor)
        if marker_index < 0:
            break
        payload_start = marker_index + len(marker)
        try:
            legacy_payload, end_offset = decoder.raw_decode(content[payload_start:])
        except json.JSONDecodeError:
            cursor = payload_start
            continue
        cursor = payload_start + end_offset
        if not isinstance(legacy_payload, Mapping):
            continue
        relationship = _legacy_relationship_from_payload(legacy_payload)
        if relationship is None:
            continue
        key, state = relationship
        states[key] = state
    return states


def load_chart_similarity_relationship_states(
    path: str | os.PathLike[str] | None = None,
    *,
    include_legacy_algorithm_log: bool = True,
    legacy_algorithm_log_path: str | os.PathLike[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Load latest user-scored chart-pair relationships by stable relationship key."""
    states = (
        _load_legacy_similarity_relationship_states(legacy_algorithm_log_path)
        if include_legacy_algorithm_log
        else {}
    )
    payload = _read_relationship_file(resolve_chart_similarity_relationships_path(path))
    relationships = payload.get("relationships", {})
    if not isinstance(relationships, Mapping):
        return states
    for key, state in relationships.items():
        if isinstance(state, Mapping):
            chart_ids = state.get("chart_ids") if isinstance(state.get("chart_ids"), list) else []
            chart_uids = state.get("chart_uids") if isinstance(state.get("chart_uids"), list) else []
            first_id = chart_ids[0] if len(chart_ids) > 0 else None
            second_id = chart_ids[1] if len(chart_ids) > 1 else None
            first_uid = chart_uids[0] if len(chart_uids) > 0 else None
            second_uid = chart_uids[1] if len(chart_uids) > 1 else None
            normalized_key = chart_similarity_relationship_key(
                chart_1_id=first_id,
                chart_2_id=second_id,
                chart_1_uid=first_uid,
                chart_2_uid=second_uid,
            )
            state_copy = dict(state)
            states[normalized_key if normalized_key != "unknown|unknown" else str(key)] = state_copy
            legacy_key = chart_similarity_relationship_key(
                chart_1_id=first_id,
                chart_2_id=second_id,
            )
            if legacy_key != "unknown|unknown":
                states[legacy_key] = state_copy
    return states


def perceived_accuracy_state_key(
    *,
    chart_1_id: int | None,
    chart_2_id: int | None,
    chart_1_uid: str | None = None,
    chart_2_uid: str | None = None,
    analysis_context: str | None = None,
) -> str:
    """Return the relationship key used by existing perceived-accuracy UI code."""
    del analysis_context
    return chart_similarity_relationship_key(
        chart_1_id=chart_1_id,
        chart_2_id=chart_2_id,
        chart_1_uid=chart_1_uid,
        chart_2_uid=chart_2_uid,
    )


load_similarity_perceived_accuracy_states = load_chart_similarity_relationship_states
