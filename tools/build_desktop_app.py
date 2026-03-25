#!/usr/bin/env python3
"""Build a standalone desktop app with bundled dependencies/resources.

This helper wraps PyInstaller for EphemeralDaddy and bundles package data plus
repo-level assets needed for offline operation.
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import pprint
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "EphemeralDaddy"
SPEC_PATH = REPO_ROOT / f"{APP_NAME}.spec"


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
    try:
        import PySide6  # noqa: F401
    except Exception as exc:  # pragma: no cover - runtime check
        raise SystemExit(
            "PySide6 is required in the build environment. "
            "Install project deps first with: python -m pip install -r requirements.txt"
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


def _build_datas() -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = []
    extra_files = [
        (REPO_ROOT / "tools" / "cities15000.txt", "tools"),
        (REPO_ROOT / "de421.bsp", "."),
    ]
    for src, dest in extra_files:
        if src.exists():
            datas.append((src.relative_to(REPO_ROOT).as_posix(), dest))

    for src_dir, dest in (
        (REPO_ROOT / "ephemeraldaddy" / "graphics", "ephemeraldaddy/graphics"),
        (REPO_ROOT / "ephemeraldaddy" / "gui" / "fonts", "ephemeraldaddy/gui/fonts"),
        (REPO_ROOT / "ephemeraldaddy" / "data" / "compiled", "ephemeraldaddy/data/compiled"),
    ):
        if src_dir.exists():
            datas.append((src_dir.relative_to(REPO_ROOT).as_posix(), dest))
    return datas


def _dynamic_hiddenimports() -> list[str]:
    """Collect import names loaded dynamically via `ensure_package`."""
    repo_root_str = str(REPO_ROOT)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    try:
        deps = importlib.import_module("ephemeraldaddy.core.deps")
        required = getattr(deps, "REQUIRED_PACKAGES", {})
    except Exception:
        return []
    return sorted({str(import_name) for import_name in required.values()})


def _write_spec(args: argparse.Namespace) -> Path:
    icon_path = _coerce_icon(args.icon)
    datas = _build_datas()
    hiddenimports = sorted(
        set(
            [
                "geopy.geocoders.nominatim",
            ]
            + _dynamic_hiddenimports()
        )
    )
    excludes = [
        "pytest",
        "pandas.tests",
        "numpy.tests",
        "numpy.f2py.tests",
        "matplotlib.tests",
        "skyfield.tests",
    ]
    icon_literal = repr(str(icon_path)) if icon_path else "None"
    spec = f"""# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")
shiboken_datas, shiboken_binaries, shiboken_hidden = collect_all("shiboken6")

datas = {pprint.pformat(datas, width=120)} + pyside_datas + shiboken_datas
binaries = pyside_binaries + shiboken_binaries
hiddenimports = {pprint.pformat(hiddenimports, width=120)} + pyside_hidden + shiboken_hidden
excludes = {pprint.pformat(excludes, width=120)}

a = Analysis(
    ["ephemeraldaddy/gui/bootstrap.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries={str(not args.onefile)},
    name={APP_NAME!r},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon_literal},
)
"""
    if args.onefile:
        spec += "\napp = BUNDLE(exe, name='EphemeralDaddy.app', icon=None, bundle_identifier=None)\n" if sys.platform == "darwin" else ""
    else:
        spec += """
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EphemeralDaddy',
)
"""
    SPEC_PATH.write_text(spec, encoding="utf-8")
    return SPEC_PATH


def _build_pyinstaller_command(spec_path: Path) -> list[str]:
    return ["-m", "PyInstaller", "--noconfirm", "--clean", str(spec_path)]


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

    spec_path = _write_spec(args)
    cmd = _build_pyinstaller_command(spec_path)
    print(f"[build] Platform: {platform.system()} {platform.release()}")
    print(f"[build] Spec: {spec_path}")
    print("[build] Running:", " ".join(cmd))
    if args.dry_run:
        return

    _run_python(cmd)

    if os.name == "nt" and args.onefile:
        dist_target = REPO_ROOT / "dist" / f"{APP_NAME}.exe"
    else:
        dist_target = REPO_ROOT / "dist" / APP_NAME
    print(f"\nBuild complete. Output in: {dist_target}")
    if os.name == "nt":
        if args.onefile:
            print(
                "[build] Inno Setup [Files] entry for this build:\n"
                f'        Source: "dist\\{APP_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion'
            )
        else:
            print(
                "[build] Inno Setup [Files] entry for this build (required for Qt deps):\n"
                f'        Source: "dist\\{APP_NAME}\\*"; DestDir: "{{app}}"; '
                "Flags: ignoreversion recursesubdirs createallsubdirs\n"
                "        (Do NOT ship only dist\\EphemeralDaddy.exe for folder builds.)"
            )


if __name__ == "__main__":
    main()
