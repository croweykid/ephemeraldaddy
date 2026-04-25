# ephemeraldaddy/core/db.py

from __future__ import annotations

import json
import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, List, Tuple, Optional

from zoneinfo import ZoneInfo
from ephemeraldaddy.core.chart import (
    Chart,
    apply_time_specific_metadata_policy,
    chart_uses_houses,
    compute_unknown_sign_positions,
)
from ephemeraldaddy.core.interpretations import RELATION_TYPE, SENTIMENT_OPTIONS
from ephemeraldaddy.analysis.bazi_getter import UNKNOWN_BAZI_VALUE, build_bazi_chart_data


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

CHART_DB_EXPORT_LOCKED_COLUMNS: set[str] = {
    "id",
    "name",
    "datetime_iso",
    "birth_place",
    "tz_name",
    "lat",
    "lon",
    "created_at",
    "chart_type",
    "source",
    "birthtime_unknown",
    "signs_unknown",
    "unknown_signs",
    "is_placeholder",
    "is_deceased",
    "birth_month",
    "birth_day",
    "birth_year",
    "is_current",
}

CHART_EXPORT_HIDDEN_COLUMNS: set[str] = {
    "is_current",
}

CHART_EXPORT_LABEL_OVERRIDES: dict[str, str] = {
    "chart_type": "Category",
}

CHART_EXPORT_DEFAULTS: dict[str, Any] = {
    "alias": "",
    "from_whence": "",
    "gender": "",
    "birth_place": "",
    "tz_name": "",
    "used_utc_fallback": 0,
    "sentiments": "",
    "relationship_types": "",
    "tags": "",
    "comments": "",
    "rectification_notes": "",
    "positive_sentiment_intensity": 0,
    "negative_sentiment_intensity": 0,
    "familiarity": 0,
    "alignment_score": None,
    "matched_expectations": 0,
    "familiarity_factors": "",
    "age_when_first_met": 0,
    "year_first_encountered": None,
    "data_rating": "blank",
    "social_score": 0,
    "birthtime_unknown": 0,
    "retcon_time_used": 0,
    "signs_unknown": 0,
    "unknown_signs": "",
    "retcon_hour": None,
    "retcon_minute": None,
    "dominant_sign_weights": "",
    "dominant_planet_weights": "",
    "dominant_nakshatra_weights": "",
    "dominant_element_weights": "",
    "dominant_mode": "",
    "modal_distribution": "",
    "human_design_gates": "",
    "human_design_lines": "",
    "human_design_channels": "",
    "human_design_type": "",
    "human_design_authority": "",
    "bazi_year_pillar": "",
    "bazi_month_pillar": "",
    "bazi_day_pillar": "",
    "bazi_hour_pillar": "",
    "bazi_year_element": "",
    "bazi_month_element": "",
    "bazi_day_element": "",
    "bazi_hour_element": "",
    "is_placeholder": 0,
    "is_deceased": 0,
    "birth_month": 0,
    "birth_day": 0,
    "birth_year": 0,
    "is_current": 0,
}


def _ensure_alignment_score_nullable(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA table_info(charts)").fetchall()
    alignment_rows = [info for info in row if str(info[1]) == "alignment_score"]
    if not alignment_rows:
        return
    alignment_info = alignment_rows[0]
    alignment_not_null = bool(alignment_info[3])
    if not alignment_not_null:
        return

    conn.execute("ALTER TABLE charts RENAME TO charts_legacy_alignment_not_null")
    _create_charts_table(conn)

    legacy_columns = _table_columns(conn, "charts_legacy_alignment_not_null")
    new_table_info = conn.execute("PRAGMA table_info(charts)").fetchall()
    ordered_new_columns = [str(info[1]) for info in new_table_info]
    transferable_columns = [column for column in ordered_new_columns if column in legacy_columns]
    quoted_columns = ", ".join([f'"{column}"' for column in transferable_columns])
    conn.execute(
        f"""
        INSERT INTO charts ({quoted_columns})
        SELECT {quoted_columns}
        FROM charts_legacy_alignment_not_null
        """
    )
    conn.execute("DROP TABLE charts_legacy_alignment_not_null")
    _create_indexes(conn)


def _ensure_sentiment_metrics_nullable(conn: sqlite3.Connection) -> None:
    table_info = conn.execute("PRAGMA table_info(charts)").fetchall()
    target_columns = {
        "positive_sentiment_intensity",
        "negative_sentiment_intensity",
        "familiarity",
    }
    not_null_targets = {
        str(info[1])
        for info in table_info
        if str(info[1]) in target_columns and bool(info[3])
    }
    if not not_null_targets:
        return

    conn.execute("ALTER TABLE charts RENAME TO charts_legacy_sentiment_metrics_not_null")
    _create_charts_table(conn)

    legacy_columns = _table_columns(conn, "charts_legacy_sentiment_metrics_not_null")
    new_table_info = conn.execute("PRAGMA table_info(charts)").fetchall()
    ordered_new_columns = [str(info[1]) for info in new_table_info]
    transferable_columns = [column for column in ordered_new_columns if column in legacy_columns]
    quoted_columns = ", ".join([f'"{column}"' for column in transferable_columns])
    conn.execute(
        f"""
        INSERT INTO charts ({quoted_columns})
        SELECT {quoted_columns}
        FROM charts_legacy_sentiment_metrics_not_null
        """
    )
    conn.execute("DROP TABLE charts_legacy_sentiment_metrics_not_null")
    _create_indexes(conn)


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


SCHEMA_VERSION = 12

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
            from_whence       TEXT,
            gender            TEXT,
            birth_place       TEXT,
            datetime_iso      TEXT NOT NULL,
            tz_name           TEXT,
            lat               REAL NOT NULL,
            lon               REAL NOT NULL,
            used_utc_fallback INTEGER NOT NULL DEFAULT 0,
            sentiments        TEXT,
            relationship_types TEXT,
            tags              TEXT,
            comments          TEXT,
            rectification_notes TEXT,
            biography         TEXT,
            chart_data_source TEXT,
            positive_sentiment_intensity INTEGER,
            negative_sentiment_intensity INTEGER,
            familiarity INTEGER,
            alignment_score INTEGER,
            matched_expectations INTEGER NOT NULL DEFAULT 0,
            familiarity_factors TEXT,
            age_when_first_met INTEGER NOT NULL DEFAULT 0,
            year_first_encountered INTEGER,
            data_rating TEXT NOT NULL DEFAULT 'blank',
            social_score INTEGER NOT NULL DEFAULT 0,
            birthtime_unknown INTEGER NOT NULL DEFAULT 0,
            signs_unknown    INTEGER NOT NULL DEFAULT 0,
            unknown_signs    TEXT,
            retcon_time_used  INTEGER NOT NULL DEFAULT 0,
            retcon_hour       INTEGER,
            retcon_minute     INTEGER,
            dominant_sign_weights TEXT,
            dominant_planet_weights TEXT,
            dominant_nakshatra_weights TEXT,
            dominant_element_weights TEXT,
            dominant_enneagram_type INTEGER,
            top_three_enneagram_types TEXT,
            dominant_mode TEXT,
            modal_distribution TEXT,
            human_design_gates TEXT,
            human_design_lines TEXT,
            human_design_channels TEXT,
            human_design_type TEXT,
            human_design_authority TEXT,
            bazi_year_pillar TEXT,
            bazi_month_pillar TEXT,
            bazi_day_pillar TEXT,
            bazi_hour_pillar TEXT,
            bazi_year_element TEXT,
            bazi_month_element TEXT,
            bazi_day_element TEXT,
            bazi_hour_element TEXT,
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
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_charts_birth_month_day
        ON charts(birth_month, birth_day)
        """
    )


def _create_duplicate_exclusions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS duplicate_exclusions (
            chart_id_low  INTEGER NOT NULL,
            chart_id_high INTEGER NOT NULL,
            created_at    TEXT NOT NULL,
            PRIMARY KEY (chart_id_low, chart_id_high),
            CHECK (chart_id_low < chart_id_high)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_duplicate_exclusions_low
        ON duplicate_exclusions(chart_id_low)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_duplicate_exclusions_high
        ON duplicate_exclusions(chart_id_high)
        """
    )


