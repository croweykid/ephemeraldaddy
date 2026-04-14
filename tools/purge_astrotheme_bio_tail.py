#!/usr/bin/env python3
"""
Purge imported Astrotheme biography tails in the local charts database.

The scraper marker below identifies the start of non-biography content:
    "Astrological Profile of "

For each matching record, this script keeps everything before that marker
and removes everything after it. By default this is a dry run.

Examples
--------
Dry run:
    python tools/purge_astrotheme_bio_tail.py

Apply updates:
    python tools/purge_astrotheme_bio_tail.py --apply

Custom database path:
    python tools/purge_astrotheme_bio_tail.py --db /path/to/charts.db --apply
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path.home() / ".ephemeraldaddy" / "charts.db"
TERMINATOR = "Astrological Profile of "


def _trim_bio(raw_bio: str) -> str:
    marker_index = raw_bio.find(TERMINATOR)
    if marker_index < 0:
        return raw_bio
    return raw_bio[:marker_index].rstrip(" \t\r\n-:|")


def _resolve_bio_column(conn: sqlite3.Connection) -> str:
    columns = {
        str(row[1]).strip().lower()
        for row in conn.execute("PRAGMA table_info(charts)").fetchall()
    }
    if "biography" in columns:
        return "biography"
    if "bio" in columns:
        return "bio"
    raise RuntimeError("Table 'charts' has neither 'biography' nor 'bio' column.")


def purge_bios(db_path: Path, *, apply: bool) -> int:
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 2

    conn = sqlite3.connect(db_path)
    try:
        bio_column = _resolve_bio_column(conn)
        rows = conn.execute(
            f"""
            SELECT id, name, {bio_column}
            FROM charts
            WHERE {bio_column} IS NOT NULL
              AND instr({bio_column}, ?) > 0
            ORDER BY id ASC
            """,
            (TERMINATOR,),
        ).fetchall()

        updated = 0
        unchanged = 0
        for chart_id, chart_name, raw_bio in rows:
            existing_bio = str(raw_bio or "")
            trimmed_bio = _trim_bio(existing_bio)
            if trimmed_bio == existing_bio:
                unchanged += 1
                continue

            if apply:
                conn.execute(
                    f"UPDATE charts SET {bio_column} = ? WHERE id = ?",
                    (trimmed_bio, int(chart_id)),
                )
            updated += 1

            if updated <= 10:
                print(f"candidate id={chart_id} name={str(chart_name or '').strip()!r}")

        mode = "APPLY" if apply else "DRY RUN"
        print(f"[{mode}] bio column: {bio_column}")
        print(f"[{mode}] matched rows: {len(rows)}")
        print(f"[{mode}] rows to update: {updated}")
        print(f"[{mode}] unchanged matches: {unchanged}")

        if apply:
            conn.commit()
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trim Astrotheme biography tails in the charts database."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to charts database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to the database. Without this flag, script runs in dry-run mode.",
    )
    args = parser.parse_args()
    return purge_bios(args.db, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
