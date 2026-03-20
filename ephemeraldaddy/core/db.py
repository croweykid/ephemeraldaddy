# ephemeraldaddy/core/db.py

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple, Optional

from zoneinfo import ZoneInfo
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import RELATION_TYPE, SENTIMENT_OPTIONS


DB_DIR = Path.home() / ".ephemeraldaddy"
DB_PATH = DB_DIR / "charts.db"
CHART_TYPE_PUBLIC_DB = "public_db"
CHART_TYPE_PERSONAL = "personal"
CHART_TYPE_PARASOCIAL = "parasocial"
CHART_TYPE_EVENT = "event"
CHART_TYPE_SYNASTRY = "synastry"
CHART_TYPE_PERSONAL_TRANSIT = "personal_transit"
CHART_TYPE_NONHUMAN_ENTITY = "nonhuman_entity"
SOURCE_USER_SUBMITTED = "user_submitted"  # legacy alias

# Backwards-compatibility aliases for legacy `source` naming.
SOURCE_PUBLIC_DB = CHART_TYPE_PUBLIC_DB
SOURCE_PERSONAL = CHART_TYPE_PERSONAL
SOURCE_PARASOCIAL = CHART_TYPE_PARASOCIAL
SOURCE_EVENT = CHART_TYPE_EVENT
SOURCE_SYNASTRY = CHART_TYPE_SYNASTRY
SOURCE_PERSONAL_TRANSIT = CHART_TYPE_PERSONAL_TRANSIT
SOURCE_NONHUMAN_ENTITY = CHART_TYPE_NONHUMAN_ENTITY


def normalize_chart_type(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    if normalized == CHART_TYPE_PUBLIC_DB:
        return CHART_TYPE_PUBLIC_DB
    if normalized == CHART_TYPE_PARASOCIAL:
        return CHART_TYPE_PARASOCIAL
    if normalized == CHART_TYPE_EVENT:
        return CHART_TYPE_EVENT
    if normalized == CHART_TYPE_SYNASTRY:
        return CHART_TYPE_SYNASTRY
    if normalized == CHART_TYPE_PERSONAL_TRANSIT:
        return CHART_TYPE_PERSONAL_TRANSIT
    if normalized == CHART_TYPE_NONHUMAN_ENTITY:
        return CHART_TYPE_NONHUMAN_ENTITY
    if normalized in {CHART_TYPE_PERSONAL, SOURCE_USER_SUBMITTED}:
        return CHART_TYPE_PERSONAL
    return CHART_TYPE_PERSONAL


def _normalize_chart_type(value: Optional[str]) -> str:
    """Backward-compatible private alias for existing internal call sites."""
    return normalize_chart_type(value)


def _normalize_source(value: Optional[str]) -> str:
    """Legacy alias for call sites still using `source` naming."""
    return normalize_chart_type(value)


def _is_personal_chart_type_for_age_inference(value: Optional[str]) -> bool:
    """
    Return True only for explicit personal chart types used in age inference.

    Unknown/blank chart types are intentionally excluded so that non-personal
    records are never accidentally treated as personal.
    """
    normalized = (value or "").strip().lower().replace(" ", "_")
    return normalized in {CHART_TYPE_PERSONAL, SOURCE_USER_SUBMITTED}


SCHEMA_VERSION = 8

_SENTIMENT_CANONICAL_BY_KEY = {
    option.strip().lower(): option for option in SENTIMENT_OPTIONS
}

# Optional back-compat aliases used to normalize legacy renamed labels.
# Keys and values are normalized case-insensitively during processing.
DEFAULT_SENTIMENT_RENAMES: dict[str, str] = {
    "crush": "lil crush",
    "little crush": "lil crush",
}


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _charts_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'charts'
        """
    ).fetchone()
    return row is not None


def _create_charts_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS charts (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT NOT NULL,
            alias             TEXT,
            gender            TEXT,
            birth_place       TEXT,
            datetime_iso      TEXT NOT NULL,
            tz_name           TEXT,
            lat               REAL NOT NULL,
            lon               REAL NOT NULL,
            used_utc_fallback INTEGER NOT NULL DEFAULT 0,
            sentiments        TEXT,
            relationship_types TEXT,
            comments          TEXT,
            positive_sentiment_intensity INTEGER NOT NULL DEFAULT 1,
            negative_sentiment_intensity INTEGER NOT NULL DEFAULT 1,
            familiarity INTEGER NOT NULL DEFAULT 1,
            alignment_score INTEGER NOT NULL DEFAULT 0,
            familiarity_factors TEXT,
            age_when_first_met INTEGER NOT NULL DEFAULT 0,
            year_first_encountered INTEGER,
            social_score INTEGER NOT NULL DEFAULT 0,
            birthtime_unknown INTEGER NOT NULL DEFAULT 0,
            retcon_time_used  INTEGER NOT NULL DEFAULT 0,
            retcon_hour       INTEGER,
            retcon_minute     INTEGER,
            dominant_sign_weights TEXT,
            dominant_planet_weights TEXT,
            chart_type        TEXT NOT NULL DEFAULT 'personal',
            source            TEXT NOT NULL DEFAULT 'personal',
            is_placeholder    INTEGER NOT NULL DEFAULT 0,
            is_deceased       INTEGER NOT NULL DEFAULT 0,
            birth_month       INTEGER,
            birth_day         INTEGER,
            birth_year        INTEGER,
            created_at        TEXT NOT NULL,
            is_current        INTEGER NOT NULL DEFAULT 0
        )
        """
    )