def _prune_duplicate_exclusions(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        DELETE FROM duplicate_exclusions
        WHERE chart_id_low NOT IN (SELECT id FROM charts)
           OR chart_id_high NOT IN (SELECT id FROM charts)
        """
    )


def _migrate_charts_columns(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "charts")
    added_year_first_encountered = False
    added_familiarity = False
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
    if "from_whence" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN from_whence TEXT
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
    if "signs_unknown" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN signs_unknown INTEGER NOT NULL DEFAULT 0
            """
        )
    if "unknown_signs" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN unknown_signs TEXT
            """
        )
    if "tags" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN tags TEXT
            """
        )
    if "comments" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN comments TEXT
            """
        )
    if "rectification_notes" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN rectification_notes TEXT
            """
        )
    if "biography" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN biography TEXT
            """
        )
    if "chart_data_source" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN chart_data_source TEXT
            """
        )
    if "positive_sentiment_intensity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN positive_sentiment_intensity INTEGER
            """
        )
    if "negative_sentiment_intensity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN negative_sentiment_intensity INTEGER
            """
        )
    if "familiarity" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN familiarity INTEGER
            """
        )
        added_familiarity = True
    if "alignment_score" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN alignment_score INTEGER
            """
        )
    if "matched_expectations" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN matched_expectations INTEGER NOT NULL DEFAULT 0
            """
        )
    #indent?
    if added_familiarity and "sentiment_confidence" in columns:
        conn.execute(
            """
            UPDATE charts
            SET familiarity = sentiment_confidence
            WHERE familiarity IS NULL
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
    if "data_rating" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN data_rating TEXT NOT NULL DEFAULT 'blank'
            """
        )

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
    if "dominant_nakshatra_weights" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_nakshatra_weights TEXT
            """
        )
    if "dominant_element_weights" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_element_weights TEXT
            """
        )
    if "dominant_enneagram_type" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_enneagram_type INTEGER
            """
        )
    if "top_three_enneagram_types" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN top_three_enneagram_types TEXT
            """
        )
    if "dominant_mode" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN dominant_mode TEXT
            """
        )
    if "modal_distribution" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN modal_distribution TEXT
            """
        )
    if "human_design_gates" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN human_design_gates TEXT
            """
        )
    if "human_design_lines" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN human_design_lines TEXT
            """
        )
    if "human_design_channels" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN human_design_channels TEXT
            """
        )
    if "human_design_type" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN human_design_type TEXT
            """
        )
    if "human_design_authority" not in columns:
        conn.execute(
            """
            ALTER TABLE charts
            ADD COLUMN human_design_authority TEXT
            """
        )
    for bazi_column in (
        "bazi_year_pillar",
        "bazi_month_pillar",
        "bazi_day_pillar",
        "bazi_hour_pillar",
        "bazi_year_element",
        "bazi_month_element",
        "bazi_day_element",
        "bazi_hour_element",
    ):
        if bazi_column not in columns:
            conn.execute(
                f"""
                ALTER TABLE charts
                ADD COLUMN {bazi_column} TEXT
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

    _ensure_alignment_score_nullable(conn)
    _ensure_sentiment_metrics_nullable(conn)

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
    _create_duplicate_exclusions_table(conn)
    _prune_duplicate_exclusions(conn)

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
        user_version = 8

    if user_version < 9:
        _create_indexes(conn)
        conn.execute("PRAGMA user_version = 9")
        user_version = 9

    if user_version < 10:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 10")
        user_version = 10

    if user_version < 11:
        _migrate_charts_columns(conn)
        conn.execute("PRAGMA user_version = 11")
        user_version = 11
    if user_version < 12:
        _create_duplicate_exclusions_table(conn)
        _prune_duplicate_exclusions(conn)
        conn.execute("PRAGMA user_version = 12")

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


def _serialize_tags(tags: Optional[list[str]]) -> Optional[str]:
    if not tags:
        return None
    return ", ".join(value.strip() for value in tags if value.strip())

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


def _serialize_int_list(values: Optional[list[int]]) -> Optional[str]:
    if values is None:
        return None
    normalized = [int(value) for value in values if isinstance(value, int)]
    return json.dumps(normalized)


def _parse_int_list(value: Optional[str]) -> list[int]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    values: list[int] = []
    for item in parsed:
        if isinstance(item, int):
            values.append(int(item))
    return values


def _serialize_string_list(values: Optional[list[str]]) -> Optional[str]:
    if values is None:
        return None
    normalized = [str(value).strip() for value in values if str(value).strip()]
    return json.dumps(normalized)


def _parse_string_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    values: list[str] = []
    for item in parsed:
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _resolve_unknown_sign_metadata(
    chart: Any,
    *,
    birthtime_unknown: Optional[bool],
    retcon_time_used: Optional[bool],
) -> tuple[bool, list[str]]:
    resolved_birthtime_unknown = bool(
        birthtime_unknown
        if birthtime_unknown is not None
        else getattr(chart, "birthtime_unknown", False)
    )
    resolved_retcon_time_used = bool(
        retcon_time_used
        if retcon_time_used is not None
        else getattr(chart, "retcon_time_used", False)
    )
    # "Conditional indicators for unknown birth time" are factual reminders and
    # should remain available whenever birth time is marked unknown, regardless
    # of whether a rectified/retcon time is also enabled.
    if not resolved_birthtime_unknown:
        return False, []

    original_birthtime_unknown = bool(getattr(chart, "birthtime_unknown", False))
    original_retcon_time_used = bool(getattr(chart, "retcon_time_used", False))
    try:
        chart.birthtime_unknown = resolved_birthtime_unknown
        chart.retcon_time_used = resolved_retcon_time_used
        unknown_positions = compute_unknown_sign_positions(chart)
    except Exception:
        unknown_positions = []
    finally:
        chart.birthtime_unknown = original_birthtime_unknown
        chart.retcon_time_used = original_retcon_time_used

    return bool(unknown_positions), list(unknown_positions)


def _resolve_human_design_metadata(chart: Any) -> tuple[Optional[str], Optional[str]]:
    hd_type = str(getattr(chart, "human_design_type", "") or "").strip()
    hd_authority = str(getattr(chart, "human_design_authority", "") or "").strip()
    if hd_type and hd_authority:
        return hd_type, hd_authority
    if not getattr(chart, "positions", None):
        return hd_type or None, hd_authority or None
    try:
        from ephemeraldaddy.analysis.human_design import build_human_design_result
        from ephemeraldaddy.analysis.human_design_reference import canonicalize_hd_authority_label

        hd_result = build_human_design_result(chart)
    except Exception:
        return hd_type or None, hd_authority or None

    resolved_type = str(getattr(hd_result, "hd_type", "") or "").strip() or hd_type
    resolved_authority = canonicalize_hd_authority_label(
        str(getattr(hd_result, "authority", "") or "").strip()
    ) or hd_authority
    chart.human_design_type = resolved_type
    chart.human_design_authority = resolved_authority
    return resolved_type or None, resolved_authority or None


