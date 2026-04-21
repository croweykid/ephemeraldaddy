#!/usr/bin/env python3
"""Backfill chart metadata for unknown-time charts without rectified time."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ephemeraldaddy.core.db import backfill_unknown_time_chart_metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-save non-placeholder charts where birthtime_unknown=1 and "
            "retcon_time_used=0 so time-specific metadata is sanitized."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of rows to process.",
    )
    args = parser.parse_args()
    updated = backfill_unknown_time_chart_metadata(limit=args.limit)
    print(f"Backfilled {updated} chart(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
