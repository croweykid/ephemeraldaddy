"""Temporary one-time cleanup for legacy one-way Reminds Me Of links.

This module is intentionally small and self-contained so it can be removed after
existing personal databases have been normalized.  Future Chart View saves keep
new Reminds Me Of edits reciprocal at entry/save time.
"""

from __future__ import annotations

from dataclasses import dataclass

from ephemeraldaddy.core import db


@dataclass(frozen=True)
class RemindsMeOfReciprocityCleanupReport:
    """Summary of a one-time legacy Reminds Me Of reciprocity cleanup."""

    charts_scanned: int
    charts_updated: int
    reciprocal_links_added: int


def ensure_existing_reminds_me_of_reciprocity() -> RemindsMeOfReciprocityCleanupReport:
    """Add missing reverse Reminds Me Of UID links for existing one-way data."""
    conn = db._get_conn()
    try:
        with conn:
            db._ensure_chart_uids(conn)
            rows = conn.execute(
                "SELECT chart_uid, reminds_me_of FROM charts WHERE chart_uid IS NOT NULL AND chart_uid != ''"
            ).fetchall()
            rows_by_uid = {
                normalized_uid: raw_reminds_me_of
                for raw_uid, raw_reminds_me_of in rows
                for normalized_uid in [db._normalize_chart_uid(raw_uid)]
                if normalized_uid is not None
            }
            updated_uids: set[str] = set()
            reciprocal_links_added = 0

            for source_uid, raw_reminds_me_of in rows_by_uid.items():
                for target_uid in db.parse_reminds_me_of_uids(raw_reminds_me_of):
                    if target_uid == source_uid or target_uid not in rows_by_uid:
                        continue
                    target_reminds_me_of = db.parse_reminds_me_of_uids(rows_by_uid[target_uid])
                    if source_uid in target_reminds_me_of:
                        continue
                    target_reminds_me_of.append(source_uid)
                    serialized_target_links = db.serialize_reminds_me_of_uids(target_reminds_me_of)
                    rows_by_uid[target_uid] = serialized_target_links
                    updated_uids.add(target_uid)
                    reciprocal_links_added += 1
                    conn.execute(
                        "UPDATE charts SET reminds_me_of = ? WHERE chart_uid = ?",
                        (serialized_target_links, target_uid),
                    )
    finally:
        conn.close()

    return RemindsMeOfReciprocityCleanupReport(
        charts_scanned=len(rows_by_uid),
        charts_updated=len(updated_uids),
        reciprocal_links_added=reciprocal_links_added,
    )
