# ephemeraldaddy/core/deps.py
"""Dependency verification helpers.

EphemeralDaddy now expects dependencies to be preinstalled (or bundled in an EXE).
This module verifies imports and returns helpful remediation instructions when a
module is missing.
"""

from __future__ import annotations

import importlib
from typing import Dict, Tuple


# pip_name -> import_name
REQUIRED_PACKAGES: Dict[str, str] = {
    "skyfield": "skyfield",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "rich": "rich",
    "timezonefinder": "timezonefinder",
    "geopy": "geopy",
    # Swiss Ephemeris (package installs as `pyswisseph`, imports as `swisseph`)
    "pyswisseph": "swisseph",
}


_module_cache: Dict[str, object] = {}


def _missing_dependency_message(pkg_name: str, module_name: str) -> str:
    return (
        f"Missing dependency '{pkg_name}' (import '{module_name}'). "
        "Install project dependencies before launching (example: `pip install -r requirements.txt` "
        "or `pip install -e .`), or run a bundled desktop build generated via "
        "`python tools/build_desktop_app.py --onefile`."
    )


def ensure_package(pkg_name: str, import_name: str | None = None):
    """Import a package and raise an actionable error if unavailable."""
    module_name = import_name or REQUIRED_PACKAGES.get(pkg_name, pkg_name)

    if module_name in _module_cache:
        return _module_cache[module_name]

    try:
        module = importlib.import_module(module_name)
    except ImportError as import_error:
        raise RuntimeError(_missing_dependency_message(pkg_name, module_name)) from import_error

    _module_cache[module_name] = module
    return module


def ensure_all_deps(verbose: bool = True) -> Dict[str, Tuple[str, object]]:
    """Ensure all REQUIRED_PACKAGES are importable."""
    results: Dict[str, Tuple[str, object]] = {}
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        if verbose:
            print(f"[EphemeralDaddy] Checking dependency: {pip_name} (import {import_name})")
        module = ensure_package(pip_name, import_name)
        results[pip_name] = (import_name, module)
    return results