def _resolve_bazi_metadata(chart: Any) -> dict[str, Optional[str]]:
    metadata = {
        "bazi_year_pillar": str(getattr(chart, "bazi_year_pillar", "") or "").strip() or None,
        "bazi_month_pillar": str(getattr(chart, "bazi_month_pillar", "") or "").strip() or None,
        "bazi_day_pillar": str(getattr(chart, "bazi_day_pillar", "") or "").strip() or None,
        "bazi_hour_pillar": str(getattr(chart, "bazi_hour_pillar", "") or "").strip() or None,
        "bazi_year_element": str(getattr(chart, "bazi_year_element", "") or "").strip() or None,
        "bazi_month_element": str(getattr(chart, "bazi_month_element", "") or "").strip() or None,
        "bazi_day_element": str(getattr(chart, "bazi_day_element", "") or "").strip() or None,
        "bazi_hour_element": str(getattr(chart, "bazi_hour_element", "") or "").strip() or None,
    }
    if any(value for value in metadata.values()):
        return metadata
    if bool(getattr(chart, "is_placeholder", False)):
        return metadata
    dt_local = getattr(chart, "dt_local", None)
    if dt_local is None:
        chart_dt = getattr(chart, "dt", None)
        if isinstance(chart_dt, datetime):
            if chart_dt.tzinfo is not None:
                dt_local = chart_dt.astimezone(chart_dt.tzinfo).replace(tzinfo=None)
            else:
                dt_local = chart_dt
    if not isinstance(dt_local, datetime):
        return metadata
    include_hour = chart_uses_houses(chart)
    if include_hour and bool(getattr(chart, "retcon_time_used", False)):
        retcon_hour = getattr(chart, "retcon_hour", None)
        retcon_minute = getattr(chart, "retcon_minute", None)
        if retcon_hour is not None and retcon_minute is not None:
            dt_local = dt_local.replace(
                hour=int(retcon_hour),
                minute=int(retcon_minute),
                second=0,
                microsecond=0,
            )
    try:
        bazi_data = build_bazi_chart_data(dt_local, include_hour=include_hour)
    except Exception:
        return metadata
    metadata = {
        "bazi_year_pillar": str(getattr(bazi_data, "year_pillar", "") or "").strip() or None,
        "bazi_month_pillar": str(getattr(bazi_data, "month_pillar", "") or "").strip() or None,
        "bazi_day_pillar": str(getattr(bazi_data, "day_pillar", "") or "").strip() or None,
        "bazi_hour_pillar": str(getattr(bazi_data, "hour_pillar", "") or "").strip() or None,
        "bazi_year_element": str((bazi_data.five_elements_summary or {}).get("year", "") or "").strip() or None,
        "bazi_month_element": str((bazi_data.five_elements_summary or {}).get("month", "") or "").strip() or None,
        "bazi_day_element": str((bazi_data.five_elements_summary or {}).get("day", "") or "").strip() or None,
        "bazi_hour_element": str((bazi_data.five_elements_summary or {}).get("hour", "") or "").strip() or None,
    }
    for key, value in metadata.items():
        setattr(chart, key, None if value == UNKNOWN_BAZI_VALUE else value)
    return metadata

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

def _normalize_optional_sentiment_metric(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"", "blank", "none", "null", "unset", "unknown"}:
            return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if 1 <= parsed <= 10:
        return parsed
    return None


def _normalize_sentiment_metric(value: Optional[int]) -> int:
    optional_value = _normalize_optional_sentiment_metric(value)
    return optional_value if optional_value is not None else 1


def _normalize_alignment_score(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return max(-10, min(10, parsed))


def _normalize_matched_expectations(value: Optional[int]) -> int:
    if value is None:
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(9, parsed))


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


def parse_tags(value: Optional[str]) -> list[str]:
    if not value:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw_value in value.split(","):
        tag = raw_value.strip()
        if not tag:
            continue
        dedupe_key = tag.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(tag)
    return normalized


def list_recognized_tags() -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT tags FROM charts").fetchall()
    deduped: dict[str, str] = {}
    for (raw_tags,) in rows:
        for tag in parse_tags(raw_tags):
            key = tag.casefold()
            if key not in deduped:
                deduped[key] = tag
    return sorted(deduped.values(), key=lambda value: value.casefold())

def add_tag_to_charts(chart_ids: Iterable[int], tag_value: str) -> set[int]:
    """Add one tag to many charts and return ids that actually changed."""
    normalized_tag = str(tag_value or "").strip()
    if not normalized_tag:
        return set()

    normalized_ids = sorted({int(chart_id) for chart_id in chart_ids})
    if not normalized_ids:
        return set()

    placeholders = ", ".join("?" for _ in normalized_ids)
    changed_ids: set[int] = set()
    normalized_key = normalized_tag.casefold()
    with _get_conn() as conn:
        rows = conn.execute(
            f"SELECT id, tags FROM charts WHERE id IN ({placeholders})",
            tuple(normalized_ids),
        ).fetchall()
        for row_id, raw_tags in rows:
            existing_tags = parse_tags(raw_tags)
            if any(tag.casefold() == normalized_key for tag in existing_tags):
                continue
            existing_tags.append(normalized_tag)
            conn.execute(
                "UPDATE charts SET tags = ? WHERE id = ?",
                (_serialize_tags(existing_tags), int(row_id)),
            )
            changed_ids.add(int(row_id))
    return changed_ids

