"""Persistent user-scored similarity relationships between chart pairs."""

from __future__ import annotations

import datetime as _datetime
import json
from dataclasses import asdict, dataclass
import os
from pathlib import Path
from typing import Any, Mapping

from ephemeraldaddy.core.db import get_chart_display_name_map, get_chart_uid_map

CHART_SIMILARITY_RELATIONSHIPS_PATH_ENV = "EPHEMERALDADDY_CHART_SIMILARITY_RELATIONSHIPS_PATH"
CHART_SIMILARITY_RELATIONSHIPS_FILENAME = "chart_similarity_relationships.json"
_LEGACY_SIMILARITIES_ALGORITHM_LOG_PATH_ENV = "EPHEMERALDADDY_SIMILARITIES_ALGORITHM_LOG_PATH"
_LEGACY_SIMILARITIES_ALGORITHM_LOG_FILENAME = "similarities_algorithm_log.txt"


@dataclass(frozen=True)
class ChartSimilarityRelationshipConversionIssue:
    relationship_key: str
    chart_ids: list[int | None]
    chart_names: list[str]
    reason: str


@dataclass(frozen=True)
class ChartSimilarityRelationshipConversionReport:
    relationship_path: str
    report_path: str
    backup_path: str
    uid_backed_relationships: int
    legacy_key_relationships: int
    issue_count: int
    issues: list[ChartSimilarityRelationshipConversionIssue]


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


def _read_relationship_file_strict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_relationship_file()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse {path} as JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}. "
            "The conversion was not run and the relationship log was left unchanged."
        ) from exc
    except OSError as exc:
        raise OSError(f"Could not read relationship log {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"Relationship log {path} must contain a JSON object at the top level; "
            f"found {type(payload).__name__}. The conversion was not run."
        )
    relationships = payload.get("relationships")
    if relationships is not None and not isinstance(relationships, dict):
        raise ValueError(
            f"Relationship log {path} has a non-object 'relationships' value "
            f"({type(relationships).__name__}). The conversion was not run."
        )
    payload.setdefault("relationships", {})
    payload.setdefault("schema_version", 1)
    return payload


def _legacy_chart_ids_from_key(key: object) -> tuple[int | None, int | None]:
    parts = str(key or "").split("|")
    if len(parts) < 2:
        return None, None
    return _coerce_chart_id(parts[0]), _coerce_chart_id(parts[1])


