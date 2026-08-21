#!/usr/bin/env python3
"""Promote a manually generated developer snapshot into the bundled catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / ".ephemeraldaddy" / ".prediction_norms_snapshot.json"
DEFAULT_DESTINATION = REPO_ROOT / "ephemeraldaddy" / "analysis" / "default_prediction_norms.json"


def bundle_snapshot(source: Path, destination: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Official prediction norms require a version-1 snapshot.")
    if int(payload.get("chart_count", 0) or 0) <= 0:
        raise ValueError("Official prediction norms require a non-empty developer cohort.")
    rows = payload.get("trait_baselines", {})
    if not isinstance(rows, dict) or not rows:
        raise ValueError("Official prediction norms require calculated trait baselines.")
    incomplete = [
        key
        for key, row in rows.items()
        if not isinstance(row, dict)
        or not str(row.get("profile_hash", "") or "")
        or not isinstance(row.get("db_average"), (int, float))
    ]
    if incomplete:
        raise ValueError(
            "Official prediction norms contain incomplete trait rows: "
            + ", ".join(sorted(incomplete)[:10])
        )
    bundled = dict(payload)
    bundled["source"] = "bundled_official"
    bundled["read_only"] = True
    bundled["complete"] = True
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(bundled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    payload = bundle_snapshot(args.snapshot, args.output)
    print(
        f"Bundled {len(payload['trait_baselines'])} trait norms from "
        f"{int(payload['chart_count']):,} charts at {args.output}"
    )


if __name__ == "__main__":
    main()
