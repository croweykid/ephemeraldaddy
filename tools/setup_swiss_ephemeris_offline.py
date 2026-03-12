#!/usr/bin/env python3
"""Install Swiss Ephemeris minor-body files from a local folder for offline use.

This utility copies required Swiss files into a local ephemeris directory used by
`ephemeraldaddy` so asteroid/minor-body calculations work without network access.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REQUIRED_FILES: dict[str, str] = {
    "seas_18.se1": "Ceres, Pallas, Juno, Vesta",
    "seorbel.txt": "Chiron",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy Swiss Ephemeris minor-body files from a local directory into "
            "an offline ephemeris directory used by ephemeraldaddy."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Directory that already contains Swiss files (e.g. seas_18.se1, seorbel.txt).",
    )
    parser.add_argument(
        "--target",
        default="~/.local/share/ephemeraldaddy/sweph",
        help="Install destination (default: ~/.local/share/ephemeraldaddy/sweph).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files in target if they already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    if not source.is_dir():
        raise SystemExit(f"Source directory does not exist: {source}")

    missing = [name for name in REQUIRED_FILES if not (source / name).exists()]
    if missing:
        details = ", ".join(f"{name} ({REQUIRED_FILES[name]})" for name in missing)
        raise SystemExit(f"Missing required files in source: {details}")

    target.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    skipped: list[Path] = []
    for name in REQUIRED_FILES:
        src = source / name
        dst = target / name
        if dst.exists() and not args.overwrite:
            skipped.append(dst)
            continue
        shutil.copy2(src, dst)
        copied.append(dst)

    print("Swiss Ephemeris offline setup complete.")
    print(f"Target directory: {target}")
    if copied:
        print("Copied:")
        for path in copied:
            print(f"  - {path.name}")
    if skipped:
        print("Skipped (already existed, use --overwrite to replace):")
        for path in skipped:
            print(f"  - {path.name}")

    print("\nSet one of these environment variables for deterministic startup:")
    print(f"  export SWEPH_PATH='{target}'")
    print(f"  export EPHEMERALDADDY_SWEPH_PATH='{target}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