def _backup_relationship_file_before_uid_migration(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_name(f"{path.stem}.pre_uid_migration{path.suffix}")
    if backup_path.exists():
        return backup_path
    backup_path.write_bytes(path.read_bytes())
    return backup_path


def _chart_ids_from_relationship_state(
    state: Mapping[str, Any],
    relationship_key: object,
) -> tuple[int | None, int | None]:
    chart_ids = state.get("chart_ids") if isinstance(state.get("chart_ids"), list) else []
    first_id = _coerce_chart_id(chart_ids[0]) if len(chart_ids) > 0 else None
    second_id = _coerce_chart_id(chart_ids[1]) if len(chart_ids) > 1 else None
    if first_id is not None and second_id is not None:
        return first_id, second_id

    first_id, second_id = _legacy_chart_ids_from_key(relationship_key)
    if first_id is not None and second_id is not None:
        return first_id, second_id

    legacy_key = state.get("legacy_relationship_key")
    first_id, second_id = _legacy_chart_ids_from_key(legacy_key)
    return first_id, second_id



def translate_former_chart_similarity_relationship_ids(
    *,
    chart_id_to_uid: Mapping[int, str],
    path: str | os.PathLike[str] | None = None,
) -> dict[str, str]:
    """Return legacy integer relationship keys mapped to stable UID keys.

    The translator is deterministic when it is supplied the chart UID map from
    the same database that produced the former integer IDs. Relationships are
    returned only when both chart IDs can be recovered from the JSON record (or
    its legacy key) and both IDs have current chart UIDs. Unmapped relationships
    are intentionally omitted rather than guessed.
    """
    payload = _read_relationship_file(resolve_chart_similarity_relationships_path(path))
    relationships = payload.get("relationships", {})
    if not isinstance(relationships, Mapping):
        return {}

    normalized_map = {
        int(chart_id): uid
        for chart_id, raw_uid in chart_id_to_uid.items()
        if (uid := _coerce_chart_uid(raw_uid))
    }
    translations: dict[str, str] = {}
    for original_key, raw_state in relationships.items():
        if not isinstance(raw_state, Mapping):
            continue
        first_id, second_id = _chart_ids_from_relationship_state(raw_state, original_key)
        first_uid = normalized_map.get(first_id) if first_id is not None else None
        second_uid = normalized_map.get(second_id) if second_id is not None else None
        if first_id is None or second_id is None or not first_uid or not second_uid:
            continue
        legacy_key = chart_similarity_relationship_key(chart_1_id=first_id, chart_2_id=second_id)
        uid_key = chart_similarity_relationship_key(
            chart_1_id=first_id,
            chart_2_id=second_id,
            chart_1_uid=first_uid,
            chart_2_uid=second_uid,
        )
        translations[str(original_key)] = uid_key
        translations[legacy_key] = uid_key
    return translations


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
    missing_uid_labels = []
    if not first_uid:
        missing_uid_labels.append(f"{chart_1_name or 'chart 1'} (id={first_id})")
    if not second_uid:
        missing_uid_labels.append(f"{chart_2_name or 'chart 2'} (id={second_id})")
    if missing_uid_labels:
        raise ValueError(
            "Refusing to save chart similarity relationship without stable chart UIDs for: "
            + ", ".join(missing_uid_labels)
        )
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
    fail_on_invalid_json: bool = False,
) -> Path:
    """Rewrite existing relationship JSON records from integer keys to UID keys.

    Integer chart IDs are retained as metadata and lookup aliases, but the stored
    relationship key becomes UID-backed when both chart IDs can be resolved.
    """
    relationships_path = resolve_chart_similarity_relationships_path(path)
    payload = (
        _read_relationship_file_strict(relationships_path)
        if fail_on_invalid_json
        else _read_relationship_file(relationships_path)
    )
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
    migrated_count = 0
    unmapped_count = 0
    for original_key, raw_state in relationships.items():
        if not isinstance(raw_state, Mapping):
            migrated[str(original_key)] = raw_state
            continue
        state = dict(raw_state)
        first_id, second_id = _chart_ids_from_relationship_state(state, original_key)
        chart_uids = state.get("chart_uids") if isinstance(state.get("chart_uids"), list) else []
        first_uid = (
            _coerce_chart_uid(chart_uids[0]) if len(chart_uids) > 0 else None
        )
        second_uid = (
            _coerce_chart_uid(chart_uids[1]) if len(chart_uids) > 1 else None
        )
        first_uid = first_uid or (normalized_map.get(first_id) if first_id is not None else None)
        second_uid = second_uid or (normalized_map.get(second_id) if second_id is not None else None)

        if first_id is None or second_id is None or not first_uid or not second_uid:
            unmapped_count += 1
            migrated[str(original_key)] = state
            continue

        new_key = chart_similarity_relationship_key(
            chart_1_id=first_id,
            chart_2_id=second_id,
            chart_1_uid=first_uid,
            chart_2_uid=second_uid,
        )
        state["chart_ids"] = [first_id, second_id]
        state["chart_uids"] = [first_uid, second_uid]
        if str(original_key) != new_key:
            state.setdefault("legacy_relationship_key", str(original_key))
            state.setdefault("legacy_chart_ids", [first_id, second_id])
        state["relationship_key"] = new_key
        if new_key != original_key or state != raw_state:
            changed = True
            migrated_count += 1
        migrated[new_key] = state

    if changed:
        relationships_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = _backup_relationship_file_before_uid_migration(relationships_path)
        timestamp_text = _utc_timestamp()
        payload["schema_version"] = 2
        payload["relationships"] = migrated
        payload["uid_migration"] = {
            "migrated_at_utc": timestamp_text,
            "migrated_relationships": migrated_count,
            "unmapped_relationships": unmapped_count,
            "backup_path": str(backup_path) if backup_path is not None else "",
        }
        payload["updated_at_utc"] = timestamp_text
        temporary_path = relationships_path.with_suffix(relationships_path.suffix + ".tmp")
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary_path.replace(relationships_path)
    return relationships_path


def _chart_issue_label(chart_id: int | None, chart_id_to_name: Mapping[int, str]) -> str:
    if chart_id is None:
        return "Unknown chart ID"
    name = str(chart_id_to_name.get(int(chart_id), "") or "").strip()
    return f"{name} (id={int(chart_id)})" if name else f"Chart #{int(chart_id)}"


