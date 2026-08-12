#!/usr/bin/env python3
"""Validate repository inputs before a Windows or Linux release build."""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str
    required: bool = True


def _version() -> str:
    source = ROOT / "ephemeraldaddy" / "version.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise RuntimeError("authoritative __version__ is missing")


def _exists(relative_path: str) -> Check:
    path = ROOT / relative_path
    return Check(relative_path, path.exists(), "present" if path.exists() else "missing")


def _command(name: str, *, required: bool) -> Check:
    found = shutil.which(name)
    return Check(name, found is not None, found or "not found on PATH", required=required)


def common_checks() -> list[Check]:
    version = _version()
    generated = ROOT / "packaging" / "windows" / "version.iss"
    generated_ok = generated.exists() and f'#define MyAppVersion "{version}"' in generated.read_text(
        encoding="utf-8"
    )
    checks = [
        _exists("tools/cities15000.txt"),
        _exists("de421.bsp"),
        _exists("ephemeraldaddy/analysis/default_traits.json"),
        _exists("ephemeraldaddy/graphics/ephemeraldaddy.ico"),
        _exists("ephemeraldaddy/graphics/ephemeraldaddy.png"),
        Check("generated release version", generated_ok, version),
    ]
    try:
        import PyInstaller  # noqa: F401
    except Exception as exc:
        checks.append(Check("PyInstaller import", False, str(exc)))
    else:
        checks.append(Check("PyInstaller import", True, "available"))
    try:
        import PySide6  # noqa: F401
    except Exception as exc:
        checks.append(Check("PySide6 import", False, str(exc)))
    else:
        checks.append(Check("PySide6 import", True, "available"))
    return checks


def platform_checks(target: str) -> list[Check]:
    if target == "windows":
        return [
            _exists("installer.iss"),
            _exists("installer-onefile.iss"),
            _command("ISCC.exe", required=False),
        ]
    appimagetool = ROOT / "tools" / "appimagetool-x86_64.AppImage"
    appimage_available = appimagetool.is_file() and appimagetool.stat().st_mode & 0o111 != 0
    return [
        _exists("tools/build_appimage.sh"),
        _exists("flatpak/io.github.ephemeraldaddy.EphemeralDaddy.yml"),
        _exists("packaging/linux/io.github.ephemeraldaddy.EphemeralDaddy.desktop"),
        Check(
            "AppImage tool",
            appimage_available or bool(shutil.which("appimagetool")),
            "available" if appimage_available or shutil.which("appimagetool") else "optional target unavailable",
            required=False,
        ),
        _command("flatpak-builder", required=False),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("windows", "linux"), required=True)
    args = parser.parse_args()
    checks = [*common_checks(), *platform_checks(args.target)]
    failed_required = False
    for check in checks:
        if check.passed:
            marker = "PASS"
        elif check.required:
            marker = "FAIL"
            failed_required = True
        else:
            marker = "WARN"
        print(f"[{marker}] {check.name}: {check.detail}")
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