def get_metadata_label_usage() -> dict[str, list[dict[str, int | str]]]:
    """Return sentiment, relationship, and tag labels with usage counts.

    Includes both current canonical options and any legacy labels currently stored
    in the database.
    """
    sentiment_counts: dict[str, int] = {label: 0 for label in SENTIMENT_OPTIONS}
    relationship_counts: dict[str, int] = {label: 0 for label in RELATION_TYPE}
    tag_counts: dict[str, tuple[str, int]] = {}

    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT sentiments, relationship_types, tags FROM charts"
        ).fetchall()

    for raw_sentiments, raw_relationship_types, raw_tags in rows:
        for sentiment in parse_sentiments(raw_sentiments):
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        for relationship in parse_relationship_types(raw_relationship_types):
            relationship_counts[relationship] = relationship_counts.get(relationship, 0) + 1
        for tag in parse_tags(raw_tags):
            tag_key = tag.casefold()
            if tag_key in tag_counts:
                existing_label, count = tag_counts[tag_key]
                tag_counts[tag_key] = (existing_label, count + 1)
            else:
                tag_counts[tag_key] = (tag, 1)

    def _format_rows(counts: dict[str, int]) -> list[dict[str, int | str]]:
        return [
            {"label": label, "count": counts[label]}
            for label in sorted(counts, key=lambda value: (value.lower(), value))
        ]

    return {
        "sentiments": _format_rows(sentiment_counts),
        "relationship_types": _format_rows(relationship_counts),
        "tags": [
            {"label": label, "count": count}
            for _key, (label, count) in sorted(
                tag_counts.items(),
                key=lambda item: (item[1][0].casefold(), item[1][0]),
            )
        ],
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

    old_key = normalized_old.casefold()

    if field == "sentiments":
        parser = parse_sentiments
        serializer = _serialize_sentiments
        column = "sentiments"
        match_casefold = False
    elif field == "relationship_types":
        parser = parse_relationship_types
        serializer = _serialize_relationship_types
        column = "relationship_types"
        match_casefold = False
    elif field == "tags":
        parser = parse_tags
        serializer = _serialize_tags
        column = "tags"
        match_casefold = True
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
                matched = value.casefold() == old_key if match_casefold else value == normalized_old
                if matched:
                    occurrences_updated += 1
                    row_changed = True
                    replacement = normalized_new

                dedupe_key = replacement.casefold() if match_casefold else replacement
                if not replacement or dedupe_key in seen:
                    continue
                rebuilt.append(replacement)
                seen.add(dedupe_key)

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


def _parse_sqlite_default_value(raw_value: Any) -> Any:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    if text.startswith("'") and text.endswith("'") and len(text) >= 2:
        return text[1:-1]
    lowered = text.lower()
    if lowered == "null":
        return None
    if lowered in {"true", "false"}:
        return 1 if lowered == "true" else 0
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _resolve_chart_export_reset_value(column: str, pragma_row: Any) -> Any:
    sentinel = object()
    configured = CHART_EXPORT_DEFAULTS.get(column, sentinel)
    if configured is not sentinel:
        return configured
    if pragma_row is None:
        return None
    not_null = bool(pragma_row[3])
    parsed_default = _parse_sqlite_default_value(pragma_row[4])
    if parsed_default is not None:
        return parsed_default
    return 0 if not_null else None


def list_chart_export_properties() -> list[dict[str, Any]]:
    """Return chart-table properties that can be selected during custom export."""
    conn = _get_conn()
    try:
        if not _charts_table_exists(conn):
            return []
        rows = conn.execute("PRAGMA table_info(charts)").fetchall()
    finally:
        conn.close()

    properties: list[dict[str, Any]] = []
    for row in rows:
        column_name = str(row[1])
        if not column_name:
            continue
        if column_name in CHART_EXPORT_HIDDEN_COLUMNS:
            continue
        label = CHART_EXPORT_LABEL_OVERRIDES.get(
            column_name,
            column_name.replace("_", " ").strip().title(),
        )
        properties.append(
            {
                "column": column_name,
                "label": label,
                "locked_for_db": column_name in CHART_DB_EXPORT_LOCKED_COLUMNS,
            }
        )
    return properties


def export_database_with_chart_property_selection(
    destination: Path,
    included_columns: list[str],
    included_chart_ids: list[int] | None = None,
) -> Path:
    """
    Export a DB backup and reset excluded chart properties to app defaults.
    """
    destination = Path(destination)
    selected = {str(column).strip() for column in included_columns if str(column).strip()}
    selected_chart_ids = (
        sorted({int(chart_id) for chart_id in included_chart_ids})
        if included_chart_ids is not None
        else None
    )
    backup_database(destination)

    conn = sqlite3.connect(destination)
    try:
        if not _charts_table_exists(conn):
            return destination
        pragma_rows = conn.execute("PRAGMA table_info(charts)").fetchall()
        chart_columns = {str(row[1]) for row in pragma_rows}
        editable_columns = chart_columns - CHART_DB_EXPORT_LOCKED_COLUMNS
        excluded_columns = sorted(editable_columns - selected)
        pragma_by_column = {str(row[1]): row for row in pragma_rows}
        with conn:
            if selected_chart_ids is not None:
                conn.execute("DROP TABLE IF EXISTS temp.selected_export_ids")
                conn.execute("CREATE TEMP TABLE selected_export_ids (id INTEGER PRIMARY KEY)")
                if selected_chart_ids:
                    conn.executemany(
                        "INSERT INTO selected_export_ids(id) VALUES (?)",
                        [(chart_id,) for chart_id in selected_chart_ids],
                    )
                conn.execute(
                    "DELETE FROM charts WHERE id NOT IN (SELECT id FROM selected_export_ids)"
                )
            for column in excluded_columns:
                reset_value = _resolve_chart_export_reset_value(
                    column,
                    pragma_by_column.get(column),
                )
                if selected_chart_ids is None:
                    conn.execute(f"UPDATE charts SET {column} = ?", (reset_value,))
                else:
                    conn.execute(
                        f"UPDATE charts SET {column} = ? WHERE id IN (SELECT id FROM selected_export_ids)",
                        (reset_value,),
                    )
    finally:
        conn.close()
    return destination


def export_chart_properties_csv(
    destination: Path,
    included_columns: list[str],
    included_chart_ids: list[int] | None = None,
) -> Path:
    """Export selected chart columns from DB as CSV."""
    destination = Path(destination)
    selected = [str(column).strip() for column in included_columns if str(column).strip()]
    selected_chart_ids = (
        sorted({int(chart_id) for chart_id in included_chart_ids})
        if included_chart_ids is not None
        else None
    )
    if not selected:
        raise ValueError("At least one property must be selected for CSV export.")

    conn = _get_conn()
    try:
        if not _charts_table_exists(conn):
            raise ValueError("No charts table found in the active database.")
        chart_columns = _table_columns(conn, "charts")
        final_columns = [column for column in selected if column in chart_columns]
        if not final_columns:
            raise ValueError("Selected properties are not available in the current database.")
        quoted_columns = ", ".join([f'"{column}"' for column in final_columns])
        if selected_chart_ids is None:
            rows = conn.execute(f"SELECT {quoted_columns} FROM charts ORDER BY id ASC").fetchall()
        else:
            conn.execute("DROP TABLE IF EXISTS temp.selected_export_ids")
            conn.execute("CREATE TEMP TABLE selected_export_ids (id INTEGER PRIMARY KEY)")
            if selected_chart_ids:
                conn.executemany(
                    "INSERT INTO selected_export_ids(id) VALUES (?)",
                    [(chart_id,) for chart_id in selected_chart_ids],
                )
            rows = conn.execute(
                f"SELECT {quoted_columns} FROM charts WHERE id IN (SELECT id FROM selected_export_ids) ORDER BY id ASC"
            ).fetchall()
    finally:
        conn.close()

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(final_columns)
        for row in rows:
            writer.writerow([row[index] for index in range(len(final_columns))])
    return destination


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


def append_database(source: Path) -> dict[str, Any]:
    """Append charts from another SQLite database into the active database."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Database file not found: {source}")

    source_conn = sqlite3.connect(source)
    source_conn.row_factory = sqlite3.Row
    target_conn = _get_conn()

    issues: list[dict[str, Any]] = []
    imported = 0
    skipped = 0
    warned = 0

    try:
        if not _charts_table_exists(source_conn):
            raise ValueError("The selected database has no 'charts' table to append.")

        source_columns = _table_columns(source_conn, "charts")
        target_max_id_row = target_conn.execute("SELECT COALESCE(MAX(id), 0) FROM charts").fetchone()
        target_max_id = int(target_max_id_row[0] or 0) if target_max_id_row else 0

        source_rows = source_conn.execute("SELECT * FROM charts ORDER BY id ASC").fetchall()
        now_iso = datetime.utcnow().isoformat(timespec="seconds")

        with target_conn:
            for row_index, row in enumerate(source_rows, start=1):
                source_id_raw = row["id"] if "id" in source_columns else row_index
                try:
                    source_id = int(source_id_raw)
                    if source_id <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    source_id = row_index
                    issues.append(
                        {
                            "chart_id": None,
                            "name": str(row["name"] or "Unnamed") if "name" in source_columns else "Unnamed",
                            "severity": "warning",
                            "error": "Invalid source chart_id; assigned a sequential fallback id.",
                        }
                    )

                new_chart_id = target_max_id + source_id

                chart_name = (
                    str(row["name"]).strip()
                    if "name" in source_columns and row["name"] is not None
                    else ""
                )
                if not chart_name:
                    chart_name = "Unnamed"
                    issues.append(
                        {
                            "chart_id": new_chart_id,
                            "name": chart_name,
                            "severity": "warning",
                            "error": "Missing name; backfilled as 'Unnamed'.",
                        }
                    )

                datetime_iso = (
                    str(row["datetime_iso"]).strip()
                    if "datetime_iso" in source_columns and row["datetime_iso"] is not None
                    else ""
                )
                if not datetime_iso:
                    skipped += 1
                    issues.append(
                        {
                            "chart_id": new_chart_id,
                            "name": chart_name,
                            "severity": "error",
                            "error": "Missing required datetime_iso; row skipped.",
                        }
                    )
                    continue

                try:
                    parsed_dt = datetime.fromisoformat(datetime_iso)
                except Exception:
                    parsed_dt = None

                lat = row["lat"] if "lat" in source_columns else None
                lon = row["lon"] if "lon" in source_columns else None
                if lat is None or lon is None:
                    skipped += 1
                    issues.append(
                        {
                            "chart_id": new_chart_id,
                            "name": chart_name,
                            "severity": "error",
                            "error": "Missing required latitude/longitude; row skipped.",
                        }
                    )
                    continue

                concerns_for_row = 0

                def _row_value(column: str, default: Any = None) -> Any:
                    return row[column] if column in source_columns else default

                birth_month = _row_value("birth_month")
                birth_day = _row_value("birth_day")
                birth_year = _row_value("birth_year")
                if parsed_dt is not None:
                    if birth_month is None:
                        birth_month = parsed_dt.month
                        concerns_for_row += 1
                    if birth_day is None:
                        birth_day = parsed_dt.day
                        concerns_for_row += 1
                    if birth_year is None:
                        birth_year = parsed_dt.year
                        concerns_for_row += 1
                elif any(value is None for value in (birth_month, birth_day, birth_year)):
                    concerns_for_row += 1

                pos_intensity = _normalize_sentiment_metric(_row_value("positive_sentiment_intensity"))
                neg_intensity = _normalize_sentiment_metric(_row_value("negative_sentiment_intensity"))
                familiarity = _normalize_sentiment_metric(_row_value("familiarity"))
                social_score = _row_value("social_score")
                if social_score is None:
                    social_score = calculate_social_score(pos_intensity, neg_intensity, familiarity)
                    concerns_for_row += 1

                resolved_chart_type = _normalize_chart_type(
                    _row_value("chart_type")
                    or _row_value("source")
                    or CHART_TYPE_PERSONAL
                )

                used_utc_fallback = int(_row_value("used_utc_fallback") or 0)
                if concerns_for_row > 0:
                    used_utc_fallback = 1
                    warned += 1
                    issues.append(
                        {
                            "chart_id": new_chart_id,
                            "name": chart_name,
                            "severity": "warning",
                            "error": "Schema/data backfill applied; row flagged with ⚠️ for review.",
                        }
                    )

                target_conn.execute(
                    """
                    INSERT INTO charts
                        (id, name, alias, from_whence, gender, birth_place, datetime_iso, tz_name,
                         lat, lon, used_utc_fallback, sentiments, relationship_types, tags, comments, rectification_notes, biography, chart_data_source,
                         positive_sentiment_intensity, negative_sentiment_intensity, familiarity,
                         alignment_score, matched_expectations, familiarity_factors, age_when_first_met, year_first_encountered, data_rating,
                         social_score, birthtime_unknown, signs_unknown, unknown_signs, retcon_time_used, retcon_hour, retcon_minute,
                         dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights, dominant_element_weights, dominant_mode, modal_distribution,
                         human_design_gates, human_design_lines, human_design_channels,
                         human_design_type, human_design_authority,
                         bazi_year_pillar, bazi_month_pillar, bazi_day_pillar, bazi_hour_pillar,
                         bazi_year_element, bazi_month_element, bazi_day_element, bazi_hour_element,
                         chart_type, source,
                         is_placeholder, is_deceased, birth_month, birth_day, birth_year, created_at, is_current)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_chart_id,
                        chart_name,
                        _row_value("alias"),
                        _row_value("from_whence"),
                        _row_value("gender"),
                        _row_value("birth_place"),
                        datetime_iso,
                        _row_value("tz_name"),
                        float(lat),
                        float(lon),
                        used_utc_fallback,
                        _row_value("sentiments"),
                        _row_value("relationship_types"),
                        _row_value("tags"),
                        _row_value("comments"),
                        _row_value("rectification_notes"),
                        _row_value("biography"),
                        _row_value("chart_data_source"),
                        pos_intensity,
                        neg_intensity,
                        familiarity,
                        _normalize_alignment_score(_row_value("alignment_score")),
                        _normalize_matched_expectations(_row_value("matched_expectations")),
                        _row_value("familiarity_factors"),
                        max(0, int(_row_value("age_when_first_met") or 0)),
                        _normalize_year_first_encountered(_row_value("year_first_encountered")),
                        str(_row_value("data_rating") or "blank"),
                        int(social_score),
                        int(_row_value("birthtime_unknown") or 0),
                        int(_row_value("signs_unknown") or 0),
                        _row_value("unknown_signs"),
                        int(_row_value("retcon_time_used") or 0),
                        int(_row_value("retcon_hour")) if _row_value("retcon_hour") is not None else None,
                        int(_row_value("retcon_minute")) if _row_value("retcon_minute") is not None else None,
                        _row_value("dominant_sign_weights"),
                        _row_value("dominant_planet_weights"),
                        _row_value("dominant_nakshatra_weights"),
                        _row_value("dominant_element_weights"),
                        _row_value("dominant_mode"),
                        _row_value("modal_distribution"),
                        _row_value("human_design_gates"),
                        _row_value("human_design_lines"),
                        _row_value("human_design_channels"),
                        _row_value("human_design_type"),
                        _row_value("human_design_authority"),
                        _row_value("bazi_year_pillar"),
                        _row_value("bazi_month_pillar"),
                        _row_value("bazi_day_pillar"),
                        _row_value("bazi_hour_pillar"),
                        _row_value("bazi_year_element"),
                        _row_value("bazi_month_element"),
                        _row_value("bazi_day_element"),
                        _row_value("bazi_hour_element"),
                        resolved_chart_type,
                        resolved_chart_type,
                        int(_row_value("is_placeholder") or 0),
                        int(_row_value("is_deceased") or 0),
                        int(birth_month) if birth_month is not None else None,
                        int(birth_day) if birth_day is not None else None,
                        int(birth_year) if birth_year is not None else None,
                        _row_value("created_at") or now_iso,
                        0,
                    ),
                )
                imported += 1
    finally:
        source_conn.close()
        target_conn.close()

    return {
        "imported": imported,
        "skipped": skipped,
        "warnings": warned,
        "issues": issues,
    }


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
    dominant_nakshatra_weights: Optional[dict[str, float]] = None,
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
    resolved_birthtime_unknown = bool(
        birthtime_unknown
        if birthtime_unknown is not None
        else bool(getattr(chart, "birthtime_unknown", False))
    )
    resolved_retcon_time_used = bool(
        retcon_time_used
        if retcon_time_used is not None
        else bool(getattr(chart, "retcon_time_used", False))
    )
    chart.birthtime_unknown = resolved_birthtime_unknown
    chart.retcon_time_used = resolved_retcon_time_used
    if retcon_hour is not None:
        chart.retcon_hour = int(retcon_hour)
    if retcon_minute is not None:
        chart.retcon_minute = int(retcon_minute)
    apply_time_specific_metadata_policy(chart)
    resolved_signs_unknown, resolved_unknown_signs = _resolve_unknown_sign_metadata(
        chart,
        birthtime_unknown=birthtime_unknown,
        retcon_time_used=retcon_time_used,
    )
    chart.signs_unknown = resolved_signs_unknown
    chart.unknown_signs = list(resolved_unknown_signs)
    human_design_type, human_design_authority = _resolve_human_design_metadata(chart)
    bazi_metadata = _resolve_bazi_metadata(chart)
    conn = _get_conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO charts
                (name, alias, from_whence, gender, birth_place, datetime_iso, tz_name,
                 lat, lon, used_utc_fallback, sentiments, relationship_types, tags,
                 comments,
                 rectification_notes,
                 biography,
                 chart_data_source,
                 positive_sentiment_intensity, negative_sentiment_intensity,
                 familiarity, alignment_score, matched_expectations, familiarity_factors, age_when_first_met, year_first_encountered, data_rating, social_score,
                 birthtime_unknown,
                 signs_unknown, unknown_signs,
                 retcon_time_used, retcon_hour, retcon_minute,
                 dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights, dominant_element_weights, dominant_enneagram_type, top_three_enneagram_types, dominant_mode, modal_distribution,
                 human_design_gates, human_design_lines, human_design_channels,
                 human_design_type, human_design_authority,
                 bazi_year_pillar, bazi_month_pillar, bazi_day_pillar, bazi_hour_pillar,
                 bazi_year_element, bazi_month_element, bazi_day_element, bazi_hour_element,
                 chart_type,
                 source,
                 is_placeholder,
                 is_deceased,
                 birth_month,
                 birth_day,
                 birth_year,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chart.name,
                getattr(chart, "alias", None),
                getattr(chart, "from_whence", None),
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
                _serialize_tags(getattr(chart, "tags", [])),
                getattr(chart, "comments", None),
                getattr(chart, "rectification_notes", None),
                getattr(chart, "biography", None),
                getattr(chart, "chart_data_source", None),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "positive_sentiment_intensity", None)
                ),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "negative_sentiment_intensity", None)
                ),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "familiarity", None)
                ),
                _normalize_alignment_score(
                    getattr(chart, "alignment_score", None)
                ),
                _normalize_matched_expectations(
                    getattr(chart, "matched_expectations", None)
                ),
                _serialize_familiarity_factors(
                    getattr(chart, "familiarity_factors", [])
                ),
                max(0, int(getattr(chart, "age_when_first_met", 0) or 0)),
                _normalize_year_first_encountered(getattr(chart, "year_first_encountered", None)),
                str(getattr(chart, "data_rating", "blank") or "blank"),
                calculate_social_score(
                    getattr(chart, "positive_sentiment_intensity", None),
                    getattr(chart, "negative_sentiment_intensity", None),
                    getattr(chart, "familiarity", None),
                ),
                int(resolved_birthtime_unknown),
                int(resolved_signs_unknown),
                _serialize_string_list(resolved_unknown_signs),
                int(resolved_retcon_time_used),
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
                _serialize_weight_map(
                    dominant_nakshatra_weights
                    if dominant_nakshatra_weights is not None
                    else getattr(chart, "dominant_nakshatra_weights", None)
                ),
                _serialize_weight_map(getattr(chart, "dominant_element_weights", None)),
                getattr(chart, "dominant_enneagram_type", None),
                _serialize_int_list(getattr(chart, "top_three_enneagram_types", None)),
                getattr(chart, "dominant_mode", None),
                _serialize_weight_map(getattr(chart, "modal_distribution", None)),
                _serialize_int_list(getattr(chart, "human_design_gates", None)),
                _serialize_int_list(getattr(chart, "human_design_lines", None)),
                _serialize_string_list(getattr(chart, "human_design_channels", None)),
                human_design_type,
                human_design_authority,
                bazi_metadata.get("bazi_year_pillar"),
                bazi_metadata.get("bazi_month_pillar"),
                bazi_metadata.get("bazi_day_pillar"),
                bazi_metadata.get("bazi_hour_pillar"),
                bazi_metadata.get("bazi_year_element"),
                bazi_metadata.get("bazi_month_element"),
                bazi_metadata.get("bazi_day_element"),
                bazi_metadata.get("bazi_hour_element"),
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


