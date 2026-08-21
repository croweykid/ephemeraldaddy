#!/usr/bin/env python3
"""Diagnose Trait coverage/identity problems in a Prediction Norms snapshot.

This is a developer diagnostic only. It never recalculates norms and never
modifies the database, Trait files, source selection, or bundled catalog.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from ephemeraldaddy.analysis.traits import list_traits
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    _load_snapshot_file,
    _stable_hash,
    _trait_key,
    load_prediction_norms_snapshot,
    load_prediction_norms_source,
    prediction_norms_snapshot_path,
)


def _profile_hash(trait: dict[str, Any]) -> str:
    return _stable_hash(trait.get("profile", {}) or {})


def audit_trait_norm_coverage(
    traits: list[dict[str, Any]], snapshot: dict[str, Any]
) -> dict[str, Any]:
    rows = snapshot.get("trait_baselines", {}) if isinstance(snapshot, dict) else {}
    rows = rows if isinstance(rows, dict) else {}

    active_traits = [
        trait
        for trait in traits
        if str(trait.get("name", "") or "").strip()
        and not bool(trait.get("archived", False))
    ]

    traits_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trait in active_traits:
        traits_by_key[_trait_key(trait)].append(trait)

    duplicate_keys = {
        key: sorted(str(trait.get("name", "") or "") for trait in grouped)
        for key, grouped in traits_by_key.items()
        if len(grouped) > 1
    }

    issues: list[dict[str, Any]] = []
    covered: list[str] = []
    expected_keys: set[str] = set()

    for trait in active_traits:
        name = str(trait.get("name", "") or "").strip()
        key = _trait_key(trait)
        expected_keys.add(key)
        row = rows.get(key)

        if key in duplicate_keys:
            issues.append(
                {
                    "name": name,
                    "key": key,
                    "reason": "duplicate_trait_key",
                    "detail": ", ".join(duplicate_keys[key]),
                }
            )
            continue

        if not isinstance(row, dict):
            issues.append(
                {
                    "name": name,
                    "key": key,
                    "reason": "missing_row",
                    "detail": "No norm row exists for the Trait key.",
                }
            )
            continue

        row_name = str(row.get("name", "") or "").strip()
        if row_name and row_name.casefold() != name.casefold():
            issues.append(
                {
                    "name": name,
                    "key": key,
                    "reason": "row_owned_by_other_trait",
                    "detail": f"Snapshot row is named {row_name!r}.",
                }
            )
            continue

        expected_hash = _profile_hash(trait)
        actual_hash = str(row.get("profile_hash", "") or "")
        if actual_hash != expected_hash:
            issues.append(
                {
                    "name": name,
                    "key": key,
                    "reason": "profile_hash_mismatch",
                    "detail": (
                        f"snapshot={actual_hash[:12] or '<missing>'} "
                        f"current={expected_hash[:12]}"
                    ),
                }
            )
            continue

        if not isinstance(row.get("db_average"), (int, float)):
            issues.append(
                {
                    "name": name,
                    "key": key,
                    "reason": "invalid_db_average",
                    "detail": repr(row.get("db_average")),
                }
            )
            continue

        covered.append(name)

    orphan_rows = sorted(str(key) for key in rows if str(key) not in expected_keys)
    return {
        "active_trait_count": len(active_traits),
        "row_count": len(rows),
        "covered_count": len(covered),
        "covered": sorted(covered, key=str.casefold),
        "issues": sorted(issues, key=lambda item: (item["name"].casefold(), item["reason"])),
        "duplicate_keys": duplicate_keys,
        "orphan_rows": orphan_rows,
    }


def _print_report(report: dict[str, Any], *, source_label: str, snapshot_path: Path) -> None:
    print(f"Prediction Norms source: {source_label}")
    print(f"Snapshot: {snapshot_path}")
    print(
        "Trait coverage: "
        f"{report['covered_count']}/{report['active_trait_count']} active Traits "
        f"({report['row_count']} snapshot rows)"
    )

    issues = report.get("issues", [])
    if not issues:
        print("No active Trait norm coverage problems found.")
    else:
        print("\nProblems:")
        for issue in issues:
            print(
                f"- {issue['name']}: {issue['reason']} "
                f"[{issue['key']}] — {issue['detail']}"
            )

    orphan_rows = report.get("orphan_rows", [])
    if orphan_rows:
        print("\nSnapshot rows not owned by an active Trait:")
        for key in orphan_rows:
            print(f"- {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Audit an explicit version-1 snapshot instead of the currently selected source.",
    )
    args = parser.parse_args()

    if args.snapshot is not None:
        snapshot = _load_snapshot_file(args.snapshot)
        source_label = "explicit file"
        snapshot_path = args.snapshot
    else:
        source = load_prediction_norms_source()
        snapshot = load_prediction_norms_snapshot()
        source_label = source
        snapshot_path = prediction_norms_snapshot_path(source)

    traits = list_traits(active_only=True)
    report = audit_trait_norm_coverage(traits, snapshot)
    _print_report(report, source_label=source_label, snapshot_path=snapshot_path)
    return 1 if report.get("issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
