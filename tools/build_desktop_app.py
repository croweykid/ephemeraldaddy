#!/usr/bin/env python3
"""Build a standalone desktop app with bundled dependencies.

This helper wraps PyInstaller and aggressively collects package data and hidden
imports so the generated binary can run in offline/locked-down environments.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "EphemeralDaddy"


def _run_python(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run([sys.executable, *cmd], cwd=cwd or REPO_ROOT, check=True)


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except Exception as exc:  # pragma: no cover - runtime check
        raise SystemExit(
            "PyInstaller is required. Install it with: python -m pip install pyinstaller"
        ) from exc


def _normalize_data_tuples(items: Iterable[tuple[str, str]]) -> list[str]:
    out: list[str] = []
    sep = ";" if os.name == "nt" else ":"
    for source, dest in items:
        out.append(f"{source}{sep}{dest}")
    return out


def _build_pyinstaller_command(args: argparse.Namespace) -> list[str]:
    from PyInstaller.utils.hooks import collect_data_files, collect_submodules

    hiddenimports = set(collect_submodules("ephemeraldaddy"))
    for package in ("skyfield", "timezonefinder", "geopy", "pandas", "numpy", "matplotlib", "swisseph"):
        hiddenimports.update(collect_submodules(package))

    data_tuples: list[tuple[str, str]] = []
    data_tuples.extend(collect_data_files("ephemeraldaddy", include_py_files=False))

    # Non-package resources referenced by repo-relative path lookups.
    extras = [
        (REPO_ROOT / "tools" / "cities15000.txt", "tools"),
        (REPO_ROOT / "de421.bsp", "."),
    ]
    for src, dest in extras:
        if src.exists():
            data_tuples.append((str(src), dest))

    command = [
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--collect-all",
        "PySide6",
    ]

    if args.onefile:
        command.append("--onefile")

    if args.icon:
        command.extend(["--icon", str(Path(args.icon).resolve())])

    for hidden in sorted(hiddenimports):
        command.extend(["--hidden-import", hidden])

    for entry in _normalize_data_tuples(data_tuples):
        command.extend(["--add-data", entry])

    command.append("ephemeraldaddy/gui/app.py")
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icon", help="Path to icon (.ico for Windows, .icns for macOS, .png for Linux)")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single-file executable (slower startup but easier distribution).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ensure_pyinstaller()

    cmd = _build_pyinstaller_command(args)
    print(f"[build] Platform: {platform.system()} {platform.release()}")
    print("[build] Running:", " ".join(cmd))
    _run_python(cmd)

    dist_target = REPO_ROOT / "dist" / (f"{APP_NAME}.exe" if os.name == "nt" and args.onefile else APP_NAME)
    print(f"\nBuild complete. Output in: {dist_target}")


if __name__ == "__main__":
    main()
