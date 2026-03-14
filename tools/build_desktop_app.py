#!/usr/bin/env python3
"""Build a standalone desktop app with bundled dependencies/resources.

This helper wraps PyInstaller for EphemeralDaddy and bundles package data plus
repo-level assets needed for offline operation.
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
            "PyInstaller is required. Install build deps with: "
            "python -m pip install pyinstaller pillow"
        ) from exc


def _normalize_data_tuples(items: Iterable[tuple[str, str]]) -> list[str]:
    sep = ";" if os.name == "nt" else ":"
    return [f"{source}{sep}{dest}" for source, dest in items]


def _coerce_icon(icon_arg: str | None) -> Path | None:
    """Return a valid platform icon path.

    - Windows: .ico required by PyInstaller. If a PNG is supplied, convert it to
      an .ico next to the source using Pillow.
    - macOS: .icns preferred (we do not auto-convert here).
    - Linux: PNG is fine.
    """
    if not icon_arg:
        return None

    icon_path = Path(icon_arg).expanduser().resolve()
    if not icon_path.exists():
        raise SystemExit(f"Icon not found: {icon_path}")

    if os.name != "nt":
        return icon_path

    if icon_path.suffix.lower() == ".ico":
        return icon_path

    if icon_path.suffix.lower() != ".png":
        raise SystemExit("On Windows, use a .ico icon (or provide a .png that can be converted).")

    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - runtime check
        raise SystemExit(
            "Pillow is required to convert PNG icons for Windows. "
            "Install build deps with: python -m pip install pyinstaller pillow"
        ) from exc

    converted = icon_path.with_suffix(".ico")
    with Image.open(icon_path) as img:
        # Typical multi-size icon set for Windows executables.
        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(converted, format="ICO", sizes=sizes)
    return converted


def _build_pyinstaller_command(args: argparse.Namespace) -> list[str]:
    from PyInstaller.utils.hooks import collect_data_files, collect_submodules

    hiddenimports = set(collect_submodules("ephemeraldaddy"))
    for package in ("skyfield", "timezonefinder", "geopy", "pandas", "numpy", "matplotlib", "swisseph"):
        hiddenimports.update(collect_submodules(package))

    data_tuples: list[tuple[str, str]] = []
    data_tuples.extend(collect_data_files("ephemeraldaddy", include_py_files=False))

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

    icon_path = _coerce_icon(args.icon)
    if icon_path:
        command.extend(["--icon", str(icon_path)])

    for hidden in sorted(hiddenimports):
        command.extend(["--hidden-import", hidden])

    for entry in _normalize_data_tuples(data_tuples):
        command.extend(["--add-data", entry])

    command.append("ephemeraldaddy/gui/app.py")
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icon", help="Icon path (.ico/.png on Windows; .icns on macOS; .png on Linux)")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single-file executable (simpler distribution, slower startup).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved PyInstaller command without executing it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ensure_pyinstaller()

    cmd = _build_pyinstaller_command(args)
    print(f"[build] Platform: {platform.system()} {platform.release()}")
    print("[build] Running:", " ".join(cmd))
    if args.dry_run:
        return

    _run_python(cmd)

    if os.name == "nt" and args.onefile:
        dist_target = REPO_ROOT / "dist" / f"{APP_NAME}.exe"
    else:
        dist_target = REPO_ROOT / "dist" / APP_NAME
    print(f"\nBuild complete. Output in: {dist_target}")


if __name__ == "__main__":
    main()
