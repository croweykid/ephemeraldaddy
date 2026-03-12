#!/usr/bin/env python3
"""Normalize and clean legacy sentiment labels in the chart database."""

from __future__ import annotations

import argparse
import json

from ephemeraldaddy.core.db import cleanup_sentiments_in_database
from ephemeraldaddy.core.interpretations import SENTIMENT_OPTIONS


def _parse_rename_pairs(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --rename value '{value}'. Expected old=new.")
        old_label, new_label = value.split("=", 1)
        old_label = old_label.strip()
        new_label = new_label.strip()
        if not old_label or not new_label:
            raise ValueError(f"Invalid --rename value '{value}'. Labels cannot be empty.")
        mapping[old_label] = new_label
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rename",
        action="append",
        default=[],
        help="Rename mapping in old=new form. Repeatable.",
    )
    parser.add_argument(
        "--max-sentiments",
        type=int,
        default=len(SENTIMENT_OPTIONS),
        help="Cap number of stored sentiments per row after normalization.",
    )
    parser.add_argument(
        "--drop-unknown",
        action="store_true",
        help="Drop sentiments not present in the current SENTIMENT_OPTIONS list.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip auto backup before running cleanup.",
    )
    args = parser.parse_args()

    rename_map = _parse_rename_pairs(args.rename)
    summary = cleanup_sentiments_in_database(
        renamed_labels=rename_map,
        max_sentiments=args.max_sentiments,
        keep_unknown=not args.drop_unknown,
        create_backup=not args.no_backup,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
