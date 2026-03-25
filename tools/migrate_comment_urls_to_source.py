#!/usr/bin/env python3
"""
Migrate chart source URLs from `comments` into `chart_data_source`.

Default behavior is a dry run. Use --apply to write updates.

Examples
--------
Dry run:
    python tools/migrate_comment_urls_to_source.py

Apply updates:
    python tools/migrate_comment_urls_to_source.py --apply

Apply and also strip migrated URL from comments:
    python tools/migrate_comment_urls_to_source.py --apply --strip-url-from-comments
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


DEFAULT_DB_PATH = Path.home() / ".ephemeraldaddy" / "charts.db"
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,;:!?)]}\"'"
NAME_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass
class ExtractionResult:
    url: str | None
    reason: str
    confidence: int


def _name_tokens(name: str) -> list[str]:
    return NAME_TOKEN_PATTERN.findall((name or "").lower())


def _normalize_candidate_url(raw: str) -> str:
    cleaned = raw.strip().rstrip(TRAILING_URL_PUNCTUATION)
    return cleaned


def _path_tail_tokens(url: str) -> tuple[str, list[str]]:
    parsed = urlparse(url)
    path = unquote(parsed.path or "")
    tail = path.rstrip("/").split("/")[-1].lower() if path else ""
    tail_tokens = NAME_TOKEN_PATTERN.findall(tail)
    return tail, tail_tokens


def _score_url_for_chart(url: str, chart_name: str) -> tuple[int, str]:
    """
    Score URL candidates against chart name.

    Heuristics:
    - Higher score if the tail includes full chart name tokens.
    - Strong bonus if tail ends with "_lastname" (or "-lastname") for multi-token names.
    - Bonus if single-token chart name appears in tail.
    """
    score = 0
    reasons: list[str] = []
    tail, tail_tokens = _path_tail_tokens(url)
    name_tokens = _name_tokens(chart_name)

    if not tail:
        return score, "empty path tail"
    if not name_tokens:
        return 1, "no chart name tokens; fallback"

    tail_token_set = set(tail_tokens)
    overlap = [token for token in name_tokens if token in tail_token_set]
    if overlap:
        score += len(overlap) * 3
        reasons.append(f"token overlap: {', '.join(overlap)}")

    full_join_underscore = "_".join(name_tokens)
    full_join_hyphen = "-".join(name_tokens)
    if full_join_underscore in tail or full_join_hyphen in tail:
        score += 8
        reasons.append("full-name slug match")

    if len(name_tokens) >= 2:
        last_name = name_tokens[-1]
        if tail.endswith(f"_{last_name}") or tail.endswith(f"-{last_name}"):
            score += 10
            reasons.append("tail ends with last name")
    else:
        single_name = name_tokens[0]
        if tail == single_name or tail.endswith(f"/{single_name}") or single_name in tail_tokens:
            score += 6
            reasons.append("single-name tail match")

    if score == 0:
        return 1, "url found but no strong name match"
    return score, "; ".join(reasons)


def extract_source_url(comment_text: str, chart_name: str) -> ExtractionResult:
    raw_matches = URL_PATTERN.findall(comment_text or "")
    if not raw_matches:
        return ExtractionResult(url=None, reason="No URL found in comments.", confidence=0)

    normalized = [_normalize_candidate_url(match) for match in raw_matches]
    scored: list[tuple[int, str, str]] = []
    for url in normalized:
        score, reason = _score_url_for_chart(url, chart_name)
        scored.append((score, reason, url))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_reason, best_url = scored[0]
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return ExtractionResult(
            url=best_url,
            reason=f"Ambiguous multiple URLs; picked first best match. ({best_reason})",
            confidence=max(1, best_score),
        )

    return ExtractionResult(url=best_url, reason=best_reason, confidence=max(1, best_score))


def strip_url_from_comments(comment_text: str, url: str) -> str:
    if not comment_text or not url:
        return comment_text or ""
    updated = comment_text.replace(url, "").strip()
    return re.sub(r"\s{2,}", " ", updated)


def migrate(
    db_path: Path,
    apply: bool,
    overwrite: bool,
    strip_migrated_url: bool,
    log_path: Path,
) -> int:
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("PRAGMA table_info(charts)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "chart_data_source" not in columns:
        print("Table 'charts' is missing 'chart_data_source'. Please run the main app once to migrate schema.")
        conn.close()
        return 2

    rows = conn.execute(
        """
        SELECT id, name, comments, chart_data_source
        FROM charts
        WHERE comments IS NOT NULL
          AND trim(comments) != ''
        ORDER BY id ASC
        """
    ).fetchall()

    updated = 0
    skipped_existing_source = 0
    no_url_found = 0
    ambiguous = 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        writer.writerow(
            [
                "chart_id",
                "chart_name",
                "status",
                "confidence",
                "reason",
                "selected_url",
            ]
        )

        for row in rows:
            chart_id = int(row["id"])
            chart_name = str(row["name"] or "").strip()
            comments = str(row["comments"] or "")
            existing_source = str(row["chart_data_source"] or "").strip()

            if existing_source and not overwrite:
                skipped_existing_source += 1
                writer.writerow(
                    [chart_id, chart_name, "skipped_existing_source", "", "chart_data_source already populated", existing_source]
                )
                continue

            result = extract_source_url(comments, chart_name)
            if not result.url:
                no_url_found += 1
                writer.writerow([chart_id, chart_name, "manual_review_no_url", 0, result.reason, ""])
                continue

            if "Ambiguous" in result.reason:
                ambiguous += 1

            if apply:
                if strip_migrated_url:
                    updated_comments = strip_url_from_comments(comments, result.url)
                    conn.execute(
                        """
                        UPDATE charts
                        SET chart_data_source = ?,
                            comments = ?
                        WHERE id = ?
                        """,
                        (result.url, updated_comments, chart_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE charts
                        SET chart_data_source = ?
                        WHERE id = ?
                        """,
                        (result.url, chart_id),
                    )

            updated += 1
            writer.writerow([chart_id, chart_name, "migrated", result.confidence, result.reason, result.url])

    if apply:
        conn.commit()
    conn.close()

    mode = "APPLY" if apply else "DRY RUN"
    print(f"[{mode}] scanned rows: {len(rows)}")
    print(f"[{mode}] migrated candidates: {updated}")
    print(f"[{mode}] skipped (existing source): {skipped_existing_source}")
    print(f"[{mode}] no URL found (manual review): {no_url_found}")
    print(f"[{mode}] ambiguous URL matches: {ambiguous}")
    print(f"[{mode}] log written: {log_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate URL-like source data from chart comments into chart_data_source."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to charts.db (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to the database. Without this flag, script runs in dry-run mode.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite chart_data_source if it already has a value.",
    )
    parser.add_argument(
        "--strip-url-from-comments",
        action="store_true",
        help="Also remove the migrated URL text from comments when applying updates.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/comment_url_to_source_migration.csv"),
        help="CSV log path for migration output and manual-review rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return migrate(
        db_path=args.db_path,
        apply=args.apply,
        overwrite=args.overwrite,
        strip_migrated_url=args.strip_url_from_comments,
        log_path=args.log_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