def find_chart_name_matches_by_birth_day(
    birth_month: Optional[int],
    birth_day: Optional[int],
) -> list[str]:
    """
    Return chart names matching the supplied birth month/day.

    Results are ordered newest-first for fast, relevant duplicate checks.
    """
    if birth_month is None or birth_day is None:
        return []

    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT name
        FROM charts
        WHERE birth_month = ?
          AND birth_day = ?
        ORDER BY created_at DESC, id DESC
        """,
        (int(birth_month), int(birth_day)),
    ).fetchall()
    conn.close()
    return [str(row[0]).strip() for row in rows if row and row[0]]


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
    dominant_nakshatra_weights: Optional[dict[str, float]] = None,
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
    resolved_birthtime_unknown = bool(
        birthtime_unknown
        if birthtime_unknown is not None
        else bool(getattr(chart, "birthtime_unknown", False))
    )
    resolved_retcon_time_used = bool(
        retcon_time_used
        if retcon_time_used is not None
        else bool(getattr(chart, "retcon_time_used", False))
    )
    chart.birthtime_unknown = resolved_birthtime_unknown
    chart.retcon_time_used = resolved_retcon_time_used
    if retcon_hour is not None:
        chart.retcon_hour = int(retcon_hour)
    if retcon_minute is not None:
        chart.retcon_minute = int(retcon_minute)
    apply_time_specific_metadata_policy(chart)
    resolved_signs_unknown, resolved_unknown_signs = _resolve_unknown_sign_metadata(
        chart,
        birthtime_unknown=birthtime_unknown,
        retcon_time_used=retcon_time_used,
    )
    chart.signs_unknown = resolved_signs_unknown
    chart.unknown_signs = list(resolved_unknown_signs)
    human_design_type, human_design_authority = _resolve_human_design_metadata(chart)
    bazi_metadata = _resolve_bazi_metadata(chart)
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            UPDATE charts
            SET name = ?,
                alias = ?,
                from_whence = ?,
                gender = ?,
                birth_place = ?,
                datetime_iso = ?,
                tz_name = ?,
                lat = ?,
                lon = ?,
                used_utc_fallback = ?,
                sentiments = ?,
                relationship_types = ?,
                tags = ?,
                comments = ?,
                rectification_notes = ?,
                biography = ?,
                chart_data_source = ?,
                positive_sentiment_intensity = ?,
                negative_sentiment_intensity = ?,
                familiarity = ?,
                alignment_score = ?,
                matched_expectations = ?,
                familiarity_factors = ?,
                age_when_first_met = ?,
                year_first_encountered = ?,
                data_rating = ?,
                social_score = ?,
                birthtime_unknown = ?,
                signs_unknown = ?,
                unknown_signs = ?,
                retcon_time_used = ?,
                retcon_hour = ?,
                retcon_minute = ?,
                dominant_sign_weights = ?,
                dominant_planet_weights = ?,
                dominant_nakshatra_weights = ?,
                dominant_element_weights = ?,
                dominant_enneagram_type = ?,
                top_three_enneagram_types = ?,
                dominant_mode = ?,
                modal_distribution = ?,
                human_design_gates = ?,
                human_design_lines = ?,
                human_design_channels = ?,
                human_design_type = ?,
                human_design_authority = ?,
                bazi_year_pillar = ?,
                bazi_month_pillar = ?,
                bazi_day_pillar = ?,
                bazi_hour_pillar = ?,
                bazi_year_element = ?,
                bazi_month_element = ?,
                bazi_day_element = ?,
                bazi_hour_element = ?,
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
                getattr(chart, "from_whence", None),
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
                _serialize_tags(getattr(chart, "tags", [])),
                getattr(chart, "comments", None),
                getattr(chart, "rectification_notes", None),
                getattr(chart, "biography", None),
                getattr(chart, "chart_data_source", None),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "positive_sentiment_intensity", None)
                ),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "negative_sentiment_intensity", None)
                ),
                _normalize_optional_sentiment_metric(
                    getattr(chart, "familiarity", None)
                ),
                _normalize_alignment_score(
                    getattr(chart, "alignment_score", None)
                ),
                _normalize_matched_expectations(
                    getattr(chart, "matched_expectations", None)
                ),
                _serialize_familiarity_factors(
                    getattr(chart, "familiarity_factors", [])
                ),
                max(0, int(getattr(chart, "age_when_first_met", 0) or 0)),
                _normalize_year_first_encountered(getattr(chart, "year_first_encountered", None)),
                str(getattr(chart, "data_rating", "blank") or "blank"),
                calculate_social_score(
                    getattr(chart, "positive_sentiment_intensity", None),
                    getattr(chart, "negative_sentiment_intensity", None),
                    getattr(chart, "familiarity", None),
                ),
                int(resolved_birthtime_unknown),
                int(resolved_signs_unknown),
                _serialize_string_list(resolved_unknown_signs),
                int(resolved_retcon_time_used),
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
                _serialize_weight_map(
                    dominant_nakshatra_weights
                    if dominant_nakshatra_weights is not None
                    else getattr(chart, "dominant_nakshatra_weights", None)
                ),
                _serialize_weight_map(getattr(chart, "dominant_element_weights", None)),
                getattr(chart, "dominant_enneagram_type", None),
                _serialize_int_list(getattr(chart, "top_three_enneagram_types", None)),
                getattr(chart, "dominant_mode", None),
                _serialize_weight_map(getattr(chart, "modal_distribution", None)),
                _serialize_int_list(getattr(chart, "human_design_gates", None)),
                _serialize_int_list(getattr(chart, "human_design_lines", None)),
                _serialize_string_list(getattr(chart, "human_design_channels", None)),
                human_design_type,
                human_design_authority,
                bazi_metadata.get("bazi_year_pillar"),
                bazi_metadata.get("bazi_month_pillar"),
                bazi_metadata.get("bazi_day_pillar"),
                bazi_metadata.get("bazi_hour_pillar"),
                bazi_metadata.get("bazi_year_element"),
                bazi_metadata.get("bazi_month_element"),
                bazi_metadata.get("bazi_day_element"),
                bazi_metadata.get("bazi_hour_element"),
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
        Optional[int],
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
            Optional[int],
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
        normalized_familiarity = _normalize_optional_sentiment_metric(familiarity)
        resolved_social_score = (
            int(social_score)
            if social_score is not None
            else calculate_social_score(
                positive_sentiment_intensity,
                negative_sentiment_intensity,
                familiarity,
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


def list_duplicate_exclusions() -> set[tuple[int, int]]:
    """Return canonical chart-id pairs explicitly marked as not duplicates."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT chart_id_low, chart_id_high
        FROM duplicate_exclusions
        """
    ).fetchall()
    conn.close()
    return {
        (int(chart_id_low), int(chart_id_high))
        for chart_id_low, chart_id_high in rows
        if chart_id_low is not None and chart_id_high is not None
    }


def save_duplicate_exclusions(chart_ids: List[int]) -> int:
    """
    Persist all pair combinations from the provided chart ids as non-duplicates.

    Returns the number of newly-inserted pairs.
    """
    normalized_ids = sorted({int(chart_id) for chart_id in chart_ids if chart_id is not None})
    if len(normalized_ids) < 2:
        return 0
    now_iso = datetime.utcnow().isoformat(timespec="seconds")
    pairs: list[tuple[int, int, str]] = []
    for index, left_id in enumerate(normalized_ids):
        for right_id in normalized_ids[index + 1 :]:
            pairs.append((left_id, right_id, now_iso))
    conn = _get_conn()
    inserted = 0
    with conn:
        for left_id, right_id, created_at in pairs:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO duplicate_exclusions (
                    chart_id_low,
                    chart_id_high,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (left_id, right_id, created_at),
            )
            inserted += int(cursor.rowcount or 0)
    conn.close()
    return inserted


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
        conn.execute(
            f"""
            DELETE FROM duplicate_exclusions
            WHERE chart_id_low IN ({placeholders})
               OR chart_id_high IN ({placeholders})
            """,
            chart_ids + chart_ids,
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
        SELECT name, alias, from_whence, gender, birth_place, datetime_iso, tz_name, lat, lon,
               used_utc_fallback, sentiments, relationship_types,
               tags, comments, rectification_notes, biography, chart_data_source,
               positive_sentiment_intensity, negative_sentiment_intensity,
               familiarity, alignment_score, matched_expectations, {familiarity_factors_projection}, age_when_first_met, year_first_encountered, data_rating, birthtime_unknown, signs_unknown, unknown_signs,
               retcon_time_used, retcon_hour, retcon_minute,
               dominant_sign_weights, dominant_planet_weights, dominant_nakshatra_weights, dominant_element_weights, dominant_enneagram_type, top_three_enneagram_types, dominant_mode, modal_distribution,
               human_design_gates, human_design_lines, human_design_channels,
               human_design_type, human_design_authority,
               bazi_year_pillar, bazi_month_pillar, bazi_day_pillar, bazi_hour_pillar,
               bazi_year_element, bazi_month_element, bazi_day_element, bazi_hour_element,
               COALESCE(chart_type, source),
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
        from_whence,
        gender,
        birth_place,
        datetime_iso,
        tz_name,
        lat,
        lon,
        used_utc_fallback,
        sentiments,
        relationship_types,
        tags,
        comments,
        rectification_notes,
        biography,
        chart_data_source,
        positive_sentiment_intensity,
        negative_sentiment_intensity,
        familiarity,
        alignment_score,
        matched_expectations,
        familiarity_factors,
        age_when_first_met,
        year_first_encountered,
        data_rating,
        birthtime_unknown,
        signs_unknown,
        unknown_signs,
        retcon_time_used,
        retcon_hour,
        retcon_minute,
        dominant_sign_weights,
        dominant_planet_weights,
        dominant_nakshatra_weights,
        dominant_element_weights,
        dominant_enneagram_type,
        top_three_enneagram_types,
        dominant_mode,
        modal_distribution,
        human_design_gates,
        human_design_lines,
        human_design_channels,
        human_design_type,
        human_design_authority,
        bazi_year_pillar,
        bazi_month_pillar,
        bazi_day_pillar,
        bazi_hour_pillar,
        bazi_year_element,
        bazi_month_element,
        bazi_day_element,
        bazi_hour_element,
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
        placeholder.from_whence = from_whence
        placeholder.gender = gender
        placeholder.birth_place = birth_place
        placeholder.dt = datetime.fromisoformat(datetime_iso)
        placeholder.lat = lat
        placeholder.lon = lon
        placeholder.used_utc_fallback = bool(used_utc_fallback)
        placeholder.sentiments = parse_sentiments(sentiments)
        placeholder.relationship_types = parse_relationship_types(relationship_types)
        placeholder.tags = parse_tags(tags)
        placeholder.comments = comments or ""
        placeholder.rectification_notes = rectification_notes or ""
        placeholder.biography = biography or ""
        placeholder.chart_data_source = chart_data_source or ""
        placeholder.positive_sentiment_intensity = _normalize_optional_sentiment_metric(
            positive_sentiment_intensity
        )
        placeholder.negative_sentiment_intensity = _normalize_optional_sentiment_metric(
            negative_sentiment_intensity
        )
        normalized_familiarity = _normalize_optional_sentiment_metric(familiarity)
        placeholder.familiarity = normalized_familiarity
        placeholder.alignment_score = _normalize_alignment_score(alignment_score)
        placeholder.matched_expectations = _normalize_matched_expectations(matched_expectations)
        placeholder.sentiment_confidence = (
            normalized_familiarity if normalized_familiarity is not None else 1
        )
        placeholder.familiarity_factors = parse_familiarity_factors(
            familiarity_factors
        )
        placeholder.age_when_first_met = max(0, int(age_when_first_met or 0))
        placeholder.year_first_encountered = _normalize_year_first_encountered(year_first_encountered)
        placeholder.data_rating = str(data_rating or "blank")
        placeholder.birthtime_unknown = bool(birthtime_unknown)
        placeholder.signs_unknown = bool(signs_unknown)
        placeholder.unknown_signs = _parse_string_list(unknown_signs)
        placeholder.retcon_time_used = bool(retcon_time_used)
        placeholder.retcon_hour = int(retcon_hour) if retcon_hour is not None else None
        placeholder.retcon_minute = int(retcon_minute) if retcon_minute is not None else None
        placeholder.use_birth_time_data = chart_uses_houses(placeholder)
        placeholder.dominant_sign_weights = _parse_weight_map(dominant_sign_weights)
        placeholder.dominant_planet_weights = _parse_weight_map(dominant_planet_weights)
        placeholder.dominant_nakshatra_weights = _parse_weight_map(dominant_nakshatra_weights)
        placeholder.dominant_element_weights = _parse_weight_map(dominant_element_weights)
        placeholder.dominant_enneagram_type = int(dominant_enneagram_type) if dominant_enneagram_type is not None else None
        placeholder.top_three_enneagram_types = _parse_int_list(top_three_enneagram_types)
        placeholder.dominant_mode = str(dominant_mode).strip() if dominant_mode else None
        placeholder.modal_distribution = _parse_weight_map(modal_distribution)
        placeholder.human_design_gates = _parse_int_list(human_design_gates)
        placeholder.human_design_lines = _parse_int_list(human_design_lines)
        placeholder.human_design_channels = _parse_string_list(human_design_channels)
        placeholder.human_design_type = str(human_design_type).strip() if human_design_type else ""
        placeholder.human_design_authority = str(human_design_authority).strip() if human_design_authority else ""
        placeholder.bazi_year_pillar = str(bazi_year_pillar).strip() if bazi_year_pillar else ""
        placeholder.bazi_month_pillar = str(bazi_month_pillar).strip() if bazi_month_pillar else ""
        placeholder.bazi_day_pillar = str(bazi_day_pillar).strip() if bazi_day_pillar else ""
        placeholder.bazi_hour_pillar = str(bazi_hour_pillar).strip() if bazi_hour_pillar else ""
        placeholder.bazi_year_element = str(bazi_year_element).strip() if bazi_year_element else ""
        placeholder.bazi_month_element = str(bazi_month_element).strip() if bazi_month_element else ""
        placeholder.bazi_day_element = str(bazi_day_element).strip() if bazi_day_element else ""
        placeholder.bazi_hour_element = str(bazi_hour_element).strip() if bazi_hour_element else ""
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
        if not isinstance(placeholder.modal_distribution, dict):
            placeholder.modal_distribution = {}
        return placeholder

    dt = datetime.fromisoformat(datetime_iso)
    # If tz info is missing but we have a tz_name, attach it:
    if tz_name and dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))

    chart = Chart(name, dt, lat, lon, tz=None, alias=alias, from_whence=from_whence)
    chart.gender = gender
    chart.birth_place = birth_place
    chart.used_utc_fallback = bool(used_utc_fallback)
    chart.sentiments = parse_sentiments(sentiments)
    chart.relationship_types = parse_relationship_types(relationship_types)
    chart.tags = parse_tags(tags)
    chart.comments = comments or ""
    chart.rectification_notes = rectification_notes or ""
    chart.biography = biography or ""
    chart.chart_data_source = chart_data_source or ""
    chart.positive_sentiment_intensity = _normalize_optional_sentiment_metric(
        positive_sentiment_intensity
    )
    chart.negative_sentiment_intensity = _normalize_optional_sentiment_metric(
        negative_sentiment_intensity
    )
    chart.familiarity = _normalize_optional_sentiment_metric(familiarity)
    chart.alignment_score = _normalize_alignment_score(alignment_score)
    chart.matched_expectations = _normalize_matched_expectations(matched_expectations)
    chart.familiarity_factors = parse_familiarity_factors(
        familiarity_factors
    )
    chart.age_when_first_met = max(0, int(age_when_first_met or 0))
    chart.year_first_encountered = _normalize_year_first_encountered(year_first_encountered)
    chart.data_rating = str(data_rating or "blank")
    chart.birthtime_unknown = bool(birthtime_unknown)
    chart.signs_unknown = bool(signs_unknown)
    chart.unknown_signs = _parse_string_list(unknown_signs)
    chart.retcon_time_used = bool(retcon_time_used)
    chart.retcon_hour = int(retcon_hour) if retcon_hour is not None else None
    chart.retcon_minute = int(retcon_minute) if retcon_minute is not None else None
    chart.dominant_sign_weights = _parse_weight_map(dominant_sign_weights)
    chart.dominant_planet_weights = _parse_weight_map(dominant_planet_weights)
    chart.dominant_nakshatra_weights = _parse_weight_map(dominant_nakshatra_weights)
    chart.dominant_element_weights = _parse_weight_map(dominant_element_weights)
    chart.dominant_enneagram_type = int(dominant_enneagram_type) if dominant_enneagram_type is not None else None
    chart.top_three_enneagram_types = _parse_int_list(top_three_enneagram_types)
    chart.dominant_mode = str(dominant_mode).strip() if dominant_mode else None
    chart.modal_distribution = _parse_weight_map(modal_distribution)
    chart.human_design_gates = _parse_int_list(human_design_gates)
    chart.human_design_lines = _parse_int_list(human_design_lines)
    chart.human_design_channels = _parse_string_list(human_design_channels)
    chart.human_design_type = str(human_design_type).strip() if human_design_type else ""
    chart.human_design_authority = str(human_design_authority).strip() if human_design_authority else ""
    chart.bazi_year_pillar = str(bazi_year_pillar).strip() if bazi_year_pillar else ""
    chart.bazi_month_pillar = str(bazi_month_pillar).strip() if bazi_month_pillar else ""
    chart.bazi_day_pillar = str(bazi_day_pillar).strip() if bazi_day_pillar else ""
    chart.bazi_hour_pillar = str(bazi_hour_pillar).strip() if bazi_hour_pillar else ""
    chart.bazi_year_element = str(bazi_year_element).strip() if bazi_year_element else ""
    chart.bazi_month_element = str(bazi_month_element).strip() if bazi_month_element else ""
    chart.bazi_day_element = str(bazi_day_element).strip() if bazi_day_element else ""
    chart.bazi_hour_element = str(bazi_hour_element).strip() if bazi_hour_element else ""
    normalized_chart_type = _normalize_chart_type(chart_type)
    chart.chart_type = normalized_chart_type
    chart.source = normalized_chart_type
    chart.is_placeholder = bool(is_placeholder)
    chart.is_deceased = bool(is_deceased)
    chart.birth_month = birth_month
    chart.birth_day = birth_day
    chart.birth_year = birth_year
    apply_time_specific_metadata_policy(chart)
    chart.use_birth_time_data = chart_uses_houses(chart)
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


def invalidate_all_dominant_weight_caches() -> None:
    """Clear cached dominant-weight blobs so downstream reads recompute them."""
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            UPDATE charts
            SET dominant_sign_weights = '',
                dominant_planet_weights = '',
                dominant_nakshatra_weights = ''
            """
        )
    conn.close()