def _collect_conversion_issues(
    relationships: Mapping[str, Any],
    *,
    chart_id_to_uid: Mapping[int, str],
    chart_id_to_name: Mapping[int, str],
) -> list[ChartSimilarityRelationshipConversionIssue]:
    issues: list[ChartSimilarityRelationshipConversionIssue] = []
    normalized_uid_map = {
        int(chart_id): uid
        for chart_id, raw_uid in chart_id_to_uid.items()
        if (uid := _coerce_chart_uid(raw_uid))
    }
    for relationship_key, raw_state in relationships.items():
        if not isinstance(raw_state, Mapping):
            issues.append(
                ChartSimilarityRelationshipConversionIssue(
                    relationship_key=str(relationship_key),
                    chart_ids=[],
                    chart_names=[],
                    reason="Relationship entry is not a JSON object.",
                )
            )
            continue
        first_id, second_id = _chart_ids_from_relationship_state(raw_state, relationship_key)
        chart_uids = raw_state.get("chart_uids") if isinstance(raw_state.get("chart_uids"), list) else []
        first_uid = _coerce_chart_uid(chart_uids[0]) if len(chart_uids) > 0 else None
        second_uid = _coerce_chart_uid(chart_uids[1]) if len(chart_uids) > 1 else None
        if first_uid and second_uid:
            continue
        missing_reasons: list[str] = []
        if first_id is None or second_id is None:
            missing_reasons.append("could not recover both legacy chart IDs")
        else:
            if not normalized_uid_map.get(first_id):
                missing_reasons.append(f"missing UID for {_chart_issue_label(first_id, chart_id_to_name)}")
            if not normalized_uid_map.get(second_id):
                missing_reasons.append(f"missing UID for {_chart_issue_label(second_id, chart_id_to_name)}")
        if missing_reasons:
            chart_ids = [first_id, second_id]
            issues.append(
                ChartSimilarityRelationshipConversionIssue(
                    relationship_key=str(relationship_key),
                    chart_ids=chart_ids,
                    chart_names=[_chart_issue_label(chart_id, chart_id_to_name) for chart_id in chart_ids],
                    reason="; ".join(missing_reasons),
                )
            )
    return issues


def convert_logged_chart_similarity_relationship_ids_to_uids(
    *,
    path: str | os.PathLike[str] | None = None,
) -> ChartSimilarityRelationshipConversionReport:
    """Run the one-time relationship-log UID conversion and write a report beside the log."""
    relationships_path = resolve_chart_similarity_relationships_path(path)
    initial_payload = _read_relationship_file_strict(relationships_path)
    initial_relationships = initial_payload.get("relationships", {})
    if not isinstance(initial_relationships, Mapping):
        initial_relationships = {}

    chart_id_to_uid = get_chart_uid_map()
    chart_id_to_name = get_chart_display_name_map()
    issues = _collect_conversion_issues(
        initial_relationships,
        chart_id_to_uid=chart_id_to_uid,
        chart_id_to_name=chart_id_to_name,
    )
    migrate_chart_similarity_relationship_file_to_chart_uids(
        chart_id_to_uid=chart_id_to_uid,
        path=relationships_path,
        fail_on_invalid_json=True,
    )

    final_payload = _read_relationship_file_strict(relationships_path)
    final_relationships = final_payload.get("relationships", {})
    if not isinstance(final_relationships, Mapping):
        final_relationships = {}
    migration = final_payload.get("uid_migration", {}) if isinstance(final_payload, Mapping) else {}
    uid_backed_count = sum(1 for key in final_relationships if str(key).startswith("uid:"))
    legacy_key_count = sum(1 for key in final_relationships if not str(key).startswith("uid:"))
    report_path = relationships_path.with_name(f"{relationships_path.stem}.uid_conversion_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = ChartSimilarityRelationshipConversionReport(
        relationship_path=str(relationships_path),
        report_path=str(report_path),
        backup_path=str(migration.get("backup_path") or ""),
        uid_backed_relationships=uid_backed_count,
        legacy_key_relationships=legacy_key_count,
        issue_count=len(issues),
        issues=issues,
    )
    report_payload = asdict(report)
    report_payload["created_at_utc"] = _utc_timestamp()
    report_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def format_chart_similarity_relationship_conversion_report(
    report: ChartSimilarityRelationshipConversionReport,
    *,
    max_issues: int = 12,
) -> str:
    lines = [
        f"Updated relationship log:\n{report.relationship_path}",
        f"Conversion report:\n{report.report_path}",
        f"UID-backed relationships now in log: {report.uid_backed_relationships}",
        f"Legacy-key relationships still in log: {report.legacy_key_relationships}",
    ]
    if report.backup_path:
        lines.append(f"Backup before conversion:\n{report.backup_path}")
    if report.issues:
        lines.append("Unresolved relationships:")
        for issue in report.issues[:max_issues]:
            names = ", ".join(issue.chart_names) if issue.chart_names else "Unknown charts"
            lines.append(f"- {issue.relationship_key}: {names} — {issue.reason}")
        remaining = len(report.issues) - max_issues
        if remaining > 0:
            lines.append(f"- ...and {remaining} more. See the conversion report for the full list.")
    elif report.legacy_key_relationships == 0:
        lines.append("No legacy-key relationships remain in the log.")
    return "\n\n".join(lines)

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
            first_id, second_id = _chart_ids_from_relationship_state(state, key)
            chart_uids = state.get("chart_uids") if isinstance(state.get("chart_uids"), list) else []
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