def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_charts_created_at
        ON charts(created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_charts_is_current
        ON charts(is_current)
        """
    )


def _migrate_charts_columns(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "charts")
    added_year_first_encountered = False
    if "is_current" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN is_current INTEGER NOT NULL DEFAULT 0
            """
        )
    if "alias" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN alias TEXT
            """
        )
    if "gender" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN gender TEXT
            """
        )
    if "sentiments" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN sentiments TEXT
            """
        )
    if "birthtime_unknown" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN birthtime_unknown INTEGER NOT NULL DEFAULT 0
            """
        )
    if "relationship_types" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN relationship_types TEXT
            """
        )
    if "comments" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN comments TEXT
            """
        )
    if "positive_sentiment_intensity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN positive_sentiment_intensity INTEGER NOT NULL DEFAULT 1
            """
        )
    if "negative_sentiment_intensity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN negative_sentiment_intensity INTEGER NOT NULL DEFAULT 1
            """
        )
    if "familiarity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN familiarity INTEGER NOT NULL DEFAULT 1
            """
        )
    if "alignment_score" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN alignment_score INTEGER NOT NULL DEFAULT 0
            """
        )
    #indent?
    if "sentiment_confidence" in columns:
        conn.execute(
            """
            UPDATE charts
            SET familiarity = sentiment_confidence
            WHERE familiarity IS NULL OR familiarity = 1
            """
        )
    if "familiarity_factors" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN familiarity_factors TEXT
            """
        )

    if "social_score" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN social_score INTEGER NOT NULL DEFAULT 0
            """
        )

    if "age_when_first_met" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN age_when_first_met INTEGER NOT NULL DEFAULT 0
            """
        )
    if "year_first_encountered" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN year_first_encountered INTEGER
            """
        )
        added_year_first_encountered = True

    conn.execute(
        """
        UPDATE charts
        SET social_score =
            (COALESCE(positive_sentiment_intensity, 1) * COALESCE(familiarity, 1))
            -
            (COALESCE(negative_sentiment_intensity, 1) * COALESCE(familiarity, 1))
        """
    )
    if "retcon_time_used" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN retcon_time_used INTEGER NOT NULL DEFAULT 0
            """
        )
        conn.execute(
            """
            UPDATE charts
            SET retcon_time_used = 1
            WHERE birthtime_unknown = 1
              AND strftime('%H:%M', datetime_iso) != '12:00'
            """
        )
    if "retcon_hour" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN retcon_hour INTEGER
            """
        )
        conn.execute(
            """
            UPDATE charts
            SET retcon_hour = CAST(strftime('%H', datetime_iso) AS INTEGER)
            WHERE datetime_iso IS NOT NULL
            """
        )
    if "retcon_minute" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN retcon_minute INTEGER
            """
        )
        conn.execute(
            """
            UPDATE charts
            SET retcon_minute = CAST(strftime('%M', datetime_iso) AS INTEGER)
            WHERE datetime_iso IS NOT NULL
            """
        )

    if "dominant_sign_weights" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_sign_weights TEXT
            """
        )
    if "dominant_planet_weights" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_planet_weights TEXT
            """
        )

    if "chart_type" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN chart_type TEXT NOT NULL DEFAULT 'personal'
            """
        )

    if "source" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN source TEXT NOT NULL DEFAULT 'personal'
            """
        )
    if "is_placeholder" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN is_placeholder INTEGER NOT NULL DEFAULT 0
            """
        )
    if "is_deceased" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN is_deceased INTEGER NOT NULL DEFAULT 0
            """
        )
    if "birth_month" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN birth_month INTEGER
            """
        )
    if "birth_day" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN birth_day INTEGER
            """
        )
    if "birth_year" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN birth_year INTEGER
            """
        )


    conn.execute(
        """
        UPDATE charts
        SET chart_type = CASE
            WHEN chart_type IS NULL OR chart_type = '' THEN source
            ELSE chart_type
        END
        WHERE chart_type IS NULL
           OR chart_type = ''
        """
    )
    conn.execute(
        """
        UPDATE charts
        SET chart_type = 'personal'
        WHERE chart_type = 'user_submitted'
        """
    )

    conn.execute(
        """
        UPDATE charts
        SET chart_type = lower(replace(trim(chart_type), ' ', '_'))
        WHERE chart_type IS NOT NULL
          AND chart_type != ''
        """
    )

    conn.execute(
        """
        UPDATE charts
        SET chart_type = 'personal'
        WHERE chart_type IS NULL
           OR chart_type = ''
        """
    )

    conn.execute(
        """
        UPDATE charts
        SET source = chart_type
        WHERE source IS NULL
           OR source = ''
           OR source != chart_type
        """
    )

    if added_year_first_encountered:
        _sync_year_first_encountered_from_age(conn)