def backfill_unknown_time_chart_metadata(*, limit: Optional[int] = None) -> int:
    """
    Re-save non-placeholder charts where birth time is unknown and no rectified
    time is enabled, so time-specific metadata is sanitized consistently.
    """
    conn = _get_conn()
    query = """
        SELECT id
        FROM charts
        WHERE is_placeholder = 0
          AND birthtime_unknown = 1
          AND retcon_time_used = 0
        ORDER BY id ASC
    """
    if limit is not None:
        rows = conn.execute(query + " LIMIT ?", (max(0, int(limit)),)).fetchall()
    else:
        rows = conn.execute(query).fetchall()
    conn.close()

    chart_ids = [int(row[0]) for row in rows if row and row[0] is not None]
    for chart_id in chart_ids:
        chart = load_chart(chart_id)
        update_chart(
            chart_id,
            chart,
            birth_place=getattr(chart, "birth_place", None),
            sentiments=list(getattr(chart, "sentiments", []) or []),
            relationship_types=list(getattr(chart, "relationship_types", []) or []),
            birthtime_unknown=bool(getattr(chart, "birthtime_unknown", False)),
            retcon_time_used=bool(getattr(chart, "retcon_time_used", False)),
            dominant_sign_weights=dict(getattr(chart, "dominant_sign_weights", {}) or {}),
            dominant_planet_weights=dict(getattr(chart, "dominant_planet_weights", {}) or {}),
            dominant_nakshatra_weights=dict(getattr(chart, "dominant_nakshatra_weights", {}) or {}),
            chart_type=getattr(chart, "chart_type", None),
            source=getattr(chart, "source", None),
            is_placeholder=bool(getattr(chart, "is_placeholder", False)),
            is_deceased=bool(getattr(chart, "is_deceased", False)),
            birth_month=getattr(chart, "birth_month", None),
            birth_day=getattr(chart, "birth_day", None),
            birth_year=getattr(chart, "birth_year", None),
            retcon_hour=getattr(chart, "retcon_hour", None),
            retcon_minute=getattr(chart, "retcon_minute", None),
        )
    return len(chart_ids)
