# ephemeraldaddy/core/deps.py
"""
Dependency bootstrapper for EphemeralDaddy.

This module is responsible for:
- Importing required third-party packages
- Installing them via pip if they're missing
- Exposing a single ensure_all_deps() hook to call at startup
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from typing import Dict, Tuple


# pip_name -> import_name
REQUIRED_PACKAGES: Dict[str, str] = {
    # Core astro / math
    "skyfield": "skyfield",
    "numpy": "numpy",

    # Data handling / analysis
    "pandas": "pandas",

    # Plotting
    "matplotlib": "matplotlib",

    # Console UI niceties
    "rich": "rich",

    # Timezone / geocoding
    "timezonefinder": "timezonefinder",
    "geopy": "geopy",
    # Swiss Ephemeris (package installs as `pyswisseph`, imports as `swisseph`)
    "pyswisseph": "swisseph",}


# simple cache so we don't import the same thing repeatedly
_module_cache: Dict[str, object] = {}


def _pip_install(pkg_name: str) -> None:
    """Install a package using pip into the current environment."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])


def ensure_package(pkg_name: str, import_name: str | None = None):
    """
    Import a package, installing it via pip if missing.

    pkg_name: name used with pip (e.g. 'timezonefinder')
    import_name: module path to import (e.g. 'timezonefinder'), defaults to pkg_name

    Returns the imported module object.
    """
    module_name = import_name or REQUIRED_PACKAGES.get(pkg_name, pkg_name)

    # Check cache first
    if module_name in _module_cache:
        return _module_cache[module_name]

    try:
        module = importlib.import_module(module_name)
        _module_cache[module_name] = module
        return module
    except ImportError:
        # Try to install the package
        try:
            _pip_install(pkg_name)
        except Exception as install_error:
            raise RuntimeError(
                f"Missing dependency '{pkg_name}' and automatic install failed. "
                "Install dependencies manually (for example: pip install -e .)."
            ) from install_error

        try:
            module = importlib.import_module(module_name)
        except ImportError as import_error:
            raise RuntimeError(
                f"Dependency '{pkg_name}' was installed but still could not be imported as '{module_name}'."
            ) from import_error
        _module_cache[module_name] = module
        return module


def ensure_all_deps(verbose: bool = True) -> Dict[str, Tuple[str, object]]:
    """
    Ensure all REQUIRED_PACKAGES are importable, installing if needed.

    Returns a dict: pip_name -> (import_name, module_object)
    """
    results: Dict[str, Tuple[str, object]] = {}
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        if verbose:
            print(f"[EphemeralDaddy] Ensuring dependency: {pip_name} (import {import_name})")
        module = ensure_package(pip_name, import_name)
        results[pip_name] = (import_name, module)
    return results