def _backfill_non_placeholder_birth_date_parts(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, datetime_iso, birth_year, birth_month, birth_day
        FROM charts
        WHERE datetime_iso IS NOT NULL
          AND datetime_iso != ''
          AND (birth_year IS NULL OR birth_month IS NULL OR birth_day IS NULL)
          AND COALESCE(is_placeholder, 0) = 0
        """
    ).fetchall()
    if not rows:
        return

    for chart_id, datetime_iso, birth_year, birth_month, birth_day in rows:
        try:
            parsed = datetime.fromisoformat(str(datetime_iso))
        except Exception:
            continue

        resolved_year = int(birth_year) if birth_year is not None else int(parsed.year)
        resolved_month = int(birth_month) if birth_month is not None else int(parsed.month)
        resolved_day = int(birth_day) if birth_day is not None else int(parsed.day)

        conn.execute(
            """
            UPDATE charts
            SET birth_year = ?,
                birth_month = ?,
                birth_day = ?
            WHERE id = ?
            """,
            (resolved_year, resolved_month, resolved_day, int(chart_id)),
        )

def _sync_year_first_encountered_from_age(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, age_when_first_met
        FROM charts
        WHERE year_first_encountered IS NULL
          AND age_when_first_met IS NOT NULL
          AND age_when_first_met != 0
        """
    ).fetchall()
    if not rows:
        return

    self_row = conn.execute(
        """
        SELECT birth_year, birth_month, datetime_iso
        FROM charts
        WHERE relationship_types LIKE '%self%'
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()
    if self_row is None:
        return

    self_birth_year, self_birth_month, self_datetime_iso = self_row
    if self_birth_year is None:
        try:
            self_birth_year = datetime.fromisoformat(str(self_datetime_iso)).year
        except Exception:
            return
    if self_birth_month is None:
        try:
            self_birth_month = datetime.fromisoformat(str(self_datetime_iso)).month
        except Exception:
            self_birth_month = 1

    now = datetime.utcnow()
    current_age = now.year - int(self_birth_year)
    if now.month < int(self_birth_month):
        current_age -= 1

    for chart_id, age_when_first_met in rows:
        try:
            age_met = int(age_when_first_met)
        except (TypeError, ValueError):
            continue
        known_duration = max(0, current_age - age_met)
        year_first_encountered = now.year - known_duration
        conn.execute(
            "UPDATE charts SET year_first_encountered = ? WHERE id = ?",
            (year_first_encountered, int(chart_id)),
        )

def _ensure_schema(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA user_version").fetchone()
    user_version = int(row[0]) if row is not None else 0

    # Keep schema self-healing for legacy databases that may report a newer
    # user_version but still be missing columns from partial/failed migrations.
    if _charts_table_exists(conn):
        _migrate_charts_columns(conn)
        _backfill_non_placeholder_birth_date_parts(conn)

    if user_version == 0:
        if not _charts_table_exists(conn):
            _create_charts_table(conn)
        else:
            _migrate_charts_columns(conn)
        _backfill_non_placeholder_birth_date_parts(conn)
        _create_indexes(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        return

    if user_version < 1:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 1")
        user_version = 1

    if user_version < 2:
        _create_indexes(conn)
        conn.execute("PRAGMA user_version = 2")
        user_version = 2

    if user_version < 3:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 3")
        user_version = 3

    if user_version < 4:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 4")
        user_version = 4

    if user_version < 5:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 5")
        user_version = 5

    if user_version < 6:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 6")
        user_version = 6

    if user_version < 7:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 7")
        user_version = 7

    if user_version < 8:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 8")

def _get_conn() -> sqlite3.Connection:
    """Open a SQLite connection and ensure the schema exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    _ensure_schema(conn)
    return conn


def _serialize_sentiments(sentiments: Optional[list[str]]) -> Optional[str]:
    if not sentiments:
        return None
    return ", ".join(cat.strip() for cat in sentiments if cat.strip())


def normalize_sentiment_labels(
    sentiments: Optional[list[str]],
    renamed_labels: Optional[dict[str, str]] = None,
    keep_unknown: bool = True,
) -> list[str]:
    """Normalize sentiment labels, dedupe, and preserve first-seen order."""
    if not sentiments:
        return []

    aliases = {
        key.strip().lower(): value.strip().lower()
        for key, value in DEFAULT_SENTIMENT_RENAMES.items()
    }
    if renamed_labels:
        aliases.update(
            {
                key.strip().lower(): value.strip().lower()
                for key, value in renamed_labels.items()
                if key and value
            }
        )

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_label in sentiments:
        label = (raw_label or "").strip()
        if not label:
            continue

        key = label.lower()
        key = aliases.get(key, key)
        canonical = _SENTIMENT_CANONICAL_BY_KEY.get(key)
        final_label = canonical or (label if keep_unknown else "")
        if not final_label or final_label in seen:
            continue

        normalized.append(final_label)
        seen.add(final_label)

    return normalized


def _serialize_relationship_types(
    relationship_types: Optional[list[str]],
) -> Optional[str]:
    if not relationship_types:
        return None
    return ", ".join(value.strip() for value in relationship_types if value.strip())

def _serialize_familiarity_factors(
    familiarity_factors: Optional[list[str]],
) -> Optional[str]:
    if not familiarity_factors:
        return None
    return ", ".join(value.strip() for value in familiarity_factors if value.strip())

def _serialize_weight_map(weights: Optional[dict[str, float]]) -> Optional[str]:
    if weights is None:
        return None
    return json.dumps(weights, sort_keys=True)

def _parse_weight_map(value: Optional[str]) -> dict[str, float]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw_value in data.items():
        if not isinstance(raw_value, (int, float)):
            continue
        normalized_key = str(key)
        if normalized_key == "DESC":
            normalized_key = "DS"
        parsed[normalized_key] = parsed.get(normalized_key, 0.0) + float(raw_value)
    return parsed

def _normalize_year_first_encountered(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= parsed <= 9999:
        return parsed
    return None

def _normalize_sentiment_metric(value: Optional[int]) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    if 1 <= parsed <= 10:
        return parsed
    return 1


def _normalize_alignment_score(value: Optional[int]) -> int:
    if value is None:
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(-10, min(10, parsed))


def calculate_social_score(
    positive_sentiment_intensity: Optional[int],
    negative_sentiment_intensity: Optional[int],
    familiarity: Optional[int],
) -> int:
    positive = _normalize_sentiment_metric(positive_sentiment_intensity)
    negative = _normalize_sentiment_metric(negative_sentiment_intensity)
    familiarity_score = _normalize_sentiment_metric(familiarity)
    return (positive * familiarity_score) - (negative * familiarity_score)


def parse_sentiments(value: Optional[str]) -> list[str]:
    if not value:
        return []
    parsed = [cat.strip() for cat in value.split(",") if cat.strip()]
    return normalize_sentiment_labels(parsed)


def cleanup_sentiments_in_database(
    renamed_labels: Optional[dict[str, str]] = None,
    max_sentiments: Optional[int] = None,
    keep_unknown: bool = True,
    create_backup: bool = True,
) -> dict[str, int]:
    """Normalize and deduplicate stored chart sentiments in-place."""
    if create_backup:
        backup_database()

    updated_rows = 0
    scanned_rows = 0
    with _get_conn() as conn:
        rows = conn.execute("SELECT id, sentiments FROM charts").fetchall()
        for row_id, raw_value in rows:
            scanned_rows += 1
            parsed = [cat.strip() for cat in (raw_value or "").split(",") if cat.strip()]
            normalized = normalize_sentiment_labels(
                parsed,
                renamed_labels=renamed_labels,
                keep_unknown=keep_unknown,
            )
            if max_sentiments is not None and max_sentiments >= 0:
                normalized = normalized[:max_sentiments]

            serialized = _serialize_sentiments(normalized)
            if serialized != raw_value:
                conn.execute(
                    "UPDATE charts SET sentiments = ? WHERE id = ?",
                    (serialized, row_id),
                )
                updated_rows += 1

    return {"rows_scanned": scanned_rows, "rows_updated": updated_rows}

def parse_relationship_types(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [value.strip() for value in value.split(",") if value.strip()]


def get_metadata_label_usage() -> dict[str, list[dict[str, int | str]]]:
    """Return sentiment + relationship labels with usage counts.

    Includes both current canonical options and any legacy labels currently stored
    in the database.
    """
    sentiment_counts: dict[str, int] = {label: 0 for label in SENTIMENT_OPTIONS}
    relationship_counts: dict[str, int] = {label: 0 for label in RELATION_TYPE}

    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT sentiments, relationship_types FROM charts"
        ).fetchall()

    for raw_sentiments, raw_relationship_types in rows:
        for sentiment in parse_sentiments(raw_sentiments):
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        for relationship in parse_relationship_types(raw_relationship_types):
            relationship_counts[relationship] = relationship_counts.get(relationship, 0) + 1

    def _format_rows(counts: dict[str, int]) -> list[dict[str, int | str]]:
        return [
            {"label": label, "count": counts[label]}
            for label in sorted(counts, key=lambda value: (value.lower(), value))
        ]

    return {
        "sentiments": _format_rows(sentiment_counts),
        "relationship_types": _format_rows(relationship_counts),
    }


def apply_metadata_label_change(
    *,
    field: str,
    old_label: str,
    new_label: Optional[str],
    create_backup: bool = True,
) -> dict[str, int]:
    """Rename or delete a sentiment/relationship label across all charts."""
    normalized_old = (old_label or "").strip()
    normalized_new = (new_label or "").strip() if new_label is not None else ""
    if not normalized_old:
        return {"rows_scanned": 0, "rows_updated": 0, "occurrences_updated": 0}

    if field == "sentiments":
        parser = parse_sentiments
        serializer = _serialize_sentiments
        column = "sentiments"
    elif field == "relationship_types":
        parser = parse_relationship_types
        serializer = _serialize_relationship_types
        column = "relationship_types"
    else:
        raise ValueError(f"Unsupported metadata field: {field}")

    if create_backup:
        backup_database()

    rows_scanned = 0
    rows_updated = 0
    occurrences_updated = 0
    with _get_conn() as conn:
        rows = conn.execute(f"SELECT id, {column} FROM charts").fetchall()
        for row_id, raw_value in rows:
            rows_scanned += 1
            parsed = parser(raw_value)
            if not parsed:
                continue

            rebuilt: list[str] = []
            seen: set[str] = set()
            row_changed = False
            for value in parsed:
                replacement = value
                if value == normalized_old:
                    occurrences_updated += 1
                    row_changed = True
                    replacement = normalized_new

                if not replacement or replacement in seen:
                    continue
                rebuilt.append(replacement)
                seen.add(replacement)

            if not row_changed:
                continue

            conn.execute(
                f"UPDATE charts SET {column} = ? WHERE id = ?",
                (serializer(rebuilt), row_id),
            )
            rows_updated += 1

    return {
        "rows_scanned": rows_scanned,
        "rows_updated": rows_updated,
        "occurrences_updated": occurrences_updated,
    }


def _contains_self_relationship(value: Optional[str]) -> bool:
    return any(rel.lower() == "self" for rel in parse_relationship_types(value))


def find_self_tagged_chart(
    exclude_chart_id: Optional[int] = None,
) -> Optional[tuple[int, str]]:
    """Return the first chart tagged with relationship type 'self'."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, name, relationship_types FROM charts ORDER BY id ASC"
    ).fetchall()
    conn.close()

    for chart_id, name, relationship_types in rows:
        if exclude_chart_id is not None and int(chart_id) == int(exclude_chart_id):
            continue
        if _contains_self_relationship(relationship_types):
            return int(chart_id), str(name or f"Chart #{chart_id}")
    return None


def clear_self_tag_from_other_charts(keep_chart_id: int) -> list[int]:
    """Remove the 'self' relationship type from every chart except keep_chart_id."""
    conn = _get_conn()
    changed_ids: list[int] = []
    with conn:
        rows = conn.execute(
            "SELECT id, relationship_types FROM charts WHERE id != ?",
            (int(keep_chart_id),),
        ).fetchall()
        for chart_id, relationship_types in rows:
            parsed = parse_relationship_types(relationship_types)
            filtered = [value for value in parsed if value.lower() != "self"]
            if filtered == parsed:
                continue
            conn.execute(
                "UPDATE charts SET relationship_types = ? WHERE id = ?",
                (_serialize_relationship_types(filtered), int(chart_id)),
            )
            changed_ids.append(int(chart_id))
    conn.close()
    return changed_ids



def resolve_user_age_details(
    reference_dt: Optional[datetime] = None,
    *,
    force_inference: bool = False,
    include_all_chart_types_for_inference: bool = False,
) -> dict[str, Optional[object]]:
    """
    Resolve likely user age from database charts.

    Keys:
      - age: int | None
      - source: 'self' | 'predicted' | 'unavailable'
      - chart_name: str | None
    """
    now = reference_dt or datetime.utcnow()
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT
            name,
            relationship_types,
            birth_year,
            birth_month,
            datetime_iso,
            COALESCE(NULLIF(chart_type, ''), source, '') AS inference_chart_type
        FROM charts
        """
    ).fetchall()
    conn.close()

    alter_ages: list[int] = []
    for name, relationship_types, birth_year, birth_month, datetime_iso, inference_chart_type in rows:
        year = birth_year
        month = birth_month
        if year is None:
            try:
                parsed_dt = datetime.fromisoformat(str(datetime_iso))
                year = parsed_dt.year
                if month is None:
                    month = parsed_dt.month
            except Exception:
                continue
        if month is None:
            month = 1

        age = now.year - int(year)
        if now.month < int(month):
            age -= 1
        include_for_inference = include_all_chart_types_for_inference or (
            _is_personal_chart_type_for_age_inference(inference_chart_type)
        )

        if include_for_inference and 0 <= age <= 120:
            alter_ages.append(age)

        if _contains_self_relationship(relationship_types) and not force_inference:
            return {
                "age": max(0, int(age)),
                "source": "self",
                "chart_name": str(name or "Unnamed chart"),
            }

    if not alter_ages:
        return {"age": None, "source": "unavailable", "chart_name": None}

    from ephemeraldaddy.data.age_distribution_estimator import infer_user_age_from_alter_ages

    inferred = infer_user_age_from_alter_ages(alter_ages)
    if inferred is None:
        return {"age": None, "source": "unavailable", "chart_name": None}
    return {
        "age": int(round(inferred)),
        "source": "predicted",
        "chart_name": None,
    }

def resolve_user_age(
    reference_dt: Optional[datetime] = None,
    *,
    force_inference: bool = False,
    include_all_chart_types_for_inference: bool = False,
) -> Optional[int]:
    """Resolve likely user age from database charts."""
    details = resolve_user_age_details(
        reference_dt=reference_dt,
        force_inference=force_inference,
        include_all_chart_types_for_inference=include_all_chart_types_for_inference,
    )
    age = details.get("age")
    return int(age) if isinstance(age, int) else None

def parse_familiarity_factors(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [value.strip() for value in value.split(",") if value.strip()]

def get_db_path() -> Path:
    """Return the path to the database file."""
    return DB_PATH


def backup_database(destination: Optional[Path] = None) -> Path:
    """
    Copy the database to a backup file.

    If destination is None, create a timestamped backup in DB_DIR.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError("Database file does not exist yet.")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if destination is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        destination = DB_DIR / f"ephemeraldaddy_dbbackup_{timestamp}.db"
    else:
        destination = Path(destination)
    shutil.copy2(DB_PATH, destination)
    return destination


def restore_database(source: Path) -> None:
    """Restore the database from a backup file."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, DB_PATH)


def check_database_health() -> tuple[bool, str]:
    """
    Validate the database file with PRAGMA integrity_check.

    Returns (ok, message). If ok is False, message explains the error.
    """
    if not DB_PATH.exists():
        return True, ""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("PRAGMA integrity_check")
        result = cur.fetchone()
        conn.close()
    except sqlite3.DatabaseError as exc:
        return False, str(exc)
    if result is None:
        return False, "Integrity check returned no result."
    status = str(result[0])
    if status.lower() != "ok":
        return False, status
    return True, ""

def save_chart(
    chart,
    birth_place: Optional[str] = None,
    sentiments: Optional[list[str]] = None,
    relationship_types: Optional[list[str]] = None,
    birthtime_unknown: Optional[bool] = None,
    retcon_time_used: Optional[bool] = None,
    dominant_sign_weights: Optional[dict[str, float]] = None,
    dominant_planet_weights: Optional[dict[str, float]] = None,
    chart_type: Optional[str] = None,
    source: Optional[str] = None,
    is_placeholder: Optional[bool] = None,
    is_deceased: Optional[bool] = None,
    birth_month: Optional[int] = None,
    birth_day: Optional[int] = None,
    birth_year: Optional[int] = None,
    retcon_hour: Optional[int] = None,
    retcon_minute: Optional[int] = None,
) -> int:
    """
    Persist a chart to the local DB.

    Returns the new chart id.
    """
    resolved_chart_type = _normalize_chart_type(
        chart_type
        or source
        or getattr(chart, "chart_type", None)
        or getattr(chart, "source", None)
    )
    conn = _get_conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO charts
                (name, alias, gender, birth_place, datetime_iso, tz_name,
                 lat, lon, used_utc_fallback, sentiments, relationship_types,
                 comments,
                 positive_sentiment_intensity, negative_sentiment_intensity,
                 familiarity, alignment_score, familiarity_factors, age_when_first_met, year_first_encountered, social_score,
                 birthtime_unknown,
                 retcon_time_used, retcon_hour, retcon_minute, dominant_sign_weights, dominant_planet_weights,
                 chart_type,
                 source,
                 is_placeholder,
                 is_deceased,
                 birth_month,
                 birth_day,
                 birth_year,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chart.name,
                getattr(chart, "alias", None),
                getattr(chart, "gender", None),
                birth_place,
                chart.dt.isoformat(),
                str(chart.dt.tzinfo) if chart.dt.tzinfo else None,
                chart.lat,
                chart.lon,
                1 if getattr(chart, "used_utc_fallback", False) else 0,
                _serialize_sentiments(
                    sentiments
                    if sentiments is not None
                    else getattr(chart, "sentiments", [])
                ),
                _serialize_relationship_types(
                    relationship_types
                    if relationship_types is not None
                    else getattr(chart, "relationship_types", [])
                ),
                getattr(chart, "comments", None),
                _normalize_sentiment_metric(
                    getattr(chart, "positive_sentiment_intensity", None)
                ),
                _normalize_sentiment_metric(
                    getattr(chart, "negative_sentiment_intensity", None)
                ),
                _normalize_sentiment_metric(
                    getattr(chart, "familiarity", None)
                ),
                _normalize_alignment_score(
                    getattr(chart, "alignment_score", None)
                ),
                _serialize_familiarity_factors(
                    getattr(chart, "familiarity_factors", [])
                ),
                max(0, int(getattr(chart, "age_when_first_met", 0) or 0)),
                _normalize_year_first_encountered(getattr(chart, "year_first_encountered", None)),
                calculate_social_score(
                    getattr(chart, "positive_sentiment_intensity", None),
                    getattr(chart, "negative_sentiment_intensity", None),
                    getattr(chart, "familiarity", None),
                ),
                int(
                    birthtime_unknown
                    if birthtime_unknown is not None
                    else bool(getattr(chart, "birthtime_unknown", False))
                ),
                int(
                    retcon_time_used
                    if retcon_time_used is not None
                    else bool(getattr(chart, "retcon_time_used", False))
                ),
                int(retcon_hour) if retcon_hour is not None else getattr(chart, "retcon_hour", None),
                int(retcon_minute) if retcon_minute is not None else getattr(chart, "retcon_minute", None),
                _serialize_weight_map(
                    dominant_sign_weights
                    if dominant_sign_weights is not None
                    else getattr(chart, "dominant_sign_weights", None)
                ),
                _serialize_weight_map(
                    dominant_planet_weights
                    if dominant_planet_weights is not None
                    else getattr(chart, "dominant_planet_weights", None)
                ),
                resolved_chart_type,
                resolved_chart_type,
                int(
                    is_placeholder
                    if is_placeholder is not None
                    else bool(getattr(chart, "is_placeholder", False))
                ),
                int(
                    is_deceased
                    if is_deceased is not None
                    else bool(getattr(chart, "is_deceased", False))
                ),
                birth_month,
                birth_day,
                birth_year,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        chart_id = cur.lastrowid
    conn.close()
    return chart_id


def update_chart(
    chart_id: int,
    chart,
    birth_place: Optional[str] = None,
    sentiments: Optional[list[str]] = None,
    relationship_types: Optional[list[str]] = None,
    birthtime_unknown: Optional[bool] = None,
    retcon_time_used: Optional[bool] = None,
    dominant_sign_weights: Optional[dict[str, float]] = None,
    dominant_planet_weights: Optional[dict[str, float]] = None,
    chart_type: Optional[str] = None,
    source: Optional[str] = None,
    is_placeholder: Optional[bool] = None,
    is_deceased: Optional[bool] = None,
    birth_month: Optional[int] = None,
    birth_day: Optional[int] = None,
    birth_year: Optional[int] = None,
    retcon_hour: Optional[int] = None,
    retcon_minute: Optional[int] = None,
) -> None:
    """Update a saved chart by id."""
    resolved_birth_place = (
        birth_place
        if birth_place is not None
        else getattr(chart, "birth_place", None)
    )
    resolved_chart_type = _normalize_chart_type(
        chart_type
        or source
        or getattr(chart, "chart_type", None)
        or getattr(chart, "source", None)
    )
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            UPDATE charts
            SET name = ?,
                alias = ?,
                gender = ?,
                birth_place = ?,
                datetime_iso = ?,
                tz_name = ?,
                lat = ?,
                lon = ?,
                used_utc_fallback = ?,
                sentiments = ?,
                relationship_types = ?,
                comments = ?,
                positive_sentiment_intensity = ?,
                negative_sentiment_intensity = ?,
                familiarity = ?,
                alignment_score = ?,
                familiarity_factors = ?,
                age_when_first_met = ?,
                year_first_encountered = ?,
                social_score = ?,
                birthtime_unknown = ?,
                retcon_time_used = ?,
                retcon_hour = ?,
                retcon_minute = ?,
                dominant_sign_weights = ?,
                dominant_planet_weights = ?,
                chart_type = ?,
                source = ?,
                is_placeholder = ?,
                is_deceased = ?,
                birth_month = ?,
                birth_day = ?,
                birth_year = ?
            WHERE id = ?
            """,
            (
                chart.name,
                getattr(chart, "alias", None),
                getattr(chart, "gender", None),
                resolved_birth_place,
                chart.dt.isoformat(),
                str(chart.dt.tzinfo) if chart.dt.tzinfo else None,
                chart.lat,
                chart.lon,
                1 if getattr(chart, "used_utc_fallback", False) else 0,
                _serialize_sentiments(
                    sentiments
                    if sentiments is not None
                    else getattr(chart, "sentiments", [])
                ),
                _serialize_relationship_types(
                    relationship_types
                    if relationship_types is not None
                    else getattr(chart, "relationship_types", [])
                ),
                getattr(chart, "comments", None),
                _normalize_sentiment_metric(
                    getattr(chart, "positive_sentiment_intensity", None)
                ),
                _normalize_sentiment_metric(
                    getattr(chart, "negative_sentiment_intensity", None)
                ),
                _normalize_sentiment_metric(
                    getattr(chart, "familiarity", None)
                ),
                _normalize_alignment_score(
                    getattr(chart, "alignment_score", None)
                ),
                _serialize_familiarity_factors(
                    getattr(chart, "familiarity_factors", [])
                ),
                max(0, int(getattr(chart, "age_when_first_met", 0) or 0)),
                _normalize_year_first_encountered(getattr(chart, "year_first_encountered", None)),
                calculate_social_score(
                    getattr(chart, "positive_sentiment_intensity", None),
                    getattr(chart, "negative_sentiment_intensity", None),
                    getattr(chart, "familiarity", None),
                ),
                int(
                    birthtime_unknown
                    if birthtime_unknown is not None
                    else bool(getattr(chart, "birthtime_unknown", False))
                ),
                int(
                    retcon_time_used
                    if retcon_time_used is not None
                    else bool(getattr(chart, "retcon_time_used", False))
                ),
                int(retcon_hour) if retcon_hour is not None else getattr(chart, "retcon_hour", None),
                int(retcon_minute) if retcon_minute is not None else getattr(chart, "retcon_minute", None),
                _serialize_weight_map(
                    dominant_sign_weights
                    if dominant_sign_weights is not None
                    else getattr(chart, "dominant_sign_weights", None)
                ),
                _serialize_weight_map(
                    dominant_planet_weights
                    if dominant_planet_weights is not None
                    else getattr(chart, "dominant_planet_weights", None)
                ),
                resolved_chart_type,
                resolved_chart_type,
                int(
                    is_placeholder
                    if is_placeholder is not None
                    else bool(getattr(chart, "is_placeholder", False))
                ),
                int(
                    is_deceased
                    if is_deceased is not None
                    else bool(getattr(chart, "is_deceased", False))
                ),
                birth_month,
                birth_day,
                birth_year,
                chart_id,
            ),
        )
    conn.close()


def list_charts() -> List[
    Tuple[
        int,
        str,
        Optional[str],
        Optional[str],
        str,
        Optional[str],
        str,
        int,
        int,
        int,
        int,
        int,
        Optional[int],
        int,
        str,
        int,
        int,
        Optional[int],
        Optional[int],
        Optional[int],
    ]
]:
    """
    Return a list of saved charts:
    (id, name, alias, gender, datetime_iso, birth_place, created_at,
    used_utc_fallback, birthtime_unknown, retcon_time_used,
    familiarity, age_when_first_met, year_first_encountered,
    social_score, chart_type, is_placeholder, is_deceased,
    birth_month, birth_day, birth_year)
    """
    conn = _get_conn()
    cur = conn.execute(
        """
        SELECT id,
               name,
               alias,
               gender,
               datetime_iso,
               birth_place,
               created_at,
               used_utc_fallback,
               birthtime_unknown,
               retcon_time_used,
               familiarity,
               age_when_first_met,
               year_first_encountered,
               social_score,
               positive_sentiment_intensity,
               negative_sentiment_intensity,
               COALESCE(chart_type, source),
               is_placeholder,
               is_deceased,
               birth_month,
               birth_day,
               birth_year
        FROM charts
        ORDER BY created_at DESC
        """
    )
    raw_rows = cur.fetchall()
    conn.close()

    rows: List[
        Tuple[
            int,
            str,
            Optional[str],
            Optional[str],
            str,
            Optional[str],
            str,
            int,
            int,
            int,
            int,
            int,
            Optional[int],
            int,
            str,
            int,
            int,
            Optional[int],
            Optional[int],
            Optional[int],
        ]
    ] = []
    for (
        chart_id,
        name,
        alias,
        gender,
        datetime_iso,
        birth_place,
        created_at,
        used_utc_fallback,
        birthtime_unknown,
        retcon_time_used,
        familiarity,
        age_when_first_met,
        year_first_encountered,
        social_score,
        positive_sentiment_intensity,
        negative_sentiment_intensity,
        chart_type,
        is_placeholder,
        is_deceased,
        birth_month,
        birth_day,
        birth_year,
    ) in raw_rows:
        normalized_familiarity = _normalize_sentiment_metric(familiarity)
        resolved_social_score = (
            int(social_score)
            if social_score is not None
            else calculate_social_score(
                positive_sentiment_intensity,
                negative_sentiment_intensity,
                normalized_familiarity,
            )
        )
        rows.append(
            (
                int(chart_id),
                str(name or ""),
                alias,
                gender,
                str(datetime_iso or ""),
                birth_place,
                str(created_at or ""),
                int(used_utc_fallback or 0),
                int(birthtime_unknown or 0),
                int(retcon_time_used or 0),
                normalized_familiarity,
                max(0, int(age_when_first_met or 0)),
                _normalize_year_first_encountered(year_first_encountered),
                resolved_social_score,
                _normalize_chart_type(chart_type),
                int(is_placeholder or 0),
                int(is_deceased or 0),
                int(birth_month) if birth_month is not None else None,
                int(birth_day) if birth_day is not None else None,
                int(birth_year) if birth_year is not None else None,
            )
        )
    return rows


def set_current_chart(chart_id: Optional[int]) -> None:
    """Mark exactly one chart as current (or clear if None)."""
    conn = _get_conn()
    with conn:
        conn.execute("UPDATE charts SET is_current = 0")
        if chart_id is not None:
            conn.execute(
                "UPDATE charts SET is_current = 1 WHERE id = ?",
                (chart_id,),
            )
    conn.close()


def get_current_chart_id() -> Optional[int]:
    """Return the current chart id, if any."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id FROM charts WHERE is_current = 1 LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return int(row[0])


def delete_charts(chart_ids: List[int]) -> int:
    """
    Delete charts by id.

    Returns the number of rows deleted.
    """
    if not chart_ids:
        return 0

    placeholders = ", ".join("?" for _ in chart_ids)
    conn = _get_conn()
    with conn:
        cur = conn.execute(
            f"DELETE FROM charts WHERE id IN ({placeholders})",
            chart_ids,
        )
    conn.close()
    return cur.rowcount

def load_chart(chart_id: int):
    """
    Load a chart from the DB and reconstruct a Chart instance.

    Raises ValueError if no such chart exists.
    """
    conn = _get_conn()
    columns = _table_columns(conn, "charts")
    familiarity_factors_projection = (
        "familiarity_factors"
        if "familiarity_factors" in columns
        else "NULL AS familiarity_factors"
    )
    cur = conn.execute(
        f"""
        SELECT name, alias, gender, birth_place, datetime_iso, tz_name, lat, lon,
               used_utc_fallback, sentiments, relationship_types,
               comments,
               positive_sentiment_intensity, negative_sentiment_intensity,
               familiarity, alignment_score, {familiarity_factors_projection}, age_when_first_met, year_first_encountered, birthtime_unknown,
               retcon_time_used, retcon_hour, retcon_minute,
               dominant_sign_weights, dominant_planet_weights, COALESCE(chart_type, source),
               is_placeholder, is_deceased, birth_month, birth_day, birth_year
        FROM charts
        WHERE id = ?
        """,
        (chart_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"No chart with id {chart_id}")

    (
        name,
        alias,
        gender,
        birth_place,
        datetime_iso,
        tz_name,
        lat,
        lon,
        used_utc_fallback,
        sentiments,
        relationship_types,
        comments,
        positive_sentiment_intensity,
        negative_sentiment_intensity,
        familiarity,
        alignment_score,
        familiarity_factors,
        age_when_first_met,
        year_first_encountered,
        birthtime_unknown,
        retcon_time_used,
        retcon_hour,
        retcon_minute,
        dominant_sign_weights,
        dominant_planet_weights,
        chart_type,
        is_placeholder,
        is_deceased,
        birth_month,
        birth_day,
        birth_year,
    ) = row

    from ephemeraldaddy.core.chart import Chart  # avoid circular import

    if bool(is_placeholder):
        placeholder = SimpleNamespace()
        placeholder.name = name
        placeholder.alias = alias
        placeholder.gender = gender
        placeholder.birth_place = birth_place
        placeholder.dt = datetime.fromisoformat(datetime_iso)
        placeholder.lat = lat
        placeholder.lon = lon
        placeholder.used_utc_fallback = bool(used_utc_fallback)
        placeholder.sentiments = parse_sentiments(sentiments)
        placeholder.relationship_types = parse_relationship_types(relationship_types)
        placeholder.comments = comments or ""
        placeholder.positive_sentiment_intensity = _normalize_sentiment_metric(
            positive_sentiment_intensity
        )
        placeholder.negative_sentiment_intensity = _normalize_sentiment_metric(
            negative_sentiment_intensity
        )
        normalized_familiarity = _normalize_sentiment_metric(familiarity)
        placeholder.familiarity = normalized_familiarity
        placeholder.alignment_score = _normalize_alignment_score(alignment_score)
        placeholder.sentiment_confidence = normalized_familiarity
        placeholder.familiarity_factors = parse_familiarity_factors(
            familiarity_factors
        )
        placeholder.age_when_first_met = max(0, int(age_when_first_met or 0))
        placeholder.year_first_encountered = _normalize_year_first_encountered(year_first_encountered)
        placeholder.birthtime_unknown = bool(birthtime_unknown)
        placeholder.retcon_time_used = bool(retcon_time_used)
        placeholder.retcon_hour = int(retcon_hour) if retcon_hour is not None else None
        placeholder.retcon_minute = int(retcon_minute) if retcon_minute is not None else None
        placeholder.dominant_sign_weights = _parse_weight_map(dominant_sign_weights)
        placeholder.dominant_planet_weights = _parse_weight_map(dominant_planet_weights)
        normalized_chart_type = _normalize_chart_type(chart_type)
        placeholder.chart_type = normalized_chart_type
        placeholder.source = normalized_chart_type
        placeholder.is_placeholder = True
        placeholder.is_deceased = bool(is_deceased)
        placeholder.birth_month = birth_month
        placeholder.birth_day = birth_day
        placeholder.birth_year = birth_year
        placeholder.positions = {}
        placeholder.retrogrades = {}
        placeholder.houses = []
        placeholder.aspects = []
        placeholder.modal_distribution = {}
        return placeholder

    dt = datetime.fromisoformat(datetime_iso)
    # If tz info is missing but we have a tz_name, attach it:
    if tz_name and dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))

    chart = Chart(name, dt, lat, lon, tz=None, alias=alias)
    chart.gender = gender
    chart.birth_place = birth_place
    chart.used_utc_fallback = bool(used_utc_fallback)
    chart.sentiments = parse_sentiments(sentiments)
    chart.relationship_types = parse_relationship_types(relationship_types)
    chart.comments = comments or ""
    chart.positive_sentiment_intensity = _normalize_sentiment_metric(
        positive_sentiment_intensity
    )
    chart.negative_sentiment_intensity = _normalize_sentiment_metric(
        negative_sentiment_intensity
    )
    chart.familiarity = _normalize_sentiment_metric(familiarity)
    chart.alignment_score = _normalize_alignment_score(alignment_score)
    chart.familiarity_factors = parse_familiarity_factors(
        familiarity_factors
    )
    chart.age_when_first_met = max(0, int(age_when_first_met or 0))
    chart.year_first_encountered = _normalize_year_first_encountered(year_first_encountered)
    chart.birthtime_unknown = bool(birthtime_unknown)
    chart.retcon_time_used = bool(retcon_time_used)
    chart.retcon_hour = int(retcon_hour) if retcon_hour is not None else None
    chart.retcon_minute = int(retcon_minute) if retcon_minute is not None else None
    chart.dominant_sign_weights = _parse_weight_map(dominant_sign_weights)
    chart.dominant_planet_weights = _parse_weight_map(dominant_planet_weights)
    normalized_chart_type = _normalize_chart_type(chart_type)
    chart.chart_type = normalized_chart_type
    chart.source = normalized_chart_type
    chart.is_placeholder = bool(is_placeholder)
    chart.is_deceased = bool(is_deceased)
    chart.birth_month = birth_month
    chart.birth_day = birth_day
    chart.birth_year = birth_year
    return chart

def load_dominant_sign_weights(
    chart_ids: list[int],
) -> dict[int, dict[str, float]]:
    if not chart_ids:
        return {}
    placeholders = ", ".join("?" for _ in chart_ids)
    conn = _get_conn()
    cur = conn.execute(
        f"""
        SELECT id, dominant_sign_weights
        FROM charts
        WHERE id IN ({placeholders})
        """,
        chart_ids,
    )
    rows = cur.fetchall()
    conn.close()
    return {
        int(row[0]): _parse_weight_map(row[1])
        for row in rows
    }


def update_chart_dominant_sign_weights(
    chart_id: int,
    dominant_sign_weights: dict[str, float],
) -> None:
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            UPDATE charts
            SET dominant_sign_weights = ?
            WHERE id = ?
            """,
            (
                _serialize_weight_map(dominant_sign_weights),
                chart_id,
            ),
        )
    conn.close()
