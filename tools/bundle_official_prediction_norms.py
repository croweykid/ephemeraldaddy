#!/usr/bin/env python3
"""Prepare, validate, and promote developer Prediction Norms into Official.

This is a developer/release tool only. None of its compatibility or preparation
steps run during normal application startup or consumer prediction rendering.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ephemeraldaddy.analysis.traits import (  # noqa: E402
    DEFAULT_TRAITS_PATH,
    parse_trait_file,
    trait_uid_for_profile,
)


DEFAULT_SOURCE = Path.home() / ".ephemeraldaddy" / ".prediction_norms_snapshot.json"
DEFAULT_DESTINATION = REPO_ROOT / "ephemeraldaddy" / "analysis" / "default_prediction_norms.json"
DEFAULT_SOURCE_SELECTION = Path.home() / ".ephemeraldaddy" / ".prediction_norms_source.json"


def _stable_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _active_default_traits(path: Path = DEFAULT_TRAITS_PATH) -> list[dict[str, Any]]:
    profiles = parse_trait_file(path, skip_invalid_profiles=False)
    traits: list[dict[str, Any]] = []
    for name, profile in profiles.items():
        if bool(profile.get("archived", False)):
            continue
        uid = trait_uid_for_profile(name, profile, bundled=True)
        traits.append(
            {
                "name": str(name),
                "uid": str(uid),
                "key": f"uid:{uid}",
                "profile": dict(profile),
                "profile_hash": _stable_hash(profile),
            }
        )
    return traits


def validate_default_trait_coverage(
    payload: Mapping[str, Any],
    *,
    default_traits_path: Path = DEFAULT_TRAITS_PATH,
) -> dict[str, Any]:
    """Require exactly one compatible norm row for every active bundled Trait."""
    rows = payload.get("trait_baselines", {})
    if not isinstance(rows, Mapping):
        raise ValueError("Official prediction norms require a trait_baselines mapping.")

    traits = _active_default_traits(default_traits_path)
    traits_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trait in traits:
        traits_by_key[trait["key"]].append(trait)

    duplicate_keys = {
        key: sorted(str(trait["name"]) for trait in grouped)
        for key, grouped in traits_by_key.items()
        if len(grouped) > 1
    }
    if duplicate_keys:
        details = "; ".join(
            f"{key} => {', '.join(names)}"
            for key, names in sorted(duplicate_keys.items())
        )
        raise ValueError(
            "Bundled default Traits contain duplicate effective UIDs. "
            "Fix Trait identity before generating Official norms: "
            + details
        )

    problems: list[str] = []
    for trait in traits:
        row = rows.get(trait["key"])
        if not isinstance(row, Mapping):
            problems.append(f"{trait['name']}: missing row ({trait['key']})")
            continue

        row_name = str(row.get("name", "") or "").strip()
        if row_name and row_name.casefold() != str(trait["name"]).casefold():
            problems.append(
                f"{trait['name']}: {trait['key']} belongs to snapshot row {row_name!r}"
            )
            continue

        actual_hash = str(row.get("profile_hash", "") or "")
        if actual_hash != trait["profile_hash"]:
            problems.append(
                f"{trait['name']}: profile hash mismatch "
                f"(snapshot {actual_hash[:12] or '<missing>'}, "
                f"current {trait['profile_hash'][:12]})"
            )
            continue

        if not isinstance(row.get("db_average"), (int, float)):
            problems.append(f"{trait['name']}: invalid db_average")

    if problems:
        preview = "\n  - " + "\n  - ".join(problems[:20])
        remainder = len(problems) - min(len(problems), 20)
        suffix = f"\n  ... and {remainder} more" if remainder else ""
        raise ValueError(
            "Official prediction norms do not cover every active bundled Trait:"
            + preview
            + suffix
        )

    return {
        "active_default_trait_count": len(traits),
        "validated_default_trait_keys": sorted(trait["key"] for trait in traits),
    }


def prepare_local_source(path: Path = DEFAULT_SOURCE_SELECTION) -> Path:
    """One-time developer bootstrap: explicitly select My Database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"source": "my_database"}, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


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

    coverage = validate_default_trait_coverage(payload)

    bundled = dict(payload)
    bundled["source"] = "bundled_official"
    bundled["read_only"] = True
    bundled["complete"] = True
    bundled["validated_default_trait_count"] = coverage["active_default_trait_count"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(bundled, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument(
        "--prepare-local",
        action="store_true",
        help=(
            "Developer-only one-time bootstrap: select My Database so the dev build can "
            "generate a local snapshot before Official norms exist. Does not bundle anything."
        ),
    )
    args = parser.parse_args()

    if args.prepare_local:
        path = prepare_local_source()
        print(f"Selected My Database for the developer profile at {path}")
        print("Now run Recalculate DB Norms in the development build, close the app, then run this tool normally.")
        return

    payload = bundle_snapshot(args.snapshot, args.output)
    print(
        f"Bundled {len(payload['trait_baselines'])} trait norms from "
        f"{int(payload['chart_count']):,} charts at {args.output}"
    )
    print(
        f"Validated complete coverage for "
        f"{int(payload.get('validated_default_trait_count', 0))} active bundled default Traits."
    )


if __name__ == "__main__":
    main()
